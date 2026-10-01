# Human Verification Record 标准母版
## 组织级标准 — v1.0.0
## 状态：Frozen
## 上游基线：SRS v1.0.0 | DDD v1.0.0（按需）| TDD v1.0.0 | CC v1.0.0 | IHR v1.0.0 | ATR v1.0.0
## 冻结日期：2026-09-04

---

## 0. 文档治理

### 0.1 定位
Human Verification Record（HVR）是 Agent Coding Workflow 中 Execution & Evidence 阶段的**人工验证证据记录**。
它记录：本次 Coding Contract 要求的人工验证实际验证了什么、由谁验证、在什么环境和代码基线上验证、实际观察到什么结果。

### 0.2 核心原则
- HVR 不得重新发明 SRS。
- HVR 不得重新发明 DDD。
- HVR 不得重新发明 TDD。
- HVR 不得重新定义 Coding Contract。
- HVR 不得自行创造新的 Acceptance Criteria。

### 0.3 职责边界
- CC 定义哪些事项必须人工验证。
- IHR 记录代码实际改了什么。
- ATR 记录自动化测试执行证据。
- **HVR 记录人工实际执行和观察证据。**
- FR 汇总所有证据判断 Contract 是否闭环。
- Human Review 决定 Merge / Release。

### 0.4 编号体系

| 前缀 | 用途 | 示例 |
|------|------|------|
| HVR-SCN | 验证场景定义 | HVR-SCN-001 |
| HVR-RUN | 验证执行事件 | HVR-RUN-001 |
| HVR-FIND | 验证发现/问题 | HVR-FIND-001 |
| HVR-EVD | 证据引用 | HVR-EVD-001 |

场景与执行分离：一个 Scenario 可被多次执行，产生多个 Run。Finding 和 Evidence 为真实 Evidence Record 对象，须使用上述正式编号。

### 0.5 证据纪律（最高纪律）
> **No execution, no PASS. No observation, no PASS.**

禁止以下行为构成正式 PASS：
- "看了一下没问题"
- 只打开页面但没有执行场景
- Agent 推测或开发者说"应该没问题"
- 自动化测试 PASS 自动等同于人工 PASS
- 代码 Review 看起来正确就推断人工 PASS

每个正式 Human Verification Scenario 必须回答：验证什么、谁验证、在哪里验证、基于什么代码、做了什么、预期是什么、实际看到什么、结果是什么。

### 0.6 Agent 与 Human 边界
- Agent 可以准备 HVR 骨架、生成 Coverage Matrix、整理 Evidence Reference。
- **Agent 不得冒充 Human Verifier。**
- 只有真实人类执行或明确观察并确认，才能形成正式 HVR PASS。
- 工具辅助时必须记录 `Execution Assistance` + 真实验证者。
- **Human Verifier 必须记录为可识别的人类验证主体**（例如姓名、组织内账号或其他可审计身份），不得仅填写 `User / Human / Business / Reviewer` 等无法识别具体验证主体的泛化角色。

### 0.7 可变快照与仅追加历史（继承 IHR/ATR 治理模型）
- **Current Snapshot（可更新）**：§3 当前状态、§4 Coverage Matrix、§8 Findings 当前状态、§10 Handoff Summary。
- **Historical Record（仅追加）**：§6 Verification Run History、附录 A Verification Baseline Change History。
- Issue Register 创建后不得删除；允许更新 Status/Follow-up，但原始 Finding、首次发现 Run 和原因不得被覆盖。

---

## 1. Verification Metadata

| 字段 | 值 |
|------|-----|
| Intent ID | `{intent_id}` |
| CC Version | `{版本}` |
| IHR Reference | `{IHR 文档或 Entry}` |
| ATR Reference | `{ATR 文档}` |
| Module | `{模块}` |
| Environment | `{环境描述}` |
| Environment Type | `{Normal / Staging / Production}` |
| Application Version | `{版本}` |
| Initial Code Baseline / Commit | `{首次开始人工验证时的 baseline}` |
| Database / Dataset | `{按需}` |
| Browser / Device / PDA | `{按需}` |
| Verification Start | `{时间}` |
| Verification End | `{时间}` |

注意：当前生效的代码基线统一由 §3 维护；每次执行时的基线由 §6 每条 Run 自带。Verifier 记录在 Run，不同 Run 可能由不同人执行。

---

## 2. Human Verification Contract Baseline

只引用，不复制：

| 来源 | ID | 标题 | 相关性 |
|------|-----|------|--------|
| CC Human Verification Requirement | #{n} | `{描述}` | 必须验证 |
| SRS AC | AC-xxx | `{描述}` | 验证依据 |
| DDD DV / INV | DV-xxx / INV-xxx | `{描述}` | 按需 |
| TDD UI / SEC / API | T-xxx | `{描述}` | 按需 |
| CC-CHANGE | CC-CHANGE-xxx | `{描述}` | 验证实现 |
| CC-PRESERVE | CC-PRESERVE-xxx | `{描述}` | 回归验证 |

---

## 3. Current Human Verification Status

### 3.1 快速摘要（可更新）

| 字段 | 值 |
|------|-----|
| Human Verification Required | `{Yes / No}` |
| Required Scenarios | `{n}` |
| PASS | `{n}` |
| FAIL | `{n}` |
| BLOCKED | `{n}` |
| NOT RUN | `{n}` |
| Current Code Baseline | `{commit}` |
| Current Valid Evidence Set | `{HVR-RUN-xxx, ...}` |
| Evidence Baseline Status | `{Complete / Partial / Incomplete}` |

### 3.2 极简路径（Human Verification Required = No）
当 CC 声明 `Human Verification Required: No` 时，HVR 允许极简记录：
- Human Verification Required: No
- CC Reference: `{CC 版本/章节}`
- Reason: `{原因}`
- Status: N/A
不生成完整模板实例。

---

## 4. Human Verification Coverage Matrix

| Verification Requirement | Scenario | Upstream | Current Valid Evidence | Result | Baseline Validity |
|--------------------------|----------|----------|----------------------|--------|-------------------|
| CC Human Verification #1 | HVR-SCN-001 | AC-UI-001 / CC-CHANGE-002 | HVR-RUN-002 | PASS | Current |
| CC Human Verification #2 | HVR-SCN-002 | CC-PRESERVE-003 | HVR-RUN-002 | PASS | Retained—unaffected |
| CC Human Verification #3 | HVR-SCN-003 | AC-PORTAL-004 | — | NOT RUN | Invalidated |

规则：每个 Required Scenario 必须有显式状态。NOT RUN ≠ 不适用。Current Valid Evidence 指当前代码基线下可用于证明该 Scenario 的有效人工验证证据，不等同于时间上最新的 Run。

---

## 5. Verification Scenarios

| 字段 | 含义 |
|------|------|
| Scenario ID | HVR-SCN-001 |
| Title | 简短场景名称 |
| Purpose | 为什么必须人工验证 |
| Upstream Reference | AC / CC-CHANGE / CC-PRESERVE / TDD |
| Preconditions | 必要前置条件 |
| Role | 使用什么业务角色 |
| Verification Steps | 最小必要操作步骤 |
| Expected Behavior | 应观察到什么（来自上游冻结语义） |
| Evidence Required | Screenshot / PDF / Observation / etc. |

---

## 6. Verification Run History（Append-only）

### Run 结构

| 字段 | 含义 |
|------|------|
| Run ID | HVR-RUN-001 |
| Timestamp | 执行时间 |
| Human Verifier | 可识别的人类验证主体 |
| Verification Type | Developer Check / Functional / Business / UAT |
| Run Code Baseline | 本次执行对应的 Commit / Build |
| Environment | 环境 |
| Scenarios | 本 Run 覆盖的 HVR-SCN |
| Execution Assistance | None / Agent / Tool |
| Result Summary | PASS / FAIL / PARTIAL / BLOCKED |
| Evidence | HVR-EVD 引用 |
| Follow-up | IHR / ATR / HVR-FIND |

### 每个 Scenario Result 至少包含：
- Scenario: `{HVR-SCN-xxx}`
- Expected Behavior: `{来自上游}`
- Actual Observation: `{人真实观察}`
- Result: `{PASS / FAIL / BLOCKED / NOT RUN}`
- Evidence: `{HVR-EVD-xxx}`
- Finding: `{HVR-FIND-xxx，如有}`

规则：Run Result Summary ≠ Scenario Result。一次 Run 中有 FAIL 的 Scenario，Run Result 不得写成 PASS。

---

## 7. Human Regression Verification

仅处理 CC 声明需要人工验证的 CC-PRESERVE 项。

| CC-PRESERVE | Scenario | Run | Result | Evidence |
|-------------|----------|-----|--------|----------|
| CC-PRESERVE-002 | HVR-SCN-004 | HVR-RUN-002 | PASS | HVR-EVD-xxx |

自动化回归属于 ATR，不在此处。

---

## 8. Findings / Issues

| ID | Scenario | Run | Finding | Severity | Status | Follow-up |
|----|----------|-----|---------|----------|--------|-----------|
| HVR-FIND-001 | HVR-SCN-003 | HVR-RUN-001 | `{描述}` | `{High/Medium/Low}` | `{Open/Resolved/Deferred/Escalated}` | `{IHR/ATR/新Run}` |

Status 允许更新，但原始 Finding 不得删除或覆盖。

---

## 9. Evidence Inventory

| Evidence ID | Type | Scenario | Run | Location / Reference | Sensitive Data |
|-------------|------|----------|-----|----------------------|----------------|
| HVR-EVD-001 | Screenshot | HVR-SCN-001 | HVR-RUN-002 | `{路径/URL}` | `{Yes/No, 如 Yes 已脱敏}` |

原则：Evidence should be sufficient, not ceremonial。不强制每场景截图。

---

## 10. Handoff to Final Report

只提供事实摘要：
- Required Scenarios: `{n}`
- PASS: `{n}` / FAIL: `{n}` / BLOCKED: `{n}` / NOT RUN: `{n}`
- Current Valid Evidence Set: `{...}`
- Evidence Baseline Status: `{...}`
- Open Findings: `{n}`

**不得写**："项目验收完成 / 可以上线 / 建议 Merge / 建议 Release"。

---

## 附录 A — Verification Baseline Change History（Append-only）

| 变更时间 | Initial Baseline | 旧 Current Baseline | 新 Current Baseline | Impact Analysis | 失效 Evidence (Invalidated) | 保留 Evidence (Retained) | 原因 |
|----------|-----------------|---------------------|---------------------|-----------------|---------------------------|------------------------|------|
| `{时间}` | `{commit}` | `{commit}` | `{commit}` | `{受影响项}` | `{旧 RUN}` | `{旧 RUN}` | `{理由}` |

---

## 附录 B — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|---------|------|
| v0.1 | 2026-09-04 | 初稿 Draft | Draft |
| v1.0.0 | 2026-09-04 | 确立 Evidence Record 定位、SCN/RUN 分离、Current Valid Evidence Set、Impact Analysis、Agent 边界、四编号体系、可审计 Verifier | **Frozen** |

---

## 附录 C — Agent & Human Maintenance Rules

1. HVR 在 CC 确定 Human Verification Requirement 后创建骨架。
2. 根据 CC 生成 Coverage Matrix。
3. 等待 Human Verifier 提供实际结果。
4. 每次正式验证追加 HVR-RUN（append-only），自带 Run Code Baseline。
5. FAIL 不删除，记录 HVR-FIND。
6. 返回 Implementation 修复时引用 IHR；自动化重测引用 ATR。
7. 修复后重新验证，追加新 HVR-RUN。
8. 代码变更后执行 Human Verification Impact Analysis，更新附录 A。
9. 当前 Summary 可更新（§3）；Run History 仅追加（§6）。
10. 最终生成 Evidence Inventory + Handoff。
11. Agent 不得冒充 Human Verifier，不得自行填写虚假 PASS。

---

# 第二部分：HVR 模板设计说明

## 1. 为什么 HVR 是 Evidence Record 而不是 Test Design / UAT Plan
HVR 只读上游验证要求（CC Human Verification Requirement / SRS AC），记录实际执行和观察。它不自行创造 Acceptance Criteria，不重新设计测试用例。UAT 只是 Human Verification 的一种 Type（Functional / Business / UAT），不另造平行文档体系。

## 2. 为什么 Human Verification 必须来自 CC
如果实施后才发现必须增加人工验证，应回 CC 修订 → 重新冻结 → 执行 HVR。禁止 HVR 自行扩大验证 Scope。验证发现设计问题 ≠ 验证者获得设计授权。

## 3. 为什么 Scenario 与 Run 必须分离
场景定义是稳定的验证要求（HVR-SCN），执行事件是特定时间、特定代码基线上的实际验证（HVR-RUN）。一个 Scenario 可被多次执行（如修复后重验）。混用会导致历史无法追溯。

## 4. 为什么 Expected / Actual 必须分离
Expected 来自上游冻结语义，Actual 必须是人真实观察。FR 才能判断两者是否一致。禁止"按钮正常"这类合并描述。

## 5. 为什么必须绑定 Code Baseline（三层模型）
人验证的是特定版本的代码。基线分三层：§1 Initial Baseline（创建起点）→ §6 Run Code Baseline（每条 Run 自带）→ §3 Current Code Baseline（可更新快照）。旧 PASS 不能自动继承给新代码。代码变更后必须做 Human Verification Impact Analysis：受影响场景旧证据失效重验；明确不影响的可保留但须记录理由。

## 6. 如何处理旧 Human PASS
与 ATR 一致：新 Code Baseline 不得自动继承旧 PASS。必须判断影响。Current Valid Evidence Set 由多个有效 Run 共同组成，不是单一 Latest Run。

## 7. 如何处理 FAIL → Fix → Retest
HVR 记录人观察到的问题 → IHR 记录代码怎么修 → ATR 记录自动化重测 → HVR 记录人工复验。HVR 不写详细 Implementation Fix。

## 8. 如何处理 Human Regression
仅处理 CC 声明需要人工验证的 CC-PRESERVE 项。自动化回归归 ATR。

## 9. 如何处理 UAT
UAT 是 Human Verification 的一种，在 Run 中标记 Verification Type = UAT，记录真实业务 Owner / Key User 作为 Verifier（须为可识别身份）。不制造独立 UAT 文档。

## 10. Agent 与 Human 的职责边界
Agent 可准备骨架、步骤、整理结果。Agent 不得冒充 Human Verifier。Human Verifier 必须是可识别、可审计的人类主体。工具辅助须声明 Execution Assistance。最终观察必须由 Human 确认。

## 11. Evidence 应如何控制
充分但不仪式化。截图/PDF/Video 按需，由场景风险和可复核性决定。不强制每场景截图。

## 12. 如何保护敏感数据
优先测试数据；必要时脱敏；不得写入 secret/token/password；引用受控位置。

## 13. 如何与 ATR / FR 分工
ATR 证明机器可验证行为；HVR 证明要求人工观察的行为；FR 读取 CC+IHR+ATR+HVR 判断闭环。HVR 不宣布 Done/Merge/Release。

## 14. 如何支持简单任务和大型项目
简单任务（Human Verification Required = No）→ 极简 N/A Record。简单 UI Fix → 1-2 个 Scenario，1-2 个 Run。大型 Portal/PDA → 多个 Scenario/Run。证据复杂度跟随实际风险，不跟随模板大小。

---

# 第三部分：HVR 自查清单（Handoff Gate）

- [ ] CC Human Verification Requirement 已正确引用
- [ ] Required Scenario 全部映射到 Coverage Matrix
- [ ] 每个 Scenario 都有显式状态（PASS/FAIL/BLOCKED/NOT RUN）
- [ ] PASS 来自真实 Human Observation，非推断
- [ ] Human Verifier 身份可识别、可审计，Agent 未冒充
- [ ] Expected 与 Actual 分离记录
- [ ] FAIL 未隐藏，BLOCKED 有原因
- [ ] NOT RUN 清晰可见
- [ ] Findings 保留（HVR-FIND），Resolved 不删除原始记录
- [ ] Fix 后如有必要已重新验证（新 HVR-RUN）
- [ ] Current Valid Evidence Set 正确（非简单取 Latest Run）
- [ ] 当前 Code Baseline（§3）与 Evidence 有效性一致
- [ ] 旧人工 PASS 未自动继承给受影响的新代码
- [ ] Regression 只覆盖 CC 要求的人工作用项
- [ ] Evidence 足够但不过度（非仪式化）
- [ ] 敏感信息未无必要暴露
- [ ] Production Verification 如发生已特殊标记
- [ ] 未把 ATR 内容复制进 HVR
- [ ] 未把 FR / Merge / Release 判断塞进 HVR
- [ ] 无占位符
- [ ] 无验证者自行补设计

---

> **CC defines what humans must verify.**
> **IHR records what implementation changed.**
> **ATR proves what automated tests actually executed and observed.**
> **HVR proves what humans actually executed and observed.**
> **FR determines closure from the evidence.**
> **Human Review decides Merge / Release.**