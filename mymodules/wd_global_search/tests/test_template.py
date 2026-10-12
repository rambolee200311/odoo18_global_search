from types import SimpleNamespace

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from ..services.card import read_card_values, serialize_card_template
from ..services.executor import execute
from ..services.template import (
    TemplateError,
    parse_template,
    render_template,
    validate_template,
)


class TestCardTemplate(TransactionCase):
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
            "{field.__class__}",
            "{field()}",
            "{field",
            "field}",
            "{field:unknown}",
        ):
            with self.subTest(template=template), self.assertRaises(TemplateError):
                parse_template(template)

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

        values, readable_fields = read_card_values(
            Records(), ["secret"], "Secret: {secret}"
        )[0]

        self.assertNotIn("secret", values)
        self.assertEqual(readable_fields, set())
