# Project Closure Report Standard Template
## PCR — 项目收口报告标准母版
## Version: v1.0.0 Frozen
## 上游基线：Project Closure Workflow Extension v1.0.0 Frozen | PVR v1.0.0 Frozen | SRS v1.0.0 | DDD v1.0.0 | TDD v1.0.0 | CC v1.0.0 | IHR v1.0.0 | ATR v1.0.0 | HVR v1.0.0 | FR v1.0.0
## 创建日期：2026-09-04

---

## 0. Document Governance

### 0.1 定位
本文件是 Agent Coding Workflow 的 **Project Closure 层标准母版**，定义 **Project Closure Report（PCR）** 的结构与规则。
PCR = **Project Closure Assessment Report**。

### 0.2 服从关系
PCR 严格服从已冻结的 **Project Closure Workflow Extension v1.0.0** 与 **PVR v1.0.0 Frozen**。
不得因本模板而修改任何前置 Frozen 母版。

### 0.3 核心边界（必须遵守）
- PCR 是 **Report**（汇总/Assessment），不是 Record（事实/证据）。
- PCR 的职责是：基于 PVR 提供的项目级 Verification Evidence，对项目是否满足 Closure 条件作出判定。
- PCR **不做** Verification Evidence 的重新采集（属 PVR）。
- PCR **不决定** Release / Merge（属 Project Final Review / Human Review）。
- PCR **不调和** SRS / DDD / TDD 之间的冲突（冲突须回上游基线修订）。
- PCR **不创建**新的 Evidence Record 文档。
- PCR **不增加**新的 Workflow Stage。
- PCR **不重新解释** Coding Closure（继承 FR 的 Closure Status）。

### 0.4 两级 Closure 不变量
1. **All Coding FRs SATISFIED does not imply Project Closure.**
2. **Project Closure applies only to the Final Project Baseline.**

### 0.5 ID 约定
| 类型 | 格式 | 示例 |
|------|------|------|
| PCR 文档 | `PCR-YYYYMMDD-NNN` | PCR-20260904-001 |
| Closure Gap | `PCR-GAP-NNN` | PCR-GAP-001 |
| Residual Risk | `PCR-RISK-NNN` | PCR-RISK-001 |

---

## 1. Metadata

| 字段 | 值 |
|------|------|
| PCR ID | `{PCR-YYYYMMDD-NNN}` |
| Project Name | `{项目名称}` |
| PCR Version | `v1.0.0 Frozen` |
| Status | `{Draft / Under Review / Approved / Rejected}` |
| Author | `{作者}` |
| Created Date | `{创建日期}` |
| Last Updated | `{最后更新日期}` |
| Upstream PVR | `{PVR-ID, e.g., PVR-20260904-001}` |

---

## 2. Final Project Baselines（必须与 PVR 一致）

### 2.1 Final Project Authority Baseline（最终验什么）
| Authority | Final Version |
|-----------|---------------|
| SRS | `{v?.?}` |
| DDD（如适用） | `{v?.?}` |
| TDD | `{v?.?}` |

### 2.2 Final Project Code Baseline（验的是哪版代码）
| 字段 | 值 |
|------|------|
| Repository | `{仓库地址}` |
| Branch | `{分支}` |
| Commit / Revision | `{提交哈希}` |
| Build / Module Version | `{构建版本}` |
| Verification Environment | `{环境描述}` |

---

## 3. Authority Baseline Consistency Check

*§2 定义"What is the baseline"；本节检查"Is the baseline internally consistent"。*

| Check | Result | Evidence / Notes |
|-------|--------|-------------------|
| SRS version matches PVR Final Authority Baseline | `{Yes / No}` | |
| DDD version matches PVR Final Authority Baseline | `{Yes / No / N/A}` | |
| TDD version matches PVR Final Authority Baseline | `{Yes / No}` | |
| Authority chain (SRS→DDD→TDD) contains unresolved conflict | `{Yes / No}` | 若有冲突，必须退回上游修订，PCR 不得自行调和 |
| Authority changed after final verification | `{Yes / No}` | |
| Impact Analysis completed if changed | `{Yes / No / N/A}` | |

---

## 4. Project Closure Matrix

*PCR 核心评估矩阵。Project Closure Status 必须由本矩阵中所有 Mandatory / Applicable Obligation 的 Assessment 推导得出。*

| Closure Obligation | Authority / Source | Applicability | Evidence Source (PVR) | Assessment | Blocking Issue | Notes |
|-------------------|-------------------|---------------|-----------------------|------------|----------------|-------|
| Final Authority Baseline Valid | §2.1 | Required | PVR §2.1 | `{SATISFIED/NOT SATISFIED/BLOCKED/N/A}` | `{PCR-GAP-NNN or —}` | |
| Final Code Baseline Valid | §2.2 | Required | PVR §2.2 | `{...}` | | |
| SRS Normative Coverage (ROLE/FR/BR/CFG/NFR) | SRS + PVR §4 | Required | PVR Coverage Matrix | `{...}` | | |
| Coding Closure Completeness | Applicable CC/FR | Required | FRs (inherited) | `{...}` | | |
| Final Regression Assessment | TDD / PVR §5 | Applicable | PVR §5, §6 | `{...}` | | |
| E2E / UAT | SRS / PVR §7,§8 | Applicable | PVR §7, §8 | `{...}` | | |
| Cross-feature Integration | SRS / PVR §9 | Applicable | PVR §9 | `{...}` | | |
| DDD/TDD Coverage | DDD/TDD / PVR §10 | Applicable | PVR §10 | `{...}` | | |
| Permission Verification | SRS/TDD / PVR §11 | Applicable | PVR §11 | `{...}` | | |
| Upgrade / Migration | TDD / PVR §12 | N/A | PVR §12 | `N/A` | | |
| Current Valid Evidence Set | PVR §15 | Required | PVR §15 | `{...}` | | |

**Assessment 取值**：`SATISFIED / NOT SATISFIED / BLOCKED / N/A`

---

## 5. Coding FR 状态汇总

*PCR 继承 FR 已形成的 Closure Status，不得重新解释或重新判定 Coding Closure。*

| CC ID | FR ID | FR Closure Status | Baseline | Applicable to Final Project? | Notes |
|-------|-------|-------------------|----------|------------------------------|-------|
| `{CC-001}` | `{FR-001}` | `{SATISFIED / NOT SATISFIED / BLOCKED}` | `{baseline}` | `{Yes / No}` | |
| `{CC-002}` | `{FR-002}` | `{SATISFIED}` | `{baseline}` | `{Yes / No}` | |

**汇总**：
- Total CC: `{N}`
- Total FR: `{N}`
- SATISFIED: `{N}`
- NOT SATISFIED: `{N}`
- BLOCKED: `{N}`

> **注意**：All Coding FRs SATISFIED does not imply Project Closure. 仍需评估 §4 Closure Matrix 中的项目级义务。

## 6. PVR 状态汇总

*基于上游 PVR 的 Coverage Matrix 与 Snapshot（PVR §3, §4）。*

| 指标 | 值 |
|------|------|
| Total Requirements (纳入 Closure 的 normative) | `{N}` |
| MAPPED | `{N}` |
| PARTIALLY MAPPED | `{N}` |
| UNMAPPED | `{N}` |
| VERIFIED | `{N}` |
| NOT VERIFIED | `{N}` |
| EVIDENCE MISSING | `{N}` |
| Open Findings | `{N}` |
| Verification Evidence Complete | `{Yes / No}` |

**关键问题**：
- 是否存在 UNMAPPED Requirement？`{Yes / No}` → 若有，列出：`{FR-xxx, ...}`
- 是否存在 PARTIALLY MAPPED Requirement？`{Yes / No}` → 若有，列出：`{FR-xxx, ...}`
- 是否存在 EVIDENCE MISSING？`{Yes / No}` → 若有，列出：`{FR-xxx, ...}`
- 是否存在 Open Findings？`{Yes / No}` → 若有，列出：`{PVR-FIND-NNN, ...}`

> **NOT VERIFIED 语义**：NOT VERIFIED 继承 PVR Verification Status，表示当前不存在足以支持 VERIFIED 的有效验证结论。PCR **不得**将 NOT VERIFIED 自动解释为验证 FAIL。若 Evidence 明确证明 Mandatory Obligation 失败 → NOT SATISFIED；若缺证据无法判断 → BLOCKED。

---

## 7. Coverage Gaps 评估

基于 PVR 事实与上游 Authority，识别并评估所有 Coverage Gaps。

| Gap ID | Type | Source | Related Obligation | Description | Severity | Closure Impact | Human Judgment Required | Required Action |
|--------|------|--------|-------------------|-------------|----------|---------------|------------------------|-----------------|
| `PCR-GAP-001` | `{UNMAPPED / PARTIALLY MAPPED / NOT VERIFIED / EVIDENCE MISSING / CONFLICT}` | `{PVR / FR / SRS}` | `{FR-xxx / BR-xxx}` | `{描述}` | `{Critical / Major / Minor}` | `{Blocking / Non-Blocking / Undetermined}` | `{Yes / No}` | `{补充验证 / 修订上游 / 接受风险}` |

**Gap Type 说明**：
- **UNMAPPED**：Requirement 适用实现义务未进入任何 CC。
- **PARTIALLY MAPPED**：已进入 CC，但仍有适用实现义务未被承载。
- **NOT VERIFIED**：继承 PVR，无有效验证结论。
- **EVIDENCE MISSING**：应验证但无有效 Evidence。
- **CONFLICT**：SRS/DDD/TDD 之间矛盾，需上游修订。

**Closure Impact（与 Severity 解耦）**：
- **Blocking**：违反 Mandatory Closure Obligation。
- **Non-Blocking**：不违反 Mandatory Closure Obligation。
- **Undetermined**：当前 Authority / Evidence 不足以判断 → PCR 整体状态应为 BLOCKED。

> **原则**：Severity 只做辅助信息，Closure Impact 由 Authority Obligation 是否被破坏决定。

---

## 8. Project Closure Determination

### 8.1 三态定义（认识论区分）

| 状态 | 定义 |
|------|------|
| **SATISFIED** | 所有 Mandatory / Applicable Closure Obligation 的 Assessment 均为 SATISFIED；无 Blocking Gap；Current Valid Evidence Set 完整。我们知道且满足。 |
| **NOT SATISFIED** | 存在 Assessment = NOT SATISFIED（Evidence 明确证明 Mandatory Obligation 不满足）；或存在 Blocking Gap 且已确认违反。我们知道且不满足。 |
| **BLOCKED** | 存在 Assessment = BLOCKED（缺证据/UNMAPPED/PARTIALLY MAPPED/EVIDENCE MISSING/冲突等无法可靠判断）；或存在 Undetermined Gap。我们现在无法可靠判断。 |

**没有第四条路**：不存在 Conditional Pass / Exception Approval / Mostly Satisfied / Human Waiver。

### 8.2 判定依据（示例映射）

| 情况 | PCR Closure Status |
|------|-------------------|
| 所有 Closure Matrix 条目 = SATISFIED | SATISFIED |
| Final Regression FAIL 且违反 Mandatory Obligation | NOT SATISFIED |
| Final Regression FAIL 但经评估 Closure Impact = Non-Blocking | SATISFIED（记录为 Non-Blocking Open Item） |
| UNMAPPED / PARTIALLY MAPPED / EVIDENCE MISSING | BLOCKED |
| Authority Conflict 未解决 | BLOCKED |
| Baseline 不确定 | BLOCKED |

> **关于 Regression 失败**：不得通过"例外批准"将 FAIL 变为 SATISFIED。Failure 必须被分析：若违反 Mandatory → NOT SATISFIED；若不违反 → Non-Blocking，SATISFIED 仍可成立但须记录。

### 8.3 Non-Blocking Open Items

当 Project Closure = SATISFIED 时，仍允许存在经正式评估为 **Non-Blocking** 的：
- Known Limitations
- Deferred Items
- Residual Risks
- Follow-up Actions

这些事项**不得**违反任何 Mandatory Project Closure Obligation。

| Item | Source | Why Non-Blocking | Follow-up | Owner | Due Date |
|------|--------|-----------------|-----------|-------|----------|
| `{描述}` | `{PVR-FIND-NNN / PCR-RISK-NNN}` | `{评估理由}` | `{后续动作}` | `{责任人}` | `{日期}` |

> **核心**：SATISFIED 不是"带条件满足"；而是 Mandatory Obligations 已满足，同时可以存在非阻塞风险。

---

## 9. Residual Risks

| Risk ID | Description | Likelihood | Impact | Mitigation |
|---------|-------------|------------|--------|------------|
| `PCR-RISK-001` | `{风险描述}` | `{High / Medium / Low}` | `{High / Medium / Low}` | `{缓解措施}` |

---

## 10. Handoff to Project Final Review

PCR 向 Project Final Review 输出以下信息，供 Human Authority 作出 Release Decision。

| 项目 | 值 |
|------|------|
| Final Authority Baseline | `{版本集合}` |
| Final Code Baseline | `{Commit / Build}` |
| Closure Status | `{SATISFIED / NOT SATISFIED / BLOCKED}` |
| Closure Matrix Summary | `{§4 摘要}` |
| Summary of Gaps | `{关键 Gap 摘要}` |
| Non-Blocking Open Items | `{§8.3 摘要}` |
| Open Findings | `{PVR-FIND 列表}` |
| Residual Risks | `{PCR-RISK 列表}` |

**禁止输出**：
- Ready to Release（属 Project Final Review）
- Ready to Merge（属 Human Review / Coding 层）

---

## 11. Traceability

Business Requirements (前置输入)
        ↓
SRS → DDD(optional) → TDD  ← Authority Chain (Project Closure 直接依据)
        ↓
CC → IHR / ATR / HVR → FR  ← Coding Closure (FR Status 被 PCR 继承)
        ↓
Final Project Authority Baseline + Final Project Code Baseline
        ↓
PVR  ← Project Verification Evidence Record
        ↓
PCR  ← Project Closure Assessment Report (本文件)
        ↓
Project Final Review  ← Human Authority Gate
        ↓
Release Decision

---

## Appendix A — Status / ID Definitions

### A.1 ID 格式汇总
| 类型 | 格式 |
|------|------|
| PCR 文档 | `PCR-YYYYMMDD-NNN` |
| Closure Gap | `PCR-GAP-NNN` |
| Residual Risk | `PCR-RISK-NNN` |

### A.2 Closure Status（三态，无例外）
- **SATISFIED**：所有 Mandatory/Applicable Obligation 已满足，我们知道且满足。
- **NOT SATISFIED**：存在 Mandatory Obligation 被 Evidence 证明未满足，我们知道且不满足。
- **BLOCKED**：无法可靠判断，缺证据或存在冲突。

### A.3 Closure Impact（与 Severity 解耦）
- **Blocking**：违反 Mandatory Closure Obligation。
- **Non-Blocking**：不违反 Mandatory Closure Obligation。
- **Undetermined**：不足以判断 → PCR = BLOCKED。

### A.4 Gap Type
`UNMAPPED / PARTIALLY MAPPED / NOT VERIFIED / EVIDENCE MISSING / CONFLICT`

---

## Appendix B — Version History

| 版本 | 日期 | 状态 | 关键变更 |
|------|------|------|---------|
| v0.1 | 2026-09-04 | Draft | 初稿：PCR 结构、Closure 判定、Gap 评估、Handoff |
| v0.2 | 2026-09-04 | RC | P1×5 + P2×4（删除 PARTIALLY SATISFIED；Severity 与 Closure Impact 解耦；重写三态认识论定义；删除 Closure Waiver；条件接受改为 Non-Blocking Open Items；新增 Closure Matrix；§3 改为 Consistency Check；NOT VERIFIED 继承 PVR；Self-Check 改空） |
| v1.0.0 | 2026-09-04 | Frozen | 评审通过，正式冻结。无新增变更。后续缺陷走 v1.0.1。 |

---

## Template Self-Check

- [ ] 是否明确引用上游 PVR？
- [ ] 是否记录 Final Authority Baseline 与 Final Code Baseline（§2）？
- [ ] 是否完成 Authority Baseline Consistency Check（§3）？
- [ ] 是否完成 Project Closure Matrix（§4）？
- [ ] 是否汇总 Coding FR 状态并继承 FR Closure Status（§5）？
- [ ] 是否汇总 PVR Coverage Matrix 结果（§6）？
- [ ] 是否识别并评估所有 Coverage Gaps，Closure Impact 与 Severity 解耦（§7）？
- [ ] 是否给出 Project Closure Determination（三态，无例外）（§8）？
- [ ] 是否列出 Residual Risks（§9）？
- [ ] 是否完成 Handoff to Project Final Review（§10）？
- [ ] 是否避免在 PCR 中决定 Release？
- [ ] 是否避免调和 SRS/DDD/TDD 冲突？
- [ ] 是否避免重新采集 Verification Evidence（属 PVR）？
- [ ] 是否避免增加新的 Workflow Stage？
- [ ] 是否避免重新解释 Coding Closure？