import logging
import time
from unittest.mock import patch
from types import SimpleNamespace
from uuid import uuid4

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools.misc import formatLang

from ..services.card import read_card_values, serialize_card_template
from ..services.executor import execute
from ..services import template as template_service
from ..services.template import (
    TemplateError,
    parse_template,
    render_template,
    template_read_field_names,
    validate_structured_card_template,
    validate_template,
)

_logger = logging.getLogger(__name__)


class TestCardTemplate(TransactionCase):
    def _create_warehouse_relation_fixture(self):
        country = self.env["res.country"].search([("code", "=", "US")], limit=1)
        self.assertTrue(country)
        grandparent = self.env["res.partner"].create(
            {"name": "Warehouse Grandparent", "country_id": country.id}
        )
        parent = self.env["res.partner"].create(
            {
                "name": "Warehouse Parent",
                "country_id": country.id,
                "parent_id": grandparent.id,
            }
        )
        address = self.env["res.partner"].create(
            {"name": "Warehouse Address", "parent_id": parent.id}
        )
        warehouse = self.env["stock.warehouse"].create(
            {
                "name": "Template Warehouse",
                "code": "T%s" % uuid4().hex[:4].upper(),
                "company_id": self.env.company.id,
                "partner_id": address.id,
            }
        )
        return warehouse, country

    def _render_record_template(self, record, template, separator=", "):
        model = record.env[record._name]
        values, readable_fields = read_card_values(
            record,
            template_read_field_names(model, template),
            template,
        )[0]
        return serialize_card_template(
            record.env,
            {
                "card_template": template,
                "card_many2many_separator": separator,
            },
            record._name,
            values,
            readable_fields,
        )

    def _measure_p95_ms(self, operation, cold=False):
        samples = []
        for _ in range(100):
            if cold:
                self.env.invalidate_all()
            started = time.perf_counter()
            operation()
            samples.append((time.perf_counter() - started) * 1000)
        return sorted(samples)[94]

    def test_relation_template_performance_uses_100_samples(self):
        warehouse, _country = self._create_warehouse_relation_fixture()
        category_model = self.env["res.partner.category"]
        categories = category_model.create(
            [{"name": "Template Category A"}, {"name": "Template Category B"}]
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Template M2M Partner",
                "category_id": [(6, 0, categories.ids)],
            }
        )
        order_partner = self.env["res.partner"].create(
            {"name": "Template Performance Order Partner"}
        )
        order = self.env["sale.order"].create({"partner_id": order_partner.id})
        products = self.env["product.product"].create(
            [
                {"name": "Template Performance Product A", "list_price": 10},
                {"name": "Template Performance Product B", "list_price": 20},
            ]
        )
        order.write(
            {
                "order_line": [
                    (0, 0, {"product_id": products[0].id, "product_uom_qty": 1}),
                    (0, 0, {"product_id": products[1].id, "product_uom_qty": 2}),
                ]
            }
        )

        scenarios = (
            (
                "many2one",
                warehouse,
                "{partner_id.parent_id.country_id.name}",
            ),
            ("many2many", partner, "{category_id.name}"),
            (
                "one2many_loop",
                order,
                "{order_line}{product_id.name}:{product_uom_qty}\\n{/order_line}",
            ),
        )
        for name, record, template in scenarios:
            model = self.env[record._name]
            parser_p95 = self._measure_p95_ms(lambda: parse_template(template))
            validation_p95 = self._measure_p95_ms(
                lambda: validate_template(template, [model])
            )
            cold_render_p95 = self._measure_p95_ms(
                lambda: self._render_record_template(record, template),
                cold=True,
            )
            hot_render_p95 = self._measure_p95_ms(
                lambda: self._render_record_template(record, template)
            )
            _logger.info(
                "CC14-1 PERF scenario=%s samples=100 parser_p95_ms=%.3f "
                "validation_p95_ms=%.3f cold_render_p95_ms=%.3f "
                "hot_render_p95_ms=%.3f",
                name,
                parser_p95,
                validation_p95,
                cold_render_p95,
                hot_render_p95,
            )

    def test_search_executor_returns_plain_template_card_text(self):
        record = self.env["res.partner"].create(
            {"name": "Template Search Fixture"}
        )
        resource = {
            "key": "template_test",
            "models": [
                {
                    "model_name": "res.partner",
                    "fields": [{"name": "name"}],
                }
            ],
            "card_template": "Partner: {name}",
        }

        outcome = execute(
            self.env,
            resource,
            SimpleNamespace(
                values=(
                    {
                        "dimension": "name",
                        "operator": "=",
                        "value": "Template Search Fixture",
                    },
                )
            ),
            limit=1,
        )

        result = next(item for item in outcome.results if item["id"] == record.id)
        self.assertEqual(
            result["snapshot"],
            {"rendered_text": "Partner: Template Search Fixture"},
        )

    def test_search_executor_resolves_from_the_searched_warehouse_root(self):
        warehouse, country = self._create_warehouse_relation_fixture()
        resource = {
            "key": "warehouse_template_test",
            "models": [
                {
                    "model_name": "stock.warehouse",
                    "fields": [{"name": "code"}],
                }
            ],
            "card_template": "{partner_id.parent_id.country_id.name}",
        }
        outcome = execute(
            self.env,
            resource,
            SimpleNamespace(
                values=(
                    {
                        "dimension": "code",
                        "operator": "=",
                        "value": warehouse.code,
                    },
                )
            ),
            limit=1,
        )

        result = next(item for item in outcome.results if item["id"] == warehouse.id)
        self.assertEqual(result["snapshot"]["rendered_text"], country.name)

    def test_search_executor_renders_one2many_rows_from_the_search_root(self):
        partner = self.env["res.partner"].create({"name": "Template Loop Partner"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        product = self.env["product.product"].create(
            {"name": "Template Loop Product", "list_price": 10}
        )
        order.write(
            {
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": 1})
                ]
            }
        )
        template = "{order_line}{product_id.name}{/order_line}"
        resource = {
            "key": "sale_order_loop_template_test",
            "models": [
                {"model_name": "sale.order", "fields": [{"name": "name"}]}
            ],
            "card_template": template,
        }
        outcome = execute(
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
            limit=1,
        )

        result = next(item for item in outcome.results if item["id"] == order.id)
        self.assertEqual(
            result["snapshot"]["rendered_text"],
            "Template Loop Product",
        )

    def test_search_executor_returns_structured_card_and_truncates_visible_details(self):
        partner = self.env["res.partner"].create(
            {"name": "Structured Card Fixture Customer"}
        )
        order = self.env["sale.order"].create({"partner_id": partner.id})
        products = self.env["product.product"].create(
            [
                {"name": "Structured Fixture Product %s" % index, "list_price": 10}
                for index in range(4)
            ]
        )
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
        resource = {
            "key": "structured_card_test",
            "models": [
                {"model_name": "sale.order", "fields": [{"name": "name"}]}
            ],
            "structured_card_template": {
                "schema_version": 1,
                "title": "{name}",
                "meta": "Sales Order · {date_order:datetime}",
                "summary": "{partner_id}",
                "details": (
                    "{order_line}{product_id.name} × {product_uom_qty}"
                    "{/order_line}"
                ),
            },
        }

        outcome = execute(
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
            limit=1,
        )

        result = next(item for item in outcome.results if item["id"] == order.id)
        card = result["snapshot"]["card"]
        self.assertEqual(card["schema_version"], 1)
        self.assertEqual(card["title"], order.name)
        self.assertEqual(card["summary"], partner.display_name)
        self.assertEqual(len(card["details"]), 3)
        self.assertTrue(card["details_truncated"])
        self.assertNotIn("rendered_text", result["snapshot"])
        self.assertEqual(outcome.count, 1)

        original_resolve_path = template_service._resolve_path

        def deny_first_product(record, path, format_key, separator):
            if (
                path == ["product_id", "name"]
                and record.product_id.name == products[0].name
            ):
                return template_service._UNAUTHORIZED
            return original_resolve_path(record, path, format_key, separator)

        with patch.object(
            template_service, "_resolve_path", side_effect=deny_first_product
        ):
            visible_details, details_truncated = template_service.render_template_items(
                self.env,
                order,
                resource["structured_card_template"]["details"],
            )
        self.assertEqual(len(visible_details), 3)
        self.assertFalse(details_truncated)
        self.assertTrue(
            all(products[0].name not in item for item in visible_details)
        )

    def test_structured_card_validation_requires_explicit_regions_and_single_loop(self):
        base = {
            "schema_version": 1,
            "title": "{name}",
            "meta": "",
            "summary": "",
            "details": "",
        }
        parsed = validate_structured_card_template(
            base, [self.env["res.partner"]]
        )
        self.assertIn("title", parsed)

        invalid = dict(base, details="{category_id}{/category_id}")
        with self.assertRaises(TemplateError):
            validate_structured_card_template(
                invalid, [self.env["res.partner"]]
            )

        invalid = dict(base, title="Partners")
        with self.assertRaises(TemplateError):
            validate_structured_card_template(
                invalid, [self.env["res.partner"]]
            )

    def test_structured_card_template_enforces_aggregate_budgets(self):
        configuration = {
            "schema_version": 1,
            "title": "{name}" + ("a" * 4100),
            "meta": "",
            "summary": "b" * 4100,
            "details": "",
        }

        with self.assertRaises(TemplateError):
            validate_structured_card_template(
                configuration, [self.env["res.partner"]]
            )

    def test_constant_only_templates_are_valid(self):
        parts = validate_template(
            "常量\n{{only}}", [self.env["res.partner"]]
        )

        self.assertEqual(
            render_template(self.env, "res.partner", {}, [], "常量\n{{only}}"),
            "常量\n{only}",
        )
        self.assertEqual(len(parts), 1)

    def test_render_published_card_template_values_with_authorized_relations(self):
        parent = self.env["res.partner"].create({"name": "Template Parent"})
        record = self.env["res.partner"].create(
            {"name": "Template Child", "parent_id": parent.id}
        )
        template = "Name: {name}\nParent: {parent_id}"
        fields = ["name", "parent_id"]
        values, readable_fields = read_card_values(record, fields, template)[0]

        rendered = serialize_card_template(
            self.env,
            {"card_template": template},
            "res.partner",
            values,
            readable_fields,
        )

        self.assertEqual(rendered, "Name: Template Child\nParent: Template Parent")

    def test_parse_constants_variables_and_escapes(self):
        parts = parse_template(
            r"Order: {name}\n{{literal}} \t{amount_total:monetary}"
        )

        self.assertEqual(
            [(part.text, part.field_name, part.format_key) for part in parts],
            [
                ("Order: ", "", ""),
                ("", "name", ""),
                ("\n{literal} \t", "", ""),
                ("", "amount_total", "monetary"),
            ],
        )

    def test_rejects_expressions_and_unmatched_braces(self):
        for template in (
            "{__import__('os')}",
            "{field()}",
            "{field",
            "field}",
            "{field:unknown}",
        ):
            with self.subTest(template=template), self.assertRaises(TemplateError):
                parse_template(template)
        with self.assertRaises(TemplateError):
            validate_template("{field.__class__}", [self.env["res.partner"]])

    def test_variable_count_limit_counts_repeated_occurrences(self):
        with self.assertRaises(TemplateError):
            parse_template("{name}" * 51)

    def test_utf8_byte_limit(self):
        with self.assertRaises(TemplateError):
            parse_template("你" * 2731)

    def test_render_keeps_unauthorized_values_blank(self):
        class Field:
            type = "char"

        class Model:
            _fields = {"name": Field()}

        class Env:
            def __getitem__(self, _model_name):
                return Model()

        rendered = render_template(
            Env(),
            "res.partner",
            {"name": "private"},
            [],
            "Name: {name}",
        )

        self.assertEqual(rendered, "Name: ")

    def test_preview_marks_unreadable_fields_without_reading_their_values(self):
        class Field:
            type = "char"

        class Model:
            _fields = {"secret": Field()}

        class Env:
            def __getitem__(self, _model_name):
                return Model()

        rendered = render_template(
            Env(),
            "res.partner",
            {},
            [],
            "Secret: {secret}",
            unauthorized_placeholder="[无权访问]",
        )

        self.assertEqual(rendered, "Secret: [无权访问]")

    def test_card_value_reader_handles_field_access_denial(self):
        class Field:
            type = "char"

        class Model:
            _fields = {"secret": Field()}

            def check_field_access_rights(self, _operation, _field_names):
                raise AccessError("field denied")

        class Env:
            def __getitem__(self, _model_name):
                return Model()

        class Records:
            env = Env()
            _name = "res.partner"

            def __iter__(self):
                return iter((SimpleNamespace(id=1),))

            def browse(self, record_id):
                return SimpleNamespace(id=record_id)

        values, readable_fields = read_card_values(
            Records(), ["secret"], "Secret: {secret}"
        )[0]

        self.assertNotIn("secret", values)
        self.assertEqual(readable_fields, set())

    def test_warehouse_many2one_paths_render_one_two_and_three_hops(self):
        warehouse, country = self._create_warehouse_relation_fixture()
        model = self.env["stock.warehouse"]
        templates = (
            "{partner_id.name}",
            "{partner_id.country_id.name}",
            "{partner_id.parent_id.country_id.name}",
        )

        for template in templates:
            with self.subTest(template=template):
                validate_template(template, [model])
                self.assertEqual(
                    self._render_record_template(warehouse, template),
                    (
                        "Warehouse Address"
                        if template == templates[0]
                        else country.name
                    ),
                )

    def test_warehouse_many2one_path_over_three_hops_is_rejected(self):
        with self.assertRaises(TemplateError):
            validate_template(
                "{partner_id.parent_id.parent_id.country_id.name}",
                [self.env["stock.warehouse"]],
            )

    def test_many2many_paths_render_values_and_use_configured_separator(self):
        category_model = self.env["res.partner.category"]
        first = category_model.create({"name": "Alpha"})
        second = category_model.create({"name": "Beta", "parent_id": first.id})
        partner = self.env["res.partner"].create(
            {"name": "Template M2M Partner", "category_id": [(6, 0, [first.id, second.id])]}
        )

        validate_template("{category_id.name}", [self.env["res.partner"]])
        validate_template(
            "{category_id.parent_id.name}", [self.env["res.partner"]]
        )
        self.assertEqual(
            self._render_record_template(partner, "{category_id.name}", " | "),
            "Alpha | Beta",
        )
        self.assertEqual(
            self._render_record_template(partner, "{category_id.parent_id.name}", " | "),
            "— | Alpha",
        )

    def test_many2many_path_depth_and_mixed_relation_types_are_rejected(self):
        model = self.env["res.partner"]
        for template in (
            "{category_id.parent_id.parent_id.name}",
            "{parent_id.category_id.name}",
            "{category_id.parent_id}",
        ):
            with self.subTest(template=template), self.assertRaises(TemplateError):
                validate_template(template, [model])

    def test_empty_many2one_and_many2many_paths_render_an_em_dash(self):
        partner = self.env["res.partner"].create({"name": "Empty Relations"})

        self.assertEqual(
            self._render_record_template(partner, "{parent_id.country_id.name}"),
            "—",
        )
        self.assertEqual(
            self._render_record_template(partner, "{category_id.name}"),
            "—",
        )

    def test_one2many_order_lines_render_current_item_paths_and_format_keys(self):
        partner = self.env["res.partner"].create({"name": "Template Order Partner"})
        order = self.env["sale.order"].create({"partner_id": partner.id})
        products = self.env["product.product"].create(
            [
                {"name": "Template Product A", "list_price": 10},
                {"name": "Template Product B", "list_price": 20},
            ]
        )
        order.write(
            {
                "order_line": [
                    (0, 0, {"product_id": products[0].id, "product_uom_qty": 1}),
                    (0, 0, {"product_id": products[1].id, "product_uom_qty": 2}),
                ]
            }
        )
        template = (
            "{order_line}{product_id.name} × {product_uom_qty} = "
            "{price_subtotal:monetary}\n{/order_line}"
        )

        validate_template(template, [self.env["sale.order"]])
        rendered = self._render_record_template(order, template)

        self.assertIn("Template Product A", rendered)
        self.assertIn("Template Product B", rendered)
        self.assertEqual(len(rendered.splitlines()), 2)
        for line in order.order_line:
            self.assertIn(
                formatLang(
                    self.env, line.price_subtotal, currency_obj=line.currency_id
                ),
                rendered,
            )

    def test_nested_one2many_loops_render_current_scope_only(self):
        root = self.env["res.partner"].create({"name": "Loop Root"})
        child = self.env["res.partner"].create(
            {"name": "Loop Child", "parent_id": root.id}
        )
        self.env["res.partner"].create(
            {"name": "Loop Grandchild", "parent_id": child.id}
        )
        template = (
            "{child_ids}{name}:"
            "{child_ids}{name}{/child_ids}"
            "{/child_ids}"
        )

        validate_template(template, [self.env["res.partner"]])
        self.assertEqual(
            self._render_record_template(root, template),
            "Loop Child:Loop Grandchild",
        )

    def test_empty_one2many_loop_emits_no_loop_body(self):
        partner = self.env["res.partner"].create({"name": "Empty Loop Partner"})
        template = "Lines:{child_ids} {name}{/child_ids}:end"

        self.assertEqual(
            self._render_record_template(partner, template),
            "Lines::end",
        )

    def test_synthetic_preview_renders_relationship_paths_and_loop_examples(self):
        template = (
            "{order_line}{product_id.name}:"
            "{product_uom_qty}{/order_line}"
        )
        validate_template(
            template,
            [self.env["sale.order"]],
            check_permissions=False,
        )

        rendered = render_template(
            self.env,
            "sale.order",
            {},
            ["order_line"],
            template,
        )

        self.assertTrue(rendered.startswith("Example:"))

    def test_structure_validation_uses_model_metadata_without_business_reads(self):
        class Model:
            def __init__(self, name):
                self._name = name
                self._fields = {}
                self.env = None

            def check_access_rights(self, _operation):
                return True

            def check_field_access_rights(self, _operation, names):
                if any(name not in self._fields for name in names):
                    raise AccessError("missing field")

            def search(self, *_args, **_kwargs):
                raise AssertionError("structure validation must not search business records")

            def read(self, *_args, **_kwargs):
                raise AssertionError("structure validation must not read business records")

        class Env(dict):
            pass

        env = Env()
        root = Model("test.root")
        related = Model("test.related")
        env.update({"test.root": root, "test.related": related})
        root.env = related.env = env
        root._fields["related_id"] = SimpleNamespace(
            type="many2one",
            store=True,
            related=False,
            comodel_name="test.related",
        )
        related._fields["name"] = SimpleNamespace(
            type="char",
            store=True,
            related=False,
            comodel_name=None,
        )

        validate_template("{related_id.name}", [root])

    def test_one2many_cannot_be_used_as_a_scalar_or_path(self):
        with self.assertRaises(TemplateError):
            validate_template("{order_line}", [self.env["sale.order"]])
        with self.assertRaises(TemplateError):
            validate_template(
                "{order_line.product_id.name}", [self.env["sale.order"]]
            )
        with self.assertRaises(TemplateError):
            validate_template("{name}", [self.env["product.product"]])

    def test_loop_scope_rejects_fields_only_available_on_the_root_model(self):
        with self.assertRaises(TemplateError):
            validate_template(
                "{order_line}{partner_id.name}{/order_line}",
                [self.env["sale.order"]],
            )

    def test_loop_labels_nesting_count_and_body_length_are_bounded(self):
        for template in (
            "{order_line}unclosed",
            "{order_line}body{/move_ids}",
            "{order_line}body{/order_line}{/order_line}",
        ):
            with self.subTest(template=template), self.assertRaises(TemplateError):
                validate_template(template, [self.env["sale.order"]])

        with self.assertRaises(TemplateError):
            parse_template(
                "{child_ids}{child_ids}{child_ids}x{/child_ids}"
                "{/child_ids}{/child_ids}"
            )
        with self.assertRaises(TemplateError):
            parse_template(
                "".join("{%s}x{/%s}" % (name, name) for name in "abcdef")
            )
        with self.assertRaises(TemplateError):
            parse_template("{child_ids}" + "x" * 1001 + "{/child_ids}")
        self.assertEqual(
            len(parse_template("{child_ids}" + "x" * 1000 + "{/child_ids}")),
            1,
        )

    def test_loop_constants_escapes_and_html_remain_plain_text(self):
        partner = self.env["res.partner"].create({"name": "<script>ignored</script>"})
        template = "{child_ids}{{line}}\\n{name}{/child_ids}"

        self.assertEqual(self._render_record_template(partner, template), "")
        self.assertEqual(
            render_template(
                self.env,
                "res.partner",
                {"name": "<script>ignored</script>"},
                ["name"],
                "{{constant}}: {name}",
            ),
            "{constant}: <script>ignored</script>",
        )

    def test_relation_rule_filters_many2many_members_for_current_user(self):
        category_model = self.env["res.partner.category"]
        visible = category_model.create({"name": "Visible Category"})
        hidden = category_model.create({"name": "Hidden Category"})
        partner = self.env["res.partner"].create(
            {
                "name": "Restricted M2M Partner",
                "category_id": [(6, 0, [visible.id, hidden.id])],
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "Template Relation Reader",
                "login": "template-relation-%s" % uuid4().hex,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.env["ir.rule"].create(
            {
                "name": "Template visible category only",
                "model_id": self.env.ref("base.model_res_partner_category").id,
                "domain_force": "[('name', '=', 'Visible Category')]",
                "groups": [(6, 0, [self.env.ref("base.group_user").id])],
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )

        rendered = self._render_record_template(
            partner.with_user(user), "{category_id.name}"
        )

        self.assertEqual(rendered, "Visible Category")

    def test_one2many_loop_applies_current_users_record_rules(self):
        user = self.env["res.users"].create(
            {
                "name": "Template Order Reader",
                "login": "template-order-%s" % uuid4().hex,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("sales_team.group_sale_salesman").id,
                        ],
                    )
                ],
            }
        )
        partner = self.env["res.partner"].create({"name": "Template Rule Partner"})
        order = self.env["sale.order"].create(
            {"partner_id": partner.id, "user_id": user.id}
        )
        products = self.env["product.product"].create(
            [
                {"name": "Visible Order Product", "list_price": 10},
                {"name": "Hidden Order Product", "list_price": 20},
            ]
        )
        order.write(
            {
                "order_line": [
                    (0, 0, {"product_id": products[0].id, "product_uom_qty": 1}),
                    (0, 0, {"product_id": products[1].id, "product_uom_qty": 1}),
                ]
            }
        )
        visible_line = order.order_line.filtered(
            lambda line: line.product_id == products[0]
        )
        self.env["ir.rule"].create(
            {
                "name": "Template visible order line only",
                "model_id": self.env.ref("sale.model_sale_order_line").id,
                "domain_force": "[('id', '=', %d)]" % visible_line.id,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )

        rendered = self._render_record_template(
            order.with_user(user),
            "{order_line}{product_id.name}{/order_line}",
        )

        self.assertEqual(rendered, "Visible Order Product")
        self.assertNotIn("Hidden Order Product", rendered)
