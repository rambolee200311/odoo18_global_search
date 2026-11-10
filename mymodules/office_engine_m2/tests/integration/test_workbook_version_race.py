"""Approved-database race harness for two independent Odoo cursors.

Run only against a non-production test DB permitted by CC-M2-CB-02 v0.3.1,
after the module is installed and synthetic fixtures are available. This file
intentionally is not imported by TransactionCase: a sequential test transaction
cannot prove database locking.
"""

import concurrent.futures
import threading


def race_accept_two_candidates(registry, uid, context, accept_candidate, candidate_ids):
    if len(candidate_ids) != 2:
        raise ValueError("exactly two competing candidates are required")
    gate = threading.Barrier(2)

    def worker(candidate_id):
        cursor = registry.cursor()
        backend_pid = False
        try:
            from odoo import api
            cursor.execute("SET LOCAL lock_timeout = '10s'")
            cursor.execute("SET LOCAL statement_timeout = '30s'")
            backend_pid = cursor._cnx.get_backend_pid()
            env = api.Environment(cursor, uid, context)
            gate.wait(timeout=10)
            result = accept_candidate(env, candidate_id)
            cursor.commit()
            return ("accepted", result.id, backend_pid, False)
        except Exception as exc:
            cursor.rollback()
            from odoo.exceptions import ValidationError
            from psycopg2.errors import SerializationFailure

            if isinstance(exc, ValidationError) and "WORKBOOK_VERSION_STALE" in str(exc):
                return ("stale", type(exc).__name__, backend_pid, str(exc)[:256])
            if isinstance(exc, SerializationFailure):
                return ("serialization_conflict", type(exc).__name__, backend_pid, str(exc)[:256])
            return ("error", type(exc).__name__, backend_pid, str(exc)[:256])
        finally:
            cursor.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, candidate_ids))
    accepted = [item for item in outcomes if item[0] == "accepted"]
    rejected = [item for item in outcomes if item[0] in {"stale", "serialization_conflict"}]
    unexpected = [item for item in outcomes if item[0] not in {"accepted", "stale", "serialization_conflict"}]
    if len(accepted) != 1 or len(rejected) != 1 or unexpected:
        raise AssertionError(f"expected one winner and one stale/revision loser, got {outcomes!r}")
    return outcomes
