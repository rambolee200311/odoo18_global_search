# HVR-015 — CC-013 Result Card and Native Form Navigation

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-NATIVE-FORM` |
| CC | CC-013 v0.1 FROZEN |
| IHR | `IHR-GS-RESULT-CARD-NATIVE-FORM.md` |
| ATR | `ATR-GS-RESULT-CARD-NATIVE-FORM.md` |
| Module | `wd_global_search` |
| Environment | Odoo 18, local `odoo18ce` |
| Code baseline | CC-013 implementation working tree; no commit created yet |
| Browser / device | User-reported local Odoo browser; exact browser version/device/viewport not provided |
| Human verifier | `lijianqiang` (user confirmation) |

## 2. Contract Baseline

| Requirement | Scenario | Human verification |
|---|---|---|
| CC13-TEST-002/003/004 | HVR-SCN-001 Card fields/order/config refresh | PASS |
| CC13-TEST-009/010 | HVR-SCN-002 configured Action/new Tab | PASS |
| CC13-TEST-019 | HVR-SCN-003 keyboard interaction | PASS |
| CC13-TEST-014/016 | HVR-SCN-004 Workspace state after opening | PASS |
| CC13-TEST-005/012/020 | HVR-SCN-005 field permission and Action groups | PASS |
| CC13-TEST-013/017 | HVR-SCN-006 deleted/revoked/error safety | PASS |
| CC13-TEST-022 | HVR-SCN-007 console and business-write behavior | PASS |

## 3. Current Human Verification Status

| Metric | Value |
|---|---|
| Human verification required | Yes |
| Required scenarios | 7 |
| PASS / FAIL / BLOCKED (current post-fix run) | 0 / 0 / 7 |
| NOT RUN (current post-fix run) | 7 |
| Current code baseline | CC-013 working tree with post-verification navigation fixes |
| Historical evidence | `HVR-RUN-001` (superseded for current code/configuration) |
| Evidence baseline | The earlier PASS report is not current evidence: later Action-context/domain failures were found, and the post-fix integrated-browser page remained hidden with an empty body. |

HVR-RUN-001 preserves the earlier user-reported result. Subsequent checks found Action expressions
that failed on standalone navigation; the affected Published mappings were corrected and all seven
server-side resolvers now succeed. The seven human scenarios have not been rerun against that
post-fix baseline. The user explicitly approved closing CC-013; that approval is recorded in the FR
as acceptance of the remaining verification deferrals, not as evidence that the scenarios passed.

## 4. Verification Scenarios

### HVR-SCN-001 — Configured Card display

- **Steps:** After publishing a compatible configuration, search Customer and Sales Order records.
- **Expected:** Card shows only configured Visible, authorized fields in Sequence order with
  current-user translated Labels and locale formatting.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

### HVR-SCN-002 — Configured Action and New Tab

- **Steps:** Double-click a single-model Resource Card and separately Ctrl/Cmd-click it.
- **Expected:** New Tab opens the matching record via its configured Odoo Form Action; Workspace
  remains open; no Preview API is called.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

### HVR-SCN-003 — Keyboard interaction

- **Steps:** Use Tab/Shift+Tab, Space, Enter, Ctrl/Cmd+Enter and Escape on Result Cards.
- **Expected:** Focus order and selection/open semantics follow CC-013; disclosure-summary keyboard
  events do not accidentally trigger record navigation.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

### HVR-SCN-004 — Workspace state after opening

- **Steps:** Open a result and verify the Workspace query, refinements, and Resource selection remain intact.
- **Expected:** Opening the Form in a new Tab does not replace or reset the Workspace state.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

### HVR-SCN-005 — Field/Action authorization

- **Steps:** Compare users with full/partial field access and users inside/outside configured Action
  group restrictions.
- **Expected:** Unauthorized values are omitted; disallowed Action does not open; error does not
  disclose record or Action existence.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

### HVR-SCN-006 — Deleted/revoked record and failure safety

- **Steps:** Search a record, remove access/delete it before open, then attempt navigation.
- **Expected:** Generic safe error; no field values, internal Action identifier or record existence
  disclosure.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

### HVR-SCN-007 — Browser console and business-write behavior

- **Steps:** Observe browser console and network activity while interacting with a Card.
- **Expected:** No browser console errors and no business write RPC is triggered by Card interaction.
- **Result:** PASS — the human verifier confirmed this scenario passed on 2026-10-10; no step-level observation was supplied.

## 5. Verification Run History

### HVR-RUN-001 — Historical, superseded

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Human Verifier | `lijianqiang` |
| Verification Type | Functional |
| Run Code Baseline | `68a7289` plus the uncommitted CC-013 implementation working tree |
| Environment | Local Odoo 18 (`http://127.0.0.1:8091`); exact browser/device details not supplied |
| Scenarios | HVR-SCN-001~007 |
| Execution Assistance | Agent-assisted record keeping; human verifier confirmed all seven scenarios passed |
| Result Summary | Historical user-reported PASS — not valid evidence for the post-fix code/configuration |
| Evidence | Earlier user confirmation in the conversation on 2026-10-10; no screenshot or per-scenario observation supplied |
| Follow-up | Post-fix HVR-SCN-001~007 were not rerun. Closure approval and accepted deferrals are documented in FR. |

## 6. Blockers / Handoff

1. HVR-SCN-001~007 were reported PASS in HVR-RUN-001, but that run is superseded after later navigation failures and fixes; current post-fix human verification remains NOT RUN.
2. CC13-TEST-023 responsive Card disclosure and the browser compatibility matrix are not covered by the required HVR scenarios above; FR must determine whether they have valid ATR evidence or remain a closure blocker.
3. Composite Resource Native Form navigation is intentionally unsupported in v0.1.
4. Readonly Native Form remains a separate contract; this HVR does not claim it.
