import json

from odoo import http
from odoo.http import request

from ..services.provider import ConfigurationError
from ._shared import html_response as _html_response
from ._shared import json_response as _json_response
from ._shared import search_service as _search_service


class WorkspaceController(http.Controller):
    search_service = _search_service

    @http.route("/wd_global_search", type="http", auth="user")
    def workspace(self, **kwargs):
        try:
            descriptor_response = self.search_service.resource_descriptors(
                request.env, "global_search_baseline"
            )
        except ConfigurationError:
            return _json_response({"status": "CONFIGURATION_ERROR"}, status=503)
        resources = [
            {
                "key": resource["key"],
                "label": resource["label"],
                "states_json": json.dumps(
                    resource.get("states", []), ensure_ascii=False
                ),
                "searchable_fields_json": json.dumps(
                    resource.get("searchable_fields", []), ensure_ascii=False
                ),
            }
            for resource in descriptor_response["resources"]
        ]
        return _html_response(
            "wd_global_search.global_search_workspace_page",
            {
                "config_version": descriptor_response["config_version"],
                "user_timezone": request.env.user.tz or "UTC",
                "resources": resources,
            },
        )
