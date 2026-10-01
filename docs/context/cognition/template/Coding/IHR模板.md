# 实施历史记录标准母版
## Implementation History Record Standard Template
## 组织级标准 — v1.0.0
## 上游基线：SRS v1.0.0 | DDD v1.0.0（按需）| TDD v1.0.0 | Coding Contract v1.0.0
## 状态：Frozen

---

## 0. 文档治理

### 0.1 定位
Implementation History Record（IHR）是 **Execution & Evidence** 阶段的工程审计事实记录。
它与 Implementation **并行维护**（不是实施结束后凭记忆补写），忠实记录 Coding Contract 实际执行过程中发生了什么。

### 0.2 核心原则
- IHR 不得重新发明 SRS。
- IHR 不得重新发明 DDD。
- IHR 不得重新发明 TDD。
- IHR 不得重新定义 Coding Contract。
- IHR 只记录事实，不重新设计；只记录工程审计价值，不写思考流水账。

### 0.3 职责边界（必须理解）
```
CC   → 冻结本次执行边界（实施前）
Impl → 实际编码
IHR  → 记录实际发生了什么（与 Impl 并行）
ATR  → 自动化测试执行证据
HVR  → 人工验证 / UAT 证据
FR   → 汇总 IHR + ATR + HVR，判定 Contract 是否闭环
Human Review → 决定 Merge / Release
```
> **IHR 不负责证明测试通过、不负责证明用户验收通过、也不负责宣布项目完成。**

### 0.4 章节属性
- **强制**：0、1、2、3、4、5、6、7、8
- **按需**：Git/PR 元数据、Migration 记录、External Integration、Baseline Change History

### 0.5 IHR Entry ID
IHR 采用**统一单序号** `IHR-{NNN}`，不设计多套前缀。
一条 Entry = 一个具有工程审计价值的实施历史事实。

> **`IHR-{NNN}` 仅用于 Implementation History Entry，不作为整份 IHR 文档的 ID。整份 IHR 通过关联 Intent ID / Coding Contract 唯一识别。**

文档命名示例：
```
CC-INT-TMS-SPRINT52FIX-003.md
IHR-INT-TMS-SPRINT52FIX-003.md
```
其中 Entry 仍为：
```
IHR-001
IHR-002
IHR-003
```

### 0.6 可变快照 vs 仅追加历史（Mutable Snapshot vs Append-only History）
IHR 中的信息分为两类：

**A. Current Snapshot（可更新）**
§1 当前状态、§3 Current Implementation Status Summary、§5 Actual Change Inventory、§7 Open Issues 当前状态、§8 Handoff Summary。
这些是可变汇总，可随实施进展更新。

**B. Historical Record（仅追加）**
§4 Implementation History Entries、§6 Deviation / Stop 事件记录、附录 A Baseline Change History。
这些不得被覆盖或删除。

> **`Append, don't rewrite history` 仅针对 Historical Record。**
> Current Snapshot 可以更新，但**不得通过更新 Snapshot 删除或掩盖已经发生的历史事实**。
> 任何已发生的 Deviation、Stop、Revert、Baseline Change 不得因当前状态恢复正常而从 Historical Record 删除。

---

## 1. 执行元数据（Execution Metadata）

| 字段 | 值 |
|------|-----|
| IHR 文档 | `IHR-{intent_id}.md` |
| Intent ID | `{intent_id}` |
| CC 引用 | `{CC 文档名}`，版本 `{CC 版本}`，状态 `{Frozen}` |
| 模块 | `{module}` |
| 工作类型 | `{新功能 / Bug 修复 / 重构 / 迁移 / 安全修复 / ...}` |
| 实施负责人 | `{人或 Agent}` |
| 开始时间 | `{timestamp}` |
| 最后更新 | `{timestamp}` |
| 当前实施状态 | `{Not Started / In Progress / Blocked / Implementation Complete}` |

### Git / PR 元数据（按需，可选）
| 字段 | 值 |
|------|-----|
| Branch | `{optional}` |
| Base Commit | `{optional}` |
| Final Commit | `{optional}` |
| PR | `{optional}` |

> Git 记录代码版本；IHR 记录**代码变更与 Coding Contract 之间的工程语义关系**。IHR 不是 Git Log 复制品。

---

## 2. Coding Contract 基线（Coding Contract Baseline）

本节**只引用，不复制** CC 内容。

| 项 | 引用 |
|----|------|
| Scope（In/Out） | 见 `{CC 文档}` §3 |
| Change Boundary（Allowed/Forbidden） | 见 CC §4 |
| Required Behavior Changes | `{CC-CHANGE-001, 002, ...}` |
| Existing Behavior Preservation | `{CC-PRESERVE-001, 002, ...}` |
| Applicable TDD Guardrails | `{T-SEC-001, T-CONC-002, ...}` |
| Test Contract | `{CC-TEST-001 / TEST-xxx, ...}` |
| Stop Conditions | 见 CC §12 |
| Done Criteria | 见 CC §13 |

**基线版本锁定**：实施过程中若 CC / TDD / SRS / DDD 发生修订，须记录旧版本 → 新版本（见 §6、附录 A）。

---

## 3. 当前实施状态摘要（Current Implementation Status Summary）

> 本节为 **Current Snapshot（可更新）**，细节在 §4 Entries。

| 项 | 状态 |
|----|------|
| CC-CHANGE 落实进度 | `{已完成数} / {总数}` |
| Preservation Impact | `{None / Potential Impact / Impacted}`（引用 CC-PRESERVE-xxx、相关 IHR-xxx） |
| Deviation | `{None / Approved / Unauthorized}` |
| Stop Condition 触发 | `{Yes / No}` |
| Open Issues | `{0 / N}` |
| Revert 发生 | `{Yes / No}` |
| 当前状态 | `{Not Started / In Progress / Blocked / Implementation Complete}` |

> **Preservation Impact** 表示实际实施是否影响了 `CC-PRESERVE` 的保护区域及是否需要后续验证，验证结果归 ATR/HVR。

**重要**：`Implementation Complete` **仅表示编码实施阶段结束**，不表示 Contract 已满足 Done Criteria，也不表示允许 Merge / Release。
后续仍需 ATR → HVR → FR → Human Review。

---

## 4. 实施历史条目（Implementation History Entries）

### 4.1 Entry 结构（统一字段）
> 本节为 **Historical Record（仅追加）**，不得覆盖或删除。

| 字段 | 含义 |
|------|------|
| IHR ID | `IHR-{NNN}` |
| 时间 | 发生时间 |
| 阶段 | Implementation / Fix / Refactor / Migration / Revert |
| Action | 实际进行的工程动作 |
| Reason | 为什么进行该动作 |
| Files / Components | 实际影响范围 |
| Contract Reference | `CC-CHANGE-xxx` / `CC-PRESERVE-xxx` / `CC-DEC-xxx` |
| Upstream Reference | 必要时引用 `TDD / SRS / DDD` |
| Result | `Completed / Partial / Blocked / Reverted` |
| Deviation | `None` / `Approved` / `Unauthorized` |
| Follow-up | 后续待处理（如有） |

字段保持紧凑：**最少字段覆盖最大审计价值**，不要求每条写大量内容。

### 4.2 记录触发条件（满足任一即记录）
- 完成一个 `CC-CHANGE`；
- 为保护 `CC-PRESERVE` 作出重要实现；
- 新增 / 删除 / 重命名文件；
- 实际修改范围与 CC 预期不同；
- **发现会影响本次 CC 实施、边界、兼容性、风险或上游设计有效性的新的技术事实**；
- 触发 Stop Condition；
- 上游 SRS / DDD / TDD / CC 被修订；
- 作出经允许的 `CC-DEC`；
- 发生 migration 实施；
- 发生公共 API / 数据结构 / 权限相关实际变更；
- 发现未解决问题；
- 实施发生阻塞；
- 修复自动化测试发现的实现缺陷并导致代码实质修改。

**无需记录**：格式化、import 排序、注释修正、每次保存/编辑/测试运行等无审计价值的细节。

### 4.3 追溯粒度
大型任务以 `CC-CHANGE` 为主要追溯锚点，但**一个 CC-CHANGE 可对应多个 IHR Entry**；一个具有原子工程意义的 IHR Entry 在必要时也可关联多个 CC 项。不得为了形成机械 1:1 映射而合并或拆分历史事实。

### 4.4 Entry 示例
```
IHR-003
时间：{timestamp}
阶段：Fix
Action：修改 models/task.py::_confirm()
Reason：落实 CC-CHANGE-002
Files / Components：models/task.py
Contract Reference：CC-CHANGE-002, CC-PRESERVE-001
Upstream Reference：T-TRX-001
Result：Completed
Deviation：None
Follow-up：无
```

### 4.5 反模式（禁止）
- 开发日报式逐小时流水账；
- Agent 的 Chain of Thought / 内部推理；
- 方案 A 不行→方案 B 的思考过程；
- 代码行数 / token 用量 / 工具调用次数等无意义统计；
- "完成 XX%" 之类主观进度。

> **记录工程事实，不记录思考流水账。**

---

## 5. 实际变更清单（Actual Change Inventory）

放置位置：**§4 之后汇总**（理由：让读者先理解过程，再用此表快速核对"最终到底动了哪些东西"，服务于 FR / Reviewer；也可在 §1 摘要处放精简版）。

> 本节为 **Current Snapshot（可更新）**——随实施追加最终代码面；但不得删除已发生变更的记录。

| 文件 | 动作 | 实际变更 | CC 来源 | IHR |
|------|------|---------|---------|------|
| `models/task.py` | Modified | `_confirm()` 行为修正 | CC-CHANGE-001 | IHR-002 |
| `tests/test_task.py` | Added | 回归测试 | CC-TEST-001 | IHR-003 |

目的：不是重复 History，而是让 FR / Reviewer 快速回答 **"最终到底动了哪些东西"**。

---

## 6. 偏离与停止条件记录（Deviation / Stop Condition Record）

### 6.1 Deviation 三类
> 本节为 **Historical Record（仅追加）**。

**A. No Deviation** — 实际修改完全在 CC 授权边界内。

**B. Approved Deviation**（流程正确）:
```
发现必须越界
  ↓ 记录发现
  ↓ Stop
  ↓ 修订 CC / TDD / SRS / DDD
  ↓ 重新批准
  ↓ 继续 Implementation
  ↓ IHR 记录新基线
```
IHR 记录：原问题 / Stop Condition / 修订前基线 / 修订后基线 / 批准结果 / 恢复实施的节点。

**C. Unauthorized Deviation**（必须处理）:
必须标记 `Unauthorized Deviation`：
- 不得通过 IHR 自行合理化；
- 必须停止；
- 要么 revert，要么回上游审批后重新纳入 Scope；
- **解决前不得进入 FR 的正常 Done 状态。**

> 绝对禁止：实际代码已越界 → IHR 写个理由 → 自动视为合法。

### 6.2 Stop Condition 事件表
（CC §12 定义什么时候必须停；IHR 只证明当时是否真的停了、怎么处理的）

一次实施可能触发多次 Stop，因此使用事件表：

| IHR ID | CC Stop Condition | Issue | Escalated To | Baseline Updated | Resumed |
|--------|-------------------|-------|--------------|-----------------|---------|
| IHR-007 | CC §12 #4 | TDD 缺少并发设计 | TDD | Yes | Yes |
| IHR-015 | CC §12 #8 | 需修改外部 API 契约 | TDD | Yes | Yes |

未触发时明确写 `Stop Conditions: None`。

---

## 7. 遗留问题与后续（Open Issues / Follow-up）

> 本节状态列可更新（Current Snapshot）；新增 Issue 为 Historical Record。已解决 Issue **不删除**，更新为 `Resolved`，解决过程若产生重要代码变更则引用对应 `IHR-xxx`。

| ID | 问题描述 | 类别 | 级别 | Status | 责任方 |
|----|---------|------|------|--------|--------|
| OI-001 | `{如：某边界需业务确认}` | `{技术 / 业务 / 依赖}` | `{Blocker / Major / Minor}` | `{Open / Resolved / Deferred / Escalated}` | `{...}` |

无遗留问题时明确写 `Open Issues: None`。

---

## 8. 移交摘要（Handoff to ATR / HVR / FR）

IHR 只提供事实，不作完成判断。

```
Implemented：CC-CHANGE-001, CC-CHANGE-002, ...
Actual Files：{清单，或引用 §5}
Open Issues：None / {引用 §7}
Deviation：None / {引用 §6}
Stop Conditions Triggered：None / {引用 §6}
```
> 由 FR 读取 `CC + IHR + ATR + HVR` 后判定 Contract 是否闭环。IHR 不写"任务已完成/可 Merge/建议 Release"。

---

## 附录 A — 基线变更历史（Baseline Change History，按需）
> Historical Record（仅追加）

| 时间 | 上游 | 旧版本 | 新版本 | 触发原因 | 批准 | IHR 记录 |
|------|------|--------|--------|---------|------|---------|
| ... | TDD | v1.0.0 | v1.0.1 | 发现并发设计缺失 | {批准人} | IHR-007 |

---

## 附录 B — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|------|------|---------|------|
| v0.1 | {date} | 初稿 Draft | Draft |
| v1.0.0 | {date} | §0.5 文档 ID 与 Entry ID 解耦；§0.6 新增 Mutable Snapshot vs Append-only History；§3 改名 Current Snapshot + Preservation Impact；§4.2 收窄技术事实触发条件 + §4.3 追溯粒度；§6.2 Stop 改为事件表；§7 增加 Issue Status | **Frozen** |

---

## 附录 C — Agent 自动维护规则
- **Historical Record 采用 Append-only；Current Snapshot 可更新。** 任何已发生的 Deviation、Stop、Revert、Baseline Change 不得因当前状态恢复正常而从 Historical Record 删除（见 §0.6）；
- 开始 Implementation 时创建；
- 过程中**增量追加**，不覆盖历史；
- **不删除**失败 / 回退 / Stop 记录；
- 修改被 Revert：原记录保留，新增 Revert Entry；
- 基线变更：记录 旧版本 → 新版本；
- 结束：生成 §5 Inventory + §8 Handoff；
- **不允许为了让记录"看起来干净"而重写历史**；
- 允许修正明显记录错误，但须保留可审计性。

---

# 第二部分：模板设计说明

## 1. 为什么采用该结构
结构按"先摘要、后事实、再判定依据"排列：`Metadata + Baseline` 给上下文 → `Current Status Summary` 快速定位 → `History Entries` 是核心事实流 → `Actual Change Inventory` 供 Reviewer 快速核对 → `Deviation / Stop` 是治理重点 → `Handoff` 只交付事实。
设计目标：**另一个没参与编码的人或 Agent，只看 CC + IHR，就能准确知道原来授权改什么、实际改了什么、为什么改、有没有偏离、有没有停下来升级、当前留下什么问题。**

## 2. 为什么 IHR 是 Evidence Record 而不是 Design Document
CC 冻结边界、Impl 改代码、IHR 记录已发生事实。IHR 不得新增业务规则、领域语义、架构设计、未经批准的技术方案或 Scope。发现设计缺失 → 记录事实 → Stop → 回上游修订。禁止在 IHR 里写一个"解释"就把越界修改合法化。

## 3. 必须记录的内容
- 实际改了哪些文件 / 模型 / 字段 / 方法 / XML / JS / Controller / Cron / Queue；
- 每项对应哪个 `CC-CHANGE / CC-PRESERVE / TDD / TEST`；
- 实施中发现的问题、Stop Condition 触发、CC/TDD/SRS/DDD 修订；
- 与原 CC 不一致的实际修改及批准状态；
- 经批准的实现级决策落地；
- 当前实施状态。
按 §4.2 触发条件记录，**持续记录而非结束后补写**。

## 4. 不应记录的内容
- Agent Chain of Thought、内部推理、方案试错过程（反模式 1、2）；
- CC 的 In/Out Scope、Guardrails 全文（只引用，反模式 3、4）；
- 测试环境、命令全集、Pass/Fail 数量、coverage（属 ATR，反模式 5）；
- UAT / 人工验收结果（属 HVR）；"任务完成/可 Merge/建议 Release"（属 FR，反模式 6）；
- 代码行数、token 用量、工具调用次数、"完成 XX%"（反模式 8）。

## 5. 如何防止变成流水账
统一 Entry 结构（§4.1）+ 触发条件（§4.2，已收窄为"影响 CC 实施/边界/兼容性/风险/上游有效性的技术事实"）+ 反模式清单（§4.5）：只记录"具有工程审计价值的事实"，不问"你在想什么"。

## 6. 如何处理 Deviation
三分类（§6.1）：No / Approved / Unauthorized。核心纪律 —— Approved 必须走完整 Stop → 修订 → 重新批准 → 续做流程；Unauthorized 不得被 IHR 合理化，必须 revert 或回上游审批，解决前不得进入 FR 正常 Done 状态。

## 7. 如何处理 Stop Condition
CC §12 定义"什么时候必须停"；IHR 只证明"当时是否真的停了、怎么处理的"（§6.2 事件表，支持一次实施多次触发）。

## 8. 如何与 CC / ATR / HVR / FR 分工
```
CC   → 边界契约（实施前）
Impl → 改代码
IHR  → 记录发生了什么（并行，事实层）
ATR  → 自动化测试证据（IHR 只引用 TEST-xxx，不存测试详情）
HVR  → 人工验证证据（IHR 只记录"实现了 visibility 逻辑"，不记录"按钮显示正常"）
FR   → 汇总判定闭环
Human Review → Merge / Release
```

## 9. 如何支持简单任务与大型 Sprint
简单 Bug Fix 可能只有 2-3 条 Entry，这是正常的（§4.2 触发条件天然收敛）。大型任务以 `CC-CHANGE` 为主要追溯锚点，但一个 CC-CHANGE 可对应多个 IHR Entry（§4.3），不得机械 1:1。模板不强制简单任务写几百行。

## 10. 为什么由 Agent 增量维护
Agent 开始 Implementation 时创建，过程中追加，不覆盖历史，不删失败/回退/Stop 记录，Revert 保留原记录并新增 Revert Entry（附录 C）。结束后补写会失真，且容易"为了看起来干净而重写历史"。同时区分 Current Snapshot（可更新）与 Historical Record（仅追加），避免 Summary 更新污染事实历史（§0.6）。

---

# 第三部分：IHR 自查清单（Frozen / Handoff Gate）

```
[ ] 1. CC 基线：已引用正确的 CC 版本且状态为 Frozen（§2）
[ ] 2. ID 无歧义：文档 ID 与 Entry ID（IHR-{NNN}）已正确区分（§0.5）
[ ] 3. 实际修改文件：已完整记录，无遗漏（§5 Inventory）
[ ] 4. 追溯性：所有重要实际修改可追溯至 CC（CC-CHANGE / CC-PRESERVE）（§4.1）
[ ] 5. Deviation：
[ ]    - 无未经批准的 Deviation（§6.1 C）
[ ]    - 如有 Approved Deviation，完整记录了 Stop → 修订 → 批准 → 续做链路
[ ]    - Historical Record 中 Deviation / Stop / Revert 未被 Snapshot 更新掩盖（§0.6）
[ ] 6. Stop Condition：如触发，已按事件表如实记录每次触发原因、升级路径、基线更新（§6.2）
[ ] 7. Revert：如发生，原记录保留，新增 Revert Entry（附录 C）
[ ] 8. Open Issues：已列出并标注 Status，或明确写 None（§7）
[ ] 9. 边界卫生：
[ ]    - 未把 ATR 内容（测试详情/覆盖率）塞进 IHR
[ ]    - 未把 HVR 内容（人工验收结果）塞进 IHR
[ ]    - 未把 FR 判断（可 Merge / 已完成）塞进 IHR
[ ]    - 未重新定义 CC 边界或复制 CC/TDD 全文
[ ] 10. 占位符：无 {待定} / {TBD} 残留
[ ] 11. 无 Agent 自行补设计：所有新增技术决策均有上游追溯或标记为 CC-DEC 实现级落地
[ ] 12. 状态诚实：当前状态未越级标注为"完成"，明确仅为 Implementation Complete
```

**未满足 Gate，不得进入 FR 的正常闭环判定。**
