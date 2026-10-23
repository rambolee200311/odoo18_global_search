# FR-M2-002：Provider Usage 兼容与计量记录

## 0. 文档治理

本 Final Report 依据已冻结的 CC-M2-002 及其 IHR/ATR 实际证据判定契约关闭状态，不修改或重新解释上游需求。

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-002` |
| FR ID / 版本 | `FR-M2-002` / V1.0.0 |
| CC 版本 | `CC-M2-002` — FROZEN V1.0.0 |
| IHR | [IHR-M2-002](IHR-M2-002_provider_usage.md) |
| ATR | [ATR-M2-002](ATR-M2-002.md) |
| HVR | N/A；CC 未要求用户可见 UI，见 CC §13 #7 |
| 模块 | `llm_openai`、`office_engine_m2` |
| 当前代码基线 | `091942a2cd2b0feadf0a41c3c3c7fc345c4fc186` |
| 评估日期 | 2026-10-23 |

## 2. 最终 Coding Contract 基线

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC-M2-002 | FROZEN V1.0.0 | 本次关闭义务的唯一执行契约 |
| M2 SRS | V1.0.0 Frozen | 业务语义与隐私需求 |
| DDD | N/A | M2 已批准不适用 |
| M2 TDD | V1.0.0 Frozen | Usage 数据、Provider 兼容与权限技术约束 |

## 3. Executive Closure Summary

| 字段 | 判定 |
|---|---|
| Closure Status | `SATISFIED` |
| CC-CHANGE | 5 / 5 satisfied |
| CC-PRESERVE | 6 / 6 satisfied |
| Applicable CC Guardrails | 4 / 4 satisfied |
| Automated Verification | `SATISFIED` |
| Human Verification | `N/A`（由 CC §13 #7 决定） |
| Unauthorized Deviation | None detected |
| Open blocking issues | 0 |
| Evidence Baseline Consistency | Valid；ATR/IHR 所测代码即本 FR 所绑定 commit 的代码 |

## 4. Coding Contract Closure Matrix

| 契约义务 | 来源 | 证据 | 状态 | 说明 |
|---|---|---|---|---|
| Provider Usage/response ID 白名单标准化 | CC-CHANGE-001 | IHR §实施阶段；ATR CC-TEST-001–003 | SATISFIED | 保留原 content/tool_calls；缺失或非法 Usage 不伪造 0、不丢正文。 |
| 创建最小 Usage ORM 模型 | CC-CHANGE-002 | IHR §变更范围；ATR CC-TEST-005/007 | SATISFIED | 仅保存批准的计量/关联元数据；0 与 NULL 可区分。 |
| 内部受控 `record_usage()` | CC-CHANGE-003 | IHR §变更范围；ATR CC-TEST-005 | SATISFIED | 未知/敏感输入、原始 SDK 对象均拒绝；提权范围仅限 Usage create。 |
| ACL / 运维读取权限 | CC-CHANGE-004 | IHR §变更范围；ATR CC-TEST-006 | SATISFIED | 普通用户无访问权；系统/运维组只读。 |
| Mock、消费者回归、Addon 验证 | CC-CHANGE-005 | ATR CC-TEST-001–008 | SATISFIED | 无真实外网请求；消费者和 streaming 保持原行为。 |
| CC-PRESERVE-001–006 | CC §6 | ATR CC-TEST-001–006、008 | SATISFIED | 各项响应结构、消息体、权限及缺失语义均有对应断言。 |
| TDD Guardrails | CC §7 | ATR 与 IHR 基线记录 | SATISFIED | `T-M2-LLM-001`、`T-M2-DATA-002`、`T-M2-SEC-001`、`T-M2-BASE-001` 均有证据。 |
| 完成定义 | CC §13 #1–7 | IHR、ATR、下列评估 | SATISFIED | 适用自动化测试均 PASS；HVR 按 CC 记 N/A。 |

## 5. Implementation Closure Assessment

IHR 的变更清单与最终工作树/提交一致：既有 Provider 文件只修改 `_openai_process_non_streaming_response()` 方法体；新增代码仅在 `mymodules/office_engine_m2/`。没有修改 Odoo 官方源码、其他 Provider、`llm_assistant` 或 `llm_thread`。Provider AST 范围检查通过；差异证据图见 [CC-M2-002 Git diff 范围证据](evidence/CC-M2-002_git_diff_scope.png)。

## 6. Preservation & Guardrail Assessment

| 保留项 / Guardrail | 证据 | 状态 |
|---|---|---|
| content 原值与消息正文 | ATR CC-TEST-001/002/004 | SATISFIED |
| tool_calls 结构与顺序 | ATR CC-TEST-001/004 | SATISFIED |
| usage/response_id 不进入聊天消息 | ATR CC-TEST-004 | SATISFIED |
| Streaming / Provider 请求行为不变 | ATR CC-TEST-008 与 streaming 回归 | SATISFIED |
| Usage ACL 最小权限 | ATR CC-TEST-006 | SATISFIED |
| 缺失/非法计量不丢响应、不伪造 0 | ATR CC-TEST-002/003/005 | SATISFIED |
| `T-M2-LLM-001` | ATR CC-TEST-001–004 | SATISFIED |
| `T-M2-DATA-002` | ATR CC-TEST-005–007 | SATISFIED |
| `T-M2-SEC-001` | ATR CC-TEST-001/008 | SATISFIED |
| `T-M2-BASE-001` | IHR §基线裁定、差异审查 | SATISFIED |

## 7. Automated Verification Assessment

ATR 对 CC-TEST-001–008 均给出原生状态 `PASS` 和实际证据。最终 Odoo 测试运行报告 `0 failed, 0 error(s) of 13 tests`；Addon 升级、ORM、ACL、响应消费者与 SDK Mock 测试均有证据。Python 编译、XML 解析、`git diff --check` 及 Provider 方法范围检查通过。最终 Odoo shell 核验确认模块已安装、模型已注册、没有持久测试 Usage 行。没有真实外网调用。

测试日志中三个其他模块不可安装的既有提示已在 ATR 记录；它们未影响 `office_engine_m2` 测试结果，不属于本 CC 的变更或失败项。

## 8. Human Verification Assessment

`Human Verification: N/A`  
Source: CC-M2-002 §13 #7。  
Reason: 本 CC 不引入用户可见 UI；验证义务由 SDK Mock、TransactionCase、ACL 与模块升级测试覆盖。N/A 不代表人工测试通过。

## 9. Deviation & Stop Condition Assessment

未发现未经批准的实现偏差，CC §12 中未触发需升级的停止条件。测试中曾发现并修正一项测试参数/断言不一致，以及 Odoo Integer 空值转 0 的陷阱；最终实现和全套回归通过，历史过程保留在 ATR。

## 10. Open Issues / Findings / Evidence Gaps

| ID | 来源 | 描述 | 对 CC 关闭的影响 | 备注 |
|---|---|---|---|---|
| FR-M2-002-NB-001 | M2 Implementation Plan 阶段 2 | 本轮以 `odoo-bin -u office_engine_m2 --test-enable` 完成真实 Odoo 升级与测试；计划阶段门禁列出的 XML-RPC 升级操作未单独执行。 | Non-Blocking for CC closure；不应据此声明计划阶段 2 的全部门禁已完成。 | CC-TEST-007 的模块安装/升级义务有当前数据库 CLI 升级证据。若项目负责人要求关闭计划的 XML-RPC 子门禁，应在具备授权凭据的验证窗口补做。 |

该计划级事项不否定 CC 本身已满足的契约义务，但 M2 Implementation Plan 阶段 2 的整体 Gate 不在本 FR 中宣告关闭。

## 11. Evidence Baseline Consistency

| 证据源 | 基线 | 对当前代码有效 | 依据 |
|---|---|---|---|
| IHR-M2-002 | `9e0d32be7b166ef7710d7a6a8fd7174ebdb5f943` + 本 CC 变更；实施 commit `091942a2cd2b0feadf0a41c3c3c7fc345c4fc186` | Yes | 最终实施提交包含被验证的代码与测试；后续仅追加关闭报告文档。 |
| ATR-M2-002 | 测试工作树对应 commit `091942a2cd2b0feadf0a41c3c3c7fc345c4fc186` 的代码内容 | Yes | 测试后代码未改变；ATR 仅补充关闭状态。 |
| HVR | N/A | N/A | 按 CC §13 #7。 |

## 12. Done Criteria Assessment

| CC §13 标准 | 证据 | 状态 | Gap |
|---|---|---|---|
| #1 CC-CHANGE 完成且差异在白名单内 | IHR §变更范围、Provider AST 检查、差异图 | SATISFIED | — |
| #2 CC-TEST-001–008 有实际证据且 PASS | ATR 验收矩阵 | SATISFIED | — |
| #3 聊天/工具/streaming 兼容 | ATR CC-TEST-004/008 | SATISFIED | — |
| #4 Usage 数据最小化，缺失/非法不伪造 | ATR CC-TEST-002/003/005 | SATISFIED | — |
| #5 权限和内部创建边界 | ATR CC-TEST-005/006 | SATISFIED | — |
| #6 Addon 升级、测试清理、基线 | ATR CC-TEST-007；Odoo shell 只读核验；IHR | SATISFIED | 计划级 XML-RPC 子门禁另见 §10。 |
| #7 IHR/ATR 完成，HVR N/A | IHR、ATR | SATISFIED | — |

## 13. Final Closure Determination

```text
Final Closure Status: SATISFIED
```

全部必需 CC-CHANGE、CC-PRESERVE、适用 Guardrails 和自动测试义务均有当前基线证据且满足；HVR 按 CC 明确为 N/A；无未解决的 CC 级阻塞项或未经批准的偏差。负责人已批准关闭 CC-M2-002。

此结论只关闭 CC-M2-002，不宣告 Implementation Plan 阶段 2 的所有项目级门禁已关闭，也不构成合并/发布批准。
