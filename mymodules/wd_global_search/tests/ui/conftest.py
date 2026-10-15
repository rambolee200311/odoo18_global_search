import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from fixtures.orm_helpers import odoo_orm_call

DEFAULT_VIEWPORT = {"width": 1440, "height": 900}
AUTH_DIRECTORY = Path(__file__).resolve().parent / ".auth"
OPERATOR_STATE = AUTH_DIRECTORY / "operator.json"
ROLE_GROUPS = {
    "reader": ("base.group_user",),
    "status_reader": ("base.group_user", "sales_team.group_sale_salesman"),
    "fixture_writer": ("base.group_user", "base.group_partner_manager"),
    "restricted": ("base.group_portal",),
    "config_manager": ("base.group_user", "wd_global_search.group_config_manager"),
}


@pytest.fixture(scope="session")
def odoo_base_url():
    value = os.environ.get("ODOO_BASE_URL", "")
    if not value:
        pytest.fail("ODOO_BASE_URL must point to the local odoo18ce instance")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.port != 8091
        or parsed.path not in {"", "/"}
        or parsed.username
        or parsed.password
    ):
        pytest.fail("CC-018 UI tests are restricted to local Odoo on port 8091")
    return value.rstrip("/")


def _odoo_session_info(page, base_url):
    response = page.request.post(
        f"{base_url}/web/session/get_session_info",
        data={"jsonrpc": "2.0", "method": "call", "params": {}},
    )
    if response.status != 200:
        raise AssertionError(
            f"Odoo session info returned HTTP {response.status}"
        )
    payload = response.json()
    if "error" in payload or not isinstance(payload.get("result"), dict):
        raise AssertionError("Odoo session info could not be read")
    return payload["result"]


@pytest.fixture(scope="session")
def role_storage_states(playwright, odoo_base_url):
    if not OPERATOR_STATE.is_file():
        pytest.fail(
            "Create one protected operator login state with "
            "create_storage_state.py --role operator"
        )
    if stat.S_IMODE(OPERATOR_STATE.stat().st_mode) & 0o077:
        pytest.fail("Operator storage state must have file mode 0600")

    provisioning_browser = playwright.chromium.launch()
    operator_context = provisioning_browser.new_context(
        storage_state=str(OPERATOR_STATE)
    )
    operator_page = operator_context.new_page()
    marker = (
        f"CC018-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-"
        f"{uuid4()}"
    )
    created_users = []
    states = {}
    cleanup_errors = []

    try:
        operator_page.goto(f"{odoo_base_url}/web", wait_until="domcontentloaded")
        if "/web/login" in operator_page.url:
            pytest.fail("Operator storage state is not authenticated")
        session = _odoo_session_info(operator_page, odoo_base_url)
        if session.get("uid") == 1:
            pytest.fail("CC-018 test provisioning must not use the Odoo superuser")
        company_id = session.get("user_companies", {}).get("current_company")
        if not company_id:
            pytest.fail("Operator session has no current company")
        states["operator"] = operator_context.storage_state()
        user_context = session.get("user_context", {})
        language = user_context.get("lang", "en_US")
        timezone_name = user_context.get("tz", "UTC")

        for model, operation in (
            ("res.users", "create"),
            ("res.users", "unlink"),
            ("res.partner", "create"),
            ("res.partner", "unlink"),
        ):
            if not odoo_orm_call(
                operator_page,
                odoo_base_url,
                model,
                "check_access_rights",
                [operation, False],
            ):
                pytest.fail(
                    f"Operator lacks normal ORM {operation} access to {model}"
                )

        external_ids = [
            group
            for groups in ROLE_GROUPS.values()
            for group in groups
        ]
        group_modules = sorted(
            {group.split(".", 1)[0] for group in external_ids}
        )
        group_rows = odoo_orm_call(
            operator_page,
            odoo_base_url,
            "ir.model.data",
            "search_read",
            [[
                ["module", "in", group_modules],
                ["name", "in", [group.split(".", 1)[1] for group in external_ids]],
                ["model", "=", "res.groups"],
            ]],
            {"fields": ["module", "name", "res_id"], "limit": 20},
        )
        group_ids = {
            f"{row['module']}.{row['name']}": row["res_id"]
            for row in group_rows
        }
        if any(group not in group_ids for group in external_ids):
            pytest.fail("An existing Odoo role group required by CC-018 is unavailable")

        for role, group_xids in ROLE_GROUPS.items():
            login = f"{marker.lower()}-{role}"
            name = f"{marker} {role}"
            password = token_urlsafe(32)
            user_id = odoo_orm_call(
                operator_page,
                odoo_base_url,
                "res.users",
                "create",
                [{
                    "name": name,
                    "login": login,
                    "password": password,
                    "active": True,
                    "company_id": company_id,
                    "company_ids": [[6, 0, [company_id]]],
                    "groups_id": [[6, 0, [group_ids[group] for group in group_xids]]],
                    "lang": language,
                    "tz": timezone_name,
                }],
                {"context": {"no_reset_password": True}},
            )
            if not isinstance(user_id, int):
                raise AssertionError(f"Temporary {role} account creation failed")
            created_users.append(
                {"role": role, "login": login, "name": name, "id": user_id}
            )

            context = provisioning_browser.new_context()
            try:
                login_page = context.new_page()
                login_page.goto(
                    f"{odoo_base_url}/web/login",
                    wait_until="domcontentloaded",
                )
                login_page.locator('input[name="login"]').fill(login)
                login_page.locator('input[name="password"]').fill(password)
                login_page.get_by_role("button", name="Log in").click()
                login_page.wait_for_url(
                    lambda url: "/web/login" not in url,
                    timeout=15000,
                )
                states[role] = context.storage_state()
            finally:
                context.close()

        yield states
    finally:
        logins = [user["login"] for user in created_users]
        user_ids = [user["id"] for user in created_users]
        if user_ids:
            try:
                odoo_orm_call(
                    operator_page,
                    odoo_base_url,
                    "res.users",
                    "unlink",
                    [user_ids],
                )
            except Exception as exc:
                cleanup_errors.append(f"user cleanup: {type(exc).__name__}")

        try:
            partner_ids = odoo_orm_call(
                operator_page,
                odoo_base_url,
                "res.partner",
                "search",
                [[["name", "ilike", f"{marker}%"]]],
                {"limit": 100},
            )
            if partner_ids:
                odoo_orm_call(
                    operator_page,
                    odoo_base_url,
                    "res.partner",
                    "unlink",
                    [partner_ids],
                )
        except Exception as exc:
            cleanup_errors.append(f"partner cleanup: {type(exc).__name__}")

        try:
            remaining_users = (
                odoo_orm_call(
                    operator_page,
                    odoo_base_url,
                    "res.users",
                    "search_count",
                    [[["login", "in", logins]]],
                )
                if logins
                else 0
            )
            remaining_partners = odoo_orm_call(
                operator_page,
                odoo_base_url,
                "res.partner",
                "search_count",
                [[["name", "ilike", f"{marker}%"]]],
            )
            if remaining_users or remaining_partners:
                cleanup_errors.append(
                    f"cleanup verification: {remaining_users} user(s), "
                    f"{remaining_partners} partner(s) remain"
                )
        except Exception as exc:
            cleanup_errors.append(f"cleanup verification: {type(exc).__name__}")
        finally:
            try:
                operator_context.close()
            finally:
                provisioning_browser.close()

        if cleanup_errors:
            pytest.fail("; ".join(cleanup_errors))


@pytest.fixture
def page_factory(browser, role_storage_states):
    contexts = []

    def create_page(role="reader", viewport=None):
        context = browser.new_context(
            storage_state=role_storage_states[role],
            viewport=viewport or DEFAULT_VIEWPORT,
        )
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(type(error).__name__))
        contexts.append((context, page_errors))
        return page

    yield create_page

    failures = []
    for context, page_errors in reversed(contexts):
        context.close()
        if page_errors:
            failures.append(len(page_errors))
    if failures:
        pytest.fail(f"Browser pages raised {sum(failures)} unhandled JavaScript error(s)")


@pytest.fixture
def prepare_resource(odoo_base_url):
    def prepare(page, query, resource_key="contact"):
        page.goto(f"{odoo_base_url}/wd_global_search", wait_until="domcontentloaded")
        expect(page.get_by_test_id("global-search-workspace")).to_be_visible()

        page.get_by_test_id("search-query").fill(query)
        with page.expect_response(
            lambda response: response.url.endswith("/wd_global_search/api/search"),
            timeout=15000,
        ) as initial_info:
            page.get_by_test_id("search-submit").click()
        if initial_info.value.status != 200:
            raise AssertionError("Workspace resource initialization failed")
        payload = initial_info.value.json()
        result = payload.get("result") if isinstance(payload, dict) else None
        if not isinstance(result, dict):
            raise AssertionError("Workspace search returned an invalid response")
        if result.get("status") not in {"SUCCESS", "EMPTY"}:
            raise AssertionError(
                "Workspace search failed: "
                f"{result.get('status')} {result.get('errors', [])}"
            )

        resource = page.get_by_test_id(f"resource-{resource_key}")
        if not resource.count():
            return False
        if resource.get_attribute("aria-pressed") != "true":
            reselect = page.get_by_test_id("reselect-all")
            if reselect.is_visible():
                button = reselect
            elif resource.is_visible():
                button = resource
            else:
                return False
            with page.expect_response(
                lambda response: response.url.endswith(
                    "/wd_global_search/api/search"
                ),
                timeout=15000,
            ) as resource_info:
                button.click()
            if resource_info.value.status != 200:
                raise AssertionError(
                    f"Workspace resource selection failed for {resource_key}"
                )
        for index in range(page.locator(".wd-resource-tab").count()):
            button = page.locator(".wd-resource-tab").nth(index)
            key = button.get_attribute("data-resource")
            should_be_selected = key == resource_key
            is_selected = button.get_attribute("aria-pressed") == "true"
            if is_selected == should_be_selected:
                continue
            if not button.is_visible():
                continue
            with page.expect_response(
                lambda response: response.url.endswith(
                    "/wd_global_search/api/search"
                ),
                timeout=15000,
            ) as selection_info:
                button.click()
            if selection_info.value.status != 200:
                raise AssertionError(
                    f"Workspace resource selection failed for {key}"
                )
        return resource.get_attribute("aria-pressed") == "true"

    return prepare


@pytest.fixture
def workspace_page(page_factory, odoo_base_url):
    page = page_factory("reader")
    page.goto(f"{odoo_base_url}/wd_global_search", wait_until="domcontentloaded")
    workspace = page.get_by_test_id("global-search-workspace")
    if not workspace.is_visible():
        raise AssertionError(
            f"Workspace unavailable at {page.url}: "
            f"{page.locator('body').inner_text()[:500]}"
        )
    return page
