from datetime import date, datetime

from odoo.exceptions import AccessError, MissingError

from .permission_boundary import AuthorizationError, authorize_fields, authorize_resource


MODEL_CONFIG = {
    "res.partner": {
        "label": "Contacts",
        "fields": ("display_name", "ref", "email", "phone", "company_id"),
    },
    "sale.order": {
        "label": "Sales Orders",
        "fields": ("display_name", "name", "partner_id", "date_order", "state", "company_id"),
    },
    "stock.picking": {
        "label": "Transfers",
        "fields": ("display_name", "name", "partner_id", "scheduled_date", "state", "origin"),
    },
}


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, tuple):
        return value[1] if len(value) > 1 else (value[0] if value else False)
    return value


def load_preview(env, model_name, record_id=None):
    if model_name not in MODEL_CONFIG:
        raise ValueError("Unknown preview model")
    model = env[model_name]
    resource = {"key": model_name, "models": [{"model_name": model_name}]}
    authorize_resource(env, resource, None)
    configured_fields = MODEL_CONFIG[model_name]["fields"]
    fields = authorize_fields(model, configured_fields, None)
    record = model.browse(record_id) if record_id else model.search([], limit=1)
    if not record.exists():
        raise MissingError("Preview record is unavailable")
    available_fields = model.fields_get(fields)
    values = record.read(fields)[0]
    view_record = env["ir.ui.view"].search(
        [("model", "=", model_name), ("type", "=", "form")],
        order="priority,id",
        limit=1,
    )
    view = model.get_view(view_id=view_record.id or False, view_type="form")
    return {
        "status": "SUCCESS",
        "model": model_name,
        "record_id": record.id,
        "display_name": record.display_name,
        "fields": [
            {
                "name": field,
                "label": available_fields[field].get("string", field),
                "value": _json_value(values.get(field)),
                "type": available_fields[field].get("type", "unknown"),
                "readonly": True,
            }
            for field in fields
        ],
        "view_id": view_record.id,
        "view_loaded": bool(view.get("arch")),
        "readonly_policy": {
            "create": False,
            "edit": False,
            "delete": False,
            "save": False,
            "business_buttons": False,
            "chatter_post": False,
            "attachment_upload": False,
            "activity_actions": False,
        },
    }


def safe_preview(env, model_name, record_id=None):
    try:
        return load_preview(env, model_name, record_id)
    except (AccessError, AuthorizationError, MissingError):
        return {
            "status": "PERMISSION_OR_DELETED",
            "message": "Record unavailable or permission changed",
        }
