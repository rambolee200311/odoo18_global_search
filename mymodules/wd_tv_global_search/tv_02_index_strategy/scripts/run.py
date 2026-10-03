import json
import os
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RESULT_PATH = BASE / "results" / "index_strategy_result.json"
EVIDENCE_DIR = BASE / "evidence"
DB = os.environ.get("TV_DB", "wd_tv_gs01_20261002_100k")
PSQL = os.environ.get("PSQL", "/Library/PostgreSQL/16/bin/psql")
DB_ENV = {**os.environ, "PGPASSWORD": os.environ.get("PGPASSWORD", "odoo")}
ROOT = BASE.parents[2]
TABLE = "res_partner"
COLUMN = "ref"
DEFAULT_INDEX = "res_partner__ref_index"
TEMP_INDEXES = [
    "tv02_ref_btree_idx",
    "tv02_ref_pattern_idx",
    "tv02_ref_gin_idx",
    "tv02_ref_gist_idx",
]

QUERIES = {
    "exact": "SELECT id FROM res_partner WHERE ref = 'TV01-PARTNER-0000001'",
    "prefix": "SELECT id FROM res_partner WHERE ref LIKE 'TV01-PARTNER-0000001%'",
    "contains": "SELECT id FROM res_partner WHERE ref LIKE '%PARTNER-0000%'",
}

STRATEGIES = {
    "no_index": None,
    "btree": "CREATE INDEX tv02_ref_btree_idx ON res_partner USING btree (ref)",
    "pattern_ops": (
        "CREATE INDEX tv02_ref_pattern_idx "
        "ON res_partner USING btree (ref text_pattern_ops)"
    ),
    "gin_trgm": (
        "CREATE INDEX tv02_ref_gin_idx "
        "ON res_partner USING gin (ref gin_trgm_ops)"
    ),
    "gist_trgm": (
        "CREATE INDEX tv02_ref_gist_idx "
        "ON res_partner USING gist (ref gist_trgm_ops)"
    ),
}


def psql(sql, json_output=False):
    command = [PSQL, "-h", "127.0.0.1", "-p", "5555", "-U", "odoo", "-d", DB]
    if json_output:
        command.extend(["-At", "-c", sql])
    else:
        command.extend(["-v", "ON_ERROR_STOP=1", "-c", sql])
    completed = subprocess.run(
        command,
        env=DB_ENV,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def explain(query):
    sql = (
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
        + query.rstrip(";")
        + ";"
    )
    raw = psql(sql, json_output=True)
    return json.loads(raw)[0]["Plan"]


def find_nodes(plan):
    nodes = [plan["Node Type"]]
    for child in plan.get("Plans", []):
        nodes.extend(find_nodes(child))
    return nodes


def measure(query):
    for _ in range(5):
        explain(query)
    plans = [explain(query) for _ in range(20)]
    timings = [plan["Actual Total Time"] for plan in plans]
    ordered = sorted(timings)

    def percentile(fraction):
        return round(ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))], 3)

    return {
        "samples": len(timings),
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
        "max_ms": round(max(timings), 3),
        "plans": [
            {
                "execution_ms": plan["Actual Total Time"],
                "planning_ms": plan.get("Planning Time"),
                "nodes": find_nodes(plan),
                "shared_hit_blocks": plan.get("Shared Hit Blocks", 0),
                "shared_read_blocks": plan.get("Shared Read Blocks", 0),
            }
            for plan in plans
        ],
    }


def index_sizes():
    names = [DEFAULT_INDEX, *TEMP_INDEXES]
    rows = psql(
        "SELECT indexrelname, pg_relation_size(indexrelid) "
        "FROM pg_stat_user_indexes "
        f"WHERE relname = '{TABLE}' "
        f"AND indexrelname IN ({','.join(repr(name) for name in names)}) "
        "ORDER BY indexrelname;",
        json_output=True,
    )
    return [
        {"index": row.split("|", 1)[0], "bytes": int(row.split("|", 1)[1])}
        for row in rows.splitlines()
        if "|" in row
    ]


def current_index_size(index_name):
    return int(
        psql(
            f"SELECT pg_relation_size('{index_name}'::regclass);",
            json_output=True,
        )
    )


def create_index(statement):
    started = time.perf_counter()
    psql(statement)
    return round(time.perf_counter() - started, 3)


def orm_write_benchmark():
    command = [
        str(ROOT / "venv/bin/python"),
        "odoo-bin",
        "shell",
        "-c",
        "odoo.conf",
        "-d",
        DB,
        "--no-http",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=DB_ENV,
        input=(BASE / "scripts/orm_write_benchmark.py").read_text(),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def selectivity_plans():
    values = [
        ("nine_rows", "TV01-PARTNER-000000%"),
        ("ninety_nine_rows", "TV01-PARTNER-00000%"),
        ("nine_hundred_ninety_nine_rows", "TV01-PARTNER-0000%"),
        ("all_rows", "TV01-PARTNER-%"),
    ]
    output = {}
    for strategy, statement in (
        ("btree", STRATEGIES["btree"]),
        ("pattern_ops", STRATEGIES["pattern_ops"]),
        ("gin_trgm", STRATEGIES["gin_trgm"]),
    ):
        psql("DROP INDEX IF EXISTS tv02_ref_btree_idx, tv02_ref_pattern_idx, tv02_ref_gin_idx, tv02_ref_gist_idx;")
        create_index(statement)
        output[strategy] = {}
        for label, value in values:
            plan = explain(
                f"SELECT id FROM res_partner WHERE ref LIKE '{value}'"
            )
            output[strategy][label] = {
                "nodes": find_nodes(plan),
                "execution_ms": plan["Actual Total Time"],
            }
    return output


def main():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    psql("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    count = int(psql("SELECT count(*) FROM res_partner WHERE ref LIKE 'TV01-PARTNER-%';", json_output=True))
    if count != 100000:
        raise RuntimeError(f"Expected 100000 TV01 partners, found {count}")

    psql(f"DROP INDEX IF EXISTS {', '.join([DEFAULT_INDEX, *TEMP_INDEXES])};")
    strategy_results = {}
    build_seconds = {}
    strategy_index_sizes = {}
    write_benchmarks = {}
    try:
        for name, statement in STRATEGIES.items():
            if statement:
                build_seconds[name] = create_index(statement)
                strategy_index_sizes[name] = current_index_size(
                    {
                        "btree": "tv02_ref_btree_idx",
                        "pattern_ops": "tv02_ref_pattern_idx",
                        "gin_trgm": "tv02_ref_gin_idx",
                        "gist_trgm": "tv02_ref_gist_idx",
                    }[name]
                )
            else:
                strategy_index_sizes[name] = 0
            write_benchmarks[name] = orm_write_benchmark()
            strategy_results[name] = {
                query_name: measure(query)
                for query_name, query in QUERIES.items()
            }
            evidence_path = EVIDENCE_DIR / f"{name}.json"
            evidence_path.write_text(
                json.dumps(strategy_results[name], indent=2),
                encoding="utf-8",
            )
            psql("DROP INDEX IF EXISTS tv02_ref_btree_idx, tv02_ref_pattern_idx, tv02_ref_gin_idx, tv02_ref_gist_idx;")
        selectivity = selectivity_plans()
        (EVIDENCE_DIR / "selectivity_plans.json").write_text(
            json.dumps(selectivity, indent=2),
            encoding="utf-8",
        )
    finally:
        psql("DROP INDEX IF EXISTS tv02_ref_btree_idx, tv02_ref_pattern_idx, tv02_ref_gin_idx, tv02_ref_gist_idx;")
        psql(
            f"CREATE INDEX IF NOT EXISTS {DEFAULT_INDEX} "
            f"ON {TABLE} USING btree ({COLUMN});"
        )
    index_size_result = index_sizes()

    result = {
        "tv": "TV-02",
        "database": DB,
        "table": TABLE,
        "column": COLUMN,
        "rows": count,
        "postgresql": psql("SELECT current_setting('server_version');", json_output=True),
        "pg_trgm": psql(
            "SELECT extversion FROM pg_extension WHERE extname='pg_trgm';",
            json_output=True,
        ),
        "cache_mode": "warm",
        "cold_cache": {
            "status": "NOT_VERIFIED",
            "reason": "Cache clearing is outside the authorized isolated index run",
        },
        "build_seconds": build_seconds,
        "index_sizes": index_size_result,
        "strategy_index_sizes": strategy_index_sizes,
        "orm_write_benchmarks": write_benchmarks,
        "strategies": strategy_results,
        "selectivity_plans": selectivity,
        "default_index_restored": True,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(RESULT_PATH)


main()
