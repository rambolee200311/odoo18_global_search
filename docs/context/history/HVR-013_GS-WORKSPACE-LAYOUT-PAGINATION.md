# HVR-013 — GS Workspace Layout and Pagination

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-WORKSPACE-QUERY-REFINEMENT` |
| CC Version | CC-005 v0.3 FROZEN; CC-004 v0.3 FROZEN |
| IHR Reference | `IHR-GS-WORKSPACE-LAYOUT-PAGINATION.md` |
| ATR Reference | `ATR-GS-WORKSPACE-LAYOUT-PAGINATION.md` |
| Module | `wd_global_search` |
| Environment | Odoo 18, `http://127.0.0.1:8091`, database `odoo18ce` |
| Code Baseline | `60d0778` |
| Browser / Device | Awaiting human run details |
| Human Verifier | Not yet recorded |

## 2. Human Verification Contract Baseline

| Source | ID | Verification |
|---|---|---|
| CC-005 | CC5-TEST-014~020 | All widths no Preview; Desktop/Narrow layout and configured Action |
| CC-005 | CC5-TEST-021~028 | Numbered pagination, page-size choices, offsets and page states |
| CC-004 | CC4-TEST-005, CC4-TEST-008 | Workspace no Preview and record Action navigation |

## 3. Current Human Verification Status

| Metric | Value |
|---|---|
| Human Verification Required | Yes |
| Required scenarios | 5 |
| PASS / FAIL / BLOCKED | 0 / 0 / 0 |
| NOT RUN | 5 |
| Current code baseline | `60d0778` |
| Current valid evidence | None |
| Evidence baseline status | Incomplete |

No human verifier or HVR run has been recorded. **No PASS is claimed.**

## 4. Human Verification Coverage Matrix

| Requirement | Scenario | Current Evidence | Result |
|---|---|---|---|
| Odoo shell loads | HVR-SCN-001 | — | NOT RUN |
| Configured Form Action opens | HVR-SCN-002 | — | NOT RUN |
| Query `009` page navigation works | HVR-SCN-003 | — | NOT RUN |
| Page-size controls and dynamic page links work | HVR-SCN-004 | — | NOT RUN |
| Preview absent at Desktop/Narrow; no Preview request | HVR-SCN-005 | — | NOT RUN |

## 5. Verification Scenarios

### HVR-SCN-001 — Odoo web shell recovery

- **Purpose:** Confirm removal of globally injected Workspace assets no longer leaves the Odoo backend blank.
- **Steps:** Hard-refresh `http://127.0.0.1:8091/odoo`; confirm the Odoo app loads. Open the configured Contact Form Action for record 143.
- **Expected:** Both Odoo home and Form Action render without a blank page or frontend error.
- **Evidence:** Human observation and browser console state.

### HVR-SCN-002 — Configured Form Action

- **Purpose:** Confirm Workspace opens records using the configured Odoo Form Action without Preview.
- **Steps:** Search for an accessible record and double-click it.
- **Expected:** The configured native Form opens; Workspace has not called `/wd_global_search/api/preview`.
- **Evidence:** Browser URL/page and network observation.

### HVR-SCN-003 — Page-two search regression

- **Purpose:** Recheck the reported `Search unavailable` failure after the narrow-scroll helper fix.
- **Steps:** Search `009`, note the total/page count, then click page 2.
- **Expected:** Page 2 results render; no `Search unavailable` message; request uses the expected offset and preserves the total.
- **Evidence:** Visible page summary and browser console/network observation.

### HVR-SCN-004 — Page-size and numbered navigation

- **Purpose:** Confirm Google-style pagination after real user interaction.
- **Steps:** Exercise page numbers, First/Previous/Next/Last, and page sizes 10, 20, 50, and 100.
- **Expected:** The selected page and page size are honored; changing query/refinement/page size resets to page 1.
- **Evidence:** Page summary and visible records.

### HVR-SCN-005 — Results-only responsive Workspace

- **Purpose:** Confirm no Preview UI or request at Desktop and Narrow widths.
- **Steps:** At a desktop width and 375px width, search and select a record; inspect the Workspace and network activity.
- **Expected:** No Preview pane at either width and no `/wd_global_search/api/preview` request; Narrow page scroll and configured Action remain usable.
- **Evidence:** Human observation and browser network panel.

## 6. Verification Run History

No `HVR-RUN` has been recorded. The prior user reports of blank Odoo pages and page-two `Search unavailable` are known issues to retest, not evidence that the fixes pass.

## 7. Findings / Issues

No formal `HVR-FIND` is recorded without a human verification run. The reported symptoms remain pending confirmation against code baseline `60d0778`.

## 8. Handoff

This HVR record is intentionally incomplete pending a human verifier's execution and confirmation. The SRS FR-SW-004 Preview requirement remains an explicitly documented, user-approved deviation; this HVR does not mark that SRS requirement as satisfied.
