import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261001
ROWS = int(os.environ.get("SPIKE_ROWS", "5000"))
BASE = Path.cwd() / "mymodules/wd_spike_global_search/spike_01_multi_model_search"
OUTPUT = BASE / "results" / "simulation_result.json"


def get_or_create_partners(env):
    prefix = "GS01-CUST-"
    existing = env["res.partner"].search([("ref", "=ilike", prefix + "%")])
    by_ref = {partner.ref: partner for partner in existing}
    missing = [
        {
            "name": f"GS01 Customer {index:06d}",
            "ref": f"{prefix}{index:06d}",
            "email": f"gs01-customer-{index:06d}@example.invalid",
            "company_type": "company",
        }
        for index in range(1, ROWS + 1)
        if f"{prefix}{index:06d}" not in by_ref
    ]
    if missing:
        env["res.partner"].create(missing)
    partners = env["res.partner"].search(
        [("ref", "=ilike", prefix + "%")], order="id", limit=ROWS
    )
    return partners


def get_or_create_orders(env, partners):
    sale_model = env["sale.order"]
    purchase_model = env["purchase.order"]
    sale_existing = sale_model.search(
        [("client_order_ref", "=ilike", "GS01-SALE-%")]
    )
    purchase_existing = purchase_model.search(
        [("partner_ref", "=ilike", "GS01-PURCHASE-%")]
    )
    sale_refs = {order.client_order_ref for order in sale_existing}
    purchase_refs = {order.partner_ref for order in purchase_existing}
    start = date(2026, 5, 1)
    sale_values = []
    purchase_values = []
    for index in range(1, ROWS + 1):
        partner = partners[(index - 1) % len(partners)]
        order_date = start + timedelta(days=index % 92)
        sale_ref = f"GS01-SALE-{index:06d}"
        purchase_ref = f"GS01-PURCHASE-{index:06d}"
        if sale_ref not in sale_refs:
            sale_values.append(
                {
                    "partner_id": partner.id,
                    "client_order_ref": sale_ref,
                    "origin": "SPIKE-GS-01",
                    "date_order": order_date.isoformat(),
                }
            )
        if purchase_ref not in purchase_refs:
            purchase_values.append(
                {
                    "partner_id": partner.id,
                    "partner_ref": purchase_ref,
                    "origin": "SPIKE-GS-01",
                    "date_order": order_date.isoformat(),
                }
            )
    if sale_values:
        sale_model.create(sale_values)
    if purchase_values:
        purchase_model.create(purchase_values)
    return {
        "sale_created": len(sale_values),
        "purchase_created": len(purchase_values),
        "sale_total": sale_model.search_count(
            [("client_order_ref", "=ilike", "GS01-SALE-%")]
        ),
        "purchase_total": purchase_model.search_count(
            [("partner_ref", "=ilike", "GS01-PURCHASE-%")]
        ),
    }


def main(env):
    random.seed(SEED)
    if "sale.order" not in env.registry.models or "purchase.order" not in env.registry.models:
        raise RuntimeError("sale.order and purchase.order must be installed before simulation")
    partners = get_or_create_partners(env)
    if not partners:
        raise RuntimeError("No simulation partners available")
    orders = get_or_create_orders(env, partners)
    env.cr.commit()
    result = {
        "spike": "SPIKE-GS-01",
        "seed": SEED,
        "rows_requested_per_model": ROWS,
        "database": env.cr.dbname,
        "uid": env.uid,
        "partner_total": len(partners),
        **orders,
        "data_marker": "GS01-",
        "orm_write": True,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT)


main(env)
