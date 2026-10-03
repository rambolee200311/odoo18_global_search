import json
import re
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_02_entity_resolution"
RESULTS = ROOT / "results"
MARKER = "GS02-"
THRESHOLD = 30
CANDIDATE_LIMIT = 10


def normalize(value):
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def score_record(record, query):
    query_raw = (query or "").strip()
    query_norm = normalize(query)
    name_raw = (record.name or "").strip()
    name = normalize(name_raw)
    comment = normalize(record.comment)
    fields = []
    score = 0
    if query_raw == (record.ref or "").strip():
        fields.append("identifier_exact")
        score = max(score, 110)
    if query_raw == name_raw:
        fields.append("name_exact")
        score = max(score, 100)
    elif query_norm == name:
        fields.append("name_case_normalized")
        score = max(score, 95)
    if re.search(rf"\bshort:\s*{re.escape(query_norm)}\b", comment):
        fields.append("short_name")
        score = max(score, 80)
    if re.search(rf"\balias:\s*{re.escape(query_norm)}\b", comment):
        fields.append("alias")
        score = max(score, 70)
    if re.search(rf"\bpinyin:\s*{re.escape(query_norm)}\b", comment):
        fields.append("pinyin_approximate")
        score = max(score, 60)
    if len(fields) > 1:
        score += min((len(fields) - 1) * 10, 20)
    return score, fields


def resolve(records, query):
    scored = []
    for record in records:
        score, fields = score_record(record, query)
        if score:
            scored.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "ref": record.ref,
                    "score": score,
                    "matched_fields": fields,
                }
            )
    scored.sort(key=lambda item: (-item["score"], item["id"]))
    top_score = scored[0]["score"] if scored else 0
    second_score = scored[1]["score"] if len(scored) > 1 else 0
    margin = top_score - second_score
    decision = classify(len(scored), margin)
    return {
        "query": query,
        "decision": decision,
        "top_score": top_score,
        "second_score": second_score,
        "margin": margin,
        "candidate_count": len(scored),
        "returned_candidates": scored[:CANDIDATE_LIMIT],
        "has_more": len(scored) > CANDIDATE_LIMIT,
        "threshold": THRESHOLD,
        "candidate_limit": CANDIDATE_LIMIT,
    }


def classify(candidate_count, margin):
    if candidate_count == 0:
        return "no_match"
    if candidate_count == 1 or margin >= THRESHOLD:
        return "unique_match"
    return "candidate_list"


Partner = env["res.partner"]
records = Partner.search([("ref", "=ilike", f"{MARKER}%")], order="id asc")
queries = [
    {"name": "unique_identifier", "value": "GS02-ENT-0001"},
    {"name": "exact_name", "value": "GS02 Entity 01 Logistics"},
    {"name": "abbreviation", "value": "E01"},
    {"name": "alias", "value": "E01"},
    {"name": "pinyin_approximate", "value": "shanghai wuliu 01"},
    {"name": "case_difference", "value": "gs02 entity 01 logistics"},
    {"name": "ambiguous_name", "value": "GS02 Entity 01 Logistics"},
]

results = []
for item in queries:
    first = resolve(records, item["value"])
    second = resolve(records, item["value"])
    results.append(
        {
            "name": item["name"],
            "value": item["value"],
            "resolution": first,
            "stable_repeat": first == second,
        }
    )

multi_field = resolve(records, "E01")
same_input_runs = [resolve(records, "E01") for _ in range(5)]
output = {
    "spike": "SPIKE-GS-02",
    "database": env.cr.dbname,
    "uid": env.uid,
    "records_loaded": len(records),
    "threshold": THRESHOLD,
    "candidate_limit": CANDIDATE_LIMIT,
    "queries": results,
    "multi_field_example": multi_field,
    "threshold_boundary_tests": [
        {
            "margin": 30,
            "decision": classify(2, 30),
            "expected": "unique_match",
        },
        {
            "margin": 29,
            "decision": classify(2, 29),
            "expected": "candidate_list",
        },
    ],
    "same_input_stable": all(run == same_input_runs[0] for run in same_input_runs),
    "scoring_order": [
        "name_exact",
        "name_case_normalized",
        "short_name",
        "alias",
        "pinyin_approximate",
    ],
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")
