import html
import json
from datetime import date, datetime

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from ..services.facade import SearchService
from ..services.types import SearchRequest


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


def _json_response(payload, status=200):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, tuple):
        return value[1] if len(value) > 1 else (value[0] if value else False)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _read_preview(model_name, record_id=None):
    config = MODEL_CONFIG[model_name]
    model = request.env[model_name]
    model.check_access_rights("read")
    available_fields = model.fields_get(list(config["fields"]))
    fields = [field for field in config["fields"] if field in available_fields]
    record = model.browse(record_id) if record_id else model.search([], limit=1)
    if not record.exists():
        return {
            "status": "PERMISSION_OR_DELETED",
            "message": "Record unavailable or permission changed",
        }
    values = record.read(fields)[0]
    view_record = request.env["ir.ui.view"].search(
        [("model", "=", model_name), ("type", "=", "form")],
        order="priority,id",
        limit=1,
    )
    view = model.get_view(view_id=view_record.id or False, view_type="form")
    return {
        "status": "LOADED",
        "model": model_name,
        "record_id": record.id,
        "display_name": record.display_name,
        "fields": [
            {
                "name": field,
                "label": available_fields[field].get("string", field),
                "value": _json_value(values.get(field)),
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


class GlobalSearchController(http.Controller):
    search_service = SearchService()

    @http.route("/wd_global_search", type="http", auth="user")
    def workspace(self, **kwargs):
        tabs = "".join(
            (
                '<button class="wd-resource-tab" data-model="%s" '
                'data-testid="resource-%s">%s</button>'
            )
            % (html.escape(model), html.escape(model.replace(".", "-")), html.escape(config["label"]))
            for model, config in MODEL_CONFIG.items()
        )
        page = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Global Search</title>
  <link rel="stylesheet" href="/wd_global_search/static/src/css/preview.css">
</head>
<body>
  <main class="wd-workspace" data-testid="global-search-workspace">
    <header class="wd-header">
      <div>
        <p class="wd-eyebrow">WD GLOBAL SEARCH</p>
        <h1>Search Workspace</h1>
      </div>
      <span class="wd-readonly-badge" data-testid="readonly-badge">READ ONLY PREVIEW</span>
    </header>
    <section class="wd-query-bar" aria-label="Search">
      <label for="wd-query">Search query</label>
      <input id="wd-query" data-testid="search-query" type="search"
             placeholder="Search results are configured by the server" readonly>
      <button type="button" disabled aria-disabled="true">Search</button>
    </section>
    <nav class="wd-resource-tabs" aria-label="Business resources">%s</nav>
    <section class="wd-layout">
      <div class="wd-results" data-testid="results-pane">
        <h2>Accessible records</h2>
        <p class="wd-muted">Select a resource to load one record under your current Odoo permissions.</p>
        <div id="wd-result-list" data-testid="result-list"></div>
      </div>
      <aside class="wd-preview" data-testid="preview-pane" aria-live="polite">
        <div class="wd-preview-empty">Choose a record to preview it.</div>
      </aside>
    </section>
  </main>
  <script src="/wd_global_search/static/src/js/preview.js"></script>
</body>
</html>""" % tabs
        return request.make_response(page, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/wd_global_search/api/preview", type="http", auth="user")
    def preview(self, model, record_id=None, **kwargs):
        if model not in MODEL_CONFIG:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        try:
            parsed_id = int(record_id) if record_id else None
            return _json_response(_read_preview(model, parsed_id))
        except (AccessError, MissingError):
            return _json_response(
                {
                    "status": "PERMISSION_OR_DELETED",
                    "message": "Record unavailable or permission changed",
                }
            )
        except (TypeError, ValueError):
            return _json_response({"status": "INVALID_REQUEST"}, status=400)

    @http.route("/wd_global_search/api/search", type="json", auth="user", methods=["POST"], csrf=False)
    def search(self, **kwargs):
        payload = kwargs.get("params", kwargs) if isinstance(kwargs, dict) else {}
        if not isinstance(payload, dict):
            return {"status": "FAILED", "errors": [{"code": "INVALID_REQUEST"}], "results": []}
        try:
            search_request = SearchRequest(
                raw_query=payload.get("query", ""),
                parsed_conditions=tuple(payload.get("conditions", ())),
                refinement_conditions=tuple(payload.get("refinement_conditions", ())),
                resource_scope=tuple(payload.get("resources", ())),
                offset=max(0, int(payload.get("offset", 0))),
                limit=int(payload.get("limit", 50)),
                cursor=payload.get("cursor"),
            )
            domain_key = payload.get("domain_key", "global_search_baseline")
            response = self.search_service.search(request.env, search_request, domain_key)
            return {
                "status": response.status,
                "request_id": response.request_id,
                "results": response.results,
                "counts": response.counts,
                "errors": response.errors,
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
