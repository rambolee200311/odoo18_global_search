import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from odoo.osv.expression import AND, OR

from ..services.aggregator import merge
from ..services.conditions import merge as merge_conditions
from ..services.cursor import decode, encode
from ..services import executor
from ..services import facade
from ..services.limiter import UserLimiter
from ..services.permission_boundary import AuthorizationError
from ..services.types import KeywordTerm, ResourceOutcome, SearchRequest


class TestSearchServiceCore(TestCase):
    def test_state_refinement_maps_business_state_to_technical_values(self):
        from .test_field_path import FakeField, field_path_models

        env = field_path_models()
        env["sale.order"]._fields["state"] = FakeField("selection")
        domain = executor._condition_domain(
            env["sale.order"],
            [],
            [],
            {
                "states": [
                    {
                        "business_state": "Quotation",
                        "technical_values": "draft, sent",
                    }
                ]
            },
            SimpleNamespace(
                values=(
                    {
                        "dimension": "state",
                        "value": "Quotation",
                        "operator": "=",
                    },
                ),
                keyword_terms=(),
            ),
            None,
        )

        self.assertEqual(domain, [("state", "in", ["draft", "sent"])])

    def test_resource_descriptor_exposes_only_readable_business_states(self):
        resource = {
            "key": "sales",
            "label": "Sales",
            "models": [{"model_name": "sale.order"}],
            "states": [
                {
                    "business_state": "Quotation",
                    "technical_values": "draft,sent",
                }
            ],
        }
        context = SimpleNamespace(lang="en_US")
        with patch.object(facade, "authorize_fields", return_value=["state"]):
            descriptor = facade._resource_descriptor(
                {"sale.order": object()}, resource, context
            )
        self.assertEqual(descriptor["states"], ["Quotation"])
        self.assertNotIn("technical_values", descriptor)

        with patch.object(
            facade,
            "authorize_fields",
            side_effect=AuthorizationError("FIELD_NOT_READABLE"),
        ):
            self.assertEqual(
                facade._resource_business_states(
                    {"sale.order": object()}, resource, context
                ),
                [],
            )

    def test_many2one_path_compiles_to_nested_authorized_any_domain(self):
        from .test_field_path import field_path_models

        env = field_path_models()
        condition = {"dimension": "partner_id.country_id.name", "value": "US"}
        domain = executor._condition_domain(
            env["sale.order"],
            [
                {
                    "name": condition["dimension"],
                    "operator_set": "exact",
                    "index_strategy": "btree",
                    "collection_match": "any",
                }
            ],
            [],
            {},
            SimpleNamespace(values=(condition,)),
            None,
        )
        self.assertEqual(
            domain,
            [
                (
                    "partner_id",
                    "any",
                    [
                        (
                            "country_id",
                            "any",
                            [("name", "=", "US")],
                        )
                    ],
                )
            ],
        )

    def test_effective_conditions_accepts_only_states_common_to_selected_resources(self):
        resources = [
            {"key": "sales", "models": [], "business_dates": []},
            {"key": "purchases", "models": [], "business_dates": []},
        ]
        conditions = SimpleNamespace(
            values=(
                {
                    "dimension": "state",
                    "value": "Confirmed",
                    "operator": "=",
                },
            )
        )
        with patch.object(
            facade,
            "_resource_business_states",
            side_effect=[
                ["Draft", "Confirmed"],
                ["Confirmed", "Done"],
            ],
        ):
            visible = facade._effective_conditions(
                {},
                resources,
                {"sales", "purchases"},
                conditions,
                None,
            )
        self.assertEqual(visible, list(conditions.values))

        conditions = SimpleNamespace(
            values=(
                {
                    "dimension": "state",
                    "value": "Draft",
                    "operator": "=",
                },
            )
        )
        with patch.object(
            facade,
            "_resource_business_states",
            side_effect=[
                ["Draft", "Confirmed"],
                ["Confirmed", "Done"],
            ],
        ):
            with self.assertRaises(facade.RequestBoundaryError):
                facade._effective_conditions(
                    {},
                    resources,
                    {"sales", "purchases"},
                    conditions,
                    None,
                )

    def test_keyword_terms_are_and_of_authorized_text_field_contains_ors(self):
        from .test_field_path import FakeField, field_path_models

        env = field_path_models()
        env["sale.order"]._fields["name"] = FakeField("char")
        field_configs = [
            {
                "name": "name",
                "operator_set": "exact",
                "index_strategy": "btree",
                "collection_match": "any",
            },
            {
                "name": "partner_id.city",
                "operator_set": "exact",
                "index_strategy": "btree",
                "collection_match": "any",
            },
            {
                "name": "partner_id.country_id.name",
                "operator_set": "exact",
                "index_strategy": "btree",
                "collection_match": "any",
            },
            {
                "name": "category_ids.name",
                "operator_set": "exact",
                "index_strategy": "btree",
                "collection_match": "any",
            },
            {
                "name": "order_line.product_id.name",
                "operator_set": "contains",
                "index_strategy": "gin_trgm",
                "collection_match": "any",
            },
        ]
        terms = (KeywordTerm("001"), KeywordTerm("chair"))
        domain = executor._condition_domain(
            env["sale.order"],
            field_configs,
            [],
            {},
            SimpleNamespace(
                values=(
                    {
                        "dimension": "partner_id.city",
                        "value": "Berkeley",
                        "operator": "=",
                    },
                ),
                keyword_terms=terms,
            ),
            None,
        )

        def term_domain(value):
            predicate = ("ilike", "%%%s%%" % value)
            return OR(
                [
                    [("name",) + predicate],
                    [("partner_id", "any", [("city",) + predicate])],
                    [
                        (
                            "partner_id",
                            "any",
                            [
                                (
                                    "country_id",
                                    "any",
                                    [("name",) + predicate],
                                )
                            ],
                        )
                    ],
                    [("category_ids", "any", [("name",) + predicate])],
                    [
                        (
                            "order_line",
                            "any",
                            [
                                (
                                    "product_id",
                                    "any",
                                    [("name",) + predicate],
                                )
                            ],
                        )
                    ],
                ]
            )

        self.assertEqual(
            domain,
            AND(
                [
                    [("partner_id", "any", [("city", "=", "Berkeley")])],
                    term_domain("001"),
                    term_domain("chair"),
                ]
            ),
        )

    def test_keyword_query_has_a_false_domain_when_no_field_can_match_token_type(self):
        from .test_field_path import FakeField, field_path_models

        env = field_path_models()
        env["sale.order"]._fields["amount"] = FakeField("integer")
        domain = executor._keyword_term_domain(
            env["sale.order"],
            [
                {
                    "name": "amount",
                    "operator_set": "exact",
                    "index_strategy": "btree",
                    "collection_match": "any",
                }
            ],
            KeywordTerm("Fremont"),
        )

        self.assertEqual(domain, [("id", "=", 0)])

    def test_keyword_query_converts_tokens_for_exact_typed_fields(self):
        from datetime import date, datetime

        from .test_field_path import FakeField, field_path_models

        cases = (
            ("integer", "42", 42),
            ("float", "3.5", 3.5),
            ("date", "2026-10-13", date(2026, 10, 13)),
            (
                "datetime",
                "2026-10-13T14:15:00",
                datetime(2026, 10, 13, 14, 15),
            ),
            ("boolean", "false", False),
        )
        env = field_path_models()
        model = env["sale.order"]
        for field_type, raw_value, expected in cases:
            with self.subTest(field_type=field_type):
                field_name = "typed_value"
                model._fields[field_name] = FakeField(field_type)
                domain = executor._keyword_term_domain(
                    model,
                    [
                        {
                            "name": field_name,
                            "operator_set": "exact",
                            "index_strategy": "btree",
                            "collection_match": "any",
                        }
                    ],
                    KeywordTerm(raw_value),
                )
                self.assertEqual(domain, [(field_name, "=", expected)])

    def test_keyword_query_uses_contains_for_all_searchable_text_fields(self):
        from .test_field_path import field_path_models

        env = field_path_models()
        domain = executor._keyword_term_domain(
            env["sale.order"],
            [
                {
                    "name": "partner_id.city",
                    "operator_set": "prefix",
                    "index_strategy": "pattern_ops",
                    "collection_match": "any",
                }
            ],
            KeywordTerm("Fremont"),
        )

        self.assertEqual(
            domain,
            [("partner_id", "any", [("city", "ilike", "%Fremont%")])],
        )

    def test_keyword_query_rejects_resources_without_searchable_fields(self):
        from .test_field_path import field_path_models

        env = field_path_models()
        with self.assertRaises(executor.FieldPathError):
            executor._keyword_term_domain(
                env["sale.order"],
                [],
                KeywordTerm("Fremont"),
            )

    def test_keyword_contains_treats_like_wildcards_as_literal_text(self):
        from .test_field_path import field_path_models

        env = field_path_models()
        domain = executor._keyword_term_domain(
            env["sale.order"],
            [
                {
                    "name": "partner_id.city",
                    "operator_set": "contains",
                    "index_strategy": "gin_trgm",
                    "collection_match": "any",
                }
            ],
            KeywordTerm(r"50%_off\sale"),
        )

        self.assertEqual(
            domain,
            [
                (
                    "partner_id",
                    "any",
                    [("city", "ilike", r"%50\%\_off\\sale%")],
                )
            ],
        )

    def test_collection_all_compiles_one_authorized_predicate_per_value(self):
        from .test_field_path import field_path_models

        env = field_path_models()
        dimension = "category_ids.name"
        domain = executor._condition_domain(
            env["sale.order"],
            [
                {
                    "name": dimension,
                    "operator_set": "contains",
                    "index_strategy": "gin_trgm",
                    "collection_match": "all",
                }
            ],
            [],
            {},
            SimpleNamespace(
                values=(
                    {"dimension": dimension, "value": "Retail"},
                    {"dimension": dimension, "value": "VIP"},
                )
            ),
            None,
        )

        terms = []

        def collect(value):
            if isinstance(value, (list, tuple)):
                if (
                    len(value) == 3
                    and isinstance(value[0], str)
                    and isinstance(value[1], str)
                    and value[1] in {"any", "=", "ilike"}
                ):
                    terms.append(tuple(value))
                    if value[1] == "any":
                        collect(value[2])
                else:
                    for item in value:
                        collect(item)

        collect(domain)
        collection_terms = [item for item in terms if item[1] == "any"]
        terminal_terms = [item for item in terms if item[1] == "ilike"]
        self.assertEqual(len(collection_terms), 2)
        self.assertEqual(
            {item[2] for item in terminal_terms},
            {"%Retail%", "%VIP%"},
        )

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
                {"dimension": "state", "value": "sale", "operator": "="},
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

    def test_aggregator_preserves_request_timeout_status(self):
        response = merge(
            [
                ResourceOutcome(
                    resource="sale_order",
                    status="FAILED",
                    error={
                        "scope": "resource",
                        "resource": "sale_order",
                        "code": "TIMEOUT",
                        "message": "Search timed out",
                        "retryable": True,
                    },
                )
            ],
            "request-timeout",
            0,
            10,
            7,
        )

        self.assertEqual(response.status, "TIMEOUT")

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

    def test_effective_conditions_only_exposes_authorized_published_paths(self):
        field_config = {
            "name": "partner_id.city",
            "operator_set": "contains",
            "index_strategy": "gin_trgm",
            "collection_match": "any",
        }
        resource = {
            "key": "sales",
            "models": [
                {"model_name": "sale.order", "fields": [field_config]},
            ],
            "business_dates": [],
        }
        conditions = SimpleNamespace(
            values=(
                {
                    "dimension": "partner_id.city",
                    "value": "Fremont",
                    "operator": "=",
                },
            )
        )
        with patch.object(
            facade, "authorize_searchable_fields", return_value=[field_config]
        ):
            visible = facade._effective_conditions(
                {"sale.order": object()},
                [resource],
                {"sales"},
                conditions,
                None,
            )

        self.assertEqual([item["dimension"] for item in visible], ["partner_id.city"])

        with patch.object(facade, "authorize_searchable_fields", return_value=[]):
            with self.assertRaises(facade.RequestBoundaryError):
                facade._effective_conditions(
                    {"sale.order": object()},
                    [resource],
                    {"sales"},
                    conditions,
                    None,
                )

    def test_effective_conditions_rejects_unpublished_direct_dimensions(self):
        resource = {"key": "sales", "models": [], "business_dates": []}
        conditions = SimpleNamespace(
            values=(
                {
                    "dimension": "not_published_dimension",
                    "value": "S00001",
                    "operator": "=",
                },
            )
        )

        with self.assertRaises(facade.RequestBoundaryError):
            facade._effective_conditions(
                {},
                [resource],
                {"sales"},
                conditions,
                None,
            )

    def test_query_understanding_exposes_keyword_values_not_search_paths(self):
        field_config = {
            "name": "partner_id.city",
            "operator_set": "contains",
            "index_strategy": "gin_trgm",
            "collection_match": "any",
        }
        resource = {
            "key": "sales",
            "models": [{"model_name": "sale.order", "fields": [field_config]}],
            "business_dates": [],
        }
        conditions = merge_conditions(
            (),
            (),
            keyword_terms=(KeywordTerm("Fremont"), KeywordTerm("ACME")),
        )
        with patch.object(
            facade, "authorize_searchable_fields", return_value=[field_config]
        ):
            visible = facade._effective_conditions(
                {"sale.order": object()},
                [resource],
                {"sales"},
                conditions,
                None,
            )

        self.assertEqual(
            visible,
            [
                {"dimension": "keyword", "operator": "contains", "value": "Fremont"},
                {"dimension": "keyword", "operator": "contains", "value": "ACME"},
            ],
        )

    def test_multitoken_query_identity_and_failure_summary(self):
        legacy = merge_conditions((), ())
        first = merge_conditions(
            (), (), keyword_terms=(KeywordTerm("Fremont"), KeywordTerm("ACME"))
        )
        second = merge_conditions(
            (), (), keyword_terms=(KeywordTerm("Oakland"), KeywordTerm("ACME"))
        )

        self.assertEqual(
            facade._condition_identity(legacy, {"sales"}),
            {"conditions": [], "resources": ["sales"]},
        )
        self.assertEqual(
            facade._condition_identity(first, {"sales"})["keyword_match_mode"],
            "contains_text",
        )
        self.assertNotEqual(
            facade._condition_identity(first, {"sales"}),
            facade._condition_identity(second, {"sales"}),
        )
        self.assertEqual(
            facade._response_conditions(
                first,
                [{"dimension": "keyword", "value": "Fremont"}],
                [ResourceOutcome(resource="sales", status="FAILED")],
                {"sales"},
            ),
            [],
        )
        self.assertEqual(
            facade._response_conditions(
                first,
                [{"dimension": "keyword", "value": "Fremont"}],
                [ResourceOutcome(resource="sales", status="SUCCESS")],
                {"sales"},
            ),
            [{"dimension": "keyword", "value": "Fremont"}],
        )

    def test_performance_config_defaults_and_rejects_unsafe_expansion(self):
        resources = [{"key": "sales"}]
        defaults = facade._performance_config({"resources": resources}, resources)

        self.assertEqual(defaults["sales"]["max_relation_depth"], 2)
        self.assertEqual(defaults["sales"]["resource_timeout"], 3.0)
        with self.assertRaises(facade.ConfigurationError):
            facade._performance_config(
                {
                    "resources": resources,
                    "performance": [
                        {
                            "resource_key": "sales",
                            "max_results": 500,
                            "resource_timeout": 3.0,
                            "request_timeout": 5.0,
                            "max_relation_depth": 3,
                        }
                    ],
                },
                resources,
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
            patch.object(executor, "authorize_searchable_fields", return_value=[]),
            patch.object(executor, "authorize_relation_path"),
            patch.object(executor, "_condition_domain", return_value=[]),
        ):
            outcome = executor.execute(
                env, resource, SimpleNamespace(values=()), 100, offset=10
            )

        self.assertEqual(outcome.count, 142)
        self.assertEqual(len(outcome.results), 100)
        self.assertEqual(
            [(item["_model"], item["id"]) for item in outcome.results],
            [("a.model", 11), ("a.model", 12)]
            + [("z.model", index) for index in range(1, 99)],
        )
        self.assertEqual(first_model.search_calls, [(10, 100, "id asc")])
        self.assertEqual(second_model.search_calls, [(0, 98, "id asc")])

    def test_executor_uses_normalized_conditions_without_parser(self):
        from ..services import request_boundary

        class FakeRecordset:
            def read(self, fields):
                return [{"id": 1, "name": "S00001"}]

        class FakeModel:
            def search_count(self, domain):
                return 1

            def search(self, domain, offset=0, limit=None, order=None):
                return FakeRecordset()

        class FakeEnv:
            def __getitem__(self, model_name):
                self.assert_model = model_name
                return FakeModel()

        env = FakeEnv()
        resource = {
            "key": "sales",
            "models": [{"model_name": "sale.order", "fields": []}],
        }
        normalized_conditions = SimpleNamespace(values=())

        with (
            patch.object(
                request_boundary,
                "parse_multi_query",
                side_effect=AssertionError("executor must not invoke the parser"),
            ),
            patch.object(executor, "authorize_search_resource"),
            patch.object(executor, "authorize_searchable_fields", return_value=[]),
            patch.object(executor, "authorize_fields", side_effect=lambda model, fields, context: fields),
            patch.object(executor, "authorize_relation_path"),
            patch.object(executor, "_condition_domain", return_value=[]),
        ):
            outcome = executor.execute(env, resource, normalized_conditions, 10)

        self.assertEqual(env.assert_model, "sale.order")
        self.assertEqual(outcome.status, "SUCCESS")
        self.assertEqual(outcome.count, 1)
        self.assertEqual(
            [(item["_model"], item["id"]) for item in outcome.results],
            [("sale.order", 1)],
        )

    def test_executor_returns_timeout_without_partial_success_shape(self):
        outcome = executor.execute(
            {},
            {"key": "sales", "models": []},
            SimpleNamespace(values=()),
            0,
            deadline=time.monotonic() - 1,
        )

        self.assertEqual(outcome.status, "FAILED")
        self.assertEqual(outcome.error["code"], "TIMEOUT")
        self.assertEqual(outcome.results, [])

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
                env["stock.picking"], "move_ids.product_id", None
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
                env["stock.picking"], "move_line_ids.lot_id", None
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
