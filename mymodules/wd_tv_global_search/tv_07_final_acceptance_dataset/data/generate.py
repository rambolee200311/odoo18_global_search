import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


MARKER = "GS-"
ROOT = Path.cwd() / "mymodules/wd_tv_global_search/tv_07_final_acceptance_dataset"
RESULT_PATH = ROOT / "results" / "generation_result.json"
MONTHS = (
    (2025, 10, 15),
    (2025, 11, 15),
    (2025, 12, 15),
    (2026, 1, 15),
    (2026, 2, 15),
    (2026, 3, 15),
    (2026, 4, 10),
)


def _date_values():
    values = []
    for year, month, count in MONTHS:
        start = datetime(year, month, 1, 10, 0, 0)
        for offset in range(count):
            values.append(start + timedelta(days=offset))
    return values


def _existing(model, field, value):
    return model.search([(field, "=", value)], limit=1)


def _create_partners(env):
    model = env["res.partner"]
    vendors = model.browse()
    customers = model.browse()
    for index in range(1, 6):
        vendor_key = f"GS-VENDOR-{index:03d}"
        customer_key = f"GS-CUSTOMER-{index:03d}"
        vendor = _existing(model, "ref", vendor_key) or model.create(
            {
                "name": vendor_key,
                "ref": vendor_key,
                "company_type": "company",
                "supplier_rank": 1,
                "email": f"{vendor_key.lower()}@example.invalid",
            }
        )
        customer = _existing(model, "ref", customer_key) or model.create(
            {
                "name": customer_key,
                "ref": customer_key,
                "company_type": "company",
                "customer_rank": 1,
                "email": f"{customer_key.lower()}@example.invalid",
            }
        )
        vendors |= vendor
        customers |= customer
    return vendors, customers


def _create_products(env):
    template_model = env["product.template"]
    products = env["product.product"].browse()
    for index in range(1, 11):
        key = f"GS-PRODUCT-{index:03d}"
        product = env["product.product"].search([("default_code", "=", key)], limit=1)
        if not product:
            template = template_model.create(
                {
                    "name": key,
                    "default_code": key,
                    "type": "consu",
                    "is_storable": True,
                    "sale_ok": True,
                    "purchase_ok": True,
                }
            )
            product = template.product_variant_id
        products |= product
    return products


def _purchase_order(env, index, partner, product, date_order, picking_type):
    model = env["purchase.order"]
    key = f"GS-PO-{index:04d}"
    order = _existing(model, "partner_ref", key)
    if not order:
        order = model.create(
            {
                "partner_id": partner.id,
                "partner_ref": key,
                "origin": key,
                "date_order": date_order,
                "picking_type_id": picking_type.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": product.display_name,
                            "product_qty": 1,
                            "price_unit": 10.0 + index,
                            "date_planned": date_order + timedelta(days=2),
                        },
                    )
                ],
            }
        )
    if order.state in {"draft", "sent", "to approve"}:
        order.button_confirm()
    if order.name != key:
        order.write({"name": key})
    return order


def _sale_order(env, index, partner, product, date_order):
    model = env["sale.order"]
    key = f"GS-SO-{index:04d}"
    order = _existing(model, "client_order_ref", key)
    if not order:
        order = model.create(
            {
                "partner_id": partner.id,
                "client_order_ref": key,
                "origin": key,
                "date_order": date_order,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": product.display_name,
                            "product_uom_qty": 1,
                            "price_unit": 20.0 + index,
                        },
                    )
                ],
            }
        )
    if order.state in {"draft", "sent"}:
        order.action_confirm()
    if order.date_order != date_order:
        order.write({"date_order": date_order})
    if order.name != key:
        order.write({"name": key})
    return order


def _tag_pickings(pickings, prefix, index):
    key = f"{prefix}{index:04d}"
    for picking in pickings:
        if not picking.origin or not picking.origin.startswith(key):
            picking.write({"origin": key})
        if picking.name != key:
            picking.write({"name": key})
    return pickings


def _relation_sample(orders, relation_name):
    sample = []
    for order in orders[:5]:
        pickings = order.picking_ids
        related = pickings.filtered(lambda picking: getattr(picking, relation_name) == order)
        sample.append(
            {
                "order": order.name,
                "order_marker": order.partner_ref if relation_name == "purchase_id" else order.client_order_ref,
                "pickings": related.mapped("name"),
                "linked": bool(related),
            }
        )
    return sample


def generate(env):
    company = env.company
    vendors, customers = _create_partners(env)
    products = _create_products(env)
    incoming = env["stock.picking.type"].search(
        [("code", "=", "incoming"), ("company_id", "=", company.id)], limit=1
    )
    outgoing = env["stock.picking.type"].search(
        [("code", "=", "outgoing"), ("company_id", "=", company.id)], limit=1
    )
    if not incoming or not outgoing:
        raise RuntimeError("Both incoming and outgoing picking types are required.")

    dates = _date_values()
    purchase_orders = env["purchase.order"].browse()
    sale_orders = env["sale.order"].browse()
    for index, date_order in enumerate(dates, 1):
        purchase_orders |= _purchase_order(
            env, index, vendors[(index - 1) % len(vendors)], products[(index - 1) % len(products)],
            date_order, incoming,
        )
        sale_orders |= _sale_order(
            env, index, customers[(index - 1) % len(customers)], products[(index + 2) % len(products)],
            date_order,
        )

    incoming_pickings = env["stock.picking"].search(
        [("origin", "=like", "GS-IN-%")], order="id"
    )
    outgoing_pickings = env["stock.picking"].search(
        [("origin", "=like", "GS-OUT-%")], order="id"
    )
    for index, order in enumerate(purchase_orders, 1):
        _tag_pickings(order.picking_ids, "GS-IN-", index)
    for index, order in enumerate(sale_orders, 1):
        _tag_pickings(order.picking_ids, "GS-OUT-", index)
    incoming_pickings = env["stock.picking"].search([("origin", "=like", "GS-IN-%")], order="id")
    outgoing_pickings = env["stock.picking"].search([("origin", "=like", "GS-OUT-%")], order="id")

    result = {
        "counts": {
            "vendors": len(vendors),
            "customers": len(customers),
            "products": len(products),
            "purchase_orders": len(purchase_orders),
            "receipts": len(incoming_pickings),
            "sales_orders": len(sale_orders),
            "deliveries": len(outgoing_pickings),
        },
        "date_distribution": {
            f"{year:04d}-{month:02d}": {
                "purchase_orders": count,
                "sales_orders": count,
            }
            for year, month, count in MONTHS
        },
        "purchase_state_distribution": dict(Counter(purchase_orders.mapped("state"))),
        "sales_state_distribution": dict(Counter(sale_orders.mapped("state"))),
        "relations": {
            "purchase_to_receipt": sum(
                bool(order.picking_ids.filtered(lambda picking: picking.purchase_id == order))
                for order in purchase_orders
            ),
            "sale_to_delivery": sum(
                bool(order.picking_ids.filtered(lambda picking: picking.sale_id == order))
                for order in sale_orders
            ),
        },
        "samples": {
            "purchase_to_receipt": _relation_sample(purchase_orders, "purchase_id"),
            "sale_to_delivery": _relation_sample(sale_orders, "sale_id"),
        },
        "product_usage": {
            product.default_code: {
                "purchase_orders": len(purchase_orders.filtered(
                    lambda order: product in order.order_line.mapped("product_id")
                )),
                "sales_orders": len(sale_orders.filtered(
                    lambda order: product in order.order_line.mapped("product_id")
                )),
            }
            for product in products
        },
        "partner_usage": {
            partner.ref: {
                "purchase_orders": len(purchase_orders.filtered(
                    lambda order: order.partner_id == partner
                )),
            }
            for partner in vendors
        },
        "customer_usage": {
            partner.ref: {
                "sales_orders": len(sale_orders.filtered(
                    lambda order: order.partner_id == partner
                )),
            }
            for partner in customers
        },
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


result = generate(env)
env.cr.commit()
print(json.dumps(result, ensure_ascii=False, indent=2))
