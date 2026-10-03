import json
from datetime import date
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_03_business_date_merge"
RESULTS = ROOT / "results"
MARKER = "GS03-"
START = date(2026, 6, 1)
END = date(2026, 7, 1)

RESOURCE_MAP = [
    ("sale.order", "client_order_ref", "date_order", "销售订单"),
    ("purchase.order", "partner_ref", "date_order", "采购订单"),
    ("account.move", "ref", "invoice_date", "发票"),
    ("stock.picking", "origin", "date_done", "出库单"),
    ("stock.move", "name", "date", "库存移动"),
]


def as_date(value):
    return value.date() if hasattr(value, "date") else value


def filter_resource(model_name, marker_field, date_field, label):
    model = env[model_name]
    records = model.search([(marker_field, "=ilike", f"{MARKER}%")], order="id asc")
    included = []
    excluded_empty = 0
    for record in records:
        business_date = as_date(getattr(record, date_field))
        if not business_date:
            excluded_empty += 1
            continue
        if START <= business_date < END:
            included.append(
                {
                    "resource": label,
                    "model": model_name,
                    "record_id": record.id,
                    "business_date": business_date.isoformat(),
                    "business_date_field": date_field,
                    "marker": getattr(record, marker_field),
                }
            )
    return included, excluded_empty


def merge_results():
    merged = []
    empty_counts = {}
    per_resource = {}
    for resource in RESOURCE_MAP:
        model_name, marker_field, date_field, label = resource
        included, excluded_empty = filter_resource(
            model_name, marker_field, date_field, label
        )
        per_resource[model_name] = len(included)
        empty_counts[model_name] = excluded_empty
        merged.extend(included)
    return sorted(merged, key=lambda item: (item["business_date"], item["model"], item["record_id"])), per_resource, empty_counts


first, per_resource, empty_counts = merge_results()
second, _, _ = merge_results()
output = {
    "spike": "SPIKE-GS-03",
    "database": env.cr.dbname,
    "uid": env.uid,
    "date_range": {
        "start_inclusive": START.isoformat(),
        "end_exclusive": END.isoformat(),
        "label": "2026-06",
    },
    "business_date_mapping": [
        {"model": model, "field": field, "resource": label}
        for model, _, field, label in RESOURCE_MAP
    ],
    "per_resource_included": per_resource,
    "empty_dates_excluded": empty_counts,
    "merged_count": len(first),
    "merged_results": first,
    "stable_repeat": first == second,
    "all_results_are_june": all(
        item["business_date"].startswith("2026-06") for item in first
    ),
    "all_results_annotated": all(
        item["business_date"] and item["business_date_field"] for item in first
    ),
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")
