import ast

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..services.template import TemplateError, validate_structured_card_template, validate_template

class BusinessResource(models.Model):
    _name = "wd.gs.business.resource"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Business Resource"

    version_id = fields.Many2one("wd.gs.config.version", required=True, ondelete="cascade", index=True)
    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    composite = fields.Boolean(default=False)
    primary_model_id = fields.Many2one(
        "ir.model",
        string="Primary Model",
        help="The model searched by this single-model Resource. Composite Resources use Model Mappings instead.",
    )
    primary_model_name = fields.Char(related="primary_model_id.model")
    navigation_action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Result Form Action",
        ondelete="restrict",
        help="Window Action for the Primary Model. Its Form View and group restrictions are preserved.",
    )
    result_identity_scope = fields.Selection(
        [("resource", "Resource"), ("model", "Technical Model")],
        required=True,
        default="resource",
    )
    model_mapping_ids = fields.One2many("wd.gs.resource.model.mapping", "resource_id")
    searchable_field_ids = fields.One2many("wd.gs.searchable.field", "resource_id")
    relation_path_ids = fields.One2many("wd.gs.relation.path", "resource_id")
    business_date_ids = fields.One2many("wd.gs.business.date.mapping", "resource_id")
    state_mapping_ids = fields.One2many("wd.gs.state.mapping", "resource_id")
    snapshot_field_ids = fields.One2many("wd.gs.snapshot.field", "resource_id")
    card_template = fields.Text(
        string="Result Card Template",
        help="Plain-text template using constants and {field_name} variables.",
    )
    structured_card_title_template = fields.Text(
        string="Structured Card Title",
        help="Required title region; use the existing card template syntax.",
    )
    structured_card_meta_template = fields.Text(
        string="Structured Card Meta",
        help="Optional metadata region using the existing card template syntax.",
    )
    structured_card_summary_template = fields.Text(
        string="Structured Card Summary",
        help="Optional summary region using the existing card template syntax.",
    )
    structured_card_details_template = fields.Text(
        string="Structured Card Details",
        help="Optional details region with one One2many loop.",
    )
    card_many2many_separator = fields.Text(
        string="Result Card Many2many Separator",
        default=", ",
        help="Plain-text separator between values in Many2many template paths.",
    )

    _sql_constraints = [
        ("version_key_unique", "unique(version_id, key)", "Business resource keys must be unique per version."),
    ]

    def init(self):
        self.env.cr.execute(
            """
            UPDATE wd_gs_config_version AS version
               SET pending_changes = TRUE,
                   pending_global_changes = TRUE
             WHERE version.state IN ('published', 'retired')
               AND EXISTS (
                    SELECT 1
                      FROM wd_gs_business_resource AS resource
                      JOIN wd_gs_resource_model_mapping AS model_mapping
                        ON model_mapping.resource_id = resource.id
                     WHERE resource.version_id = version.id
                       AND resource.composite = FALSE
               )
            """
        )
        self.env.cr.execute(
            """
            UPDATE wd_gs_business_resource AS resource
               SET primary_model_id = ir_model.id
              FROM (
                    SELECT resource_id, MIN(model_name) AS model_name
                      FROM wd_gs_resource_model_mapping
                     GROUP BY resource_id
                    HAVING COUNT(*) = 1
                   ) AS legacy_mapping
              JOIN ir_model ON ir_model.model = legacy_mapping.model_name
             WHERE resource.id = legacy_mapping.resource_id
               AND resource.composite = FALSE
               AND resource.primary_model_id IS NULL
            """
        )
    def _validate_configuration(self):
        self.ensure_one()
        priorities = self.model_mapping_ids.mapped("priority")
        if len(priorities) != len(set(priorities)):
            raise ValidationError(_("Technical model priorities must be unique for %s.") % self.key)
        if not self.business_date_ids:
            raise ValidationError(_("Business Date is not configured for %s.") % self.key)
        structured_template = self._structured_card_template()
        if bool(self.card_template) == bool(structured_template):
            raise ValidationError(
                _(
                    "Configure exactly one Result Card template mode for %s."
                )
                % self.key
            )
        if not self.composite:
            if not self.primary_model_id or self.model_mapping_ids:
                raise ValidationError(
                    _("A single-model Resource must have a Primary Model and no Model Mappings.")
                )
            if not self.navigation_action_id:
                raise ValidationError(
                    _("A Form Action is required for single-model Resource %s.") % self.key
                )
            self._validate_navigation_action()
        elif (
            self.primary_model_id
            or len(self.model_mapping_ids) < 2
            or self.navigation_action_id
            or self.searchable_field_ids
        ):
            raise ValidationError(
                _("Composite Resources use Model Mappings and cannot define a Primary Model or single-model Action.")
            )
        model_names = (
            self.model_mapping_ids.mapped("model_name")
            if self.composite
            else [self.primary_model_id.model]
        )
        try:
            models = [self.env[name] for name in model_names]
            if structured_template:
                validate_structured_card_template(
                    structured_template,
                    models,
                    many2many_separator=self.card_many2many_separator or ", ",
                )
            else:
                validate_template(
                    self.card_template,
                    models,
                    many2many_separator=self.card_many2many_separator or ", ",
                )
        except TemplateError as exc:
            raise ValidationError(str(exc)) from exc
        for mapping in self.model_mapping_ids:
            mapping._validate_configuration()
        searchable_fields = (
            self.model_mapping_ids.mapped("searchable_field_ids")
            | self.searchable_field_ids
        )
        fields_by_model = (
            [
                (mapping.model_name, mapping.searchable_field_ids)
                for mapping in self.model_mapping_ids
            ]
            if self.composite
            else [(self.primary_model_id.model, self.searchable_field_ids)]
        )
        for model_name, model_fields in fields_by_model:
            if not model_fields.filtered(lambda item: item.searchable):
                raise ValidationError(
                    _(
                        "Resource %s model %s requires at least one searchable "
                        "field for multi-token search."
                    )
                    % (self.key, model_name)
                )
        direct_field_names = self.searchable_field_ids.filtered(
            lambda item: not item.mapping_id
        ).mapped("field_name")
        if len(direct_field_names) != len(set(direct_field_names)):
            raise ValidationError(_("Searchable fields must be unique per Primary Model."))
        for field in searchable_fields:
            field._validate_configuration()
        for path in self.relation_path_ids:
            path._validate_configuration()
        for business_date in self.business_date_ids:
            business_date._validate_configuration()

    def _validate_navigation_action(self):
        self.ensure_one()
        action = self.navigation_action_id
        model_name = self.primary_model_id.model
        if not model_name:
            raise ValidationError(_("Select a Primary Model before configuring its Form Action."))
        if action.type != "ir.actions.act_window":
            raise ValidationError(_("Result Action must be an Odoo Window Action."))
        if action.res_model != model_name:
            raise ValidationError(
                _("Result Action model must match Resource %s.") % self.key
            )
        if "form" not in (action.view_mode or "").split(","):
            raise ValidationError(_("Result Action must provide a Form View."))
        if action.target not in ("current", "main"):
            raise ValidationError(
                _("Result Action must open the Form in the current browser client.")
            )
        for expression in (action.context or "{}", action.domain or "[]"):
            try:
                expression_tree = ast.parse(expression, mode="eval")
            except SyntaxError as exc:
                raise ValidationError(
                    _("Result Action Context and Domain must be valid expressions.")
                ) from exc
            if any(
                isinstance(node, ast.Name)
                and node.id in {"active_id", "active_ids", "active_model"}
                for node in ast.walk(expression_tree)
            ):
                raise ValidationError(
                    _(
                        "Result Action Context and Domain cannot depend on "
                        "active_id, active_ids, or active_model."
                    )
                )
        form_action_views = action.view_ids.filtered(
            lambda item: item.view_mode == "form"
        )
        configured_view = (
            form_action_views[:1].view_id
            or (action.view_id if action.view_id.type == "form" else self.env["ir.ui.view"])
        )
        if configured_view and (
            configured_view.model != model_name or configured_view.type != "form"
        ):
            raise ValidationError(
                _("Result Action Form View must match Resource %s.") % self.key
            )
        try:
            view = self.env[model_name].get_view(
                view_id=configured_view.id if configured_view else False,
                view_type="form",
            )
        except (AccessError, UserError, ValidationError) as exc:
            raise ValidationError(
                _("Result Action Form View is unavailable for Resource %s.") % self.key
            ) from exc
        if not view.get("arch"):
            raise ValidationError(
                _("Result Action Form View is unavailable for Resource %s.") % self.key
            )

    def _navigation_action_snapshot(self):
        self.ensure_one()
        action = self.navigation_action_id
        if not action:
            return None
        form_action_views = action.view_ids.filtered(
            lambda item: item.view_mode == "form"
        )
        form_view = form_action_views[:1].view_id
        if not form_view and action.view_id.type == "form":
            form_view = action.view_id
        return {
            "id": action.id,
            "res_model": action.res_model,
            "view_mode": action.view_mode,
            "view_id": form_view.id or None,
            "target": action.target,
            "groups": sorted(action.groups_id.ids),
            "context": action.context or "{}",
            "domain": action.domain or "[]",
        }

    def _snapshot_values(self):
        self.ensure_one()
        languages = self.env["res.lang"].search([("active", "=", True)])

        def translated(value, field_name):
            result = {
                language.code: value.with_context(lang=language.code)[field_name]
                for language in languages
            }
            result.setdefault(
                "en_US",
                value.with_context(lang="en_US")[field_name]
                or value[field_name],
            )
            return result

        return {
            "key": self.key,
            "name": self.name,
            "name_translations": translated(self, "name"),
            "active": self.active,
            "composite": self.composite,
            "result_identity_scope": self.result_identity_scope,
            "navigation_action_id": self.navigation_action_id.id or None,
            "navigation_action": self._navigation_action_snapshot(),
            "models": (
                [
                    {
                        "model_name": self.primary_model_id.model,
                        "priority": 1,
                        "fields": [
                            {
                                "name": field.field_name,
                                "purpose": field.purpose,
                                "operator_set": field.operator_set,
                                "index_strategy": field.index_strategy,
                                "searchable": field.searchable,
                                "readable_required": field.readable_required,
                                "collection_match": field.collection_match,
                            }
                            for field in self.searchable_field_ids
                        ],
                    }
                ]
                if not self.composite
                else [
                    {
                        "model_name": mapping.model_name,
                        "priority": mapping.priority,
                        "fields": [
                            {
                                "name": field.field_name,
                                "purpose": field.purpose,
                                "operator_set": field.operator_set,
                                "index_strategy": field.index_strategy,
                                "searchable": field.searchable,
                                "readable_required": field.readable_required,
                                "collection_match": field.collection_match,
                            }
                            for field in mapping.searchable_field_ids
                        ],
                    }
                    for mapping in self.model_mapping_ids
                ]
            ),
            "relation_paths": [
                {"path": path.path, "max_depth": path.max_depth}
                for path in self.relation_path_ids
            ],
            "business_dates": [
                {
                    "model_name": item.model_name,
                    "field_name": item.field_name,
                    "timezone_behavior": item.timezone_behavior,
                    "empty_date_policy": item.empty_date_policy,
                }
                for item in self.business_date_ids
            ],
            "states": [
                {
                    "business_state": item.business_state,
                    "technical_values": item.technical_values,
                }
                for item in self.state_mapping_ids
            ],
            "card_template": self.card_template,
            **(
                {"structured_card_template": self._structured_card_template()}
                if self._structured_card_template()
                else {}
            ),
            "card_many2many_separator": self.card_many2many_separator or ", ",
            "snapshot_fields": [
                {
                    "field_name": item.field_name,
                    "label": item.label,
                    "labels": translated(item, "label"),
                    "sequence": item.sequence,
                    "visible": item.visible,
                    "format_type": item.format_type,
                    "allow_empty": item.allow_empty,
                }
                for item in self.snapshot_field_ids.sorted(
                    lambda field: (field.sequence, field.id)
                )
            ],
        }

    def _structured_card_template(self):
        self.ensure_one()
        values = {
            "title": self.structured_card_title_template or "",
            "meta": self.structured_card_meta_template or "",
            "summary": self.structured_card_summary_template or "",
            "details": self.structured_card_details_template or "",
        }
        if not any(values.values()):
            return None
        return {"schema_version": 1, **values}

    def action_use_structured_card_template(self):
        self.check_access("write")
        for resource in self:
            structured_template = resource._structured_card_template()
            if not structured_template:
                raise UserError(_("Configure the structured card regions before switching modes."))
            model_names = (
                resource.model_mapping_ids.mapped("model_name")
                if resource.composite
                else [resource.primary_model_id.model]
            )
            try:
                validate_structured_card_template(
                    structured_template,
                    [resource.env[name] for name in model_names],
                    many2many_separator=resource.card_many2many_separator or ", ",
                )
            except TemplateError as exc:
                raise ValidationError(str(exc)) from exc
            resource.write({"card_template": False})
        return True

    def action_use_legacy_card_template(self):
        self.check_access("write")
        for resource in self:
            if not resource.card_template:
                raise UserError(_("Configure the legacy card template before switching modes."))
            model_names = (
                resource.model_mapping_ids.mapped("model_name")
                if resource.composite
                else [resource.primary_model_id.model]
            )
            try:
                validate_template(
                    resource.card_template,
                    [resource.env[name] for name in model_names],
                    many2many_separator=resource.card_many2many_separator or ", ",
                )
            except TemplateError as exc:
                raise ValidationError(str(exc)) from exc
            resource.write(
                {
                    "structured_card_title_template": False,
                    "structured_card_meta_template": False,
                    "structured_card_summary_template": False,
                    "structured_card_details_template": False,
                }
            )
        return True

    def _legacy_card_template(self):
        self.ensure_one()
        visible_fields = self.snapshot_field_ids.filtered("visible").sorted(
            lambda item: (item.sequence, item.id)
        )
        if not visible_fields:
            return ""
        sequences = visible_fields.mapped("sequence")
        if any(sequence <= 0 for sequence in sequences) or len(sequences) != len(set(sequences)):
            raise ValidationError(
                _("Legacy Card fields need unique positive sequence values before migration.")
            )
        for item in visible_fields:
            item._validate_for_resource(self)
        if any(not item.allow_empty for item in visible_fields):
            raise ValidationError(
                _(
                    "Resource %s has Card fields whose empty-value behavior cannot be "
                    "represented by a template. Configure a template explicitly."
                )
                % self.key
            )
        lines = []
        for item in visible_fields:
            label = item.with_context(lang="en_US").label or item.label
            if "\\n" in label or "\\t" in label:
                raise ValidationError(
                    _(
                        "Legacy Card label %s contains an escape sequence that cannot be "
                        "migrated losslessly."
                    )
                    % item.field_name
                )
            label = label.replace("{", "{{").replace("}", "}}")
            model_names = item.allowed_model_names
            field_type = (
                self.env[model_names[0]]._fields.get(item.field_name)
                if model_names
                else None
            )
            format_key = item.format_type
            if format_key == "number" and field_type:
                format_key = {
                    "integer": "integer",
                    "float": "float",
                    "monetary": "monetary",
                }.get(field_type.type, "")
            if format_key in {"date", "datetime"}:
                variable = "{%s:%s}" % (item.field_name, format_key)
            elif format_key in {"integer", "float", "monetary"}:
                variable = "{%s:%s}" % (item.field_name, format_key)
            else:
                variable = "{%s}" % item.field_name
            lines.append("%s: %s" % (label, variable))
        return "\n".join(lines)
