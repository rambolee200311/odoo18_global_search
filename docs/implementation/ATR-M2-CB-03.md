# ATR — CC-M2-CB-03 Workbook Validator

## 0. Governance

- Contract: `CC-M2-CB-03_Workbook_Validator_v0.2.md` (Frozen; implementation authorized after owner gate decisions dated 2026-11-08).
- Status at original implementation start: **IN PROGRESS — no acceptance claim yet**. Current owner acceptance is recorded append-only in §5 below.
- Scope: local XLSX candidate validation and trusted typed Receipt registration; synthetic data only.
- Prohibited in this run: Provider calls, real business data/attachments, production processing, Git staging/commit/push/reset/clean, changes outside frozen CC whitelist.
- Owner gates: CC-02 Final Accepted; narrowly scoped local-validator/Synthetic Receipt SRS exception; non-production `odoo18ce` module upgrade and TransactionCase authorization. See `IHR-M2-CB-03.md` IHR-001.

## 1. Test Evidence

No test result is recorded here until the command has actually run. Subsequent entries record exact command, exit status, discovered/pass/fail/error/skip counts, log/evidence path, and whether execution was pure Python or Odoo TransactionCase.

## 2. Run Log

| Run | Date | Layer | Command / evidence | Result |
|---|---|---|---|---|
| ATR-001 | 2026-11-08 | Baseline | Pre-change worktree and source inspection | In progress |

## 3. Final Implementation Evidence (append-only; 2026-11-08)

### 3.1 Commands and actual results

| Run | Layer / environment | Command or log | Actual result |
|---|---|---|---|
| ATR-002 | Full `office_engine_m2` Odoo TransactionCase regression; nonproduction `odoo18ce`, synthetic fixtures, module update | `./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2 --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile docs/implementation/evidence/CB-M2-CB-03/odoo_office_engine_m2_full.log` | Process exit 0; log contains **186 `Starting Test` entries** and `odoo.tests.result: 0 failed, 0 error(s) of 186 tests`. Module `tests.stats` reports 222 tests; discrepancy unexplained. `office_engine_m2` update/load succeeded. This run preceded the later isolated Expected Effect budget decoupling; see post-change Candidate class test in ATR-006. |
| ATR-003 | Failure-first Expected Effect budget regression | `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py -k expected_effect_budget_is_separate_from_m1_mapping_budget` before budget fix; `failure_expected_effect_uses_mapping_budget.log` | 1 failed as expected: old M1 `max_mapping_bytes=64` rejected Candidate metadata despite separate Candidate cap=512. |
| ATR-004 | Pure Python final | `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests`; `pytest_office_verify_final.log` | **43 passed in 3.35s**. Includes existing M1 verifier tests and Candidate-neutral XLSX checks. |
| ATR-005 | Focused Candidate budget regression after fix | `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py -k expected_effect_budget_is_separate_from_m1_mapping_budget`; `pytest_expected_effect_budget_final.log` | **1 passed, 18 deselected**. Independent Candidate budget is separately configured and enforced. |
| ATR-006 | Odoo Candidate TransactionCase after budget fix; nonproduction `odoo18ce`, synthetic fixture, `--stop-after-init`, loopback ephemeral HTTP port | `./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 --test-enable --test-tags /office_engine_m2:TestCandidateValidator --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile docs/implementation/evidence/CB-M2-CB-03/odoo_candidate_validator_final.log` | Process exit 0; `odoo.tests.result`: **0 failed, 0 errors of 6 tests**. `odoo.tests.stats` says 8; unexplained mismatch. Module update completed. |
| ATR-007 | Standalone M1 `office.document.request` / attachment regression; nonproduction `odoo18ce`, synthetic TransactionCase, no module upgrade | `./venv/bin/python ./odoo-bin -c odoo.conf -d odoo18ce --test-enable --test-tags /office_engine_odoo --stop-after-init --http-interface=127.0.0.1 --http-port=0 --gevent-port=0 --workers=0 --max-cron-threads=0 --log-level=test --logfile docs/implementation/evidence/CB-M2-CB-03/odoo_office_engine_odoo_m1.log` | Process exit 0; 23 `Starting Test` entries and `odoo.tests.result: 0 failed, 0 error(s) of 23 tests`. `tests.stats` says 27; unexplained. |
| ATR-008 | Static Python syntax | `./venv/bin/python -m py_compile mymodules/office_verify/models.py mymodules/office_verify/service.py mymodules/office_verify/verify.py mymodules/office_verify/__init__.py mymodules/office_verify/tests/test_candidate_verify.py mymodules/office_verify/tests/__init__.py mymodules/office_engine_m2/services/candidate_validator.py mymodules/office_engine_m2/services/__init__.py mymodules/office_engine_m2/tests/test_candidate_validator.py mymodules/office_engine_m2/tests/__init__.py` | Exit 0; syntax compile passed. |
| ATR-009 | Git whitespace validation | `git diff --check` | No output; passed. No Git write operation was performed. |

All Odoo runner commands used the authorized non-production database and an ephemeral loopback HTTP port; no 8091 restart occurred. The Odoo TransactionCase data uses synthetic fixtures and transactional rollback. `office_engine_m2` full regression traversed existing M1 RenderBridge, attachment/Document Request, version-state and chat integration tests. ATR-009 separately ran the existing `office_engine_odoo` attachment and `office.document.request` tests without upgrading that module.

### 3.2 Resource measurement

`odoo_candidate_validator_final.log` records:

```text
CB03_RESOURCE_EVIDENCE elapsed_seconds=0.259099 timeout_seconds=15.0 rss_observed=True max_observed_rss_bytes=87851008 worker_exited=True source_bytes=4853 candidate_bytes=4853 expected_effect_budget_bytes=1048576
```

This is one small synthetic-workbook sample. RSS is the parent process's sampled maximum, not a continuous peak measurement. No throughput/P95 SLA is claimed. Odoo's test harness also emitted a warning that a Python child process remained visible and might hang at shutdown; its identity/final cleanup was not verified. The Candidate worker's own `worker_exited=True` assertion passed.

### 3.3 Preserved failures and environment warnings

- Failure-first history (including the earlier metrics/date regression outcomes whose raw terminal output was not saved) is summarized transparently in `evidence/CB-M2-CB-03/failure_first_history.md`; the later Expected Effect budget failure is preserved as a raw pytest log.
- `office_engine_odoo` module regression completed after the initial ATR-002 run; see ATR-007. The earlier statement that its standalone suite was not run is superseded by this later result.
- Odoo test logs report three unrelated addons as not installable (`wd_qooling_app`, `wd_advanced_m2o_record_panel`, `wd_evidence_album`). They are outside this CC; their module-loading warnings are not represented as test passes.
- `tests.stats` versus final `tests.result` counts are **UNEXPLAINED**: full M2 222 vs 186; Candidate class 8 vs 6; `office_engine_odoo` 27 vs 23. Use `tests.result` and exact `Starting Test` count as the observed method-run evidence, while retaining the inconsistency for owner review; no cause is inferred.
- The broad-run log contains an expected injected `attachment read failed` exception from the error-path test; final suite result is still 0 failed/0 errors. It also contains a module-loader `ERROR` listing the unrelated unavailable addons; this is reported separately from test result.

### 3.4 Acceptance state and open items

- **Implementation:** local XLSX Candidate Validator and typed Receipt registration implemented; focused pure Python and Odoo tests pass.
- **Not claimed:** Candidate B Provider / Browser / user-delivery E2E, real business data, production attachments, full external file-policy approval, formula recalculation, or production SLA.
- **Owner review required before CC-03 Final Acceptance:** frozen CC assumes one external `office` Agent Tool, while existing `office_tools.xml` registers legacy `office_prepare_context`, `office_save_mapping_preview` and `office_finalize` entries and existing tests assert them. This CC added no registry entry and did not alter that out-of-scope legacy architecture. Decide whether this is an accepted legacy boundary or requires a separate contract/work item.
- **Evidence issues:** Odoo stats mismatch and child-process cleanup warning remain unresolved. These facts are preserved; no explanation or cleanup success is inferred.
- CC-02 is formally **Final Accepted — CB-02 technical scope only**, per the owner's decision recorded in CB-02 IHR/ATR. Its production `Release Gate OPEN` remains separate.

**CC-M2-CB-03 status: implementation evidence submitted for owner review; not marked Final Accepted by Codex.**

## 4. Final Technical Evidence Review (append-only; 2026-11-08)

The records below are a review of existing execution evidence, not a new test run.

| CC-M2-CB-03 evidence item | Reviewed disposition |
|---|---|
| Python contract and Candidate validation | 43 `office_verify` tests passed; isolated Candidate budget regression passed (1 passed, 18 deselected). |
| Odoo Candidate integration | 6 actual `Starting Test` methods; final `tests.result` 0 failed / 0 errors. The module update and post-budget-fix Candidate run are evidenced in `odoo_candidate_validator_final.log`. |
| Odoo module regression / M1 compatibility | `office_engine_m2`: 186 actual `Starting Test` methods, `tests.result` 0 failed / 0 errors and module upgrade completed. `office_engine_odoo`: 23 actual `Starting Test` methods, `tests.result` 0 failed / 0 errors. |
| Resource evidence | One synthetic sample: 4,853-byte source and candidate, 0.259099 s, sampled max RSS 87,851,008 bytes, 15 s timeout, worker exited. Not an SLA. |
| Static checks | Python syntax check exited 0; `git diff --check` passed. |
| Single external `office` Tool invariant | **Legacy architecture debt, assigned to CB-04 by owner disposition.** CB-03 added no external tool and did not touch the historical registry. This report does not claim the single-tool architecture is currently implemented. |
| Odoo counter mismatch | **UNEXPLAINED**: `tests.stats` 222/8/27 vs `Starting Test` and `tests.result` 186/6/23. No full rerun solely for counter reconciliation. |
| Child process cleanup warning | Remains an observation: Candidate worker exit was reported, but the additional process identity/final cleanup was not verified. No leak or Candidate test failure is inferred. |
| Provider/Browser/Finalize, production attachment policy | Not run / out of CB-03 technical implementation evidence. Production attachment retention/deletion is still `Release Gate OPEN`. |

The detailed evidence paths remain in §3 and `evidence/CB-M2-CB-03/README.md`; historical failures and warnings remain unchanged.

**Current status: READY FOR FINAL ACCEPTANCE — CB-03 technical implementation scope only.** This is not `Final Accepted`; that decision belongs to the owner. The legacy Tool Registry debt, counter mismatch, and cleanup observation are explicitly carried forward and do not become claims of resolution.

## 5. Owner Final Acceptance (append-only; 2026-11-08)

The owner approved:

**Final Accepted — CB-03 technical implementation scope only.**

The accepted scope is the local XLSX Candidate Validator, deterministic validation, resource boundaries, and CB-02 typed `ValidationReceipt` registration. Provider, Browser, user preview, Finalize, real business attachments, and production deployment are excluded. Production file retention/deletion remains **Release Gate OPEN**.

This acceptance does not resolve the unexplained Odoo `tests.stats` differences, the additional child-process cleanup observation, or the legacy multi-tool registry debt; those remain recorded as observations/follow-up scope and are not represented as passed or repaired.
