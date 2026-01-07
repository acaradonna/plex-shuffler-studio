import unittest

from plex_shuffler.query_builder import (
    Clause,
    Group,
    QueryState,
    parse_query_string,
    serialize_query_state,
)


class QueryBuilderTests(unittest.TestCase):
    def test_parse_empty_query_returns_builder(self):
        state = parse_query_string("")
        self.assertEqual(state.mode, "builder")
        self.assertEqual(state.groups, [])
        self.assertEqual(state.advanced_query, "")

    def test_parse_repeated_keys_to_values(self):
        state = parse_query_string("genre=Animation&genre=Comedy")
        self.assertEqual(state.mode, "builder")
        self.assertEqual(len(state.groups), 1)
        clause = state.groups[0].clauses[0]
        self.assertEqual(clause.field, "genre")
        self.assertEqual(clause.op, "eq")
        self.assertEqual(clause.values, ["Animation", "Comedy"])

    def test_serialize_builder_repeats_keys(self):
        state = QueryState(
            mode="builder",
            groups=[Group(clauses=[Clause(field="genre", op="eq", values=["Animation", "Comedy"])])],
            advanced_query="",
        )
        self.assertEqual(serialize_query_state(state), "genre=Animation&genre=Comedy")

    def test_serialize_advanced_trims_whitespace(self):
        state = QueryState(mode="advanced", groups=[], advanced_query="  genre=Animation  ")
        self.assertEqual(serialize_query_state(state), "genre=Animation")

    def test_parse_trims_keys_and_values(self):
        state = parse_query_string("  genre=Animation  &  year=2020  ")
        clause_genre = state.groups[0].clauses[0]
        clause_year = state.groups[0].clauses[1]
        self.assertEqual(clause_genre.field, "genre")
        self.assertEqual(clause_genre.values, ["Animation"])
        self.assertEqual(clause_year.field, "year")
        self.assertEqual(clause_year.values, ["2020"])

    def test_parse_interleaved_duplicates_uses_first_seen_order(self):
        state = parse_query_string("genre=Animation&year=2020&genre=Comedy")
        self.assertEqual(serialize_query_state(state), "genre=Animation&genre=Comedy&year=2020")

    def test_parse_strict_unknown_field_forces_advanced(self):
        state = parse_query_string("unknown=1", known_fields={"genre"}, strict=True)
        self.assertEqual(state.mode, "advanced")
        self.assertEqual(state.advanced_query, "unknown=1")


if __name__ == "__main__":
    unittest.main()
