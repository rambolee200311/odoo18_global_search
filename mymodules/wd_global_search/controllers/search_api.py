from odoo import http
from odoo.http import request

from ..services.types import SearchRequest
from ._shared import search_service as _search_service


class SearchApiController(http.Controller):
    search_service = _search_service

    @http.route("/wd_global_search/api/search", type="json", auth="user", methods=["POST"], csrf=False)
    def search(self, **kwargs):
        payload = kwargs.get("params", kwargs) if isinstance(kwargs, dict) else {}
        if not isinstance(payload, dict):
            return {"status": "FAILED", "errors": [{"code": "INVALID_REQUEST"}], "results": []}
        try:
            raw_query = payload.get("query", "")
            parsed_conditions = list(payload.get("conditions", ()))
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
            visible_conditions = response.meta.get("effective_conditions", [])
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
