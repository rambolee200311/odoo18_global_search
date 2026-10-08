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
| Browser / Device | User-shared browser; exact browser/device not recorded |
| Human Verifier | `lijianqiang` |

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
| Required scenarios | 6 |
| PASS / FAIL / BLOCKED | 4 / 0 / 0 |
| NOT RUN | 2 |
| Current code baseline | `60d0778` |
| Current valid evidence | `HVR-RUN-001` (partial scenario coverage) |
| Evidence baseline status | Partial |

The verifier confirmed the Odoo shell/Form Action, query `009` page 2, and no-Preview presentation. Page-size controls and absence of Preview API network requests were not explicitly confirmed and remain NOT RUN.

## 4. Human Verification Coverage Matrix

| Requirement | Scenario | Current Evidence | Result |
|---|---|---|---|
| Odoo shell loads | HVR-SCN-001 | HVR-RUN-001 | PASS |
| Configured Form Action opens | HVR-SCN-002 | HVR-RUN-001 | PASS |
| Query `009` page navigation works | HVR-SCN-003 | HVR-RUN-001 | PASS |
| Page-size controls and dynamic page links work | HVR-SCN-004 | — | NOT RUN |
| Preview absent at Desktop/Narrow | HVR-SCN-005 | HVR-RUN-001 | PASS |
| Workspace sends no Preview API request | HVR-SCN-006 | — | NOT RUN |

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

- **Purpose:** Confirm no Preview UI at Desktop and Narrow widths.
- **Steps:** At Desktop and Narrow widths, search and select a record.
- **Expected:** No Preview pane at either width; Narrow page scroll and configured Action remain usable.
- **Evidence:** Human confirmation in the current session.

### HVR-SCN-006 — No Preview API request

- **Purpose:** Confirm selecting a result does not make a hidden Preview request.
- **Steps:** Observe browser network activity while selecting results at Desktop and Narrow widths.
- **Expected:** No `/wd_global_search/api/preview` request is issued by the Workspace.
- **Evidence:** Browser network panel; NOT RUN.

## 6. Verification Run History

### HVR-RUN-001

| Field | Value |
|---|---|
| Date | 2026-10-08 |
| Human Verifier | `lijianqiang` |
| Execution Assistance | Agent/tool-assisted; human verifier confirmed the observed outcomes |
| Code Baseline | `60d0778` |
| Environment | Odoo 18, `http://127.0.0.1:8091`, database `odoo18ce` |
| Scope | Odoo shell/Form Action, query `009` page 2, Desktop/Narrow no-Preview presentation |
| Result | PARTIAL — four scenarios confirmed; two remain NOT RUN |
| Evidence | Human confirmation in the current conversation; no screenshot/network capture attached |

## 7. Findings / Issues

No new finding was reported in the confirmed scenarios. The prior blank-page and page-two symptoms were reported as resolved by the verifier for the scenarios listed in HVR-RUN-001.

## 8. Handoff

This HVR remains partial: verify HVR-SCN-004 and HVR-SCN-006 before closure. The SRS FR-SW-004 Preview requirement remains an explicitly documented, user-approved deviation; this HVR does not mark that SRS requirement as satisfied.
