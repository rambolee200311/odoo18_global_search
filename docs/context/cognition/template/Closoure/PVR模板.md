# Project Verification Record Standard Template
## PVR — 项目验证记录标准母版
## Version: v1.0.0
## 状态：Frozen
## 上游基线：Project Closure Workflow Extension v1.0.0 Frozen | SRS v1.0.0 | DDD v1.0.0 | TDD v1.0.0 | CC v1.0.0 | IHR v1.0.0 | ATR v1.0.0 | HVR v1.0.0 | FR v1.0.0
## 冻结日期：2026-09-04

---

## 0. Document Governance

### 0.1 定位
本文件是 Agent Coding Workflow 的 **Project Closure 层标准母版**，定义 Project Verification Record（PVR）的结构与规则。

### 0.2 服从关系
PVR 严格服从已冻结的 **Project Closure Workflow Extension v1.0.0**。
不得因本模板而修改任何前置 Frozen 母版（SRS / DDD / TDD / CC / IHR / ATR / HVR / FR）。

### 0.3 核心边界（必须遵守）
- PVR = **Project Verification Evidence Record**。
- PVR 记录事实与证据；**不做 Project Closure 判断**（Closure 判断属于 PCR）。
- PVR 可以发现 `FR-028 → UNMAPPED`，但**不得**自行宣布 `Project Closure = BLOCKED`。
- PVR 不决定 Merge / Release（属于 Human Review / Project Final Review）。
- PVR 不重新发明 CC / IHR / ATR / HVR / FR；不复制整个 ATR 或 HVR 母版。
- PVR 不建立 Project-IHR / Project-ATR / Project-HVR。

### 0.4 两级 Closure 不变量
1. **All Coding FRs SATISFIED does not imply Project Closure.**
2. **Project Closure applies only to the Final Project Baseline.**

### 0.5 ID 约定
| 类型 | 格式 | 示例 |
|------|------|------|
| 自动化验证运行 | `PVR-ARUN-NNN` | PVR-ARUN-001 |
| 验证场景 | `PVR-SCN-NNN` | PVR-SCN-001 |
| 人工验证运行 | `PVR-HRUN-NNN` | PVR-HRUN-001 |
| 发现/问题 | `PVR-FIND-NNN` | PVR-FIND-001 |
| 证据 | `PVR-EVD-NNN` | PVR-EVD-001 |

---

## 1. Metadata

| 字段 | 值 |
|------|------|
| PVR ID | `{PVR-YYYYMMDD-NNN}` |
| Project Name | `{项目名称}` |
| PVR Version | `v1.0.0` |
| Status | `Frozen` |
| Author | `{作者}` |
| Created Date | `{创建日期}` |
| Last Updated | `{最后更新日期}` |
| Upstream Workflow | `Project Closure Workflow Extension v1.0.0 Frozen` |

---

## 2. Final Project Baselines

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

### 2.3 Baseline 变更规则
- 历史 Coding FR / ATR / HVR 可以来自更早的代码或 Authority Baseline，但**不得因此自动证明 Final Project Baseline 已满足**。
- 若 Authority Baseline 或 Code Baseline 发生变化，必须触发 **Project Verification Impact Analysis**（§16）。

---

## 3. Current Verification Snapshot

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

---

## 4. Project Requirement Coverage Matrix

### 4.1 覆盖原则
- 覆盖所有适用于 Project Closure 的 SRS Normative Requirements：**ROLE / FR / BR / CFG / NFR** 及其 **AC**。
- 建立追溯链：`Requirement → AC → CC → FR → PVR Evidence`。
- 允许多个 Requirement / AC 由同一项目级场景或测试共同验证，不机械要求 1:1。

### 4.2 状态定义

**Mapping Status（实现义务映射状态）：**
| 状态 | 定义 |
|------|------|
| **MAPPED** | 该 Requirement 在本项目中的**全部适用实现义务**，已由一个或多个 Coding Contract 明确承载。 |
| **PARTIALLY MAPPED** | Requirement 已进入 Coding Contract，但仍存在适用实现义务未被任何 Coding Contract 承载。 |
| **UNMAPPED** | Requirement 的适用实现义务未进入任何 Coding Contract。 |
| **N/A** | 有正式依据证明该 Requirement 不适用于本项目 Closure。 |

**Verification Status（验证状态）：**
| 状态 | 定义 |
|------|------|
| **VERIFIED** | 存在对 **Final Project Authority Baseline + Final Project Code Baseline** 当前有效的 Verification Evidence。该 Evidence 可以是在 Final Baseline 上直接执行产生，也可以是经 **Project Verification Impact Analysis** 明确证明未受影响并保留的历史 Evidence。 |
| **NOT VERIFIED** | 尚未验证或验证未通过。 |
| **EVIDENCE MISSING** | 应验证但未获得有效 Evidence。 |
| **N/A** | 不适用。 |

> **核心纪律**：`MAPPED ≠ VERIFIED`（已进入 CC ≠ 已在最终基线上验证）；`Historical PASS ≠ Final Baseline PASS`。

### 4.3 Coverage Matrix 表格

| SRS Requirement | Related AC | Coding Contract(s) | Coding FR(s) | Mapping Status | Project Verification Evidence | Verification Status | Notes |
|-----------------|------------|-------------------|-------------|----------------|------------------------------|---------------------|-------|
| `{FR-001}` | `{AC-001.1}` | `{CC-001}` | `{FR-001}` | MAPPED | `{PVR-ARUN-001, PVR-HRUN-001}` | VERIFIED | |
| `{FR-002}` | `{AC-002.1}` | `{CC-001}` | `{FR-001}` | PARTIALLY MAPPED | `{PVR-EVD-003}` | NOT VERIFIED | 部分义务未在CC中 |
| `{FR-028}` | `{AC-028.1}` | — | — | UNMAPPED | — | EVIDENCE MISSING | |

---

## 5. Final Regression Assessment

### 5.1 Assessment Questions（强制回答，不强制答案）
- 是否存在可执行自动化测试？
- 多轮 CC 是否存在跨变更回归风险？
- 哪些测试必须在 Final Project Baseline 重跑？
- 是否可以保留部分历史 ATR Evidence？若保留，为什么仍然有效？
- 若不执行某类最终回归，理由是什么？替代验证方式是什么？Residual Risk 是什么？

### 5.2 Final Regression Plan / Result

| 字段 | 值 |
|------|------|
| Final Baseline Regression | `{Full / Partial / Not Executed}` |
| Historical Evidence Retained | `{Yes / No}` |
| Alternative Verification | `{Yes / No}` |
| Executed Scope | `{测试范围描述}` |
| Retained Evidence | `{引用的历史 ATR / Evidence ID}` |
| Alternative Evidence | `{替代验证 Evidence ID}` |
| Rationale | `{决策依据}` |
| Residual Risk | `{残留风险 / None}` |

> **原则**：ATR PASS @ commit A + B + C **不能**自动证明 Final Baseline @ commit D PASS。

---

## 6. Project Automated Verification Runs

记录项目级自动化验证 Run（不复制整个 ATR 母版）。

| 字段 | 值 |
|------|------|
| Run ID | `PVR-ARUN-NNN` |
| Final Code Baseline | `{Commit / Build}` |
| Environment | `{环境}` |
| Test Scope | `{测试范围}` |
| Command / Test Suite | `{命令}` |
| Started At | `{开始时间}` |
| Finished At | `{结束时间}` |
| Result | `{PASS / FAIL / SKIPPED / BLOCKED / NOT RUN}` |
| Evidence | `{PVR-EVD-NNN}` |
| Related Requirement / AC | `{需求/AC}` |
| Related historical ATR | `{ATR-RUN-NNN（如有）}` |
| Notes | `{备注}` |

**纪律**：No execution, no PASS。

---

## 7. End-to-End / Human / UAT Scenarios

本节**只定义验证场景**（What should be verified），不记录执行结果。

| 字段 | 值 |
|------|------|
| Scenario ID | `PVR-SCN-NNN` |
| Purpose | `{验证目的}` |
| Related Requirement / AC | `{关联需求}` |
| Verification Type | `{E2E / UAT / Integration / Permission / ...}` |
| Preconditions | `{前置条件}` |
| Role | `{执行角色}` |
| End-to-End Steps | `{步骤描述}` |
| Expected Result | `{预期结果}` |
| Evidence Required | `{所需证据类型}` |

---

## 8. Human Verification Runs

本节**专门记录人工验证执行结果**（What was actually executed）。继承 HVR 核心纪律：**No execution, no PASS. No observation, no PASS.**

| 字段 | 值 |
|------|------|
| Run ID | `PVR-HRUN-NNN` |
| Human Verifier | `{可识别、可审计的人类身份}` |
| Verification Type | `{UAT / E2E / Demo / ...}` |
| Final Code Baseline | `{Commit / Build}` |
| Environment | `{环境}` |
| Scenario | `{PVR-SCN-NNN}` |
| Actual Result | `{实际结果}` |
| Result | `{PASS / FAIL / SKIPPED / BLOCKED / NOT RUN}` |
| Evidence | `{PVR-EVD-NNN}` |
| Finding | `{PVR-FIND-NNN（如有）}` |
| Notes | `{备注}` |

**Agent 边界**：Agent 可以准备步骤、辅助记录、整理 Evidence；**不得**冒充 Human Verifier；**不得**自行宣布人工 UAT PASS。

---

## 9. Cross-feature Integration Verification

显式考虑跨 CC 集成场景。各轮 FR 可能 SATISFIED，但最终组合可能存在集成问题。

| 场景 | 相关 CC | 风险描述 | 验证方式 | Status | Evidence |
|------|---------|---------|---------|--------|----------|
| `{跨模块流程}` | `{CC-001, CC-003}` | `{风险}` | `{PVR-SCN-NNN}` | `{状态}` | `{PVR-EVD-NNN}` |

不另建 Integration Test Record 文档。

---

## 10. DDD / TDD Verification（按需）

### 10.1 DDD（如项目使用）
支持对关键 Domain Verification / Invariant 的最终有效性进行追溯。**No DDD means no invented DDD artifacts**——不生成 AGG/ENT/VO 占位符。

### 10.2 TDD
只验证项目最终适用的规范性技术义务、架构约束、关键 Guardrails。禁止把所有 T-xxx 机械变成 PVR Test Item。不重新设计 TDD。

---

## 11. Permission Verification（按需，Odoo 项目常见）

通过"Applicable Verification Domain"进入，非所有项目必填。

| Role | Operation | Object / View / Route | Expected | Actual | Result | Evidence |
|------|-----------|----------------------|----------|--------|--------|----------|
| `{角色}` | `{操作}` | `{对象}` | `{预期}` | `{实际}` | `{PASS/FAIL}` | `{PVR-EVD-NNN}` |

检查范围：ACL、Record Rule、business permission、button visibility、Portal access、company/owner isolation、sensitive operation。

---

## 12. Upgrade / Migration Verification（按需）

| 字段 | 值 |
|------|------|
| Required | `{Yes / No}` |
| Source Version | `{源版本}` |
| Target Version | `{目标版本}` |
| Migration Scope | `{范围}` |
| Existing Data | `{现有数据描述}` |
| Upgrade Execution | `{执行记录}` |
| Post-upgrade Verification | `{验证记录}` |
| Result | `{PASS / FAIL / BLOCKED / NOT RUN / N/A}` |
| Evidence | `{PVR-EVD-NNN}` |
| Reason (if No) | `{原因}` |

---

## 13. Project Verification Findings

| 字段 | 值 |
|------|------|
| Finding ID | `PVR-FIND-NNN` |
| Source | `{发现来源}` |
| Related Requirement / AC | `{关联需求}` |
| Description | `{描述}` |
| Severity | `{Critical / Major / Minor / Info}` |
| Status | `{Open / Investigating / Resolved / Won't Fix}` |
| Evidence | `{PVR-EVD-NNN}` |
| Owner | `{责任人}` |
| Follow-up | `{后续动作}` |
| Closure Impact Assessment Input | `{对 PCR 的潜在影响说明}` |

> PVR 记录事实，不做 Closure 判定。不充当 Bug Tracker。

---

## 14. Evidence Register

| Evidence ID | Type | Source (Run/Scenario/Finding) | Baseline Valid | Description | Location |
|-------------|------|-------------------------------|----------------|-------------|----------|
| `PVR-EVD-NNN` | `{Screenshot/Log/Video/PDF/...}` | `{PVR-ARUN-001 / PVR-HRUN-003 / ...}` | `{Authority+Code Baseline}` | `{描述}` | `{存储位置}` |

要求：Evidence 必须可追溯到 Run/Scenario/Finding；必须绑定有效 Baseline；不得只写"verified manually"；敏感信息受控；只引用已有 ATR/HVR Evidence，不复制正文。

---

## 15. Current Valid Evidence Set

由多个 Automated Run + Human Run + 历史 Coding Evidence **共同构成**，但只有对 **Final Project Authority Baseline + Final Project Code Baseline** 仍然有效的 Evidence 才能进入。

| Evidence ID | Origin | Original Baseline | Impact Analysis Result | Current Valid |
|-------------|--------|-------------------|----------------------|---------------|
| `{PVR-EVD-001}` | `{PVR-ARUN-001 / ATR-RUN-012}` | `{Commit B}` | `{未受影响，保留}` | `Yes` |
| `{PVR-EVD-002}` | `{PVR-ARUN-003}` | `{Commit D}` | `{直接执行}` | `Yes` |

**禁止**：Latest Run = Current Truth；新 Baseline 自动继承旧 PASS。

---

## 16. Project Verification Impact Analysis

触发条件：Final Code Baseline 改变 / SRS 版本改变 / DDD 版本改变 / TDD 版本改变 / PVR 执行期间修复代码 / 新 Finding 导致实现变更 / Final Regression 后又有代码变更。

| 字段 | 值 |
|------|------|
| Trigger | `{触发原因}` |
| Changed Baseline | `{变更前后}` |
| Evidence Impact | `{哪些 Evidence 失效}` |
| Retained Evidence | `{哪些可保留（附 Impact Analysis 理由）}` |
| Re-run Required | `{哪些 Automated Run 必须重跑}` |
| Re-verify Required | `{哪些 Human Scenario 必须重验}` |
| Coverage Matrix Impact | `{哪些条目需重新评估}` |

---

## 17. PVR Status

PVR **不使用** `SATISFIED / NOT SATISFIED / BLOCKED` 作为 Project Closure Status（属 PCR）。

PVR 自有状态（仅表示证据完整性）：

| 状态 | 含义 |
|------|------|
| COMPLETE | 项目级 Verification Evidence 完整，足以交给 PCR |
| INCOMPLETE | 证据不完整，存在缺失 |
| BLOCKED | 验证被阻塞，无法继续 |

或简化为单一字段：

**Verification Evidence Complete: `{Yes / No}`**

> **硬化定义**：`Verification Evidence Complete = Yes` **不要求**所有 Verification Result 为 PASS / VERIFIED。只要所有适用验证义务均已获得足够事实与证据，使 PCR 能够作出可靠 Closure Assessment，即可为 Yes。**明确的 FAIL / NOT VERIFIED 本身也是有效 Closure Evidence。** 禁止为了让 Complete = Yes 而隐瞒或篡改 FAIL。

---

## 18. PCR Handoff

PVR 最终输出清晰的 PCR Handoff：

| 项目 | 值 |
|------|------|
| Final Authority Baseline | `{版本集合}` |
| Final Code Baseline | `{Commit / Build}` |
| Requirement Coverage Summary | `{MAPPED / PARTIALLY MAPPED / UNMAPPED 计数}` |
| Unmapped Requirements | `{列表}` |
| Verification Evidence Summary | `{ARUN / HRUN / Evidence 计数}` |
| Final Regression Summary | `{§5.2 摘要}` |
| E2E / UAT Summary | `{§7/§8 摘要}` |
| Open Findings | `{PVR-FIND 列表}` |
| Evidence Gaps | `{缺失 Evidence 说明}` |
| Current Valid Evidence Set | `{§15 摘要}` |
| Verification Evidence Complete | `{Yes / No}` |

**禁止输出**：Project Closure = SATISFIED / Ready to Release / Ready to Merge / Release Approved。

---

## 19. Traceability

```
Requirement (SRS) → AC → CC → FR → PVR Coverage Matrix
                                    ↓
Final Authority Baseline + Final Code Baseline
                                    ↓
              ┌─────────────────────┼─────────────────────┐
              ↓                     ↓                     ↓
    Final Regression Assessment   E2E / UAT          Integration
              ↓                     ↓                     ↓
         PVR-ARUN              PVR-SCN → PVR-HRUN    Cross-feature
              ↓                     ↓                     ↓
         PVR-EVD ←─────────────────┴─────────────────────┘
              ↓
    Current Valid Evidence Set
              ↓
            PVR
              ↓
            PCR
```

---

## Appendix A — Status / ID Definitions

### A.1 ID 格式汇总
| 类型 | 格式 |
|------|------|
| PVR 文档 | `PVR-YYYYMMDD-NNN` |
| 自动化运行 | `PVR-ARUN-NNN` |
| 验证场景 | `PVR-SCN-NNN` |
| 人工运行 | `PVR-HRUN-NNN` |
| 发现 | `PVR-FIND-NNN` |
| 证据 | `PVR-EVD-NNN` |

### A.2 Mapping Status
- **MAPPED**：全部适用实现义务已由一个或多个 CC 明确承载。
- **PARTIALLY MAPPED**：已进入 CC，但仍有适用实现义务未被承载。
- **UNMAPPED**：未进入任何 CC。
- **N/A**：有正式依据证明不适用。

### A.3 Verification Status
- **VERIFIED**：存在对 Final Baseline 当前有效的 Evidence（直接执行或经 Impact Analysis 保留的历史 Evidence）。
- **NOT VERIFIED**：尚未验证或验证未通过。
- **EVIDENCE MISSING**：应验证但无有效 Evidence。
- **N/A**：不适用。

### A.4 Run Result
`PASS / FAIL / SKIPPED / BLOCKED / NOT RUN`

### A.5 PVR 自身状态
`COMPLETE / INCOMPLETE / BLOCKED`（或 `Verification Evidence Complete: Yes / No`）

---

## Appendix B — Version History

| 版本 | 日期 | 状态 | 关键变更 |
|------|------|------|---------|
| v0.1 | 2026-09-04 | Draft | 初稿：双 Baseline、Coverage Matrix、Final Regression、PVR 边界 |
| v0.2 | 2026-09-04 | RC | P1×2 + P2×4（见下） |
| v1.0.0 | 2026-09-04 | **Frozen** | v0.2 RC 评审通过，正式冻结 |

**v0.2 RC 变更（相对 v0.1）：**

| # | 级别 | 修改内容 |
|---|------|----------|
| 1 | **P1** | Mapping Status 增加 **PARTIALLY MAPPED**，定义为"适用实现义务覆盖"而非"碰到过 CC"；MAPPED 收紧为全部适用实现义务已被 CC 完整承载 |
| 2 | **P1** | VERIFIED 定义改为"存在对 Final Baseline 当前有效的 Evidence"，兼容经 Impact Analysis 保留的历史 Evidence，闭合逻辑 |
| 3 | P2 | §7 只定义 Scenario，§8 专门记录 Human Run（SCN = What should be verified, HRUN = What was actually executed） |
| 4 | P2 | Final Regression Decision 拆为 Final Baseline Regression / Historical Evidence Retained / Alternative Verification 三个维度，避免互斥错误 |
| 5 | P2 | 硬化 Verification Evidence Complete 定义：FAIL 本身也是有效 Closure Evidence，Complete=Yes 不要求所有 Result=PASS |
| 6 | P2 | Upgrade/Migration Result 枚举增加 BLOCKED / NOT RUN，防止"没跑"被塞进 N/A |

冻结规则：v1.0.0 后不再迭代小版本；后续真实缺陷走 v1.0.1。

---

## Template Self-Check

- [x] 是否明确 Final Authority Baseline？
- [x] 是否明确 Final Code Baseline？
- [x] 是否完成全部适用 SRS normative requirement mapping（ROLE/FR/BR/CFG/NFR + AC）？
- [x] 是否区分 MAPPED / PARTIALLY MAPPED / UNMAPPED？
- [x] 是否区分 MAPPED 与 VERIFIED？
- [x] 是否完成 Final Regression Assessment？
- [x] 是否记录 Final Baseline Automated Verification（适用时）？
- [x] 是否完成 E2E / Human / UAT（适用时）？
- [x] 是否完成 Cross-feature Integration Verification（适用时）？
- [x] 是否评估 Permission Verification（适用时）？
- [x] 是否评估 Migration / Upgrade（适用时）？
- [x] 是否所有 Evidence 对 Final Baseline 有效？
- [x] 是否完成 Impact Analysis（发生 Baseline 变化时）？
- [x] 是否存在 UNMAPPED Requirement？
- [x] 是否存在 EVIDENCE MISSING？
- [x] 是否存在未解决 Finding？
- [x] 是否形成 Current Valid Evidence Set？
- [x] 是否完成 PCR Handoff？
- [x] 是否避免在 PVR 中做 Project Closure 判断？
- [x] 是否避免在 PVR 中做 Release / Merge 决策？