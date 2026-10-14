from unittest import TestCase

from ..services.request_boundary import (
    RequestBoundaryError,
    validate_condition_query_object,
    validate_search_request,
)
from ..services.types import ConditionQueryObject, KeywordTerm, SearchRequest


class TestRequestBoundary(TestCase):
    def test_raw_query_has_a_500_character_limit(self):
        validate_search_request(SearchRequest(raw_query="x" * 500))
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(SearchRequest(raw_query="x" * 501))

    def test_conditions_are_capped_and_nested(self):
        conditions = tuple({"dimension": "name", "value": str(index)} for index in range(20))
        validate_search_request(SearchRequest(parsed_conditions=conditions))
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(SearchRequest(parsed_conditions=conditions + (conditions[0],)))
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(parsed_conditions=(
                    {
                        "dimension": "name",
                        "value": "x",
                        "nested": [{"nested": [{"nested": [{"value": "x"}]}]}],
                    },
                ))
            )

    def test_relation_path_is_limited_to_two_segments(self):
        validate_search_request(
            SearchRequest(parsed_conditions=(
                {
                    "dimension": "partner_id.name",
                    "value": "US",
                    "relation_path": "partner_id.country_id",
                },
            ))
        )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(parsed_conditions=(
                    {
                        "dimension": "partner_id.name",
                        "value": "US",
                        "relation_path": "partner_id.country_id.name",
                    },
                ))
            )

    def test_condition_query_object_rejects_invalid_shape(self):
        nested = {
            "dimension": "name",
            "value": "x",
            "nested": [{"nested": [{"nested": [{"value": "x"}]}]}],
        }
        invalid_objects = (
            None,
            ConditionQueryObject(combinator="OR"),
            ConditionQueryObject(field_conditions=({"dimension": "name"},)),
            ConditionQueryObject(field_conditions=(nested,)),
            ConditionQueryObject(keyword_terms=(KeywordTerm(["A"]),)),
        )
        for query_object in invalid_objects:
            with self.subTest(query_object=query_object):
                with self.assertRaises(RequestBoundaryError):
                    validate_condition_query_object(query_object)

        valid = ConditionQueryObject(
            keyword_terms=(KeywordTerm("A"),),
            field_conditions=(
                {"dimension": "partner_id.name", "operator": "=", "value": "Acme"},
            ),
        )
        self.assertIs(validate_condition_query_object(valid), valid)

    def test_conditions_require_dimension_and_value(self):
        for condition in (
            {"dimension": "name"},
            {"value": "Acme"},
            {"dimension": "", "value": "Acme"},
            {"dimension": "name", "value": None},
            {"dimension": "name", "value": ["Acme"]},
            {"dimension": "name", "value": float("nan")},
            {"dimension": "name", "value": float("inf")},
            {"dimension": "name", "operator": "", "value": "Acme"},
        ):
            with self.subTest(condition=condition):
                with self.assertRaises(RequestBoundaryError):
                    validate_search_request(
                        SearchRequest(parsed_conditions=(condition,))
                    )

    def test_condition_dimension_and_operator_have_bounded_types(self):
        validate_search_request(
            SearchRequest(
                refinement_conditions=(
                    {"dimension": "partner_id.city", "operator": "ilike", "value": "X"},
                )
            )
        )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(refinement_conditions=({"dimension": ["path"]},))
            )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(
                    refinement_conditions=(
                        {"dimension": "x" * 101, "value": "value"},
                    )
                )
            )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(
                    refinement_conditions=(
                        {"dimension": "name", "operator": ["="], "value": "X"},
                    )
                )
            )

    def test_custom_date_range_refinement_accepts_exclusive_iso_bounds(self):
        validate_search_request(
            SearchRequest(
                refinement_conditions=(
                    {
                        "dimension": "date",
                        "operator": "between",
                        "value": {"start": "2026-06-01", "end": "2026-07-01"},
                    },
                )
            )
        )

    def test_custom_date_range_refinement_rejects_incomplete_or_invalid_bounds(self):
        invalid_conditions = (
            {
                "dimension": "date",
                "operator": "between",
                "value": {"start": "2026-06-01"},
            },
            {
                "dimension": "date",
                "operator": "between",
                "value": {"end": "2026-07-01"},
            },
            {
                "dimension": "date",
                "operator": "between",
                "value": {
                    "start": "2026-06-01",
                    "end": "2026-07-01",
                    "timezone": "UTC",
                },
            },
            {
                "dimension": "date",
                "operator": "between",
                "value": {"start": "2026-02-30", "end": "2026-03-01"},
            },
            {
                "dimension": "date",
                "operator": "between",
                "value": {"start": "2026-06-01", "end": "2026-06-01"},
            },
            {
                "dimension": "date",
                "operator": "between",
                "value": {"start": "2026-07-01", "end": "2026-06-01"},
            },
            {
                "dimension": "name",
                "operator": "between",
                "value": {"start": "2026-06-01", "end": "2026-07-01"},
            },
            {
                "dimension": "date",
                "operator": "=",
                "value": {"start": "2026-06-01", "end": "2026-07-01"},
            },
            {
                "dimension": "date",
                "operator": "between",
                "value": "2026-06-01",
            },
        )
        for condition in invalid_conditions:
            with self.subTest(condition=condition):
                with self.assertRaises(RequestBoundaryError):
                    validate_search_request(
                        SearchRequest(refinement_conditions=(condition,))
                    )

    def test_conditions_reject_client_execution_fields(self):
        for key, value in (
            ("model", "res.users"),
            ("action", "ir.actions.act_window"),
            ("domain", [("id", "!=", 0)]),
            ("relation_expression", "partner_id.user_id"),
        ):
            with self.subTest(key=key):
                with self.assertRaises(RequestBoundaryError):
                    validate_search_request(
                        SearchRequest(
                            parsed_conditions=(
                                {
                                    "dimension": "name",
                                    "operator": "=",
                                    "value": "S00001",
                                    key: value,
                                },
                            )
                        )
                    )

    def test_control_characters_are_rejected(self):
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(SearchRequest(raw_query="safe\nunsafe"))

    def test_multitoken_query_builds_and_bounded_keyword_terms(self):
        query = validate_search_request(
            SearchRequest(raw_query="  Acme+Tools North  ")
        )

        self.assertEqual(query.combinator, "AND")
        self.assertEqual(
            [term.value for term in query.keyword_terms],
            ["Acme", "Tools", "North"],
        )
        self.assertEqual(query.field_conditions, ())

        validate_search_request(
            SearchRequest(raw_query=" ".join("T%s" % index for index in range(10)))
        )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(raw_query=" ".join("T%s" % index for index in range(11)))
            )

    def test_single_token_query_keeps_legacy_name_behavior(self):
        query = validate_search_request(SearchRequest(raw_query="  OR  "))

        self.assertEqual(query.keyword_terms, ())
        self.assertEqual(
            query.field_conditions,
            ({"dimension": "name", "operator": "ilike", "value": "OR"},),
        )

    def test_plus_separator_spacing_produces_same_keyword_terms(self):
        compact = validate_search_request(SearchRequest(raw_query="Acme+Tools"))
        spaced = validate_search_request(SearchRequest(raw_query="Acme + Tools"))

        self.assertEqual(compact.keyword_terms, spaced.keyword_terms)

    def test_multitoken_syntax_and_token_lengths_fail_closed(self):
        for query in (
            "A++B",
            "+A",
            "A+",
            "A OR B",
            "A NOT B",
            "A (B)",
            '"A B"',
            "A " + ("x" * 101),
        ):
            with self.subTest(query=query):
                with self.assertRaises(RequestBoundaryError):
                    validate_search_request(SearchRequest(raw_query=query))

        validate_search_request(SearchRequest(raw_query=("x" * 100) + " B"))

    def test_unicode_multitoken_policy_preserves_text_and_rejects_controls(self):
        query = validate_search_request(
            SearchRequest(raw_query="客户 Cafe\u0301")
        )
        self.assertEqual(
            [term.value for term in query.keyword_terms],
            ["客户", "Cafe\u0301"],
        )

        for character in (
            "\u0085",
            "\u202e",
            "\u200b",
            "\u200c",
            "\u200d",
            "\u2060",
            "\ufeff",
            chr(0xD800),
        ):
            with self.subTest(codepoint=ord(character)):
                with self.assertRaises(RequestBoundaryError):
                    validate_search_request(SearchRequest(raw_query="A " + character + "B"))

    def test_query_terms_share_the_existing_condition_limit(self):
        conditions = tuple(
            {"dimension": "field_%s" % index, "value": str(index)}
            for index in range(10)
        )
        validate_search_request(
            SearchRequest(
                raw_query=" ".join("T%s" % index for index in range(10)),
                parsed_conditions=conditions,
            )
        )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(
                    raw_query=" ".join("T%s" % index for index in range(10)),
                    parsed_conditions=conditions + (conditions[0],),
                )
            )
