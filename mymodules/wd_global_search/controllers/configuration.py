import secrets

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request

from ..services.card import read_card_values
from ..services.limiter import UserLimiter
from ..services.observability import log_event
from ..services.permission_boundary import AuthorizationError
from ..services.template import (
    TemplateError,
    render_template,
    template_read_field_names,
    validate_template,
)
from ._shared import html_response as _html_response
from ._shared import json_response as _json_response


_template_preview_limiter = UserLimiter(max_requests=60)
_PREVIEW_TOKEN_LIMIT = 100


def _many2many_separator(resource, supplied):
    if supplied is None:
        supplied = resource.card_many2many_separator
    return supplied or ", "


class ConfigurationController(http.Controller):
    def _require_template_manager(self):
        if not request.env.user.has_group("wd_global_search.group_config_manager"):
            raise AccessError("Configuration manager access is required.")

    def _template_resource(self, resource_id):
        self._require_template_manager()
        try:
            resource_id = int(resource_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid Resource.") from exc
        resource = request.env["wd.gs.business.resource"].search(
            [("id", "=", resource_id)], limit=1
        )
        if not resource:
            raise MissingError("Resource is unavailable.")
        resource.check_access("read")
        return resource

    @http.route(
        "/wd_global_search/card_templates",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def card_template_designer(self, resource_id=None, **kwargs):
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        return _html_response(
            "wd_global_search.card_template_designer_page",
            {
                "resource_id": resource.id,
                "resource_name": resource.display_name,
                "csrf_token": request.csrf_token(),
            },
        )

    @http.route(
        "/wd_global_search/card_templates/descriptor",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def card_template_descriptor(self, resource_id=None, **kwargs):
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        models = self._template_models(resource)
        template, migration_warning = self._resource_template_text(resource)
        common = None
        for model in models:
            field_names = []
            for name, field in model._fields.items():
                if (
                    field.type not in {
                        "char", "text", "html", "integer", "float", "date",
                        "datetime", "boolean", "selection", "many2one", "many2many",
                        "one2many", "monetary",
                    }
                    or not field.store
                    or field.related
                ):
                    continue
                try:
                    model.check_field_access_rights("read", [name])
                except AccessError:
                    continue
                field_names.append(name)
            fields_info = model.fields_get(field_names, ["string", "type"])
            current = {
                name: self._template_field_descriptor(
                    name, model._fields[name], values
                )
                for name, values in fields_info.items()
            }
            common = current if common is None else {
                name: {
                    **info,
                    "group_restricted": (
                        info["group_restricted"]
                        or current[name]["group_restricted"]
                    ),
                }
                for name, info in common.items()
                if name in current and current[name]["type"] == info["type"]
            }
        return _json_response(
            {
                "status": "SUCCESS",
                "resource_id": resource.id,
                "template": template,
                "migration_warning": migration_warning,
                "state": resource.version_id.state,
                "pending": resource.version_id.pending_changes,
                "models": [model._name for model in models],
                "many2many_separator": resource.card_many2many_separator or ", ",
                "fields": sorted((common or {}).values(), key=lambda item: item["name"]),
            }
        )

    @staticmethod
    def _template_field_descriptor(name, field, values):
        return {
            "name": name,
            "type": values["type"],
            "label": values.get("string", name),
            "readable": True,
            "group_restricted": bool(field.groups),
        }

    @staticmethod
    def _resource_template_text(resource):
        if resource.card_template:
            return resource.card_template, ""
        try:
            return resource._legacy_card_template(), ""
        except ValidationError as exc:
            return "", str(exc)

    @http.route(
        "/wd_global_search/card_templates/records",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def card_template_records(self, resource_id=None, query="", **kwargs):
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        if len(query or "") > 200:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        if not _template_preview_limiter.acquire(request.env.uid):
            log_event(
                "warning",
                "card_template.preview_rate_limited",
                {
                    "resource": resource.key,
                    "config_version": resource.version_id.version,
                    "status": "RATE_LIMITED",
                    "error_code": "RATE_LIMITED",
                    "retryable": True,
                },
            )
            return _json_response({"status": "RATE_LIMITED"}, status=429)
        try:
            options = []
            tokens = request.session.get("wd_gs_card_preview_records", {})
            for model in self._template_models(resource):
                try:
                    model.check_access("read")
                except AccessError:
                    continue
                records = model.name_search(query or "", operator="ilike", limit=20)
                for record_id, label in records:
                    token = secrets.token_urlsafe(24)
                    tokens[token] = (model._name, record_id, resource.id)
                    options.append(
                        {
                            "record_id": token,
                            "label": "%s — %s" % (model._description, label),
                        }
                    )
                    if len(tokens) >= _PREVIEW_TOKEN_LIMIT:
                        tokens.pop(next(iter(tokens)))
            request.session["wd_gs_card_preview_records"] = tokens
            return _json_response({"status": "SUCCESS", "records": options})
        finally:
            _template_preview_limiter.release(request.env.uid)

    @http.route(
        "/wd_global_search/card_templates/preview",
        type="http",
        auth="user",
        methods=["POST"],
    )
    def card_template_preview(
        self,
        resource_id=None,
        template=None,
        source=None,
        record_id=None,
        many2many_separator=None,
        csrf_token=None,
        **kwargs,
    ):
        del csrf_token
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        if not _template_preview_limiter.acquire(request.env.uid):
            log_event(
                "warning",
                "card_template.preview_rate_limited",
                {
                    "resource": resource.key,
                    "config_version": resource.version_id.version,
                    "status": "RATE_LIMITED",
                    "error_code": "RATE_LIMITED",
                    "retryable": True,
                },
            )
            return _json_response({"status": "RATE_LIMITED"}, status=429)
        try:
            template = template or ""
            models = self._template_models(resource)
            separator = _many2many_separator(resource, many2many_separator)
            parts = validate_template(
                template,
                models,
                check_permissions=False,
                many2many_separator=separator,
            )
            selected = None
            actual_source = source or "synthetic_example"
            if actual_source == "selected_readable_record":
                token = request.session.get("wd_gs_card_preview_records", {}).get(
                    record_id
                )
                if not token or token[2] != resource.id:
                    return _json_response({"status": "RECORD_UNAVAILABLE"}, status=403)
                selected = (request.env[token[0]], token[1])
            elif actual_source == "latest_readable_record":
                selected = self._latest_template_record(resource, models)
                if not selected:
                    actual_source = "synthetic_example"
            elif actual_source != "synthetic_example":
                return _json_response({"status": "INVALID_REQUEST"}, status=400)

            if selected:
                model, record_id = selected
                record = model.browse(record_id).exists()
                if not record:
                    return _json_response({"status": "RECORD_UNAVAILABLE"}, status=403)
                record.check_access("read")
                field_names = template_read_field_names(model, template)
                readable_fields = self._readable_template_fields(model, field_names)
                if readable_fields:
                    values, readable_fields = read_card_values(
                        record, readable_fields, template
                    )[0]
                else:
                    values = {}
            else:
                model = models[0]
                field_names = template_read_field_names(model, template)
                readable_fields = self._readable_template_fields(model, field_names)
                values = self._synthetic_template_values(
                    model, parts, readable_fields, request.env
                )
            rendered = render_template(
                request.env,
                model._name,
                values,
                readable_fields,
                template,
                unauthorized_placeholder="[无权访问]",
                many2many_separator=separator,
            )
            return _json_response(
                {
                    "status": "SUCCESS",
                    "rendered_plain_text": rendered,
                    "validation_errors": [],
                    "safe_preview_metadata": {
                        "source": actual_source,
                        "display_label": model._description,
                        "permission_warning": True,
                    },
                }
            )
        except TemplateError as exc:
            return _json_response(
                {
                    "status": "CONFIGURATION_ERROR",
                    "rendered_plain_text": "",
                    "validation_errors": [str(exc)],
                },
                status=400,
            )
        except (AccessError, AuthorizationError, MissingError):
            return _json_response({"status": "RECORD_UNAVAILABLE"}, status=403)
        except (UserError, ValidationError) as exc:
            return _json_response(
                {"status": "CONFIGURATION_ERROR", "message": str(exc)}, status=400
            )
        except (TypeError, ValueError, KeyError):
            log_event(
                "error",
                "card_template.preview_failed",
                {
                    "resource": resource.key,
                    "config_version": resource.version_id.version,
                    "status": "FAILED",
                    "error_code": "INTERNAL_ERROR",
                    "retryable": False,
                },
            )
            return _json_response({"status": "INTERNAL_ERROR"}, status=500)
        finally:
            _template_preview_limiter.release(request.env.uid)

    @http.route(
        "/wd_global_search/card_templates/check",
        type="http",
        auth="user",
        methods=["POST"],
    )
    def card_template_check(
        self,
        resource_id=None,
        template=None,
        many2many_separator=None,
        csrf_token=None,
        **kwargs,
    ):
        del csrf_token
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        models = self._template_models(resource)
        separator = _many2many_separator(resource, many2many_separator)
        try:
            validate_template(
                template or "",
                models,
                many2many_separator=separator,
            )
        except TemplateError as exc:
            return _json_response(
                {"status": "CONFIGURATION_ERROR", "message": str(exc)},
                status=400,
            )
        return _json_response({"status": "SUCCESS", "message": "Template structure is valid."})

    @http.route(
        "/wd_global_search/card_templates/save",
        type="http",
        auth="user",
        methods=["POST"],
    )
    def card_template_save(
        self,
        resource_id=None,
        template=None,
        many2many_separator=None,
        csrf_token=None,
        **kwargs,
    ):
        del csrf_token
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        template = template or ""
        separator = _many2many_separator(resource, many2many_separator)
        try:
            validate_template(
                template,
                self._template_models(resource),
                many2many_separator=separator,
            )
            resource.write(
                {
                    "card_template": template,
                    "card_many2many_separator": separator,
                }
            )
        except (TemplateError, ValidationError) as exc:
            log_event(
                "warning",
                "card_template.save_rejected",
                {
                    "resource": resource.key,
                    "config_version": resource.version_id.version,
                    "status": "FAILED",
                    "error_code": "CONFIGURATION_ERROR",
                    "retryable": False,
                },
            )
            return _json_response(
                {"status": "CONFIGURATION_ERROR", "message": str(exc)}, status=400
            )
        return _json_response(
            {
                "status": "SUCCESS",
                "pending": resource.version_id.pending_changes,
                "state": resource.version_id.state,
            }
        )

    @http.route(
        "/wd_global_search/card_templates/apply",
        type="http",
        auth="user",
        methods=["POST"],
    )
    def card_template_apply(self, resource_id=None, csrf_token=None, **kwargs):
        del csrf_token
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        result = resource.version_id.action_apply_changes()
        return _json_response(
            {
                "status": "SUCCESS" if not resource.version_id.pending_changes else "CONFIGURATION_ERROR",
                "pending": resource.version_id.pending_changes,
                "result": result,
            },
            status=200 if not resource.version_id.pending_changes else 400,
        )

    @staticmethod
    def _template_models(resource):
        names = (
            resource.model_mapping_ids.sorted(
                lambda item: (item.priority, item.model_name)
            ).mapped("model_name")
            if resource.composite
            else [resource.primary_model_name]
        )
        return [request.env[name] for name in names if name in request.env]

    @staticmethod
    def _readable_template_fields(model, field_names):
        readable = []
        for name in field_names:
            try:
                model.check_field_access_rights("read", [name])
            except AccessError:
                continue
            readable.append(name)
        return readable

    @staticmethod
    def _latest_template_record(resource, models):
        candidates = []
        for model in models:
            mapping = resource.business_date_ids.filtered(
                lambda item: item.model_name == model._name
            )[:1]
            date_field = mapping.field_name if mapping else (
                "write_date" if "write_date" in model._fields else "create_date"
            )
            if date_field not in model._fields:
                continue
            try:
                model.check_access("read")
                model.check_field_access_rights("read", [date_field])
                record = model.search(
                    [], order="%s desc, id desc" % date_field, limit=1
                )
            except AccessError:
                continue
            if record:
                candidates.append((record[date_field] or "", model._name, record.id))
        if not candidates:
            return None
        _, model_name, record_id = max(candidates)
        return request.env[model_name], record_id

    @staticmethod
    def _synthetic_template_values(model, parts, readable_fields, env):
        values = {}
        for part in parts:
            if not part.is_variable or part.field_name not in readable_fields:
                continue
            field = model._fields[part.field_name]
            if field.type in {"char", "text", "html"}:
                values[part.field_name] = "Example"
            elif field.type in {"integer", "float", "monetary"}:
                values[part.field_name] = 1234
                values["_currency_%s" % field.name] = env.company.currency_id
            elif field.type == "boolean":
                values[part.field_name] = True
            elif field.type == "date":
                values[part.field_name] = "2026-10-10"
            elif field.type == "datetime":
                values[part.field_name] = "2026-10-10 09:30:00"
            elif field.type == "selection":
                selection = model.fields_get([part.field_name])[part.field_name].get(
                    "selection", []
                )
                values[part.field_name] = selection[0][0] if selection else False
            elif field.type == "many2one":
                values[part.field_name] = "Example"
        return values
