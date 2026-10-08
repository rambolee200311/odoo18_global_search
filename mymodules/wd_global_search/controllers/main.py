import html
import json

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from ..services.facade import SearchService
from ..services.provider import ConfigurationError
from ..services.preview import MODEL_CONFIG, safe_preview
from ..services.types import SearchRequest


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
  <link rel="stylesheet" href="/wd_global_search/static/src/css/preview.css?v=cc012-v11">
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
  <script src="/wd_global_search/static/src/js/preview.js?v=cc012-v11"></script>
</body>
</html>""" % (html.escape(str(descriptor_response["config_version"]), quote=True), tabs)
        return request.make_response(page, headers=[("Content-Type", "text/html; charset=utf-8")])

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
    def form_url(self, model, record_id=None, **kwargs):
        action_refs = {
            "res.partner": "wd_global_search.action_gs_native_form_partner",
            "product.product": "wd_global_search.action_gs_native_form_product",
            "purchase.order": "wd_global_search.action_gs_native_form_purchase",
            "sale.order": "wd_global_search.action_gs_native_form_sale",
            "stock.picking": "wd_global_search.action_gs_native_form_picking",
        }
        if model not in action_refs:
            return _json_response({"status": "INVALID_REQUEST"}, status=400)
        try:
            record = request.env[model].browse(int(record_id)).exists()
            record.check_access_rule("read")
            action = request.env.ref(action_refs[model])
        except (AccessError, ValueError, MissingError):
            return _json_response(
                {"status": "PERMISSION_OR_DELETED"},
                status=403,
            )
        return _json_response(
            {
                "status": "SUCCESS",
                "url": "/web#id=%s&action=%s&model=%s&view_type=form"
                % (record.id, action.id, model),
            }
        )

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
