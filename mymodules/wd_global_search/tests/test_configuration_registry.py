from odoo.tests.common import TransactionCase


class TestConfigurationModelRegistry(TransactionCase):
    def test_configuration_models_and_relations_are_registered(self):
        model_names = {
            "wd.gs.configuration.mutation.mixin",
            "wd.gs.config.domain",
            "wd.gs.config.version",
            "wd.gs.business.resource",
            "wd.gs.resource.model.mapping",
            "wd.gs.searchable.field",
            "wd.gs.relation.path",
            "wd.gs.business.date.mapping",
            "wd.gs.state.mapping",
            "wd.gs.snapshot.field",
            "wd.gs.vocabulary.entry",
            "wd.gs.entity.scoring.config",
            "wd.gs.performance.config",
            "wd.gs.audit.event",
        }
        models = {name: self.env[name] for name in model_names}
        self.assertEqual(
            {model._name for model in models.values()},
            model_names,
        )

        expected_fields = {
            "wd.gs.config.domain": {
                "key": ("char", None),
                "version_ids": ("one2many", "wd.gs.config.version"),
            },
            "wd.gs.config.version": {
                "domain_id": ("many2one", "wd.gs.config.domain"),
                "snapshot_json": ("text", None),
                "resource_ids": ("one2many", "wd.gs.business.resource"),
                "vocabulary_ids": ("one2many", "wd.gs.vocabulary.entry"),
            },
            "wd.gs.business.resource": {
                "version_id": ("many2one", "wd.gs.config.version"),
                "model_mapping_ids": (
                    "one2many",
                    "wd.gs.resource.model.mapping",
                ),
                "snapshot_field_ids": ("one2many", "wd.gs.snapshot.field"),
            },
            "wd.gs.resource.model.mapping": {
                "resource_id": ("many2one", "wd.gs.business.resource"),
                "searchable_field_ids": ("one2many", "wd.gs.searchable.field"),
            },
            "wd.gs.searchable.field": {
                "resource_id": ("many2one", "wd.gs.business.resource"),
                "mapping_id": ("many2one", "wd.gs.resource.model.mapping"),
            },
            "wd.gs.relation.path": {
                "resource_id": ("many2one", "wd.gs.business.resource"),
            },
            "wd.gs.business.date.mapping": {
                "resource_id": ("many2one", "wd.gs.business.resource"),
            },
            "wd.gs.state.mapping": {
                "resource_id": ("many2one", "wd.gs.business.resource"),
            },
            "wd.gs.snapshot.field": {
                "resource_id": ("many2one", "wd.gs.business.resource"),
            },
            "wd.gs.vocabulary.entry": {
                "version_id": ("many2one", "wd.gs.config.version"),
            },
            "wd.gs.entity.scoring.config": {
                "version_id": ("many2one", "wd.gs.config.version"),
            },
            "wd.gs.performance.config": {
                "version_id": ("many2one", "wd.gs.config.version"),
            },
            "wd.gs.audit.event": {
                "domain_id": ("many2one", "wd.gs.config.domain"),
                "version_id": ("many2one", "wd.gs.config.version"),
            },
        }
        for model_name, fields in expected_fields.items():
            for field_name, (field_type, comodel_name) in fields.items():
                field = models[model_name]._fields[field_name]
                self.assertEqual(field.type, field_type, (model_name, field_name))
                if comodel_name:
                    self.assertEqual(
                        field.comodel_name,
                        comodel_name,
                        (model_name, field_name),
                    )

    def test_configuration_lifecycle_methods_remain_registered(self):
        version = self.env["wd.gs.config.version"]
        for method_name in (
            "action_apply_changes",
            "action_validate",
            "action_publish",
            "action_retire",
            "_build_snapshot",
        ):
            self.assertTrue(
                callable(getattr(version, method_name, None)),
                method_name,
            )
