import json
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

SEED = 20261002
ROWS = int(os.environ.get("TV_ROWS", "1000000"))
CHUNK_SIZE = int(os.environ.get("TV_CHUNK_SIZE", "1000"))
MARKER = "TV01-"
BASE = Path.cwd() / "mymodules/wd_tv_global_search/tv_01_nfr_001_performance"
RESULT_PATH = BASE / "results" / "generation_result.json"


def chunked(values):
    for start in range(0, len(values), CHUNK_SIZE):
        yield values[start : start + CHUNK_SIZE]


def create_or_reuse(model, domain, values):
    existing = model.search(domain)
    existing_keys = set(existing.mapped("ref"))
    missing = [value for value in values if value["ref"] not in existing_keys]
    created = 0
    for chunk in chunked(missing):
        model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, model.search(domain)


def partner_values():
    return [
        {
            "name": f"{MARKER}Partner {index:07d}",
            "ref": f"{MARKER}PARTNER-{index:07d}",
            "email": f"tv01-partner-{index:07d}@example.invalid",
            "company_type": "company",
        }
        for index in range(1, ROWS + 1)
    ]


def create_partners():
    values = partner_values()
    created, records = create_or_reuse(
        env["res.partner"],
        [("ref", "=ilike", f"{MARKER}PARTNER-%")],
        values,
    )
    return created, records


def create_orders(model_name, field_name, prefix, partners):
    model = env[model_name]
    existing = model.search([(field_name, "=ilike", f"{prefix}%")])
    existing_keys = set(existing.mapped(field_name))
    values = []
    start = date(2026, 1, 1)
    for index in range(1, ROWS + 1):
        key = f"{prefix}{index:07d}"
        if key in existing_keys:
            continue
        values.append(
            {
                "partner_id": partners[(index - 1) % len(partners)].id,
                field_name: key,
                "origin": "TV-01",
                "date_order": (start + timedelta(days=index % 366)).isoformat(),
            }
        )
    created = 0
    for chunk in chunked(values):
        model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, model.search([(field_name, "=ilike", f"{prefix}%")])


def create_pickings(partners, picking_type_code):
    model = env["stock.picking"]
    picking_types = env["stock.picking.type"].search(
        [("code", "=", picking_type_code)], limit=1
    )
    if not picking_types and picking_type_code == "internal":
        company = env["res.company"].search([], limit=1)
        source = env["stock.location"].search(
            [("usage", "=", "internal"), ("company_id", "in", [company.id, False])],
            limit=1,
        )
        destination = env["stock.location"].search(
            [
                ("usage", "=", "internal"),
                ("id", "!=", source.id),
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,
        )
        if not destination:
            destination = source
        if not source or not destination:
            raise RuntimeError("No internal locations available for internal picking type")
        picking_types = env["stock.picking.type"].create(
            {
                "name": "TV-01 Internal Transfers",
                "code": "internal",
                "sequence_code": "TVINT",
                "company_id": company.id,
                "default_location_src_id": source.id,
                "default_location_dest_id": destination.id,
            }
        )
        env.cr.commit()
    if not picking_types:
        raise RuntimeError(f"No picking type for {picking_type_code}")
    prefix = f"{MARKER}PICK-{picking_type_code.upper()}-"
    existing = model.search([("origin", "=ilike", f"{prefix}%")])
    existing_keys = set(existing.mapped("origin"))
    values = []
    for index in range(1, ROWS + 1):
        key = f"{prefix}{index:07d}"
        if key in existing_keys:
            continue
        values.append(
            {
                "picking_type_id": picking_types.id,
                "partner_id": partners[(index - 1) % len(partners)].id,
                "origin": key,
                "scheduled_date": "2026-06-01 00:00:00",
            }
        )
    created = 0
    for chunk in chunked(values):
        model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, model.search([("origin", "=ilike", f"{prefix}%")])


def create_invoices(partners):
    model = env["account.move"]
    journal = env["account.journal"].search([("type", "=", "sale")], limit=1)
    if not journal:
        raise RuntimeError("No sale journal available")
    prefix = f"{MARKER}INV-"
    existing = model.search([("ref", "=ilike", f"{prefix}%")])
    existing_keys = set(existing.mapped("ref"))
    values = []
    for index in range(1, ROWS + 1):
        key = f"{prefix}{index:07d}"
        if key in existing_keys:
            continue
        values.append(
            {
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "partner_id": partners[(index - 1) % len(partners)].id,
                "ref": key,
                "invoice_date": "2026-06-01",
            }
        )
    created = 0
    for chunk in chunked(values):
        model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, model.search([("ref", "=ilike", f"{prefix}%")])


def create_products():
    model = env["product.product"]
    template_model = env["product.template"]
    existing = model.search([("default_code", "=ilike", f"{MARKER}PROD-%")])
    existing_keys = set(existing.mapped("default_code"))
    created = 0
    values = []
    for index in range(1, ROWS + 1):
        key = f"{MARKER}PROD-{index:07d}"
        if key in existing_keys:
            continue
        values.append(
            {"name": key, "default_code": key, "type": "consu", "is_storable": True}
        )
    for chunk in chunked(values):
        template_model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, model.search([("default_code", "=ilike", f"{MARKER}PROD-%")])


def create_projects_and_tasks():
    project_model = env["project.project"]
    task_model = env["project.task"].with_context(
        mail_create_nolog=True,
        mail_notrack=True,
        tracking_disable=True,
    )
    project = project_model.search([("name", "=", f"{MARKER}Project")], limit=1)
    if not project:
        project = project_model.create({"name": f"{MARKER}Project"})
        env.cr.commit()
    existing = task_model.search([("name", "=ilike", f"{MARKER}TASK-%")])
    existing_keys = set(existing.mapped("name"))
    values = [
        {"name": f"{MARKER}TASK-{index:07d}", "project_id": project.id}
        for index in range(1, ROWS + 1)
        if f"{MARKER}TASK-{index:07d}" not in existing_keys
    ]
    created = 0
    for chunk in chunked(values):
        task_model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, task_model.search([("name", "=ilike", f"{MARKER}TASK-%")])


def create_quants(products):
    model = env["stock.quant"]
    location = env["stock.location"].search([("usage", "=", "internal")], limit=1)
    if not location:
        raise RuntimeError("No internal stock location available")
    existing = model.search([("product_id", "in", products.ids), ("location_id", "=", location.id)])
    existing_products = set(existing.mapped("product_id").ids)
    values = [
        {
            "product_id": product.id,
            "location_id": location.id,
            "inventory_quantity": 1,
        }
        for product in products
        if product.id not in existing_products
    ]
    created = 0
    for chunk in chunked(values):
        model.create(chunk)
        created += len(chunk)
        env.cr.commit()
    return created, model.search([("product_id", "in", products.ids), ("location_id", "=", location.id)])


def main():
    random.seed(SEED)
    started = time.perf_counter()
    required = [
        "res.partner",
        "sale.order",
        "purchase.order",
        "stock.picking",
        "account.move",
        "product.product",
        "project.task",
        "stock.quant",
    ]
    missing_models = [name for name in required if name not in env.registry.models]
    if missing_models:
        raise RuntimeError(f"Missing required models: {', '.join(missing_models)}")
    partner_created, partners = create_partners()
    sale_created, sales = create_orders("sale.order", "client_order_ref", f"{MARKER}SALE-", partners)
    purchase_created, purchases = create_orders("purchase.order", "partner_ref", f"{MARKER}PURCHASE-", partners)
    picking_results = {}
    for code in ("incoming", "outgoing", "internal"):
        picking_results[code] = create_pickings(partners, code)[0]
    invoice_created, invoices = create_invoices(partners)
    product_created, products = create_products()
    task_created, tasks = create_projects_and_tasks()
    quant_created, quants = create_quants(products)
    result = {
        "tv": "TV-01",
        "seed": SEED,
        "rows_target_per_logical_resource": ROWS,
        "database": env.cr.dbname,
        "uid": env.uid,
        "orm_write": True,
        "created": {
            "res.partner": partner_created,
            "sale.order": sale_created,
            "purchase.order": purchase_created,
            "stock.picking.incoming": picking_results["incoming"],
            "stock.picking.outgoing": picking_results["outgoing"],
            "stock.picking.internal": picking_results["internal"],
            "account.move": invoice_created,
            "product.product": product_created,
            "project.task": task_created,
            "stock.quant": quant_created,
        },
        "counts": {
            "res.partner": len(partners),
            "sale.order": len(sales),
            "purchase.order": len(purchases),
            "stock.picking.incoming": env["stock.picking"].search_count(
                [("origin", "=ilike", f"{MARKER}PICK-INCOMING-%")]
            ),
            "stock.picking.outgoing": env["stock.picking"].search_count(
                [("origin", "=ilike", f"{MARKER}PICK-OUTGOING-%")]
            ),
            "stock.picking.internal": env["stock.picking"].search_count(
                [("origin", "=ilike", f"{MARKER}PICK-INTERNAL-%")]
            ),
            "account.move": len(invoices),
            "product.product": len(products),
            "project.task": len(tasks),
            "stock.quant": len(quants),
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


main()
