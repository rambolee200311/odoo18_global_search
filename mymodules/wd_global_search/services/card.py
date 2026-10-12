from datetime import date, datetime

from odoo import _
from odoo.exceptions import AccessError
from odoo.tools.misc import format_date, format_datetime, formatLang

from .permission_boundary import AuthorizationError, authorize_fields
from .template import (
    render_template,
    template_field_names,
    template_read_field_names,
)


def card_field_names(resource, model):
    if resource.get("card_template"):
        return [
            field_name
            for field_name in template_read_field_names(model, resource["card_template"])
            if field_name in model._fields
        ]
    return [
        item["field_name"]
        for item in sorted(
            resource.get("snapshot_fields", ()),
            key=lambda field: (field.get("sequence", 10), field.get("field_name", "")),
        )
        if item.get("visible", True) and item.get("field_name") in model._fields
    ]


def authorized_card_field_names(resource, model, context):
    configured_names = card_field_names(resource, model)
    if not configured_names:
        return []
    try:
        return authorize_fields(model, configured_names, context)
    except AuthorizationError as exc:
        if exc.code == "FIELD_NOT_READABLE":
            return []
        raise


def _is_empty(value, field_type):
    return (
        value is None
        or value == ""
        or (value is False and field_type != "boolean")
    )


def _text_value(value):
    if isinstance(value, (list, tuple)):
        return value[1] if len(value) > 1 else (value[0] if value else False)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _format_value(env, value, format_type, field_type):
    if field_type == "boolean":
        return _("Yes") if value else _("No")
    if format_type == "date":
        return format_date(env, value)
    if format_type == "datetime":
        return format_datetime(env, value)
    if format_type == "number":
        return formatLang(env, value)
    return _text_value(value)


def _field_label(field_config, lang):
    labels = field_config.get("labels")
    if isinstance(labels, dict):
        return labels.get(lang) or labels.get("en_US") or field_config.get("label", "")
    return field_config.get("label", "")


def serialize_card_fields(env, resource, model_name, values, readable_fields, context):
    configured = sorted(
        (
            item
            for item in resource.get("snapshot_fields", ())
            if item.get("visible", True)
            and item.get("field_name") in readable_fields
            and item.get("field_name") in values
            and item.get("field_name") in env[model_name]._fields
        ),
        key=lambda item: (item.get("sequence", 10), item.get("field_name", "")),
    )
    fields = []
    for item in configured:
        field_name = item["field_name"]
        if field_name not in readable_fields:
            continue
        value = values.get(field_name)
        field_type = env[model_name]._fields[field_name].type
        if _is_empty(value, field_type) and not item.get("allow_empty", True):
            continue
        fields.append(
            {
                "field_name": field_name,
                "label": _field_label(item, context.lang),
                "format": item.get("format_type", "text"),
                "value": "—" if _is_empty(value, field_type) else _format_value(
                    env, value, item.get("format_type", "text"), field_type
                ),
            }
        )
    return fields


def serialize_card_template(env, resource, model_name, values, readable_fields):
    return render_template(
        env,
        model_name,
        values,
        readable_fields,
        resource["card_template"],
    )


def read_card_values(records, field_names, template):
    model = records.env[records._name]
    template_names = set(template_field_names(template))
    relation_fields = {
        name: model._fields[name]
        for name in field_names
        if name in model._fields
        and model._fields[name].type == "many2one"
    }
    monetary_fields = {
        name: model._fields[name]
        for name in template_names
        if name in model._fields and model._fields[name].type == "monetary"
    }
    for field in monetary_fields.values():
        currency_name = field.currency_field
        if currency_name in model._fields and model._fields[currency_name].type == "many2one":
            relation_fields[currency_name] = model._fields[currency_name]

    fields_to_read = list(dict.fromkeys(field_names))
    for field in monetary_fields.values():
        if field.currency_field in model._fields:
            fields_to_read.append(field.currency_field)
    fields_to_read = list(dict.fromkeys(fields_to_read))
    readable_fields = []
    for name in fields_to_read:
        try:
            model.check_field_access_rights("read", [name])
        except AccessError:
            continue
        readable_fields.append(name)
    for monetary_name, monetary_field in monetary_fields.items():
        if monetary_field.currency_field not in readable_fields:
            readable_fields = [
                name for name in readable_fields if name != monetary_name
            ]

    relation_names = [name for name in relation_fields if name in readable_fields]
    scalar_names = [name for name in readable_fields if name not in relation_names]
    scalar_rows = records.read(scalar_names) if scalar_names else [
        {"id": record.id} for record in records
    ]
    relation_rows = (
        records.read(relation_names, load=False) if relation_names else [
            {"id": record.id} for record in records
        ]
    )
    relation_by_id = {row["id"]: row for row in relation_rows}
    result = []
    for scalar_row in scalar_rows:
        record_id = scalar_row["id"]
        values = dict(scalar_row)
        allowed = set(readable_fields)
        raw_relations = relation_by_id.get(record_id, {})
        for name in relation_names:
            relation_id = raw_relations.get(name)
            if not relation_id:
                values[name] = False
                continue
            relation = records.env[relation_fields[name].comodel_name].browse(relation_id)
            try:
                relation.check_access("read")
                label = relation.display_name
            except AccessError:
                values[name] = False
                allowed.discard(name)
                for monetary_name, monetary_field in monetary_fields.items():
                    if monetary_field.currency_field == name:
                        allowed.discard(monetary_name)
                continue
            if name in template_names:
                values[name] = label
            else:
                for monetary_name, monetary_field in monetary_fields.items():
                    if monetary_field.currency_field == name:
                        values["_currency_%s" % monetary_name] = relation
        result.append((values, allowed))
    return result
