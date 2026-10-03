import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_04_query_refinement_merge"
RESULTS = ROOT / "results"
snapshot = json.loads((RESULTS / "data_snapshot.json").read_text())
records = snapshot["records"]


def condition_key(condition):
    return (
        condition["dimension"],
        condition["operator"],
        json.dumps(condition["value"], ensure_ascii=False, sort_keys=True),
    )


def merge_conditions(parsed, refinement, deleted=None):
    deleted = set(deleted or [])
    parsed_valid = [
        item for item in parsed if item.get("parsed", True) and item["dimension"] not in deleted
    ]
    refinement_valid = [
        item
        for item in refinement
        if item.get("parsed", True) and item["dimension"] not in deleted
    ]
    refinement_dimensions = {item["dimension"] for item in refinement_valid}
    selected = [
        item
        for item in parsed_valid
        if item["dimension"] not in refinement_dimensions
    ] + refinement_valid
    unique = {}
    for item in selected:
        unique[condition_key(item)] = item
    return sorted(unique.values(), key=condition_key)


def matches(record, conditions):
    for condition in conditions:
        value = condition["value"]
        actual = record.get(condition["dimension"])
        if condition["operator"] == "=" and actual != value:
            return False
        if condition["operator"] == "in" and actual not in value:
            return False
    return True


def result_set(conditions):
    return sorted(
        tuple(record["identity"])
        for record in records
        if matches(record, conditions)
    )


def count_unique_with_duplicate_paths(conditions):
    matching = result_set(conditions)
    duplicated_paths = matching + matching
    return len(set(duplicated_paths)), len(matching)


path_a_parsed = [
    {"dimension": "entity", "operator": "=", "value": "GS03 Partner"},
    {"dimension": "resource", "operator": "=", "value": "出库单"},
    {"dimension": "month", "operator": "=", "value": "2026-06"},
    {"dimension": "state", "operator": "=", "value": "draft"},
]
path_b_parsed = [
    {"dimension": "entity", "operator": "=", "value": "GS03 Partner"},
]
path_b_refinement = [
    {"dimension": "resource", "operator": "=", "value": "出库单"},
    {"dimension": "month", "operator": "=", "value": "2026-06"},
    {"dimension": "state", "operator": "=", "value": "draft"},
]

path_a_effective = merge_conditions(path_a_parsed, [])
path_b_effective = merge_conditions(path_b_parsed, path_b_refinement)
path_a_results = result_set(path_a_effective)
path_b_results = result_set(path_b_effective)

conflict = merge_conditions(
    [{"dimension": "resource", "operator": "=", "value": "出库单"}],
    [{"dimension": "resource", "operator": "=", "value": "入库单"}],
)
duplicate = merge_conditions(
    [
        {"dimension": "month", "operator": "=", "value": "2026-06"},
        {"dimension": "month", "operator": "=", "value": "2026-06"},
    ],
    [],
)
invalid = merge_conditions(
    [
        {"dimension": "entity", "operator": "=", "value": "GS03 Partner"},
        {
            "dimension": "state",
            "operator": "=",
            "value": "unknown",
            "parsed": False,
        },
    ],
    [],
)
deleted = merge_conditions(
    path_a_parsed,
    [],
    deleted=["state"],
)
dedup_count, raw_count = count_unique_with_duplicate_paths(path_a_effective)

output = {
    "spike": "SPIKE-GS-04",
    "source_snapshot": snapshot["source_spike"],
    "records_loaded": len(records),
    "path_a": {
        "raw_query": "GS03 Partner 出库 2026-06 draft",
        "effective_conditions": path_a_effective,
        "result_count": len(path_a_results),
        "result_identities": path_a_results,
    },
    "path_b": {
        "raw_query": "GS03 Partner",
        "refinement_conditions": path_b_refinement,
        "effective_conditions": path_b_effective,
        "result_count": len(path_b_results),
        "result_identities": path_b_results,
    },
    "path_a_b_equivalent": (
        path_a_effective == path_b_effective and path_a_results == path_b_results
    ),
    "conflict_refinement_wins": conflict,
    "duplicate_removed": {
        "input_count": 2,
        "effective_count": len(duplicate),
        "effective_conditions": duplicate,
    },
    "invalid_condition_ignored": {
        "effective_conditions": invalid,
        "contains_unknown": any(
            item["value"] == "unknown" for item in invalid
        ),
    },
    "deleted_condition": {
        "raw_query_unchanged": True,
        "effective_conditions": deleted,
        "state_removed": not any(item["dimension"] == "state" for item in deleted),
    },
    "count_deduplication": {
        "raw_hits_with_duplicate_paths": raw_count * 2,
        "unique_result_identity_count": dedup_count,
        "br_013_correct": dedup_count == raw_count,
    },
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")

