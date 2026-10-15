# IHR - CC-018 Phase 4

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Phase | Workspace JavaScript module split |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Status | Implementation and Chromium automated verification complete; one-time HVR/browser waiver applies |

## 2. Contract Baseline

CC-018 §8. The existing Workspace behavior, request contract, shared state,
initialization order, and module-loading constraints were retained. The
Template Designer script was not changed.

## 3. Implementation History

| ID | Action | Result |
|---|---|---|
| IHR-001 | Kept `preview.js` as the Workspace entry and changed the QWeb script to an ES module. | Existing entry URL retained; module cache version set to `cc018-phase4-v01`. |
| IHR-002 | Extracted Workspace bootstrap/event registration, conditions/refinements, Resource/configuration state, Search API, and results/navigation/pagination into five local ES modules. | One Workspace state owner and one Search sequence remain; dependency flow is entry to the four responsibility modules. |
| IHR-003 | Added CC-TEST-026 to verify the entry and all four dependencies load with JavaScript content types, no failed script requests or console errors, and successful seeded-record rendering. | Completed |
| IHR-004 | Added the Resource label formatter and Resource tab dependency omitted during mechanical extraction; kept the card-density state mutable for resize handling. | Targeted integration test and complete Chromium regression pass. |

## 4. Change Inventory

- Updated `mymodules/wd_global_search/static/src/js/preview.js` as the module entry.
- Added `workspace_entry.js`, `workspace_conditions.js`,
  `workspace_resources.js`, `workspace_search.js`, and `workspace_results.js`.
- Updated `views/controller_pages.xml` to load the Workspace entry as a module.
- Added CC-TEST-026 to `tests/ui/test_workspace_baseline.py`.

## 5. Verification

- All six ES modules passed Node module syntax checks.
- Odoo module upgrade loaded the updated QWeb script declaration; the restored
  local service returned HTTP 200 on port 8091.
- CC-TEST-026 targeted Chromium run: 1 passed.
- Full Chromium UI suite, including CC-TEST-001-012, CC-TEST-024-026:
  17 passed.
- Python compilation, pytest collection (18 tests), and `git diff --check`
  passed before final phase closure.

## 6. Deviations / Limitations

- The first browser runs detected missing extracted dependencies (`text` and
  `resourceTabs`) and a captured state value that needed to remain mutable for
  resize events. These were corrected; the final targeted and full Chromium
  suites pass.
- Firefox and WebKit module-loading runs and Safari manual HVR were not
  performed under the user's one-time cross-browser/HVR waiver recorded in
  [the phase-1 waiver record](HVR-GS-CC018-PHASE-1.md). This is not a PASS claim.
- CC-TEST-023 remains for final comparison against the frozen phase-1
  performance baseline.

## 7. Handoff

Phase 4 is independently complete for the approved Chromium scope. Phase 5 may
proceed. CC-018 remains open pending phase 5 and the final deviation review.
