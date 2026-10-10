from datetime import date, datetime

from odoo import _
from odoo.tools.misc import format_date, format_datetime, formatLang

from .permission_boundary import AuthorizationError, authorize_fields


def card_field_names(resource, model):
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
