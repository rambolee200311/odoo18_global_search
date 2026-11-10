# ATR — CC-M2-CB-04 Intent / Confirmation / Edit Orchestration

## 0. Status and boundaries

- Frozen contract: `CC-M2-CB-04_Intent_Confirmation_Edit_Orchestration_v0.2.md`.
- Authorized implementation: local service/tool orchestration with synthetic XLSX, Mock Provider seam, and Odoo TransactionCase on owner-authorized `odoo18ce`.
- Not authorized/performed: real Provider request, real business data/attachments, Browser/Finalize/production delivery, production deployment, Git stage/commit/push/reset/clean.
- Historical v0.2 disposition: **READY FOR FINAL ACCEPTANCE — CC-04 local/mock and Odoo integration scope.**
- Latest v3.0 implementation-test disposition (2026-11-09): local partial-candidate accept/reject and full tagged Odoo regression **PASS**; Playwright and human HVR remain **NOT RUN/PENDING**. Prior v0.2/v3.0 records remain historical evidence; see §6.5.

## 1. Run record

| Run | Command/evidence | Result |
|---|---|---|
| ATR-001 | `./venv/bin/python -m compileall -q mymodules/office_engine_m2/services/intent_contract.py mymodules/office_engine_m2/services/edit_orchestrator.py mymodules/office_engine_m2/tests/test_intent_contract.py mymodules/office_engine_m2/tests/test_edit_orchestration.py mymodules/office_engine_m2/tests/test_native_chat_integration.py mymodules/office_engine_m2/tests/test_conversational_preview.py` | Exit 0. |
| ATR-002 | `git diff --check` | Exit 0, no output. No Git write operation. |
| ATR-003 | Initial complete upgrade and tagged Odoo run; log `evidence/CB-M2-CB-04/odoo-elevated-run.log` | Process completed, final result `1 failed, 15 errors of 222 tests`; preserved as failure-first evidence. No pass claim. |
| ATR-004 | Focused first run; log `odoo-targeted-run1.log` | `7 failed, 1 error of 90 tests`; preserved. Exposed transaction-message flush and tool registry expectation issues. |
| ATR-005 | Focused diagnostics; logs `odoo-targeted-run2.log`, `odoo-orchestration-run3.log`, `odoo-orchestration-run4.log`, `odoo-orchestration-run5.log` | Intermediate failures preserved. Root causes were narrowed through structured result output and server traceback. |
| ATR-006 | `./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2:TestEditOrchestration --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/odoo-orchestration-run6.log` | Exit 0; 7 test methods; `0 failed, 0 errors of 7 tests`. |
| ATR-007 | `./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2:TestEditOrchestration.test_two_successive_edits_use_successive_accepted_workbook_versions --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/odoo-orchestration-run7.log` | Exit 0; 1 test method; `0 failed, 0 errors of 1 test`. |
| ATR-008 | Historical v0.2 final full upgrade and tagged regression; log `evidence/CB-M2-CB-04/odoo-final-regression.log` | Exit 0; 222 `Starting Test` lines; `odoo.tests.result: 0 failed, 0 errors of 222 tests`. Module loads succeeded. `tests.stats` reports 237 (`office_engine_m2`) and 27 (`office_engine_odoo`); discrepancy remains unexplained. |
| ATR-009 | Restore Odoo and host-network HTTP check; log `evidence/CB-M2-CB-04/odoo-8091-restored.log` | Odoo 8091 registry loaded; GET `/web/login` returned HTTP 200. |

Full regression command for ATR-008:

```sh
./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_odoo,office_engine_m2 --test-enable --test-tags /office_engine_m2,/office_engine_odoo --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile=docs/implementation/evidence/CB-M2-CB-04/odoo-final-regression.log
```

## 2. Implemented contract surface

- Intent parsing is a bounded, generic interpretation and does not define an Excel editing DSL.
- Intent and Expected Effect bind to a server-resolved user message, Thread, Session, accepted parent version, real input SHA and current revisions.
- Confirmation receipts are computed server-side; `confirmed`, model-supplied identity, or `force_override` are not accepted as authorization.
- `office` is a bounded Candidate B facade. Internal Provider/Version/Validator/orchestration services are not separate Agent Tools.
- Candidate creation, validation receipt registration, acceptance and rejection use existing CB-01/02/03 service boundaries; Current advances only via CB-02.
- Ambiguity, missing confirmation, fail-closed external processing, provider failure, stale binding, effect mismatch, verified review, accept and reject paths have structured outcomes.
- Tests validate that M1 operations remain available. Legacy XML tool entries were not modified; the workspace does not claim a completed global single-tool migration.

## 3. Failure analysis and repairs

The first full run and all subsequent failing logs remain in evidence. Changes were limited to the frozen CB-04 whitelist:

- Flush the stored computed `mail.message.llm_role` before querying the just-created user message in the same transaction.
- Treat the initially synced `office` decorated tool entry as an auto-registration lifecycle: the first upgrade test run observed it absent, then the subsequent upgrade/test run found it registered. Existing M1 tests now assert the staged facade while keeping old tools.
- Fix duplicate fields passed to `_public_result` by constructing a single merged result dictionary.
- Correct the broad-scope synthetic fixture to modify A2, not B1; correct the second-round Expected Effect to expect the requested value 20.
- Normalize `docProps/core.xml` timestamps in test-generated synthetic XLSX only, so the test isolates the intended cell-value effect. No Validator check was relaxed.

The final full regression has no failed tests. Initial failure logs are not overwritten or removed.

## 4. Test coverage disposition

| Evidence layer | State | Evidence/boundary |
|---|---|---|
| Python syntax and diff whitespace | PASS | ATR-001/002. |
| Intent/Orchestration TransactionCase | PASS | 7/7 exact class methods in `odoo-orchestration-run6.log`; second-version focused method also passed in run7. |
| Odoo M1 compatibility and full integration suite | PASS | 222 final test methods, 0 failures/errors; includes `office_engine_odoo` and existing M1 Mapping, native chat, RenderBridge, attachment/Document Request and version tests. |
| Odoo module upgrade | PASS | `office_engine_odoo` and `office_engine_m2` loaded on final run. |
| Test count reconciliation | OPEN / UNEXPLAINED | 222 `Starting Test` and final result versus `tests.stats` 237 + 27. No inferred cause. |
| Worker cleanup observation | OPEN / OBSERVATION | Odoo runner warned about a visible Python child; separate from the Candidate worker's own exit evidence. |
| Mock candidate byte processing | PASS in Odoo TransactionCase | Synthetic in-process adapter seam; actual CB-02 and CB-03 services are used. |
| Real Provider / Responses API | NOT RUN | SRS/data-policy gate remains open and facade external dispatch is false. |
| Browser, Preview/Finalize download and delivery E2E | NOT RUN / OUT OF THIS CC IMPLEMENTATION RUN | No UI, browser or delivery path was changed. |
| Real business attachments / production deployment | NOT RUN / NOT AUTHORIZED | No business file or external Provider processing. |

The Odoo runner logs include expected ACL denials and an injected duplicate-key exception from a negative test. They are not counted as test failures; final Odoo result is the pass/fail evidence.

## 5. Worktree and final disposition

- Branch/HEAD at baseline: `main` / `f9801fca76f7c248a9cc823c583138ab0191b978` (recorded before test execution).
- Existing unrelated dirty/untracked files were preserved. `git diff --check` was read-only. No staging, commit, push, reset, or clean occurred.
- No `office_tools.xml` change, no CB-02/03 implementation change, no SRS/TDD/Plan/CC change, no Provider configuration change.
- Odoo service was restored at 8091 and HTTP 200 was verified after tests.
- `tests.stats` discrepancy, the additional child-process cleanup observation, global legacy M1 tool coexistence, real Provider validation, Browser/Delivery E2E and production file-retention gate remain explicitly open/unverified.

**Historical v0.2 submitted state:** READY FOR FINAL ACCEPTANCE — CC-M2-CB-04 local/mock and authorized Odoo integration scope. This did not sign Final Accepted or claim production readiness.

## 6. v3.0 addendum — reimplementation evidence and current disposition

### 6.1 Actual implementation and boundaries

- Business-risk and “does the original instruction authorize this?” decisions are taken from the model-supplied Intent; local code binds and validates the confirmation credential but does not infer risk from non-empty content, headers, formulas or broad scope.
- Confirmation execution requires the real current user's thread message, authenticated `env.uid`, matching plan/request, Session/Proposal/Document revisions, current parent version and input bytes SHA. Candidate receipts bind the actual decision message and user.
- Review output distinguishes local verified facts, observed effects, model claims and unverified aspects. Technical failure remains fail-closed.
- CB-03 grades and CB-02 current-version acceptance invariants remain unchanged. A PARTIALLY_VERIFIED candidate can be presented with its evidence, but the current CB-02 interface supports persisted accept/reject only for VERIFIED. CC-04 reports that limit; it does not write state fields or bypass CB-02.
- No Provider request was made. `EXTERNAL_PROVIDER_DISPATCH_ENABLED` remains false. No real business attachment/data was used.

### 6.2 v3.0 test record

| Run | Evidence | Result |
|---|---|---|
| ATR-V3-001 focused orchestration | `evidence/CB-M2-CB-04/v3-edit-orchestration-run5.log` | **21 tests, 0 failures, 0 errors** (`odoo.tests.result`). Module `tests.stats` says 23; discrepancy retained. |
| ATR-V3-002 generic target | `evidence/CB-M2-CB-04/v3-generic-target-run1.log` | **1 targeted test passed**. |
| ATR-V3-003 full Odoo regression | `evidence/CB-M2-CB-04/v3-full-regression-run1.log` | **239 tests, 2 failed, 0 errors**. Modules: `office_engine_m2` 1 failure/215; `office_engine_odoo` 1 failure/24. Overall **FAIL**. |
| ATR-V3-004 independent XLSX readback | `v3-t01-parent.xlsx`, `v3-t01-candidate.xlsx`, `v3-t02-v1.xlsx`–`v3-t02-v3.xlsx` and paired JSON | All five files passed ZIP `testzip`; openpyxl read them. T01 A1 changed to 15 and formula `=A1*2` remained. T02 V1→V2→V3 retained A1=15, then A2=20. SHA values and parent links are recorded in JSON. |
| ATR-V3-005 Playwright | `v3-odoo-8092-playwright.log` and `v3-test-matrix.md` | **NOT RUN**. Built-in browser only loaded the authenticated Odoo page; no scenario prompt was submitted. No Playwright trace/screenshot is claimed. |
| ATR-V3-006 M1 attachment-binding fixture follow-up | `v3-m1-attachment-binding-run1.log`; `mymodules/office_engine_odoo/tests/test_attachment_identity.py` | Updated the test fixture to pass the matching synthetic `_M1VersionBindingProof` required by the existing delivery contract. Targeted test: **1 test, 0 failures, 0 errors**. Production code unchanged. Full suite was not rerun after this correction. |
| ATR-V3-007 compile/diff checks | `./venv/bin/python -m py_compile` on the changed CC-04 service/model/test Python files and `mymodules/office_engine_odoo/tests/test_attachment_identity.py`; `git diff --check`; Markdown whitespace check on IHR, ATR, HVR, T01–T15 matrix and evidence README | **PASS** after the M1 fixture follow-up; no whitespace errors. |

The initial full-regression failures are preserved. Failure (1), `TestAttachmentIdentity.test_publish_failure_rolls_back_output_and_retry_publishes_same_request`, was caused by the test passing `False` instead of the current required binding proof; the test fixture was corrected and its targeted run passed. No M1 production code changed. Failure (2), `TestPrivateOfficeExportSkill.test_skill_hit_uses_latest_data_through_m1_engine`, still fails in the prior full log because the test invokes the production checkpointing service inside TransactionCase. The full suite was not rerun after the fixture correction; therefore no final full-suite PASS is claimed. Neither failure has been attributed to CC-04 v3 source changes.

The final result line counts 239 test methods; module load summaries are 215 + 24 = 239, while `tests.stats` are 253 + 28 = 281. This discrepancy remains **UNEXPLAINED**; no cause is guessed.

### 6.3 T01–T15 acceptance map

See [`evidence/CB-M2-CB-04/v3-test-matrix.md`](evidence/CB-M2-CB-04/v3-test-matrix.md) for each item, exact test/log source and disposition. In summary, focused orchestration tests and synthetic XLSX evidence cover T01–T08, T11–T13, and T15; T09/T10 are supported only for VERIFIED Candidates and blocked for PARTIALLY_VERIFIED by CB-02; T14 is **FAIL** because the full suite reports two M1-related failures. Browser/Playwright scenario coverage is **NOT RUN**.

### 6.4 Initial v3.0 disposition (superseded by §6.5)

**PARTIAL — NOT READY FOR FINAL ACCEPTANCE.** Remaining items:

1. Full Odoo/M1 regression: two failures above; no out-of-scope changes were made to conceal them.
2. CB-02 PARTIALLY_VERIFIED accept/reject interface: unresolved within CC-04 scope. A contract/interface decision is required before this candidate class can be finally accepted or rejected; CB-02 state semantics were not changed.
3. Playwright scenario tests: not run. The app's built-in browser loaded Odoo on 8092, but did not execute a scenario; a Playwright-authenticated flow was not established without extracting credentials or calling a model.
4. Odoo final counters: `tests.stats` 281 versus final result 239 remains unexplained.

No real Provider, external file processing, CB-06 delivery/Finalize, or production data was involved. Earlier v0.2 test and readiness records remain intact and historical; this v3.0 addendum is the current status.

### 6.5 Partial-review repair and current execution record — 2026-11-09

#### Changed implementation and safety boundary

- CB-02's existing typed Candidate acceptance/rejection services now support `PARTIALLY_VERIFIED` **edit** Candidates under the same Candidate/Session/user/message/parent/revision/SHA/effect binding checks. Acceptance does not change `validation_result`; it remains `PARTIALLY_VERIFIED`. `FAILED` and `REJECTED` are not made acceptable.
- Acceptance still advances Current only through `_accept_verified_version` and `_advance_document_version_from_service`; the caller cannot write Current or the state field as an authorization shortcut. A partial Candidate requires a scoped `CandidateAcceptanceAuthorization` validated against the authenticated user's Thread messages. Rejection requires a scoped `CandidateRejection` and leaves Current, Last Valid and Document Revision unchanged.
- Candidate presentation includes an ORM read-checked download URL and SHA plus verified facts, observed effects, model claims and unverified aspects. Acceptance messaging explicitly preserves the validation grade and unresolved business claims.
- The M1 private-skill TransactionCase mocks `env.cr.commit` only in the test context where the render worker is mocked. The production checkpoint remains unchanged; checkpoint ordering stays covered by RenderBridge tests.

#### Actual test evidence

| Run | Command / evidence | Result |
|---|---|---|
| Focused changed paths | `v3-partial-review-focused-run1.log` | **32 tests, 0 failed, 0 errors**, exit 0. Odoo `tests.stats` reports 38; unexplained. |
| Full run with `-u office_engine_odoo,office_engine_m2` | `v3-partial-review-full-run1.log` | **FAILED / incomplete**: exit 255 on `psycopg2.errors.SerializationFailure` while flushing `ir_module_module.state`; no final `tests.result`. Preserved and not counted as a successful full run or upgrade PASS. |
| Full tagged run without a second upgrade | `v3-partial-review-full-run2-no-upgrade.log` | **240 tests, 0 failed, 0 errors**, exit 0. `Starting Test` count and final `odoo.tests.result` are both 240. Includes the corrected M1 private-skill case and both requested modules. `tests.stats` reports `office_engine_m2: 254`, `office_engine_odoo: 28` (282 total); discrepancy is **UNEXPLAINED** and no cause is guessed. |
| C1 partial acceptance | `test_partial_candidate_can_be_accepted_without_changing_its_validation_grade` in both passing logs; `v3-partially-accepted-candidate.xlsx/.json` | PASS: Candidate V2 becomes Current and Last Valid; Document Revision 2; decision bound to the actual user message; original `PARTIALLY_VERIFIED` grade unchanged; XLSX A1=15 and formula C1=`=A1*2`. Input/output SHA recorded. |
| C2 partial rejection | `test_partial_candidate_can_be_rejected_without_advancing_current` in both passing logs | PASS: Candidate rejected; Current and Last Valid remain V1; Document Revision remains 1; grade remains partial. |
| C3 continuous modification | `test_two_successive_edits_use_successive_accepted_workbook_versions`; `v3-partially-verified-version-chain.json`; V1/V2/V3 artifacts | PASS: V2 input is V1/current bytes; V3 input is accepted V2 bytes; V3 preserves A1=15 and adds A2=20. Parent-version links and SHA chain independently verified. |
| C4 required technical gates | Focused/full logs include `test_verified_candidate_review_accept_and_reject_are_user_bound`, `test_confirmed_plan_is_stale_after_current_version_advances`, `test_corrupt_candidate_is_hard_blocked_and_never_current`, `test_facade_fails_closed_while_srs_external_processing_gate_is_open`, and `TestWorkbookVersionAccess` | PASS in the Odoo suite: tested access, stale binding, corrupt file and closed Provider-policy gate do not advance Current. The existing four-item local check boundary was not expanded. |
| Independent artifact readback | `v3-partial-review-artifact-readback.txt` | PASS: all four synthetic XLSX files match recorded SHA-256; ZIP integrity and openpyxl readback passed; V2/V3 lineage and expected values verified. |
| Syntax / diff check | `py_compile` for changed Python files; `git diff --check` | PASS. |
| Playwright | `v3-playwright-attempt.md` and current check | **NOT RUN**. The existing authenticated in-app browser has no supported bridge to the standalone Playwright runner. No credentials were extracted and no Provider call was made. |

The successful full run did not repeat module upgrades because the first upgrade attempt ended with the serialization error above; it ran the complete tagged test suite against the existing module schema and current source. The prior 239-test run with two failures remains historical; this 240-test rerun after the partial-review change and test-only TransactionCase repair is the current automated regression result.

#### Current result

**Automated local/mock closure: PASS.** The partial Candidate can be reviewed, accepted without falsifying its CB-03 grade, or rejected without moving Current; V1→V2→V3 byte lineage passes; the complete tagged Odoo regression is 240/240 with zero failures/errors. **Playwright/HVR and real Provider are not verified.** No real business data, real attachment or Provider was used. No Git write operation or 8091 restart occurred.

## 7. 2026-11-10 scoped HVR repair and retest

This run addresses only the whitespace-tainted Candidate download href and the false rejection of normal XLSX-derived dimension/default-style serialization. It does not supersede the 2026-11-09 results or claim the full UI acceptance/rejection loop.

| Run | Command / evidence | Actual result |
|---|---|---|
| ATR-HVR-FIX-01 focused download-link TransactionCase | Odoo test command recorded by `hvr-fix-download-focused-20261110-final.log` | **1 test, 0 failed, 0 errors**, process exit 0. The regression checks internal link cleanup, preservation of sanitized HTML markup, and that external links are not rewritten. |
| ATR-HVR-FIX-02 `office_verify` suite | `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests` | **46 passed, 1 warning**. Coverage includes legal blank-cell writes with derived dimension/default style serialization, formula preservation, and corrupt XLSX rejection. |
| ATR-HVR-FIX-03 full tagged Odoo regression | `evidence/CB-M2-CB-04/hvr-fix-full-regression-20261110.log` | **241 tests started; 0 failed, 0 errors of 241**, exit 0. One HTTP/browser test skipped because `websocket-client` is unavailable. No module upgrade was run. `tests.stats` says 255 + 28 = 283; discrepancy against 241 remains **UNEXPLAINED**. Worker cleanup warning and unrelated unavailable addons are present in the raw log. |
| ATR-HVR-FIX-04 Candidate byte readback | `hvr-fix-current-readback-20261110.txt`, `readback_hvr_rerun_20261110.txt`, paired synthetic XLSX files | **PASS for artifact/lineage assertions**: version 1464 parent/input bind to accepted V2 1176; attachment SHA matches output SHA; ZIP readable; A1=15, A2=20, C1=`=A1*2`; grade remains `PARTIALLY_VERIFIED`. This is ORM/readback evidence, not a UI download. |
| ATR-HVR-FIX-05 UI post-fix download link | `hvr-fix-browser-observation-20261110.txt`; `hvr-fix-live-8092-rerun-20261110.log` | **NOT RUN / BLOCKED**: old message had escaped link text and no DOM anchor; the UI re-presentation request timed out before producing a new message/link. No manual URL visit was used as substitute. |
| ATR-HVR-FIX-06 syntax/whitespace | `py_compile` for changed files; affected-code `git diff --check` | **PASS**. |

### HVR-02 through HVR-05 status

| Scenario | Result | Basis |
|---|---|---|
| HVR-02 | **BLOCKED / NOT RUN** | Automated formatter fix is covered, but no real post-fix UI link click, HTTP 200 and downloaded-file SHA were captured. |
| HVR-03 | **BLOCKED** | Candidate 1464 was not opened/downloaded by the user through UI and was not accepted. |
| HVR-04 | **PARTIAL** | Fixed Validator allows normal XLSX serialization changes and candidate generation/readback succeeded; no user review/acceptance or Current-to-V3 transition occurred. |
| HVR-05 | **NOT RUN / BLOCKED** | No accepted V3 baseline; V4 was not generated or rejected. |

Final read-only database state: Current=Last Valid=1176; Document Revision=2; Candidate 1464 remains PARTIALLY_VERIFIED and parented by 1176. No formal decision, Current advance, or HVR-05 action occurred. The 8092 test service was stopped after the UI request stalled; 8091 was not restarted. No XLSX bytes were sent to OpenAI. No production or business data was used.

**Result:** repair and automated regression criteria pass. The user-requested full HVR completion criteria do **not** pass because actual UI download/view, user acceptance of V3 and V4 rejection were not completed. No Final HVR PASS is claimed.
