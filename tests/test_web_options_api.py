import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from plex_shuffler.models import LibrarySection
from plex_shuffler.plex_client import PlexError
from plex_shuffler.web_server import PlexShufflerHandler, PlexShufflerWebServer, WebApp


class FakePlexClient:
    def __init__(self) -> None:
        self.section_key = "1"
        self.section_title = "TV Shows"
        self.section_type = "show"
        self.options = ["Drama", "Comedy", "Sci-Fi"]
        self.error_sources: set[str] = set()
        self.section_calls = 0
        self.options_calls = 0
        self.last_media_type: str | None = None

    def get_section_by_title(self, title: str) -> LibrarySection:
        self.section_calls += 1
        if title != self.section_title:
            raise PlexError(f"Library section not found: {title}")
        return LibrarySection(key=self.section_key, title=title, type=self.section_type)

    def get_filter_options(self, section_key: str, source: str, media_type: str | None = None) -> list[str]:
        self.options_calls += 1
        self.last_media_type = media_type
        if source in self.error_sources:
            raise PlexError("Simulated Plex failure")
        if section_key != self.section_key:
            raise PlexError(f"Library section not found: {section_key}")
        return list(self.options)


class OptionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config_path = Path(self.temp_dir.name) / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "plex": {"url": "http://example.com", "token": "token", "timeout_seconds": 30},
                    "playlists": [],
                }
            ),
            encoding="utf-8",
        )
        self.fake_client = FakePlexClient()
        app = WebApp(
            config_path=str(config_path),
            web_root=self.temp_dir.name,
            plex_client_factory=lambda _cfg: self.fake_client,
        )
        self.server = PlexShufflerWebServer(("127.0.0.1", 0), PlexShufflerHandler, app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.temp_dir.cleanup()

    def _fetch_json(self, path: str) -> tuple[int, dict[str, object]]:
        with urlopen(f"{self.base_url}{path}") as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
        return status, payload

    def test_options_returns_values(self) -> None:
        status, payload = self._fetch_json(
            "/api/plex/options?library=TV%20Shows&source=genre&media_type=both"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("options"), ["Drama", "Comedy", "Sci-Fi"])
        self.assertEqual(self.fake_client.section_calls, 1)
        self.assertEqual(self.fake_client.options_calls, 1)
        self.assertEqual(self.fake_client.last_media_type, "both")

    def test_options_limit_slices_values(self) -> None:
        status, payload = self._fetch_json(
            "/api/plex/options?library=TV%20Shows&source=genre&media_type=both&limit=2"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("options"), ["Drama", "Comedy"])


if __name__ == "__main__":
    unittest.main()
