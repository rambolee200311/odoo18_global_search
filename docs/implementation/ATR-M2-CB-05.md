# ATR-M2-CB-05 — Existing Retriever Integration

**Status:** PASS — CC-05 TransactionCase, Automated User Simulation, and targeted M1 Retriever regression
**Date:** 2026-11-10
**Contract:** CC-M2-CB-05 v0.2.2 FROZEN

## Results

| Check | Result | Evidence / scope |
|---|---|---|
| Python syntax validation | PASS | Original implementation files have `py_compile` evidence in `static-checks-20261110.log`; final test and readback scripts passed `ast.parse`, and the Odoo runner imported and executed the TransactionCase. |
| Whitespace validation | PASS | Original `git diff --check` is in `static-checks-20261110.log`; after runtime evidence edits, a targeted trailing-whitespace scan passed for the changed test/readback scripts and IHR/ATR/HVR/FR documents. |
| CC-05 TransactionCase | PASS | All 5 methods in `TestOfficeRetrieverIntegration` ran on `odoo18ce`; included in final 13-method run. |
| Contact two-stage Automated User Simulation | PASS | Mock Candidate adapter; two Retriever phases in one Thread; both Candidates accepted via `office(action="accept")`; independent XLSX readback passed. This is not browser or real-Provider E2E. |
| Existing M1 Retriever regression | PASS | 8 existing `TestNativeOfficeChatIntegration` Retriever tests ran, 0 failed / 0 errors. |
| Module update | PASS | Odoo test runner updated `office_engine_m2` on `odoo18ce`; no 8091 restart and no new database. |
| Real Provider / Browser | OUT OF SCOPE | Neither was called or used. |

## Test Methods Added

1. Bound Retriever reuse, stable ID projection/order, repeated ID-based reads, and no Current/version prerequisite.
2. Empty results versus missing query and rejected query extensions.
3. Rejection when the caller does not own the Thread.
4. `office.retrieve` schema exposure without a second public Tool.
5. Two-stage contact refresh: two retrieval rounds in one Thread, Mock Candidate generation, formal accepts, and independent XLSX/version readback assertions.

## Runtime Run — 2026-11-10

### Target and command

- Config target: `odoo.conf` has `db_name=odoo18ce`; the Odoo command also explicitly used `-d odoo18ce`.
- Runtime: repository `venv` Python 3.11.9, Odoo 18.0.
- The selected test invocation used `-u office_engine_m2 --test-enable --stop-after-init --no-http --http-interface=127.0.0.1 --http-port=0 --gevent-port=0`. Odoo test mode still starts its test HTTP worker despite `--no-http`; port `0` let the OS assign a temporary loopback port and left 8091 untouched.
- Final log: `evidence/CB-M2-CB-05/cc05_artifact_run_20261110.log`.

### Final test result

- `odoo.tests.result`: **0 failed, 0 errors of 13 tests**; process exit code 0.
- The 13 executed methods comprise all **5 CC-05 TransactionCase methods** and **8 M1 Retriever regression methods**. `tests.stats` reports 17 for this run; the final `tests.result` method count is used as the executed-test count.
- M1 methods: `test_retriever_uses_current_user_model_and_field_rights`, `test_native_retriever_honors_model_limit_for_duplicate_matches`, `test_native_retriever_pages_with_stable_order_and_current_user_count`, `test_office_retriever_supports_acl_readable_relational_fields`, `test_office_retriever_uses_requested_domain_inside_active_session`, `test_office_retriever_allows_acl_readable_records_before_prepare`, `test_office_retriever_uses_native_search_read_for_relation_queries`, and `test_office_retriever_uses_current_user_permissions_without_environment_gate`.
- The first test run reported 1 failure / 0 errors of 13. It was a test assertion assuming a new session's initial `document_revision` was 1; the fixture's actual pre-read value was 0. The test now compares the post-read value to the captured baseline. No production code or M1 Retriever behavior was changed. The original failure remains in `cc05_targeted_20261110.log`; the passing retry and final run are retained separately.
- Runner startup note: the sandbox initially blocked the local DB connection; the authorized retry reached `odoo18ce`. Odoo test mode started an HTTP listener despite `--no-http`, conflicting with the already-running service on its default port. The final runner used only `127.0.0.1` with OS-assigned port `0`; 8091 was not stopped or restarted.
- Odoo's standard test cleanup logged `filestore gc 10 checked, 10 removed` after the final run. The log does not enumerate attachment identifiers, so the exact garbage-collected blob scope is **UNVERIFIED**. No explicit deletion of business attachments or records was issued by this task; no further cleanup or inspection was performed.
- Final run also emitted an explicit HVR line containing Thread/Session, synthetic contact IDs, V1/V2/V3 IDs, acceptance outcomes, revisions, hashes, and addresses.

### Independent workbook readback

- Actual V1 input, V2 Candidate and V3 Candidate bytes produced during the test transaction were saved as synthetic evidence under `evidence/CB-M2-CB-05/hvr_artifacts_20261110/`.
- Independent script: `evidence/CB-M2-CB-05/readback_hvr_artifacts_20261110.py`; output: `evidence/CB-M2-CB-05/hvr_artifacts_20261110_readback.log`.
- V1, V2 and V3 ZIP integrity, `openpyxl` readability, headers and values passed. V3 A–C matches V2; D1:D4 matches the three retrieved addresses. The log records each byte length and SHA-256.
- TransactionCase rolled back the synthetic ORM contacts, Thread, Session, Candidate and attachment rows after the test. The XLSX files are local synthetic evidence, not persistent Odoo business data.
- No real Provider call, real-contact read, browser HVR, 8091 restart, or database creation occurred.

## Acceptance Summary

All CC-05 automated TransactionCase and Automated User Simulation criteria exercised in this run passed, and the selected M1 Retriever compatibility regression passed. This is `READY FOR FINAL ACCEPTANCE` evidence, not an owner-signed Final Accepted decision. Real Provider, browser UI and production release remain outside this CC's acceptance scope.
