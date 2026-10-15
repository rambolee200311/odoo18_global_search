import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from playwright.sync_api import expect

from fixtures.orm_helpers import contact_records


SEARCH_ENDPOINT = "/wd_global_search/api/search"
PAGE_SUMMARY = "[data-testid='page-summary']"


def _p95(samples):
    ordered = sorted(samples)
    return round(ordered[math.ceil(len(ordered) * 0.95) - 1], 3)


@pytest.mark.cc_test("CC-TEST-023")
def test_cc_test_023_workspace_performance(
    browser, page_factory, contact_records, odoo_base_url, prepare_resource
):
    page = page_factory("reader")
    navigation_samples = []
    for index in range(33):
        started = time.perf_counter()
        page.goto(
            f"{odoo_base_url}/wd_global_search",
            wait_until="domcontentloaded",
        )
        expect(page.get_by_test_id("global-search-workspace")).to_be_visible()
        elapsed_ms = (time.perf_counter() - started) * 1000
        if index >= 3:
            navigation_samples.append(elapsed_ms)

    expect(page.get_by_test_id("search-query")).to_be_visible()
    if not prepare_resource(page, contact_records["marker"]):
        raise AssertionError("Contact resource could not be selected for timing")
    search_samples = []
    query_timings = []

    def mark_search_response(response):
        if response.url.endswith(SEARCH_ENDPOINT):
            query_timings.append(time.perf_counter())

    page.on("response", mark_search_response)
    try:
        for index in range(33):
            query = (
                f"{contact_records['marker']} ZZNORESULT"
                if index % 2 == 0
                else contact_records["marker"]
            )
            expected_summary = (
                "0 records"
                if index % 2 == 0
                else "Showing 1–10 of 12"
            )
            response_count = len(query_timings)
            with page.expect_response(
                lambda response: response.url.endswith(SEARCH_ENDPOINT),
                timeout=15000,
            ):
                page.get_by_test_id("search-query").fill(query)
                page.get_by_test_id("search-submit").click()
            expect(page.locator(PAGE_SUMMARY)).to_have_text(expected_summary)
            if len(query_timings) <= response_count:
                raise AssertionError("Search response timing was not captured")
            elapsed_ms = (
                time.perf_counter() - query_timings[-1]
            ) * 1000
            if index >= 3:
                search_samples.append(elapsed_ms)
    finally:
        page.remove_listener("response", mark_search_response)

    navigation_p95_ms = _p95(navigation_samples)
    response_to_render_p95_ms = _p95(search_samples)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_directory = Path(os.environ["CC018_EVIDENCE_DIR"])
    evidence_directory.mkdir(parents=True, exist_ok=True)
    browser_name = browser.browser_type.name
    evidence = {
        "test_id": "CC-TEST-023",
        "database": "odoo18ce",
        "browser": browser_name,
        "browser_version": browser.version,
        "viewport": {"width": 1440, "height": 900},
        "fixture_marker": contact_records["marker"],
        "warmup_samples": 3,
        "measured_samples": 30,
        "workspace_navigation_p95_ms": navigation_p95_ms,
        "response_to_render_p95_ms": response_to_render_p95_ms,
        "thresholds_ms": {
            "workspace_navigation": 1000,
            "response_to_render": 500,
        },
        "soft_gate_exceeded": (
            navigation_p95_ms > 1000 or response_to_render_p95_ms > 500
        ),
    }
    evidence_path = evidence_directory / (
        f"CC018-performance-{browser_name}-{timestamp}.json"
    )
    evidence_path.write_text(
        json.dumps(evidence, indent=2) + "\n",
        encoding="utf-8",
    )
    screenshot_path = evidence_directory / (
        f"CC-TEST-023_{browser_name}_desktop_{timestamp}.png"
    )
    page.screenshot(path=str(screenshot_path), full_page=True)
