import json
import random
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_02_entity_resolution"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
SEED = 20261002
TOTAL = 1000
MARKER = "GS02-"

random.seed(SEED)
Partner = env["res.partner"]
existing = Partner.search([("ref", "=ilike", f"{MARKER}%")])
existing_refs = set(existing.mapped("ref"))

vals_list = []
for index in range(1, TOTAL + 1):
    group = ((index - 1) % 50) + 1
    ref = f"{MARKER}ENT-{index:04d}"
    if ref in existing_refs:
        continue
    vals_list.append(
        {
            "name": f"GS02 Entity {group:02d} Logistics",
            "ref": ref,
            "comment": (
                f"GS02 marker; Short: E{group:02d}; "
                f"Alias: E{group:02d}; "
                f"Pinyin: shanghai wuliu {group:02d}; "
                f"Address: GS02 Zone {index % 10}"
            ),
            "company_type": "company",
        }
    )

created = 0
for start in range(0, len(vals_list), 100):
    created += len(Partner.create(vals_list[start : start + 100]))
env.cr.commit()

result = {
    "spike": "SPIKE-GS-02",
    "seed": SEED,
    "database": env.cr.dbname,
    "uid": env.uid,
    "rows_requested": TOTAL,
    "rows_created": created,
    "rows_total": Partner.search_count([("ref", "=ilike", f"{MARKER}%")]),
    "data_marker": MARKER,
    "orm_write": True,
}
(RESULTS / "simulation_result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "simulation_result.json")
