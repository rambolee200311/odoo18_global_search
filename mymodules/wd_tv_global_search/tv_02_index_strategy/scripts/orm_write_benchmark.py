import json
import time

PREFIX = "TV02-WRITE-"
ROWS = 1000
model = env["res.partner"]

existing = model.search([("ref", "=ilike", f"{PREFIX}%")])
if existing:
    existing.unlink()
    env.cr.commit()

values = [
    {
        "name": f"{PREFIX}{index:04d}",
        "ref": f"{PREFIX}{index:04d}",
        "email": f"tv02-write-{index:04d}@example.invalid",
        "company_type": "company",
    }
    for index in range(ROWS)
]
started = time.perf_counter()
records = model.create(values)
env.cr.commit()
create_seconds = time.perf_counter() - started

started = time.perf_counter()
records.unlink()
env.cr.commit()
unlink_seconds = time.perf_counter() - started

print(
    json.dumps(
        {
            "rows": ROWS,
            "create_seconds": round(create_seconds, 6),
            "unlink_seconds": round(unlink_seconds, 6),
        }
    )
)
