from unittest import TestCase

from ..services.index_strategy import expected_strategy, validate_strategy


class TestIndexStrategy(TestCase):
    def test_default_strategy_matches_operator_set(self):
        self.assertEqual(expected_strategy("exact"), "btree")
        self.assertEqual(expected_strategy("prefix"), "pattern_ops")
        self.assertEqual(expected_strategy("contains"), "gin_trgm")

    def test_none_is_allowed_for_optional_index(self):
        self.assertTrue(validate_strategy("contains", "none"))

    def test_compatible_non_default_strategies_match_configuration_model(self):
        self.assertTrue(validate_strategy("prefix", "btree"))
        self.assertTrue(validate_strategy("contains", "gist_trgm"))

    def test_incompatible_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_strategy("prefix", "gin_trgm")
        with self.assertRaises(ValueError):
            validate_strategy("exact", "gist_trgm")
