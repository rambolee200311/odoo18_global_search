from odoo.exceptions import AccessError


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
