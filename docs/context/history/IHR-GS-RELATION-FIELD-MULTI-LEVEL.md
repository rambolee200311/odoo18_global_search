# IHR-GS-RELATION-FIELD-MULTI-LEVEL

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-RELATION-FIELD-MULTI-LEVEL` |
| CC | [CC-014-1 v0.1 FROZEN](../intent/CC-014-1_relation_field_multi_level.md) |
| Module | `wd_global_search` |
| Work type | Result Card relation paths and One2many loops |
| Implementer | Copilot assistant |
| Date | 2026-10-12 |
| Branch / base | `main` / `09f2629` |
| Current implementation state | Implementation complete; HVR run recorded; FR assessment pending |

The tested code baseline is commit `09f2629` plus the uncommitted working-tree changes listed in
§5. This is not a committed release baseline.

## 2. Coding Contract Baseline

- CC-014-1 v0.1 FROZEN defines relation path types/depth, One2many loop scope, limits,
  formatting, empty handling, security, Publish validation, and CC14-1-TEST-001~038.
- CC-014 remains the source for the existing template editor, formatter, published snapshot, and
  single-field behavior.
- CC-003's current-user access boundary and CC-013 navigation remain unchanged.
- No SRS, TDD, implementation-plan, or existing CC-001~CC-014 was modified during implementation.
  CC-014-1's warehouse examples were corrected by the approved erratum before the contract was
  frozen.

## 3. Current Implementation Summary

| Area | Result |
|---|---|
| Template syntax | Parser represents variables and nested One2many blocks; path, field type, scope, depth, loop count, body length, and tag pairing are validated from model metadata. |
| Related path resolution | Many2one and Many2many paths are resolved using the current user's ORM environment. A terminal Odoo delegated/related alias is expanded to its declared field path only inside an explicit multi-level token; the effective relation path is validated and depth-counted. Single-field CC-014 behavior remains unchanged. |
| Loop rendering | One2many loops render each current-user-readable item, support nested loops up to the contract limit, and keep loop values scoped to the current item. |
| Permissions | Relation traversal uses normal ORM field checks, model ACLs, and `search` under the current user; inaccessible relation targets fail closed. No `sudo()` or superuser environment was added. |
| Published lifecycle | Many2many separator is stored with Resource configuration and its Published Snapshot. Existing Apply/Publish validation remains authoritative. |
| Designer / Check | Designer supports relationship field descriptors, separator editing, relation insertion and loop skeleton insertion; Check, Preview, Save and Publish share template validation. Structural validation uses model metadata and does not search/read business records. |
| Automated evidence | Final module suite and performance sample results are recorded in [ATR](./ATR-GS-RELATION-FIELD-MULTI-LEVEL.md). |
| Human evidence | User-confirmed HVR pass is recorded in [HVR](./HVR-GS-RELATION-FIELD-MULTI-LEVEL.md); scenario-level output detail was not supplied. |

## 4. Implementation History

### IHR-001 — Extending relation-template parsing and validation

- **Action:** Added dot-path variables, nested One2many loop blocks, scope checks, relation-type
  restrictions, effective depth checks, loop-count/body-size limits, and Publish-time validation.
- **Files:** `services/template.py`
- **Contract:** CC14-1-INV-001~012, INV-018~020; §14; TEST-001~025, TEST-035
- **Result:** Completed
- **Deviation:** None

### IHR-002 — Resolving relation paths and loop rows

- **Action:** Extended Result Card reads/rendering to retain the Search root record, resolve
  Many2one/Many2many segments and render One2many loop items through ordinary ORM access.
  Odoo delegated terminal aliases such as `product.product.name` are expanded through their
  declared relation path for explicit dotted paths; direct `{name}` retains CC-014's prior
  rejection behavior for that non-stored related field.
- **Files:** `services/template.py`, `services/card.py`
- **Contract:** CC14-1-INV-004~010, INV-013~023; §5~§12
- **Result:** Completed
- **Deviation:** None; this reconciles the frozen `{product_id.name}` loop example with existing
  single-field validation without permitting arbitrary related/computed-field traversal.

### IHR-003 — Binding separator and structural Check to existing configuration lifecycle

- **Action:** Added a Resource Many2many separator, included it in configuration validation and
  Published Snapshot serialization, and wired designer Check/Preview/Save to the shared
  validator. The field picker exposes relationship type metadata and loop insertion.
- **Files:** `models/configuration.py`, `controllers/main.py`,
  `static/src/js/template_designer_page.js`, `static/src/css/template_designer.css`,
  `views/configuration_views.xml`, `__manifest__.py`, `README.md`
- **Contract:** CC14-1-INV-006; §6, §14, §16, §20
- **Result:** Completed
- **Deviation:** None; no new architecture or external search dependency was added.

### IHR-004 — Correcting issues found during automated verification

- **Action:** Removed a parser-local `_` binding that shadowed Odoo's translation helper; used
  Odoo Monetary's model-aware `get_currency_field()` for default currency fields; preserved
  existing single-field related-field rejection while enabling validated explicit path expansion;
  corrected the test double and record-rule fixture to model Odoo ORM behavior.
- **Files:** `services/template.py`, `services/card.py`, `tests/test_template.py`
- **Contract:** CC-014 compatibility; CC14-1-INV-002/004/009/014~017/020~023;
  TEST-004/018/019/026/029/030
- **Result:** Completed; final module run passed.
- **Deviation:** None

### IHR-005 — Adding regression evidence

- **Action:** Added relation-path, loop, separator, scope, depth/type limit, empty-value,
  HTML/plain-text, permission-rule, Search integration, and published-configuration tests.
- **Files:** `tests/test_template.py`, `tests/test_configuration.py`
- **Contract:** CC14-1-TEST-001~037; CC-002~CC-014 regression requirements
- **Result:** Completed for automated coverage; performance sampling was added in IHR-006.

### IHR-006 — Measuring relation rendering performance

- **Action:** Added 100-sample parser, validation, and cold-/warm-cache rendering measurements for
  Many2one paths, Many2many paths, and One2many loops. Human verification and final evidence
  reconciliation are recorded separately in HVR and FR.
- **Files:** `tests/test_template.py`
- **Contract:** CC14-1-TEST-038; CC-014 §7.3 performance budgets
- **Result:** Completed; measurements and environment are recorded in ATR.
- **Deviation:** None

## 5. Actual Change Inventory

| File | Action | Scope |
|---|---|---|
| `docs/context/intent/CC-014-1_relation_field_multi_level.md` | Modified | Approved `stock.warehouse.partner_id` examples and related acceptance erratum |
| `README.md` | Modified | Relation path, loop, structural Check, and separator usage |
| `mymodules/wd_global_search/__manifest__.py` | Modified | Module version |
| `mymodules/wd_global_search/controllers/main.py` | Modified | Shared template Check/Preview/Save validation and relation metadata |
| `mymodules/wd_global_search/models/configuration.py` | Modified | Separator configuration, validation, and Published Snapshot |
| `mymodules/wd_global_search/services/card.py` | Modified | Root-record retention, relation reads, and Monetary currency lookup |
| `mymodules/wd_global_search/services/template.py` | Modified | Parser, validator, related path expansion, renderer, and synthetic preview |
| `mymodules/wd_global_search/static/src/css/template_designer.css` | Modified | Separator editor layout |
| `mymodules/wd_global_search/static/src/js/template_designer_page.js` | Modified | Relation field insertion, loop skeleton, Check, and separator input |
| `mymodules/wd_global_search/tests/test_configuration.py` | Modified | Published separator and invalid Apply lifecycle tests |
| `mymodules/wd_global_search/tests/test_template.py` | Modified | Relation, loop, formatting, permission, integration, and 100-sample performance tests |
| `mymodules/wd_global_search/tests/__init__.py` | Modified | Loads relation-field descriptor tests |
| `mymodules/wd_global_search/tests/test_template_descriptor.py` | Added | Preview-user field readability and group-restriction descriptor tests |
| `mymodules/wd_global_search/views/configuration_views.xml` | Modified | Resource form field loading |
| `docs/context/history/IHR-GS-RELATION-FIELD-MULTI-LEVEL.md` | Added | Implementation history |
| `docs/context/history/ATR-GS-RELATION-FIELD-MULTI-LEVEL.md` | Added | Automated test evidence |
| `docs/context/history/HVR-GS-RELATION-FIELD-MULTI-LEVEL.md` | Added | Human verification scenarios and user-confirmed run |
| `docs/context/history/FR-GS-RELATION-FIELD-MULTI-LEVEL.md` | Added | Final closure assessment |
| `docs/implementation/CC-014_card_template_admin_guide.md` | Added | Administrator template-design guide |

No files under `odoo/` or official `addons/` were changed.

## 6. Deviation / Stop Conditions

- Unauthorized deviation: None.
- Frozen-contract revision: None.
- `sudo()` / superuser environment: None added.
- Direct database access: None added; model metadata and record access use Odoo ORM.
- Stop condition: None remains open. The related-field compatibility issue was resolved by
  restricting expansion to explicit dotted paths and validating the expanded path, not by
  enabling arbitrary related fields.

## 7. Open Issues / Follow-up

| ID | Description | Category | Severity | Status | Owner |
|---|---|---|---|---|---|
| OI-001 | Execute the prepared HVR scenarios as a human on the final working-tree baseline; do not treat automated tests as human acceptance. | Evidence | Major | Closed by HVR-RUN-001; the human verifier confirmed all required scenarios passed, while detailed per-scenario output was not supplied. | Human verifier |

## 8. Handoff to ATR / HVR / FR

```text
Implemented: CC14-1 relation paths, One2many loops, validation, separator snapshot, and designer Check integration
Automated evidence: Final module test and performance evidence are recorded in ATR-GS-RELATION-FIELD-MULTI-LEVEL.md
Human evidence: User-confirmed HVR-RUN-001; detailed per-scenario output was not supplied
Open issue: None; see FR-GS-RELATION-FIELD-MULTI-LEVEL.md for closure assessment
Deviation / Stop Conditions: None
```

This IHR records implementation facts only; it does not declare CC-014-1 closed or authorize
merge/release.
