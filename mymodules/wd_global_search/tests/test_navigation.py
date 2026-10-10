from uuid import uuid4

from odoo.tests.common import TransactionCase

from ..services.navigation import (
    SAFE_NAVIGATION_FAILURE,
    action_allowed_for_user,
    resolve_form_navigation,
)


class TestConfiguredNavigation(TransactionCase):
    def _published_resource(self):
        suffix = uuid4().hex
        domain = self.env["wd.gs.config.domain"].create(
            {"key": "navigation_%s" % suffix, "name": "Navigation Test"}
        )
        version = self.env["wd.gs.config.version"].create(
            {"domain_id": domain.id, "version": 1}
        )
        resource = self.env["wd.gs.business.resource"].create(
            {
                "version_id": version.id,
                "key": "partner_%s" % suffix,
                "name": "Partners",
                "primary_model_id": self.env["ir.model"].search(
                    [("model", "=", "res.partner")], limit=1
                ).id,
                "navigation_action_id": self.env.ref(
                    "wd_global_search.action_gs_native_form_partner"
                ).id,
            }
        )
        self.env["wd.gs.business.date.mapping"].create(
            {
                "resource_id": resource.id,
                "model_name": "res.partner",
                "field_name": "create_date",
            }
        )
        self.env["wd.gs.snapshot.field"].create(
            {
                "resource_id": resource.id,
                "field_name": "name",
                "label": "Name",
                "sequence": 10,
                "visible": True,
                "format_type": "text",
            }
        )
        version.action_publish()
        return resource

    def test_resolver_uses_published_action_and_existing_record(self):
        resource = self._published_resource()
        record = self.env["res.partner"].create({"name": "CC-013 navigation fixture"})

        result = resolve_form_navigation(
            self.env,
            resource.key,
            record.id,
            "navigation_%s" % resource.version_id.domain_id.key.split("_", 1)[1],
        )

        action = resource.navigation_action_id
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("/odoo/action-%s/%s" % (action.id, record.id), result["navigation_url"])
        self.assertIn("model=res.partner", result["navigation_url"])
        self.assertNotIn("javascript:", result["navigation_url"])

    def test_resolver_safely_rejects_unknown_resource_and_client_model(self):
        resource = self._published_resource()

        unknown = resolve_form_navigation(
            self.env,
            "unknown_resource",
            1,
            resource.version_id.domain_id.key,
        )
        invalid_key = resolve_form_navigation(
            self.env,
            {"resource_key": resource.key, "model": "res.users"},
            1,
            resource.version_id.domain_id.key,
        )

        self.assertEqual(unknown, SAFE_NAVIGATION_FAILURE)
        self.assertEqual(invalid_key, SAFE_NAVIGATION_FAILURE)

    def test_resolver_fails_closed_when_published_action_changes(self):
        resource = self._published_resource()
        record = self.env["res.partner"].create({"name": "CC-013 action drift fixture"})
        resource.navigation_action_id.write({"context": "{'search_default_customer': 1}"})

        result = resolve_form_navigation(
            self.env,
            resource.key,
            record.id,
            resource.version_id.domain_id.key,
        )

        self.assertEqual(result, SAFE_NAVIGATION_FAILURE)

    def test_action_group_restriction_is_enforced_for_current_user(self):
        class Groups(list):
            @property
            def ids(self):
                return list(self)

        allowed_user = type("User", (), {"groups_id": Groups([5])})()
        denied_user = type("User", (), {"groups_id": Groups([7])})()
        unrestricted_action = type("Action", (), {"groups_id": Groups()})()
        restricted_action = type("Action", (), {"groups_id": Groups([3, 5])})()

        self.assertTrue(action_allowed_for_user(unrestricted_action, denied_user))
        self.assertTrue(action_allowed_for_user(restricted_action, allowed_user))
        self.assertFalse(action_allowed_for_user(restricted_action, denied_user))
