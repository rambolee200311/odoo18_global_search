# HVR-GS-RELATION-FIELD-MULTI-LEVEL

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-RELATION-FIELD-MULTI-LEVEL` |
| CC Version | CC-014-1 v0.1 FROZEN |
| IHR | [IHR-GS-RELATION-FIELD-MULTI-LEVEL.md](./IHR-GS-RELATION-FIELD-MULTI-LEVEL.md) |
| ATR | [ATR-GS-RELATION-FIELD-MULTI-LEVEL.md](./ATR-GS-RELATION-FIELD-MULTI-LEVEL.md) |
| Module | `wd_global_search` |
| Environment | Local Odoo 18 CE `odoo18ce`, accessed at `127.0.0.1:8091`; browser/device version not supplied |
| Application Version | `wd_global_search` 18.0.1.2.0 |
| Initial / current baseline | Commit `09f2629` plus CC-014-1 working-tree changes; the later change was test-only performance instrumentation |
| Human verifier | Odoo Administrator (UID 1; identity confirmed by the user) |
| Verification status | HVR-RUN-001 recorded from the user's explicit aggregate pass confirmation |

## 2. Human Verification Contract Baseline

Scenarios below derive from CC-014-1 §4~§14, §15 and §18, and the designer/Preview behavior
inherited from CC-014. This HVR does not add acceptance criteria or treat ATR results as human
evidence.

## 3. Current Human Verification Status

| Metric | Value |
|---|---:|
| Human verification required | Yes |
| Required scenarios | 5 |
| PASS / FAIL / BLOCKED | 5 / 0 / 0 |
| NOT RUN | 0 |
| Current valid evidence set | HVR-EVD-001, user confirmation for HVR-RUN-001 |
| Evidence baseline status | Partial; per-scenario observations, browser version, and screenshots were not supplied |

## 4. Human Verification Coverage Matrix

| Requirement | Scenario | Current evidence | Result | Baseline validity |
|---|---|---|---|---|
| Designer syntax Check and validation feedback | HVR-SCN-001 | HVR-RUN-001; user-confirmed aggregate pass, details not supplied | PASS | Current runtime baseline; attestation is summarized |
| Relation Preview and Many2many separator | HVR-SCN-002 | HVR-RUN-001; user-confirmed aggregate pass, details not supplied | PASS | Current runtime baseline; attestation is summarized |
| One2many and nested-loop rendering | HVR-SCN-003 | HVR-RUN-001; user-confirmed aggregate pass, details not supplied | PASS | Current runtime baseline; attestation is summarized |
| Current-user permission and plain-text output | HVR-SCN-004 | HVR-RUN-001; user-confirmed aggregate pass, details not supplied | PASS | Current runtime baseline; attestation is summarized |
| Published Configuration persistence and CC-013 navigation | HVR-SCN-005 | HVR-RUN-001; user-confirmed aggregate pass, details not supplied | PASS | Current runtime baseline; attestation is summarized |

## 5. Verification Scenarios

### HVR-SCN-001 — Check valid and invalid relation paths

- **Purpose:** Verify the designer exposes the same relation syntax and Publish-time structural
  validation described by CC-014-1.
- **Upstream:** CC-014-1 §4~§8, §14; TEST-001~010, TEST-024~025.
- **Preconditions:** Use an isolated development Resource mapped to `stock.warehouse`; open the
  template designer as a configuration manager.
- **Steps:** Enter `{partner_id.country_id.name}` and run Check; then enter the four-hop
  `{partner_id.parent_id.parent_id.country_id.name}` and run Check. Verify loop tag pairing using
  one valid and one unclosed block.
- **Expected:** The supported path/block passes; over-depth or malformed syntax is rejected with
  a visible validation message. No business records are changed by Check.
- **Evidence required:** Human observation; capture sanitized screenshot only if useful.

### HVR-SCN-002 — Preview relation values and separator

- **Purpose:** Verify Preview renders Many2one/Many2many paths and uses the configured separator.
- **Upstream:** CC-014-1 §5~§6, §9~§10; TEST-001~007, TEST-033~034.
- **Preconditions:** Use isolated Resource configurations mapped to `stock.warehouse` for the
  Many2one path and `res.partner` for the Many2many path; prepare a warehouse address/country and
  a partner with at least two categories.
- **Steps:** Preview `{partner_id.country_id.name}` and `{category_id.name}`; change the
  Many2many separator from `, ` to ` | ` and preview again.
- **Expected:** Values follow the chosen record; Many2many members use the published/configured
  separator; empty relations render `—`.
- **Evidence required:** Human observation; note the selected source record and displayed text.

### HVR-SCN-003 — Preview One2many loops and nested loops

- **Purpose:** Verify loop output follows current-item scope and empty loops emit no body.
- **Upstream:** CC-014-1 §7, §9~§11; TEST-011~025, TEST-033.
- **Preconditions:** Use isolated sales-order test data with multiple lines; where available,
  include an empty order and a nested One2many example.
- **Steps:** Preview
  `{order_line}{product_id.name} × {product_uom_qty} = {price_subtotal:monetary}\n{/order_line}`;
  switch to an order with no lines; then check the nested loop template allowed by the contract.
- **Expected:** Each line renders its own product, quantity and formatted subtotal; no root-only
  field leaks into loop scope; an empty loop emits no body; the configured nesting limit is
  enforced.
- **Evidence required:** Human observation of the rendered card and selected record.

### HVR-SCN-004 — Verify permissions and plain-text rendering

- **Purpose:** Verify relation traversal respects the current user's access and that template text
  is displayed as text rather than executable HTML.
- **Upstream:** CC-014-1 §12, §13, §16; TEST-026~030.
- **Preconditions:** Prepare one restricted test user and records subject to a Record Rule; include
  a harmless literal such as `<b>literal</b>` in a test template.
- **Steps:** Run Search as the restricted user for a record with visible and rule-hidden related
  rows; inspect the Card and the literal output.
- **Expected:** Hidden relation data is not disclosed; allowed data renders; markup remains literal
  text and does not create formatted/injected HTML.
- **Evidence required:** Human observation; do not capture credentials or sensitive record data.

### HVR-SCN-005 — Verify Apply persistence and existing navigation

- **Purpose:** Verify the edited template/separator are published through the existing lifecycle
  and that CC-013 navigation remains intact.
- **Upstream:** CC-014-1 §16; CC-014 configuration lifecycle; CC-013 navigation contract.
- **Preconditions:** Use an isolated test Resource or an explicitly approved test database; record
  its original configuration before applying changes.
- **Steps:** Save and Apply a valid template, reopen the Resource, execute Search, open a result
  through its existing configured Action, and return to Search.
- **Expected:** The Published Snapshot is used by Search; navigation behavior is unchanged; no
  Workspace-only value mutates the published configuration.
- **Evidence required:** Human observation; record the exact Resource and test role, not secret data.

## 6. Verification Run History

### HVR-RUN-001 — User-confirmed manual verification

| Field | Value |
|---|---|
| Run date | 2026-10-12 14:50 +08 |
| Human verifier | Odoo Administrator (UID 1; identity confirmed by the user) |
| Verification type | Manual functional verification |
| Code baseline | Commit `09f2629` plus CC-014-1 working-tree implementation |
| Environment | Odoo 18 CE `odoo18ce` at `127.0.0.1:8091`; browser/device version not supplied |
| Scenarios | HVR-SCN-001~005 |
| Result | PASS — the user explicitly reported that manual verification passed and approved CC-014-1 closure |
| Actual observations | Per-scenario displayed values, exact steps, and artifacts were not included in the user's confirmation; no individual output has been inferred here |
| Evidence baseline | Partial detail; runtime implementation was not changed after this run, and the later source change only added automated performance measurement |

## 7. Human Regression Verification

| Regression | Scenario | Run | Result |
|---|---|---|---|
| CC-013 Result Card / Native Form navigation | HVR-SCN-005 | HVR-RUN-001 | PASS (user-confirmed) |

## 8. Findings / Issues

No functional failure was reported. Evidence detail limitation: the user's aggregate pass
confirmation did not include scenario-by-scenario observations or screenshots.

## 9. Evidence Inventory

| Evidence | Type | Reference | Scope | Notes |
|---|---|---|---|---|
| HVR-EVD-001 | Explicit user confirmation | Current conversation, 2026-10-12 14:50 +08 | HVR-SCN-001~005 | Confirms aggregate manual pass and closure approval; no per-scenario output or screenshot supplied |

Do not attach production data, credentials, or tokens.

## 10. Handoff to Final Report

```text
Required scenarios: 5
PASS: 5   FAIL: 0   BLOCKED: 0   NOT RUN: 0
Current valid evidence set: HVR-EVD-001 / HVR-RUN-001
Evidence baseline status: Partial detail; user-confirmed aggregate pass
```

This HVR records the human verifier's reported result without manufacturing per-scenario
observations or artifacts.
