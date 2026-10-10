from urllib.parse import urlencode

from odoo.exceptions import AccessError, MissingError, UserError, ValidationError

from .permission_boundary import AuthorizationError, authorize_resource
from .provider import ConfigurationError, published_snapshot


SAFE_NAVIGATION_FAILURE = {
    "status": "PERMISSION_OR_DELETED",
    "message": "Record unavailable or permission changed",
}


def action_allowed_for_user(action, user):
    action_group_ids = set(action.groups_id.ids)
    return not action_group_ids or bool(action_group_ids.intersection(user.groups_id.ids))


def resolve_form_navigation(env, resource_key, record_id, domain_key):
    if not isinstance(resource_key, str) or not resource_key:
        return SAFE_NAVIGATION_FAILURE.copy()
    try:
        parsed_record_id = int(record_id)
    except (TypeError, ValueError):
        return SAFE_NAVIGATION_FAILURE.copy()
    if parsed_record_id <= 0:
        return SAFE_NAVIGATION_FAILURE.copy()

    try:
        snapshot_info = published_snapshot(env, domain_key)
    except ConfigurationError:
        return {"status": "CONFIGURATION_ERROR", "message": "Navigation unavailable"}

    resource = next(
        (
            item
            for item in snapshot_info["snapshot"].get("resources", ())
            if item.get("key") == resource_key
        ),
        None,
    )
    if not resource or not resource.get("active", True):
        return SAFE_NAVIGATION_FAILURE.copy()

    models = resource.get("models", ())
    action_id = resource.get("navigation_action_id")
    published_action = resource.get("navigation_action")
    if len(models) != 1 or not action_id or not isinstance(published_action, dict):
        return SAFE_NAVIGATION_FAILURE.copy()
    try:
        action_id = int(action_id)
    except (TypeError, ValueError):
        return SAFE_NAVIGATION_FAILURE.copy()
    model_name = models[0].get("model_name")
    if not model_name or model_name not in env:
        return SAFE_NAVIGATION_FAILURE.copy()

    try:
        authorize_resource(env, resource, None)
        model = env[model_name]
        model.check_access_rights("read")
        record = model.browse(parsed_record_id).exists()
        if not record:
            return SAFE_NAVIGATION_FAILURE.copy()
        record.check_access_rule("read")

        action = env["ir.actions.act_window"].browse(action_id).exists()
        if not action:
            return SAFE_NAVIGATION_FAILURE.copy()
        action.check_access_rights("read")
        action.check_access_rule("read")
        action_form_views = action.view_ids.filtered(
            lambda item: item.view_mode == "form"
        )
        form_view = action_form_views[:1].view_id
        if not form_view and action.view_id.type == "form":
            form_view = action.view_id
        live_action = {
            "id": action.id,
            "res_model": action.res_model,
            "view_mode": action.view_mode,
            "view_id": form_view.id or None,
            "target": action.target,
            "groups": sorted(action.groups_id.ids),
            "context": action.context or "{}",
            "domain": action.domain or "[]",
        }
        if (
            live_action != published_action
            or action.res_model != model_name
            or "form" not in (action.view_mode or "").split(",")
            or action.target not in ("current", "main")
        ):
            return SAFE_NAVIGATION_FAILURE.copy()
        if not action_allowed_for_user(action, env.user):
            return SAFE_NAVIGATION_FAILURE.copy()

        view = model.get_view(
            view_id=form_view.id if form_view else False,
            view_type="form",
        )
        if not view.get("arch"):
            return SAFE_NAVIGATION_FAILURE.copy()
    except (
        AccessError,
        AuthorizationError,
        MissingError,
        UserError,
        ValidationError,
        ValueError,
    ):
        return SAFE_NAVIGATION_FAILURE.copy()

    query = urlencode(
        {
            "action": action.id,
            "model": model_name,
            "resId": record.id,
        }
    )
    return {
        "status": "SUCCESS",
        "navigation_url": "/odoo/action-%s/%s?%s"
        % (action.id, record.id, query),
    }
