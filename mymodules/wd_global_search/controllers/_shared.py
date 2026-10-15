import json

from odoo.http import request

from ..services.facade import SearchService


search_service = SearchService()


def json_response(payload, status=200):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


def html_response(template, values, status=200):
    response = request.render(template, values)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.status_code = status
    return response
