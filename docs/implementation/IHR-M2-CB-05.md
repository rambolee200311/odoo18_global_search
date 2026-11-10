# IHR-M2-CB-05 — Existing Retriever Integration

**Status:** FINAL ACCEPTED — CC-05 TECHNICAL IMPLEMENTATION SCOPE
**Date:** 2026-11-10
**Authority:** Owner instruction “批准冻结cc-05，进入实施”
**Contract:** `CC-M2-CB-05_Existing_Retriever_Integration_v0.2.2.md` — FROZEN / CODING AUTHORIZED

## Implementation Record

- Repository branch: `main`
- HEAD at implementation start: `f9801fca76f7c248a9cc823c583138ab0191b978`
- The working tree already contained extensive unrelated modifications and untracked files. They were preserved; no stage, commit, reset, clean, or push was performed.
- No database, Odoo service, module upgrade, Provider, or business record was accessed or changed.

## Changes

1. `office` Tool schema now exposes `action="retrieve"` and a bounded `query_spec` matching the existing Retriever inputs.
2. The dispatcher routes `retrieve` before `_resolve_current`, so read-only retrieval does not require Current, Last Valid, or Document Revision state.
3. The route resolves the active Retriever bound to the same Thread and calls its existing `.with_context(message=tool_message).execute(...)` path under the current user. It does not call ORM search/read itself, use `sudo()`, or change the Retriever implementation.
4. M2 adds `id` to a non-empty field projection when absent. Paginated reads with no explicit ordering use `id`; M1 defaults and direct results remain unchanged.
5. Results carry the Retriever data unchanged with lightweight query scope and UTC retrieval time. Invalid or unavailable queries do not become successful empty results.
6. Agent instructions now direct post-Current Odoo data refresh requests through `office(action="retrieve")`, then through the existing edit/review flow.
7. Added TransactionCase coverage, including a two-stage Automated User Simulation that reads test contacts, produces two Mock Candidates, and accepts them through the normal Office service path.

## Runtime and HVR Boundary — Initial Coding Turn (Historical)

CC §13 requires separate environment authorization for database-backed TransactionCase/HVR work. This implementation turn did not receive authorization specifying a test database and permitted test-data writes. Therefore no Odoo TransactionCase, module upgrade, or HVR was run. The test source and report skeleton are not execution evidence.

The paired HVR TDD/Plan successor documents remain DRAFT. The frozen CC §11 HVR requirement governs this implementation as recorded by the owner-freeze note in the CC.

## Runtime Addendum — 2026-11-10

- The owner subsequently authorized CC-05 TransactionCase and Automated User Simulation on the existing development database `odoo18ce`; no database was created. The test command explicitly used `-d odoo18ce`, matching `db_name=odoo18ce` in `odoo.conf`.
- Odoo 18 / Python 3.11.9 test runner updated `office_engine_m2` and ran the five CC-05 TransactionCase methods plus eight existing M1 Retriever regressions. Final `odoo.tests.result`: **0 failed, 0 errors of 13 tests**. 8091 was not restarted; the test runner used an OS-assigned loopback port. No real Provider was called.
- The first actual test run exposed one incorrect test expectation: it hard-coded the initial Document Revision as 1 although the fixture baseline was 0. The assertion was corrected to compare with the captured pre-read value. Production code and M1 Retriever code were not changed for this failure. The first-failure log was preserved.
- The Automated User Simulation passed both retrieval/edit/accept stages. Exact Thread/Session, synthetic contact IDs, Candidate IDs, Current/Last Valid pointers, Document Revisions, source/output SHA-256 values and addresses are recorded in the HVR report and `evidence/CB-M2-CB-05/cc05_artifact_run_20261110.log`.
- V1, V2 and V3 XLSX bytes were saved as synthetic evidence and independently read with ZIP/openpyxl checks; A–C was preserved and D addresses matched. The TransactionCase rolled back created ORM contacts and Office records. The local synthetic XLSX evidence remains under `evidence/CB-M2-CB-05/hvr_artifacts_20261110/`.
- ATR and HVR contain the run command, test split, first failure and correction, final result, artifact index and scope limitations. The owner subsequently marked the CC-05 technical implementation scope **Final Accepted** on 2026-11-10; production release remains separate.
