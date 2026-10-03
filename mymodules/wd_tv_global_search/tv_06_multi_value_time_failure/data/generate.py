from datetime import datetime, timedelta


MARKER = "TV06-"


def create_fixtures(env):
    partner = env["res.partner"].search([], limit=1)
    if not partner:
        raise RuntimeError("TV-06 requires an accessible res.partner")
    SaleOrder = env["sale.order"]
    values = [
        ("DRAFT", "draft", datetime(2026, 10, 1, 12, 0, 0)),
        ("SENT", "sent", datetime(2026, 10, 2, 12, 0, 0)),
        ("SALE", "sale", datetime(2026, 10, 3, 12, 0, 0)),
        ("CANCEL", "cancel", datetime(2026, 10, 4, 12, 0, 0)),
        ("BOUNDARY", "draft", datetime(2026, 11, 1, 0, 0, 0)),
    ]
    records = SaleOrder
    for suffix, state, date_order in values:
        records |= SaleOrder.create(
            {
                "partner_id": partner.id,
                "client_order_ref": f"{MARKER}{suffix}",
                "date_order": date_order,
            }
        )
        record = records[-1]
        if record.state != state:
            record.write({"state": state})
    return records


def cleanup(env, language=None, original_week_start=None):
    orders = env["sale.order"].search([("client_order_ref", "=ilike", f"{MARKER}%")])
    for order in orders.filtered(lambda order: order.state not in {"draft", "cancel"}):
        order._action_cancel()
    if orders:
        orders.unlink()
    if language:
        if original_week_start is None:
            language.unlink()
        else:
            language.write({"week_start": original_week_start})


def ensure_language(env, code="zh_CN"):
    language = env["res.lang"].with_context(active_test=False).search(
        [("code", "=", code)], limit=1
    )
    if language:
        original_week_start = language.week_start
        if not language.active:
            language.toggle_active()
        language.write({"week_start": "1"})
        return language, False, original_week_start
    return (
        env["res.lang"].create(
            {
                "name": "Chinese (China) TV06",
                "code": code,
                "iso_code": code,
                "url_code": code,
                "active": True,
                "direction": "ltr",
                "date_format": "%Y-%m-%d",
                "time_format": "%H:%M:%S",
                "short_time_format": "%H:%M",
                "week_start": "1",
                "grouping": "[]",
                "decimal_point": ".",
                "thousands_sep": ",",
            }
        ),
        True,
        None,
    )
