from uuid import uuid4

import pytest


def odoo_orm_call(page, base_url, model, method, args=None, kwargs=None):
    response = page.request.post(
        f"{base_url}/web/dataset/call_kw/{model}/{method}",
        data={
            "id": "cc018-ui-fixture",
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {},
            },
        },
    )
    if response.status != 200:
        raise AssertionError(
            f"ORM call {model}.{method} returned HTTP {response.status}"
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise AssertionError(f"ORM call {model}.{method} returned an invalid response")
    if "error" in payload:
        error = payload["error"]
        error_data = error.get("data", {}) if isinstance(error, dict) else {}
        error_name = error_data.get("name", "OdooError")
        raise AssertionError(f"ORM call {model}.{method} failed ({error_name})")
    if "result" not in payload:
        raise AssertionError(f"ORM call {model}.{method} omitted its result")
    return payload["result"]


@pytest.fixture
def contact_records(request, page_factory, odoo_base_url):
    fixture_writer = page_factory("fixture_writer")
    marker = f"CC018-{uuid4()}"
    domain = [["name", "ilike", f"{marker} Contact %"]]

    def cleanup():
        record_ids = odoo_orm_call(
            fixture_writer,
            odoo_base_url,
            "res.partner",
            "search",
            [domain],
            {"limit": 100},
        )
        if record_ids:
            odoo_orm_call(
                fixture_writer,
                odoo_base_url,
                "res.partner",
                "unlink",
                [record_ids],
            )
        remaining = odoo_orm_call(
            fixture_writer,
            odoo_base_url,
            "res.partner",
            "search_count",
            [domain],
        )
        if remaining:
            pytest.fail(
                f"Fixture cleanup left {remaining} contact record(s) "
                f"for marker {marker}"
            )

    request.addfinalizer(cleanup)
    names = [f"{marker} Contact {index:02d}" for index in range(1, 13)]
    emails = [
        f"{marker.lower()}-{index:02d}@example.test"
        for index in range(1, 13)
    ]
    for name, email in zip(names, emails):
        odoo_orm_call(
            fixture_writer,
            odoo_base_url,
            "res.partner",
            "create",
            [{"name": name, "email": email}],
        )

    return {"marker": marker, "names": names, "emails": emails}


@pytest.fixture
def sale_order_records(request, page_factory, odoo_base_url):
    status_reader = page_factory("status_reader")
    operator = page_factory("operator")
    if not odoo_orm_call(
        operator,
        odoo_base_url,
        "sale.order",
        "check_access_rights",
        ["unlink", False],
    ):
        pytest.fail("Authorized operator cannot clean the isolated Sales Order fixture")
    partner_ids = odoo_orm_call(
        status_reader,
        odoo_base_url,
        "res.partner",
        "search",
        [[]],
        {"limit": 1},
    )
    if not partner_ids:
        pytest.fail("Status-filter fixture could not find an accessible Contact")

    marker = f"CC018-SO-{uuid4()}"
    domain = [["name", "ilike", f"{marker}%"]]
    names = {
        "quotation": f"{marker} Quotation",
        "cancelled": f"{marker} Cancelled",
    }

    def cleanup():
        order_ids = odoo_orm_call(
            operator,
            odoo_base_url,
            "sale.order",
            "search",
            [domain],
            {"limit": 20},
        )
        if order_ids:
            odoo_orm_call(
                operator,
                odoo_base_url,
                "sale.order",
                "unlink",
                [order_ids],
            )
        remaining = odoo_orm_call(
            operator,
            odoo_base_url,
            "sale.order",
            "search_count",
            [domain],
        )
        if remaining:
            pytest.fail(
                f"Fixture cleanup left {remaining} Sales Order(s) "
                f"for marker {marker}"
            )

    request.addfinalizer(cleanup)
    order_ids = [
        odoo_orm_call(
            status_reader,
            odoo_base_url,
            "sale.order",
            "create",
            [{"name": name, "partner_id": partner_ids[0]}],
        )
        for name in names.values()
    ]
    odoo_orm_call(
        status_reader,
        odoo_base_url,
        "sale.order",
        "action_cancel",
        [[order_ids[1]]],
    )
    records = odoo_orm_call(
        status_reader,
        odoo_base_url,
        "sale.order",
        "search_read",
        [[["id", "in", order_ids]]],
        {"fields": ["name", "state"], "limit": 10},
    )
    states_by_name = {record["name"]: record["state"] for record in records}
    if states_by_name != {
        names["quotation"]: "draft",
        names["cancelled"]: "cancel",
    }:
        pytest.fail("Status-filter fixture did not produce its expected order states")

    return {"marker": marker, **names}
