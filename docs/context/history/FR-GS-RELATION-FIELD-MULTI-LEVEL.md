# FR — CC-014-1 Relation Field Multi-Level

## 0. Document Governance

This Final Report assesses closure evidence for the frozen Coding Contract. It does not change
SRS/TDD/CC requirements and does not approve merge or release.

## 1. Closure Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-RELATION-FIELD-MULTI-LEVEL` |
| FR ID | `FR-GS-RELATION-FIELD-MULTI-LEVEL.md` |
| FR Version | v0.1 |
| CC Version | CC-014-1 v0.1 FROZEN |
| IHR Reference | [IHR-GS-RELATION-FIELD-MULTI-LEVEL.md](./IHR-GS-RELATION-FIELD-MULTI-LEVEL.md) |
| ATR Reference | [ATR-GS-RELATION-FIELD-MULTI-LEVEL.md](./ATR-GS-RELATION-FIELD-MULTI-LEVEL.md) |
| HVR Reference | [HVR-GS-RELATION-FIELD-MULTI-LEVEL.md](./HVR-GS-RELATION-FIELD-MULTI-LEVEL.md) |
| Module | `wd_global_search` |
| Current implementation baseline | `09f2629` plus the CC-014-1 working-tree changes represented by the final ATR runs |
| Prepared by | Copilot assistant |
| Assessment date | 2026-10-12 |

## 2. Final Coding Contract Baseline

| Source | Version | Relevance |
|---|---|---|
| CC | CC-014-1 v0.1 FROZEN | Closure authority |
| SRS | Global Search v1.5 FROZEN | Business semantics |
| DDD | N/A | No DDD-specific obligation was added by this CC |
| TDD | Global Search v0.4 FROZEN | Technical design and guardrails incorporated by the CC |

No SRS, TDD, implementation plan, or pre-existing CC was changed for this implementation.

## 3. Executive Closure Summary

| Field | Value |
|---|---|
| Closure Status | **SATISFIED** |
| Current code baseline | `09f2629` plus the tested CC-014-1 working tree |
| CC-CHANGE | All CC §3 In-Scope obligations satisfied |
| CC-PRESERVE | All applicable CC §16 regression boundaries satisfied |
| Applicable CC guardrails | All CC §12 security and §17 stop-condition constraints satisfied |
| Automated verification | **SATISFIED** — CC14-1-TEST-001~038 mapped PASS; final suite 59/59 |
| Human verification | **SATISFIED** — HVR-RUN-001 records explicit user-confirmed pass for all five scenarios |
| Unauthorized deviation | None reported |
| Open blocking issues | 0 |
| Evidence baseline consistency | Partial detail only; runtime baseline is unchanged since HVR-RUN-001 |

## 4. Coding Contract Closure Matrix

| Contract obligation | Source | Evidence | Status | Notes |
|---|---|---|---|---|
| Many2one / Many2many relation paths, depth/type rules, and ordinary terminal fields | CC §3~§6; §8; INV-001~006 | IHR-001~002; ATR §4 | SATISFIED | Paths are statically validated and rendered through the current user's ORM environment |
| One2many loops, scope, nesting, count/body limits, empty behavior, formatting and escaping | CC §3, §7~§11; INV-007~013, INV-018~022 | IHR-001~002; ATR §4 | SATISFIED | Automated matrix includes nested scope, empty loop, formatting and text-safety cases |
| Resource separator and explicit Apply/Published Snapshot lifecycle | CC §6, §14, §16; INV-006 | IHR-003; ATR §4; HVR-SCN-005 | SATISFIED | Separator is carried by the existing snapshot/checksum lifecycle |
| Check/Apply validation uses model metadata and does not read business records | CC §14, §17, §18; TEST-036~037 | ATR §4; `test_structure_validation_uses_model_metadata_without_business_reads`; Apply snapshot-preservation tests | SATISFIED | No arbitrary relation IDs or record queries are used for structural Check |
| Current-user access boundary, Record Rules, fail-closed behavior and safe plain text | CC §12~§13, §16; INV-014~017, INV-021~023 | IHR-002; ATR §4, §6; HVR-SCN-004 | SATISFIED | No `sudo()`, superuser environment, or direct database access was added |
| Required automated contract tests | CC §15; TEST-001~038 | ATR §3~§5; ATR-RUN-008 | SATISFIED | All 38 IDs have explicit PASS evidence |
| Applicable CC-002~CC-014 regression requirements | CC §16 | ATR §6; HVR-SCN-005 | SATISFIED | Module regression suite passed |
| Required human verification | CC §18; HVR scenarios | HVR-RUN-001 / HVR-EVD-001 | SATISFIED | User confirmed manual pass and approved closure; granular observations were not supplied |
| No prohibited architecture or upstream-contract change | CC §2~§3, §17 | IHR §2, §6 | SATISFIED | No official Odoo source, external search engine, LLM, vector search, or `/nl_search` change |

## 5. Implementation Closure Assessment

IHR-001~006 record the parser/validator, relation renderer, separator lifecycle, designer
integration, regression tests, and performance measurements. The actual change inventory is in
IHR §5. The implementation uses the existing template, Card, Resource configuration, and Search
service paths; it introduces no new search architecture.

## 6. Preservation & Guardrail Assessment

### 6.1 Preservation

| CC preservation boundary | Evidence | Status |
|---|---|---|
| CC-014 template editor, formatting, Preview and rendering behavior | ATR-RUN-008; HVR-SCN-001~003 | SATISFIED |
| CC-013 Result Card / Native Form navigation | ATR §6; HVR-SCN-005 | SATISFIED |
| CC-012 Resource selection and counts | ATR §6 | SATISFIED |
| CC-003 current-user and company access boundary | ATR §6; HVR-SCN-004 | SATISFIED |
| CC-007 failure semantics and CC-008 observability | ATR §6 | SATISFIED |
| CC-009 server locale/timezone and CC-010 published version/checksum | ATR §6; HVR-SCN-005 | SATISFIED |
| CC-002 response shape, paging and counts | ATR §6 | SATISFIED |

### 6.2 Applicable guardrails

| CC guardrail | Evidence | Status |
|---|---|---|
| CC §12: current-user ORM ACL, field access and Record Rules; fail closed | IHR §3; ATR §4; HVR-SCN-004 | SATISFIED |
| CC §17: no `sudo()`, superuser environment, direct database access, official-source edits, or prohibited search dependency | IHR §6 | SATISFIED |

No additional TDD-only obligation has been imported into this assessment.

## 7. Automated Verification Assessment

- ATR maps CC14-1-TEST-001~038 to PASS.
- ATR-RUN-008 executed 59 module tests with 0 failures and 0 errors; the descriptor and
  performance tests were discovered.
- Parser, structural validation and cold-/warm-cache relation rendering P95 measurements for
  each relation type, plus the actual Preview API endpoint P95, are below the inherited budgets:

  | Stage | Many2one | Many2many | One2many loop | Budget |
  |---|---:|---:|---:|---:|
  | Parser P95 | 0.002 ms | 0.001 ms | 0.006 ms | ≤10 ms |
  | Validation P95 | 0.010 ms | 0.005 ms | 0.015 ms | ≤100 ms |
  | Cold-cache render P95 | 2.895 ms | 0.397 ms | 3.174 ms | ≤50 ms |
  | Warm-cache render P95 | 0.837 ms | 0.152 ms | 0.898 ms | ≤50 ms |
  | Preview API P95 | 16 ms across 100 successful requests | — | — | ≤500 ms |

  See ATR-RUN-008 and ATR-RUN-009 for environment, fixture and cache-state details.
- CC-002~CC-014 regression tests passed. The Odoo upgrade emitted non-fatal skipped-deletion
  warnings for absent legacy XML IDs; no test or runtime failure resulted.
- No flaky test or unresolved automated failure is recorded.

**Automated Verification: SATISFIED.**

## 8. Human Verification Assessment

HVR-RUN-001 records the user's explicit statement that manual verification passed and approval to
close CC-014-1. The verifier is identified as Odoo Administrator (UID 1), as confirmed by the
user. All five required scenarios are recorded PASS. The user did not provide individual
scenario outputs, screenshots, or browser/device version; HVR discloses this detail limitation
without inventing observations.

The runtime implementation did not change after the reported human run; the subsequent change
was test-only performance instrumentation. The reported run therefore applies to the current
runtime code baseline.

**Human Verification: SATISFIED.**

## 9. Deviation & Stop Condition Assessment

| Assessment | Result |
|---|---|
| Unauthorized deviation | None reported |
| Frozen-contract change | None |
| Triggered unresolved stop condition | None |
| `sudo()` / superuser / direct database read | None added |
| Prohibited search architecture or endpoint | None added |
| Evidence refreshed after implementation changes | Yes; ATR-RUN-008 and the Preview API run follow the final runtime implementation |

## 10. Open Issues / Findings / Evidence Gaps

| ID | Source | Description | Closure impact | Human judgment | Basis |
|---|---|---|---|---|---|
| HVR-EVIDENCE-DETAIL | HVR-RUN-001 | Per-scenario outputs, screenshots and browser version were not supplied; user explicitly confirmed the aggregate five-scenario pass | Non-blocking detail limitation | Yes — accepted by the user's explicit closure approval | CC §18; HVR §6, §9 |
| ATR-OBS-LEGACY-XMLID | ATR-RUN-004 / RUN-008 | Odoo logged skipped deletions for absent legacy designer XML IDs during upgrade | Non-blocking | No | No runtime or test failure; unrelated legacy XML cleanup is out of scope |

There are no open blocking issues.

## 11. Evidence Baseline Consistency

| Source | Baseline | Valid for current code? | Basis |
|---|---|---|---|
| IHR | `09f2629` + CC-014-1 working tree | Yes | Describes final implementation inventory |
| ATR | `09f2629` + CC-014-1 working tree | Yes | Final module and performance tests ran after test-only instrumentation |
| HVR | `09f2629` + CC-014-1 runtime changes | Yes, with detail limitation | No runtime code changed after the user-reported run |

## 12. Done Criteria Assessment

| Done criterion | Evidence | Status | Gap |
|---|---|---|---|
| Relation path depth/type/terminal rules work | IHR §3; ATR §4 | SATISFIED | — |
| One2many nesting, scope and bounded template limits work | IHR §3; ATR §4 | SATISFIED | — |
| Separator and Published Snapshot lifecycle work | IHR-003; ATR §4; HVR-SCN-005 | SATISFIED | — |
| Metadata-only Check and Apply/Publish validation work | ATR TEST-036~037; HVR-SCN-001/005 | SATISFIED | — |
| Current-user permissions, empty handling, formatting and escaping work | ATR §4; HVR-SCN-002~004 | SATISFIED | — |
| Relation rendering performance is measured against inherited budgets | ATR-RUN-008~009 | SATISFIED | — |
| CC14-1-TEST-001~038 pass | ATR §4~§5 | SATISFIED | — |
| Applicable CC-002~CC-014 regression requirements pass | ATR §6 | SATISFIED | — |
| IHR, ATR and HVR are complete; prohibited upstream changes are absent | IHR §5~§8; ATR; HVR | SATISFIED | HVR detail limitation is disclosed in §10 |

## 13. Final Closure Determination

**Final Closure Status: SATISFIED**

All mandatory CC-014-1 implementation, preservation, security, automated test, performance, and
human-verification obligations have current evidence. The aggregate human pass was explicitly
confirmed by the identified user verifier; missing per-scenario narrative detail is disclosed and
does not change the reported PASS result. No unauthorized deviation or unresolved stop condition
remains.

This determination closes the Coding Contract only. It does not authorize merge or release.

## 14. Handoff to Human Review

```text
Closure Assessment Complete: Yes
Human Review Required: Yes
Closure Status: SATISFIED
Blocking Items: None
Non-blocking evidence detail: HVR per-scenario output/browser details not supplied
```

## Appendix A — Evidence Reference Index

| Evidence | Reference | Purpose |
|---|---|---|
| CC | [CC-014-1](../intent/CC-014-1_relation_field_multi_level.md) | Frozen closure authority |
| IHR | [IHR-GS-RELATION-FIELD-MULTI-LEVEL.md](./IHR-GS-RELATION-FIELD-MULTI-LEVEL.md) | Implementation facts |
| ATR | [ATR-GS-RELATION-FIELD-MULTI-LEVEL.md](./ATR-GS-RELATION-FIELD-MULTI-LEVEL.md) | Automated, regression and performance evidence |
| HVR | [HVR-GS-RELATION-FIELD-MULTI-LEVEL.md](./HVR-GS-RELATION-FIELD-MULTI-LEVEL.md) | User-confirmed manual verification |

## Appendix B — Version History

| Version | Date | Closure status | Reason |
|---|---|---|---|
| v0.1 | 2026-10-12 | SATISFIED | Initial assessment after user-confirmed HVR and final automated evidence |
