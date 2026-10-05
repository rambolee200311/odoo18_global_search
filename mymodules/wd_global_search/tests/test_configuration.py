from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from uuid import uuid4

from psycopg2 import IntegrityError


class TestGlobalSearchConfiguration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.domain_model = cls.env["wd.gs.config.domain"]
        cls.version_model = cls.env["wd.gs.config.version"]
        cls.resource_model = cls.env["wd.gs.business.resource"]
        cls.mapping_model = cls.env["wd.gs.resource.model.mapping"]
        cls.field_model = cls.env["wd.gs.searchable.field"]
        cls.date_model = cls.env["wd.gs.business.date.mapping"]

    def _create_draft(self, key="test"):
        key = "%s_%s" % (key, uuid4().hex)
        domain = self.domain_model.create({"key": key, "name": key})
        version = self.version_model.create({"domain_id": domain.id, "version": 1})
        resource = self.resource_model.create(
            {"version_id": version.id, "key": "partner", "name": "Partner"}
        )
        mapping = self.mapping_model.create(
            {"resource_id": resource.id, "model_name": "res.partner", "priority": 1}
        )
        self.field_model.create(
            {
                "mapping_id": mapping.id,
                "field_name": "name",
                "purpose": "identifier",
                "operator_set": "exact",
                "index_strategy": "btree",
            }
        )
        self.date_model.create(
            {"resource_id": resource.id, "model_name": "res.partner", "field_name": "create_date"}
        )
        return domain, version

    def test_publish_creates_canonical_snapshot_and_audit(self):
        domain, version = self._create_draft("publish")

        version.action_publish()

        self.assertEqual(version.state, "published")
        self.assertTrue(version.checksum)
        self.assertGreater(version.snapshot_size, 0)
        self.assertEqual(
            self.env["wd.gs.audit.event"].search_count(
                [("domain_id", "=", domain.id), ("action", "=", "publish")]
            ),
            1,
        )

    def test_published_version_is_immutable(self):
        _, version = self._create_draft("immutable")
        version.action_publish()

        with self.assertRaises(UserError):
            version.write({"version": 2})

    def test_invalid_configuration_is_rejected_without_publishing(self):
        domain = self.domain_model.create({"key": "invalid", "name": "Invalid"})
        version = self.version_model.create({"domain_id": domain.id, "version": 1})

        version.action_publish()
        self.assertEqual(version.state, "rejected")
        self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")
        self.assertFalse(
            self.version_model.search(
                [("domain_id", "=", domain.id), ("state", "=", "published")]
            )
        )

    def test_duplicate_configuration_keys_are_rejected(self):
        domain, version = self._create_draft("unique")
        duplicate = self.version_model.create({"domain_id": domain.id, "version": 2})

        with self.env.cr.savepoint(), self.assertRaises(IntegrityError):
            self.version_model.create({"domain_id": domain.id, "version": version.version})

        duplicate.unlink()

    def test_unsupported_schema_is_rejected(self):
        _, version = self._create_draft("schema")
        version.schema_version = 999

        version.action_publish()
        self.assertEqual(version.state, "rejected")

    def test_snapshot_contains_resource_configuration(self):
        _, version = self._create_draft("snapshot")
        snapshot = version._build_snapshot()

        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["resources"][0]["models"][0]["model_name"], "res.partner")
        self.assertEqual(snapshot["resources"][0]["models"][0]["fields"][0]["name"], "name")
