import html
import json

from odoo import http
from odoo.http import request

from ..services.facade import SearchService
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
        resource_keys = {
            "res.partner": "contact",
            "sale.order": "sale_order",
            "stock.picking": "stock_picking",
        }
        tabs = "".join(
            (
                '<button class="wd-resource-tab" data-model="%s" data-resource="%s" '
                'data-testid="resource-%s">%s</button>'
            )
            % (
                html.escape(model),
                html.escape(resource_keys[model]),
                html.escape(model.replace(".", "-")),
                html.escape(config["label"]),
            )
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
    <form class="wd-query-bar" aria-label="Search">
      <label for="wd-query">Search query</label>
      <input id="wd-query" data-testid="search-query" type="search"
             placeholder="Search business records">
      <button id="wd-search-submit" data-testid="search-submit" type="submit">Search</button>
    </form>
    <nav class="wd-resource-tabs" aria-label="Business resources">
      <button class="wd-resource-tab" data-resource="" type="button">All</button>%s
    </nav>
    <section class="wd-refinements" aria-label="Refinement">
      <label>Date <select id="wd-date-refinement" data-testid="date-refinement">
        <option value="">Any time</option><option value="today">Today</option>
        <option value="this_week">This week</option><option value="this_month">This month</option>
      </select></label>
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
        <p class="wd-muted">Select a resource to load one record under your current Odoo permissions.</p>
        <div id="wd-result-list" data-testid="result-list"></div>
      </div>
      <aside class="wd-preview" data-testid="preview-pane" aria-live="polite">
        <div class="wd-preview-empty">Choose a record to preview it.</div>
      </aside>
    </section>
  </main>
  <script src="/wd_global_search/static/src/js/preview.js?v=cc005c"></script>
</body>
</html>""" % tabs
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
                "resource_counts": response.counts.get("by_resource", {}),
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
