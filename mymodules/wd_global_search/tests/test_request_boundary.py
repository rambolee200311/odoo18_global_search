from unittest import TestCase

from ..services.request_boundary import (
    RequestBoundaryError,
    validate_search_request,
)
from ..services.types import SearchRequest


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
                    {"nested": [{"nested": [{"nested": [{"value": "x"}]}]}]},
                ))
            )

    def test_relation_path_is_limited_to_two_segments(self):
        validate_search_request(
            SearchRequest(parsed_conditions=(
                {"relation_path": "partner_id.country_id"},
            ))
        )
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(
                SearchRequest(parsed_conditions=(
                    {"relation_path": "partner_id.country_id.name"},
                ))
            )

    def test_control_characters_are_rejected(self):
        with self.assertRaises(RequestBoundaryError):
            validate_search_request(SearchRequest(raw_query="safe\nunsafe"))
