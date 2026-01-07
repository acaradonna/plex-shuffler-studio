"""Minimal web server for Plex Shuffler Studio UI and API."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from plex_shuffler import __version__
from plex_shuffler.builder import build_playlist_items
from plex_shuffler.config import (
    apply_plex_overrides,
    default_config,
    load_config,
    load_config_raw,
    save_config,
)
from plex_shuffler.plex_auth import PlexAuthError, check_pin, create_pin, fetch_resources, fetch_user
from plex_shuffler.plex_client import PlexClient, PlexError
from plex_shuffler.playlist import sync_playlist
from plex_shuffler.query_builder import (
    DEFAULT_KNOWN_FIELDS,
    parse_query_string,
    query_state_from_dict,
    query_state_to_dict,
    serialize_query_state,
)
from plex_shuffler.query_catalog import catalog_for_api, plex_option_sources
from plex_shuffler.utils import now_utc

LOGGER = logging.getLogger(__name__)


class WebApp:
    def __init__(self, config_path: str, web_root: str) -> None:
        self.config_path = Path(config_path)
        self.web_root = Path(web_root)
        self._lock = threading.Lock()

    def load_config_raw(self) -> dict[str, Any]:
        return load_config_raw(str(self.config_path))

    def save_config_raw(self, config: dict[str, Any]) -> None:
        save_config(str(self.config_path), config)

    def ensure_client_id(self, config: dict[str, Any]) -> str:
        plex_cfg = config.setdefault("plex", {})
        client_id = (plex_cfg.get("client_id") or "").strip()
        if not client_id:
            client_id = uuid.uuid4().hex
            plex_cfg["client_id"] = client_id
            self.save_config_raw(config)
        return client_id

    def get_config_for_api(self) -> dict[str, Any]:
        config = self.load_config_raw()
        config_view = json.loads(json.dumps(config))
        plex_cfg = config_view.setdefault("plex", {})
        if plex_cfg.get("token"):
            plex_cfg["token"] = ""
        _attach_query_state(config_view)
        return config_view


class PlexShufflerHandler(BaseHTTPRequestHandler):
    server_version = "PlexShufflerWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api_get(parsed)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api_post(parsed.path)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_api_get(self, parsed) -> None:
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/config":
            app = self._app
            config = app.get_config_for_api()
            raw = app.load_config_raw()
            token_set = bool(raw.get("plex", {}).get("token"))
            meta = {"token_set": token_set, "query_fields": catalog_for_api()}
            self._send_json({"config": config, "meta": meta})
            return

        if path == "/api/plex/account":
            app = self._app
            with app._lock:
                config = app.load_config_raw()
                plex_cfg = config.get("plex", {})
                token = plex_cfg.get("token")
                client_id = app.ensure_client_id(config)
            if not token:
                self._send_json({"error": "Plex token not set"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                account = fetch_user(
                    token=token,
                    client_id=client_id,
                    product="Plex Shuffler Studio",
                    platform="Web",
                    device="Browser",
                    device_name="Plex Shuffler Studio",
                    version=__version__,
                )
            except PlexAuthError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            self._send_json({"account": account})
            return

        if path == "/api/plex/resources":
            app = self._app
            with app._lock:
                config = app.load_config_raw()
                plex_cfg = config.get("plex", {})
                token = plex_cfg.get("token")
                client_id = app.ensure_client_id(config)
            if not token:
                self._send_json({"error": "Plex token not set"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                resources = fetch_resources(
                    token=token,
                    client_id=client_id,
                    product="Plex Shuffler Studio",
                    platform="Web",
                    device="Browser",
                    device_name="Plex Shuffler Studio",
                    version=__version__,
                )
            except PlexAuthError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            servers = _extract_servers(resources)
            self._send_json({"servers": servers})
            return

        if path == "/api/plex/options":
            library = (query.get("library", [""])[0] or "").strip()
            source = (query.get("source", [""])[0] or "").strip()
            media_type = (query.get("media_type", [""])[0] or "").strip()
            if not library or not source:
                self._send_json({"error": "library and source are required"}, status=HTTPStatus.BAD_REQUEST)
                return
            if source not in plex_option_sources():
                self._send_json({"error": "Unsupported options source"}, status=HTTPStatus.BAD_REQUEST)
                return
            try:
                config = load_config(str(self._app.config_path))
            except (OSError, ValueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            plex_cfg = config.get("plex", {})
            if not plex_cfg.get("token"):
                self._send_json({"error": "Plex token not set"}, status=HTTPStatus.BAD_REQUEST)
                return
            client = PlexClient(
                base_url=plex_cfg.get("url", ""),
                token=plex_cfg.get("token", ""),
                timeout=int(plex_cfg.get("timeout_seconds", 30) or 30),
            )
            try:
                section = client.get_section_by_title(library)
                options = client.get_filter_options(
                    section_key=section.key,
                    source=source,
                    media_type=media_type or section.type,
                )
            except PlexError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            self._send_json({"options": options})
            return

        if path.startswith("/api/plex/pin/"):
            pin_id_raw = path.rsplit("/", 1)[-1]
            try:
                pin_id = int(pin_id_raw)
            except ValueError:
                self._send_json({"error": "Invalid pin id"}, status=HTTPStatus.BAD_REQUEST)
                return
            app = self._app
            with app._lock:
                config = app.load_config_raw()
                client_id = app.ensure_client_id(config)
            try:
                pin = check_pin(
                    pin_id=pin_id,
                    client_id=client_id,
                    product="Plex Shuffler Studio",
                    platform="Web",
                    device="Browser",
                    device_name="Plex Shuffler Studio",
                    version=__version__,
                )
            except PlexAuthError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return

            token_saved = False
            if pin.auth_token:
                with app._lock:
                    config = app.load_config_raw()
                    config.setdefault("plex", {})["token"] = pin.auth_token
                    app.save_config_raw(config)
                    token_saved = True
            self._send_json({"pin_id": pin_id, "authorized": bool(pin.auth_token), "token_saved": token_saved})
            return

        if path == "/api/libraries":
            try:
                config = load_config(str(self._app.config_path))
            except (OSError, ValueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            plex_cfg = config.get("plex", {})
            if not plex_cfg.get("token"):
                self._send_json({"error": "Plex token not set"}, status=HTTPStatus.BAD_REQUEST)
                return
            client = PlexClient(
                base_url=plex_cfg.get("url", ""),
                token=plex_cfg.get("token", ""),
                timeout=int(plex_cfg.get("timeout_seconds", 30) or 30),
            )
            try:
                sections = client.get_sections()
            except PlexError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            payload = [
                {"key": section.key, "title": section.title, "type": section.type}
                for section in sections
            ]
            self._send_json({"libraries": payload})
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_api_post(self, path: str) -> None:
        if path == "/api/config":
            payload = self._read_json() or {}
            incoming = payload.get("config", payload)
            if not isinstance(incoming, dict):
                self._send_json({"error": "Invalid config payload"}, status=HTTPStatus.BAD_REQUEST)
                return
            app = self._app
            with app._lock:
                current = app.load_config_raw()
                incoming.setdefault("plex", {})
                if not incoming["plex"].get("token"):
                    incoming["plex"]["token"] = current.get("plex", {}).get("token", "")
                if not incoming["plex"].get("client_id"):
                    incoming["plex"]["client_id"] = current.get("plex", {}).get("client_id", "")
                if not incoming.get("playlists"):
                    incoming["playlists"] = default_config()["playlists"]
                _apply_query_state(incoming)
                app.save_config_raw(incoming)
            self._send_json({"status": "saved"})
            return

        if path == "/api/plex/pin":
            payload = self._read_json() or {}
            plex_url = payload.get("plex_url") if isinstance(payload, dict) else None
            app = self._app
            with app._lock:
                config = app.load_config_raw()
                apply_plex_overrides(config, plex_url)
                client_id = app.ensure_client_id(config)
                app.save_config_raw(config)
            host = self.headers.get("Host", "localhost")
            forward_url = f"http://{host}/"
            try:
                pin = create_pin(
                    client_id=client_id,
                    product="Plex Shuffler Studio",
                    platform="Web",
                    device="Browser",
                    device_name="Plex Shuffler Studio",
                    version=__version__,
                    forward_url=forward_url,
                )
            except PlexAuthError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            self._send_json(
                {
                    "pin_id": pin.pin_id,
                    "code": pin.code,
                    "expires_at": pin.expires_at,
                    "auth_url": pin.auth_url,
                }
            )
            return

        if path == "/api/preview":
            payload = self._read_json() or {}
            playlist_index = int(payload.get("playlist_index", 0) or 0)
            limit = int(payload.get("limit", 30) or 30)
            limit = max(1, min(200, limit))

            try:
                config = load_config(str(self._app.config_path))
            except (OSError, ValueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            playlists = config.get("playlists", [])
            if not playlists or playlist_index >= len(playlists):
                self._send_json({"error": "Playlist not found"}, status=HTTPStatus.BAD_REQUEST)
                return

            plex_cfg = config.get("plex", {})
            if not plex_cfg.get("token"):
                self._send_json({"error": "Plex token not set"}, status=HTTPStatus.BAD_REQUEST)
                return
            client = PlexClient(
                base_url=plex_cfg.get("url", ""),
                token=plex_cfg.get("token", ""),
                timeout=int(plex_cfg.get("timeout_seconds", 30) or 30),
            )
            try:
                items, stats = build_playlist_items(client, playlists[playlist_index], now_utc())
            except PlexError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return

            preview = [
                {
                    "type": item.type,
                    "title": item.title,
                    "show_title": item.show_title,
                    "season": item.season_index,
                    "episode": item.episode_index,
                }
                for item in items[:limit]
            ]
            self._send_json({"items": preview, "stats": stats.__dict__})
            return

        if path == "/api/run":
            payload = self._read_json() or {}
            playlist_index = int(payload.get("playlist_index", 0) or 0)

            try:
                config = load_config(str(self._app.config_path))
            except (OSError, ValueError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            playlists = config.get("playlists", [])
            if not playlists or playlist_index >= len(playlists):
                self._send_json({"error": "Playlist not found"}, status=HTTPStatus.BAD_REQUEST)
                return

            plex_cfg = config.get("plex", {})
            if not plex_cfg.get("token"):
                self._send_json({"error": "Plex token not set"}, status=HTTPStatus.BAD_REQUEST)
                return
            client = PlexClient(
                base_url=plex_cfg.get("url", ""),
                token=plex_cfg.get("token", ""),
                timeout=int(plex_cfg.get("timeout_seconds", 30) or 30),
            )
            playlist_cfg = playlists[playlist_index]
            name = playlist_cfg.get("name", "")
            output_cfg = playlist_cfg.get("output", {})
            try:
                items, stats = build_playlist_items(client, playlist_cfg, now_utc())
                playlist = sync_playlist(
                    client,
                    name=name,
                    items=items,
                    mode=output_cfg.get("mode", "replace"),
                    chunk_size=int(output_cfg.get("chunk_size", 200) or 200),
                )
            except PlexError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return

            self._send_json(
                {
                    "status": "ok",
                    "playlist": playlist.title if playlist else None,
                    "stats": stats.__dict__,
                }
            )
            return

        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _serve_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        web_root = self._app.web_root
        target = (web_root / path.lstrip("/")).resolve()
        if web_root.resolve() not in target.parents and target != web_root.resolve():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        if not target.exists() or not target.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = _guess_type(target.suffix)
        try:
            data = target.read_bytes()
        except OSError:
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return None
        data = self.rfile.read(length)
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        LOGGER.info("%s - %s", self.address_string(), format % args)

    @property
    def _app(self) -> WebApp:
        return self.server.app  # type: ignore[attr-defined]


class PlexShufflerWebServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[PlexShufflerHandler], app: WebApp):
        super().__init__(server_address, handler_class)
        self.app = app


def _guess_type(suffix: str) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".ico": "image/x-icon",
    }.get(suffix.lower(), "application/octet-stream")


def _extract_servers(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    servers: list[dict[str, Any]] = []
    for resource in resources:
        provides = resource.get("provides") or ""
        if "server" not in provides:
            continue
        connections = resource.get("connections") or []
        servers.append(
            {
                "name": resource.get("name", ""),
                "clientIdentifier": resource.get("clientIdentifier", ""),
                "owned": resource.get("owned", False),
                "connections": connections,
                "preferredUri": _pick_preferred_connection(connections),
            }
        )
    return servers


def _pick_preferred_connection(connections: list[dict[str, Any]]) -> str:
    if not connections:
        return ""

    def score(conn: dict[str, Any]) -> tuple[int, str]:
        protocol = (conn.get("protocol") or "").lower()
        is_https = protocol == "https"
        relay = bool(conn.get("relay"))
        local = bool(conn.get("local"))
        base = 0
        if is_https:
            base += 4
        if not relay:
            base += 2
        if not local:
            base += 1
        return (base, conn.get("uri", ""))

    best = max(connections, key=score)
    return best.get("uri", "")


def _attach_query_state(config: dict[str, Any]) -> None:
    playlists = config.get("playlists", [])
    if not isinstance(playlists, list):
        return
    for playlist in playlists:
        if not isinstance(playlist, dict):
            continue
        _attach_query_state_to_section(playlist.get("tv", {}))
        _attach_query_state_to_section(playlist.get("movies", {}))


def _attach_query_state_to_section(section: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        return
    query = section.get("query", "")
    raw_state = section.get("query_state")
    if isinstance(raw_state, dict):
        state = query_state_from_dict(raw_state)
        if serialize_query_state(state) == (query or "").strip():
            section["query_state"] = query_state_to_dict(state)
            return
    state = parse_query_string(query, known_fields=DEFAULT_KNOWN_FIELDS, strict=True)
    section["query_state"] = query_state_to_dict(state)


def _apply_query_state(config: dict[str, Any]) -> None:
    playlists = config.get("playlists", [])
    if not isinstance(playlists, list):
        return
    for playlist in playlists:
        if not isinstance(playlist, dict):
            continue
        _apply_query_state_to_section(playlist.get("tv", {}))
        _apply_query_state_to_section(playlist.get("movies", {}))


def _apply_query_state_to_section(section: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        return
    current_query = (section.get("query", "") or "").strip()
    raw_state = section.get("query_state")
    if isinstance(raw_state, dict):
        state = query_state_from_dict(raw_state)
        state_query = serialize_query_state(state)
        if state_query != current_query:
            state = parse_query_string(current_query, known_fields=DEFAULT_KNOWN_FIELDS, strict=True)
            section["query"] = current_query
            section["query_state"] = query_state_to_dict(state)
            return
        section["query"] = state_query
        section["query_state"] = query_state_to_dict(state)
        return
    section["query"] = current_query
    state = parse_query_string(current_query, known_fields=DEFAULT_KNOWN_FIELDS, strict=True)
    section["query_state"] = query_state_to_dict(state)


def run_web_server(config_path: str, host: str, port: int) -> None:
    web_root = Path(__file__).resolve().parent / "web"
    app = WebApp(config_path=config_path, web_root=str(web_root))
    server = PlexShufflerWebServer((host, port), PlexShufflerHandler, app)
    LOGGER.info("Plex Shuffler Studio web UI running on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down web server")
    finally:
        server.server_close()
