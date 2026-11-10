# IHR — CC-M2-CB-04 Intent / Confirmation / Edit Orchestration

## 1. Governance and status

- Frozen contract: [CC-M2-CB-04 v0.2](CC-M2-CB-04_Intent_Confirmation_Edit_Orchestration_v0.2.md).
- Implementation baseline: frozen TDD V2.0.3, Implementation Plan V2.0.2, and the owner-approved CB-02 Intent Binding amendment. The CB-02 amendment's Odoo integration evidence is recorded in `IHR-M2-CB-02.md` / `ATR-M2-CB-02.md`.
- Environment: Odoo 18 CE, project Python 3.11.9, owner-authorized non-production database `odoo18ce`.
- Execution scope: synthetic XLSX and TransactionCase; module upgrade of `office_engine_odoo,office_engine_m2`; no real Provider request, no real business attachment processing, no production data operation, and no Git write operation.
- External-processing policy: the frozen SRS/data-processing gate remains open. `EXTERNAL_PROVIDER_DISPATCH_ENABLED` remains `False`; the public `office` facade stays fail-closed for external editing. Automated orchestration tests inject a Mock adapter and synthetic workbook bytes.
- Historical v0.2 disposition: **READY FOR FINAL ACCEPTANCE — CC-04 local/mock and Odoo integration scope** (see the dated v0.2 run record below).
- Latest v3.0 implementation-test disposition (2026-11-09): **LOCAL/MOCK ACCEPT/REJECT LOOP AND FULL ODOO REGRESSION PASS**. `PARTIALLY_VERIFIED` accept/reject now uses the existing CB-02 service path without changing the grade. Playwright scenarios remain **NOT RUN**; this is not human HVR, real Provider, Finalize, or production acceptance. See §6.5.

## 2. Implementation summary

The implementation adds a generic Intent contract and a service orchestration path that resolves the current authenticated Thread, user message, Session, accepted CB-02 version and actual attachment bytes through ORM. The server binds Intent and Expected Effect to the user message, Thread/Session, parent version, SHA and revision. Confirmation receipts are server-generated and bound to the corresponding Intent/effect and revisions. The service creates Candidates through CB-02, validates them through CB-03, and advances Current only through CB-02's typed acceptance interface when the validated effect is covered by the explicit or confirmed authorization. Failed, stale, rejected, or out-of-scope Candidates do not advance Current.

The only Candidate B Agent facade is `office` with bounded actions. Existing M1 methods and the legacy M1 XML tool registrations remain for compatibility; this work does not claim that the global Office registry has already migrated to a single tool. No change was made to `office_tools.xml`.

The service records unexpected processing exceptions in the server log without exposing exception details or workbook content in the Agent result. M1 Mapping behavior was not intentionally changed; its compatibility assertions ran as part of the full Odoo regression.

## 3. Verification record

### 3.1 Historical v0.2 final passing Odoo run

Command:

```sh
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_odoo,office_engine_m2 --test-enable --test-tags /office_engine_m2,/office_engine_odoo --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/odoo-final-regression.log
```

Observed result:

- Process exit code: `0`.
- `Starting Test` entries: `222`.
- Final `odoo.tests.result`: `0 failed, 0 errors of 222 tests`.
- Module upgrade/load: `office_engine_odoo` and `office_engine_m2` loaded successfully.
- Odoo `tests.stats`: `office_engine_m2: 237`, `office_engine_odoo: 27`. The relationship between these counters and the 222 test methods/final result remains **UNEXPLAINED**; no cause is inferred.
- The full tagged run includes the new Intent/Orchestration TransactionCases and existing M1 Mapping RPC, native chat, RenderBridge, Document Request, attachment and version-service tests. It is not a Browser E2E result.

Focused CC-04 command:

```sh
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2:TestEditOrchestration --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/odoo-orchestration-run6.log
```

Observed result: process exit `0`; 7 `Starting TestEditOrchestration` entries; final result `0 failed, 0 errors of 7 tests`. The module stats line reports 9 and is part of the same unresolved counter discrepancy.

The specific second-version test was rerun after making synthetic package metadata deterministic:

```sh
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2:TestEditOrchestration.test_two_successive_edits_use_successive_accepted_workbook_versions --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/odoo-orchestration-run7.log
```

Observed result: process exit `0`; 1 test method; final result `0 failed, 0 errors of 1 test`.

### 3.2 Static checks and 8091 restoration

- `./venv/bin/python -m compileall -q` on the changed CC-04 service and test Python files: exit `0`.
- `git diff --check`: exit `0`, no output.
- After the test runner stopped, Odoo 8091 was started using the project venv and existing `odoo.conf`. The service log records HTTP service on port 8091 and registry load; a host-network `curl http://127.0.0.1:8091/web/login` returned **HTTP 200**. The first sandboxed curl was blocked by local network isolation; the host-network verification succeeded. No PostgreSQL/5555 check was made.

## 4. Preserved failure-first evidence and repairs

All first-run and intermediate logs are retained in `evidence/CB-M2-CB-04/`; they were not overwritten.

1. The first full upgrade/test run ended with `1 failed, 15 errors of 222 tests`. The diagnostics identified, among other issues, same-transaction lookup of the stored computed `llm_role` before flush, and first-time `office` tool registration not yet being present during that same upgrade's tests. The tool record was available on the subsequent upgrade/test run; M1 tool assertions were updated to include the Candidate B facade while preserving legacy tools.
2. Subsequent targeted tests found a duplicate keyword in result construction; it was corrected by merging the final result fields before serialization.
3. A broad-scope fixture wrote a value to B1 while the declared target was A1:A2; the fixture was corrected to write A2.
4. The second-round fixture declared expected value 15 while requesting/writing 20. The test input was corrected to 20. A later full run then exposed `docProps/core.xml` serializer timestamps as an undeclared package change. The synthetic fixture now normalizes only test-generated core-property timestamps; the Validator rules were not weakened.
5. The first full finalization attempt had only that one timestamp-related failure. The focused test and subsequent complete run passed.

One Odoo test intentionally exercises a duplicate `office_document_request_request_uuid_unique` violation. That logged SQL error is part of the negative test path and is not a test result failure; the final aggregate result is the evidence of pass/fail.

## 5. Open items and evidence limits

- `tests.stats` (237 + 27) versus `Starting Test`/`tests.result` (222) remains **UNEXPLAINED**.
- The test harness emitted warnings about a visible Python child process during worker cleanup. The CB-03 worker reports `worker_exited=True` in its own evidence, but the additional process identity and final cleanup state were not proven. No test failure or confirmed leak is inferred.
- No real OpenAI/Responses request was made. The `office` facade's external processing path remains deliberately blocked by the SRS/data-policy gate.
- No Provider/browser editing, Preview/Finalize delivery, OnlyOffice, download, production attachment retention, or real business-file test is claimed. Production attachment retention/deletion remains **Release Gate OPEN**.
- Legacy M1 tools remain registered alongside the Candidate B `office` facade. This is a staged compatibility boundary, not proof of a globally single-tool registry.
- Git workspace had existing unrelated dirty/untracked files. No stage, commit, push, reset, or clean was performed.

**Historical v0.2 submission:** CC-M2-CB-04 was submitted as READY FOR FINAL ACCEPTANCE for local/mock + authorized Odoo integration scope only. The owner retained the Final Acceptance decision.

## 6. v3.0 reimplementation addendum — 2026-11-09

This addendum records the v3.0 implementation and evidence. It supersedes the earlier readiness disposition for the current worktree; it does not erase the v0.2 run history or its original results.

### 6.1 Implementation changes

- The Agent supplies `confirmation_required` and its explanation. The local orchestrator no longer infers business risk from cell contents, headers, formulas, broad scope, or model-reported unknowns. The service binds the model's requested confirmation to the current plan and verifies the real user's follow-up message, authenticated user, Session, Thread, accepted parent version, SHA and revisions before candidate execution.
- After candidate generation and CB-03 validation, the orchestration result separates local `verified_facts`, observed `actual_effects`, `model_claims` and `unverified_aspects`. A `PARTIALLY_VERIFIED` candidate is exposed for review and stays partial; it is not re-labelled `VERIFIED`.
- Review operations still use CB-02. In this checkout CB-02 persists accept/reject only for `VERIFIED`; for `PARTIALLY_VERIFIED`, CC-04 returns a structured interface block and leaves Candidate, Current, Last Valid and Document Revision unchanged. The CB-02 state machine and CB-03 grading were not weakened or changed by v3.0.
- The public tool prompt was updated to explain that limitation. The SRS external processing gate remains closed; no Responses/Code Interpreter or other external Candidate Provider request was made.
- v3.0 source/test edits: `services/intent_contract.py`, `services/edit_orchestrator.py`, `models/llm_thread.py`, `tests/test_intent_contract.py`, and `tests/test_edit_orchestration.py`. CB-02 service/state code and CB-03 Validator rules were not modified as part of this v3.0 implementation.
- M1 regression fixture follow-up: `mymodules/office_engine_odoo/tests/test_attachment_identity.py` now passes a valid `_M1VersionBindingProof` to the retry/publication test instead of the stale `False` value. The production M1 delivery code was not changed. The exact test passed in `v3-m1-attachment-binding-run1.log` (1 test, 0 failures/errors).

### 6.2 v3.0 automated evidence

| Evidence | Actual result |
|---|---|
| Focused `TestEditOrchestration` | `v3-edit-orchestration-run5.log`: final result **0 failed, 0 errors of 21 tests**. |
| Generic target case | `v3-generic-target-run1.log`: **1 targeted test passed** for an arbitrary worksheet/address; no customer/template/model branch. |
| Full Odoo tagged upgrade/regression | `v3-full-regression-run1.log`: **239 tests, 2 failed, 0 errors**; `office_engine_m2` reports 1 failed of 215, `office_engine_odoo` reports 1 failed of 24. This run is **FAIL**. A later targeted repair/retest is recorded below; the full suite was not rerun afterward. |
| Failure 1 / targeted follow-up | `office_engine_odoo.tests.test_attachment_identity.TestAttachmentIdentity.test_publish_failure_rolls_back_output_and_retry_publishes_same_request` initially received `version_binding=False`, so the current M1 delivery guard correctly rejected it before the test's intended injected publish error. The test fixture was updated to pass a matching synthetic `_M1VersionBindingProof`. `v3-m1-attachment-binding-run1.log` confirms 1 test, 0 failed, 0 errors. This was a test-fixture repair; production M1 code was not changed. |
| Failure 2 | `office_engine_m2.tests.test_private_skill.TestPrivateOfficeExportSkill.test_skill_hit_uses_latest_data_through_m1_engine` failed because the test directly calls `render_confirmed_mapping()` inside TransactionCase while the service performs its production transaction checkpoint `env.cr.commit()`. The production flow relies on that checkpoint before an independent worker cursor. No production/test workaround was introduced to suppress the transaction guard. This M1 regression remains unresolved. |
| Test counter discrepancy | Final `odoo.tests.result` is 239. Module loading lines report 215 + 24 = 239, while `tests.stats` report 253 + 28 = 281. The additional count is **UNEXPLAINED**; 281 is not claimed as the executed/passing total. |
| File readback | `v3-t01-*` and `v3-t02-*` synthetic XLSX files were read independently with `openpyxl`; all ZIP checks passed. Parent/candidate SHA and V1→V2→V3 links are in the adjacent JSON evidence. |
| Static checks | Python `compileall` on the changed CC-04 service/model/test Python files: exit `0`. `git diff --check`: exit `0`, no output. Neither substitutes for the failed full regression or unrun Playwright scenarios. |

Focused command:

```sh
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2:TestEditOrchestration --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/v3-edit-orchestration-run5.log
```

Full regression command:

```sh
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_odoo,office_engine_m2 --test-enable --test-tags /office_engine_m2,/office_engine_odoo --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/v3-full-regression-run1.log
```

The focused tests cover explicit edits/header replacement, user-supplied confirmation, decline, confirmation-message identity binding, candidate review facts/claims/unknowns, ambiguity, corrupt candidates, stale plans, generic targets and V1→V2→V3 continuity. The per-requirement T01–T15 disposition is recorded in `evidence/CB-M2-CB-04/v3-test-matrix.md`.

After the full run, the single M1 attachment-identity test was rerun after correcting its stale proof fixture and passed. The full 239-test suite was not rerun after that test-only correction; the separate RenderBridge/private-skill failure remains from the original full run, so the suite cannot be marked green.

### 6.3 Browser / Playwright evidence and limit

- The prior 2026-11-09 built-in Odoo browser simulation remains in HVR §1.4, including the failed whole-workbook clear scenario and successful limited sequential edit. Those facts are not overwritten.
- For v3.0, the 8092 Odoo page loaded in the built-in browser with the existing Mitchell Admin session, but no chat prompt was submitted and no scenario was exercised. The isolated process was stopped afterward. Its request log is `v3-odoo-8092-playwright.log`.
- **Playwright: NOT RUN.** Python Playwright is installed, but this run did not have a supported way to attach it to the already-authenticated in-app Odoo session. Credentials were not read or changed, and no model/Provider request was sent to manufacture an authenticated browser workflow. A browser-page load through the built-in browser is only a smoke check, not Playwright evidence or a scenario PASS.
- The default-sandbox attempt to start the dedicated UI process was denied at the configured database connection boundary; the permitted elevated test process subsequently loaded the UI, then was stopped. This is recorded as an environment limitation, not as an Odoo test failure.

### 6.4 v3.0 initial disposition (superseded by §6.5)

**PARTIAL — NOT READY FOR FINAL ACCEPTANCE.** The focused CC-04 Odoo tests and synthetic byte readback pass. The complete Odoo regression fails in two tests; the PARTIALLY_VERIFIED review-decision path is blocked by the unchanged CB-02 interface; and required Playwright scenarios were not run. No claim is made that external Provider editing, Preview/Finalize delivery, Browser E2E, or production handling passed.

No Git stage, commit, push, reset or clean was performed. The 8091 service was not restarted in this v3.0 run. No real business file or real business record was edited.

### 6.5 2026-11-09 partial-review repair and final local regression

This addendum supersedes the earlier v3.0 status above for the local/mock implementation and Odoo automated-test scope. It does not supersede historical logs, create human HVR, or claim Provider/Browser/production acceptance.

- CB-02 acceptance now permits a technically reviewable `PARTIALLY_VERIFIED` edit Candidate only through the existing typed acceptance service and a server-validated, user-scoped authorization bound to Candidate, Session, owner, Thread, Intent, decision message, parent version, Document Revision, output SHA and effect digest. The persisted validation result remains `PARTIALLY_VERIFIED`. `FAILED` remains non-acceptable. Rejection uses the existing CB-02 service and leaves Current/Last Valid/Document Revision unchanged.
- Candidate review returns an access-checked attachment download URL, filename, actual output SHA and separate verified facts, observed effects, model claims and unverified aspects. The Agent prompt says accepting a partial result does not promote its grade; the Candidate is not presented as fully business-verified.
- The M1 `test_skill_hit_uses_latest_data_through_m1_engine` test stubs only the `TransactionCase` rollback-only cursor's `commit` in the test context where the render worker is mocked. Production checkpoint behavior was not removed or changed; checkpoint ordering remains covered by RenderBridge tests.

| Run | Evidence | Actual result |
|---|---|---|
| Focused CB-04/CB-02/M1 cases | `evidence/CB-M2-CB-04/v3-partial-review-focused-run1.log` | 32 `Starting Test` entries; final `odoo.tests.result`: **0 failed, 0 errors of 32**; process exit 0. Includes partial accept/reject, V1→V2→V3, FAILED/corrupt/stale/Provider-gate cases and the M1 private-skill case. `tests.stats` says 38; discrepancy remains UNEXPLAINED. |
| Full upgrade attempt | `evidence/CB-M2-CB-04/v3-partial-review-full-run1.log` | Process exit 255. Module upgrades/test execution reached finalization but failed while flushing `ir_module_module.state` with `could not serialize access due to concurrent update`; no final `odoo.tests.result` was emitted. Preserved as failed/incomplete evidence; not counted as test PASS or successful full upgrade. |
| Full tagged regression without another module upgrade | `evidence/CB-M2-CB-04/v3-partial-review-full-run2-no-upgrade.log` | Process exit 0; 240 `Starting Test` entries; final `odoo.tests.result`: **0 failed, 0 errors of 240**. This includes `office_engine_m2` and `office_engine_odoo`, including the formerly failing M1 private-skill test. `tests.stats` reports 254 and 28 (282 combined); the difference from 240 remains UNEXPLAINED. No cause is inferred. |
| Independent artifact readback | `evidence/CB-M2-CB-04/v3-partial-review-artifact-readback.txt`, paired JSON and XLSX files | PASS: SHA-256 matched each metadata record, ZIP `testzip` passed, openpyxl readback confirmed accepted A1=15 and formula C1=`=A1*2`; V2 kept A1=15; V3 kept A1=15 and added A2=20; JSON parent/input SHA links matched. |
| Python syntax and whitespace | `py_compile` and `git diff --check` (see ATR §6.5) | PASS. |
| Playwright scenarios | Existing browser attempt plus current environment | **NOT RUN**. An authenticated Odoo page is present in the in-app browser, but the standalone Playwright runner has no supported bridge to that session. No credentials were read or copied. TransactionCase results are not Browser/HVR evidence. |

The C1/C2/C3 assertions verify actual Odoo Candidate/Version state transitions with synthetic XLSX bytes and Mock Provider dependencies: acceptance advances Current and Last Valid while retaining the partial grade; rejection preserves both pointers and revision; the second edit consumes accepted V2 bytes and creates V3. C4 permission, stale-version, corrupt-file and external-processing-policy gates are covered by the named tests in the focused and full logs. No real Provider request or real business file was used.

Current conclusion: **the requested local Candidate review/accept/reject and continuous-edit loop is verified by Odoo TransactionCase, and the full tagged regression is green.** Playwright scenario behavior and real human HVR remain unverified. The failed upgrade attempt is preserved; the successful full test run used the existing module schema/current source and did not repeat `-u`. No Git stage/commit/push/reset/clean or 8091 restart occurred in this repair run.

## 7. 2026-11-10 HVR defect repair addendum

This addendum records the scoped repairs and the 2026-11-10 retest. It does not replace prior HVR history or claim a complete user-acceptance flow.

### 7.1 Implementation changes

- `mymodules/office_engine_m2/models/llm_thread.py`: normalize trailing whitespace/`%20` only on the internal numeric `/web/content/<id>?download=true` href after the parent sanitizer. Preserve the sanitized result as `Markup`; without this, `re.sub` downgraded the value to plain text and Odoo escaped the anchor. The download controller, attachment identity, and access checks were not changed.
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`: add a focused regression that checks whitespace normalization, Markup preservation and that an unrelated external URL is unchanged.
- `mymodules/office_verify/verify.py`: compare effective default styles semantically and exclude derived worksheet dimension and index-only empty-row serialization from independent structure differences. Existing package integrity and meaningful-change validation remain enabled.
- `mymodules/office_verify/tests/test_candidate_verify.py`: add neutral-workbook regression coverage for a blank-cell write, formula preservation and legal derived dimension/default-style serialization; retain rejection of a corrupted XLSX and meaningful changes.

### 7.2 Actual verification evidence

| Verification | Actual result | Evidence |
|---|---|---|
| Focused Odoo URL regression | 1 test, 0 failed, 0 errors; exit 0 | `evidence/CB-M2-CB-04/hvr-fix-download-focused-20261110-final.log` |
| `office_verify` tests | 46 passed, 1 warning | Command: `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests` |
| Full Odoo regression | 241 started; final 0 failed, 0 errors of 241; exit 0; one HTTP test skipped due missing `websocket-client` | `evidence/CB-M2-CB-04/hvr-fix-full-regression-20261110.log`. No module upgrade was run. `tests.stats` totals 283 versus 241 final result remains UNEXPLAINED. Worker cleanup warning preserved. |
| Static checks | `py_compile` and affected-code `git diff --check` passed | Current worktree result; no Git mutation. |
| Post-fix UI href click | NOT RUN | Existing Candidate message was persisted before the Markup fix and rendered as escaped text with no anchor. The UI request to re-present it timed out before a new assistant response. No manual URL substitution was counted. |
| Candidate 1464 readback | PASS for bytes/lineage only | ORM-bound attachment SHA matches version SHA; V2 parent/input SHA match; ZIP/openpyxl readback: A1=15, A2=20, C1=`=A1*2`; grade remains PARTIALLY_VERIFIED. See `hvr-fix-current-readback-20261110.txt` and `readback_hvr_rerun_20261110.txt`. |

### 7.3 HVR disposition and service boundary

- HVR-02: **BLOCKED / NOT RUN** at UI-click/download stage. The fix and regression test pass, but no post-fix UI anchor click, HTTP 200 or downloaded-byte SHA was obtained.
- HVR-03: **BLOCKED**. The Candidate was ORM-read and independently inspected, but was not actually opened/downloaded by the user through the UI and was not accepted.
- HVR-04: **PARTIAL**. The repaired pipeline produced Candidate 1464 from accepted V2 1176 and independent readback confirmed the requested second value with formula and first edit intact. Candidate remains PARTIALLY_VERIFIED and has not been accepted; Current did not advance.
- HVR-05: **NOT RUN / BLOCKED**, because no accepted V3 exists from which to create and reject V4.

Read-only state: Current=Last Valid=1176, Document Revision=2; Candidate 1464 is `partially_verified`, parent=1176. No decision or formal version transition occurred in this retest. 8091 was not restarted. The dedicated 8092 test process was stopped after the stalled UI call. No XLSX was sent to an external Provider; only synthetic text chat was dispatched, and the re-presentation request timed out.

**Current disposition:** code-level fixes and automated regressions pass; requested HVR closure remains incomplete. The required user-visible download, view/accept, accepted V3 and V4 rejection are not claimed.
