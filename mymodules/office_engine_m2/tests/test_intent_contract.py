"""Server-owned idempotency and confirmation receipt fingerprints."""

import unittest

from odoo.addons.office_engine_m2.services.intent_contract import confirmation_receipt_id, digest_json


class TestServerReceiptFingerprints(unittest.TestCase):
    def test_server_digest_is_stable_for_equivalent_json(self):
        self.assertEqual(digest_json({"a": 1, "b": [2]}), digest_json({"b": [2], "a": 1}))

    def test_confirmation_receipt_binds_user_thread_source_and_revision(self):
        binding = {
            "thread_id": 7,
            "session_id": 3,
            "owner_id": 2,
            "intent_message_id": 9,
            "intent_digest": digest_json({"message_id": 9, "body": "edit this file"}),
            "parent_version_id": 4,
            "input_sha256": "a" * 64,
        }
        common = {
            "owner_id": 2,
            "session_revision": 1,
            "proposal_revision": 0,
            "document_revision": 5,
        }
        pending = confirmation_receipt_id(binding, **common)
        confirmed = confirmation_receipt_id(
            binding, **common, decision_message_id=10, confirmed_by_user_id=2,
        )
        stale_revision = confirmation_receipt_id(
            binding, **{**common, "document_revision": 6},
        )
        other_user = confirmation_receipt_id(
            binding, **common, decision_message_id=10, confirmed_by_user_id=3,
        )
        self.assertNotEqual(pending, confirmed)
        self.assertNotEqual(confirmed, stale_revision)
        self.assertNotEqual(confirmed, other_user)


if __name__ == "__main__":
    unittest.main()
