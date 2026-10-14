import logging
import time
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from odoo.tests.common import TransactionCase

from ..services.card import (
    authorized_card_field_names,
    read_card_values,
    serialize_structured_card,
)
from ..services.executor import execute
from ..services import template as template_service
from ..services.template import (
    TemplateError,
    parse_template,
    validate_structured_card_template,
)

_logger = logging.getLogger(__name__)


class TestStructuredCard(TransactionCase):
    def _order(self, line_count):
        partner = self.env["res.partner"].create(
            {"name": "CC17-1 Structured Customer"}
        )
        order = self.env["sale.order"].create({"partner_id": partner.id})
        products = (
            self.env["product.product"].create(
                [
                    {
                        "name": "CC17-1 Product %s" % index,
                        "list_price": 10,
                    }
                    for index in range(line_count)
                ]
            )
            if line_count
            else self.env["product.product"].browse()
        )
        if products:
            order.write(
                {
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "product_uom_qty": index + 1,
                            },
                        )
                        for index, product in enumerate(products)
                    ]
                }
            )
        return order, products

    def _resource(self, template):
        return {
            "key": "structured_%s" % uuid4().hex,
            "models": [
                {"model_name": "sale.order", "fields": [{"name": "name"}]}
            ],
            "structured_card_template": template,
        }

    def _execute_order(self, order, resource):
        return execute(
            self.env,
            resource,
            SimpleNamespace(
                values=(
                    {
                        "dimension": "name",
                        "operator": "=",
                        "value": order.name,
                    },
                )
            ),
            limit=10,
        )

    def _template(self, details=""):
        return {
            "schema_version": 1,
            "title": "{name}",
            "meta": "Sales Order",
            "summary": "",
            "details": details,
        }

    def _measure_p95_ms(self, operation):
        samples = []
        for _ in range(100):
            started = time.perf_counter()
            operation()
            samples.append((time.perf_counter() - started) * 1000)
        return sorted(samples)[94]

    def test_publish_accepts_structured_template(self):
        domain = self.env["wd.gs.config.domain"].create(
            {"key": "cc17_1_%s" % uuid4().hex, "name": "CC17-1"}
        )
        version = self.env["wd.gs.config.version"].create(
            {"domain_id": domain.id, "version": 1}
        )
        resource = self.env["wd.gs.business.resource"].create(
            {
                "version_id": version.id,
                "key": "partner",
                "name": "Partner",
                "structured_card_title_template": "{name}",
                "primary_model_id": self.env["ir.model"].search(
                    [("model", "=", "res.partner")], limit=1
                ).id,
                "navigation_action_id": self.env.ref(
                    "wd_global_search.action_gs_native_form_partner"
                ).id,
            }
        )
        self.env["wd.gs.searchable.field"].create(
            {
                "resource_id": resource.id,
                "field_name": "name",
                "purpose": "identifier",
                "operator_set": "exact",
                "index_strategy": "btree",
            }
        )
        self.env["wd.gs.business.date.mapping"].create(
            {
                "resource_id": resource.id,
                "model_name": "res.partner",
                "field_name": "create_date",
            }
        )

        version.action_publish()

        published = self.env["wd.gs.config.version"].browse(version.id)
        self.assertEqual(published.state, "published")
        self.assertIn('"structured_card_template"', published.snapshot_json)

    def test_response_has_snapshot_card_schema(self):
        order, _products = self._order(0)
        outcome = self._execute_order(order, self._resource(self._template()))

        result = next(item for item in outcome.results if item["id"] == order.id)
        self.assertEqual(
            set(result["snapshot"]["card"]),
            {
                "schema_version",
                "title",
                "meta",
                "summary",
                "details",
                "details_truncated",
            },
        )
        self.assertEqual(result["snapshot"]["card"]["schema_version"], 1)
        self.assertEqual(result["snapshot"]["card"]["details"], [])
        self.assertEqual(result["snapshot"]["card"]["details_truncated"], False)
        self.assertEqual(result["snapshot"]["card"]["summary"], "")

    def test_three_detail_limit_and_truncation(self):
        template = self._template(
            "{order_line}{product_id.name} × {product_uom_qty}{/order_line}"
        )
        for line_count, expected_count, expected_truncated in (
            (0, 0, False),
            (1, 1, False),
            (3, 3, False),
            (4, 3, True),
        ):
            with self.subTest(line_count=line_count):
                order, _products = self._order(line_count)
                outcome = self._execute_order(order, self._resource(template))
                card = next(
                    item["snapshot"]["card"]
                    for item in outcome.results
                    if item["id"] == order.id
                )
                self.assertEqual(len(card["details"]), expected_count)
                self.assertEqual(
                    card["details_truncated"], expected_truncated
                )

    def test_publish_rejects_invalid_structured_regions(self):
        invalid_templates = (
            self._template().copy() | {"schema_version": True},
            self._template().copy() | {"title": "constant"},
            self._template().copy()
            | {"details": "{order_line}{product_id.name}"},
        )
        for template in invalid_templates:
            with self.subTest(template=template):
                with self.assertRaises(TemplateError):
                    validate_structured_card_template(
                        template, [self.env["sale.order"]]
                    )

    def test_current_user_unreadable_detail_is_not_counted_for_truncation(self):
        order, products = self._order(4)
        template = self._template(
            "{order_line}{product_id.name}{/order_line}"
        )["details"]
        original_resolve_path = template_service._resolve_path

        def hide_first_detail(record, path, format_key, separator):
            if (
                path == ["product_id", "name"]
                and record.product_id.id == products[0].id
            ):
                return template_service._UNAUTHORIZED
            return original_resolve_path(record, path, format_key, separator)

        with patch.object(
            template_service, "_resolve_path", side_effect=hide_first_detail
        ):
            details, details_truncated = template_service.render_template_items(
                self.env, order, template
            )

        self.assertEqual(len(details), 3)
        self.assertFalse(details_truncated)
        self.assertNotIn(products[0].name, details)

    def test_unknown_schema_fails_resource_without_legacy_fallback(self):
        order, _products = self._order(0)
        template = self._template()
        template["schema_version"] = 2

        outcome = self._execute_order(order, self._resource(template))

        self.assertEqual(outcome.status, "FAILED")
        self.assertEqual(outcome.error["code"], "CONFIGURATION_ERROR")
        self.assertFalse(outcome.results)

    def test_multiple_resources_use_their_own_structured_templates(self):
        order, _products = self._order(0)
        first = self._resource(self._template())
        second_template = self._template()
        second_template["title"] = "Order {name}"
        second = self._resource(second_template)

        first_result = next(
            item
            for item in self._execute_order(order, first).results
            if item["id"] == order.id
        )
        second_result = next(
            item
            for item in self._execute_order(order, second).results
            if item["id"] == order.id
        )

        self.assertEqual(first_result["_resource"], first["key"])
        self.assertEqual(second_result["_resource"], second["key"])
        self.assertEqual(first_result["snapshot"]["card"]["title"], order.name)
        self.assertEqual(
            second_result["snapshot"]["card"]["title"], "Order %s" % order.name
        )

    def test_locale_formats_fields_without_translating_template_constants(self):
        order, _products = self._order(0)
        template = self._template()
        template["title"] = "Configured {date_order:date}"
        resource = self._resource(template)
        french_env = self.env(context={**self.env.context, "lang": "fr_FR"})

        result = next(
            item
            for item in execute(
                french_env,
                resource,
                SimpleNamespace(
                    values=(
                        {
                            "dimension": "name",
                            "operator": "=",
                            "value": order.name,
                        },
                    )
                ),
                limit=1,
            ).results
            if item["id"] == order.id
        )

        self.assertTrue(result["snapshot"]["card"]["title"].startswith("Configured "))

    def test_structured_output_does_not_change_count_or_pagination(self):
        for index in range(4):
            self._order(0)
        structured = self._resource(self._template())
        legacy = {
            "key": "legacy_page_%s" % uuid4().hex,
            "models": [
                {"model_name": "sale.order", "fields": [{"name": "name"}]}
            ],
            "card_template": "{name}",
        }
        conditions = SimpleNamespace(values=())

        structured_outcome = execute(
            self.env, structured, conditions, limit=2, offset=1
        )
        legacy_outcome = execute(self.env, legacy, conditions, limit=2, offset=1)

        self.assertEqual(structured_outcome.count, legacy_outcome.count)
        self.assertEqual(
            [item["id"] for item in structured_outcome.results],
            [item["id"] for item in legacy_outcome.results],
        )
        self.assertEqual(len(structured_outcome.results), 2)

    def test_structured_rendering_performance_p95(self):
        details_template = (
            "{order_line}{product_id.name} × {product_uom_qty}{/order_line}"
        )
        template = self._template(details_template)
        order, _products = self._order(3)
        resource = self._resource(template)

        parser_p95 = self._measure_p95_ms(
            lambda: parse_template(details_template)
        )
        validation_p95 = self._measure_p95_ms(
            lambda: validate_structured_card_template(
                template, [self.env["sale.order"]]
            )
        )
        readable_fields = authorized_card_field_names(
            resource, self.env["sale.order"], None
        )
        root_templates = "\n".join(
            template[name] for name in ("title", "meta", "summary")
        )
        values = read_card_values(
            order, readable_fields, root_templates
        )[0][0]
        card_render_p95 = self._measure_p95_ms(
            lambda: serialize_structured_card(
                self.env,
                resource,
                "sale.order",
                order,
                values,
                readable_fields,
            )
        )
        render_p95 = self._measure_p95_ms(
            lambda: self._execute_order(order, resource)
        )

        _logger.info(
            "CC17-1 PERF samples=100 parser_p95_ms=%.3f "
            "publish_validation_p95_ms=%.3f card_render_p95_ms=%.3f "
            "search_service_p95_ms=%.3f",
            parser_p95,
            validation_p95,
            card_render_p95,
            render_p95,
        )
