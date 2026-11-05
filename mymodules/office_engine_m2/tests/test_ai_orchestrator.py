from types import SimpleNamespace
from uuid import uuid4

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from ..services import ai_orchestrator


class TestAuthorizedOfficeDataHelpers(TransactionCase):
    def test_related_record_rule_blocks_many2one_value_from_office_mapping(self):
        parent = self.env["res.partner"].create(
            {
                "name": "Hidden related partner " + uuid4().hex,
                "company_id": self.env.company.id,
            }
        )
        child = self.env["res.partner"].create(
            {
                "name": "Visible related child " + uuid4().hex,
                "parent_id": parent.id,
                "company_id": self.env.company.id,
            }
        )
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Office Related Field User " + uuid4().hex,
                "login": "office-related-field-" + uuid4().hex,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        # A global test-only rule makes the child readable but hides its
        # Many2one parent from this non-superuser. The TransactionCase rolls
        # back both the rule and records after the test.
        self.env["ir.rule"].create(
            {
                "name": "Office related-field test visibility " + uuid4().hex,
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": "[('id', '=', %d)]" % child.id,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        target = self.env["res.partner"].with_user(user).browse(child.id)
        self.assertEqual(target.exists().ids, [child.id])
        self.assertEqual(
            ai_orchestrator._scalar_field_path_status(target, "parent_id.name"),
            (None, "related_record_read_access_denied"),
        )
        session = SimpleNamespace(target_model="res.partner", target_record_id=child.id)
        with self.assertRaises(AccessError):
            ai_orchestrator._retrieve_record(target.env, session, ["parent_id.name"])

    def test_retriever_returns_acl_checked_many2one_name_and_street_values(self):
        parent = self.env["res.partner"].create(
            {
                "name": "Retriever customer " + uuid4().hex,
                "street": "42 Verified Road",
                "company_id": self.env.company.id,
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Retriever child " + uuid4().hex,
                "parent_id": parent.id,
                "company_id": self.env.company.id,
            }
        )
        session = SimpleNamespace(target_model="res.partner", target_record_id=partner.id)

        result = ai_orchestrator._retrieve_record(
            self.env,
            session,
            ["name", "parent_id.name", "parent_id.street"],
        )

        self.assertEqual(result["parent_id.name"], parent.name)
        self.assertEqual(result["parent_id.street"], "42 Verified Road")
        self.assertEqual(result["name"], partner.name)

    def test_target_label_context_keeps_merged_write_target_and_visual_label_distinct(self):
        manifest = [{
            "element_id": "xlsx:Sheet1!E17",
            "required": False,
            "merge_range": "E17:H17",
            "write_target": "xlsx:Sheet1!E17",
            "visual_labels": [{
                "element_id": "xlsx:Sheet1!F16",
                "text": "订单号",
                "relation": "above_merged_region",
            }],
        }]

        context = ai_orchestrator._target_label_context(manifest, [])

        self.assertEqual(context[0]["element_id"], "xlsx:Sheet1!E17")
        self.assertEqual(context[0]["write_target"], "xlsx:Sheet1!E17")
        self.assertEqual(context[0]["merge_range"], "E17:H17")
        self.assertEqual(context[0]["nearby_labels"][0]["text"], "订单号")
