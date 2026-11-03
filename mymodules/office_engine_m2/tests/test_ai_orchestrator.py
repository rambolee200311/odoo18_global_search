from types import SimpleNamespace
from uuid import uuid4

from odoo.tests import TransactionCase

from ..services import ai_orchestrator


class TestAuthorizedOfficeDataHelpers(TransactionCase):
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
