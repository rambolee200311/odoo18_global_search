from types import SimpleNamespace
from uuid import uuid4

from odoo.tests.common import TransactionCase

from ..services.executor import execute


class TestStructuredCardBackwardCompatibility(TransactionCase):
    def _resource(self):
        return {
            "key": "legacy_%s" % uuid4().hex,
            "models": [
                {"model_name": "res.partner", "fields": [{"name": "name"}]}
            ],
            "card_template": "Partner: {name}",
            "snapshot_fields": [
                {
                    "field_name": "name",
                    "label": "Name",
                    "labels": {"en_US": "Name"},
                    "sequence": 10,
                    "visible": True,
                    "format_type": "text",
                    "allow_empty": True,
                }
            ],
        }

    def _execute_partner(self, partner, resource, context=None):
        return execute(
            self.env,
            resource,
            SimpleNamespace(
                values=(
                    {
                        "dimension": "name",
                        "operator": "=",
                        "value": partner.name,
                    },
                )
            ),
            limit=1,
            context=context,
        )

    def test_plain_text_template_payload_is_unchanged(self):
        partner = self.env["res.partner"].create(
            {"name": "CC17-1 Legacy Template Fixture"}
        )
        resource = self._resource()

        outcome = self._execute_partner(partner, resource)

        result = next(item for item in outcome.results if item["id"] == partner.id)
        self.assertEqual(
            result["snapshot"],
            {"rendered_text": "Partner: CC17-1 Legacy Template Fixture"},
        )
        self.assertEqual(outcome.count, 1)

    def test_legacy_snapshot_fields_payload_is_unchanged(self):
        partner = self.env["res.partner"].create(
            {"name": "CC17-1 Legacy Fields Fixture"}
        )
        resource = self._resource()
        resource.pop("card_template")

        outcome = self._execute_partner(
            partner, resource, context=SimpleNamespace(lang=self.env.user.lang)
        )

        result = next(item for item in outcome.results if item["id"] == partner.id)
        self.assertEqual(
            result["snapshot"],
            {
                "fields": [
                    {
                        "field_name": "name",
                        "label": "Name",
                        "format": "text",
                        "value": "CC17-1 Legacy Fields Fixture",
                    }
                ]
            },
        )
        self.assertEqual(outcome.count, 1)
