import json
import os
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from odoo.api import Environment

SEED = 20261002
MARKER = "TV01-"
BASE = Path.cwd() / "mymodules/wd_tv_global_search/tv_01_nfr_001_performance"
RESULT_PATH = BASE / "results" / "performance_result.json"
GENERATION_PATH = BASE / "results" / "generation_result.json"

QUERIES = [
    ("res.partner", "ref", "=", f"{MARKER}PARTNER-0000001"),
    ("res.partner", "ref", "=ilike", f"{MARKER}PARTNER-0000001%"),
    ("res.partner", "ref", "ilike", f"%{MARKER}PARTNER%"),
    ("sale.order", "client_order_ref", "=", f"{MARKER}SALE-0000001"),
    ("sale.order", "client_order_ref", "=ilike", f"{MARKER}SALE-0000001%"),
    ("sale.order", "client_order_ref", "ilike", f"%{MARKER}SALE%"),
    ("purchase.order", "partner_ref", "=", f"{MARKER}PURCHASE-0000001"),
    ("purchase.order", "partner_ref", "=ilike", f"{MARKER}PURCHASE-0000001%"),
    ("purchase.order", "partner_ref", "ilike", f"%{MARKER}PURCHASE%"),
    ("account.move", "ref", "=", f"{MARKER}INV-0000001"),
    ("account.move", "ref", "=ilike", f"{MARKER}INV-0000001%"),
    ("account.move", "ref", "ilike", f"%{MARKER}INV%"),
    ("product.product", "default_code", "=", f"{MARKER}PROD-0000001"),
    ("product.product", "default_code", "=ilike", f"{MARKER}PROD-0000001%"),
    ("product.product", "default_code", "ilike", f"%{MARKER}PROD%"),
    ("project.task", "name", "=", f"{MARKER}TASK-0000001"),
    ("project.task", "name", "=ilike", f"{MARKER}TASK-0000001%"),
    ("project.task", "name", "ilike", f"%{MARKER}TASK%"),
]


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]


def summary(values):
    milliseconds = [value * 1000 for value in values]
    return {
        "count": len(milliseconds),
        "p50_ms": round(percentile(milliseconds, 0.50), 3),
        "p95_ms": round(percentile(milliseconds, 0.95), 3),
        "p99_ms": round(percentile(milliseconds, 0.99), 3),
        "max_ms": round(max(milliseconds), 3),
    }


def timed_search(model, field, operator, value, limit):
    started = time.perf_counter()
    count = len(model.search([(field, operator, value)], limit=limit))
    return time.perf_counter() - started, count


def run_query(env, query, limit):
    model_name, field, operator, value = query
    if model_name not in env.registry.models:
        return {"status": "MODEL_MISSING", "query": query}
    timings = []
    counts = []
    for _ in range(20):
        elapsed, count = timed_search(env[model_name], field, operator, value, limit)
        timings.append(elapsed)
        counts.append(count)
    return {
        "status": "OK",
        "query": query,
        "limit": limit,
        "result_count": sorted(set(counts)),
        "timing": summary(timings),
    }


def run_parallel(env, query_set, limit, requests=20):
    available = [query for query in query_set if query[0] in env.registry.models]
    jobs = [available[index % len(available)] for index in range(requests)]

    def execute(query):
        with env.registry.cursor() as cursor:
            thread_env = Environment(cursor, env.uid, {})
            started = time.perf_counter()
            thread_env[query[0]].search([(query[1], query[2], query[3])], limit=limit)
            return time.perf_counter() - started

    errors = 0
    timings = []
    with ThreadPoolExecutor(max_workers=requests) as executor:
        futures = [executor.submit(execute, query) for query in jobs]
        for future in futures:
            try:
                timings.append(future.result())
            except Exception:
                errors += 1
    return {
        "requests": requests,
        "errors": errors,
        "error_rate": round(errors / requests, 6),
        "timing": summary(timings) if timings else None,
    }


def run_relation(env):
    if "sale.order" not in env.registry.models:
        return {"status": "MODEL_MISSING"}
    partner = env["res.partner"].search([("ref", "=", f"{MARKER}PARTNER-0000001")], limit=1)
    if not partner:
        return {"status": "NO_FIXTURE"}
    timings = []
    counts = []
    for _ in range(20):
        started = time.perf_counter()
        orders = env["sale.order"].search([("partner_id", "=", partner.id)])
        related_partners = orders.mapped("partner_id").filtered(lambda record: record.id == partner.id)
        timings.append(time.perf_counter() - started)
        counts.append(len(related_partners))
    return {"status": "OK", "timing": summary(timings), "result_counts": sorted(set(counts))}


def main():
    if not GENERATION_PATH.exists():
        raise RuntimeError("generation_result.json is missing; run data/generate.py first")
    generation = json.loads(GENERATION_PATH.read_text(encoding="utf-8"))
    if generation["database"] != env.cr.dbname:
        raise RuntimeError("Generation and execution databases differ")
    serial_first = [run_query(env, query, 50) for query in QUERIES]
    serial_complete = [run_query(env, query, False) for query in QUERIES]
    parallel_first = run_parallel(env, QUERIES, 50)
    parallel_complete = run_parallel(env, QUERIES, False)
    relation = run_relation(env)
    result = {
        "tv": "TV-01",
        "seed": SEED,
        "database": env.cr.dbname,
        "uid": env.uid,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "nfr_target": {
            "logical_resources": 10,
            "rows_per_resource": 1000000,
            "concurrency": 20,
            "first_result_p95_ms": 2000,
            "complete_result_p95_ms": 5000,
            "error_rate_max": 0.01,
        },
        "serial_first_result": serial_first,
        "serial_complete_result": serial_complete,
        "parallel_first_result": parallel_first,
        "parallel_complete_result": parallel_complete,
        "relation_depth_2": relation,
        "cold_cache": {"status": "NOT_VERIFIED", "reason": "Cache clearing is outside ORM-only TV scope"},
        "record_rule_overhead": {"status": "NOT_VERIFIED", "reason": "Dedicated restricted user fixture is required"},
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(RESULT_PATH)


main()
