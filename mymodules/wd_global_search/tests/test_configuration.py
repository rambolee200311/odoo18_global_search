import json

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase
from types import SimpleNamespace
from uuid import uuid4

from psycopg2 import IntegrityError
from ..services import executor
from ..services.provider import ConfigurationError, published_snapshot


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
            {
                "version_id": version.id,
                "key": "partner",
                "name": "Partner",
                "card_template": "Name: {name}",
                "primary_model_id": self.env["ir.model"].search(
                    [("model", "=", "res.partner")], limit=1
                ).id,
                "navigation_action_id": self.env.ref(
                    "wd_global_search.action_gs_native_form_partner"
                ).id,
            }
        )
        self.field_model.create(
            {
                "resource_id": resource.id,
                "field_name": "name",
                "purpose": "identifier",
                "operator_set": "exact",
                "index_strategy": "btree",
            }
        )
        self.date_model.create(
            {"resource_id": resource.id, "model_name": "res.partner", "field_name": "create_date"}
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

    def test_publish_accepts_explicit_structured_card_template(self):
        _, version = self._create_draft("structured_card")
        resource = version.resource_ids
        resource.write(
            {
                "card_template": False,
                "structured_card_title_template": "{name}",
                "structured_card_meta_template": "",
                "structured_card_summary_template": "",
                "structured_card_details_template": "",
            }
        )

        version.action_publish()
        snapshot_resource = json.loads(version.snapshot_json)["resources"][0]

        self.assertEqual(
            snapshot_resource["structured_card_template"],
            {
                "schema_version": 1,
                "title": "{name}",
                "meta": "",
                "summary": "",
                "details": "",
            },
        )
        self.assertFalse(snapshot_resource["card_template"])

    def test_publish_rejects_both_card_template_modes(self):
        _, version = self._create_draft("ambiguous_card_mode")
        version.action_publish()
        original_snapshot = version.snapshot_json
        original_checksum = version.checksum
        version.resource_ids.write(
            {"structured_card_title_template": "{name}"}
        )

        version.action_apply_changes()

        self.assertTrue(version.pending_changes)
        self.assertEqual(version.snapshot_json, original_snapshot)
        self.assertEqual(version.checksum, original_checksum)

    def test_published_card_mode_switch_applies_atomically(self):
        _, version = self._create_draft("structured_mode_switch")
        version.action_publish()
        original_checksum = version.checksum
        version.resource_ids.write(
            {
                "card_template": False,
                "structured_card_title_template": "{name}",
            }
        )

        version.action_apply_changes()

        self.assertFalse(version.pending_changes)
        self.assertNotEqual(version.checksum, original_checksum)
        snapshot_resource = json.loads(version.snapshot_json)["resources"][0]
        self.assertIn("structured_card_template", snapshot_resource)
        self.assertFalse(snapshot_resource["card_template"])

    def test_ui_structured_mode_switch_clears_legacy_template_after_validation(self):
        _, version = self._create_draft("ui_structured_mode_switch")
        version.action_publish()
        resource = version.resource_ids
        original_checksum = version.checksum
        resource.write(
            {
                "structured_card_title_template": "{name}",
                "structured_card_meta_template": "",
                "structured_card_summary_template": "",
                "structured_card_details_template": "",
            }
        )

        resource.action_use_structured_card_template()

        self.assertFalse(resource.card_template)
        self.assertTrue(version.pending_changes)
        self.assertEqual(version.checksum, original_checksum)
        version.action_apply_changes()
        self.assertFalse(version.pending_changes)
        snapshot_resource = json.loads(version.snapshot_json)["resources"][0]
        self.assertFalse(snapshot_resource["card_template"])
        self.assertEqual(
            snapshot_resource["structured_card_template"]["title"], "{name}"
        )

    def test_ui_structured_mode_switch_rejects_invalid_template_without_clearing_legacy(self):
        _, version = self._create_draft("ui_invalid_structured_mode_switch")
        resource = version.resource_ids
        resource.write({"structured_card_title_template": "{missing_field}"})

        with self.assertRaises(ValidationError):
            resource.action_use_structured_card_template()

        self.assertEqual(resource.card_template, "Name: {name}")

    def test_ui_legacy_mode_switch_clears_structured_template_after_validation(self):
        _, version = self._create_draft("ui_legacy_mode_switch")
        version.action_publish()
        resource = version.resource_ids
        original_checksum = version.checksum
        resource.write(
            {
                "structured_card_title_template": "{name}",
                "structured_card_meta_template": "Partner",
                "structured_card_summary_template": "",
                "structured_card_details_template": "",
            }
        )

        resource.action_use_legacy_card_template()

        self.assertEqual(resource.card_template, "Name: {name}")
        self.assertFalse(resource.structured_card_title_template)
        self.assertFalse(resource.structured_card_meta_template)
        self.assertFalse(resource.structured_card_summary_template)
        self.assertFalse(resource.structured_card_details_template)
        self.assertTrue(version.pending_changes)
        version.action_apply_changes()
        self.assertFalse(version.pending_changes)
        self.assertEqual(version.checksum, original_checksum)
        snapshot_resource = json.loads(version.snapshot_json)["resources"][0]
        self.assertEqual(snapshot_resource["card_template"], "Name: {name}")
        self.assertNotIn("structured_card_template", snapshot_resource)

    def test_ui_legacy_mode_switch_rejects_invalid_template_without_clearing_structured(self):
        _, version = self._create_draft("ui_invalid_legacy_mode_switch")
        resource = version.resource_ids
        resource.write(
            {
                "card_template": "{missing_field}",
                "structured_card_title_template": "{name}",
            }
        )

        with self.assertRaises(ValidationError):
            resource.action_use_legacy_card_template()

        self.assertEqual(resource.card_template, "{missing_field}")
        self.assertEqual(resource.structured_card_title_template, "{name}")

    def test_publish_accepts_contains_field_and_requires_searchable_field(self):
        _, version = self._create_draft("multi_token_exact_field")
        searchable_field = version.resource_ids.searchable_field_ids
        searchable_field.write(
            {
                "operator_set": "contains",
                "index_strategy": "gin_trgm",
            }
        )

        version._validate_configuration()

        searchable_field.write({"searchable": False})
        with self.assertRaises(ValidationError):
            version._validate_configuration()

    def test_version_identity_remains_protected(self):
        _, version = self._create_draft("identity")
        version.action_publish()

        with self.assertRaises(UserError):
            version.write({"version": 2})

    def test_navigation_action_rejects_active_record_context_and_domain(self):
        _, version = self._create_draft("active_record_action")
        resource = version.resource_ids
        action = resource.navigation_action_id.copy(
            {"context": "{'default_partner_id': active_id}"}
        )
        resource.navigation_action_id = action

        with self.assertRaises(ValidationError):
            resource._validate_navigation_action()

        action.write({"context": "{}", "domain": "[('id', '=', active_id)]"})
        with self.assertRaises(ValidationError):
            resource._validate_navigation_action()

    def test_published_edits_are_staged_until_applied(self):
        domain, version = self._create_draft("staged")
        version.action_publish()
        resource = version.resource_ids
        original_snapshot = version.snapshot_json
        original_checksum = version.checksum

        resource.write({"name": "Partner Records"})

        self.assertTrue(version.pending_changes)
        self.assertEqual(version.snapshot_json, original_snapshot)
        self.assertEqual(version.checksum, original_checksum)
        runtime_before_apply = published_snapshot(self.env, domain.key)
        self.assertEqual(runtime_before_apply["checksum"], original_checksum)
        self.assertEqual(runtime_before_apply["snapshot"]["resources"][0]["name"], "Partner")

        version.action_apply_changes()

        self.assertFalse(version.pending_changes)
        self.assertNotEqual(version.snapshot_json, original_snapshot)
        self.assertNotEqual(version.checksum, original_checksum)
        self.assertIn("Partner Records", version.snapshot_json)
        runtime_after_apply = published_snapshot(self.env, domain.key)
        self.assertEqual(runtime_after_apply["checksum"], version.checksum)
        self.assertEqual(
            runtime_after_apply["snapshot"]["resources"][0]["name"],
            "Partner Records",
        )
        applied_event = self.env["wd.gs.audit.event"].search(
            [("version_id", "=", version.id), ("action", "=", "apply")],
            limit=1,
        )
        self.assertEqual(applied_event.previous_checksum, original_checksum)
        self.assertEqual(applied_event.checksum, version.checksum)

    def test_many2many_separator_uses_the_published_snapshot_lifecycle(self):
        domain, version = self._create_draft("many2many_separator")
        version.action_publish()
        resource = version.resource_ids
        initial = published_snapshot(self.env, domain.key)
        initial_checksum = version.checksum
        self.assertEqual(
            initial["snapshot"]["resources"][0]["card_many2many_separator"],
            ", ",
        )

        resource.write({"card_many2many_separator": " | "})

        self.assertTrue(version.pending_changes)
        self.assertEqual(version.checksum, initial_checksum)
        self.assertEqual(
            published_snapshot(self.env, domain.key)["snapshot"]["resources"][0][
                "card_many2many_separator"
            ],
            ", ",
        )
        version.action_apply_changes()

        applied = published_snapshot(self.env, domain.key)
        self.assertEqual(
            applied["snapshot"]["resources"][0]["card_many2many_separator"],
            " | ",
        )
        self.assertNotEqual(version.checksum, initial_checksum)

    def test_invalid_relation_template_cannot_replace_published_snapshot(self):
        _, version = self._create_draft("invalid_relation_template")
        version.action_publish()
        resource = version.resource_ids
        original_snapshot = version.snapshot_json
        original_checksum = version.checksum
        resource.write({"card_template": "{name.name}"})

        result = version.action_apply_changes()

        self.assertEqual(result["tag"], "display_notification")
        self.assertTrue(version.pending_changes)
        self.assertEqual(version.snapshot_json, original_snapshot)
        self.assertEqual(version.checksum, original_checksum)

    def test_failed_apply_keeps_active_snapshot_and_pending_changes(self):
        _, version = self._create_draft("failed_apply")
        version.action_publish()
        resource = version.resource_ids
        original_snapshot = version.snapshot_json
        original_checksum = version.checksum
        resource.write(
            {
                "navigation_action_id": self.env.ref(
                    "wd_global_search.action_gs_native_form_sale"
                ).id
            }
        )

        version.action_apply_changes()

        self.assertTrue(version.pending_changes)
        self.assertEqual(version.snapshot_json, original_snapshot)
        self.assertEqual(version.checksum, original_checksum)
        self.assertTrue(
            self.env["wd.gs.audit.event"].search(
                [("version_id", "=", version.id), ("action", "=", "apply_rejected")]
            )
        )

    def test_domain_deactivation_is_staged_until_apply(self):
        domain, version = self._create_draft("domain_active")
        version.action_publish()
        domain.write({"active": False})

        self.assertTrue(domain.active)
        self.assertTrue(domain.pending_active_set)
        self.assertFalse(domain.pending_active)
        self.assertTrue(version.pending_changes)
        self.assertEqual(published_snapshot(self.env, domain.key)["version_id"], version.id)

        version.action_apply_changes()

        self.assertFalse(domain.active)
        self.assertFalse(domain.pending_active_set)
        with self.assertRaises(ConfigurationError):
            published_snapshot(self.env, domain.key)

    def test_non_manager_cannot_apply_configuration(self):
        _, version = self._create_draft("apply_acl")
        version.action_publish()
        version.resource_ids.write({"name": "Staged Partner"})
        user = self.env["res.users"].create(
            {
                "name": "Global Search Reader",
                "login": "gs-reader-%s" % uuid4().hex,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        with self.assertRaises(AccessError):
            version.with_user(user).action_apply_changes()

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
        self.assertEqual(
            snapshot["resources"][0]["navigation_action_id"],
            self.env.ref("wd_global_search.action_gs_native_form_partner").id,
        )
        self.assertEqual(
            snapshot["resources"][0]["navigation_action"]["res_model"],
            "res.partner",
        )
        self.assertEqual(snapshot["resources"][0]["snapshot_fields"][0]["sequence"], 10)
        self.assertTrue(snapshot["resources"][0]["snapshot_fields"][0]["visible"])
        self.assertEqual(snapshot["resources"][0]["card_template"], "Name: {name}")

    def test_explicit_card_template_is_staged_until_applied(self):
        domain, version = self._create_draft("card_template")
        version.action_publish()
        resource = version.resource_ids
        previous_checksum = version.checksum

        resource.write({"card_template": "Partner: {name}\nReference: {ref}"})

        self.assertTrue(version.pending_changes)
        self.assertEqual(version.checksum, previous_checksum)
        self.assertNotIn("Partner: {name}", version.snapshot_json)

        version.action_apply_changes()

        self.assertFalse(version.pending_changes)
        self.assertNotEqual(version.checksum, previous_checksum)
        self.assertIn("Partner: {name}\\nReference: {ref}", version.snapshot_json)
        self.assertEqual(
            published_snapshot(self.env, domain.key)["snapshot"]["resources"][0][
                "card_template"
            ],
            "Partner: {name}\nReference: {ref}",
        )

    def test_single_model_resource_uses_primary_model_and_direct_search_fields(self):
        _, version = self._create_draft("primary_model")
        resource = version.resource_ids

        self.assertEqual(resource.primary_model_id.model, "res.partner")
        self.assertEqual(resource.primary_model_name, "res.partner")
        self.assertFalse(resource.model_mapping_ids)
        self.assertEqual(resource.searchable_field_ids.field_name, "name")

    def test_multi_level_searchable_field_is_validated_and_snapshotted(self):
        _, version = self._create_draft("multi_level_field")
        resource = version.resource_ids
        field = self.field_model.create(
            {
                "resource_id": resource.id,
                "field_name": "category_id.parent_id.name",
                "purpose": "entity",
                "operator_set": "contains",
                "index_strategy": "gin_trgm",
                "collection_match": "all",
            }
        )

        field._validate_configuration()
        snapshot_fields = version._build_snapshot()["resources"][0]["models"][0][
            "fields"
        ]
        configured = next(
            item for item in snapshot_fields if item["name"] == field.field_name
        )

        self.assertEqual(configured["collection_match"], "all")
        self.assertTrue(configured["searchable"])
        self.assertTrue(configured["readable_required"])

    def test_multi_level_searchable_field_rejects_excess_collection_depth(self):
        _, version = self._create_draft("multi_level_invalid")
        resource = version.resource_ids
        field = self.field_model.create(
            {
                "resource_id": resource.id,
                "field_name": "category_id.parent_id.parent_id.name",
                "purpose": "entity",
                "operator_set": "contains",
                "index_strategy": "gin_trgm",
            }
        )

        with self.assertRaises(ValidationError):
            field._validate_configuration()

    def test_many2many_search_path_obeys_related_record_rules(self):
        suffix = uuid4().hex
        category_model = self.env["res.partner.category"]
        partner_model = self.env["res.partner"]
        visible_category = category_model.create({"name": "GS visible %s" % suffix})
        hidden_category = category_model.create({"name": "GS hidden %s" % suffix})
        partner_model.create(
            {
                "name": "GS visible partner %s" % suffix,
                "category_id": [(6, 0, [visible_category.id])],
            }
        )
        partner_model.create(
            {
                "name": "GS hidden partner %s" % suffix,
                "category_id": [(6, 0, [hidden_category.id])],
            }
        )

        internal_group = self.env.ref("base.group_user")
        user = self.env["res.users"].create(
            {
                "name": "GS path user %s" % suffix,
                "login": "gs_path_user_%s" % suffix,
                "groups_id": [(6, 0, [internal_group.id])],
                "company_ids": [(6, 0, self.env.company.ids)],
                "company_id": self.env.company.id,
            }
        )
        self.env["ir.rule"].create(
            {
                "name": "GS category visibility %s" % suffix,
                "model_id": self.env.ref("base.model_res_partner_category").id,
                "domain_force": "[('id', '=', %s)]" % visible_category.id,
                "groups": [(6, 0, [internal_group.id])],
            }
        )

        user_model = partner_model.with_user(user)

        def domain_for(value):
            return executor._condition_domain(
                user_model,
                [
                    {
                        "name": "category_id.name",
                        "operator_set": "exact",
                        "index_strategy": "btree",
                        "collection_match": "all",
                    }
                ],
                [],
                {},
                SimpleNamespace(
                    values=(
                        {
                            "dimension": "category_id.name",
                            "value": value,
                            "operator": "=",
                        },
                    )
                ),
                None,
            )

        self.assertEqual(
            user_model.search_count(domain_for(visible_category.name)), 1
        )
        self.assertEqual(
            user_model.search_count(domain_for(hidden_category.name)), 0
        )

    def test_stock_picking_relation_paths_keep_picking_as_result_model(self):
        _, version = self._create_draft("picking_relations")
        resource = version.resource_ids
        resource.write(
            {
                "primary_model_id": self.env["ir.model"].search(
                    [("model", "=", "stock.picking")], limit=1
                ).id,
                "navigation_action_id": self.env.ref(
                    "wd_global_search.action_gs_native_form_picking"
                ).id,
            }
        )
        resource.model_mapping_ids.searchable_field_ids.unlink()
        resource.business_date_ids.write(
            {"model_name": "stock.picking", "field_name": "scheduled_date"}
        )
        self.env["wd.gs.relation.path"].create(
            [
                {"resource_id": resource.id, "path": "move_ids.product_id"},
                {"resource_id": resource.id, "path": "move_line_ids.lot_id"},
            ]
        )

        resource._validate_configuration()
        snapshot_resource = version._build_snapshot()["resources"][0]

        self.assertEqual(snapshot_resource["models"][0]["model_name"], "stock.picking")
        self.assertEqual(snapshot_resource["card_template"], "Name: {name}")
        self.assertEqual(
            {path["path"] for path in snapshot_resource["relation_paths"]},
            {"move_ids.product_id", "move_line_ids.lot_id"},
        )
        self.env["stock.picking"].search(
            [
                ("move_ids.product_id.default_code", "ilike", "GS-PRODUCT"),
                ("move_line_ids.lot_id.name", "ilike", "GS-SERIAL"),
            ]
        )

    def test_composite_resource_maps_independent_result_models(self):
        _, version = self._create_draft("composite")
        resource = version.resource_ids
        resource.searchable_field_ids.unlink()
        resource.business_date_ids.unlink()
        resource.write(
            {
                "composite": True,
                "primary_model_id": False,
                "navigation_action_id": False,
            }
        )
        for priority, model_name in enumerate(("sale.order", "purchase.order"), 1):
            mapping = self.mapping_model.create(
                {
                    "resource_id": resource.id,
                    "model_name": model_name,
                    "priority": priority,
                }
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
                {
                    "resource_id": resource.id,
                    "model_name": model_name,
                    "field_name": "date_order",
                }
            )

        resource._validate_configuration()
        snapshot_models = version._build_snapshot()["resources"][0]["models"]

        self.assertEqual(
            [item["model_name"] for item in snapshot_models],
            ["sale.order", "purchase.order"],
        )

    def test_single_model_mapping_upgrade_migrates_to_primary_model(self):
        _, version = self._create_draft("legacy_mapping")
        resource = version.resource_ids
        mapping = self.mapping_model.create(
            {"resource_id": resource.id, "model_name": "res.partner", "priority": 1}
        )
        legacy_field = self.field_model.create(
            {
                "resource_id": resource.id,
                "mapping_id": mapping.id,
                "field_name": "email",
                "purpose": "text",
                "operator_set": "contains",
                "index_strategy": "none",
            }
        )

        resource.init()
        legacy_field.init()
        resource.invalidate_recordset()
        legacy_field.invalidate_recordset()

        self.assertEqual(resource.primary_model_id.model, "res.partner")
        self.assertFalse(resource.model_mapping_ids)
        self.assertEqual(legacy_field.resource_id, resource)
        self.assertFalse(legacy_field.mapping_id)

    def test_card_field_picker_resolves_field_from_resource_models(self):
        _, version = self._create_draft("card_field_selector")
        resource = version.resource_ids
        snapshot_field = resource.snapshot_field_ids
        field_reference = snapshot_field.field_reference_id

        self.assertEqual(snapshot_field.allowed_model_names, ["res.partner"])
        self.assertEqual(field_reference.model, "res.partner")
        self.assertEqual(field_reference.name, "name")
        self.assertEqual(field_reference.ttype, "char")

    def test_card_field_picker_uses_config_manager_metadata_acl(self):
        access = self.env["ir.model.access"].search(
            [
                ("model_id.model", "=", "ir.model.fields"),
                ("group_id", "=", self.env.ref("wd_global_search.group_config_manager").id),
            ],
            limit=1,
        )

        self.assertTrue(access.perm_read)
        self.assertFalse(access.perm_write)
        self.assertFalse(access.perm_create)
        self.assertFalse(access.perm_unlink)

    def test_publish_rejects_action_model_mismatch(self):
        _, version = self._create_draft("action_mismatch")
        resource = version.resource_ids
        resource.navigation_action_id = self.env.ref(
            "wd_global_search.action_gs_native_form_sale"
        )

        version.action_publish()

        self.assertEqual(version.state, "rejected")
        self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")

    def test_publish_rejects_unknown_template_variable(self):
        _, version = self._create_draft("unknown_template_variable")
        resource = version.resource_ids
        resource.card_template = "Name: {name}{unknown}"

        version.action_publish()

        self.assertEqual(version.state, "rejected")
        self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")

    def test_publish_rejects_navigation_action_with_dialog_target(self):
        _, version = self._create_draft("action_target")
        action = self.env.ref("wd_global_search.action_gs_native_form_partner")
        resource = version.resource_ids
        resource.navigation_action_id = action.copy(
            {"name": "Invalid dialog action", "target": "new"}
        )

        version.action_publish()

        self.assertEqual(version.state, "rejected")
        self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")

    def test_publish_rejects_missing_visible_card_field(self):
        _, version = self._create_draft("missing_card")
        version.resource_ids.card_template = False

        version.action_publish()

        self.assertEqual(version.state, "rejected")
        self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")

    def test_publish_rejects_incompatible_card_field_format(self):
        _, version = self._create_draft("card_format")
        version.resource_ids.card_template = "{name:date}"

        version.action_publish()

        self.assertEqual(version.state, "rejected")
        self.assertEqual(version.rejection_code, "CONFIGURATION_ERROR")
