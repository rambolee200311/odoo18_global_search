import json
from datetime import datetime, time
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_03_business_date_merge"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
MARKER = "GS03-"
DATES = ["2026-05-31", "2026-06-30", "2026-07-01", False]


def business_datetime(value):
    return datetime.combine(
        datetime.strptime(value, "%Y-%m-%d").date(), time(12, 0)
    ) if value else False

partner = env["res.partner"].search([], limit=1)
if not partner:
    partner = env["res.partner"].create({"name": f"{MARKER} Partner"})
company = env.company
created = {}

def find_or_create(model, ref_field, ref, values):
    record = env[model].search([(ref_field, "=", ref)], limit=1)
    if not record:
        record = env[model].create(values)
        created[model] = created.get(model, 0) + 1
    return record


for index, business_date in enumerate(DATES, 1):
    if not business_date:
        continue
    ref = f"{MARKER}SALE-{index}"
    record = find_or_create(
        "sale.order",
        "client_order_ref",
        ref,
        {
            "partner_id": partner.id,
            "client_order_ref": ref,
        },
    )
    record.write(
        {"date_order": business_datetime(business_date) if business_date else False}
    )

    ref = f"{MARKER}PURCHASE-{index}"
    record = find_or_create(
        "purchase.order",
        "partner_ref",
        ref,
        {
            "partner_id": partner.id,
            "partner_ref": ref,
        },
    )
    record.write(
        {"date_order": business_datetime(business_date) if business_date else False}
    )

journal = env["account.journal"].search(
    [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
)
if not journal:
    raise RuntimeError("No sale journal available for SPIKE-GS-03")
for index, business_date in enumerate(DATES, 1):
    ref = f"{MARKER}INVOICE-{index}"
    find_or_create(
        "account.move",
        "ref",
        ref,
        {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "journal_id": journal.id,
            "ref": ref,
            "invoice_date": business_date,
        },
    )

picking_type = env["stock.picking.type"].search(
    [("code", "=", "outgoing"), ("company_id", "=", company.id)], limit=1
)
location = env["stock.location"].search(
    [("usage", "=", "internal"), ("company_id", "=", company.id)], limit=1
)
customer_location = env["stock.location"].search([("usage", "=", "customer")], limit=1)
product = env["product.product"].search([], limit=1)
if not picking_type or not location or not customer_location or not product:
    raise RuntimeError("Required stock records unavailable for SPIKE-GS-03")

for index, business_date in enumerate(DATES, 1):
    ref = f"{MARKER}PICKING-{index}"
    picking = find_or_create(
        "stock.picking",
        "origin",
        ref,
        {
            "picking_type_id": picking_type.id,
            "location_id": location.id,
            "location_dest_id": customer_location.id,
            "origin": ref,
            "scheduled_date": business_datetime(business_date),
        },
    )
    picking.write({"date_done": business_datetime(business_date)})

for index, business_date in enumerate(DATES, 1):
    if not business_date:
        continue
    ref = f"{MARKER}MOVE-{index}"
    picking = env["stock.picking"].search([("origin", "=", f"{MARKER}PICKING-{index}")], limit=1)
    find_or_create(
        "stock.move",
        "name",
        ref,
        {
            "name": ref,
            "reference": ref,
            "picking_id": picking.id,
            "product_id": product.id,
            "product_uom_qty": 1,
            "product_uom": product.uom_id.id,
            "location_id": location.id,
            "location_dest_id": customer_location.id,
            "date": business_datetime(business_date),
        },
    )

env.cr.commit()
result = {
    "spike": "SPIKE-GS-03",
    "database": env.cr.dbname,
    "uid": env.uid,
    "rows_per_resource": 4,
    "resources": 5,
    "dates": DATES,
    "created": created,
    "data_marker": MARKER,
    "orm_write": True,
}
(RESULTS / "simulation_result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "simulation_result.json")
