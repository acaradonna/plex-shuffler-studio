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
        self.facet_values = {"genre": ["Drama", "Comedy", "Drama"]}
        self.error_facets: set[str] = set()
        self.section_calls = 0
        self.facet_calls = 0

    def get_section_by_title(self, title: str) -> LibrarySection:
        self.section_calls += 1
        if title != self.section_title:
            raise PlexError(f"Library section not found: {title}")
        return LibrarySection(key=self.section_key, title=title, type=self.section_type)

    def get_section_facet_values(self, section_key: str, facet: str, media_type: str | None = None) -> list[str]:
        self.facet_calls += 1
        if facet in self.error_facets:
            raise PlexError("Simulated Plex failure")
        if section_key != self.section_key:
            raise PlexError(f"Library section not found: {section_key}")
        return self.facet_values.get(facet, [])


class FacetsApiTests(unittest.TestCase):
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

    def test_facets_by_section_title_returns_sorted_unique_values(self) -> None:
        status, payload = self._fetch_json("/api/facets?section_title=TV%20Shows&facet=genre")
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("values"), ["Comedy", "Drama"])
        self.assertFalse(payload.get("error"))
        self.assertEqual(self.fake_client.section_calls, 1)

    def test_facets_limit_slices_values_after_normalization(self) -> None:
        status, payload = self._fetch_json("/api/facets?section_title=TV%20Shows&facet=genre&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("values"), ["Comedy"])
        self.assertFalse(payload.get("error"))

    def test_facets_caches_per_section_and_facet(self) -> None:
        self._fetch_json("/api/libraries/1/facets/genre")
        self._fetch_json("/api/libraries/1/facets/genre")
        self.assertEqual(self.fake_client.facet_calls, 1)

    def test_facets_limit_does_not_change_cache_key(self) -> None:
        self._fetch_json("/api/libraries/1/facets/genre?limit=1")
        self._fetch_json("/api/libraries/1/facets/genre")
        self.assertEqual(self.fake_client.facet_calls, 1)

    def test_facets_unsupported_facet_returns_error(self) -> None:
        status, payload = self._fetch_json("/api/libraries/1/facets/notreal")
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("values"), [])
        self.assertIn("Unsupported facet", payload.get("error", ""))
        self.assertEqual(self.fake_client.facet_calls, 0)

    def test_facets_returns_error_on_plex_failure(self) -> None:
        self.fake_client.error_facets.add("genre")
        status, payload = self._fetch_json("/api/libraries/1/facets/genre")
        self.assertEqual(status, 200)
        self.assertEqual(payload.get("values"), [])
        self.assertIn("Simulated Plex failure", payload.get("error", ""))
        self.assertEqual(self.fake_client.facet_calls, 1)


if __name__ == "__main__":
    unittest.main()
