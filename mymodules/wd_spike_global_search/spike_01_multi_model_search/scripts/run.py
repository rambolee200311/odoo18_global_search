import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from odoo.api import Environment

BASE = Path.cwd() / "mymodules/wd_spike_global_search/spike_01_multi_model_search"
CORPUS_PATH = BASE / "results" / "query_corpus.json"
RESULT_PATH = BASE / "results" / "spike_result.json"
SIMULATION_PATH = BASE / "results" / "simulation_result.json"
TARGET_MODELS = [
    "res.partner",
    "sale.order",
    "purchase.order",
    "stock.picking",
    "account.move",
    "product.product",
    "project.task",
    "stock.quant",
]
RELATION_PATHS = [
    ("res.partner", "sale.order"),
    ("res.partner", "purchase.order"),
]


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]


def summarize(values):
    milliseconds = [value * 1000 for value in values]
    return {
        "count": len(milliseconds),
        "p50_ms": round(percentile(milliseconds, 0.50), 3),
        "p95_ms": round(percentile(milliseconds, 0.95), 3),
        "p99_ms": round(percentile(milliseconds, 0.99), 3),
        "max_ms": round(max(milliseconds), 3),
    }


def timed_query(model_env, field, operator, value):
    started = time.perf_counter()
    records = model_env.search([(field, operator, value)], limit=50)
    elapsed = time.perf_counter() - started
    return elapsed, len(records)


def run_serial(env, queries):
    output = []
    for query in queries:
        if query["model"] not in env.registry.models:
            output.append(
                {
                    "query": query,
                    "status": "MODEL_MISSING",
                    "timing": None,
                }
            )
            continue
        timings = []
        counts = []
        for _ in range(20):
            elapsed, count = timed_query(
                env[query["model"]],
                query["field"],
                query["operator"],
                query["value"],
            )
            timings.append(elapsed)
            counts.append(count)
        output.append(
            {
                "query": query,
                "status": "OK",
                "result_count_min": min(counts),
                "result_count_max": max(counts),
                "timing": summarize(timings),
            }
        )
    return output


def concurrent_query(dbname, uid, registry, query):
    with registry.cursor() as cursor:
        thread_env = Environment(cursor, uid, {})
        started = time.perf_counter()
        count = len(
            thread_env[query["model"]].search(
                [(query["field"], query["operator"], query["value"])],
                limit=50,
            )
        )
        return time.perf_counter() - started, count


def run_concurrent(env, queries):
    available = [query for query in queries if query["model"] in env.registry.models]
    if not available:
        return {"status": "NOT_RUN", "reason": "No target model is installed"}
    jobs = [available[index % len(available)] for index in range(20)]
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(
                concurrent_query,
                env.cr.dbname,
                env.uid,
                env.registry,
                query,
            )
            for query in jobs
        ]
        samples = [future.result() for future in futures]
    return {
        "status": "OK",
        "requests": len(samples),
        "result_counts": sorted({count for _, count in samples}),
        "timing": summarize([elapsed for elapsed, _ in samples]),
    }


def main(env):
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    simulation = (
        json.loads(SIMULATION_PATH.read_text(encoding="utf-8"))
        if SIMULATION_PATH.exists()
        else None
    )
    installed_models = {
        model: model in env.registry.models for model in TARGET_MODELS
    }
    model_counts = {
        model: env[model].search_count([])
        for model, available in installed_models.items()
        if available
    }
    relation_paths = [
        {
            "source": source,
            "target": target,
            "status": "AVAILABLE"
            if source in env.registry.models and target in env.registry.models
            else "MODEL_MISSING",
        }
        for source, target in RELATION_PATHS
    ]
    result = {
        "spike": "SPIKE-GS-01",
        "seed": corpus["seed"],
        "database": env.cr.dbname,
        "uid": env.uid,
        "target_models": TARGET_MODELS,
        "installed_models": installed_models,
        "model_counts": model_counts,
        "relation_paths": relation_paths,
        "serial_queries": run_serial(env, corpus["queries"]),
        "concurrent_queries": run_concurrent(env, corpus["queries"]),
        "nfr_profile": {
            "target_resources": 10,
            "target_rows_per_resource": 1000000,
            "target_concurrency": 20,
            "target_first_result_p95_ms": 2000,
            "target_complete_result_p95_ms": 5000,
            "actual_business_data_writes": bool(simulation and simulation["orm_write"]),
            "simulation": simulation,
        },
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(RESULT_PATH)


main(env)
