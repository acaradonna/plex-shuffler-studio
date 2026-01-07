import unittest

from plex_shuffler.config import apply_plex_overrides


class ApplyPlexOverridesTests(unittest.TestCase):
    def test_updates_url_when_provided(self):
        config = {"plex": {"url": "http://localhost:32400"}}
        apply_plex_overrides(config, "https://example.com/")
        self.assertEqual(config["plex"]["url"], "https://example.com/")

    def test_ignores_blank_url(self):
        config = {"plex": {"url": "http://localhost:32400"}}
        apply_plex_overrides(config, " ")
        self.assertEqual(config["plex"]["url"], "http://localhost:32400")

    def test_creates_plex_section_when_missing(self):
        config = {}
        apply_plex_overrides(config, "https://plex.local")
        self.assertEqual(config["plex"]["url"], "https://plex.local")


if __name__ == "__main__":
    unittest.main()
