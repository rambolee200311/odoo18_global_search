from unittest import TestCase

from ..services.permission_boundary import (
    AuthorizationError,
    authorize_fields,
    authorize_relation_path,
    authorize_resource,
)


class FakeField:
    def __init__(self, field_type="char", comodel_name=None):
        self.type = field_type
        self.comodel_name = comodel_name


class FakeModel:
    def __init__(self, readable_fields, fields=None, access=True):
        self._readable_fields = set(readable_fields)
        self._fields = fields or {}
        self._access = access

    def check_access_rights(self, operation):
        if operation == "read" and not self._access:
            from odoo.exceptions import AccessError

            raise AccessError("denied")

    def check_field_access_rights(self, operation, fields):
        if operation == "read" and any(field not in self._readable_fields for field in fields):
            from odoo.exceptions import AccessError

            raise AccessError("field denied")


class FakeEnvironment(dict):
    def __getitem__(self, model_name):
        return super().__getitem__(model_name)


class TestPermissionBoundary(TestCase):
    def test_resource_access_rejects_inaccessible_model(self):
        env = FakeEnvironment({"sale.order": FakeModel((), access=False)})

        with self.assertRaises(AuthorizationError) as raised:
            authorize_resource(
                env,
                {"models": [{"model_name": "sale.order"}]},
                None,
            )

        self.assertEqual(raised.exception.code, "RESOURCE_NOT_ACCESSIBLE")

    def test_field_access_returns_only_readable_fields(self):
        model = FakeModel({"name"}, {"name": FakeField(), "secret": FakeField()})

        self.assertEqual(authorize_fields(model, ["name", "secret"], None), ["name"])

    def test_relation_path_rejects_non_relation_segments(self):
        env = FakeEnvironment(
            {
                "sale.order": FakeModel(
                    {"partner_id"},
                    {"partner_id": FakeField("many2one", "res.partner")},
                ),
                "res.partner": FakeModel({"name"}, {"name": FakeField()}),
            }
        )

        with self.assertRaises(AuthorizationError) as raised:
            authorize_relation_path(
                env,
                {"key": "sale_order", "models": [{"model_name": "sale.order"}]},
                "partner_id.name",
                None,
            )

        self.assertEqual(raised.exception.code, "RELATION_PATH_BLOCKED")

    def test_card_serializer_keeps_sequence_and_omits_unreadable_and_hidden_fields(self):
        from ..services.card import serialize_card_fields

        class CardField:
            def __init__(self, field_type="char"):
                self.type = field_type

        class CardModel:
            _fields = {
                "name": CardField(),
                "is_company": CardField("boolean"),
                "secret": CardField(),
                "hidden": CardField(),
            }

        class CardEnv(dict):
            pass

        resource = {
            "snapshot_fields": [
                {
                    "field_name": "secret",
                    "label": "Secret",
                    "labels": {"en_US": "Secret"},
                    "sequence": 20,
                    "visible": True,
                    "format_type": "text",
                    "allow_empty": True,
                },
                {
                    "field_name": "is_company",
                    "label": "Company",
                    "labels": {"en_US": "Company"},
                    "sequence": 15,
                    "visible": True,
                    "format_type": "text",
                    "allow_empty": False,
                },
                {
                    "field_name": "hidden",
                    "label": "Hidden",
                    "sequence": 5,
                    "visible": False,
                    "format_type": "text",
                },
                {
                    "field_name": "name",
                    "label": "Name",
                    "labels": {"en_US": "Name", "fr_FR": "Nom"},
                    "sequence": 10,
                    "visible": True,
                    "format_type": "text",
                    "allow_empty": False,
                },
            ]
        }
        values = {
            "name": "Acme",
            "is_company": False,
            "secret": "classified",
            "hidden": "internal",
        }

        fields = serialize_card_fields(
            CardEnv({"res.partner": CardModel()}),
            resource,
            "res.partner",
            values,
            {"name", "is_company"},
            type("Context", (), {"lang": "fr_FR"})(),
        )

        self.assertEqual(fields, [
            {
                "field_name": "name",
                "label": "Nom",
                "format": "text",
                "value": "Acme",
            },
            {
                "field_name": "is_company",
                "label": "Company",
                "format": "text",
                "value": "No",
            },
        ])
