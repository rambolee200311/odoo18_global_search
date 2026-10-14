# FR — CC-016 Condition Builder and Visualization

## 0. 文档治理

本报告按 [CC-016 v0.2 FROZEN](../intent/CC-016_condition_builder_visualization.md) 评估实现与证据，不修改或重新解释 CC。用户批准了带例外的行政收口；该批准不替代 CC 明确要求的测试或 HVR 证据，也不将缺失项改判为通过。

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `CC-016` |
| FR Version | v0.1 |
| CC Version | v0.2 FROZEN |
| IHR | [IHR-GS-CC016-CC017.md](./IHR-GS-CC016-CC017.md) |
| ATR | [ATR-GS-CC016-CC017.md](./ATR-GS-CC016-CC017.md) |
| HVR | [HVR-GS-CC016-CC017.md](./HVR-GS-CC016-CC017.md) |
| 模块 | `wd_global_search` |
| 实现基线 | `2a360d0` |
| 评估日期 | 2026-10-14 |
| Prepared By | Copilot assistant |

## 2. 最终 Coding Contract 基线

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC-016 | v0.2 FROZEN | Closure 权威 |
| SRS_global_search | v1.5 FROZEN | 业务语义 |
| TDD_global_search | v0.4 FROZEN | 技术边界与防护栏 |

## 3. Executive Closure Summary

| 字段 | 结果 |
|---|---|
| 严格 Closure Status | **BLOCKED** |
| 当前代码基线 | `2a360d0` |
| 实施 | 主要 UI/服务端校验已实现；无冻结语义变更 |
| 自动化验证 | **BLOCKED**：34 项定向测试通过；CC16-TEST-001~027 逐项有效证据映射不完整 |
| Human Verification | **BLOCKED**：用户曾总体报告 HVR 通过，但缺逐场景记录、Published checksum 和可审计验证者信息 |
| 未授权偏差 | 无已知偏差 |
| Open Blocking Issues | 2 |
| 证据基线 | 实现与定向测试对应；HVR 无法验证其精确 baseline |
| 行政处置 | 用户批准带例外收口；不等于严格 Coding Contract SATISFIED |

## 4. Coding Contract Closure Matrix

| Contract Obligation | 来源 | 证据 | 状态 | 说明 |
|---|---|---|---|---|
| Keyword chips 仅表示并更新 Raw Query | CC-016 §§3–4 | IHR-002；ATR §4 局部浏览器观察 | PARTIAL | 已实现；缺少 HVR 逐场景证据 |
| 字段选择、operator/value 和权限约束 | CC-016 §§5、10；CC16-TEST-005/006/008/010 | IHR-001/002；ATR-RUN-001；历史 Odoo 套件 | PARTIAL | 类型校验回归通过；完整 CC16 测试逐项映射未建立 |
| 关键词、结构化条件、Refinement 分区展示 | CC-016 §6；CC16-TEST-007 | IHR-002；ATR §4 | PARTIAL | 有页面观察；无正式逐项 HVR |
| CC-015 搜索语义、错误、Count、分页/cursor 保持 | CC-016 §§7–11、14 | ATR §3；历史 Odoo 模块测试 81/81 | PARTIAL | 81 项运行早于 CC-017 UI 最终工作树；不能代替当前全量回归矩阵 |
| CC16-TEST-001~027 有可复核结果 | CC-016 §14 | ATR §3 | **BLOCKED** | 34 项核心单测不构成 27 项契约测试逐项证据 |
| 10 项用户 HVR 与浏览器/视口/Published checksum | CC-016 §14.1–14.2 | HVR §2 | **BLOCKED** | 只有用户总体确认，缺逐项实际观察和 checksum |
| 禁止边界与权限保护 | CC-016 §§3、10、13 | IHR §3；ATR §3 | PARTIAL | 未发现越界；不替代要求的完整权限 HVR |

## 5. Implementation Closure Assessment

IHR 记录 CC-016 条件构建交互、终端字段类型校验及测试变更。代码没有新增搜索语义、API 或 Published schema；`facade.py` 的终端值类型校验由定向单测和既有 Odoo 套件覆盖。实现事实成立，但不能填补 Contract 测试和人工验证的证据缺口。

## 6. Preservation & Guardrail Assessment

| 保留项 | 证据 | 状态 |
|---|---|---|
| 不改变 CC-015 多词/单词/Count/分页语义 | IHR §3；ATR §3 | PARTIAL |
| 不绕过权限、不使用 `sudo()`、不读取业务数据 | IHR §3；HVR §3 | SATISFIED（本次实现边界） |
| 不修改 SRS/TDD/既有 CC 或 Published schema | IHR §3 | SATISFIED |
| CC-002~CC-015 与 TD-001 适用回归 | ATR §3 | BLOCKED（全量逐项映射不足） |

## 7. Automated Verification Assessment

34/34 Search Core 单元测试通过；Python 编译、JavaScript 语法与 staged diff 检查通过。历史 Odoo 套件 81/81 通过，但其运行早于 CC-017 最终 UI 修改。由于 CC16-TEST-001~027 没有完整逐项映射，自动化子状态为 **BLOCKED**。

## 8. Human Verification Assessment

HVR 记录了用户的总体通过陈述及 agent-assisted 浏览器观察，并明确缺少逐项场景实际结果、Published checksum 和可审计验证者身份。CC-016 §14.2 要求逐项用户验收，因此 Human Verification 子状态为 **BLOCKED**。不以总体确认或自动化测试替代该要求。

## 9. Deviation & Stop Condition Assessment

未发现修改冻结语义或突破代码边界的未授权偏差。没有证据表明 CC-016 Stop Condition 被触发；仍需补齐的证据缺口见 §10。

## 10. Open Issues / Evidence Gaps

| ID | 描述 | Closure Impact | Human Judgment Required | 依据 |
|---|---|---|---|---|
| CC16-GAP-001 | CC16-TEST-001~027 未形成逐项有效 ATR 证据 | Blocking | No | CC-016 §14 DoD |
| CC16-GAP-002 | 10 项 HVR 缺逐场景执行观察、Published checksum、可审计 verifier | Blocking | No（需实际 HVR，不以判断代替） | CC-016 §14.1–14.2 |

## 11. Evidence Baseline Consistency

| 来源 | 基线 | 当前有效性 |
|---|---|---|
| IHR | `2a360d0` | Yes |
| ATR-RUN-001 | `2a360d0` 对应的提交前相同工作树 | Yes（仅记录的定向范围） |
| 历史 ATR-RUN-002 | CC-017 UI 最终修改前的工作树 | 仅对其历史测试范围有效 |
| HVR | 页面配置版本 191；未记录 checksum | Partial；不能证明所有场景对应最终基线 |

## 12. Done Criteria Assessment

| Done Criterion | 状态 | 缺口 |
|---|---|---|
| 条件构建、字段选择器和分区展示实现 | PARTIAL | 缺逐项 HVR |
| CC16-TEST-001~027 | BLOCKED | 缺完整有效 ATR 矩阵 |
| CC-002~CC-015 / TD-001 适用回归 | BLOCKED | 缺当前基线下逐项映射 |
| 用户 HVR 10 场景及 checksum | BLOCKED | 缺场景记录及 checksum |
| IHR、ATR、HVR、FR 可追溯 | PARTIAL | 文件齐备；HVR 内容不足以证明 Done |

## 13. Final Closure Determination

**Final Closure Status: BLOCKED**

严格 Coding Contract Closure 仍受 CC16-GAP-001/002 阻塞。用户批准了带例外的行政收口并授权提交，但没有修订冻结 CC-016 或补造缺失证据；因此本报告不将 CC-016 判为 SATISFIED。

## 14. Handoff to Human Review

Closure Assessment Complete: Yes
Human Review Required: Yes

若之后要求严格满足 CC-016，应补齐 CC16-TEST-001~027 的当前基线证据及 10 项 HVR，再更新 FR。当前提交只记录用户批准的带例外收口和仍未满足的证据义务。
