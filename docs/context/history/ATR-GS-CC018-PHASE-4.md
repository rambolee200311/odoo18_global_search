# ATR - CC-018 Phase 4

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Framework | Node module syntax checks / pytest-playwright 0.10.0 / Chromium |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Executed | 2026-10-15 |

## 2. Test Contract Baseline

CC-TEST-026 and CC-TEST-001-012, CC-TEST-024-025, as defined by
[CC-018 §§8 and 11](../intent/CC-018_architecture_refactoring.md).

## 3. Coverage

| Test | Result | Evidence |
|---|---|---|
| ES module syntax | PASS | `node --input-type=module --check` on `preview.js` and all five Workspace modules |
| QWeb module script delivery | PASS | Odoo module upgrade followed by HTTP 200 service check |
| CC-TEST-026 targeted module loading and seeded search | PASS, 1 passed | `run_isolated.py --browser chromium -k cc_test_026` |
| Existing-browser cache refresh and `acme` search | PASS | After the v02 QWeb upgrade and page reload, all six modules loaded with v02; search returned HTTP 200 and rendered 10 results without JavaScript errors |
| CC-TEST-001-012, CC-TEST-024-026 | PASS, 17/17 | `run_isolated.py --browser chromium` |
| Python compilation and UI collection | PASS, 18 collected | `py_compile` and `pytest --collect-only -q mymodules/wd_global_search/tests/ui` |
| Whitespace validation | PASS | `git diff --check` |

CC-TEST-026 checks HTTP 200 JavaScript responses and content types for
`preview.js`, `workspace_entry.js`, `workspace_conditions.js`,
`workspace_resources.js`, `workspace_results.js`, and `workspace_search.js`.
It also checks for failed script requests and console errors and verifies that
the seeded contact search renders the expected result cards. A retained browser
session initially used cached v01 modules: the API returned success, but
`workspace_results.js` raised `ReferenceError: resourceTabs is not defined`,
which the UI surfaced as “Search unavailable”. The module URLs were bumped to
v02, the module was upgraded in the database, and the same browser session
rendered the `acme` results after reload without requiring another login.

## 4. Run History

| Run | Scope | Result |
|---|---|---|
| ATR-RUN-001 | Initial CC-TEST-026 smoke search | FAIL; detected missing `text` helper in the Resource module; corrected |
| ATR-RUN-002 | Initial full Chromium regression | FAIL; detected missing `resourceTabs` dependency and immutable card-density state; corrected |
| ATR-RUN-003 | CC-TEST-026 with seeded records | PASS, 1 passed |
| ATR-RUN-004 | Full Chromium UI suite | PASS, 17 passed in 20.59s |
| ATR-RUN-005 | Existing-browser v02 cache refresh and `acme` rendering | PASS, 10 results; no JavaScript errors |

The failed intermediate runs were investigated and fixed; they are retained
here to preserve the execution history.

## 5. Limitations and Handoff

Firefox and WebKit runs, and manual Safari HVR, remain waived only for this
execution by the user; see [the phase-1 HVR waiver record](HVR-GS-CC018-PHASE-1.md).
No Firefox, WebKit, or Safari PASS is claimed. Phase 5 completed the final
CC-TEST-023 comparison with phase 1 and passed it; see
[ATR-GS-CC018-PHASE-5.md](ATR-GS-CC018-PHASE-5.md). Final CC-018 closure
and acceptance, including the disposition of recorded deviations, is recorded
in [ATR-GS-CC018-PHASE-5.md](ATR-GS-CC018-PHASE-5.md).
