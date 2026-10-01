# Automated Test Record 标准母版
## 组织级标准 — v1.0.0
## 状态：Frozen
## 上游基线：SRS v1.0.0 | DDD v1.0.0（按需）| TDD v1.0.0 | CC v1.0.0 | IHR v1.0.0
## 冻结日期：2026-09-04

---

## 0. 文档治理

### 0.1 定位
Automated Test Record（ATR）是单次开发任务 / Sprint / Intent 的**自动化测试执行证据记录**。
它记录：Coding Contract 要求的自动化测试实际执行了什么、在哪个代码基线上执行、结果是什么、这些结果能证明什么。

ATR 位于 Execution & Evidence 阶段：
`Implementation + IHR → ATR → HVR → FR → Human Review / Merge / Release`

### 0.2 核心原则
- ATR 不得重新发明 SRS。
- ATR 不得重新发明 DDD。
- ATR 不得重新发明 TDD。
- ATR 不得重新定义 Coding Contract。
- ATR 不得重新设计测试需求。
- **No execution, no PASS.**

ATR 消费已存在的：SRS AC、DDD DV/INV（如适用）、TDD TEST-xxx/T-xxx、CC Test Contract、CC-PRESERVE。只记录实际执行证据，不复制规范性正文。

### 0.3 越界治理
测试过程中如发现 SRS AC / DDD INV·DV / TDD TEST / CC Test Contract 存在问题，或"为通过测试必须修改业务规则 / 突破 CC Scope / 修改技术架构"：
记录 FAIL / BLOCKED → 触发 CC Stop → 回 SRS/DDD/TDD/CC 修订 → Implementation 修复 → IHR 留痕 → 重新执行测试 → ATR 追加新 Run。

**绝对禁止**：为了让测试通过，修改测试去迎合错误实现（除非上游 Test Contract 经正式修订）。

### 0.4 章节属性
- **强制**：0、1、2、3、4、5、6、10 及附录 C
- **按需**：7（Issues，无问题可写 None）、8（Special Verification）、9（Evidence Inventory）

### 0.5 Run 编号
统一使用 `ATR-RUN-{NNN}` 标识一次正式测试执行。
不设计 ATR-PASS / ATR-FAIL / ATR-ENV 等大量子前缀。

### 0.6 Mutable Snapshot vs Append-only History（继承自 IHR §0.6）
- **Current Snapshot（可更新）**：§1 当前状态、§3 Current Automated Test Status、§4 Coverage Matrix 当前状态、§7 Issues 当前状态、§10 Handoff Summary。可随 Test Run 更新。
- **Historical Record（仅追加）**：§5 Test Run History、§6 Regression Verification 历史、§7 已关闭 Issue、附录 A Baseline Change History。不得为"最后全绿"而删除或重写。
- 核心纪律：**Append test history; update current snapshot.**

---

## 1. Execution Metadata（Current Snapshot）

| 字段 | 值 |
|------|-----|
| Intent ID | `{intent_id}` |
| IHR 文档 | `IHR-{intent_id}.md` |
| CC Version | `{CC 版本}` |
| Module | `{module}` |
| Environment | `{环境标识}` |
| Test Framework | `{pytest / odoo --test-enable / npm test / ...}` |
| Code Baseline（当前） | `{commit hash 或明确可识别基线}` |
| Branch | `{按需}` |
| Execution Start | `{timestamp}` |
| Execution End | `{timestamp}` |
| Executed By | `{agent / CI / developer}` |

Git Commit 在 ATR 中尤为重要：测试证据必须绑定代码版本。每次正式 Test Run 应尽可能绑定 Commit Hash（不强求所有项目统一工具，但需可识别基线）。

---

## 2. Test Contract Baseline（仅引用，不复制）

| 来源类型 | ID | 验证点 | ATR 关注 |
|---------|-----|--------|---------|
| CC Test Contract | CC-TEST-xxx | `{行为/边界}` | 必须执行并给出结果 |
| SRS AC | AC-xxx | `{验收条件}` | 按 CC 要求覆盖 |
| DDD DV（如适用） | DV-xxx | `{领域验证}` | 按 CC 要求覆盖 |
| DDD INV（如适用） | INV-xxx | `{不变量}` | 按 CC 要求覆盖 |
| TDD Guardrail | T-xxx | `{防护栏}` | 按 CC 要求验证 |
| CC-PRESERVE | CC-PRESERVE-xxx | `{回归保护}` | 见 §6 Regression |

SSOT 归属上游冻结版本。ATR 仅引用 ID，可用一句短描述辅助阅读。

---

## 3. Current Automated Test Status（Current Snapshot，可更新）

| 指标 | 值 |
|------|-----|
| Required Automated Tests | `{n}` |
| PASS | `{n}` |
| FAIL | `{n}` |
| SKIPPED | `{n}` |
| BLOCKED | `{n}` |
| NOT RUN | `{n}` |
| **Latest Valid Run** | `{ATR-RUN-NNN}` |
| **Current Code Baseline** | `{commit}` |
| **Evidence Baseline Match** | `{Yes / No}` |

**Latest Valid Run 规则**：自动化测试证据仅对其绑定的 Code Baseline 有效。
若测试之后代码发生实质修改：必须判断哪些测试证据失效、重新执行受影响测试，不得将旧 Commit 的 PASS 自动继承给新 Commit。
Evidence Baseline Match = No 时，§4 Matrix 中对应项视为 NOT RUN / 失效，须重新执行。

此摘要可更新；历史 Run 本身永不删除。

---

## 4. Core Test Contract Coverage Matrix

每个纳入本次 CC Test Contract 的自动化测试要求，都必须有显式结果：`PASS / FAIL / SKIPPED / BLOCKED / NOT RUN`。
**不得通过"没有记录"表示"不适用"**；不适用应在 CC 阶段裁剪，或触发治理流程，而非 ATR 自行删除。

| CC / TEST 来源 | Automated Test | Run | Result | Evidence |
|---------------|---------------|-----|--------|----------|
| CC-TEST-001 | TEST-023 | ATR-RUN-003 | PASS | `{log/CI ref}` |
| AC-xxx / INV-xxx | TEST-024 | ATR-RUN-003 | PASS | ... |
| T-CONC-002 | TEST-025 | ATR-RUN-003 | PASS | ... |
| CC-PRESERVE-002 | existing `test_bill_creation` | ATR-RUN-003 | PASS | ... |
| ... | ... | ... | NOT RUN | ... |

---

## 5. Test Run History（Append-only Historical Record）

每次正式执行追加一条 `ATR-RUN-{NNN}`。失败 Run 必须保留。

### 5.1 Run Entry 结构

| 字段 | 含义 |
|------|------|
| Run ID | ATR-RUN-001 |
| Timestamp | 执行时间 |
| Code Baseline | Commit / 可识别基线 |
| Environment | 环境引用 |
| Invocation | 命令 / CI Job |
| Scope | 实际执行测试范围（Targeted / Module / Integration / Regression / Relevant Suite） |
| Expected Tests | 预期数量（如可得） |
| Executed | 实际执行数量 |
| PASS / FAIL / SKIPPED / BLOCKED | 计数 |
| Result | PASS / FAIL / PARTIAL / BLOCKED（整体结论，非"项目完成"判定） |
| Evidence | log / CI / artifact 引用 |
| Follow-up | IHR / issue 引用（修复后重新测试时） |

### 5.2 Test Fix → Retest 闭环示例

```
ATR-RUN-002
  TEST-023: FAIL
  Reason: confirmed state rejects unchanged many2one value
  Follow-up: IHR-012（修正 models/task.py::_confirm）

    ↓ Implementation Fix

ATR-RUN-003
  TEST-023: PASS
  Code Baseline: abc123
```

- ATR 记录 Failure 与重新执行结果；
- IHR 记录因失败导致的代码修改；
- ATR 不写详细修复过程。

### 5.3 不得伪造全量

```
Executed Scope: wd_ai_vendor_invoice module tests
Not Executed: entire Odoo test suite
Reason: outside CC regression boundary
```
必须明确实际运行范围，不虚构"全量测试通过"。

---

## 6. Regression Verification（映射 CC-PRESERVE）

专门回答："修 A 有没有破坏 B？" 不得只写 "Regression passed"。

| CC-PRESERVE | 回归测试（Existing / New） | Run | Result | Code Baseline |
|------------|--------------------------|-----|--------|---------------|
| CC-PRESERVE-001 | existing `test_api_contract` | ATR-RUN-003 | PASS | abc123 |
| CC-PRESERVE-002 | new `test_bill_creation_regression` | ATR-RUN-003 | PASS | abc123 |

结果同时汇总到 §4 Matrix。

---

## 7. Issues（Current Snapshot；历史 append-only）

### 7.1 FAIL / BLOCKED / SKIPPED / Flaky Issues

| ID | TEST | Run | 类型 | 原因 | Status | Follow-up |
|----|------|-----|------|------|--------|-----------|
| 1 | TEST-023 | ATR-RUN-002 | FAIL | 状态校验逻辑错误 | Resolved（IHR-012） | ATR-RUN-003 PASS |
| 2 | TEST-040 | ATR-RUN-003 | BLOCKED | 外部服务不可用 | Open | ... |

Status：`Open / Resolved / Deferred / Escalated`。已解决 Issue 不删除，更新 Status；若解决过程产生代码变更，引用对应 IHR。

### 7.2 Flaky Test 治理

同基线、无代码修改下重复执行结果不一致 → 标记 `Potential Flaky Test`：
- 哪个 TEST、哪些 Run、结果差异、是否阻塞、Follow-up。
- 禁止："第一次 FAIL、第二次 PASS → 直接写 PASS 忽略第一次。"

---

## 8. Special Verification [按需]

简单 Bug Fix 可全部写 N/A / Not Required。不为复杂 Work Type 制造大量表格。

### 8.1 Performance（按需）
benchmark / baseline / threshold / actual / result。

### 8.2 Security（按需）
权限测试、敏感数据暴露测试（T-ERR-001）、安全扫描。

### 8.3 Migration（按需）
迁移执行测试、历史数据校验、Recovery / Rollback 验证（按 CC/TDD 要求）。

### 8.4 Integration / Mock 透明度（重要）
必须声明测试所用替身层级，不得夸大证据能力：

| 层级 | 声明 |
|------|------|
| Unit Test with Mock / Stub / Fake | 仅证明单元逻辑，不代表真实集成 |
| Integration Test with Sandbox | 仅证明沙箱环境交互 |
| Real External Integration Test | 才可宣称真实外部集成已验证 |

Adapter / API / AI Provider / Webhook / Queue 场景尤其必须透明。
**Mock 通过 ≠ 真实外部 API 已验证。**

### 8.5 Coverage（按需，非普遍硬 Gate）
仅在 TDD/CC/项目标准要求时记录：tool / scope / result / threshold / pass-fail。
否则：`Coverage: N/A / Not Required`。
测试质量由需求、行为、边界、异常、回归覆盖决定，不机械等同于覆盖率百分比。

---

## 9. Evidence Inventory [按需]

不复制海量原始证据（不把 ATR 写成 console log）。
仅记录可复核引用：CI Job URL / artifact、JUnit XML、coverage report、log 文件路径、截图路径。

| Evidence ID | 类型 | 位置 / 引用 | 对应 Run |
|------------|------|------------|---------|
| E-001 | CI Job | `{url}` | ATR-RUN-003 |
| E-002 | JUnit XML | `{path}` | ATR-RUN-003 |

---

## 10. Handoff to HVR / FR

ATR 只提供自动化验证事实摘要，**不宣布** "Coding Contract 已完成 / 可以 Merge / 可以 Release"。

```
Required Automated Tests: 18
PASS: 17   FAIL: 0   SKIPPED: 1   BLOCKED: 0   NOT RUN: 0
Latest Valid Run: ATR-RUN-003
Evidence Baseline Match: Yes
Outstanding: SKIPPED TEST-050（reason: ...）

→ 交由 HVR（人工验证部分）+ FR（汇总证据判定闭环）
→ 最终 Merge / Release 由 Human Review 决定
```

若存在 FAIL / BLOCKED / NOT RUN，ATR 如实暴露，由 FR / Human Review 决定是否允许 Closure。

---

## 附录 A — Baseline Change History（Append-only）

| 时间 | 旧 Code Baseline | 新 Code Baseline | 失效的 Run | 处理 |
|------|-----------------|----------------|----------|------|
| ... | abc123 | def456 | ATR-RUN-003（部分） | 重新执行受影响测试 → ATR-RUN-004 |

---

## 附录 B — Version History

| 版本 | 日期 | 变更 | 状态 |
|------|------|------|------|
| v0.1 | 2026-09-04 | 初稿 Draft | Draft |
| v0.2 RC | 2026-09-04 | 结构收口、增加 Latest Valid Run、Mock 分层、Core Coverage Matrix | RC |
| v1.0.0 | 2026-09-04 | 治理规则定型、Snapshot/History 二分、Flaky/Retest 闭环 | **Frozen** |

---

## 附录 C — Agent 维护规则

1. Implementation 进入自动化测试阶段时创建 ATR，锁定 CC / IHR / Code Baseline。
2. 据 CC Test Contract 生成 §4 Coverage Matrix。
3. 实际执行测试；每次正式执行追加 ATR-RUN（append-only）。
4. FAIL 不删除；返回 Implementation 修复时引用 IHR。
5. 修复后重新执行受影响测试，新 Run 记录新 Code Baseline。
6. **新代码 Baseline 不得自动继承旧 Baseline 的 PASS**；更新 §3 Evidence Baseline Match。
7. Current Snapshot（§3/§4/§7/§10）可更新；Run History 与已关闭 Issue 永不删除。
8. 最终生成 Evidence Inventory + Handoff。
9. 不得根据"预期应该通过"填写 PASS；未执行即 NOT RUN。
10. 严禁修改测试去迎合错误实现（除非上游 Test Contract 经正式修订）。

---

## ATR 自查清单（Handoff Gate）

```
[ ] 1. CC 基线（版本）正确引用
[ ] 2. IHR / Code Baseline 已锁定，每次 Run 绑定 commit 或可识别基线
[ ] 3. §4 Coverage Matrix 完整映射 CC Test Contract；无"未记录=不适用"
[ ] 4. 每个 required 自动化验证项均有显式状态（PASS/FAIL/SKIPPED/BLOCKED/NOT RUN）
[ ] 5. 所有 PASS 均来自真实执行（No execution, no PASS）
[ ] 6. FAIL 未被隐藏或删除，保留在历史 Run 中
[ ] 7. SKIPPED 有 Skip Reason；BLOCKED 有 Block Reason
[ ] 8. NOT RUN 清晰可见，未被算作 PASS
[ ] 9. §6 Regression 逐项对应 CC-PRESERVE
[ ] 10. 关键 AC / DV / INV / T-xxx 已按 CC 要求覆盖
[ ] 11. Latest Valid Run 与 Current Code Baseline 匹配（Evidence Baseline Match）
[ ] 12. 代码变更后旧 PASS 未错误继承，受影响项已重测
[ ] 13. Flaky 已显式标记并有 Follow-up
[ ] 14. Mock / Stub / Sandbox / Real 分层已透明声明，证据未夸大
[ ] 15. Evidence 可复核（CI / artifact / log 引用）
[ ] 16. 未把 HVR（人工 UAT）或 FR（完成判定 / Merge 建议）内容塞进 ATR
[ ] 17. 无占位符残留（或已显式标记 N/A）
[ ] 18. Agent 未通过修改测试来迎合错误实现
```

---

## 反模式（禁止）

1. Test Exists = PASS（测试代码存在 ≠ 执行通过）
2. 只保留最后一次绿色结果（失败历史必须保留）
3. 测试失败就改测试（除非上游 Test Contract 正式修订）
4. 旧 Commit PASS 自动继承给新 Commit
5. Mock = Real Integration（证据能力不得夸大）
6. Coverage = Quality（覆盖率非唯一质量标准）
7. ATR = Console Log（只存可复核摘要与 Reference）
8. ATR = IHR（代码怎么修属 IHR）
9. ATR = HVR（人工体验验证属 HVR）
10. ATR = Final Report（不宣布 Contract Done / Merge / Release）

---

## 职责纪律

> CC defines what must be verified.
> IHR records what implementation changed.
> ATR proves what automated tests actually executed and observed.
> HVR proves what humans actually verified.
> FR determines closure from the evidence.
> Human Review decides Merge / Release.
