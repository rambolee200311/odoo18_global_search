import time
from unittest import TestCase
from unittest.mock import patch

from ..services.aggregator import merge
from ..services.conditions import merge as merge_conditions
from ..services.cursor import decode, encode
from ..services import executor
from ..services import facade
from ..services.limiter import UserLimiter
from ..services.permission_boundary import AuthorizationError
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

    def test_aggregator_count_is_independent_of_page_length(self):
        outcomes = [
            ResourceOutcome(
                resource="sales",
                status="SUCCESS",
                results=[
                    {"_resource": "sales", "_model": "sale.order", "id": index}
                    for index in range(1, 11)
                ],
                count=37,
            )
        ]

        response = merge(outcomes, "request-2", 0, 10, 7)

        self.assertEqual(len(response.results), 10)
        self.assertEqual(response.counts["all"], 37)

    def test_aggregator_separates_selected_result_counts_from_facets(self):
        outcomes = [
            ResourceOutcome(
                resource="contact",
                status="SUCCESS",
                results=[{"_resource": "contact", "_model": "res.partner", "id": 1}],
                count=1,
            ),
            ResourceOutcome(
                resource="sale_order",
                status="SUCCESS",
                count=3,
            ),
        ]

        response = merge(
            outcomes, "request-facets", 0, 10, 7, count_scope={"contact"}
        )

        self.assertEqual(response.counts, {"all": 1, "by_resource": {"contact": 1}})
        self.assertEqual(
            response.meta["resource_counts"],
            {"contact": 1, "sale_order": 3},
        )

    def test_empty_result_scope_can_return_facets_without_results(self):
        outcomes = [
            ResourceOutcome(
                resource="sale_order",
                status="SUCCESS",
                count=3,
            )
        ]

        response = merge(outcomes, "request-empty-scope", 0, 10, 7, count_scope=set())

        self.assertEqual(response.status, "EMPTY")
        self.assertEqual(response.results, [])
        self.assertEqual(response.counts, {"all": 0, "by_resource": {}})
        self.assertEqual(response.meta["resource_counts"], {"sale_order": 3})

    def test_facet_failure_remains_partial_for_empty_result_scope(self):
        outcomes = [
            ResourceOutcome(resource="contact", status="SUCCESS", count=1),
            ResourceOutcome(
                resource="sale_order",
                status="FAILED",
                error={"code": "TIMEOUT", "resource": "sale_order"},
            ),
        ]

        response = merge(outcomes, "request-facet-timeout", 0, 10, 7, count_scope=set())

        self.assertEqual(response.status, "PARTIAL_SUCCESS")
        self.assertEqual(response.results, [])
        self.assertEqual(response.counts, {"all": 0, "by_resource": {}})
        self.assertEqual(response.meta["resource_counts"], {"contact": 1})
        self.assertEqual(response.meta["failed_resources"], ["sale_order"])

    def test_authorized_candidate_filter_omits_inaccessible_resources(self):
        def authorize(env, resource, context):
            if resource["key"] == "private":
                raise AuthorizationError("RESOURCE_NOT_ACCESSIBLE")

        with patch.object(facade, "authorize_search_resource", side_effect=authorize):
            resources = facade._authorized_resources(
                {},
                [{"key": "private"}, {"key": "sale_order"}, {"key": "contact"}],
                None,
            )

        self.assertEqual(
            [resource["key"] for resource in resources],
            ["contact", "sale_order"],
        )

    def test_executor_returns_exact_total_and_requested_model_offset(self):
        class FakeRecordset:
            def __init__(self, rows):
                self.rows = rows

            def read(self, fields):
                return [dict(row) for row in self.rows]

        class FakeModel:
            def __init__(self, rows):
                self.rows = rows
                self.search_calls = []

            def search_count(self, domain):
                return len(self.rows)

            def search(self, domain, offset=0, limit=None, order=None):
                self.search_calls.append((offset, limit, order))
                return FakeRecordset(self.rows[offset : offset + limit])

        class FakeEnv:
            def __init__(self, models):
                self.models = models

            def __getitem__(self, model_name):
                return self.models[model_name]

        first_rows = [{"id": index} for index in range(1, 13)]
        second_rows = [{"id": index} for index in range(1, 131)]
        first_model = FakeModel(first_rows)
        second_model = FakeModel(second_rows)
        env = FakeEnv({"a.model": first_model, "z.model": second_model})
        resource = {
            "key": "sales",
            "models": [
                {"model_name": "z.model", "fields": []},
                {"model_name": "a.model", "fields": []},
            ],
        }

        with (
            patch.object(executor, "authorize_resource"),
            patch.object(executor, "authorize_fields", side_effect=lambda model, fields, context: fields),
            patch.object(executor, "authorize_relation_path"),
            patch.object(executor, "_condition_domain", return_value=[]),
        ):
            outcome = executor.execute(env, resource, {}, 100, offset=10)

        self.assertEqual(outcome.count, 142)
        self.assertEqual(len(outcome.results), 100)
        self.assertEqual(
            [(item["_model"], item["id"]) for item in outcome.results],
            [("a.model", 11), ("a.model", 12)]
            + [("z.model", index) for index in range(1, 99)],
        )
        self.assertEqual(first_model.search_calls, [(10, 100, "id asc")])
        self.assertEqual(second_model.search_calls, [(0, 98, "id asc")])

    def test_relation_search_fields_include_product_codes_and_serial_numbers(self):
        class RelationField:
            def __init__(self, comodel_name):
                self.comodel_name = comodel_name

        class FakeModel:
            def __init__(self, fields, env):
                self._fields = fields
                self.env = env

            def check_field_access_rights(self, operation, field_names):
                return field_names

        class FakeEnv:
            def __init__(self):
                self.models = {
                    "stock.picking": FakeModel(
                        {
                            "move_ids": RelationField("stock.move"),
                            "move_line_ids": RelationField("stock.move.line"),
                        },
                        self,
                    ),
                    "stock.move": FakeModel(
                        {"product_id": RelationField("product.product")}, self
                    ),
                    "stock.move.line": FakeModel(
                        {"lot_id": RelationField("stock.lot")}, self
                    ),
                    "product.product": FakeModel(
                        {
                            field: object()
                            for field in (
                                "name",
                                "display_name",
                                "default_code",
                                "barcode",
                            )
                        },
                        self,
                    ),
                    "stock.lot": FakeModel(
                        {"name": object(), "display_name": object()}, self
                    ),
                }

            def __getitem__(self, model_name):
                return self.models[model_name]

        env = FakeEnv()
        self.assertEqual(
            executor._relation_search_fields(
                env["stock.picking"], "move_ids.product_id"
            ),
            [
                "move_ids.product_id.name",
                "move_ids.product_id.display_name",
                "move_ids.product_id.default_code",
                "move_ids.product_id.barcode",
            ],
        )
        self.assertEqual(
            executor._relation_search_fields(
                env["stock.picking"], "move_line_ids.lot_id"
            ),
            ["move_line_ids.lot_id.name", "move_line_ids.lot_id.display_name"],
        )

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
