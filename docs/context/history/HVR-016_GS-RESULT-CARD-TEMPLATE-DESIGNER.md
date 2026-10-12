# HVR-016 — CC-014 Result Card Template Designer

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-TEMPLATE-DESIGNER` |
| CC | CC-014 v0.1 FROZEN |
| IHR | `IHR-GS-RESULT-CARD-TEMPLATE-DESIGNER.md` |
| ATR | `ATR-GS-RESULT-CARD-TEMPLATE-DESIGNER.md` |
| Module | `wd_global_search` |
| Environment | Odoo 18 CE, local `odoo18ce`, macOS |
| Browser/device | Integrated browser, exact engine version/device not exposed |
| Verification type | Agent-assisted browser observation; human acceptance still required |
| Run baseline | `3024403` + uncommitted CC-014 implementation |
| Verification date | 2026-10-10 |

## 2. Human Verification Contract Baseline

| Requirement | Observed browser scenario | Status |
|---|---|---|
| CC14-TEST-008/029 | Insert a field using ArrowDown/Enter | PASS for insertion only |
| CC14-TEST-009/017/018 | Latest, manually selected and synthetic preview; rapid edits/aborted request | PASS for source display and latest final result; stale-order stress is partial |
| CC14-TEST-016 | Designer at 390/768/1280 CSS px | PASS for no horizontal overflow at these widths |
| CC14-TEST-019 | Persistent current-account permission warning | PASS for warning visibility |
| CC14-TEST-023 | Render an `<img onerror>` payload | PASS for text display and no created image node |
| CC14-TEST-010/011 | Save/Apply and visible production Search Card refresh | NOT RUN in browser; ORM tests cover staging and Apply |
| CC14-TEST-014/022/026/027/031 | Non-manager, field/record revocation, forged inputs, hidden Record Rule, negative CSRF/rate-limit | NOT RUN as role/security HVR |

## 3. Current Human Verification Status

| Metric | Value |
|---|---|
| Formal human verification required | Yes |
| Agent-assisted scenarios observed | 5 partial/full UI scenarios |
| Formal human sign-off | NOT RUN |
| Current evidence status | Partial |
| Current code baseline | CC-014 uncommitted working tree based on `3024403` |
| Shared active configuration changed | No |

The browser observations below were performed by the coding agent with the integrated browser. They
are useful HVR evidence but do not replace a human verifier's acceptance, non-manager testing or
Save/Apply verification on an isolated configuration.

## 4. Verification Scenarios

### HVR-SCN-001 — Designer page and permission warning

- **Steps:** Open `/wd_global_search/card_templates` with the local configuration-manager session.
- **Expected:** Designer loads; current-account permission warning remains visible.
- **Observed:** Designer, Resource selector, template editor, preview and field list rendered. Warning
  was visible.
- **Result:** PASS (agent browser observation; human sign-off pending).

### HVR-SCN-002 — Preview sources and refresh

- **Steps:** Edit the template; use latest readable record, select a readable record, and use a
  synthetic example; observe each refreshed result and source label.
- **Expected:** Source is labeled, preview uses the latest template, selected records are read-only,
  and synthetic values do not require a real record.
- **Observed:** All three sources returned previews; rapid edits aborted an in-flight request and the
  final settled preview reflected the latest template. A controlled out-of-order response harness
  was not used.
- **Result:** PASS for source and normal refresh behavior; PARTIAL for race stress.

### HVR-SCN-003 — Keyboard field insertion

- **Steps:** Focus the available field list, press ArrowDown and Enter.
- **Expected:** Exactly one `{field_name}` token is inserted at the editor selection and the preview
  refreshes.
- **Observed:** One token was inserted and formatted in the preview.
- **Result:** PASS for this keyboard path; Save/Apply shortcuts and Escape remain NOT RUN.

### HVR-SCN-004 — Text-only rendering / injection safety

- **Steps:** Enter a template constant containing `<img src=x onerror=alert(1)>`; inspect preview
  text and DOM descendants.
- **Expected:** Payload appears as text; no image/script node or event handler is created.
- **Observed:** The payload remained visible text and the preview contained zero `img` nodes. No
  script dialog or execution was observed.
- **Result:** PASS for the tested payload. Full script/attribute/Network matrix remains NOT RUN.

### HVR-SCN-005 — Responsive layout

- **Steps:** Set integrated browser viewport widths to 390, 768 and 1280 CSS pixels; inspect body
  scroll width and visible controls.
- **Expected:** Editor, preview, warning and field list remain reachable without horizontal page
  overflow.
- **Observed:** Initial 390px run found a 10px overflow in long field-list buttons. Added wrapping and
  min-width constraints; rerun measured `scrollWidth == clientWidth` at 390, 768 and 1280px.
- **Result:** PASS for the measured widths after the fix; tablet/other desktop breakpoints remain
  unverified.

### HVR-SCN-006 — Save, Apply and production Card refresh

- **Steps:** Save a template on an isolated Published Resource, verify pending state and unchanged
  active checksum, Apply, then Search and inspect the Card.
- **Expected:** Existing Snapshot remains active until Apply; then the new template renders without
  changing Search identity/count/pagination or CC-013 navigation.
- **Observed:** Not run in browser because the available session shares active configuration and
  applying would persist a user-visible change. The ORM transaction test verifies staged checksum
  stability and Apply publication; Search Executor tests verify rendered text.
- **Result:** NOT RUN (browser); automated coverage partial.

### HVR-SCN-007 — Reduced permissions, Record Rule and invalid record

- **Steps:** Open as a non-manager; revoke a template variable field or record; exercise latest,
  manual and synthetic sources; verify hidden records remain inaccessible.
- **Expected:** Manager-only API denies ordinary users; Preview shows `[无权访问]` for unreadable
  existing fields; real records obey ACL/Record Rules; no sudo fallback or sensitive error details.
- **Observed:** No separate role or permission-revocation session was available for this run.
- **Result:** NOT RUN.

## 5. Verification Run History

### HVR-RUN-001 — Integrated browser inspection

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Verifier | Copilot assistant (agent-assisted; not user sign-off) |
| Environment | Local Odoo 18 `odoo18ce`, port 8092 |
| Browser page | Integrated browser page for `/wd_global_search/card_templates` |
| Scenarios | HVR-SCN-001~005 |
| Result | PARTIAL |
| Evidence | Browser snapshots/interactions: source previews, field insertion, text-only image payload, responsive overflow before/after wrapping fix |
| Console/Network note | Invalid template preview returned the expected HTTP 400 validation response; rapid-edit request cancellation produced `ERR_ABORTED`. No script execution was observed. |
| Follow-up | Human sign-off, Save/Apply workflow, permission revocation, CSRF-negative and browser matrix remain outstanding. |

## 6. Blockers / Handoff

1. HVR-SCN-006 is NOT RUN in browser; execute on an isolated/test configuration before claiming
   visible Search Card update.
2. HVR-SCN-007 is NOT RUN; verify with an ordinary user and controlled field/record access changes.
3. Exact browser engine/version was unavailable; Firefox, Safari and other browser compatibility are
   NOT RUN.
4. This HVR does not close CC-014. Human Review and the remaining ATR/CC test evidence are required.
