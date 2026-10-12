from odoo.exceptions import AccessError

from .field_path import FieldPathError, validate_field_path


class AuthorizationError(Exception):
    def __init__(self, code, message="Permission boundary rejected the request"):
        super().__init__(message)
        self.code = code


def authorize_resource(env, resource, context):
    del context
    for mapping in resource.get("models", ()):
        model_name = mapping.get("model_name")
        if not model_name or model_name not in env:
            raise AuthorizationError("RESOURCE_NOT_ACCESSIBLE")
        model = env[model_name]
        try:
            model.check_access_rights("read")
        except AccessError as exc:
            raise AuthorizationError("RESOURCE_NOT_ACCESSIBLE") from exc
    return True


def authorize_fields(model, fields, context):
    del context
    readable = []
    for field_name in fields:
        if field_name not in model._fields:
            continue
        try:
            model.check_field_access_rights("read", [field_name])
        except AccessError:
            continue
        readable.append(field_name)
    if not readable:
        raise AuthorizationError("FIELD_NOT_READABLE")
    return readable


def authorize_searchable_fields(env, model, fields, context):
    del context
    readable = []
    for field_config in fields:
        if not isinstance(field_config, dict):
            raise AuthorizationError("CONFIGURATION_ERROR")
        if "searchable" in field_config and not isinstance(
            field_config["searchable"], bool
        ):
            raise AuthorizationError("CONFIGURATION_ERROR")
        if "readable_required" in field_config and not isinstance(
            field_config["readable_required"], bool
        ):
            raise AuthorizationError("CONFIGURATION_ERROR")
        if not field_config.get("searchable", True):
            continue
        field_name = field_config.get("name")
        if not isinstance(field_name, str):
            raise AuthorizationError("CONFIGURATION_ERROR")
        if "." in field_name and not {
            "operator_set",
            "index_strategy",
        }.issubset(field_config):
            raise AuthorizationError("CONFIGURATION_ERROR")
        try:
            resolved = validate_field_path(
                model,
                field_config.get("name"),
                operator_set=field_config.get("operator_set", "exact"),
                index_strategy=field_config.get("index_strategy", "none"),
                collection_match=field_config.get("collection_match", "any"),
            )
        except FieldPathError as exc:
            raise AuthorizationError("CONFIGURATION_ERROR") from exc
        if (
            resolved.collection_match_applicable
            and "collection_match" not in field_config
        ):
            raise AuthorizationError("CONFIGURATION_ERROR")

        current = model
        allowed = True
        for position, field_name in enumerate(resolved.segments):
            try:
                current.check_field_access_rights("read", [field_name])
            except AccessError:
                allowed = False
                break
            if position == len(resolved.segments) - 1:
                continue
            relation = current._fields[field_name]
            current = env[relation.comodel_name]
            try:
                current.check_access_rights("read")
            except AccessError:
                allowed = False
                break
        if allowed:
            readable.append(field_config)

    if not readable:
        raise AuthorizationError("FIELD_NOT_READABLE")
    return readable


def authorize_relation_path(env, resource, path, context):
    del context
    model_name = resource.get("models", [{}])[0].get("model_name")
    if not model_name:
        raise AuthorizationError("RELATION_PATH_BLOCKED")
    model = env[model_name]
    for field_name in path.split("."):
        field = model._fields.get(field_name)
        if field is None or field.type not in {"many2one", "one2many", "many2many"}:
            raise AuthorizationError("RELATION_PATH_BLOCKED")
        try:
            model.check_field_access_rights("read", [field_name])
        except AccessError as exc:
            raise AuthorizationError("RELATION_PATH_BLOCKED") from exc
        model = env[field.comodel_name]
        try:
            model.check_access_rights("read")
        except AccessError as exc:
            raise AuthorizationError("RELATION_PATH_BLOCKED") from exc
    return True
