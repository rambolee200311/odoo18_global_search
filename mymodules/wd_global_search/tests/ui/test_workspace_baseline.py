import json
import os
import re

from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from fixtures.orm_helpers import contact_records, odoo_orm_call, sale_order_records


SEARCH_ENDPOINT = "/wd_global_search/api/search"
RESULT_CARDS = '[data-testid="result-list"] .wd-record-card'


def submit_search(page, query, odoo_base_url, expected_status=200):
    with page.expect_response(
        lambda response: response.url.endswith(SEARCH_ENDPOINT),
        timeout=15000,
    ) as response_info:
        search = page.get_by_test_id("search-query")
        search.fill(query)
        search.press("Enter")

    response = response_info.value
    assert response.status == expected_status
    return response


@pytest.mark.cc_test("CC-TEST-001")
def test_cc_test_001_authenticated_workspace(workspace_page):
    expect(workspace_page.get_by_role("heading", name="Search Workspace")).to_be_visible()
    expect(workspace_page.get_by_test_id("readonly-badge")).to_have_text(
        "READ ONLY SEARCH"
    )


@pytest.mark.cc_test("CC-TEST-002")
def test_cc_test_002_keyword_search(workspace_page, contact_records, prepare_resource):
    assert prepare_resource(workspace_page, contact_records["marker"])
    expect(workspace_page.locator(RESULT_CARDS)).to_have_count(10)
    expect(workspace_page.get_by_test_id("page-summary")).to_have_text(
        "Showing 1–10 of 12"
    )


@pytest.mark.cc_test("CC-TEST-003")
def test_cc_test_003_resource_selection(
    workspace_page, contact_records, odoo_base_url, prepare_resource
):
    assert prepare_resource(workspace_page, contact_records["marker"])
    resource = workspace_page.get_by_test_id("resource-contact")
    expect(resource).to_be_visible()
    expect(resource).to_have_attribute("aria-pressed", "true")

    resource.click()
    expect(resource).to_have_attribute("aria-pressed", "false")
    expect(workspace_page.get_by_test_id("resource-empty")).to_be_visible()

    workspace_page.get_by_test_id("reselect-all").click()
    expect(resource).to_have_attribute("aria-pressed", "true")
    submit_search(workspace_page, contact_records["marker"], odoo_base_url)
    expect(workspace_page.locator(RESULT_CARDS)).to_have_count(10)


@pytest.mark.cc_test("CC-TEST-004")
def test_cc_test_004_structured_condition(
    workspace_page, contact_records, prepare_resource
):
    assert prepare_resource(workspace_page, contact_records["marker"])
    workspace_page.get_by_test_id("condition-builder").locator("summary").click()

    field = workspace_page.get_by_test_id("condition-field")
    field.select_option(label="Email")
    operator = workspace_page.get_by_test_id("condition-operator")
    operator_values = [
        value
        for value in operator.locator("option").evaluate_all(
            "(options) => options.map((option) => option.value)"
        )
        if value
    ]
    assert operator_values, "Email field exposed no supported condition operator"
    preferred_operator = next(
        (value for value in operator_values if value in {"contains", "ilike"}),
        operator_values[0],
    )
    operator.select_option(value=preferred_operator)
    workspace_page.get_by_test_id("condition-value").fill(contact_records["emails"][0])
    workspace_page.get_by_test_id("condition-submit").click()
    workspace_page.get_by_test_id("query-understanding").locator("summary").click()
    structured_partition = workspace_page.get_by_test_id("structured-partition")
    expect(structured_partition).to_contain_text(
        contact_records["emails"][0]
    )

    structured_partition.get_by_role(
        "button", name="Edit condition for Email"
    ).click()
    workspace_page.get_by_test_id("condition-value").fill(contact_records["emails"][1])
    workspace_page.get_by_test_id("condition-submit").click()
    expect(structured_partition).to_contain_text(contact_records["emails"][1])
    structured_partition.get_by_role(
        "button", name="Remove condition for Email"
    ).click()
    expect(structured_partition).not_to_contain_text(contact_records["emails"][1])

    keyword_partition = workspace_page.get_by_test_id("keyword-partition")
    workspace_page.get_by_test_id("keyword-add").fill("Contact")
    workspace_page.get_by_test_id("keyword-add-submit").click()
    expect(
        keyword_partition.get_by_role("button", name="Edit keyword Contact")
    ).to_be_visible()
    expect(workspace_page.locator(RESULT_CARDS)).to_have_count(10)
    keyword_partition.get_by_role(
        "button", name="Edit keyword Contact"
    ).click()
    workspace_page.get_by_label("Edit keyword", exact=True).fill("NotInFixture")
    keyword_partition.get_by_role("button", name="Save").click()
    expect(
        keyword_partition.get_by_role("button", name="Edit keyword NotInFixture")
    ).to_be_visible()
    expect(workspace_page.locator(RESULT_CARDS)).to_have_count(0)
    keyword_partition.get_by_role(
        "button", name="Remove keyword NotInFixture"
    ).click()
    expect(
        keyword_partition.get_by_role("button", name="Edit keyword NotInFixture")
    ).to_have_count(0)
    expect(workspace_page.locator(RESULT_CARDS)).to_have_count(10)


@pytest.mark.cc_test("CC-TEST-005")
def test_cc_test_005_date_and_state_refinement(
    page_factory, sale_order_records, odoo_base_url, prepare_resource
):
    page = page_factory("status_reader")
    assert prepare_resource(page, sale_order_records["marker"], "sale_order")
    page.locator("summary").filter(
        has_text="Date and state filters"
    ).click()
    page.get_by_test_id("date-start").fill("2000-01-01")
    with page.expect_response(
        lambda response: response.url.endswith(SEARCH_ENDPOINT), timeout=15000
    ) as narrow_range_info:
        page.get_by_test_id("date-end").fill("2001-01-01")
    narrow_result = narrow_range_info.value.json().get("result", {})
    assert narrow_result.get("counts", {}).get("all") == 0, {
        key: narrow_result.get(key)
        for key in ("status", "counts", "errors", "effective_conditions")
    }
    expect(page.get_by_test_id("date-refinement")).to_have_value("")
    expect(page.locator(RESULT_CARDS)).to_have_count(0)
    expect(page.get_by_test_id("page-summary")).to_have_text("0 records")
    with page.expect_response(
        lambda response: response.url.endswith(SEARCH_ENDPOINT), timeout=15000
    ) as broad_range_info:
        page.get_by_test_id("date-end").fill("2100-01-01")
    broad_result = broad_range_info.value.json().get("result", {})
    broad_request = broad_range_info.value.request.post_data_json.get("params", {})
    assert broad_result.get("counts", {}).get("all") == 2, {
        key: broad_result.get(key)
        for key in ("status", "counts", "errors", "effective_conditions")
    } | {"request_resources": broad_request.get("resources")}
    expect(page.locator(RESULT_CARDS)).to_have_count(2)
    expect(page.get_by_test_id("page-summary")).to_have_text("Showing 1–2 of 2")
    page.get_by_test_id("date-start").fill("2100-01-01")
    page.get_by_test_id("date-end").fill("2000-01-01")
    date_message = page.locator("#wd-date-message")
    expect(date_message).to_be_visible()
    expect(date_message).to_have_text("The To date must be after the From date.")
    expect(page.locator(RESULT_CARDS)).to_have_count(2)

    state_refinement = page.get_by_test_id("state-refinement")
    expect(state_refinement).to_be_enabled()
    with page.expect_response(
        lambda response: response.url.endswith(SEARCH_ENDPOINT), timeout=15000
    ) as quotation_info:
        state_refinement.select_option(label="Quotation")
    quotation_result = quotation_info.value.json().get("result", {})
    assert quotation_result.get("counts", {}).get("all") == 1
    expect(page.locator(RESULT_CARDS)).to_contain_text(
        sale_order_records["quotation"]
    )

    with page.expect_response(
        lambda response: response.url.endswith(SEARCH_ENDPOINT), timeout=15000
    ) as cancelled_info:
        state_refinement.select_option(label="Cancelled")
    cancelled_result = cancelled_info.value.json().get("result", {})
    assert cancelled_result.get("counts", {}).get("all") == 1
    expect(page.locator(RESULT_CARDS)).to_contain_text(
        sale_order_records["cancelled"]
    )


@pytest.mark.cc_test("CC-TEST-006")
def test_cc_test_006_pagination(workspace_page, contact_records, prepare_resource):
    assert prepare_resource(workspace_page, contact_records["marker"])
    expect(workspace_page.get_by_test_id("page-summary")).to_have_text(
        "Showing 1–10 of 12"
    )
    first_page = set(
        workspace_page.locator("[data-testid='result-list'] .wd-card-title").all_text_contents()
    )

    with workspace_page.expect_response(
        lambda response: response.url.endswith(SEARCH_ENDPOINT), timeout=15000
    ):
        workspace_page.get_by_test_id("page-controls").get_by_role(
            "button", name="Next"
        ).click()
    expect(workspace_page.get_by_test_id("page-summary")).to_have_text(
        "Showing 11–12 of 12"
    )
    second_page = set(
        workspace_page.locator("[data-testid='result-list'] .wd-card-title").all_text_contents()
    )
    assert len(first_page) == 10
    assert len(second_page) == 2
    assert first_page.isdisjoint(second_page)
    assert first_page | second_page == set(contact_records["names"])


@pytest.mark.cc_test("CC-TEST-007")
def test_cc_test_007_structured_card_and_navigation(
    workspace_page, contact_records, odoo_base_url, prepare_resource
):
    assert prepare_resource(workspace_page, contact_records["marker"])
    card = workspace_page.locator(RESULT_CARDS).first
    expect(card.locator(".wd-card-title")).to_be_visible()
    expect(card.locator(".wd-card-meta")).to_be_attached()
    expect(card.locator(".wd-card-summary")).to_be_attached()
    link = card.locator("a.wd-card-open")
    href = link.get_attribute("href")
    assert href and href.startswith(
        "/wd_global_search/open_result?resource_key=contact&record_id="
    )
    expected_record_id = parse_qs(urlsplit(href).query)["record_id"][0]
    assert odoo_orm_call(
        workspace_page,
        odoo_base_url,
        "res.partner",
        "search",
        [[["id", "=", int(expected_record_id)]]],
        {"limit": 1},
    ), "Reader cannot access the partner result selected for navigation"

    with workspace_page.context.expect_page() as page_info:
        card.dblclick()
    record_page = page_info.value
    try:
        record_page.wait_for_load_state("domcontentloaded")
        opened_url = urlsplit(record_page.url)
        assert opened_url.path.startswith("/odoo/"), (
            f"Navigation stopped at {record_page.url}: "
            f"{record_page.locator('body').inner_text()}"
        )
        query = parse_qs(opened_url.query)
        assert query.get("model") == ["res.partner"]
        assert query.get("resId") == [expected_record_id]
    finally:
        record_page.close()


@pytest.mark.cc_test("CC-TEST-008")
def test_cc_test_008_search_error_state(workspace_page, odoo_base_url):
    workspace_page.route(
        f"**{SEARCH_ENDPOINT}",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"status":"FAILED","errors":[{"code":"SERVICE_UNAVAILABLE"}]}',
        ),
    )
    submit_search(
        workspace_page,
        "cc018 controlled failure",
        odoo_base_url,
        expected_status=503,
    )
    expect(workspace_page.get_by_test_id("search-error")).to_be_visible()


@pytest.mark.cc_test("CC-TEST-009")
def test_cc_test_009_restricted_user_cannot_see_fixture(
    page_factory, odoo_base_url, contact_records, prepare_resource
):
    page = page_factory("restricted")
    prepare_resource(page, contact_records["marker"])
    submit_search(page, contact_records["marker"], odoo_base_url)
    expect(page.locator(RESULT_CARDS)).to_have_count(0)
    expect(page.get_by_test_id("result-list")).not_to_contain_text(
        contact_records["marker"]
    )


@pytest.mark.cc_test("CC-TEST-010")
def test_cc_test_010_configuration_manager_can_open_structured_config(
    page_factory, odoo_base_url
):
    page = page_factory("config_manager")
    version_ids = odoo_orm_call(
        page,
        odoo_base_url,
        "wd.gs.config.version",
        "search",
        [[
            ["state", "=", "published"],
            ["domain_id.key", "=", "global_search_baseline"],
        ]],
        {"limit": 1, "order": "version desc, id desc"},
    )
    assert version_ids, "No published Global Search configuration was available"
    page.goto(
        f"{odoo_base_url}/odoo/wd.gs.config.version/{version_ids[0]}",
        wait_until="domcontentloaded",
    )
    contact_row = page.get_by_role("row", name=re.compile(r"\bContact\b", re.I))
    expect(contact_row).to_be_visible()
    contact_row.dblclick()
    expect(page.locator('[name="structured_card_title_template"]')).to_be_visible()


@pytest.mark.cc_test("CC-TEST-011")
def test_cc_test_011_language_and_timezone_baseline(workspace_page):
    expected_language = os.environ.get("CC018_EXPECTED_LANGUAGE")
    expected_timezone = os.environ.get("CC018_EXPECTED_TIMEZONE")
    assert expected_language, "CC018_EXPECTED_LANGUAGE must describe the reader fixture"
    assert expected_timezone, "CC018_EXPECTED_TIMEZONE must describe the reader fixture"
    expect(workspace_page.locator("html")).to_have_attribute("lang", expected_language)
    expect(workspace_page.get_by_test_id("global-search-workspace")).to_have_attribute(
        "data-user-timezone", expected_timezone
    )


@pytest.mark.cc_test("CC-TEST-012")
@pytest.mark.parametrize(
    "viewport",
    [
        {"width": 1440, "height": 900},
        {"width": 768, "height": 1024},
        {"width": 390, "height": 844},
    ],
    ids=("desktop", "tablet", "narrow"),
)
def test_cc_test_012_responsive_and_keyboard(
    page_factory, contact_records, prepare_resource, viewport
):
    page = page_factory("reader", viewport)
    assert prepare_resource(page, contact_records["marker"])
    page.get_by_test_id("search-query").fill(contact_records["marker"])
    page.get_by_test_id("search-query").press("Enter")
    expect(page.locator(RESULT_CARDS)).to_have_count(10)
    expect(page.get_by_test_id("page-summary")).to_have_text("Showing 1–10 of 12")
    condition_details = page.get_by_test_id("condition-builder")
    condition_summary = condition_details.locator("summary")
    condition_summary.focus()
    condition_summary.press("Enter")
    expect(condition_details).to_have_attribute("open", "")
    condition_summary.press("Enter")
    expect(condition_details).not_to_have_attribute("open", "")

    resource = page.get_by_test_id("resource-contact")
    resource.focus()
    resource.press("Space")
    expect(resource).to_have_attribute("aria-pressed", "false")
    reselect = page.get_by_test_id("reselect-all")
    reselect.focus()
    reselect.press("Space")
    expect(resource).to_have_attribute("aria-pressed", "true")

    first_card = page.locator(RESULT_CARDS).first
    first_card.focus()
    first_card.press("Space")
    expect(first_card).to_have_attribute("aria-pressed", "true")
    first_card.press("Escape")
    expect(first_card).to_have_attribute("aria-pressed", "false")

    next_button = page.get_by_test_id("page-controls").get_by_role(
        "button", name="Next"
    )
    next_button.focus()
    next_button.press("Enter")
    expect(page.get_by_test_id("page-summary")).to_have_text("Showing 11–12 of 12")
    no_horizontal_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth <= window.innerWidth"
    )
    assert no_horizontal_overflow


@pytest.mark.cc_test("CC-TEST-024")
def test_cc_test_024_workspace_qweb_response(
    page_factory, odoo_base_url
):
    page = page_factory("reader")
    response = page.goto(
        f"{odoo_base_url}/wd_global_search",
        wait_until="domcontentloaded",
    )
    assert response is not None
    assert response.status == 200
    assert response.headers.get("content-type") == "text/html; charset=utf-8"
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page).to_have_title("Global Search")
    expect(page.get_by_role("heading", name="Search Workspace")).to_be_visible()

    child_order = page.locator("main.wd-workspace").evaluate(
        "(main) => Array.from(main.children).map((node) => "
        "node.classList[0] || node.tagName.toLowerCase())"
    )
    assert child_order == [
        "wd-header",
        "wd-query-bar",
        "wd-resource-tabs",
        "wd-resource-empty",
        "wd-condition-builder",
        "wd-refinements",
        "wd-understanding",
        "wd-layout",
    ]

    tabs = page.locator(".wd-resource-tab")
    assert tabs.count() > 0
    for index in range(tabs.count()):
        tab = tabs.nth(index)
        assert isinstance(json.loads(tab.get_attribute("data-states")), list)
        assert isinstance(
            json.loads(tab.get_attribute("data-searchable-fields")), list
        )
        assert tab.locator(".wd-resource-label").locator("*").count() == 0

    manager_page = page_factory("config_manager")
    version_ids = odoo_orm_call(
        manager_page,
        odoo_base_url,
        "wd.gs.config.version",
        "search",
        [[
            ["state", "=", "published"],
            ["domain_id.key", "=", "global_search_baseline"],
        ]],
        {"limit": 1, "order": "version desc, id desc"},
    )
    assert version_ids, "No published baseline configuration was available"
    resource_ids = odoo_orm_call(
        manager_page,
        odoo_base_url,
        "wd.gs.business.resource",
        "search",
        [[
            ["version_id", "=", version_ids[0]],
            ["key", "=", "contact"],
        ]],
        {"limit": 1},
    )
    assert resource_ids, "No Contact resource was available in the baseline"

    designer_response = manager_page.goto(
        f"{odoo_base_url}/wd_global_search/card_templates"
        f"?resource_id={resource_ids[0]}",
        wait_until="domcontentloaded",
    )
    assert designer_response is not None
    assert designer_response.status == 200
    assert designer_response.headers.get("content-type") == (
        "text/html; charset=utf-8"
    )
    expect(manager_page).to_have_title(re.compile(r"^Card Template — "))
    expect(manager_page.locator("main.wd-template-designer-page")).to_have_count(1)
    expect(manager_page.locator("#wd-template-input")).to_be_visible()

    error_page = page_factory("reader")
    error_response = error_page.goto(
        f"{odoo_base_url}/wd_global_search/open_result"
        "?resource_key=cc018_invalid&record_id=0",
        wait_until="domcontentloaded",
    )
    assert error_response is not None
    assert error_response.status == 403
    expect(error_page).to_have_title("Record unavailable")
    expect(error_page.get_by_role("link", name="Back to search")).to_have_attribute(
        "href", "/wd_global_search"
    )


@pytest.mark.cc_test("CC-TEST-025")
def test_cc_test_025_controller_route_contract(page_factory, odoo_base_url):
    manager_page = page_factory("config_manager")
    version_ids = odoo_orm_call(
        manager_page,
        odoo_base_url,
        "wd.gs.config.version",
        "search",
        [[
            ["state", "=", "published"],
            ["domain_id.key", "=", "global_search_baseline"],
        ]],
        {"limit": 1, "order": "version desc, id desc"},
    )
    assert version_ids, "No published baseline configuration was available"
    resource_ids = odoo_orm_call(
        manager_page,
        odoo_base_url,
        "wd.gs.business.resource",
        "search",
        [[
            ["version_id", "=", version_ids[0]],
            ["key", "=", "contact"],
        ]],
        {"limit": 1},
    )
    assert resource_ids, "No Contact resource was available in the baseline"
    resource_id = resource_ids[0]
    model_rows = odoo_orm_call(
        manager_page,
        odoo_base_url,
        "wd.gs.business.resource",
        "read",
        [[resource_id], ["primary_model_name"]],
    )
    assert model_rows[0]["primary_model_name"] == "res.partner"
    designer_url = f"{odoo_base_url}/wd_global_search/card_templates?resource_id={resource_id}"
    designer_response = manager_page.goto(
        designer_url,
        wait_until="domcontentloaded",
    )
    assert designer_response is not None
    assert designer_response.status == 200
    csrf_token = manager_page.locator("main.wd-template-designer-page").get_attribute(
        "data-csrf-token"
    )
    assert csrf_token

    descriptor_response = manager_page.request.get(
        f"{odoo_base_url}/wd_global_search/card_templates/descriptor",
        params={"resource_id": resource_id},
    )
    assert descriptor_response.status == 200, descriptor_response.text()[:500]
    descriptor = descriptor_response.json()
    assert descriptor["status"] == "SUCCESS"
    assert descriptor["resource_id"] == resource_id
    assert {"fields", "models", "pending", "state", "template"} <= descriptor.keys()

    records_response = manager_page.request.get(
        f"{odoo_base_url}/wd_global_search/card_templates/records",
        params={"resource_id": resource_id},
    )
    assert records_response.status == 200
    assert records_response.json()["status"] == "SUCCESS"

    check_url = f"{odoo_base_url}/wd_global_search/card_templates/check"
    wrong_method = manager_page.request.get(
        check_url,
        params={"resource_id": resource_id},
    )
    assert wrong_method.status == 405
    missing_csrf = manager_page.request.post(
        check_url,
        form={"resource_id": resource_id, "template": "Name: {name}"},
    )
    assert missing_csrf.status in {400, 403}

    form_data = {
        "resource_id": resource_id,
        "template": "Name: {name}",
        "csrf_token": csrf_token,
    }
    check_response = manager_page.request.post(check_url, form=form_data)
    assert check_response.status == 200, check_response.text()[:500]
    assert check_response.json()["status"] == "SUCCESS"

    preview_response = manager_page.request.post(
        f"{odoo_base_url}/wd_global_search/card_templates/preview",
        form={**form_data, "source": "synthetic_example"},
    )
    assert preview_response.status == 200
    preview = preview_response.json()
    assert preview["status"] == "SUCCESS"
    assert {"rendered_plain_text", "safe_preview_metadata", "validation_errors"} <= (
        preview.keys()
    )

    for endpoint, payload in (
        (
            "save",
            {**form_data},
        ),
        (
            "apply",
            {"resource_id": "0", "csrf_token": csrf_token},
        ),
    ):
        safe_payload = {**payload, "resource_id": "0"}
        response = manager_page.request.post(
            f"{odoo_base_url}/wd_global_search/card_templates/{endpoint}",
            form=safe_payload,
        )
        assert response.status == 400, response.text()[:500]

    reader_page = page_factory("reader")
    forbidden = reader_page.request.get(designer_url, timeout=15000)
    assert forbidden.status == 403

    invalid_preview = reader_page.request.get(
        f"{odoo_base_url}/wd_global_search/api/preview",
        params={"model": "cc018.invalid.model"},
    )
    assert invalid_preview.status == 400
    assert invalid_preview.json()["status"] == "INVALID_REQUEST"

    invalid_navigation = reader_page.request.get(
        f"{odoo_base_url}/wd_global_search/api/form_url",
        params={"resource_key": "cc018_invalid", "record_id": "0"},
    )
    assert invalid_navigation.status == 403
    assert invalid_navigation.json()["status"] != "SUCCESS"

    search_response = reader_page.request.post(
        f"{odoo_base_url}/wd_global_search/api/search",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "query": "",
                    "conditions": [],
                    "resources": [],
                },
            }
        ),
        headers={"Content-Type": "application/json"},
    )
    assert search_response.status == 200
    search_envelope = search_response.json()
    search_result = search_envelope.get("result", search_envelope)
    assert {
        "status",
        "request_id",
        "results",
        "counts",
        "errors",
        "resource_counts",
        "effective_conditions",
        "next_cursor",
        "meta",
    } <= search_result.keys()

    cancel_response = reader_page.request.post(
        f"{odoo_base_url}/wd_global_search/api/cancel",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"request_id": "cc018-no-active-request"},
            }
        ),
        headers={"Content-Type": "application/json"},
    )
    assert cancel_response.status == 200
    cancel_envelope = cancel_response.json()
    assert cancel_envelope.get("result", {}).get("status") == "FAILED"


@pytest.mark.cc_test("CC-TEST-026")
def test_cc_test_026_workspace_module_loading(
    page_factory, odoo_base_url, contact_records, prepare_resource
):
    page = page_factory("reader")
    script_responses = {}
    failed_scripts = []
    console_errors = []

    def record_script_response(response):
        path = urlsplit(response.url).path
        if "/static/src/js/" in path:
            script_responses[path.rsplit("/", 1)[-1]] = (
                response.status,
                response.headers.get("content-type", ""),
                parse_qs(urlsplit(response.url).query).get("v"),
            )

    def record_failed_request(request):
        if "/static/src/js/" in request.url:
            failed_scripts.append(request.url)

    page.on("response", record_script_response)
    page.on("requestfailed", record_failed_request)
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    response = page.goto(
        f"{odoo_base_url}/wd_global_search",
        wait_until="load",
    )
    assert response is not None
    assert response.status == 200
    expect(page.get_by_test_id("global-search-workspace")).to_be_visible()
    page.wait_for_load_state("networkidle")

    expected_modules = {
        "preview.js",
        "workspace_entry.js",
        "workspace_conditions.js",
        "workspace_resources.js",
        "workspace_results.js",
        "workspace_search.js",
    }
    assert expected_modules <= script_responses.keys()
    for name in expected_modules:
        status, content_type, version = script_responses[name]
        assert status == 200, f"{name} returned HTTP {status}"
        assert "javascript" in content_type
        assert version == ["cc018-phase4-v02"], f"{name} has a stale cache version"
    assert not failed_scripts

    assert prepare_resource(page, contact_records["marker"])
    assert not console_errors
    expect(page.locator(RESULT_CARDS)).to_have_count(10)


@pytest.mark.cc_test("CC-TEST-028")
def test_cc_test_028_temporary_user_role_scope(role_storage_states):
    assert set(role_storage_states) == {
        "operator",
        "reader",
        "fixture_writer",
        "restricted",
        "config_manager",
        "status_reader",
    }
