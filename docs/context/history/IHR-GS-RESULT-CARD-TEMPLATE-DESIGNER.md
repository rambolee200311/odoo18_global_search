# IHR-GS-RESULT-CARD-TEMPLATE-DESIGNER

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-TEMPLATE-DESIGNER` |
| CC | CC-014 v0.1 FROZEN |
| Module | `wd_global_search` |
| Work type | Result Card template, designer and live preview |
| Implementer | Copilot assistant |
| Start date | 2026-10-10 |
| Implementation state | In Progress; core path implemented, required evidence incomplete |
| Base commit | `3024403` (`Implement CC-013 native form navigation`) |

## 2. Coding Contract Baseline

- CC-014 v0.1 FROZEN defines the template grammar, Resource configuration, preview UI/API,
  field authorization, formatting, Apply lifecycle, and CC14-TEST-001~031.
- Upstream baseline: SRS v1.5 FROZEN, TDD v0.4 FROZEN, Implementation Plan v0.3 FROZEN.
- CC-013 Action navigation and CC-001 Published Snapshot/Apply semantics remain unchanged.
- No Odoo core or official addon files were changed. Business records are accessed through the
  current-user ORM environment; no direct database queries or `sudo()` were added.

## 3. Current Implementation Summary

| Item | Status |
|---|---|
| CC-014 implementation | Core parser, validator, renderer, Resource field, Preview API and designer UI implemented |
| Published/Apply preservation | ORM test verifies staging, active checksum stability and Apply update |
| Search integration | Executor emits template-rendered plain text; legacy snapshots retain the old Card path until explicit migration |
| Security | Server-owned Resource/model/field resolution; current-user record and field access; session-bound opaque record token; CSRF-protected POST routes; 60/minute preview limiter |
| Browser evidence | Integrated browser validated live preview sources, keyboard field insertion, text-only XSS handling and responsive overflow at 390/768/1280px |
| ATR/HVR | Partial; see linked records |
| Open issues | Full CC14-TEST-001~031 evidence, non-manager/field-revocation HVR, formatter matrix, performance budget and Save/Apply browser flow remain outstanding |

## 4. Implementation History

### IHR-001 — Freezing the approved contract baseline

- **Action:** Changed CC-014 governance and review history to FROZEN after explicit user approval.
- **Files:** `docs/context/intent/CC-014_result_card_template_designer.md`
- **Contract:** CC-014 §0, §17
- **Result:** Completed

### IHR-002 — Adding the template parser and publish validation

- **Action:** Added a bounded parser for constants, escapes, newline/tab tokens and field/format
  variables; enforced the 8 KiB and 50-occurrence limits; validated supported stored fields,
  formatter compatibility, mapped-model coverage and monetary currency metadata.
- **Files:** `services/template.py`, `models/configuration.py`
- **Contract:** CC14-INV-002/003/009/021/022/023; CC14-TEST-002/007/024/025
- **Result:** Completed for implemented unit/ORM coverage

### IHR-003 — Binding template content to Published Snapshots

- **Action:** Added `card_template` to Business Resource and Snapshot generation. Published/Retired
  edits use the existing pending-change and explicit Apply lifecycle. Legacy Card fields remain a
  deterministic, explicit migration suggestion; configurations with non-equivalent empty-value
  behavior must provide a template before Apply.
- **Files:** `models/configuration.py`, `views/configuration_views.xml`
- **Contract:** CC14-INV-001/018; CC14-DEC-001/014/015; CC14-TEST-001/010/028
- **Result:** Completed for model lifecycle; browser Save/Apply HVR remains open

### IHR-004 — Rendering authorized plain-text Result Cards

- **Action:** Search Executor now reads template variables from the Published Resource snapshot,
  authorizes fields per request user, checks Many2one target access before reading display names,
  formats values on the server, and returns one plain-text Card body. The browser creates a text
  node; it does not parse template output as HTML. Existing snapshots without a template continue
  through the legacy serializer until migrated.
- **Files:** `services/card.py`, `services/executor.py`, `services/template.py`,
  `static/src/js/preview.js`, `static/src/css/preview.css`
- **Contract:** CC14-INV-004/005/006/010/011/019/020; CC14-TEST-003/004/005/006/011
- **Result:** Completed for tested Search Executor/relationship paths; formatter and permission matrix remains incomplete

### IHR-005 — Adding the authenticated Preview and designer

- **Action:** Added a configuration-manager-only designer page, common-field list, keyboard and drag
  insertion, 300 ms debounce, abort/sequence stale-response protection, latest/manual/synthetic
  sources, CSRF-protected Save/Apply/Preview routes, current-user ORM reads, session-scoped opaque
  `record_id` tokens and preview rate limiting. Preview distinguishes inaccessible existing fields
  with `[无权访问]`; production leaves those variables blank.
- **Files:** `controllers/main.py`, `static/src/js/template_designer.js`,
  `static/src/css/template_designer.css`, `views/configuration_views.xml`
- **Contract:** CC14-INV-012~017; CC14-DEC-008~013/026; CC14-TEST-008/009/016~019/022/023/026/027/029/031
- **Result:** Core behavior implemented; role, CSRF-negative, limiter-threshold and browser Save/Apply cases not all verified

### IHR-006 — Adding automated and human evidence

- **Action:** Added parser, renderer, Search Executor, configuration staging and navigation fixture
  coverage; ran the module suite and authenticated browser smoke checks.
- **Files:** `tests/test_template.py`, `tests/test_configuration.py`, `tests/test_navigation.py`,
  `tests/__init__.py`, `README.md`, linked ATR/HVR records
- **Contract:** CC14-TEST-001~031; CC-002~CC-013 regression
- **Result:** Partial; no FR closure assessment yet

## 5. Actual Change Inventory

| File | Change |
|---|---|
| `docs/context/intent/CC-014_result_card_template_designer.md` | Recorded approved FROZEN status and approval history |
| `mymodules/wd_global_search/services/template.py` | Parser, validation, formatting and plain-text renderer |
| `mymodules/wd_global_search/models/configuration.py` | `card_template`, publish validation and Snapshot field |
| `mymodules/wd_global_search/services/card.py` | Template field authorization, Many2one/currency safe reads and rendering |
| `mymodules/wd_global_search/services/executor.py` | Published-template Search Card projection |
| `mymodules/wd_global_search/controllers/main.py` | Manager-gated designer, Preview/record selection/Save/Apply endpoints |
| `mymodules/wd_global_search/static/src/js/template_designer.js` | Accessible editor, field insertion, debounce and response ordering |
| `mymodules/wd_global_search/static/src/css/template_designer.css` | Responsive designer layout |
| `mymodules/wd_global_search/static/src/js/preview.js` | Text-node rendering for template Card bodies |
| `mymodules/wd_global_search/static/src/css/preview.css` | Template Card text layout |
| `mymodules/wd_global_search/views/configuration_views.xml` | Template field and designer menu |
| `mymodules/wd_global_search/tests/test_template.py` | Parser, renderer, Search projection and access-placeholder tests |
| `mymodules/wd_global_search/tests/test_configuration.py` | Snapshot and Save/Apply staging tests |
| `mymodules/wd_global_search/tests/test_navigation.py` | Required template on CC-013 navigation fixtures |
| `README.md` | Designer use and migration notes |

## 6. Deviation / Stop Conditions

- No unauthorized scope deviation recorded.
- Manual-record selection uses the frozen request field `record_id` as a random, session-bound
  opaque token. The server resolves it to model/record only from the authenticated session and
  rechecks current ORM access; the client does not supply a model.
- Browser Save/Apply was not run against shared active configuration because doing so would persist
  a user-visible configuration change. The ORM transaction test covers lifecycle behavior instead.

## 7. Open Issues / Follow-up

| ID | Description | Severity | Status |
|---|---|---|---|
| OI-001 | Complete the full CC14-TEST-001~031 coverage matrix, including locale/formatter and performance thresholds | Major | Open |
| OI-002 | Verify as a non-manager and after field/record permission revocation; test CSRF rejection and request 61 rate-limit boundary | Major | Open |
| OI-003 | Complete browser Save → pending → Apply → refreshed Search Card HVR on an isolated/test configuration | Major | Open |
| OI-004 | Exercise mouse drag positions, Escape, wider browser compatibility matrix and console/network assertions | Minor | Open |
| OI-005 | Verify deterministic legacy migration with hidden fields, duplicate sequence and `allow_empty=False` fixtures | Major | Open |

## 8. Handoff

```
Implemented: parser, validation, Snapshot field, Search renderer, Preview API and designer core
Automated tests: 36 module tests passed on the recorded run; see ATR
Human verification: partial browser smoke only; see HVR-016
Open issues: OI-001~OI-005
Deviation: None; opaque session record token is an implementation of the frozen `record_id` boundary
Stop conditions triggered: None
Coding closure: Not ready; required evidence remains incomplete
```
