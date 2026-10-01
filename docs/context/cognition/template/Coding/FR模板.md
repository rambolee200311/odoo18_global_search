# Final Report 标准母版
## 组织级标准 — v1.0.0
## 状态：Frozen
## 上游基线：SRS v1.0.0 | DDD v1.0.0（按需）| TDD v1.0.0 | CC v1.0.0 | IHR v1.0.0 | ATR v1.0.0 | HVR v1.0.0
## 冻结日期：2026-09-04

---

## 0. 文档治理

### 0.1 定位
Final Report（FR）是 Agent Coding Workflow 中 **Evidence → Closure** 阶段的收口文档。
它基于 Frozen Coding Contract 及 IHR / ATR / HVR 的实际证据，逐项判断本次 Coding Contract 的执行义务是否已经满足，并形成可追溯的 Closure Determination。

### 0.2 核心原则
- FR 不得重新发明 SRS / DDD / TDD。
- FR 不得重新定义 Coding Contract。
- FR 不得重新解释 CC Done Criteria 以便让任务通过。
- **FR may assess evidence; FR may not manufacture evidence.**

### 0.3 职责边界
- CC 定义执行义务（CC 是 Closure 权威）。
- IHR / ATR / HVR 是证据源。
- **FR 消费证据、判断 Closure。**
- Human Review 决定 Merge / Release。
- 即：`Contract Closure ≠ Merge Decision ≠ Release Decision`。

### 0.4 Evidence Gap 处理
FR 中发现证据缺失时：
```
发现 Evidence Gap
→ FR 标记 Closure Blocked / Incomplete
→ 返回对应 Evidence Record 补充真实证据
→ 必要时重新 Implementation / Test / Human Verification
→ Evidence 更新
→ 重新生成 / 更新 FR
```
禁止 FR 补写 IHR/ATR/HVR 中缺失的事实。若 Mandatory Contract Obligation 所需 Evidence 缺失，Closure Impact **必须为 Blocking**；Human Review 不得用人工判断替代缺失 Evidence。

---

## 1. Closure Metadata

| 字段 | 值 |
|------|-----|
| Intent ID | `{intent_id}` |
| FR ID | `FR-{intent_id}.md` |
| FR Version | `{v0.1 / v1.0 / ...}` |
| CC Version | `{最终 Frozen 版本}` |
| IHR Reference | `{IHR 文档}` |
| ATR Reference | `{ATR 文档}` |
| HVR Reference | `{HVR 文档 或 N/A}` |
| Module | `{模块}` |
| Current Implementation Baseline | `{commit}` |
| Prepared By | `{Agent / 人}` |
| Assessment Date | `{时间}` |

---

## 2. Final Coding Contract Baseline

只引用，不复制：

| 来源 | 最终版本 | 相关性 |
|------|---------|--------|
| CC | `{版本}` | **Closure 权威**（所有 Obligation 的来源） |
| SRS | `{版本}` | 业务语义 |
| DDD | `{版本 或 N/A}` | 领域语义 |
| TDD | `{版本}` | 技术设计与 Guardrails（由 CC 裁剪本次适用项） |

---

## 3. Executive Closure Summary

保持极短（**事实摘要，非 Completion Percentage**）：

| 字段 | 值 |
|------|-----|
| Closure Status | `{SATISFIED / NOT SATISFIED / BLOCKED}` |
| Current Code Baseline | `{commit}` |
| CC-CHANGE | `{n required / n satisfied}` |
| CC-PRESERVE | `{n required / n satisfied}` |
| Applicable CC Guardrails | `{n required / n satisfied}` |
| Automated Verification | `{SATISFIED / NOT SATISFIED / BLOCKED / N/A}` |
| Human Verification | `{SATISFIED / NOT SATISFIED / BLOCKED / N/A}` |
| Unauthorized Deviation | `{None / Present}` |
| Open Blocking Issues | `{n}` |
| Evidence Baseline Consistency | `{Valid / Partial / Invalid}` |

注意：统计维度是 **satisfied**，不是 evidenced。有 Evidence ≠ 满足。

---

## 4. Coding Contract Closure Matrix（核心）

| Contract Obligation | Source | Evidence (IHR/ATR/HVR) | Status | Notes |
|---------------------|--------|------------------------|--------|-------|
| 实现功能 A | CC-CHANGE-001 | IHR-003, IHR-005 | SATISFIED | — |
| 保持行为 B | CC-PRESERVE-001 | ATR-RUN-004 | SATISFIED | — |
| 并发 Guardrail | CC §Guardrails → T-CONC-002 | IHR-007 + ATR-RUN-005 | SATISFIED | sourced from TDD |
| 自动化测试 | CC-TEST-001 | ATR Coverage Matrix | SATISFIED | — |
| Portal 人工验证 | CC HVR #1 | HVR-SCN-001 / HVR-RUN-002 | SATISFIED | — |
| Done Criterion #4 | CC §13 | IHR + ATR + HVR | SATISFIED | — |

规则：
- 每个 Mandatory Obligation 必须有显式 Status + Evidence Reference。
- **Source 列必须指向 CC**，不得直接从 TDD/SRS 拉取义务。
- FR 仅评估 Frozen CC 明确纳入的义务。TDD 中存在但未被 CC 纳入的 T-xxx，不得由 FR 自行加入 Closure Obligation。

---

## 5. Implementation Closure Assessment（读 IHR）

| CC-CHANGE | IHR Evidence | Actual Change Inventory | Status |
|-----------|--------------|------------------------|--------|
| CC-CHANGE-001 | IHR-003 | `models/task.py` | SATISFIED |
| CC-CHANGE-002 | IHR-006 | `views/task.xml` | SATISFIED |

不复制 IHR 实施过程，只判断是否存在充分 Implementation Evidence 且结果为 satisfied。

---

## 6. Preservation & Guardrail Assessment

### 6.1 Preservation（读 IHR + ATR + HVR）

| CC-PRESERVE | Implementation Impact | ATR Evidence | HVR Evidence | Status |
|-------------|----------------------|--------------|--------------|--------|
| CC-PRESERVE-001 | Potential Impact | ATR-RUN-004 PASS | N/A | SATISFIED |
| CC-PRESERVE-002 | Impacted | ATR PASS | HVR-RUN-003 PASS | SATISFIED |

### 6.2 Applicable CC Guardrails（sourced from TDD）

| CC Guardrail Reference | TDD Source | Evidence | Status |
|------------------------|------------|----------|--------|
| CC §Guardrails / T-TRX-001 | T-TRX-001 | IHR-004 + TEST-023 | SATISFIED |
| CC §Guardrails / T-ADPT-001 | T-ADPT-001 | IHR-006 + TEST-027 | SATISFIED |

**硬规则**：FR 仅评估 Frozen CC 明确纳入本次执行边界的 TDD Guardrails。CC 未纳入的 T-xxx 不得成为 Closure Obligation。

---

## 7. Automated Verification Assessment（读 ATR）

读取 ATR 的：Current Status、Coverage Matrix、Current Valid Evidence Set、Evidence Baseline Status、Open Test Issues。

逐项回答：
1. CC Test Contract 是否全部有显式状态；
2. Required Verification Items 是否均有当前有效证据；
3. 是否存在 FAIL / BLOCKED / NOT RUN；
4. SKIPPED 是否有合理分类（Expected/Unexpected）与治理结果；
5. Regression 是否满足 CC-PRESERVE；
6. Evidence 是否对应当前 Code Baseline；
7. Mock/Sandbox Evidence 是否被正确理解（不夸大）；
8. 是否存在 Flaky Test 风险。

子状态映射：全部满足 → SATISFIED；明确未满足（FAIL/NOT RUN）→ NOT SATISFIED；受阻无法判断 → BLOCKED。

FR 不重新运行测试，不复制 ATR Run 明细。

---

## 8. Human Verification Assessment（读 HVR）

### 若 Human Verification Required = No
```
Human Verification: N/A
Source: CC
Reason: {原因}
```
N/A ≠ PASS，不得偷换。

### 若 Human Verification Required = Yes
读取 HVR Coverage Matrix / Current Valid Evidence Set / Verifier / Expected vs Actual / Findings / Evidence Baseline Status，回答：
1. Required Scenario 是否全部有当前有效证据；
2. 是否存在 FAIL / BLOCKED / NOT RUN；
3. Human Verifier 是否可识别、可审计；
4. Agent 是否冒充 Human；
5. Human Regression 是否满足；
6. Open Findings 是否影响 Closure；
7. Evidence 是否仍对应当前 Code Baseline。

子状态映射同 §7：全部满足 → SATISFIED；明确未满足 → NOT SATISFIED；受阻 → BLOCKED。

FR 不重新做人工验证。

---

## 9. Deviation & Stop Condition Assessment（读 IHR）

### 9.1 Deviation

| 类型 | 要求 | Closure 条件 |
|------|------|-------------|
| No Deviation | — | 正常 |
| Approved Deviation | 发现→Stop→上游修订→重新批准→Baseline 更新→恢复→Evidence 重生成 | 链路完整才可 Closure |
| Unauthorized Deviation | 未解决 | **Contract 不得 SATISFIED** |

FR 不得通过"实际效果没问题"把 Unauthorized Deviation 合法化。

### 9.2 Stop Condition

| Stop Event | Condition | Escalated To | Resolution | Evidence Refreshed | Status |
|------------|-----------|--------------|------------|-------------------|--------|
| `{IHR-xxx}` | CC §12 #{n} | `{SRS/TDD/CC}` | `{修订}` | `{是/否}` | `{Resolved/Open}` |

对每个触发的 Stop 检查：是否真的停止 → 是否升级到正确权威 → Baseline 是否更新 → 是否重新批准 → 是否刷新受影响的 Evidence。

---

## 10. Open Issues / Findings / Evidence Gaps

汇总 IHR/ATR/HVR 中当前未关闭事项。

**Closure Impact 与 Human Judgment 为两个独立维度：**

| ID | 来源 | 描述 | Closure Impact | Human Judgment Required | 依据 |
|----|------|------|---------------|------------------------|------|
| `{ID}` | `{IHR/ATR/HVR}` | `{描述}` | `{Blocking / Non-Blocking / Undetermined}` | `{Yes / No}` | `{CC 条款}` |

判定逻辑：
- **Blocking**：违反 Mandatory CC Obligation / Done Criteria / 使 Evidence 无效 / 产生未解决 Unauthorized Deviation。
- **Non-Blocking**：不影响 Contract Closure（如未来增强、文档 follow-up、发布窗口安排）。
- **Undetermined**：当前无法确定是否满足 Contract → **整体 Closure Status 必须为 BLOCKED**，直到正确上游权威（SRS/DDD/TDD/CC）完成判断或修订。Human Review 不得代替上游权威解决 Contract 语义不确定性。
- Low Severity **不**自动等于 Non-Blocking——若违反 Mandatory AC，仍属 Blocking。
- 判断依据是 Contract，不是主观 Severity。

### Evidence Gap 显式暴露
```
Evidence Status: MISSING
Closure Impact: Blocking
Human Judgment Required: No（不得用人工判断替代缺失 Evidence）
Required Action: {返回 IHR / ATR / HVR / CC}
```

---

## 11. Evidence Baseline Consistency

| Evidence Source | Baseline | Valid for Current Code? | Basis |
|----------------|----------|------------------------|-------|
| IHR | `{commit}` | Yes | Current |
| ATR | `{commit}` | Yes | Impact Analysis + Retest |
| HVR | `{commit}` | Yes | Retained—unaffected |

核心：`Closure applies to the current implementation baseline, not to a historical green baseline.`

---

## 12. Done Criteria Assessment（逐项判定 CC §13）

| Done Criterion | Evidence | Status | Gap |
|----------------|----------|--------|-----|
| CC §13 #1 | IHR §5 | SATISFIED | — |
| CC §13 #2 | ATR §4 | SATISFIED | — |
| CC §13 #3 | HVR §4 | SATISFIED | — |
| CC §13 #4 | IHR §6 | SATISFIED | — |

FR 不重新创造 Requirement ID，直接引用 CC §13 编号。

---

## 13. Final Closure Determination

### 若 SATISFIED
```
Final Closure Status: SATISFIED
Basis:
- All mandatory CC-CHANGE obligations have implementation evidence and are satisfied.
- Required preservation verification is satisfied.
- Applicable CC Guardrails (sourced from TDD) have evidence and are satisfied.
- CC Test Contract has valid automated evidence.
- Required Human Verification has valid human evidence (or N/A by CC).
- No unresolved Unauthorized Deviation exists.
- All triggered Stop Conditions were resolved through approved baselines.
- Current evidence is valid for the current implementation baseline.
- All CC Done Criteria are satisfied.

This determination means the Coding Contract has sufficient evidence for closure.
It does NOT constitute Merge or Release approval.
```

### 若 NOT SATISFIED
```
Final Closure Status: NOT SATISFIED
Unsatisfied Obligations:
- CC-CHANGE-003: implementation incomplete
- CC-TEST-004: FAIL
- CC-PRESERVE-002: regression failure
Basis:
Evidence is sufficient to determine that one or more mandatory Coding Contract
obligations are not satisfied. This is NOT a case of missing evidence (BLOCKED),
but a case of evidence proving non-satisfaction.
Required Next Action:
Return to the appropriate Implementation / Evidence stage.
```

### 若 BLOCKED
```
Final Closure Status: BLOCKED
Blocking Gaps:
- CC-TEST-004 = NOT RUN (Missing Evidence → Blocking)
- HVR-SCN-003 = BLOCKED
- Current HVR evidence baseline does not match current code
Required Next Action:
Return to ATR / HVR and regenerate valid evidence.
```

---

## 14. Handoff to Human Review

```
Closure Assessment Complete: Yes
Human Review Required: Yes
```

告知 Reviewer：
- Contract Closure Status；
- Blocking Items（如有）；
- Non-Blocking Known Items（如有）；
- Items Requiring Human Judgment（如有，标注 Human Judgment Required = Yes）；
- Evidence References（附录 A）。

FR 不作 Merge / Release 决策。即使 Closure = BLOCKED，FR 本身仍可以是 `Closure Assessment Complete: Yes`（已成功判断当前被阻塞）。

---

## 附录 A — Evidence Reference Index

| Evidence Type | Reference | Current / Valid | Purpose |
|---------------|-----------|-----------------|---------|
| CC | `{CC 文档}` | Frozen | Contract authority |
| IHR | `{IHR 文档}` | Yes | Implementation evidence |
| ATR | `{ATR 文档}` | Yes | Automated verification |
| HVR | `{HVR 文档}` | Yes | Human verification |

不复制证据正文。

## 附录 B — FR Version History

| Version | Date | Closure Status | Reason |
|---------|------|---------------|--------|
| v0.1 | 2026-09-04 | BLOCKED | Missing HVR evidence for SCN-003 |
| v0.2 | 2026-09-04 | SATISFIED | HVR-RUN-004 completed, evidence valid |

FR 采用 **Versioned Current Assessment + Version History**，不做 append-only event log。

## 附录 C — Agent Maintenance Rules

1. 读取 Frozen CC（**所有 Obligation 来源**）；
2. 读取最终 IHR / ATR / HVR（或确认 HVR N/A）；
3. 获取 Current Code Baseline；
4. 构建 Closure Matrix（§4），Source 只引用 CC；
5. 逐项评估 §5–§12；
6. 输出 Closure Status（§13，三态：SATISFIED / NOT SATISFIED / BLOCKED）；
7. 输出 Human Review Handoff（§14）；
8. Evidence 更新时，递增 FR Version，保留 Version History。
禁止：补造 Evidence、修改 Evidence Record 历史、从 TDD 直接增加 Closure Obligation（须经 CC）、重新解释 CC、忽略 FAIL/BLOCKED/NOT RUN、N/A 偷换 PASS、因测试全绿自动判 Closure、宣布 Merge/Release Approved。

---

# 第二部分：FR 模板设计说明

## 问题 A：Closure Status 采用三态还是四态？
**采用三态：`SATISFIED / NOT SATISFIED / BLOCKED`，不使用 `PARTIALLY SATISFIED`。**

理由：
- `PARTIALLY SATISFIED` 极易被误用为"软通过"，削弱 Mandatory Obligation 硬闸门语义；
- "部分满足"已通过 Closure Matrix 逐行 NOT SATISFIED 精确表达；
- 三态决策树：`Can FR determine?` → No → BLOCKED；Yes → `Are all mandatory satisfied?` → No → NOT SATISFIED，Yes → SATISFIED。无灰色地带。

## 问题 B：FR 应 append-only 还是 versioned assessment？
**采用 Versioned Current Assessment + Version History（附录 B），不做 append-only event log。**

理由：IHR/ATR/HVR 已保留全部事实历史；FR 本质是"当前 Closure 判断"，更新是常态；保留版本历史满足审计性。

## 问题 C：FR 最后的 Gate 应叫什么？
**采用 `Closure Assessment Complete` + `Human Review Required`。**

理由：切断 "Contract Closure" 与 "Merge/Release Decision" 的语义混淆。即使 BLOCKED，FR 也可标记 Assessment Complete = Yes。

## 其余设计要点

1. **CC 是 Closure 权威**：FR 所有 Obligation 必须来自 CC。TDD Guardrails 须经 CC 裁剪纳入，FR 不得直接从 TDD 拉取义务（P1-1 修正）。
2. **Closure Impact 与 Human Judgment 分离**（P1-2 修正）：不确定 → Undetermined → BLOCKED；Human Review 不替代上游权威。
3. **子状态统一**（P2-1 修正）：Automated/Human Verification 统一使用 SATISFIED / NOT SATISFIED / BLOCKED / N/A。
4. **NOT SATISFIED 模板**（P2-2 修正）：与 BLOCKED 明确区分——前者是"已知不满足"，后者是"无法可靠判断"。
5. **satisfied 非 evidenced**（P2-3 修正）：摘要统计的是 satisfied 数量，不是 evidenced 数量。
6. FR 不产生新证据、不做发布审批、Closure 复杂度跟随 Contract 复杂度。

---

# 第三部分：FR 自查清单（Closure / Handoff Gate）

- [ ] 最终 Frozen CC Baseline 正确（所有 Obligation 来源）
- [ ] 当前 Implementation Baseline 正确
- [ ] IHR / ATR / HVR 引用正确
- [ ] Human Verification Required=No 时正确标记为 N/A（非 PASS）
- [ ] 所有 CC-CHANGE 有 Implementation Evidence 且 Status 正确
- [ ] 所有适用 CC-PRESERVE 有所需验证证据
- [ ] Applicable CC Guardrails 全部来自 CC（非直接从 TDD 拉取）
- [ ] CC Test Contract 已完整评估
- [ ] Required Automated Verification 子状态正确（SATISFIED/NOT SATISFIED/BLOCKED/N/A）
- [ ] Required Human Verification 子状态正确（SATISFIED/NOT SATISFIED/BLOCKED/N/A 或 N/A）
- [ ] 无未解决 Unauthorized Deviation
- [ ] Approved Deviation 升级链路完整
- [ ] 所有 Stop Condition 已正确处理或明确阻塞
- [ ] Open Issues / Findings 已评估 Closure Impact（Blocking/Non-Blocking/Undetermined）
- [ ] Missing Evidence 已显式暴露且 Closure Impact = Blocking
- [ ] Evidence Baseline 与 Current Code 一致或有有效 Impact Analysis
- [ ] Done Criteria（CC §13）已逐项判断
- [ ] Closure Matrix 无遗漏 Mandatory Obligation，Source 指向 CC
- [ ] FR 没有制造新 Evidence
- [ ] FR 没有重新设计 SRS / DDD / TDD / CC
- [ ] FR 没有宣布 Merge / Release
- [ ] 无占位符
- [ ] Closure Status 与证据一致（三态）

---

> **CC defines the obligations.**
> **IHR proves what implementation changed.**
> **ATR proves what machines verified.**
> **HVR proves what humans verified.**
> **FR assesses whether the obligations are satisfied by the evidence.**
> **Human Review decides Merge / Release.**