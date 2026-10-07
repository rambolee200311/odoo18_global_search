from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..services.upgrade import validate_published_versions


class TestUpgradePreflight(TransactionCase):
    def test_empty_database_passes(self):
        result = validate_published_versions(self.env)
        self.assertEqual(result, {"published_count": 0})

    def test_invalid_published_snapshot_fails_closed(self):
        domain = self.env["wd.gs.config.domain"].create({"key": "upgrade", "name": "Upgrade"})
        version = self.env["wd.gs.config.version"].create(
            {
                "domain_id": domain.id,
                "version": 1,
                "state": "published",
                "snapshot_json": "{}",
                "checksum": "invalid",
            }
        )
        with self.assertRaises(ValidationError):
            validate_published_versions(self.env)
        self.assertEqual(version.state, "published")
