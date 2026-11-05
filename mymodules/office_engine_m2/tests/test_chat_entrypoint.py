"""Server-owned, bounded metadata helpers for native Office tools."""

from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests import TransactionCase
from office_mapping_verify import validate_user_revision

from ..services.chat_entrypoint import (
    _cell_coordinates,
    _field_candidates,
    _field_metadata,
    _template_context,
)


class TestOfficeToolContextHelpers(TransactionCase):
    def test_template_context_returns_only_schema_targets_and_bounded_visible_text(self):
        inspection = SimpleNamespace(
            elements=[
                SimpleNamespace(kind="cell", element_id="xlsx:Sheet1!A1", value="客户名称", writable=True),
                SimpleNamespace(kind="cell", element_id="xlsx:Sheet1!B1", value=None, writable=True),
                SimpleNamespace(kind="formula", element_id="xlsx:Sheet1!C1", value={"formula": "=B1*3"}, writable=False),
            ]
        )
        manifest, visible_text = _template_context(inspection)
        self.assertEqual(
            manifest,
            [
                {
                    "element_id": "xlsx:Sheet1!A1",
                    "required": False,
                    "writable": True,
                    "allowed_value_types": ["string", "number", "boolean", "date", "datetime", "formula"],
                    "approved_to_skip": True,
                },
                {
                    "element_id": "xlsx:Sheet1!B1",
                    "required": False,
                    "writable": True,
                    "allowed_value_types": ["string", "number", "boolean", "date", "datetime", "formula"],
                    "approved_to_skip": True,
                    "visual_labels": [
                        {
                            "element_id": "xlsx:Sheet1!A1",
                            "text": "客户名称",
                            "relation": "same_row_left",
                        }
                    ],
                },
                {
                    "element_id": "xlsx:Sheet1!C1",
                    "required": False,
                    "writable": True,
                    "allowed_value_types": ["string", "number", "boolean", "date", "datetime", "formula"],
                    "approved_to_skip": True,
                    "visual_labels": [
                        {
                            "element_id": "xlsx:Sheet1!A1",
                            "text": "客户名称",
                            "relation": "same_row_left",
                        }
                    ],
                }
            ],
        )
        self.assertEqual(
            visible_text,
            [
                {"element_id": "xlsx:Sheet1!A1", "text": "客户名称"},
                {"element_id": "xlsx:Sheet1!C1", "text": "=B1*3"},
            ],
        )
        self.assertEqual(_cell_coordinates("xlsx:Sheet1!B1"), ("Sheet1", 2, 1, "B1"))

    def test_formula_summary_row_does_not_turn_blank_neighbors_into_required_targets(self):
        inspection = SimpleNamespace(
            elements=[
                SimpleNamespace(kind="cell", element_id="xlsx:Blad1!B26", value="Total Pallet", writable=True),
                SimpleNamespace(kind="cell", element_id="xlsx:Blad1!C26", value=None, writable=True),
                SimpleNamespace(kind="formula", element_id="xlsx:Blad1!D26", value={"formula": "=SUM(D23:D25)"}, writable=False),
                SimpleNamespace(kind="cell", element_id="xlsx:Blad1!E26", value=None, writable=True),
                SimpleNamespace(kind="formula", element_id="xlsx:Blad1!F26", value={"formula": "=SUM(F23:F25)"}, writable=False),
            ]
        )

        manifest, _visible_text = _template_context(inspection)
        by_id = {item["element_id"]: item for item in manifest}

        self.assertFalse(by_id["xlsx:Blad1!C26"]["required"])
        self.assertTrue(by_id["xlsx:Blad1!C26"]["approved_to_skip"])
        self.assertFalse(by_id["xlsx:Blad1!E26"]["required"])
        self.assertTrue(by_id["xlsx:Blad1!E26"]["approved_to_skip"])

    def test_field_candidates_use_current_orm_rights_and_exclude_sensitive_fields(self):
        partner = self.env["res.partner"].create({"name": "Office tool target"})
        result = _field_candidates(self.env, partner)
        self.assertIn("name", result)
        self.assertIn("email", result)
        self.assertNotIn("password", result)

    def test_field_metadata_uses_dynamic_odoo_label_and_help(self):
        result = _field_metadata(
            self.env,
            "res.partner",
            {"contact_address": "string", "display_name": "string"},
        )
        field = self.env["res.partner"]._fields["contact_address"]
        self.assertEqual(result["contact_address"]["type"], "string")
        self.assertEqual(result["contact_address"]["label"], field.string)
        if field.help:
            self.assertEqual(result["contact_address"]["help"], field.help.strip()[:500])
        else:
            self.assertNotIn("help", result["contact_address"])
        self.assertEqual(
            result["display_name"]["label"],
            self.env["res.partner"]._fields["display_name"].string,
        )

    def test_template_context_exposes_merged_anchor_and_above_label(self):
        inspection = SimpleNamespace(
            elements=[
                SimpleNamespace(
                    kind="cell", element_id="xlsx:Sheet1!F16", value="订单号", writable=True
                ),
                SimpleNamespace(
                    kind="cell", element_id="xlsx:Sheet1!E17", value=None, writable=True,
                    merged_range="E17:H17",
                ),
            ]
        )
        manifest, _visible = _template_context(inspection)
        target = next(item for item in manifest if item["element_id"] == "xlsx:Sheet1!E17")
        self.assertEqual(target["merge_range"], "E17:H17")
        self.assertEqual(target["write_target"], "xlsx:Sheet1!E17")
        self.assertEqual(target["visual_labels"][0]["text"], "订单号")
        self.assertEqual(target["visual_labels"][0]["relation"], "above_merged_region")
        report = validate_user_revision(
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            [],
            manifest,
            {},
        )
        self.assertNotEqual(report.status, "invalid", report.to_dict())

    def test_template_context_marks_headers_read_only_and_exposes_data_row_labels(self):
        inspection = SimpleNamespace(
            format="xlsx",
            elements=[
                SimpleNamespace(
                    kind="cell", element_id="xlsx:Sheet1!A1", value="订单号", writable=False,
                    table_role="table_header", table_header="订单号",
                ),
                SimpleNamespace(
                    kind="cell", element_id="xlsx:Sheet1!B1", value="金额", writable=False,
                    table_role="table_header", table_header="金额",
                ),
                SimpleNamespace(
                    kind="cell", element_id="xlsx:Sheet1!A2", value=None, writable=True,
                    table_role="table_data", table_header="订单号",
                ),
                SimpleNamespace(
                    kind="cell", element_id="xlsx:Sheet1!B2", value=None, writable=True,
                    table_role="table_data", table_header="金额",
                ),
            ],
        )

        manifest, visible_text = _template_context(inspection)
        by_id = {item["element_id"]: item for item in manifest}
        self.assertFalse(by_id["xlsx:Sheet1!A1"]["writable"])
        self.assertFalse(by_id["xlsx:Sheet1!B1"]["writable"])
        self.assertEqual(by_id["xlsx:Sheet1!A1"]["table_role"], "table_header")
        self.assertTrue(by_id["xlsx:Sheet1!A2"]["writable"])
        self.assertEqual(by_id["xlsx:Sheet1!A2"]["table_role"], "table_data")
        self.assertEqual(by_id["xlsx:Sheet1!A2"]["table_header"], "订单号")
        self.assertEqual(visible_text[0]["text"], "订单号")

    def test_field_candidate_budget_is_shared_fairly_across_relations(self):
        # Reproduce the old failure: a large first relation exhausted the
        # global 500-field cap before later useful relations were considered.
        first_fields = {
            **{f"zz_field_{index:03d}": object() for index in range(600)},
            "name": object(),
            "password": object(),
        }
        second_fields = {"name": object(), "street": object()}
        models = {
            "first.model": SimpleNamespace(_fields=first_fields),
            "second.model": SimpleNamespace(_fields=second_fields),
        }

        class FakeEnv:
            def __getitem__(self, model_name):
                return models[model_name]

        target = SimpleNamespace(
            _fields={
                "a_first": SimpleNamespace(type="many2one", comodel_name="first.model"),
                "b_second": SimpleNamespace(type="many2one", comodel_name="second.model"),
                "name": SimpleNamespace(type="char"),
            },
            check_access=lambda _operation: None,
        )

        def authorized_field_type(record, field_name):
            if field_name.lower().split(".")[-1] == "password":
                return None
            if "." not in field_name:
                return "string" if field_name in record._fields else None
            return "string"

        with patch(
            "odoo.addons.office_engine_m2.services.chat_entrypoint._authorized_scalar_field_type",
            side_effect=authorized_field_type,
        ):
            result = _field_candidates(FakeEnv(), target)

        self.assertLessEqual(len(result), 500)
        self.assertIn("a_first.name", result)
        self.assertIn("b_second.name", result)
        self.assertNotIn("a_first.password", result)

    def test_nested_full_address_keeps_budget_ahead_of_large_one_hop_relation(self):
        nested_models = {
            f"x.large.leaf.{relation_index}": SimpleNamespace(
                _fields={
                    f"field_{field_index:03d}": SimpleNamespace(type="char")
                    for field_index in range(250)
                }
            )
            for relation_index in range(100)
        }
        large_model = SimpleNamespace(
            _fields={
                f"nested_{relation_index:03d}": SimpleNamespace(
                    type="many2one",
                    comodel_name=f"x.large.leaf.{relation_index}",
                )
                for relation_index in range(100)
            }
        )
        partner_model = SimpleNamespace(
            _fields={"contact_address": SimpleNamespace(type="char")}
        )
        warehouse_model = SimpleNamespace(
            _fields={
                "partner_id": SimpleNamespace(type="many2one", comodel_name="res.partner")
            }
        )
        models = {
            "x.large": large_model,
            "stock.warehouse": warehouse_model,
            "res.partner": partner_model,
            **nested_models,
        }

        class FakeEnv:
            def __getitem__(self, model_name):
                return models[model_name]

        target = SimpleNamespace(
            _name="sale.order",
            env=FakeEnv(),
            _fields={
                "name": SimpleNamespace(type="char"),
                "large_relation_id": SimpleNamespace(type="many2one", comodel_name="x.large"),
                "warehouse_id": SimpleNamespace(type="many2one", comodel_name="stock.warehouse"),
            },
            check_access=lambda _operation: None,
        )

        with patch(
            "odoo.addons.office_engine_m2.services.chat_entrypoint._authorized_scalar_field_type",
            side_effect=lambda _record, _field_name: "string",
        ):
            result = _field_candidates(FakeEnv(), target)

        self.assertLessEqual(len(result), 500)
        self.assertIn("warehouse_id.partner_id.contact_address", result)
