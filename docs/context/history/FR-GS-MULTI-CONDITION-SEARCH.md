# FR — CC-015 Multi-Condition Search

## 0. Document Governance

This Final Report assesses closure evidence for CC-015 v0.5. It does not change the Coding
Contract and does not approve merge or release.

## 1. Closure Metadata

| Field | Value |
|---|---|
| Intent ID | `CC-015` |
| FR ID | `FR-GS-MULTI-CONDITION-SEARCH.md` |
| FR Version | v0.1 |
| CC Version | CC-015 v0.5 AMENDED / APPROVED |
| IHR Reference | [IHR-GS-MULTI-CONDITION-SEARCH.md](./IHR-GS-MULTI-CONDITION-SEARCH.md) |
| ATR Reference | [ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) |
| HVR Reference | User-confirmed HVR recorded in ATR-RUN-013 and ATR E-018 |
| Module | `wd_global_search` |
| Current Implementation Baseline | `0e43bff` |
| Prepared By | Copilot assistant |
| Assessment Date | 2026-10-14 |

## 2. Final Coding Contract Baseline

| Source | Version | Relevance |
|---|---|---|
| [CC-015](../intent/CC-015_multi_condition_search.md) | v0.5 AMENDED / APPROVED | Closure authority, including the DEC-027 TEST-041 waiver |
| SRS | Global Search v1.5 FROZEN | Business semantics |
| DDD | N/A | No DDD-specific obligation added by CC-015 |
| TDD | Global Search v0.4 FROZEN | Technical design and guardrails referenced by CC-015 |

## 3. Executive Closure Summary

| Field | Value |
|---|---|
| Closure Status | **SATISFIED** |
| Current Code Baseline | `0e43bff` |
| CC-CHANGE | 7 required / 7 satisfied |
| CC-PRESERVE | 12 required / 12 satisfied for the CC-015 regression scope |
| Applicable CC Guardrails | All applicable guardrails satisfied |
| Automated Verification | **SATISFIED** |
| Human Verification | **SATISFIED** |
| Unauthorized Deviation | None |
| Open Blocking Issues | 0 |
| Evidence Baseline Consistency | Valid |

## 4. Coding Contract Closure Matrix

| Contract Obligation | Source | Evidence (IHR/ATR/HVR) | Status | Notes |
|---|---|---|---|---|
| Bounded deterministic multi-token parsing and internal CQO boundary | CC-015 §§3.1, 4–7 | IHR-002/018; ATR-RUN-026/028 | SATISFIED | Public SearchRequest and route remain unchanged |
| Authorized Contains-on-text token AND execution with single-token compatibility | CC-015 §§3.1, 8–10, 12 | IHR-002/020; ATR-RUN-028; ATR-RUN-012/016 | SATISFIED | ORM fixtures cover cross-field matching and same-root-record AND |
| Structured conditions use complete Published field paths and allowed operators | CC-015 §§3.1, 8, 10 | IHR-020; ATR-RUN-028 | SATISFIED | Invalid Published field/operator/path cases fail closed |
| Condition combination, Refinement precedence, collection semantics, Count and cursor identity | CC-015 §§3.1, 9, 13 | IHR-011/014/020; ATR-RUN-019/022/024/028 | SATISFIED | Existing Resource scope and Result Identity behavior retained |
| Current-user permission, relation-hop authorization, multi-company and Record Rule boundaries | CC-015 §§3.1, 10, 12 | IHR-020; ATR-RUN-028 | SATISFIED | Portal, user/company isolation and cross-user cursor cases use Odoo TransactionCase |
| Safe Query Understanding, error and observability behavior | CC-015 §§3.1, 11, 14 | IHR-017/020/024; ATR-RUN-025/028 | SATISFIED | No claim beyond the recorded allowlist and audit-event assertions |
| Required CC tests and applicable regression verification | CC-015 §§17–18, 20 | ATR §4/§6; ATR-RUN-028/029/030 | SATISFIED | 42 required IDs PASS; TEST-041 remains SKIPPED under approved DEC-027 |
| Preserve CC-002, CC-003, CC-005, CC-007, CC-008, CC-009, CC-012, CC-013, CC-014, CC-014-1, CC-014-2, and TD-001 | CC-015 §18 | ATR §6; ATR-RUN-005/015/019/022/024/025/028/030 | SATISFIED | CC-009 evidence is scoped to this CC's regression obligation, not full CC-009 acceptance |
| Required human search verification | CC-015 §20 | ATR-RUN-013; ATR E-005/E-018; IHR-007 | SATISFIED | User confirmed manual verification and approved CC-015 closure; scope is not expanded beyond recorded scenarios |
| No prohibited architecture, permission bypass, schema migration, or unauthorized upstream change | CC-015 §§3.2, 12, 16, 19 | IHR §2/§6; ATR §8 | SATISFIED | No unauthorized deviation or unresolved stop condition is recorded |

## 5. Implementation Closure Assessment

IHR-001~026 record the implementation, approved v0.5 amendment, targeted ORM coverage,
runtime refinement checks, and final baseline. The implementation is committed as `0e43bff`;
the verification evidence was collected against the same working-tree code before that commit,
and no runtime code changed afterward.

| CC-015 implementation area | IHR Evidence | Assessment |
|---|---|---|
| CQO, deterministic request boundary, adapters and execution | IHR-002/018 | SATISFIED |
| Searchable field authorization, relation paths, Count and cursor preservation | IHR-002/020 | SATISFIED |
| State mapping and fail-closed dimension validation | IHR-011~014 | SATISFIED |
| Date/state disclosure-group presentation | IHR-021/022 | SATISFIED |
| Test registration, ORM/permission contract fixtures and audit-event coverage | IHR-008/020/024 | SATISFIED |
| Approved performance-test scope amendment and evidence baseline | IHR-023/026 | SATISFIED |

## 6. Preservation & Guardrail Assessment

### 6.1 Preservation

| CC-PRESERVE source | Evidence | Status | Scope note |
|---|---|---|---|
| CC-002 | ATR §6; RUN-005/007/019/024 | SATISFIED | Request shape, paging, cursor, Count and errors retained |
| CC-003 | ATR §6; RUN-005/028 | SATISFIED | Current-user, company, field/relation and Record Rule cases |
| CC-005 | ATR §6; RUN-007/019/022/029 | SATISFIED | Raw Query/Refinement separation and UI interaction |
| CC-007 | ATR §6; RUN-005/007/015 | SATISFIED | Aggregation/error semantics tested at core/API unit layers; no live infrastructure failure injection is claimed |
| CC-008 | ATR §6; RUN-025/028 | SATISFIED | Log allowlist and publish audit-event uniqueness assertion |
| CC-009 | ATR §6; RUN-014/030 | SATISFIED | CC-015 locale/timezone/date regression scope only; full CC-009 acceptance is not claimed |
| CC-012 | ATR §6; RUN-007/015/019 | SATISFIED | Resource selection, scope and facet-count behavior |
| CC-013 | ATR §6; RUN-014/024 | SATISFIED | Configured Action route and record identity preserved |
| CC-014 | ATR §6; RUN-007 | SATISFIED | Existing Card rendering retained |
| CC-014-1 | ATR §6; RUN-007 | SATISFIED | Existing relation/One2many rendering retained |
| CC-014-2 | ATR §6; RUN-010/028 | SATISFIED | Published full paths, operators and collection semantics |
| TD-001 | ATR §6; RUN-005/026 | SATISFIED | Request length, condition count, nesting and relation-depth limits |

### 6.2 Applicable CC Guardrails

| CC guardrail | Evidence | Status |
|---|---|---|
| Current-user Odoo ORM permissions; no `sudo()`, superuser business context or cross-user authorization cache | IHR-020; ATR-RUN-028 | SATISFIED |
| Fail closed for invalid syntax, unpublished fields/configuration, permission boundaries and unsupported execution fields | IHR-010/012/018/020; ATR-RUN-020/026/028 | SATISFIED |
| No direct database access, external search dependency, LLM/vector search, new route, or public CQO envelope | IHR §5; ATR §8 | SATISFIED |
| No unapproved SRS/TDD/CC semantic change; TEST-041 waiver recorded in CC-015 v0.5 / DEC-027 | IHR-023; CC-015 v0.5 | SATISFIED |

## 7. Automated Verification Assessment

- All 43 CC15 test IDs have explicit states: 42 PASS, 1 SKIPPED, 0 FAIL, 0 BLOCKED, and 0 NOT RUN.
- CC15-TEST-041 is intentionally **SKIPPED**, not PASS or N/A, under the user-approved CC-015 v0.5 / DEC-027 amendment. Its waiver applies only to this closure; no concurrency performance baseline or performance-compliance claim is made.
- The remaining required CC15 tests pass. ATR-RUN-028 reports 77/77 Odoo module tests, including the 14 ORM/permission/configuration/Unicode contract tests and the publish audit-event assertion. Focused harnesses and static checks are separately recorded in ATR.
- RUN-029 validates the date/state disclosure interaction; RUN-030 verifies the service-side locale/timezone boundary and date refinement against client-supplied context fields.
- Mock/fake-model tests are treated only as unit evidence. ORM, ACL, Record Rule, Count and request cases are separately represented by TransactionCase or authorized runtime evidence; no unsupported live fault-injection claim is made.
- ATR records no flaky test risk. The failed/blocked exploratory attempts remain in the historical run record and are not counted as PASS.

**Automated Verification: SATISFIED for the amended CC-015 v0.5 test scope.**

## 8. Human Verification Assessment

Human verification is required by the CC closure process. ATR-RUN-013 records the user's
confirmation of the specified `001 chair` search results and preserved single-token behavior.
The user reaffirmed “人工验证通过，批准关闭 CC-15” on 2026-10-14 at 09:49 +08:00 (ATR E-018).
The confirmation is human-authored; automated Playwright runs are not represented as human
verification. The assessment is limited to the scenarios documented in ATR-RUN-013.

**Human Verification: SATISFIED.**

## 9. Deviation & Stop Condition Assessment

| Assessment | Result |
|---|---|
| Unauthorized deviation | None reported |
| Approved amendment | CC-015 v0.5 / DEC-027; user-approved TEST-041 execution waiver |
| Triggered unresolved stop condition | None |
| Evidence refreshed for amended baseline | Yes; RUN-028/029/030 are recorded against the committed implementation baseline |

The amendment is part of the approved Coding Contract baseline, not an unapproved implementation
deviation. The skipped test remains explicitly visible.

## 10. Open Issues / Findings / Evidence Gaps

| ID | Source | Description | Closure Impact | Human Judgment Required | Basis |
|---|---|---|---|---|---|
| CC15-TEST-041 | CC-015 v0.5 / DEC-027; ATR §4/§8 | No valid P50/P95/P99 concurrency baseline was collected; execution is waived for this implementation | Non-Blocking | No | The amended §20 excludes execution for this closure while retaining SKIPPED; future performance acceptance remains separate |
| CC-009 full acceptance | ATR §6; IHR-025 | This report verifies only the CC-015 locale/timezone/date regression boundary, not the entire CC-009 HVR matrix | Non-Blocking | No | CC-015 §18 requires preservation of relevant behavior, not closure of the independent CC-009 contract |

No missing evidence remains for a mandatory CC-015 v0.5 closure obligation.

## 11. Evidence Baseline Consistency

| Evidence Source | Baseline | Valid for Current Code? | Basis |
|---|---|---|---|
| IHR | `0e43bff` | Yes | IHR-026 records the implementation commit and evidence alignment |
| ATR | `0e43bff` | Yes | Tested working-tree code was committed unchanged; later changes are documentation-only |
| Human verification | 8091 running the same tested workspace implementation, captured by `0e43bff` | Yes | User confirmation predates the commit but refers to the unchanged runtime code; no later runtime code change |

## 12. Done Criteria Assessment

| CC-015 §20 Done Criterion | Evidence | Status | Gap |
|---|---|---|---|
| Internal CQO and adapter boundary documented/tested; external request unchanged | IHR-002/018/020; ATR-RUN-026/028 | SATISFIED | — |
| Multi-token syntax, bounds, authorized Contains expansion, token AND and rejection implemented | IHR-002/020; ATR-RUN-028 | SATISFIED | — |
| Structured conditions use full Published paths and preserve operator compatibility | IHR-020; ATR-RUN-028 | SATISFIED | — |
| Same-/different-dimension composition, Refinement precedence and `collection_match` retained | IHR-011/014/020; ATR-RUN-019/022/028 | SATISFIED | — |
| Relation Path, field/hop authorization, multi-company and fail-closed tests pass | IHR-020; ATR-RUN-028 | SATISFIED | — |
| Query Understanding is authorized and does not disclose internal paths | IHR-020; ATR-RUN-028 | SATISFIED | — |
| Count matches authorized predicates, Resource scope, identity and paging | IHR-020; ATR-RUN-024/028 | SATISFIED | — |
| Published version/operator configuration verified from the approved snapshot | IHR-001; CC-015 §2.3; ATR-RUN-028 | SATISFIED | — |
| TEST-001~040, TEST-042/043 and applicable regressions pass; TEST-041 retains approved SKIPPED state | ATR §3/§4/§6; RUN-028; DEC-027 | SATISFIED | No performance baseline is claimed |
| CC-002/003/005/007/008/009/012/013/014/014-1/014-2 and TD-001 regression requirements pass | ATR §6; RUN-005/015/019/022/024/025/028/030 | SATISFIED | CC-009 status is limited to the CC-015 regression scope |
| IHR, ATR and required HVR evidence complete | IHR-026; ATR-RUN-013/E-018; this FR | SATISFIED | — |
| No prohibited dependency, permission bypass, official Odoo edit or direct database shortcut | IHR §5/§6; ATR §8 | SATISFIED | — |

## 13. Final Closure Determination

**Final Closure Status: SATISFIED**

Basis:

- All mandatory CC-CHANGE obligations have implementation evidence and are satisfied.
- Required CC-PRESERVE boundaries are satisfied for the CC-015 regression scope.
- Applicable CC guardrails have evidence and are satisfied.
- The amended CC test contract has valid automated evidence: 42 PASS and the explicitly
  authorized TEST-041 SKIPPED state, with no FAIL, BLOCKED, or NOT RUN items.
- Required human verification is recorded from the user and remains valid for the committed
  implementation baseline.
- No unauthorized deviation or unresolved stop condition exists.
- All CC-015 §20 Done Criteria are satisfied under the approved v0.5 amendment.

This determination means CC-015 has sufficient evidence for closure. It does **not** constitute
Merge or Release approval.

## 14. Handoff to Human Review

```text
Closure Assessment Complete: Yes
CC-015 Closure Status: SATISFIED
Human Review Required: Yes (for any separate merge/release decision)
Blocking Items: 0
Non-Blocking Known Items: TEST-041 performance baseline deferred by approved DEC-027; full CC-009 acceptance is outside this CC-015 closure
Merge / Release Approved: No
```

## Appendix A — Evidence Reference Index

| Evidence Type | Reference | Current / Valid | Purpose |
|---|---|---|---|
| CC | [CC-015 v0.5](../intent/CC-015_multi_condition_search.md) | Approved | Contract authority and DEC-027 waiver |
| IHR | [IHR-GS-MULTI-CONDITION-SEARCH.md](./IHR-GS-MULTI-CONDITION-SEARCH.md) | Yes | Implementation and baseline record |
| ATR | [ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) | Yes | Automated and runtime evidence |
| Human HVR | ATR-RUN-013; ATR E-018 | Yes | User-confirmed required search scenarios and closure approval |

## Appendix B — FR Version History

| Version | Date | Closure Status | Reason |
|---|---|---|---|
| v0.1 | 2026-10-14 | SATISFIED | Assessed CC-015 v0.5 evidence, approved TEST-041 waiver, and committed implementation baseline |
