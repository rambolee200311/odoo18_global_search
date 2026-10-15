from types import SimpleNamespace

from odoo.tests.common import TransactionCase

from ..controllers.configuration import ConfigurationController


class TestTemplateFieldDescriptor(TransactionCase):
    def test_descriptor_reports_readability_and_group_restrictions(self):
        cases = (
            (None, False),
            ("base.group_user", True),
        )
        for groups, expected_restriction in cases:
            with self.subTest(groups=groups):
                descriptor = ConfigurationController._template_field_descriptor(
                    "name",
                    SimpleNamespace(
                        groups=groups,
                    ),
                    {"type": "char", "string": "Name"},
                )

                self.assertEqual(descriptor["name"], "name")
                self.assertEqual(descriptor["type"], "char")
                self.assertEqual(descriptor["label"], "Name")
                self.assertTrue(descriptor["readable"])
                self.assertEqual(
                    descriptor["group_restricted"], expected_restriction
                )
