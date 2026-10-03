import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_04_query_refinement_merge"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
MARKER = "GS03-"

RESOURCE_MAP = [
    ("sale.order", "client_order_ref", "date_order", "销售订单"),
    ("purchase.order", "partner_ref", "date_order", "采购订单"),
    ("account.move", "ref", "invoice_date", "发票"),
    ("stock.picking", "origin", "date_done", "出库单"),
    ("stock.move", "name", "date", "库存移动"),
]


def as_date(value):
    return value.date() if hasattr(value, "date") else value


records = []
for model_name, marker_field, date_field, resource in RESOURCE_MAP:
    model = env[model_name]
    for record in model.search(
        [(marker_field, "=ilike", f"{MARKER}%")], order="id asc"
    ):
        business_date = as_date(getattr(record, date_field))
        records.append(
            {
                "resource": resource,
                "model": model_name,
                "record_id": record.id,
                "identity": [resource, model_name, record.id],
                "entity": "GS03 Partner",
                "month": business_date.strftime("%Y-%m") if business_date else None,
                "state": getattr(record, "state", "draft") or "draft",
                "marker": getattr(record, marker_field),
            }
        )

output = {
    "spike": "SPIKE-GS-04",
    "database": env.cr.dbname,
    "uid": env.uid,
    "source_spike": "SPIKE-GS-03",
    "records": records,
    "orm_read": True,
}
(RESULTS / "data_snapshot.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "data_snapshot.json")

