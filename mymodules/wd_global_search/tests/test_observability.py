from unittest import TestCase
from unittest.mock import patch

from ..services.observability import (
    HASH_VERSION,
    canonical_hash,
    event_fields,
    hash_value,
    log_event,
)


class TestObservability(TestCase):
    def test_hash_is_stable_and_secret_bound(self):
        self.assertEqual(hash_value("secret", "query"), hash_value("secret", "query"))
        self.assertNotEqual(hash_value("secret", "query"), hash_value("other", "query"))
        self.assertEqual(
            canonical_hash("secret", {"b": 2, "a": 1}),
            canonical_hash("secret", {"a": 1, "b": 2}),
        )

    def test_missing_secret_does_not_fallback_to_plaintext(self):
        with self.assertRaises(ValueError):
            hash_value("", "query")

    def test_event_fields_apply_allowlist(self):
        payload = event_fields(
            "gs.search.completed",
            {"request_id": "r1", "raw_query": "secret", "status": "SUCCESS"},
        )
        self.assertEqual(payload["hash_version"], HASH_VERSION)
        self.assertNotIn("raw_query", payload)

    @patch("mymodules.wd_global_search.services.observability._logger")
    def test_log_event_uses_structured_json_payload(self, logger):
        payload = log_event("info", "gs.search.completed", {"request_id": "r1"})
        logger.info.assert_called_once()
        self.assertEqual(payload["event"], "gs.search.completed")
