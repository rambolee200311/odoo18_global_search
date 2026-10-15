from odoo import http
from odoo.http import request

from ..services.navigation import resolve_form_navigation
from ..services.preview import MODEL_CONFIG, safe_preview
from ._shared import html_response as _html_response
from ._shared import json_response as _json_response


class NavigationController(http.Controller):
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
            return _html_response(
                "wd_global_search.navigation_error_page",
                {
                    "message": result.get(
                        "message", "Record unavailable or permission changed"
                    )
                },
                status=status,
            )
        return request.redirect(result["navigation_url"], code=303, local=True)
