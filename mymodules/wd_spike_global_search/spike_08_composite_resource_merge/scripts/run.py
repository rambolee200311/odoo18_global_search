import json
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_08_composite_resource_merge"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
SEED = 20261008
ROWS_PER_MODEL = 100_000
MODEL_PRIORITY = {"sale.order": 1, "purchase.order": 2}
random.seed(SEED)


def state_mapping(model_name, state):
    if state in ("draft", "sent", "to approve"):
        return "未完成"
    if state in ("sale", "purchase", "done"):
        return "已完成"
    if state == "cancel":
        return "已取消"
    return "未知"


def make_record(model_name, record_id):
    day = record_id % 365
    business_date = None if record_id % 10_000 == 0 else date(2026, 1, 1) + timedelta(days=day)
    system_state = ("draft", "sale", "cancel")[record_id % 3]
    relevance = 100 - (record_id % 5) * 10
    return {
        "business_resource": "订单",
        "technical_model": model_name,
        "record_id": record_id,
        "title": f"{model_name} Order {record_id:06d}",
        "business_date": business_date.isoformat() if business_date else None,
        "system_state": system_state,
        "business_state": state_mapping(model_name, system_state),
        "snapshot": {
            "title": f"{model_name} Order {record_id:06d}",
            "partner": f"Partner {record_id % 1000:04d}",
            "amount": round(100 + (record_id % 10000) / 100, 2),
        },
        "relevance": relevance,
    }


def sort_key(record):
    return (
        record["business_date"] is None,
        -record["relevance"],
        -(date.fromisoformat(record["business_date"]).toordinal())
        if record["business_date"]
        else 0,
        MODEL_PRIORITY[record["technical_model"]],
        record["record_id"],
    )


def validate_priorities(priorities):
    values = list(priorities.values())
    return len(values) == len(set(values))


models = ["sale.order", "purchase.order"]
model_metadata = {}
for model_name in models:
    model = env[model_name]
    fields = model.fields_get()
    model_metadata[model_name] = {
        "title_field": "name" in fields,
        "business_date_field": "date_order" in fields,
        "state_field": "state" in fields,
        "snapshot_fields": all(field in fields for field in ["name", "partner_id", "amount_total"]),
        "field_names": ["name", "date_order", "state", "partner_id", "amount_total"],
    }

records = [
    make_record(model_name, record_id)
    for model_name in models
    for record_id in range(1, ROWS_PER_MODEL + 1)
]
ordered_first = sorted(records, key=sort_key)
ordered_second = sorted(records, key=sort_key)

duplicate_path_hits = [
    (record["business_resource"], record["technical_model"], record["record_id"])
    for record in ordered_first[:100]
] * 2
unique_identities = set(duplicate_path_hits)
sale_count = len(
    {
        (record["business_resource"], record["technical_model"], record["record_id"])
        for record in records
        if record["technical_model"] == "sale.order"
    }
)
purchase_count = len(
    {
        (record["business_resource"], record["technical_model"], record["record_id"])
        for record in records
        if record["technical_model"] == "purchase.order"
    }
)

same_score_group = [
    record
    for record in ordered_first
    if record["relevance"] == 100 and record["business_date"] == ordered_first[0]["business_date"]
][:20]
empty_start = next(
    index for index, record in enumerate(ordered_first) if record["business_date"] is None
)
output = {
    "spike": "SPIKE-GS-08",
    "seed": SEED,
    "rows_per_model": ROWS_PER_MODEL,
    "rows_total": len(records),
    "composite_resource": {
        "name": "订单",
        "models": models,
        "priorities": MODEL_PRIORITY,
    },
    "model_metadata": model_metadata,
    "mapping_complete": all(all(item.values()) for item in model_metadata.values()),
    "priority_validation": {
        "valid_unique": validate_priorities(MODEL_PRIORITY),
        "duplicate_rejected": not validate_priorities({"sale.order": 1, "purchase.order": 1}),
    },
    "ordering": {
        "sample_top_20": ordered_first[:20],
        "stable_repeat": ordered_first == ordered_second,
        "empty_date_first_index": empty_start,
        "non_empty_before_empty": all(
            record["business_date"] is not None for record in ordered_first[:empty_start]
        ),
        "same_score_group_record_ids": [record["record_id"] for record in same_score_group],
    },
    "counting": {
        "sale_category_count": sale_count,
        "purchase_category_count": purchase_count,
        "all_count": sale_count + purchase_count,
        "duplicate_path_hits": len(duplicate_path_hits),
        "unique_result_identity_count": len(unique_identities),
        "identity_dedup_correct": len(unique_identities) == 100,
        "all_equals_category_sum": sale_count + purchase_count == len(records),
    },
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")
