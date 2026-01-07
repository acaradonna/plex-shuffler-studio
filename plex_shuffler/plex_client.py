"""Minimal Plex API client using standard library only."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from plex_shuffler import __version__
from plex_shuffler.models import LibrarySection, MediaItem, PlaylistInfo

LOGGER = logging.getLogger(__name__)


class PlexError(RuntimeError):
    pass


class PlexClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._machine_identifier: str | None = None

    def _request(
        self,
        path: str,
        params: Iterable[tuple[str, str]] | None = None,
        method: str = "GET",
    ) -> ET.Element:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(list(params), doseq=True)}"

        headers = {
            "X-Plex-Token": self.token,
            "X-Plex-Product": "Plex Shuffler Studio",
            "X-Plex-Version": __version__,
            "X-Plex-Client-Identifier": "plex-shuffler-studio",
            "Accept": "application/xml",
        }

        request = Request(url, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise PlexError(f"Plex API error {exc.code} for {url}: {body}") from exc
        except URLError as exc:
            raise PlexError(f"Plex API connection error for {url}: {exc}") from exc

        try:
            return ET.fromstring(data)
        except ET.ParseError as exc:
            snippet = data[:200].decode("utf-8", errors="replace")
            raise PlexError(f"Invalid Plex API response from {url}: {snippet}") from exc

    def _get_machine_identifier(self) -> str:
        if self._machine_identifier:
            return self._machine_identifier
        root = self._request("/identity")
        machine_identifier = root.attrib.get("machineIdentifier")
        if not machine_identifier:
            server = root.find("Server")
            if server is not None:
                machine_identifier = server.attrib.get("machineIdentifier")
        if not machine_identifier:
            raise PlexError("Unable to determine Plex machine identifier from /identity")
        self._machine_identifier = machine_identifier
        return self._machine_identifier

    def get_sections(self) -> list[LibrarySection]:
        root = self._request("/library/sections")
        sections = []
        for entry in root.findall("Directory"):
            sections.append(
                LibrarySection(
                    key=entry.attrib.get("key", ""),
                    title=entry.attrib.get("title", ""),
                    type=entry.attrib.get("type", ""),
                )
            )
        return sections

    def get_section_by_title(self, title: str) -> LibrarySection:
        lowered = title.strip().lower()
        for section in self.get_sections():
            if section.title.strip().lower() == lowered:
                return section
        raise PlexError(f"Library section not found: {title}")

    def get_shows(self, section_key: str, query: list[tuple[str, str]] | None = None) -> list[MediaItem]:
        params = [("type", "2")]
        if query:
            params.extend(query)
        root = self._request(f"/library/sections/{section_key}/all", params=params)
        shows = []
        for entry in root.findall("Directory"):
            if entry.attrib.get("type") != "show":
                continue
            shows.append(
                MediaItem(
                    rating_key=entry.attrib.get("ratingKey", ""),
                    title=entry.attrib.get("title", ""),
                    type="show",
                )
            )
        return shows

    def get_show_episodes(self, show_key: str, query: list[tuple[str, str]] | None = None) -> list[MediaItem]:
        params = []
        if query:
            params.extend(query)
        root = self._request(f"/library/metadata/{show_key}/allLeaves", params=params)
        episodes = []
        for entry in root.findall("Video"):
            if entry.attrib.get("type") != "episode":
                continue
            episodes.append(self._parse_episode(entry))
        return episodes

    def get_movies(self, section_key: str, query: list[tuple[str, str]] | None = None) -> list[MediaItem]:
        params = [("type", "1")]
        if query:
            params.extend(query)
        root = self._request(f"/library/sections/{section_key}/all", params=params)
        movies = []
        for entry in root.findall("Video"):
            if entry.attrib.get("type") != "movie":
                continue
            movies.append(self._parse_movie(entry))
        return movies

    def get_collections(self, section_key: str, query: list[tuple[str, str]] | None = None) -> list[MediaItem]:
        params = []
        if query:
            params.extend(query)
        try:
            root = self._request(f"/library/sections/{section_key}/collections", params=params)
        except PlexError as exc:
            LOGGER.warning("Collections endpoint failed, retrying with fallback: %s", exc)
            fallback_params = list(params) + [("type", "18")]
            root = self._request(f"/library/sections/{section_key}/all", params=fallback_params)
        collections = []
        for entry in root.findall("Directory"):
            if entry.attrib.get("type") not in {"collection", "collectionGroup"}:
                continue
            collections.append(
                MediaItem(
                    rating_key=entry.attrib.get("ratingKey", ""),
                    title=entry.attrib.get("title", ""),
                    type="collection",
                )
            )
        return collections

    def get_collection_items(self, collection_key: str) -> list[MediaItem]:
        root = self._request(f"/library/metadata/{collection_key}/children")
        items = []
        for entry in root.findall("Video"):
            if entry.attrib.get("type") != "movie":
                continue
            items.append(self._parse_movie(entry))
        return items

    def get_filter_options(
        self,
        section_key: str,
        source: str,
        media_type: str | None = None,
    ) -> list[str]:
        params: list[tuple[str, str]] = []
        if media_type:
            type_value = _media_type_param(media_type)
            if type_value:
                params.append(("type", type_value))
        try:
            root = self._request(f"/library/sections/{section_key}/{source}", params=params)
            return _parse_filter_options(root)
        except PlexError:
            if source == "collection":
                collections = self.get_collections(section_key)
                return sorted(
                    {entry.title for entry in collections if entry.title},
                    key=str.lower,
                )
            raise

    def get_playlists(self, title: str | None = None) -> list[PlaylistInfo]:
        params: list[tuple[str, str]] = []
        if title:
            params.append(("title", title))
        root = self._request("/playlists", params=params)
        playlists = []
        for entry in root.findall("Playlist"):
            playlists.append(
                PlaylistInfo(
                    rating_key=entry.attrib.get("ratingKey", ""),
                    title=entry.attrib.get("title", ""),
                    playlist_type=entry.attrib.get("playlistType", ""),
                )
            )
        return playlists

    def delete_playlist(self, playlist_key: str) -> None:
        self._request(f"/playlists/{playlist_key}", method="DELETE")

    def create_playlist(self, title: str, rating_keys: list[str], list_type: str = "video") -> PlaylistInfo:
        if not rating_keys:
            raise PlexError("Cannot create playlist without items")

        machine_identifier = self._get_machine_identifier()
        uri = f"server://{machine_identifier}/com.plexapp.plugins.library/library/metadata/{','.join(rating_keys)}"
        params = [("uri", uri), ("type", list_type), ("title", title), ("smart", "0")]
        root = self._request("/playlists", params=params, method="POST")

        playlist = root.find("Playlist")
        if playlist is None:
            raise PlexError("Playlist creation failed: no playlist returned")

        return PlaylistInfo(
            rating_key=playlist.attrib.get("ratingKey", ""),
            title=playlist.attrib.get("title", title),
            playlist_type=playlist.attrib.get("playlistType", list_type),
        )

    def add_playlist_items(self, playlist_key: str, rating_keys: list[str]) -> None:
        if not rating_keys:
            return
        machine_identifier = self._get_machine_identifier()
        uri = f"server://{machine_identifier}/com.plexapp.plugins.library/library/metadata/{','.join(rating_keys)}"
        params = [("uri", uri)]
        self._request(f"/playlists/{playlist_key}/items", params=params, method="PUT")

    @staticmethod
    def _parse_episode(entry: ET.Element) -> MediaItem:
        return MediaItem(
            rating_key=entry.attrib.get("ratingKey", ""),
            title=entry.attrib.get("title", ""),
            type="episode",
            show_title=entry.attrib.get("grandparentTitle"),
            season_index=_parse_int(entry.attrib.get("parentIndex")),
            episode_index=_parse_int(entry.attrib.get("index")),
            originally_available_at=_parse_date(entry.attrib.get("originallyAvailableAt")),
            view_count=_parse_int(entry.attrib.get("viewCount")),
            last_viewed_at=_parse_timestamp(entry.attrib.get("lastViewedAt")),
        )

    @staticmethod
    def _parse_movie(entry: ET.Element) -> MediaItem:
        return MediaItem(
            rating_key=entry.attrib.get("ratingKey", ""),
            title=entry.attrib.get("title", ""),
            type="movie",
            originally_available_at=_parse_date(entry.attrib.get("originallyAvailableAt")),
            view_count=_parse_int(entry.attrib.get("viewCount")),
            last_viewed_at=_parse_timestamp(entry.attrib.get("lastViewedAt")),
        )


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _media_type_param(media_type: str) -> str | None:
    lowered = media_type.strip().lower()
    if lowered in {"movie", "movies", "1"}:
        return "1"
    if lowered in {"show", "shows", "tv", "2"}:
        return "2"
    return None


def _parse_filter_options(root: ET.Element) -> list[str]:
    values: set[str] = set()
    for entry in root.findall("Directory") + root.findall("Tag"):
        title = entry.attrib.get("title") or entry.attrib.get("tag") or entry.attrib.get("name")
        if title:
            values.add(title)
    return sorted(values, key=str.lower)


def _parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromtimestamp(int(value), tz=dt.timezone.utc)
    except (ValueError, OSError):
        return None
