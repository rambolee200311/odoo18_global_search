import html
import json
import secrets

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request

from ..services.card import read_card_values
from ..services.facade import SearchService
from ..services.limiter import UserLimiter
from ..services.navigation import resolve_form_navigation
from ..services.observability import log_event
from ..services.permission_boundary import AuthorizationError
from ..services.provider import ConfigurationError
from ..services.preview import MODEL_CONFIG, safe_preview
from ..services.template import (
    TemplateError,
    render_template,
    template_read_field_names,
    validate_template,
)
from ..services.types import SearchRequest


_template_preview_limiter = UserLimiter(max_requests=60)
_PREVIEW_TOKEN_LIMIT = 100


def _json_response(payload, status=200):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


class GlobalSearchController(http.Controller):
    search_service = SearchService()

    @http.route("/wd_global_search", type="http", auth="user")
    def workspace(self, **kwargs):
        try:
            descriptor_response = self.search_service.resource_descriptors(
                request.env, "global_search_baseline"
            )
        except ConfigurationError:
            return _json_response({"status": "CONFIGURATION_ERROR"}, status=503)
        descriptors = descriptor_response["resources"]
        tabs = "".join(
            (
                '<button class="wd-resource-tab" data-resource="%s" '
                'data-testid="resource-%s" aria-pressed="false">'
                '<span class="wd-resource-label">%s</span> '
                '<span class="wd-resource-count" data-count-for="%s">—</span></button>'
            )
            % tuple(
                html.escape(value)
                for value in (
                    resource["key"],
                    resource["key"],
                    resource["label"],
                    resource["key"],
                )
            )
            for resource in descriptors
        )
        page = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Global Search</title>
  <link rel="stylesheet" href="/wd_global_search/static/src/css/preview.css?v=cc013-v02">
</head>
<body>
  <main class="wd-workspace" data-testid="global-search-workspace"
        data-config-version="%s">
    <header class="wd-header">
      <div>
        <p class="wd-eyebrow">WD GLOBAL SEARCH</p>
        <h1>Search Workspace</h1>
      </div>
      <span class="wd-readonly-badge" data-testid="readonly-badge">READ ONLY SEARCH</span>
    </header>
    <form class="wd-query-bar" aria-label="Search">
      <label for="wd-query">Search query</label>
      <input id="wd-query" data-testid="search-query" type="search"
             placeholder="Search business records">
      <button id="wd-search-submit" data-testid="search-submit" type="submit">Search</button>
    </form>
    <nav id="wd-resource-tabs" class="wd-resource-tabs"
         aria-label="Business resources" hidden>%s
    </nav>
    <div class="wd-resource-empty" data-testid="resource-empty" hidden>
      <p>Select at least one Resource to show results.</p>
      <button id="wd-reselect-all" data-testid="reselect-all" type="button">
        Reselect all accessible resources
      </button>
    </div>
    <section class="wd-refinements" aria-label="Refinement">
      <label>Date preset <select id="wd-date-refinement" data-testid="date-refinement">
        <option value="">Any time</option><option value="today">Today</option>
        <option value="this_week">This week</option><option value="this_month">This month</option>
      </select></label>
      <label>From <input id="wd-date-start" data-testid="date-start" type="date"></label>
      <label>To (exclusive) <input id="wd-date-end" data-testid="date-end" type="date"></label>
      <label>State <select id="wd-state-refinement" data-testid="state-refinement">
        <option value="">Any state</option><option value="draft">Draft</option>
        <option value="sale">Confirmed</option><option value="done">Done</option>
      </select></label>
      <div id="wd-active-refinements" data-testid="active-refinements"></div>
    </section>
    <section class="wd-understanding" data-testid="query-understanding" aria-live="polite">
      <strong>Query Understanding</strong><span id="wd-effective-conditions">No conditions</span>
    </section>
    <section class="wd-layout">
      <div class="wd-results" data-testid="results-pane">
        <h2>Accessible records</h2>
        <p class="wd-muted">Select a result; double-click to open its configured Odoo form.</p>
        <div id="wd-result-list" data-testid="result-list"></div>
        <div class="wd-pagination" data-testid="pagination" hidden>
          <label>Rows per page
            <select id="wd-page-size" data-testid="page-size">
              <option value="10" selected>10</option>
              <option value="20">20</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </label>
          <span id="wd-page-summary" class="wd-page-summary"
                data-testid="page-summary" aria-live="polite"></span>
          <nav id="wd-page-controls" class="wd-page-controls"
               data-testid="page-controls" aria-label="Accessible records pages"></nav>
        </div>
      </div>
    </section>
  </main>
  <script src="/wd_global_search/static/src/js/preview.js?v=cc013-v07"></script>
</body>
</html>""" % (html.escape(str(descriptor_response["config_version"]), quote=True), tabs)
        return request.make_response(page, headers=[("Content-Type", "text/html; charset=utf-8")])

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
        page = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Card Template — %s</title>
  <link rel="stylesheet" href="/wd_global_search/static/src/css/template_designer.css">
</head>
<body>
  <main class="wd-template-designer-page"
        data-resource-id="%s"
        data-csrf-token="%s">
    <header class="wd-template-header">
      <div>
        <p><button id="wd-template-back" class="btn btn-secondary" type="button">Back to Resource</button></p>
        <h1>Card Template</h1>
        <p class="wd-template-resource-name">%s</p>
      </div>
      <div class="wd-template-actions">
        <button id="wd-template-save" class="btn btn-secondary" type="button">Save</button>
        <button id="wd-template-apply" class="btn btn-primary" type="button" disabled>Apply Changes</button>
      </div>
    </header>
    <p class="alert alert-warning" role="note">
      Preview uses your current configuration account permissions; other users may see different fields or records.
    </p>
    <p id="wd-template-message" class="wd-template-message" role="status" aria-live="polite"></p>
    <div class="wd-template-layout">
      <label class="wd-template-editor">
        <span>Template</span>
        <textarea id="wd-template-input" maxlength="8192" spellcheck="false"></textarea>
      </label>
      <section class="wd-template-preview">
        <h2>Live Preview</h2>
        <label>
          <span>Source</span>
          <select id="wd-template-source">
            <option value="latest_readable_record">Latest readable record</option>
            <option value="selected_readable_record">Select a readable record</option>
            <option value="synthetic_example">Synthetic example</option>
          </select>
        </label>
        <select id="wd-template-record" aria-label="Readable preview records" hidden></select>
        <pre id="wd-template-rendered" aria-live="polite"></pre>
      </section>
      <section class="wd-template-fields">
        <h2>Available fields</h2>
        <p>Drag a field into the template, or focus a field and press Enter to insert it.</p>
        <ul id="wd-template-fields" class="wd-template-fields-list" role="listbox"></ul>
      </section>
    </div>
  </main>
  <script src="/wd_global_search/static/src/js/template_designer_page.js"></script>
</body>
</html>""" % (
            html.escape(resource.display_name, quote=True),
            resource.id,
            html.escape(request.csrf_token(), quote=True),
            html.escape(resource.display_name, quote=True),
        )
        return request.make_response(
            page, headers=[("Content-Type", "text/html; charset=utf-8")]
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
                        "datetime", "boolean", "selection", "many2one", "monetary",
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
                name: {
                    "name": name,
                    "type": values["type"],
                    "label": values.get("string", name),
                }
                for name, values in fields_info.items()
            }
            common = current if common is None else {
                name: info
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
                "fields": sorted((common or {}).values(), key=lambda item: item["name"]),
            }
        )

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
            parts = validate_template(template, models, check_permissions=False)
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
        "/wd_global_search/card_templates/save",
        type="http",
        auth="user",
        methods=["POST"],
    )
    def card_template_save(
        self, resource_id=None, template=None, csrf_token=None, **kwargs
    ):
        del csrf_token
        if kwargs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        resource = self._template_resource(resource_id)
        template = template or ""
        try:
            validate_template(template, self._template_models(resource))
            resource.write({"card_template": template})
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
            else [resource.primary_model_id.model]
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

    @http.route("/wd_global_search/api/preview", type="http", auth="user")
    def preview(self, model, record_id=None, **kwargs):
        if model not in MODEL_CONFIG:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        try:
            parsed_id = int(record_id) if record_id else None
            return _json_response(safe_preview(request.env, model, parsed_id))
        except (TypeError, ValueError):
            return _json_response({"status": "INVALID_REQUEST"}, status=400)

    @http.route("/wd_global_search/api/form_url", type="http", auth="user")
    def form_url(self, resource_key=None, record_id=None, **kwargs):
        if kwargs or not resource_key or record_id is None:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        result = resolve_form_navigation(
            request.env,
            resource_key,
            record_id,
            "global_search_baseline",
        )
        if result["status"] != "SUCCESS":
            status = 503 if result["status"] == "CONFIGURATION_ERROR" else 403
            return _json_response(result, status=status)
        return _json_response(result)

    @http.route(
        "/wd_global_search/open_result",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def open_result(self, resource_key=None, record_id=None, **kwargs):
        if kwargs or not resource_key or record_id is None:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        result = resolve_form_navigation(
            request.env,
            resource_key,
            record_id,
            "global_search_baseline",
        )
        if result["status"] != "SUCCESS":
            status = 503 if result["status"] == "CONFIGURATION_ERROR" else 403
            message = html.escape(
                result.get("message", "Record unavailable or permission changed")
            )
            page = (
                "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<title>Record unavailable</title></head><body><main>"
                "<p>%s</p><a href=\"/wd_global_search\">Back to search</a>"
                "</main></body></html>"
            ) % message
            return request.make_response(
                page,
                headers=[("Content-Type", "text/html; charset=utf-8")],
                status=status,
            )
        return request.redirect(result["navigation_url"], code=303, local=True)

    @http.route("/wd_global_search/api/search", type="json", auth="user", methods=["POST"], csrf=False)
    def search(self, **kwargs):
        payload = kwargs.get("params", kwargs) if isinstance(kwargs, dict) else {}
        if not isinstance(payload, dict):
            return {"status": "FAILED", "errors": [{"code": "INVALID_REQUEST"}], "results": []}
        try:
            raw_query = payload.get("query", "")
            if isinstance(raw_query, str):
                raw_query = raw_query.strip()
            parsed_conditions = list(payload.get("conditions", ()))
            if isinstance(raw_query, str) and raw_query:
                parsed_conditions.append(
                    {"dimension": "name", "operator": "ilike", "value": raw_query}
                )
            search_request = SearchRequest(
                raw_query=raw_query,
                parsed_conditions=tuple(parsed_conditions),
                refinement_conditions=tuple(payload.get("refinement_conditions", ())),
                resource_scope=tuple(payload.get("resources", ())),
                offset=max(0, int(payload.get("offset", 0))),
                limit=int(payload.get("limit", 50)),
                cursor=payload.get("cursor"),
            )
            domain_key = payload.get("domain_key", "global_search_baseline")
            response = self.search_service.search(request.env, search_request, domain_key)
            visible_conditions = (
                []
                if any(item.get("code") == "INVALID_REQUEST" for item in response.errors)
                else [
                    *search_request.parsed_conditions,
                    *search_request.refinement_conditions,
                ]
            )
            return {
                "status": response.status,
                "request_id": response.request_id,
                "results": response.results,
                "counts": response.counts,
                "errors": response.errors,
                "resource_counts": response.meta.get("resource_counts", {}),
                "effective_conditions": visible_conditions,
                "next_cursor": response.meta.get("next_cursor"),
                "meta": response.meta,
            }
        except (TypeError, ValueError):
            return {
                "status": "FAILED",
                "request_id": None,
                "results": [],
                "counts": {"all": 0, "by_resource": {}},
                "errors": [{"code": "INTERNAL_ERROR", "retryable": False}],
                "meta": {},
            }

    @http.route("/wd_global_search/api/cancel", type="json", auth="user", methods=["POST"], csrf=False)
    def cancel(self, **kwargs):
        payload = kwargs.get("params", kwargs) if isinstance(kwargs, dict) else {}
        request_id = payload.get("request_id") if isinstance(payload, dict) else None
        return {
            "status": "CANCELLED"
            if self.search_service.cancel(request.env, request_id)
            else "FAILED"
        }
