import time
from unittest import TestCase

from ..services.aggregator import merge
from ..services.conditions import merge as merge_conditions
from ..services.cursor import decode, encode
from ..services.limiter import UserLimiter
from ..services.types import ResourceOutcome, SearchRequest


class TestSearchServiceCore(TestCase):
    def test_conditions_merge_uses_distinct_dimensions_and_drops_invalid_values(self):
        conditions = merge_conditions(
            [{"dimension": "name", "value": "Acme"}],
            [
                {"dimension": "name", "value": "Acme"},
                {"dimension": "state", "value": ""},
                {"dimension": "state", "value": "sale"},
            ],
        )

        self.assertEqual(
            list(conditions.values),
            [
                {"dimension": "name", "value": "Acme", "operator": "contains"},
                {"dimension": "state", "value": "sale", "operator": "contains"},
            ],
        )

    def test_aggregator_deduplicates_after_stable_sort(self):
        outcomes = [
            ResourceOutcome(
                resource="sales",
                status="SUCCESS",
                results=[
                    {"_resource": "sales", "_model": "sale.order", "id": 2},
                    {"_resource": "sales", "_model": "sale.order", "id": 1},
                ],
                count=2,
            ),
            ResourceOutcome(
                resource="sales",
                status="SUCCESS",
                results=[{"_resource": "sales", "_model": "sale.order", "id": 1}],
                count=1,
            ),
        ]

        response = merge(outcomes, "request-1", 0, 10, 7)

        self.assertEqual(response.results[0]["id"], 1)
        self.assertEqual(response.counts["all"], 3)

    def test_cursor_rejects_other_user_and_expired_values(self):
        secret = b"test-secret"
        cursor = encode(
            {
                "config_version": 7,
                "conditions_hash": "conditions",
                "user_context_hash": "user-1",
                "sort_version": "v1",
            },
            secret,
        )

        decoded = decode(
            cursor,
            secret,
            {
                "config_version": 7,
                "conditions_hash": "conditions",
                "user_context_hash": "user-1",
                "sort_version": "v1",
            },
        )
        self.assertEqual(decoded["config_version"], 7)

        with self.assertRaises(ValueError):
            decode(cursor, secret, {"user_context_hash": "user-2"})

        expired = encode({"expires_at": int(time.time()) - 1}, secret)
        with self.assertRaises(TimeoutError):
            decode(expired, secret, {})

    def test_limiter_releases_user_capacity(self):
        limiter = UserLimiter(max_concurrency=1)

        self.assertTrue(limiter.acquire(2))
        self.assertFalse(limiter.acquire(2))
        limiter.release(2)
        self.assertTrue(limiter.acquire(2))
