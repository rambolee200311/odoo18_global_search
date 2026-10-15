# ATR — CC-018 Phase 1

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Framework | pytest 8.4.2, pytest-playwright 0.10.0, Playwright 1.37.0 |
| Environment | Local Odoo 18, database `odoo18ce`, port 8091 |
| Code baseline | Working tree based on commit `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Executed | 2026-10-15 |

## 2. Test Contract Baseline

CC-TEST-001–012, CC-TEST-020, and CC-TEST-023 refer to
[CC-018 §§5 and 11](../intent/CC-018_architecture_refactoring.md). The
remaining phase-specific tests are not applicable to this phase and remain
open for their required later stages.

## 3. Current Automated Test Status

| Metric | Result |
|---|---|
| Chromium UI scenarios | 14 passed |
| CC-TEST-023 performance | 1 passed |
| WebKit UI scenarios | 14 passed |
| Firefox UI scenarios | 14 setup errors; browser launch blocked |
| Required browser evidence complete | Waived for this execution by explicit user approval |
| Phase 1 | Satisfied for transition; HVR is WAIVED, not PASS |

## 4. Coverage Matrix

| Contract test | Result | Evidence |
|---|---|---|
| CC-TEST-001–012 | PASS on Chromium; PASS on WebKit; Firefox BLOCKED | Full run dated 2026-10-15 |
| CC-TEST-020 | Partial: Chromium/WebKit UI suite ran; Firefox blocked; Safari HVR not run | Cross-engine run |
| CC-TEST-023 | PASS on Chromium; P95 below both thresholds | Ignored local JSON referenced by UI evidence index |
| CC-TEST-013–019, CC-TEST-021–022 | NOT RUN as a complete matrix | Existing targeted tests are not a substitute for the specified full regression |
| CC-TEST-024–028 | NOT RUN | Later-stage integration tests |

## 5. Test Run History

| Run | Invocation / scope | Executed | Result | Evidence / follow-up |
|---|---|---:|---|---|
| ATR-RUN-001 | `run_isolated.py --browser chromium --browser firefox --browser webkit`; UI suite | 42 total across engines | PARTIAL: 28 passed, 14 Firefox setup errors in 218.50s | Firefox launch logs identify macOS sandbox/profile failures; no Firefox PASS claimed. |
| ATR-RUN-002 | `run_isolated.py --performance --browser chromium`; first measurement implementation | 1 | FAIL | Query alternation assumption was invalid; test corrected. |
| ATR-RUN-003 | `run_isolated.py --performance --browser chromium`; corrected measurement | 1 passed in 11.14s | PASS | 30 samples after 3 warm-ups; P95 21.427 ms navigation, 4.944 ms response-to-render. |
| ATR-RUN-004 | `run_isolated.py --browser chromium`; complete CC-TEST-001–012 suite | 14 passed in 18.87s | PASS | Current working tree only. |

## 6. Regression Verification

The UI run exercises the browser flows; it does not replace the full Odoo
module regression required by CC-TEST-013–019 and CC-TEST-021–022. The
previous targeted navigation test result is not treated as a full-module pass.

## 7. Issues

- Firefox cannot launch in the current macOS environment; the error is
  preserved as BLOCKED rather than suppressed.
- The performance check measures the current working tree after the QWeb
  extraction; it is not evidence of the original pre-refactor baseline.
- Cross-engine/latest-browser execution was waived by the user for this run;
  the waiver does not amend CC-018 or turn blocked/untested browsers into PASS.
- Manual HVR and Safari HVR were explicitly waived by the user for this run;
  see [the phase-1 HVR waiver record](HVR-GS-CC018-PHASE-1.md). No agent-
  performed interaction is represented as a human PASS.

## 8. Evidence Inventory

See [the CC-018 UI evidence index](../../../mymodules/wd_global_search/tests/ui/evidence/INDEX.md).
Screenshot and measurement JSON files are local, ignored runtime artifacts.

## 9. Handoff

Automated evidence supports transition under the user's one-time HVR/browser
waiver. The original pre-refactor baseline and historical deviations remain
open for final CC-018 disposition.
