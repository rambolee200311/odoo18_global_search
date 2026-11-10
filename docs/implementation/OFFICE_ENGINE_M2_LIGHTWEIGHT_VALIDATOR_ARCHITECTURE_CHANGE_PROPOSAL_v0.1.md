# Office Engine M2 — Lightweight Validator Architecture Change Proposal

**Version:** v0.1  
**Status:** DRAFT — FOR OWNER REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION  
**Date:** 2026-11-08  
**Scope:** Versioned architecture change proposal only. This document does not amend or supersede frozen SRS, TDD, Implementation Plan, CC-M2-CB-03 v0.2, or accepted CB-02.

## 1. Purpose and decision boundary

The owner’s proposed principle is: local software performs deterministic, low-complexity safety work; the LLM performs complex Office editing; a human judges business correctness and makes the final business decision. This proposal identifies the smallest contract and lifecycle changes needed to adopt that principle without rewriting or deleting the already implemented CB-03 validator.

No production code, test, database, service, Provider, or frozen baseline was changed for this proposal. The proposed future behavior has not been tested.

## 2. Current evidence baseline

### 2.1 Frozen contract and TDD semantics

Frozen TDD V2.0.2 currently assigns the local Validator more than technical file safety:

- §6.1 and §6.2 describe bounded workbook parsing and checks for values/types, formulas, styles, supported structure, target scope, and non-target changes.
- §6.3 defines `VERIFIED` to require file safety/integrity **and** declared structured effects matching independent readback, with changes inside the applicable plan/confirmation and capability policy. `PARTIALLY_VERIFIED` cannot become current or be normally delivered; `FAILED` rejects the candidate.
- §4.1–4.2 describe pre-edit plans and risk confirmation. §6.3/§8.1 allow a `VERIFIED` candidate to become current and then produce Preview; §6.4 separates artifact and delivery state.

Therefore, dropping routine full-workbook diff/precise Effect checking while preserving the existing meaning of `VERIFIED` would be a contract contradiction. A ZIP/SHA/parse-only check must not be reported as satisfying the current TDD’s Effect-verification claim.

### 2.2 Current CB-03 and CB-02 implementation

`mymodules/office_engine_m2/services/candidate_validator.py` currently reads the parent and candidate through the caller’s ORM environment, checks Session/Candidate/Parent/Revision/attachment identity and actual SHA-256 bytes, passes the structured `expected_effect` to `office_verify`, and registers the typed CB-02 `ValidationReceipt`. It does not itself promote a candidate.

`mymodules/office_engine_m2/services/workbook_version_service.py` defines `ValidationReceipt` with candidate ID/output SHA, policy version, report ID/hash, result, Session/Proposal/Document revisions, parent/input SHA, and `effect_digest`. `record_validation_receipt()` binds these to the candidate and rereads the attachment bytes. `accept_verified_candidate()` rechecks the stored proof, bytes, current revisions and parent under the Session lock; only `VERIFIED` can advance. `PARTIALLY_VERIFIED`, `FAILED`, and `REJECTED` cannot advance. For ordinary edit candidates, this method does not itself require a post-preview human business-acceptance receipt; the current typed `ConfirmationReceipt` path is specifically enforced for restore candidates.

The current Candidate policy version is `office_verify.candidate.xlsx.v1`. Existing `effect_digest` is a binding to the candidate’s declared effect object; it does not, by itself, prove that the business result is correct.

### 2.3 Existing CB-03 evidence

CB-03 v0.2 implementation evidence is recorded in [IHR-M2-CB-03.md](IHR-M2-CB-03.md), [ATR-M2-CB-03.md](ATR-M2-CB-03.md), and [the evidence index](evidence/CB-M2-CB-03/README.md). The current technical disposition is `READY FOR FINAL ACCEPTANCE — CB-03 technical implementation scope only`, not `Final Accepted`. This proposal does not revoke or reinterpret that historical implementation evidence.

## 3. Proposed responsibility boundary

| Responsibility | Accountable layer | Boundary |
|---|---|---|
| XLSX/container and OOXML basic validity; malformed package detection | Local Validator | Deterministic format/integrity checks only; a readable package is not proof of business correctness or complete feature fidelity. |
| ZIP/XML safety, file and expanded-size limits, bounded parsing and execution time | Local Validator/worker | Preserve and reuse existing `office_verify` resource controls. Human or model confirmation cannot waive these limits. |
| Current-user ORM ACL, Record Rules, attachment ownership and company/Thread/Session access | Odoo services | Use current ORM environment and existing authorization checks. No `sudo`, SQL, or user-supplied trust flags. |
| Candidate, parent, Session/Document revision, attachment bytes and SHA-256 binding | CB-02 Version Service | Remains the version authority. Receipt registration does not accept/promote the candidate. |
| Sorting, filtering, insertion/deletion, formula/style edits and other complex spreadsheet work | LLM-controlled Provider environment | Produces an actual candidate file. Model narrative is not file or business-result evidence. No model-generated code runs in the Odoo process. |
| Business result correctness and whether the edited workbook meets the user’s goal | Human user | Review the actual candidate workbook, not only an LLM summary; decide accept, continue editing, or abandon. |
| Promotion/current version, rollback and delivery | Odoo/CB-02/CB-06 | Promote only after technical gates pass and the required human decision is bound to the candidate; enforce private attachment access and lineage. |

The local Validator reports technical facts and risk facts. It does not decide that a non-empty cell, header, formula, or other business content must not be changed. Those changes are not automatically `FAILED` merely because old content existed. If the operation violates file safety, ACL, integrity, resource limits, or another non-overridable technical constraint, it remains blocked regardless of user approval.

## 4. Minimum proposed receipt and result semantics

### 4.1 Keep the existing typed Receipt shape where possible

Do not create a second persisted receipt model or a general Excel policy DSL. Preserve the CB-02 typed `ValidationReceipt` and its candidate/session/revision/SHA binding. Keep `effect_digest` as an opaque digest binding the candidate to the intent/plan/authorization context; stop treating it as evidence that the effect was independently proven.

The report and `validator_policy_version` must make the claim being made explicit. A future lightweight policy should use a new policy version rather than reinterpreting historical `office_verify.candidate.xlsx.v1` receipts. Its report can state which deterministic checks ran and which business/feature checks were not performed. No code or schema decision is made here.

### 4.2 Narrow meaning proposed for the result labels

The following is a proposed TDD change, not current behavior:

| Result | Proposed meaning | Promotion behavior |
|---|---|---|
| `VERIFIED` | Minimum technical trust checks passed: supported file type/package, safe bounded read, required OOXML/XLSX integrity, current-user authorization and exact version/attachment/SHA/revision binding. It says nothing about whether the business edit is correct or whether natural-language intent was fully met. | Eligible for human review only; not sufficient by itself to advance Current. |
| `PARTIALLY_VERIFIED` | The workbook is readable, but at least one required technical property cannot be established under the active policy. It is not a business-quality score. | Not Current and not a normal deliverable under current TDD. Whether a clearly isolated diagnostic candidate is ever shown remains a separate owner policy. |
| `FAILED` | Corruption, prohibited/unsafe package content, ACL/ownership failure, hash/version/revision mismatch, resource-limit failure, or another required technical check failed. | Reject/block; never bypass with user confirmation. |

Risk facts (for example, “existing content will be overwritten”, if deterministically observable) remain separate from `Validation Result`. The Confirmation Gate remains a separate authority. This proposal does not make confirmation automatic and does not request confirmation for every edit.

### 4.3 Expected Effect and claim discipline

Expected Effect should remain a small structured description of intent/authorization scope where needed (target or condition, allowed change class/range, and digest binding), not a local editing language. The lightweight Validator does not claim to prove all individual cell changes against it. Where exact semantic assertions are absent, the report must explicitly say the business effect was not verified and must not claim complete semantic verification. Model-reported success is descriptive only.

The future policy may stop running full-workbook cell diff, formula dependency analysis, exhaustive style/structure comparison, and automated business-correctness assertions on every edit. These existing checks remain in the v1 implementation and tests until a separately reviewed, versioned policy rollout establishes how old candidates and receipts are handled.

## 5. Proposed human-review and version lifecycle

The key necessary change is the order of preview and promotion:

```text
accepted Vn
  → LLM edits a copy and returns candidate bytes
  → local technical Validator checks format/safety/ACL/bindings/resources
  → candidate is exposed as a private, non-current review preview
  → human opens/reviews the actual workbook and accepts, requests another edit, or abandons
  → on explicit acceptance, CB-02 rechecks candidate SHA, parent, revisions and technical receipt, then promotes V(n+1)
  → CB-06 Finalize/delivery uses exactly that accepted SHA
```

- Failed or stale candidates never replace the last-valid/current version.
- A “continue editing” decision uses the reviewed candidate as the next input only after the relevant acceptance/version rule is met; a rejected candidate is not silently replayed or made current.
- A human approval must be bound to the exact candidate version, candidate SHA-256, parent/current version, relevant Session/Document revision, and the declared intent/effect digest. If any bound item changes, approval is stale.
- Human review is a business decision, not a waiver for a failed technical check.
- Current CB-02 only accepts a technically `VERIFIED` candidate, but ordinary edit acceptance currently has no required post-preview approval receipt. To enforce the proposed lifecycle, CB-04 must be the sole production caller after explicit user acceptance and the trusted acceptance evidence must be bound to the candidate. Whether the existing `ConfirmationReceipt`/`confirmation_receipt_id` can be safely reused or the CB-02 acceptance interface needs a narrow versioned amendment is an owner decision; this proposal does not alter it.

## 6. Minimum impact inventory

| Artifact/contract | Disposition | Minimum required change if approved |
|---|---|---|
| Frozen SRS `SRS_office_engine_m2_ai_mapping_v1.1.0.md` and its V1.0 baseline | `MODIFY` through a new controlled version; do not edit frozen files | Add/clarify that after initial fill, LLM-controlled editing operates on the current workbook, while a human decides business acceptance; local Odoo retains technical/security/version authority. Existing SRS centers M2 on Proposal/M1 rendering and does not define this human-reviewed open workbook lifecycle. Plan V2.0.1 §0.2 requires versioned SRS change before affected implementation. |
| Frozen TDD V2.0.2 | `MODIFY` through a new version | Update §2 roles; §4 confirmation vs post-edit business acceptance; §5 state/order; §6.1–6.3 technical-only validation claims and statuses; §6.4 Preview/delivery; §8.1/8.2 interfaces/outcomes; §12 rollback. Explicitly state human review does not prove all natural-language requirements. |
| Frozen Implementation Plan V2.0.1 | `MODIFY` through a new version | Re-scope CB-03 as light technical validation; insert the non-current review preview and human acceptance handoff into CB-04/CB-06; adjust evidence/tests and acceptance conditions. Preserve CB-01/02 and M1. |
| Frozen CC-M2-CB-03 v0.2 | `KEEP` as historical contract; future version required | A versioned replacement/amendment must remove routine full diff/precise Effect as default obligations and define policy migration. Do not declare the v0.2 implementation noncompliant retroactively. |
| Accepted CB-02 contract/service | `KEEP` as current authority; likely narrow interface review | Preserve current receipt/attachment/revision/hash checks and atomic pointer update. Decide whether promotion requires a typed human-acceptance binding; if yes, issue a versioned CB-02 contract amendment rather than adding an unreviewed bypass. |
| CB-04 contract | `MODIFY` before freeze/implementation | Own human review decision, confirmation binding, stale approval rejection, outcome text and sole trusted call to promotion. Also plan migration from the existing multiple legacy external tools to the target `office` tool; the single-tool architecture is not yet implemented. |
| CB-06 contract | `MODIFY` before freeze/implementation | Define private preview of a technically checked but non-current candidate; acceptance then promotion; Finalize/delivery only for the exact accepted SHA; preserve attachment ACL and retry behavior. |
| Existing `candidate_validator.py`, `office_verify`, CB-02 version service and tests | `KEEP` now; future versioned implementation after approvals | Retain v1 code, receipts and test evidence. Add an explicitly selected new policy path only after contracts are approved; do not silently change interpretation of existing receipt policy versions. |
| M1 Mapping/RenderBridge and Provider Adapter | `KEEP` | No change proposed. |

## 7. Migration, compatibility, and rollback boundary

- Preserve historical CB-03 v0.2 results and the `office_verify.candidate.xlsx.v1` receipt meaning. A new policy version applies only to newly created candidates after the approved rollout point; historical receipts are not relabeled.
- Keep existing detailed verification code/tests during the first rollout. Removing or disabling v1 checks requires later comparative evidence and an explicit versioned contract decision.
- **Close the new entry path:** stop creating/routing candidates under the lightweight policy; retain current/last-valid versions, attachments, hashes and existing receipts; leave pending candidates non-current and require revalidation under an explicitly selected policy before reuse.
- **True rollback:** restore the prior accepted code path/policy only after checking candidates already processed by the new policy. Do not rewrite old receipts, downgrade accepted versions, or silently repoint Current. Any version restoration must use the existing CB-02 recovery path with fresh validation and fresh scoped confirmation.
- Avoid destructive schema migration. If a later implementation finds a new persistent field unavoidable for a candidate preview or human approval binding, stop and submit a separate contract change before migration.

## 8. Proposed evidence and acceptance tests (not executed)

Future implementation evidence should distinguish deterministic technical checks, human business review, and delivery. Minimum tests should include:

1. Valid synthetic XLSX, supported package, byte/hash/version bindings pass; corrupted ZIP, invalid OOXML, unsafe/unsupported package, wrong MIME, size/expanded-size/XML/cell/time limit fail closed.
2. ACL, Record Rule, company, attachment owner, cross-Session, stale parent/revision and changed SHA are rejected before receipt/acceptance.
3. Technical `VERIFIED` does not assert the user’s business request was met; report and Agent outcome say business effect was not independently validated.
4. An existing non-empty cell or header edit is not automatically a technical failure. Risk/confirmation policy is represented independently.
5. A technically valid candidate remains non-current until a valid human decision bound to candidate/hash/parent/revision/effect context is supplied; rejection, stale approval, or a different candidate cannot advance it.
6. `PARTIALLY_VERIFIED`, `FAILED`, and `REJECTED` do not advance Current; human acceptance cannot override technical failure.
7. The candidate review preview is private, references exact candidate bytes, and is not mislabeled as last-valid/current. Finalize uses only the accepted SHA.
8. Retry, Provider timeout and attachment delivery failure preserve the last-valid version and do not replay or duplicate promotion.
9. Existing M1 `verify_output`, Mapping, RenderBridge, Document Request and attachment access behavior remains unchanged.
10. Legacy tools remain separately tracked until CB-04 migrates them; no claim that this proposal implements one external `office` Tool.

These are proposed tests only. The existing CB-03 evidence proves the frozen v0.2 implementation scope, not any future lightweight policy or post-edit human acceptance workflow.

## 9. Owner decisions and open gates

Only the following decisions materially change future implementation:

1. **Approve the semantic change:** may `VERIFIED` mean technical file/security/version trust only, with no Validator claim that Expected Effect/business intent was fulfilled? If not approved, the current detailed-diff TDD policy remains required.
2. **Choose the enforcement point for the required review-before-promotion:** the human review/accept step is part of the owner’s stated architecture. Decide whether CB-02 should require a typed acceptance binding (preferably reusing its existing confirmation receipt mechanism with a versioned contract amendment), or whether a CB-04-only trusted-caller gate is sufficient. The current CB-02 service does not enforce post-preview human acceptance for ordinary edits.
3. **Approve the versioned SRS path:** does this architecture change proceed through a new SRS version before implementation, as required by Implementation Plan V2.0.1 §0.2? The previous CB-03 synthetic/local exception is not assumed to authorize this wider workflow change.
4. **Define `PARTIALLY_VERIFIED` use:** retain its existing non-current/non-delivery rule (recommended for v1) or separately approve a diagnostic-only display policy. It must not be used as a substitute for a successful technical check.

Production external-file processing, retention/deletion and browser/runtime gates remain open according to their existing decisions; this proposal does not close them.

## 10. Disposition

This proposal preserves the frozen SRS/TDD/Implementation Plan/CC history, accepted CB-02 authority, CB-03 v0.2 implementation and M1 path. It identifies a necessary TDD lifecycle/meaning change and the smallest affected downstream contracts. No implementation, testing, Provider call, service operation, module upgrade, database change, or Git operation was performed to produce this proposal.

**Status: DRAFT — FOR OWNER REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION.**
