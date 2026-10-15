import json

from odoo.tests.common import HttpCase, TransactionCase


EXPECTED_ROUTES = {
    "/wd_global_search": ("http", None, True),
    "/wd_global_search/card_templates": ("http", ("GET",), True),
    "/wd_global_search/card_templates/descriptor": ("http", ("GET",), True),
    "/wd_global_search/card_templates/records": ("http", ("GET",), True),
    "/wd_global_search/card_templates/preview": ("http", ("POST",), True),
    "/wd_global_search/card_templates/check": ("http", ("POST",), True),
    "/wd_global_search/card_templates/save": ("http", ("POST",), True),
    "/wd_global_search/card_templates/apply": ("http", ("POST",), True),
    "/wd_global_search/api/preview": ("http", None, True),
    "/wd_global_search/api/form_url": ("http", None, True),
    "/wd_global_search/open_result": ("http", ("GET",), True),
    "/wd_global_search/api/search": ("json", ("POST",), False),
    "/wd_global_search/api/cancel": ("json", ("POST",), False),
}


class TestControllerRouteRegistry(TransactionCase):
    def test_controller_routes_are_registered_once_with_expected_contract(self):
        routing_map = self.env["ir.http"].routing_map()
        rules_by_path = {}
        for rule in routing_map.iter_rules():
            if rule.rule in EXPECTED_ROUTES:
                rules_by_path.setdefault(rule.rule, []).append(rule)

        self.assertEqual(set(rules_by_path), set(EXPECTED_ROUTES))
        for path, (route_type, methods, csrf) in EXPECTED_ROUTES.items():
            with self.subTest(path=path):
                rules = rules_by_path[path]
                self.assertEqual(len(rules), 1, "route must not be duplicated")
                routing = rules[0].endpoint.routing
                self.assertEqual(routing.get("type"), route_type)
                self.assertEqual(routing.get("auth"), "user")
                actual_methods = routing.get("methods")
                if methods is None:
                    self.assertIsNone(actual_methods)
                else:
                    self.assertEqual(tuple(actual_methods), methods)
                default_csrf = route_type == "http"
                self.assertEqual(routing.get("csrf", default_csrf), csrf)


class TestControllerUnauthenticatedRoutes(HttpCase):
    def test_route_families_reject_unauthenticated_requests(self):
        http_requests = (
            ("GET", "/wd_global_search"),
            ("GET", "/wd_global_search/card_templates?resource_id=0"),
            (
                "GET",
                "/wd_global_search/card_templates/descriptor?resource_id=0",
            ),
            (
                "GET",
                "/wd_global_search/card_templates/records?resource_id=0",
            ),
            (
                "POST",
                "/wd_global_search/card_templates/preview",
            ),
            (
                "POST",
                "/wd_global_search/card_templates/check",
            ),
            (
                "POST",
                "/wd_global_search/card_templates/save",
            ),
            (
                "POST",
                "/wd_global_search/card_templates/apply",
            ),
            ("GET", "/wd_global_search/api/preview?model=unknown"),
            ("GET", "/wd_global_search/api/form_url"),
            (
                "GET",
                "/wd_global_search/open_result?resource_key=unknown&record_id=0",
            ),
        )
        for method, path in http_requests:
            with self.subTest(method=method, path=path):
                response = self.url_open(
                    path,
                    data={"resource_id": "0"} if method == "POST" else None,
                    allow_redirects=False,
                )
                self.assertIn(response.status_code, (302, 303))

        json_request = json.dumps(
            {"jsonrpc": "2.0", "method": "call", "params": {}}
        )
        for path in (
            "/wd_global_search/api/search",
            "/wd_global_search/api/cancel",
        ):
            with self.subTest(path=path):
                response = self.url_open(
                    path,
                    data=json_request,
                    headers={"Content-Type": "application/json"},
                    allow_redirects=False,
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("error", response.json())
