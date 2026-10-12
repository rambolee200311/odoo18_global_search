<!-- Skill bundle metadata
Source path: Skill-authored; structure informed by docs/implementation/IMPLEMENTATION_PLAN_global_search.md
Source version/status: v0.1; Draft
Synced: 2026-10-12
-->

# {Project / Module} Implementation Plan

## Document Information

| Item | Value |
|---|---|
| Document | `IMPLEMENTATION_PLAN_{scope}` |
| Version | `{vX.Y}` |
| Status | `Draft / Under Review / Frozen / Amendment` |
| Baseline validity | `VALID / IMPACT REVIEW REQUIRED` |
| Project / Module | `{name}` |
| Plan owner | `{name or role}` |
| Created | `{YYYY-MM-DD}` |
| Baseline date | `{YYYY-MM-DD}` |
| Approval / baseline record | `{reviewer, date, approval reference}` |

### Freeze Gate

This plan is prepared **after the applicable TDD is frozen and before the first Coding Contract (CC)**. The first CC and implementation work must not begin until the plan's review/approval status is recorded as required by the project. Do not claim approval or a Frozen status without the corresponding authorization.

The plan defines execution order, phases, dependencies, deliverables, readiness, and acceptance gates. It does not replace or revise SRS, DDD, TDD, or Technical Verification (TV) authority.

### First CC Gate Checklist

- [ ] SRS is Frozen, or an authorized applicability decision records N/A and its reason.
- [ ] DDD is Frozen when domain complexity or project policy requires it; otherwise N/A and the reason are recorded.
- [ ] Applicable TV items are closed with a result and approved disposition; no unresolved technical uncertainty blocks TDD. If no TV was needed, the reason is recorded.
- [ ] TDD is Frozen and names the same upstream baselines as this plan.
- [ ] This plan has the required review/approval and a valid baseline.
- [ ] Every plan phase maps to at least one planned CC ID and scope; every planned CC maps back to a phase.

**Gate result:** `{READY / BLOCKED}`  
**Evidence / approval reference:** `{link or record}`

## 1. Upstream Baselines

| Authority / Input | Version / ID | Status | Location |
|---|---|---|---|
| SRS | `{version}` | `{status}` | `{path}` |
| DDD | `{version or N/A}` | `{status or N/A}` | `{path or N/A}` |
| TV / Spike | `{IDs or N/A}` | `{status}` | `{path or N/A}` |
| TDD | `{version}` | `{Frozen status}` | `{path}` |
| Other approved input | `{name/version or N/A}` | `{status}` | `{path}` |

If an upstream baseline changes, assess affected phases, deliverables, acceptance criteria, and CCs. Follow that authority's change process before resuming affected work.

## 2. Objective and Scope

### 2.1 Objective

{State the deliverable and the user or business outcome.}

### 2.2 In Scope

- {Capability, module, integration, or migration}

### 2.3 Out of Scope

- {Explicit exclusions}

### 2.4 Constraints

- {Applicable SRS/TDD guardrails, version constraints, security/privacy requirements, or other approved constraints}

## 3. Readiness Prerequisites

| Prerequisite | Required state / evidence | Owner | Priority | Status |
|---|---|---|---|---|
| SRS / DDD / TDD baselines | `{approved versions}` | `{role}` | P0 | `{status}` |
| Odoo / Python / database environment | `{versions and readiness evidence}` | `{role}` | P0 | `{status}` |
| Test database and fixtures | `{isolation, data, permissions}` | `{role}` | P0 | `{status}` |
| CI and required test commands | `{commands / pipelines}` | `{role}` | P0 | `{status}` |
| External services / extensions | `{availability or N/A}` | `{role}` | `{priority}` | `{status}` |

If a P0 prerequisite is unmet, only proceed with work that does not depend on it. Do not mark the affected phase or project milestone complete.

## 4. Implementation Phases

Create one subsection per phase. Split or combine phases to fit the project, while keeping dependencies and acceptance gates explicit.

### Phase {N}: {Name}

**Objective**

{What this phase establishes.}

**Inputs and dependencies**

- `{baseline, prerequisite, or prior phase}`

**Deliverables**

- `{code, migration, configuration, documentation, or evidence}`

**Acceptance gate**

- `{observable, testable condition}`

**Verification evidence**

- `{test type, command/environment, required record, and evidence location}`

**CC mapping**

- `{planned CC ID(s) and scope; do not leave a phase unmapped at the first-CC gate}`

**Estimate / owner / risk** (optional when unknown)

- Estimate: `{basis and estimate, or TBD}`
- Owner: `{role}`
- Risk and response: `{risk → mitigation / fallback}`

## 5. Phase Order and Dependencies

```mermaid
flowchart TD
    P0[Phase 0: {name}] --> P1[Phase 1: {name}]
    P1 --> P2[Phase 2: {name}]
```

**Critical path:** `{phase sequence}`

**Parallel work and constraints:**

- `{parallelizable phases and the interface/readiness conditions that permit it}`

Parallel work does not waive dependencies or approval gates.

## 6. Milestones

| Milestone | Included phases / deliverables | Exit criteria and evidence | Target / status |
|---|---|---|---|
| M1 — `{name}` | `{items}` | `{criteria}` | `{date or TBD}` |

Use target dates only when there is a reasonable basis. Record assumptions and buffers; do not fabricate commitments.

## 7. Acceptance and Verification Matrix

| Requirement / design obligation / TV item | Plan phase | Acceptance criterion | Verification method and evidence | CC / FR | Status |
|---|---|---|---|---|---|
| `{SRS ID / TDD section / TV ID}` | `{phase}` | `{criterion}` | `{actual evidence required}` | `{IDs or TBD}` | `{status}` |

Include all applicable normative requirements and material TDD/TV obligations. Identify inapplicable items explicitly with a reason. A planned test is not evidence that it passed.

## 8. Quality and Verification Strategy

| Verification area | Applicable scope | Required evidence / gate |
|---|---|---|
| Automated / unit / ORM | `{scope}` | `{ATR/test run evidence}` |
| Permissions and security | `{scope}` | `{scenarios and evidence}` |
| Browser / E2E / human | `{scope}` | `{HVR or other evidence}` |
| Performance / capacity | `{scope}` | `{environment, data size, thresholds}` |
| Upgrade / migration / rollback | `{scope}` | `{rehearsal and evidence}` |
| Final baseline regression | `{scope}` | `{assessment and evidence}` |

Mark non-applicable areas with a reason. Preserve failed, skipped, blocked, and not-run results accurately.

## 9. Risks and Contingencies

| Risk | Probability / impact | Mitigation | Fallback / decision owner | Status |
|---|---|---|---|---|
| `{risk}` | `{rating}` | `{action}` | `{fallback / owner}` | `{status}` |

## 10. Resources and Environments

| Resource / environment | Requirement | Owner | Availability / status |
|---|---|---|---|
| `{role, database, browser, test data, service, or tool}` | `{capacity/version/access}` | `{role}` | `{status}` |

Use only known commitments. Record unknowns as open prerequisites.

## 11. Change Control

- **SRS / DDD / TDD change:** return to the owning authority, assess impact, obtain its required approval, then update this plan and affected CC mappings.
- **Plan-only sequencing or estimate change:** record the reason, affected phases, dependencies, acceptance impact, and approval/status.
- **Implementation discovery that conflicts with an upstream baseline:** stop affected work; do not resolve the conflict by silently changing this plan or a CC.

## 12. Deliverables and Project Handoff

| Deliverable | Planned phase | Acceptance evidence | Final location / status |
|---|---|---|---|
| `{code, tests, docs, migration, report, or operational item}` | `{phase}` | `{evidence}` | `{path/status}` |

At project closure, reconcile each planned phase and deliverable against its CC(s), FR(s), and PVR evidence. The plan does not replace normative requirement coverage or PCR closure assessment.

## 13. Open Decisions and Follow-up

| ID | Question / TODO | Blocking phases | Owner | Due / status |
|---|---|---|---|---|
| `{ID}` | `{item}` | `{phase(s)}` | `{role}` | `{date or TBD}` |

## 14. Traceability

### 14.1 Authority to Plan

| SRS / DDD / TDD / TV reference | Plan phase | Planned acceptance / evidence |
|---|---|---|
| `{reference}` | `{phase}` | `{evidence}` |

### 14.2 Plan to Coding Closure

| Plan phase / deliverable | CC | IHR / ATR / HVR | FR | PVR evidence |
|---|---|---|---|---|
| `{item}` | `{CC ID}` | `{record IDs}` | `{FR ID}` | `{evidence reference}` |

## 15. Change History

| Version | Date | Status | Change and reason | Affected phases / baselines |
|---|---|---|---|---|
| `{vX.Y}` | `{date}` | `{status}` | `{change}` | `{impact}` |
