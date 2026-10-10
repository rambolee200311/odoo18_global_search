# IHR-GS-RESULT-CARD-NATIVE-FORM

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-NATIVE-FORM` |
| CC | CC-013 v0.1 FROZEN |
| Module | `wd_global_search` |
| Work type | Result Card Snapshot configuration and configured Native Form Action |
| Implementer | Copilot assistant |
| Implementation state | Implementation Complete; required human scenarios confirmed PASS; FR closure assessment pending |

## 2. Coding Contract Baseline

- CC-013 v0.1 defines Published Snapshot driven Card fields, CC-003 filtered values, and server-side configured Odoo Action resolution from `resource_key + record_id`.
- Native Form readonly behavior remains outside CC-013.
- Composite Resource navigation is explicitly unsupported in v0.1; it is not routed by inspecting `_model`.

## 3. Implementation History Entries

### IHR-001 — Extending the existing Snapshot Field configuration

- **Action:** Added per-field Sequence and Visible options to the existing `wd.gs.snapshot.field`; added default ordering, field type validation, duplicate Sequence rejection and a single-model Resource Action binding.
- **Reason:** Meet the frozen Card configuration and Publish validation contract without introducing a second Card Field registry.
- **Files:** `models/configuration.py`, `views/configuration_views.xml`
- **Contract:** CC13-CHANGE-001/004; CC13-INV-001/004/007
- **Result:** Completed

### IHR-002 — Publishing Action and localized Card metadata

- **Action:** Included Action identity and immutable Action metadata in the Published Resource Snapshot; published Resource/Card Labels in active server languages with English fallback.
- **Reason:** Bind Cards and navigation to the same Published version and detect post-Publish Action drift.
- **Files:** `models/configuration.py`
- **Contract:** CC13-INV-009/011; CC13-DEC-008/011
- **Result:** Completed

### IHR-003 — Serializing authorized Result Cards

- **Action:** Executor reads configured Visible Card fields rather than all Searchable Fields; added server-side permission-filtered Card serialization with configured ordering, labels, formatting and empty-value behavior.
- **Reason:** Separate searchability from presentation and limit Card payload to authorized Published fields.
- **Files:** `services/card.py`, `services/executor.py`, `services/facade.py`
- **Contract:** CC13-CHANGE-001/002; CC13-INV-001/002/003/004/014
- **Result:** Completed

### IHR-004 — Resolving configured Native Form navigation

- **Action:** Replaced the static model-to-XML-ID resolver with a `resource_key + record_id` resolver; rechecks current-user Resource/model/record/Action access, Action group restrictions, Published Action integrity and Form View availability; returns an Odoo 18 Router path.
- **Reason:** Make the server—not the client—own Resource, model and Action resolution.
- **Files:** `services/navigation.py`, `controllers/main.py`
- **Contract:** CC13-CHANGE-003~005; CC13-INV-005~009/012/013
- **Result:** Completed

### IHR-005 — Rendering Cards and explicit Open interaction

- **Action:** Replaced name-only result buttons with DOM-safe Card fields, responsive “More” field disclosure, selection/highlight, keyboard behavior and new-tab navigation using the server-returned same-origin Odoo Router target.
- **Reason:** Implement CC13-CHANGE-001/005 while keeping Workspace Preview absent and Card content independent of Form rendering.
- **Files:** `static/src/js/preview.js`, `static/src/css/preview.css`, `controllers/main.py`
- **Contract:** CC13-INV-001/003/004/006/010/011
- **Result:** Completed

### IHR-006 — Adding Configuration and runtime tests

- **Action:** Added Publish validation, Card serialization, Action resolution/group/drift and current Search regression tests.
- **Files:** `tests/test_configuration.py`, `tests/test_permission_boundary.py`, `tests/test_navigation.py`, `tests/__init__.py`
- **Contract:** CC13-TEST-001~018; selected regression coverage
- **Result:** Completed

### IHR-007 — Applying Card density changes across viewport breakpoints

- **Action:** Keep the “More” disclosure synchronized when crossing the 768px density breakpoint, while preserving a user's manual disclosure choice during resizes within the same density range; bump the Workspace script cache key.
- **Reason:** Ensure responsive density remains correct after rendering and avoid stale cached JavaScript after deployment.
- **Files:** `static/src/js/preview.js`, `controllers/main.py`
- **Contract:** CC-013 §4.3; CC13-TEST-023
- **Result:** Completed; verified in authenticated Chromium at 375, 767, 768, 900, 1023, 1024, and 1440px.

## 4. Actual Change Inventory

| File | Change |
|---|---|
| `models/configuration.py` | Existing SnapshotField/BusinessResource extensions; Publish validation; translated Published metadata and Action binding |
| `views/configuration_views.xml` | Configuration admin controls for Resource Action, Card fields and existing related mappings |
| `services/card.py` | Configured Snapshot field selection, localization, formatting and authorized serialization |
| `services/executor.py` | Search result projection limited to authorized configured Card fields |
| `services/facade.py` | Server-provided localized Resource descriptor integration retained |
| `services/navigation.py` | Published Action resolver and open-time permission checks |
| `controllers/main.py` | Existing `form_url` route now accepts only `resource_key + record_id`; Workspace script cache key updated |
| `static/src/js/preview.js` | DOM-safe Card rendering, accessible selection, keyboard and new-tab open |
| `static/src/css/preview.css` | Card styles, focus/selection and responsive field disclosure |
| `tests/test_configuration.py` | Publish validation and snapshot tests |
| `tests/test_permission_boundary.py` | Card order, i18n and unauthorized/hidden-field serialization test |
| `tests/test_navigation.py` | Configured resolver, unknown resource, action drift and Action group tests |

## 5. Open Issues / Handoff

- Current local `global_search_baseline` Published v5 predates CC-013 and contains no `navigation_action_id` or CC-013 Action metadata. Published versions are immutable; no existing version was rewritten. A configuration administrator must create/publish a new compatible version before a successful Card → configured Action browser HVR.
- Human verifier later confirmed all seven required CC-013 HVR scenarios passed; see HVR-RUN-001. Playwright responsive/keyboard/regression checks are recorded in ATR-RUN-006. Firefox, Safari, and Edge compatibility remains unverified.
- CC-013 does not make Native Form readonly. Do not claim a readonly Form from these changes.
