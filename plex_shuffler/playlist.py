"""Playlist synchronization helpers."""

from __future__ import annotations

import logging

from plex_shuffler.models import MediaItem, PlaylistInfo
from plex_shuffler.plex_client import PlexClient
from plex_shuffler.utils import chunked

LOGGER = logging.getLogger(__name__)


def sync_playlist(
    client: PlexClient,
    name: str,
    items: list[MediaItem],
    mode: str = "replace",
    chunk_size: int = 200,
) -> PlaylistInfo | None:
    if not items:
        LOGGER.warning("Playlist %s has no items; skipping", name)
        return None

    existing = _find_playlist(client, name)
    mode = (mode or "replace").lower()

    if existing and mode == "replace":
        LOGGER.info("Deleting existing playlist: %s", name)
        client.delete_playlist(existing.rating_key)
        existing = None

    rating_keys = [item.rating_key for item in items]
    chunks = chunked(rating_keys, chunk_size)

    playlist = existing
    if not playlist:
        LOGGER.info("Creating playlist %s with %s items", name, len(items))
        playlist = client.create_playlist(name, chunks[0])
    else:
        LOGGER.info("Appending to existing playlist %s", name)

    for chunk in chunks[1:]:
        client.add_playlist_items(playlist.rating_key, chunk)

    return playlist


def _find_playlist(client: PlexClient, name: str) -> PlaylistInfo | None:
    playlists = client.get_playlists(title=name)
    lowered = name.strip().lower()
    for playlist in playlists:
        if playlist.title.strip().lower() == lowered:
            return playlist
    return None
