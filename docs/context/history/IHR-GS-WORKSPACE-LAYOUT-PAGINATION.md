# IHR-GS-WORKSPACE-LAYOUT-PAGINATION

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-WORKSPACE-QUERY-REFINEMENT` |
| CC | CC-005 v0.3 FROZEN; CC-004 v0.3 FROZEN |
| Module | `wd_global_search` |
| Work type | Workspace layout, pagination, Preview removal, runtime asset isolation |
| Implementer | Copilot assistant |
| Implementation state | Implementation Complete; final human verification pending |

## 2. Coding Contract Baseline

- CC-005 v0.3: Results-only Workspace at every width; Desktop result-list scroll boundary; numbered pagination, page-size options 10/20/50/100; configured Odoo Form Action on explicit open.
- CC-004 v0.3: Workspace does not display or call Preview; the existing read-only Preview API security contract remains unchanged.
- SRS/TDD were not modified. The user-approved Workspace Preview exception is recorded in both CCs; SRS FR-SW-004 remains unsatisfied.

## 3. Implementation History Entries

### IHR-001 — Isolating Workspace assets

- **Action:** Removed Workspace CSS/JS from global `web.assets_backend`; kept the assets directly linked by the standalone Workspace page and added a DOM guard before Workspace initialization.
- **Reason:** Global Workspace styles reset Odoo page-wide styles, and the Workspace script bound controls absent from `/odoo`, causing the Odoo home and Form Action shell to appear blank.
- **Files:** `mymodules/wd_global_search/__manifest__.py`, `controllers/main.py`, `static/src/css/preview.css`, `static/src/js/preview.js`
- **Contract:** CC5-CHANGE-006/007; CC5-PRESERVE-004
- **Result:** Completed

### IHR-002 — Implementing Results-only layout

- **Action:** Removed the Preview pane and Workspace Preview fetch path at all widths; retained result selection and configured Form Action navigation.
- **Reason:** User-approved CC-004/CC-005 v0.3 behavior.
- **Files:** `controllers/main.py`, `static/src/css/preview.css`, `static/src/js/preview.js`
- **Contract:** CC4-CHANGE-005; CC5-CHANGE-006/007
- **Result:** Completed

### IHR-003 — Implementing numbered pagination

- **Action:** Added page-size selection (10/20/50/100), dynamic First/Previous/page-window/Next/Last controls, page reset on query/refinement/resource/page-size changes, and bounded stale-response handling.
- **Reason:** Implement CC5-CHANGE-008 without adding a Search API.
- **Files:** `controllers/main.py`, `static/src/css/preview.css`, `static/src/js/preview.js`
- **Contract:** CC5-CHANGE-008; WORKSPACE-PAGINATION-INV-001~006
- **Result:** Completed

### IHR-004 — Returning exact offset pages

- **Action:** Changed Resource Executor to retain `search_count()` totals and fetch only the requested per-model offset/limit slice; changed Search Facade to allocate the global page over stable Resource/model ordering.
- **Reason:** Support exact page totals and reachable pages beyond the former 50-row fetch cap.
- **Files:** `services/executor.py`, `services/facade.py`, `tests/test_service_core.py`
- **Contract:** CC5-CHANGE-008; CC5-TEST-024/025; TDD §3.10 preserved
- **Result:** Completed

### IHR-005 — Fixing page-navigation failure

- **Action:** Restored the narrow-layout predicate used to scroll to the results after page navigation.
- **Reason:** Removing Preview also removed a helper still used by the page-navigation success path, causing the catch handler to display “Search unavailable” after a successful API response.
- **Files:** `static/src/js/preview.js`
- **Contract:** CC5-TEST-016/023
- **Result:** Completed; browser retest remains pending.

## 4. Actual Change Inventory

| File | Change | Contract |
|---|---|---|
| `docs/context/intent/CC-004_global_search_preview_container.md` | v0.3 frozen; Workspace Preview exception | CC4-CHANGE-005 |
| `docs/context/intent/CC-005_global_search_workspace_query_refinement.md` | v0.3 frozen; all-width Results-only and pagination rules | CC5-CHANGE-006~008 |
| `mymodules/wd_global_search/__manifest__.py` | Removed globally injected Workspace assets | CC5-PRESERVE-004 |
| `mymodules/wd_global_search/controllers/main.py` | Results-only page and pagination controls | CC5-CHANGE-006~008 |
| `mymodules/wd_global_search/services/executor.py` | Exact authorized count and offset slice | CC5-TEST-024/025 |
| `mymodules/wd_global_search/services/facade.py` | Stable global pagination across Resources | CC5-TEST-023~025 |
| `mymodules/wd_global_search/static/src/css/preview.css` | Results-only responsive scroll layout and paginator | CC5-CHANGE-007/008 |
| `mymodules/wd_global_search/static/src/js/preview.js` | Results-only UI, pagination and explicit Form Action | CC5-CHANGE-006/008 |
| `mymodules/wd_global_search/tests/test_service_core.py` | Count/page independence and multi-model offset tests | CC5-TEST-024/025 |

## 5. Open Issues / Handoff

- Final browser verification of page 2 after the narrow-scroll fix and Odoo `/odoo`/Form Action shell after asset isolation is pending.
- Human HVR has not been completed; no human PASS is claimed.
- SRS v1.4 FR-SW-004 still requires Desktop Preview. Per user instruction, SRS/TDD were not changed; this explicit nonconformance remains visible.
- CC-012 draft changes are outside this implementation and are not included in this record's change inventory.
