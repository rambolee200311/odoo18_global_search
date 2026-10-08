# ATR-GS-WORKSPACE-LAYOUT-PAGINATION

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-WORKSPACE-QUERY-REFINEMENT` |
| IHR | `IHR-GS-WORKSPACE-LAYOUT-PAGINATION.md` |
| Contract | CC-005 v0.3 FROZEN; CC-004 v0.3 FROZEN |
| Module | `wd_global_search` |
| Environment | Odoo 18, database `odoo18ce`, macOS |
| Test Framework | Odoo `--test-enable`, Odoo shell/unittest, Node.js syntax check |
| Code Baseline | `60d0778` (CC-005 implementation commit) |
| Branch | `main` |
| Executed By | Copilot assistant |

**Baseline note:** The working tree also contains an excluded CC-012 draft and an unstaged CC-012 zero-count UI hunk in `preview.js`; neither is included in commit `60d0778`. The CC-005 hunks listed in this ATR match the committed source. No result below claims coverage of the excluded hunk.

## 2. Test Contract Baseline

| Source | IDs | Automated coverage |
|---|---|---|
| CC-005 | CC5-TEST-021, 023~027 | Limit/offset and exact page-total behavior |
| CC-005 | CC5-TEST-013~020, 022, 028 | Browser/HVR required; not covered by the unit run |
| CC-004 | CC4-TEST-005, 008 | Browser/HVR required; not covered by the unit run |
| CC-PRESERVE | CC5-PRESERVE-002~004 | Search API, permission and read-only action preservation |

## 3. Current Automated Test Status

| Metric | Result |
|---|---:|
| Core unit tests in latest valid run | 6 |
| PASS | 6 |
| FAIL | 0 |
| BLOCKED/NOT RUN in that unit run | 0 |
| Final browser/HVR tests | NOT RUN |
| Latest unit run | ATR-RUN-002 |
| Code baseline | `60d0778` |
| Evidence baseline match | Partial — see baseline note above |

## 4. Coverage Matrix

| Contract test | Automated check | Run | Result | Evidence |
|---|---|---|---|---|
| CC5-TEST-024 | Exact result total independent from page length | ATR-RUN-002 | PASS | `test_aggregator_count_is_independent_of_page_length` |
| CC5-TEST-025 | 100-row page slice across model groups with exact total | ATR-RUN-002 | PASS | `test_executor_returns_exact_total_and_requested_model_offset` |
| CC5-TEST-023 | Real Odoo numbered page 2 / Last navigation | — | NOT RUN after final browser fix | Requires HVR/browser run |
| CC5-TEST-014/016 | No Preview at Desktop/Narrow | — | NOT RUN | Requires HVR/browser run |
| CC5-TEST-018 | Configured Form Action with no Preview request | — | NOT RUN | Requires HVR/browser run |
| CC4-TEST-005/008 | Odoo home/Form Action shell and Workspace no Preview | — | NOT RUN | Requires HVR/browser run |
| CC5-PRESERVE-002 | Search API protocol | ATR-RUN-003 | PASS | Odoo module test command exited 0 |

## 5. Test Run History

### ATR-RUN-001 — Standalone unittest invocation

| Field | Value |
|---|---|
| Timestamp | 2026-10-08 |
| Scope | Attempted core unit tests outside Odoo add-on import context |
| Invocation | `./venv/bin/python -m unittest mymodules.wd_global_search.tests.test_service_core` |
| Executed | 0 tests |
| Result | BLOCKED |
| Evidence | Python import assertion required the `odoo.addons.*` namespace |
| Follow-up | Retried correctly in Odoo shell as ATR-RUN-002 |

### ATR-RUN-002 — Core unit tests

| Field | Value |
|---|---|
| Timestamp | 2026-10-08 |
| Code Baseline | CC-005 staged source corresponding to `60d0778` |
| Scope | `TestSearchServiceCore` |
| Invocation | Odoo shell + `unittest.TextTestRunner` |
| Executed | 6 |
| PASS / FAIL | 6 / 0 |
| Result | PASS |
| Evidence | Shell output: `Ran 6 tests ... OK` |

### ATR-RUN-003 — Module upgrade/test invocation

| Field | Value |
|---|---|
| Timestamp | 2026-10-08 |
| Scope | `wd_global_search` module update with `--test-enable --stop-after-init` |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf --http-port=8092 -d odoo18ce -u wd_global_search --test-enable --stop-after-init --log-level=test` |
| Result | PASS — process exit code 0 |
| Evidence | Command completion; this is not a full Odoo suite claim |

### ATR-RUN-004 — Static checks

| Field | Value |
|---|---|
| Timestamp | 2026-10-08 |
| Scope | Global Search module syntax and staged/unstaged whitespace checks |
| Invocation | `node --check .../preview.js`; `python -m compileall`; `git diff --check`; `git diff --cached --check` |
| Result | PASS |

## 6. Regression Verification

| Preservation | Evidence | Result |
|---|---|---|
| CC5-PRESERVE-002 Search API/cursor/limit | ATR-RUN-002/003 | PASS for covered service behavior |
| CC5-PRESERVE-003 Permission boundary | No final multi-user browser run | NOT RUN |
| CC5-PRESERVE-004 No Workspace Preview / no business writes | No final browser/network monitor run | NOT RUN |

## 7. Issues

| ID | Run | Status | Description | Follow-up |
|---|---|---|---|---|
| ATR-ISSUE-001 | ATR-RUN-001 | Resolved | Standalone Python import bypassed Odoo add-on namespace; no tests executed | Correct Odoo-shell invocation used in ATR-RUN-002 |
| ATR-ISSUE-002 | HVR-RUN-001 | Open | Human confirmed Odoo shell/Form Action, page 2, and no-Preview presentation; page-size choices and Preview API network absence remain NOT RUN | Complete remaining HVR scenarios before declaring CC-005 DoD satisfied |

## 8. Handoff to HVR

- Unit and static checks are recorded above; they do not prove browser behavior.
- Human verification confirmed `/odoo`, the configured Form Action, query `009` page-2 navigation, and no-Preview presentation at Desktop/Narrow widths; page-size controls and Preview API network absence remain pending.
- SRS FR-SW-004 remains explicitly unmet under the user-approved product deviation; SRS/TDD were not modified.
