# Project Closure Workflow Extension
## 组织级标准 — v1.0.0
## 状态：Frozen
## 上游基线：SRS v1.0.0 | DDD v1.0.0 | TDD v1.0.0 | CC v1.0.0 | IHR v1.0.0 | ATR v1.0.0 | HVR v1.0.0 | FR v1.0.0
## 冻结日期：2026-09-04

---

## 0. 文档治理

### 0.1 定位
本文件定义 Agent Coding Workflow 的 **Project Closure Extension**，在单轮 Coding Closure（CC → IHR/ATR/HVR → FR）之上，补充项目级收口机制。

### 0.2 核心问题
单轮 Coding Contract 全部 SATISFIED，不等于整个项目完成。典型风险：
- SRS 中部分 Normative Requirement 从未进入任何 CC；
- 多轮变更后，最终集成基线未完成项目级 Regression Assessment，或适用的最终基线回归尚未执行；
- 各轮 HVR 分别验证局部场景，但端到端业务流未验证。

本文件建立两级 Closure 解决此问题。

### 0.3 涉及母版

| 层级 | 目录 | 文件 | 状态 |
|------|------|------|------|
| Designing | docs/template/Designing/ | SRS模板.md | Frozen v1.0.0 |
| | | DDD模板.md | Frozen v1.0.0 |
| | | TDD模板.md | Frozen v1.0.0 |
| Coding | docs/template/Coding/ | Coding_Contract模板.md | Frozen v1.0.0 |
| | | IHR模板.md | Frozen v1.0.0 |
| | | ATR模板.md | Frozen v1.0.0 |
| | | HVR模板.md | Frozen v1.0.0 |
| | | FR模板.md | Frozen v1.0.0 |
| Closure | docs/template/Closure/ | 
| | | PVR模板.md | Draft（占位） |
| | | PCR模板.md | Draft（占位） |

---

## 1. 两级 Closure 模型

| 层级 | Authority Chain | Evidence | Closure 文档 | Human Gate |
|------|----------------|----------|-------------|------------|
| Coding | CC | IHR + ATR + HVR | FR | Human Review → Merge / Integration Decision |
| Project | SRS → DDD（如有）→ TDD | 全部 Coding FR + PVR | PCR | Project Final Review → Release Decision |

**不变量：**
1. All Coding FRs SATISFIED does not imply Project Closure.
2. Project Closure applies only to the Final Project Authority Baseline AND the Final Project Code Baseline.

---

## 2. 顶层职责链

```
                 PROJECT AUTHORITY
                        │
          SRS → DDD(optional) → TDD
                        │
                        ▼
               Coding Iterations
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       CC-001         CC-002         CC-N
          ↓             ↓             ↓
       IHR/ATR/HVR    IHR/ATR/HVR    ...
          ↓             ↓
       FR-001         FR-002
          └─────────────┼─────────────┘
                        ▼
        Final Project Authority Baseline
        Final Project Code Baseline
                        │
                        ▼
                       PVR
             Project Verification Evidence
                        │
                        ▼
                       PCR
              Project Closure Assessment
                        │
                        ▼
              Project Final Review
                        │
                        ▼
                 Release Decision
```

---

## 3. 权威链设计

### 3.1 两级权威对照

| 层级 | Authority Chain | Evidence | Closure |
|------|----------------|----------|---------|
| Coding | CC | IHR + ATR + HVR | FR |
| Project | **SRS → DDD（如有）→ TDD** | 全部 Coding FR + PVR | PCR |

### 3.1.1 项目级权威分层职责与冲突处理
- **SRS**：决定"业务是否完成"——所有纳入 Project Closure 的 Normative Requirements 是否覆盖并满足。
- **DDD**（如有）：决定"领域语义是否保持一致"——关键领域概念、不变式、聚合边界在项目演进中是否被遵守。
- **TDD**：决定"技术设计与技术约束是否落实"——架构决策、接口契约、技术 Guardrails 是否在最终基线中正确实现。

当 SRS / DDD / TDD 之间出现矛盾时，**不得由 PCR 自行调和或充当最终总裁判**。必须回到对应上游基线修订，更新后重新进入 Project Closure 流程。

### 3.2 Final Project Authority Baseline（必填）

Project Closure 开始前，必须冻结一组 Final Project Authority Baseline：

| Authority | Final Version |
|-----------|---------------|
| SRS | v1.1 |
| DDD | v1.1 |
| TDD | v1.2 |

规则：
- PVR / PCR 的 Coverage 与 Closure 判断**均以该最终批准的 SRS / DDD（如有）/ TDD 版本为准**。
- 历史 Coding FR 可来自更早的上游版本，但**不得因此自动证明最终 Authority Baseline 已被覆盖**。
- 若最终基线**新增、修改或废止**了规范性义务，必须重新完成对应 Coverage / Impact Analysis / Verification。

**两个 Final Baseline（必须区分）：**

| 概念 | 含义 |
|------|------|
| Final Project Authority Baseline | 最终验什么（上游规范版本集合） |
| Final Project Code Baseline | 验的是哪版代码（Commit / Build） |

---

## 4. 反模式（禁止事项）

| 禁止 | 原因 |
|------|------|
| 拼各轮 FR = Project Done | FR 只证明单轮 CC，不证明 SRS 全覆盖 |
| 拼各轮 ATR = Final Regression | 分散 commit 的 PASS 不能证明最终集成基线正确 |
| 造 Project-IHR / Project-ATR / Project-HVR | 体系膨胀，用 PVR+PCR 两个文档收口即可 |
| FR 宣布 Project Closure | FR 的 Closure 对象是单份 CC |
| PCR 决定 Release | PCR 只做项目级 Closure，Release 由 Project Final Review 决定 |
| PCR 调和 SRS/DDD/TDD 冲突 | 冲突须回上游基线修订 |
| "完整回归 / 全量回归" | 应为 Final Regression Assessment，范围由风险决定 |

---

## 5. PVR（Project Verification Record）

### 5.1 定位
**PVR = 项目级综合 Verification Evidence Record。**
PVR 聚合项目级自动化验证、人工验证、E2E/UAT 与最终基线覆盖事实。**PVR 不做 Closure 判断。**

### 5.2 核心职责
- SRS Coverage Review（事实映射）
- Final Regression Assessment（适用时执行）
- End-to-End / UAT 场景验证
- Outstanding Issues 汇总

### 5.3 Project Coverage Matrix（核心表）

| Requirement | Upstream AC | Coding Contract | Coding FR | Mapping Status | Project Evidence | Verification Status |
|-------------|-------------|----------------|----------|---------------|------------------|---------------------|
| FR-001 | AC-001.1 | CC-001 | FR-001 | MAPPED | IHR-003, ATR-004 | VERIFIED |
| FR-002 | AC-002.1 | CC-001 | FR-001 | MAPPED | — | NOT VERIFIED |
| FR-028 | AC-028.1 | — | — | UNMAPPED | — | NOT VERIFIED |

**两个状态维度（不可合并）：**
- **Mapping Status**：`MAPPED / UNMAPPED / N/A` —— 该 Requirement 是否进入 CC 映射。
- **Verification Status**：`VERIFIED / NOT VERIFIED / EVIDENCE MISSING / N/A` —— 该 Requirement 是否已被最终验证。

`MAPPED` ≠ `VERIFIED`（已进入 CC ≠ 已在最终基线上验证）。

**规则**：
- PVR 可以发现 UNMAPPED / NOT VERIFIED / EVIDENCE MISSING，但**不得**输出 Project Closure 结论。Closure 判定属于 PCR。
- 追溯链：`Requirement → AC → CC → FR → PVR Evidence`

---

## 6. Project Closure 核心内容

### 6.1 Final Regression Assessment
Project Closure 必须对 Final Project Code Baseline 执行 Final Regression Assessment。

- 对于**存在可执行自动化回归能力且变更可能产生跨 CC 影响**的项目：必须在 Final Project Baseline 上执行适当范围的 **Final Baseline Regression**。
- 若**不执行**回归：必须记录明确理由、风险评估及替代验证方式。

保持原则：**强制回答，不强制答案。**（不使用"完整回归 / 全量回归"措辞）

### 6.2 SRS Normative Requirements 覆盖
全部纳入 Project Closure 的 SRS Normative Requirements 必须完成项目级追溯：
- **ROLE / FR / BR / CFG / NFR** 及其 **AC**
- 不遗漏任何规范性 Requirement Type

### 6.3 DDD/TDD Coverage Review
仅检查项目适用、规范性、且被 Final Project Baseline 承载的 DDD/TDD obligations。
- **不要求**机械覆盖所有设计说明、决策记录或非规范性内容。
- DDD：检查关键 ENT / VO / Aggregate 边界是否保持语义一致。
- TDD：检查关键架构约束、接口契约、Guardrails 是否在最终基线中落实。

---

## 7. PVR 文档结构（概要）

1. Project Metadata（**Final Project Authority Baseline + Final Project Code Baseline**）
2. Project Coverage Matrix（§5.3，Mapping + Verification 双状态）
3. DDD/TDD Coverage Summary
4. Final Regression Assessment Record
5. E2E / UAT Evidence
6. Outstanding Issues（事实列表，不做 Closure 判定）

---

## 8. PCR 文档结构（概要）

1. Project Metadata（两个 Final Baseline）
2. Authority Chain 核对（SRS → DDD → TDD，逐层版本 = Final Authority Baseline）
3. 全部 Coding FR 状态汇总
4. PVR 状态汇总（Coverage Matrix 结论）
5. Coverage Gaps 评估（基于 PVR 事实 + 上游权威）
6. Project Closure Determination（SATISFIED / NOT SATISFIED / BLOCKED）
7. Handoff to Project Final Review

---

## 9. 对现有体系的影响

- **FR 母版**：§0.1 增补——"FR 的 Closure 对象是一份 Coding Contract / Intent。一个项目包含多轮 Coding Contract 时，各轮 FR 的 SATISFIED 不自动等同于 Project Closure；项目最终验收由 PVR/PCR 负责。" **FR 不改名。**
- **IHR/ATR/HVR**：不受影响，职责边界不变。
- **SRS/DDD/TDD**：不受影响，仍是上游设计基线。

---

## 10. 单轮项目处理

单轮项目**仍应完成 Project Closure 判断**，但允许：
- 将 PVR / PCR 极简化；
- 或在组织规则允许时采用合并式 Project Closure Record。

**不得**因为只有一轮 Coding Contract 就省略 SRS 全局覆盖与最终项目级验收判断。

---

## 11. 母版起草顺序

1. workflow.md → **Frozen v1.0.0**
2. PVR 母版 → Draft → RC → Frozen
3. PCR 母版 → Draft → RC → Frozen
4. 回填占位文件，更新各母版上游引用
5. 统一打包

---

## 12. 目录约定

```
docs/template/
├── Designing/
│   ├── SRS模板.md
│   ├── DDD模板.md
│   └── TDD模板.md
├── Coding/
│   ├── Coding_Contract模板.md
│   ├── IHR模板.md
│   ├── ATR模板.md
│   ├── HVR模板.md
│   └── FR模板.md
└── Closure/
    ├── workflow.md
    ├── PVR模板.md
    └── PCR模板.md
```

---

## 13. 术语表

| 缩写 | 全称 | 层级 |
|------|------|------|
| CC | Coding Contract | Coding |
| IHR | Implementation History Record | Coding |
| ATR | Automated Test Record | Coding |
| HVR | Human Verification Record | Coding |
| FR | Final Report | Coding |
| PVR | Project Verification Record | Project |
| PCR | Project Closure Report | Project |

**Human Gate 术语：**
- Coding 层：`Human Review`（FR → Merge / Integration Decision）
- Project 层：`Project Final Review`（PCR → Release Decision）

不另设"Project Final Review 与 Human Review 两个 Gate"——二者是不同层级的 Human Authority Gate。

---

## 14. 版本历史

| 版本 | 日期 | 状态 | 关键变更 |
|------|------|------|---------|
| v0.1 | 2026-09-04 | Draft | 初稿：两级 Closure、PVR+PCR 两文档、防体系膨胀 |
| v0.2 | 2026-09-04 | RC | P1×3 + P2×4：Authority Chain、PVR 不做 Closure、Final Regression Assessment、normative coverage、单轮退化 |
| v1.0.0 | 2026-09-04 | **Frozen** | P1×1 + P2×3（见下） |

**v1.0.0 变更（相对 v0.2 RC）：**

| # | 级别 | 修改内容 |
|---|------|----------|
| 1 | **P1** | 新增 §3.2 **Final Project Authority Baseline**（与 Final Project Code Baseline 并列）；规则：最终基线新增/修改/废止义务须重新 Coverage / Impact Analysis / Verification |
| 2 | P2 | "完整回归/全量回归/Full Regression" 全文统一为 **Final Regression Assessment / Final Baseline Regression** |
| 3 | P2 | Coverage Matrix 拆为 **Mapping Status（MAPPED/UNMAPPED/N/A）+ Verification Status（VERIFIED/NOT VERIFIED/EVIDENCE MISSING/N/A）** 双维度 |
| 4 | P2 | Human Gate 术语统一：Coding = **Human Review**（→ Merge/Integration Decision）；Project = **Project Final Review**（→ Release Decision）；二者为不同层级的 Human Authority Gate，不另设第二 Gate |

冻结规则：v1.0.0 后不再迭代小版本；后续真实缺陷走 v1.0.1。