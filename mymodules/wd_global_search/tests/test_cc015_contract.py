from unittest.mock import patch
from uuid import uuid4

from odoo import api
from odoo.tests.common import TransactionCase

from ..services import executor, facade, permission_boundary, request_boundary
from ..services.conditions import merge as merge_conditions
from ..services.provider import published_snapshot
from ..services.request_boundary import RequestBoundaryError
from ..services.types import (
    ConditionQueryObject,
    KeywordTerm,
    ResourceOutcome,
    SearchRequest,
)


class TestCC015SearchContracts(TransactionCase):
    def _publish_domain(self, resources):
        suffix = uuid4().hex
        key = "cc015_%s" % suffix
        domain = self.env["wd.gs.config.domain"].create({"key": key, "name": key})
        version = self.env["wd.gs.config.version"].create(
            {"domain_id": domain.id, "version": 1}
        )
        model = self.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        for resource_key, field_names in resources:
            resource = self.env["wd.gs.business.resource"].create(
                {
                    "version_id": version.id,
                    "key": resource_key,
                    "name": resource_key,
                    "primary_model_id": model.id,
                    "navigation_action_id": self.env.ref(
                        "wd_global_search.action_gs_native_form_partner"
                    ).id,
                    "card_template": "Name: {name}",
                }
            )
            for field_name in field_names:
                self.env["wd.gs.searchable.field"].create(
                    {
                        "resource_id": resource.id,
                        "field_name": field_name,
                        "purpose": "identifier" if field_name == "name" else "text",
                        "operator_set": "contains",
                        "index_strategy": "gin_trgm",
                    }
                )
            self.env["wd.gs.snapshot.field"].create(
                {
                    "resource_id": resource.id,
                    "field_name": "name",
                    "label": "Name",
                    "sequence": 10,
                    "visible": True,
                    "format_type": "text",
                }
            )
            self.env["wd.gs.business.date.mapping"].create(
                {
                    "resource_id": resource.id,
                    "model_name": "res.partner",
                    "field_name": "create_date",
                }
            )
        self.assertTrue(version.action_publish(), version.rejection_message)
        snapshot = published_snapshot(self.env, key)["snapshot"]
        return key, {item["key"]: item for item in snapshot["resources"]}

    def _publish_restricted_partner_domain(self):
        key = "cc015_restricted_%s" % uuid4().hex
        domain = self.env["wd.gs.config.domain"].create({"key": key, "name": key})
        version = self.env["wd.gs.config.version"].create(
            {"domain_id": domain.id, "version": 1}
        )
        resource = self.env["wd.gs.business.resource"].create(
            {
                "version_id": version.id,
                "key": "partner",
                "name": "Partner",
                "primary_model_id": self.env["ir.model"].search(
                    [("model", "=", "res.partner")], limit=1
                ).id,
                "navigation_action_id": self.env.ref(
                    "wd_global_search.action_gs_native_form_partner"
                ).id,
                "card_template": "Name: {name}",
            }
        )
        self.env["wd.gs.searchable.field"].create(
            [
                {
                    "resource_id": resource.id,
                    "field_name": "name",
                    "purpose": "identifier",
                    "operator_set": "contains",
                    "index_strategy": "gin_trgm",
                },
                {
                    "resource_id": resource.id,
                    "field_name": "signup_type",
                    "purpose": "text",
                    "operator_set": "contains",
                    "index_strategy": "gin_trgm",
                },
            ]
        )
        self.env["wd.gs.snapshot.field"].create(
            {
                "resource_id": resource.id,
                "field_name": "name",
                "label": "Name",
                "sequence": 10,
                "visible": True,
                "format_type": "text",
            }
        )
        self.env["wd.gs.business.date.mapping"].create(
            {
                "resource_id": resource.id,
                "model_name": "res.partner",
                "field_name": "create_date",
            }
        )
        self.assertTrue(version.action_publish(), version.rejection_message)
        snapshot = published_snapshot(self.env, key)["snapshot"]
        return key, snapshot["resources"][0]

    def _search(self, domain_key, resource_keys, **request_values):
        request = SearchRequest(resource_scope=tuple(resource_keys), **request_values)
        return facade.SearchService().search(self.env, request, domain_key)

    def _ids(self, response):
        return {result["_record_id"] for result in response.results}

    def _create_user(self, name, company, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": name,
                "login": "%s_%s" % (name, uuid4().hex),
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "groups_id": [(6, 0, [self.env.ref(group_xmlid).id])],
            }
        )

    def _user_env(self, user, company):
        return api.Environment(
            self.env.cr,
            user.id,
            {"allowed_company_ids": [company.id]},
        )

    def test_005_raw_and_structured_contains_have_identical_results(self):
        query_a = "cc15a_%s" % uuid4().hex
        query_b = "cc15b_%s" % uuid4().hex
        match = self.env["res.partner"].create(
            {"name": "Fixture %s %s" % (query_a, query_b)}
        )
        self.env["res.partner"].create({"name": "Fixture %s only" % query_a})
        domain_key, resources = self._publish_domain([("partner", ("name",))])

        raw = self._search(
            domain_key, ("partner",), raw_query="%s %s" % (query_a, query_b)
        )
        structured = self._search(
            domain_key,
            ("partner",),
            parsed_conditions=(
                {
                    "dimension": "name",
                    "operator": "contains",
                    "value": "%s %s" % (query_a, query_b),
                },
            ),
        )

        self.assertEqual(raw.status, "SUCCESS")
        self.assertEqual(structured.status, "SUCCESS")
        self.assertEqual(raw.counts["all"], structured.counts["all"])
        self.assertEqual(self._ids(raw), self._ids(structured))
        self.assertEqual(self._ids(raw), {match.id})
        self.assertIn("partner", resources)

    def test_007_raw_and_structured_adapters_share_authorized_fields(self):
        token_a = "cc15a_%s" % uuid4().hex
        token_b = "cc15b_%s" % uuid4().hex
        self.env["res.partner"].create(
            {
                "name": "Fixture %s %s" % (token_a, token_b),
                "email": "%s@example.test" % token_a,
            }
        )
        domain_key, _ = self._publish_domain(
            [("partner", ("name", "email"))]
        )
        authorized_fields = []
        authorize = permission_boundary.authorize_searchable_fields

        def capture_authorized_fields(
            env, model, fields, context, max_relation_depth=None
        ):
            result = authorize(
                env,
                model,
                fields,
                context,
                max_relation_depth=max_relation_depth,
            )
            authorized_fields.append(tuple(sorted(item["name"] for item in result)))
            return result

        with patch.object(
            facade,
            "authorize_searchable_fields",
            side_effect=capture_authorized_fields,
        ):
            raw = self._search(
                domain_key,
                ("partner",),
                raw_query="%s %s" % (token_a, token_b),
            )
            structured = self._search(
                domain_key,
                ("partner",),
                parsed_conditions=(
                    {
                        "dimension": "name",
                        "operator": "contains",
                        "value": "%s %s" % (token_a, token_b),
                    },
                ),
            )

        self.assertEqual(raw.status, "SUCCESS")
        self.assertEqual(structured.status, "SUCCESS")
        self.assertEqual(len(authorized_fields), 4)
        self.assertEqual(authorized_fields[0], ("email", "name"))
        self.assertEqual(authorized_fields[0], authorized_fields[1])
        self.assertEqual(authorized_fields[0], authorized_fields[2])
        self.assertEqual(authorized_fields[0], authorized_fields[3])

    def test_008_executor_does_not_reparse_validated_keyword_terms(self):
        token_a = "cc15a_%s" % uuid4().hex
        token_b = "cc15b_%s" % uuid4().hex
        match = self.env["res.partner"].create(
            {"name": "Fixture %s %s" % (token_a, token_b)}
        )
        domain_key, resources = self._publish_domain([("partner", ("name",))])
        query_object = request_boundary.validate_search_request(
            SearchRequest(raw_query="%s %s" % (token_a, token_b))
        )
        conditions = merge_conditions(
            query_object.field_conditions,
            (),
            keyword_terms=query_object.keyword_terms,
        )

        with patch.object(
            request_boundary,
            "parse_multi_query",
            side_effect=AssertionError("executor must not parse raw text"),
        ):
            outcome = executor.execute(
                self.env, resources["partner"], conditions, 20
            )

        self.assertEqual(outcome.status, "SUCCESS")
        self.assertEqual(outcome.count, 1)
        self.assertEqual(
            {result["_record_id"] for result in outcome.results}, {match.id}
        )
        self.assertTrue(domain_key)

    def test_009_all_keyword_terms_must_match_the_same_record(self):
        token_a = "cc15a_%s" % uuid4().hex
        token_b = "cc15b_%s" % uuid4().hex
        match = self.env["res.partner"].create(
            {"name": "Fixture %s" % token_a, "email": "%s@example.test" % token_b}
        )
        self.env["res.partner"].create(
            {"name": "Fixture %s" % token_a, "email": "unrelated@example.test"}
        )
        self.env["res.partner"].create(
            {"name": "Unrelated fixture", "email": "%s@example.test" % token_b}
        )
        domain_key, _ = self._publish_domain(
            [("partner", ("name", "email"))]
        )

        response = self._search(
            domain_key, ("partner",), raw_query="%s %s" % (token_a, token_b)
        )

        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.counts["all"], 1)
        self.assertEqual(self._ids(response), {match.id})

    def test_011_query_conditions_combine_with_keyword_search(self):
        token_a = "cc15a_%s" % uuid4().hex
        token_b = "cc15b_%s" % uuid4().hex
        marker = "cc15marker_%s" % uuid4().hex
        exact_name = "%s %s %s" % (token_a, token_b, marker)
        match = self.env["res.partner"].create(
            {"name": exact_name}
        )
        domain_key, _ = self._publish_domain([("partner", ("name",))])

        response = self._search(
            domain_key,
            ("partner",),
            raw_query="%s %s" % (token_a, token_b),
            parsed_conditions=(
                {"dimension": "name", "operator": "=", "value": exact_name},
            ),
        )

        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(self._ids(response), {match.id})
        visible = response.meta["effective_conditions"]
        self.assertCountEqual(
            visible,
            [
                {
                    "dimension": "keyword",
                    "operator": "contains",
                    "value": token_a,
                },
                {
                    "dimension": "keyword",
                    "operator": "contains",
                    "value": token_b,
                },
                {"dimension": "name", "operator": "=", "value": exact_name},
            ],
        )

    def test_022_user_company_scope_and_cursor_are_isolated(self):
        company_a = self.env["res.company"].create(
            {"name": "CC-015 A %s" % uuid4().hex}
        )
        company_b = self.env["res.company"].create(
            {"name": "CC-015 B %s" % uuid4().hex}
        )
        user_a = self._create_user(
            "CC-015 user A", company_a, "base.group_user"
        )
        user_b = self._create_user(
            "CC-015 user B", company_b, "base.group_user"
        )
        marker = "cc15scope_%s" % uuid4().hex
        records_a = self.env["res.partner"].create(
            [
                {"name": "%s A1" % marker, "company_id": company_a.id},
                {"name": "%s A2" % marker, "company_id": company_a.id},
            ]
        )
        record_b = self.env["res.partner"].create(
            {"name": "%s B1" % marker, "company_id": company_b.id}
        )
        domain_key, _ = self._publish_domain([("partner", ("name",))])
        request = {
            "resource_scope": ("partner",),
            "parsed_conditions": (
                {"dimension": "name", "operator": "contains", "value": marker},
            ),
            "limit": 1,
        }

        response_a = facade.SearchService().search(
            self._user_env(user_a, company_a),
            SearchRequest(**request),
            domain_key,
        )
        response_b = facade.SearchService().search(
            self._user_env(user_b, company_b),
            SearchRequest(**request),
            domain_key,
        )

        self.assertEqual(response_a.counts["all"], 2)
        self.assertEqual(response_b.counts["all"], 1)
        self.assertTrue(self._ids(response_a).issubset(set(records_a.ids)))
        self.assertEqual(self._ids(response_b), {record_b.id})
        cursor = response_a.meta.get("next_cursor")
        self.assertTrue(cursor)
        cross_user_page = facade.SearchService().search(
            self._user_env(user_b, company_b),
            SearchRequest(**{**request, "cursor": cursor}),
            domain_key,
        )
        self.assertEqual(cross_user_page.errors[0]["code"], "CURSOR_INVALID")

    def test_029_portal_results_obey_partner_record_rules(self):
        company = self.env.company
        portal_user = self._create_user(
            "CC-015 portal", company, "base.group_portal"
        )
        marker = "cc15portal_%s" % uuid4().hex
        portal_partner = portal_user.partner_id
        portal_partner.name = marker
        unrelated_partner = self.env["res.partner"].create({"name": marker})
        outside_company = self.env["res.company"].create(
            {"name": "CC-015 portal outside %s" % uuid4().hex}
        )
        outside_company_partner = self.env["res.partner"].create(
            {"name": marker, "company_id": outside_company.id}
        )
        domain_key, _ = self._publish_domain([("partner", ("name",))])

        response = facade.SearchService().search(
            self._user_env(portal_user, company),
            SearchRequest(
                resource_scope=("partner",),
                parsed_conditions=(
                    {"dimension": "name", "operator": "contains", "value": marker},
                ),
            ),
            domain_key,
        )

        self.assertEqual(response.status, "SUCCESS")
        self.assertEqual(response.counts["all"], 1)
        self.assertEqual(self._ids(response), {portal_partner.id})
        self.assertNotIn(unrelated_partner.id, self._ids(response))
        self.assertNotIn(outside_company_partner.id, self._ids(response))

    def test_013_unreadable_terminal_field_is_excluded_before_matching(self):
        portal_user = self._create_user(
            "CC-015 product portal", self.env.company, "base.group_portal"
        )
        user_env = self._user_env(portal_user, self.env.company)
        hidden_value = "cc15secret_%s" % uuid4().hex
        portal_user.partner_id.write(
            {
                "name": "CC-015 visible product %s" % uuid4().hex,
                "signup_type": hidden_value,
            }
        )
        domain_key, resource = self._publish_restricted_partner_domain()
        model_config = resource["models"][0]
        readable = permission_boundary.authorize_searchable_fields(
            user_env,
            user_env["res.partner"],
            model_config["fields"],
            facade.user_context(user_env),
        )
        conditions = merge_conditions(
            (),
            (),
            keyword_terms=(KeywordTerm(hidden_value),),
        )
        visible = facade._effective_conditions(
            user_env,
            [resource],
            {"partner"},
            conditions,
            facade.user_context(user_env),
        )
        outcome = executor.execute(
            user_env,
            resource,
            conditions,
            20,
            facade.user_context(user_env),
        )
        summary = facade._response_conditions(
            conditions,
            visible,
            [outcome],
            {"partner"},
        )

        self.assertEqual([item["name"] for item in readable], ["name"])
        self.assertEqual(
            visible,
            [
                {
                    "dimension": "keyword",
                    "operator": "contains",
                    "value": hidden_value,
                }
            ],
        )
        self.assertEqual(outcome.count, 0)
        self.assertEqual(outcome.results, [])
        self.assertNotIn("signup_type", repr(summary))
        self.assertNotIn(hidden_value, repr(outcome.results))
        self.assertTrue(domain_key)

    def test_031_query_understanding_only_contains_authorized_conditions(self):
        product_name = "CC-015 visible condition %s" % uuid4().hex
        portal_user = self._create_user(
            "CC-015 condition portal", self.env.company, "base.group_portal"
        )
        portal_user.partner_id.write(
            {"name": product_name, "signup_type": "cc15hidden_%s" % uuid4().hex}
        )
        user_env = self._user_env(portal_user, self.env.company)
        _, resource = self._publish_restricted_partner_domain()
        keywords = (KeywordTerm("product"), KeywordTerm("visible"))
        visible_condition = {
            "dimension": "name",
            "operator": "contains",
            "value": product_name,
        }
        conditions = merge_conditions(
            (visible_condition,),
            (),
            keyword_terms=keywords,
        )
        visible = facade._effective_conditions(
            user_env,
            [resource],
            {"partner"},
            conditions,
            facade.user_context(user_env),
        )
        summary = facade._response_conditions(
            conditions,
            visible,
            [ResourceOutcome(resource="partner", status="SUCCESS")],
            {"partner"},
        )

        self.assertIn(visible_condition, summary)
        self.assertEqual(
            [item["value"] for item in summary if item["dimension"] == "keyword"],
            ["product", "visible"],
        )
        self.assertNotIn("signup_type", repr(summary))
        with self.assertRaises(RequestBoundaryError):
            facade._effective_conditions(
                user_env,
                [resource],
                {"partner"},
                merge_conditions(
                    (
                        {
                            "dimension": "signup_type",
                            "operator": "contains",
                            "value": "cc15hidden",
                        },
                    ),
                    (),
                ),
                facade.user_context(user_env),
            )

    def test_030_keyword_terms_do_not_combine_across_resources(self):
        token_a = "cc15a_%s" % uuid4().hex
        token_b = "cc15b_%s" % uuid4().hex
        self.env["res.partner"].create(
            {"name": "Fixture %s" % token_a, "email": "unrelated@example.test"}
        )
        self.env["res.partner"].create(
            {
                "name": "Unrelated fixture",
                "email": "%s@example.test" % token_b,
            }
        )
        domain_key, _ = self._publish_domain(
            [
                ("name_only", ("name",)),
                ("email_only", ("email",)),
            ]
        )

        response = self._search(
            domain_key,
            ("name_only", "email_only"),
            raw_query="%s %s" % (token_a, token_b),
        )

        self.assertEqual(response.counts["by_resource"], {"name_only": 0, "email_only": 0})
        self.assertEqual(response.counts["all"], 0)
        self.assertEqual(response.results, [])

    def test_032_direct_condition_query_object_executes_without_parser(self):
        token_a = "cc15a_%s" % uuid4().hex
        token_b = "cc15b_%s" % uuid4().hex
        match = self.env["res.partner"].create(
            {"name": "Fixture %s %s" % (token_a, token_b)}
        )
        _, resources = self._publish_domain([("partner", ("name",))])
        query_object = request_boundary.validate_condition_query_object(
            ConditionQueryObject(
                keyword_terms=(KeywordTerm(token_a), KeywordTerm(token_b))
            )
        )
        conditions = merge_conditions(
            query_object.field_conditions,
            (),
            keyword_terms=query_object.keyword_terms,
        )

        with patch.object(
            request_boundary,
            "parse_multi_query",
            side_effect=AssertionError("executor must not parse raw text"),
        ):
            outcome = executor.execute(
                self.env, resources["partner"], conditions, 20
            )

        self.assertEqual(outcome.status, "SUCCESS")
        self.assertEqual(outcome.count, 1)
        self.assertEqual(
            {result["_record_id"] for result in outcome.results}, {match.id}
        )

    def test_036_empty_request_matches_orm_compatibility_baseline(self):
        marker = "cc15empty_%s" % uuid4().hex
        fixture = self.env["res.partner"].create({"name": marker})
        domain_key, _ = self._publish_domain([("partner", ("name",))])
        model = self.env["res.partner"]
        baseline_count = model.search_count([])

        response = self._search(domain_key, ("partner",), limit=200)
        post_request_count = model.search_count([])

        self.assertIn(response.status, ("SUCCESS", "EMPTY"))
        self.assertEqual(response.counts["all"], baseline_count)
        self.assertEqual(post_request_count, baseline_count)
        self.assertGreater(baseline_count, 0)
        self.assertTrue(fixture.exists())
        self.assertLessEqual(len(response.results), 200)

    def test_042_unicode_contains_and_rejected_controls_are_end_to_end(self):
        marker = "客户 Café\u0301_%s" % uuid4().hex
        fixture = self.env["res.partner"].create({"name": "Fixture %s" % marker})
        domain_key, _ = self._publish_domain([("partner", ("name",))])

        response = self._search(domain_key, ("partner",), raw_query=marker)

        self.assertEqual(response.status, "SUCCESS")
        self.assertIn(fixture.id, self._ids(response))
        invalid_queries = (
            "A\u0001 B",
            "A\u202e B",
            "A\u200b B",
            "A\u200c B",
            "A\u200d B",
            "A\u2060 B",
            "A\ufeff B",
            "A\ud800 B",
        )
        for raw_query in invalid_queries:
            with self.subTest(codepoints=[hex(ord(char)) for char in raw_query]):
                with patch.object(facade, "execute", wraps=executor.execute) as execute:
                    invalid = self._search(
                        domain_key, ("partner",), raw_query=raw_query
                    )

                self.assertEqual(invalid.errors[0]["code"], "INVALID_REQUEST")
                self.assertEqual(invalid.results, [])
                self.assertEqual(invalid.counts["all"], 0)
                self.assertNotIn(raw_query, repr(invalid))
                execute.assert_not_called()

    def test_039_invalid_publish_and_invalid_request_errors_are_distinct(self):
        invalid_domain_keys = []
        for field_name, operator_set, index_strategy in (
            ("missing_terminal", "contains", "gin_trgm"),
            ("name", "contains", "btree"),
            ("parent_id.missing_terminal", "contains", "gin_trgm"),
        ):
            key = "cc015_invalid_%s" % uuid4().hex
            domain = self.env["wd.gs.config.domain"].create(
                {"key": key, "name": key}
            )
            version = self.env["wd.gs.config.version"].create(
                {"domain_id": domain.id, "version": 1}
            )
            resource = self.env["wd.gs.business.resource"].create(
                {
                    "version_id": version.id,
                    "key": "partner",
                    "name": "Partner",
                    "primary_model_id": self.env["ir.model"].search(
                        [("model", "=", "res.partner")], limit=1
                    ).id,
                    "navigation_action_id": self.env.ref(
                        "wd_global_search.action_gs_native_form_partner"
                    ).id,
                    "card_template": "Name: {name}",
                }
            )
            self.env["wd.gs.searchable.field"].create(
                {
                    "resource_id": resource.id,
                    "field_name": field_name,
                    "purpose": "identifier",
                    "operator_set": operator_set,
                    "index_strategy": index_strategy,
                }
            )
            self.env["wd.gs.snapshot.field"].create(
                {
                    "resource_id": resource.id,
                    "field_name": "name",
                    "label": "Name",
                    "sequence": 10,
                    "visible": True,
                    "format_type": "text",
                }
            )
            self.env["wd.gs.business.date.mapping"].create(
                {
                    "resource_id": resource.id,
                    "model_name": "res.partner",
                    "field_name": "create_date",
                }
            )

            self.assertFalse(version.action_publish())
            self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")
            invalid_domain_keys.append(key)

        config_failure = facade.SearchService().search(
            self.env,
            SearchRequest(resource_scope=("partner",)),
            invalid_domain_keys[0],
        )
        valid_domain_key, _ = self._publish_domain([("partner", ("name",))])
        request_failure = facade.SearchService().search(
            self.env,
            SearchRequest(
                resource_scope=("partner",),
                parsed_conditions=(
                    {"dimension": "", "operator": "contains", "value": "x"},
                ),
            ),
            valid_domain_key,
        )

        self.assertEqual(config_failure.errors[0]["code"], "CONFIGURATION_ERROR")
        self.assertEqual(request_failure.errors[0]["code"], "INVALID_REQUEST")

    def test_043_cc016_resource_descriptor_exposes_searchable_field_metadata(self):
        domain_key, _ = self._publish_domain([("partner", ("name", "email"))])

        response = facade.SearchService().resource_descriptors(self.env, domain_key)

        fields = response["resources"][0]["searchable_fields"]
        email = next(field for field in fields if field["dimension"] == "email")
        self.assertEqual(email["type"], "char")
        self.assertEqual(email["operator"], "contains")
        self.assertEqual(email["operator_label"], "contains")
        self.assertNotIn("name", {field["dimension"] for field in fields})

    def test_044_cc016_resource_descriptor_omits_unreadable_fields(self):
        portal_user = self._create_user(
            "CC-016 descriptor portal", self.env.company, "base.group_portal"
        )
        user_env = self._user_env(portal_user, self.env.company)
        domain_key, _ = self._publish_restricted_partner_domain()

        response = facade.SearchService().resource_descriptors(user_env, domain_key)

        fields = response["resources"][0]["searchable_fields"]
        self.assertNotIn("signup_type", {field["dimension"] for field in fields})

    def test_045_cc016_structured_field_condition_rejects_unavailable_operator(self):
        _, snapshot = self._publish_domain([("partner", ("email",))])
        condition = {
            "dimension": "email",
            "operator": "=",
            "value": "contact@example.com",
        }

        with self.assertRaises(RequestBoundaryError):
            facade._effective_conditions(
                self.env,
                [snapshot["partner"]],
                {"partner"},
                merge_conditions((condition,), ()),
                facade.user_context(self.env),
                submitted_conditions=(condition,),
            )

    def test_046_cc016_structured_field_condition_rejects_wrong_value_type(self):
        _, snapshot = self._publish_domain([("partner", ("email",))])
        condition = {
            "dimension": "email",
            "operator": "contains",
            "value": 123,
        }

        with self.assertRaises(RequestBoundaryError):
            facade._effective_conditions(
                self.env,
                [snapshot["partner"]],
                {"partner"},
                merge_conditions((condition,), ()),
                facade.user_context(self.env),
                submitted_conditions=(condition,),
            )
