import json
import os
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from odoo.api import Environment

BASE = Path.cwd() / "mymodules/wd_tv_global_search/tv_03_freshness"
RESULT_PATH = BASE / "results" / "freshness_result.json"
PREFIX = "TV03-"
SAMPLES = 20
BATCH_SIZE = 100


def percentile(values, fraction):
    ordered = sorted(values)
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


def cleanup():
    records = env["res.partner"].search([("ref", "=ilike", f"{PREFIX}%")])
    if records:
        records.unlink()
        env.cr.commit()


def read_visible(ref, expected_name=None):
    with env.registry.cursor() as cursor:
        reader = Environment(cursor, env.uid, {})
        domain = [("ref", "=", ref)]
        if expected_name is not None:
            domain.append(("name", "=", expected_name))
        return bool(reader["res.partner"].search(domain, limit=1))


def create_one(index):
    ref = f"{PREFIX}CREATE-{index:04d}"
    name = f"{PREFIX}Created {index:04d}"
    started = time.perf_counter_ns()
    record = env["res.partner"].create(
        {"name": name, "ref": ref, "email": f"{ref.lower()}@example.invalid"}
    )
    env.cr.commit()
    committed = time.perf_counter_ns()
    visible = read_visible(ref, name)
    observed = time.perf_counter_ns()
    return {
        "ref": ref,
        "record_id": record.id,
        "commit_to_search_ms": (observed - committed) / 1_000_000,
        "visible": visible,
        "operation_elapsed_ms": (observed - started) / 1_000_000,
    }


def update_one(index):
    ref = f"{PREFIX}UPDATE-{index:04d}"
    old_name = f"{PREFIX}Before {index:04d}"
    new_name = f"{PREFIX}After {index:04d}"
    record = env["res.partner"].create({"name": old_name, "ref": ref})
    env.cr.commit()
    record.write({"name": new_name})
    env.cr.commit()
    committed = time.perf_counter_ns()
    visible = read_visible(ref, new_name)
    old_visible = read_visible(ref, old_name)
    observed = time.perf_counter_ns()
    record.unlink()
    env.cr.commit()
    return {
        "ref": ref,
        "commit_to_search_ms": (observed - committed) / 1_000_000,
        "new_value_visible": visible,
        "old_value_visible": old_visible,
    }


def delete_one(index):
    ref = f"{PREFIX}DELETE-{index:04d}"
    record = env["res.partner"].create({"name": ref, "ref": ref})
    env.cr.commit()
    record.unlink()
    env.cr.commit()
    committed = time.perf_counter_ns()
    visible = read_visible(ref)
    observed = time.perf_counter_ns()
    return {
        "ref": ref,
        "commit_to_search_ms": (observed - committed) / 1_000_000,
        "still_visible": visible,
    }


def batch_create():
    refs = [f"{PREFIX}BATCH-CREATE-{index:04d}" for index in range(BATCH_SIZE)]
    values = [{"name": ref, "ref": ref} for ref in refs]
    env["res.partner"].create(values)
    env.cr.commit()
    committed = time.perf_counter_ns()
    visible = env["res.partner"].search_count([("ref", "in", refs)])
    observed = time.perf_counter_ns()
    env["res.partner"].search([("ref", "in", refs)]).unlink()
    env.cr.commit()
    return {
        "rows": BATCH_SIZE,
        "commit_to_search_ms": (observed - committed) / 1_000_000,
        "visible_rows": visible,
    }


def batch_update():
    refs = [f"{PREFIX}BATCH-UPDATE-{index:04d}" for index in range(BATCH_SIZE)]
    records = env["res.partner"].create([{"name": ref, "ref": ref} for ref in refs])
    env.cr.commit()
    records.write({"comment": "TV03 batch update"})
    env.cr.commit()
    committed = time.perf_counter_ns()
    visible = env["res.partner"].search_count(
        [("ref", "in", refs), ("comment", "=", "TV03 batch update")]
    )
    observed = time.perf_counter_ns()
    records.unlink()
    env.cr.commit()
    return {
        "rows": BATCH_SIZE,
        "commit_to_search_ms": (observed - committed) / 1_000_000,
        "visible_rows": visible,
    }


def batch_delete():
    refs = [f"{PREFIX}BATCH-DELETE-{index:04d}" for index in range(BATCH_SIZE)]
    records = env["res.partner"].create([{"name": ref, "ref": ref} for ref in refs])
    env.cr.commit()
    records.unlink()
    env.cr.commit()
    committed = time.perf_counter_ns()
    visible = env["res.partner"].search_count([("ref", "in", refs)])
    observed = time.perf_counter_ns()
    return {
        "rows": BATCH_SIZE,
        "commit_to_search_ms": (observed - committed) / 1_000_000,
        "visible_rows": visible,
    }


def concurrent_reads():
    refs = [f"{PREFIX}CONCURRENT-{index:04d}" for index in range(SAMPLES)]
    env["res.partner"].create([{"name": ref, "ref": ref} for ref in refs])
    env.cr.commit()
    committed = time.perf_counter_ns()

    def read(ref):
        started = time.perf_counter_ns()
        with env.registry.cursor() as cursor:
            reader = Environment(cursor, env.uid, {})
            visible = bool(
                reader["res.partner"].search([("ref", "=", ref)], limit=1)
            )
        return (time.perf_counter_ns() - started) / 1_000_000, visible

    errors = 0
    values = []
    visible = 0
    with ThreadPoolExecutor(max_workers=SAMPLES) as executor:
        for future in [executor.submit(read, ref) for ref in refs]:
            try:
                elapsed, is_visible = future.result()
                values.append(elapsed)
                visible += int(is_visible)
            except Exception:
                errors += 1
    env["res.partner"].search([("ref", "in", refs)]).unlink()
    env.cr.commit()
    return {
        "requests": SAMPLES,
        "errors": errors,
        "error_rate": errors / SAMPLES,
        "visible_rows": visible,
        "timing": summary([value / 1000 for value in values]),
        "commit_to_first_observation_ms": (time.perf_counter_ns() - committed) / 1_000_000,
    }


def configuration_capability():
    module_installed = bool(
        env["ir.module.module"].search(
            [("name", "=", "wd_global_search"), ("state", "=", "installed")],
            limit=1,
        )
    )
    config_models = [
        name
        for name in env.registry.models
        if "global" in name and ("config" in name or "resource" in name)
    ]
    return {
        "status": "VERIFIED" if module_installed and config_models else "NOT_VERIFIED",
        "module_installed": module_installed,
        "candidate_models": sorted(config_models),
        "reason": (
            "No wd_global_search configuration model or publish API is available"
            if not module_installed or not config_models
            else None
        ),
    }


def main():
    cleanup()
    try:
        creates = [create_one(index) for index in range(SAMPLES)]
        updates = [update_one(index) for index in range(SAMPLES)]
        deletes = [delete_one(index) for index in range(SAMPLES)]
        batch = {
            "create": batch_create(),
            "update": batch_update(),
            "delete": batch_delete(),
        }
        concurrent = concurrent_reads()
        result = {
            "tv": "TV-03",
            "database": env.cr.dbname,
            "uid": env.uid,
            "environment": {
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
            },
            "target_ms": 5000,
            "single": {
                "create": {"samples": creates, "timing": summary([x["commit_to_search_ms"] / 1000 for x in creates])},
                "update": {"samples": updates, "timing": summary([x["commit_to_search_ms"] / 1000 for x in updates])},
                "delete": {"samples": deletes, "timing": summary([x["commit_to_search_ms"] / 1000 for x in deletes])},
            },
            "batch": batch,
            "concurrent": concurrent,
            "configuration_publish": configuration_capability(),
            "configuration_deactivate": configuration_capability(),
        }
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(RESULT_PATH)
    finally:
        cleanup()


main()
