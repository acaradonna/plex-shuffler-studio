import unittest

from plex_shuffler.query_catalog import catalog_for_api, known_field_keys, plex_option_sources


class QueryCatalogTests(unittest.TestCase):
    def test_catalog_filters_unverified_fields(self):
        keys = {field["key"] for field in catalog_for_api()}
        self.assertIn("genre", keys)
        self.assertIn("unwatched", keys)
        self.assertIn("title", keys)

    def test_known_field_keys_matches_verified(self):
        known = known_field_keys()
        self.assertIn("collection", known)
        self.assertIn("contentRating", known)
        self.assertIn("title", known)
        self.assertNotIn("summary", known)

    def test_option_sources_include_verified_fields(self):
        sources = plex_option_sources()
        self.assertIn("genre", sources)
        self.assertIn("collection", sources)
        self.assertIn("studio", sources)


if __name__ == "__main__":
    unittest.main()
