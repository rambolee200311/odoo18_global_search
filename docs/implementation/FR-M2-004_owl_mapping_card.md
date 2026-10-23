<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/FR模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# FR-M2-004：Owl 映射卡片与 RPC 服务端校验

## 0. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-004` |
| FR ID / Version | `FR-M2-004` / `V1.0.0` |
| CC Version | `CC-M2-004 FROZEN V1.0.0` |
| IHR | [IHR-M2-004_owl_mapping_card.md](IHR-M2-004_owl_mapping_card.md) |
| ATR | [ATR-M2-004.md](ATR-M2-004.md) |
| HVR | [HVR-M2-004_owl_mapping_card.md](HVR-M2-004_owl_mapping_card.md) |
| Module | `office_engine_m2` |
| TDD | `TDD_office_engine_m2.md V1.0.0 Frozen` |
| Current implementation baseline | `24d6d4c7a7b28172c156c0b58b46fa1ef78b869d`（CC-M2-004 实现代码提交）；本次文档提交只追加关闭处置/追溯及 CC-M2-005 Draft |
| Prepared by / Assessment date | Codex / 2026-10-23 |
| Freeze disposition | `FROZEN WITH OPEN ITEMS`；登记册 [`AUTHORIZATION_RECORDS.md`](AUTHORIZATION_RECORDS.md)，记录 `EXEMPTION-CC-M2-004-001`–`003` |

## 1. 最终 CC 基线

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC | `CC-M2-004 FROZEN V1.0.0` | 本 FR 的唯一义务来源 |
| SRS | M2 SRS V1.0.0 Frozen | 映射卡片、用户修正、权限隔离 |
| DDD | N/A | 按冻结 M2 TDD 判定 |
| TDD | M2 TDD V1.0.0 Frozen | Owl/RPC/revision/安全约束 |
| Plan | M2 Implementation Plan V1.0.0 Frozen | 阶段 4；阶段 3 Gate 缺口仍单独保留 |

## 2. 执行摘要

| 字段 | 判定 |
|---|---|
| Final Closure Status | **`NOT SATISFIED`** |
| 行政关闭处置 | 负责人批准 `FROZEN WITH OPEN ITEMS`，见授权登记册；不等于所有义务满足 |
| CC-CHANGE | 实现已完成；证据见 IHR |
| Automated Verification | `NOT SATISFIED` — 后端测试通过，但 `HttpCase.browser_js` 为 SKIPPED，ATR 总体 PARTIAL |
| Human Verification | `NOT SATISFIED` — HVR-SCN-001/002 PASS；HVR-SCN-003/004 未完整通过 |
| Open blocking evidence | 自动浏览器验证、HVR 未完成子场景、阶段 3 XML-RPC Gate 缺口 |
| Unauthorized deviation | 未发现代码越界；阶段 Gate 证据仍缺失 |
| Evidence baseline | 测试在 Odoo/Python 项目环境对 CC-004 工作树执行；本次提交包含同一代码内容及文档处置 |

## 3. Coding Contract Closure Matrix

| 契约义务 | 来源 | 证据 | 状态 | 说明 |
|---|---|---|---|---|
| 专用 mapping 消息呈现卡片、目标与下拉项 | CC-CHANGE-001/002 | IHR；ATR CC-TEST-001；HVR-SCN-001 | SATISFIED | 人类确认实际卡片及下拉显示。 |
| 当前用户权限下读取 Session/context | CC-CHANGE-003 | IHR；ATR CC-TEST-004/008 | SATISFIED | JSON-RPC 跨用户拒绝及数据最小化测试通过。 |
| 校验并保存映射 edits、拒绝非法字段和旧 revision | CC-CHANGE-004 | IHR；ATR CC-TEST-003/005/006 | SATISFIED | 服务端 validator、revision 和无副作用断言通过。 |
| 确认/取消和 revision 绑定 | CC-CHANGE-005 | IHR；ATR CC-TEST-007；HVR-SCN-002（确认部分） | NOT SATISFIED | 自动化服务测试通过；HVR 要求中的取消及完整状态路径未由人类执行。 |
| RPC 失败时受控反馈和交互恢复 | CC-CHANGE-006 | ATR CC-TEST-009；Agent HVR 观察 | NOT SATISFIED | HVR 的普通聊天实际发送与 console 断言缺证据。 |
| `Message.components`/资产加载/普通消息不回归 | CC §13 #2–3、CC-TEST-001/010 | ATR CC-TEST-010；HVR-SCN-001 | NOT SATISFIED | 人工卡片显示通过；浏览器自动化跳过，普通消息隔离未获完整浏览器证据。 |
| owner/company、字段白名单、无提权、样例不落库 | CC-TEST-003/004/008、CC-PRESERVE-001–005 | ATR CC-TEST-003/004/008；IHR | SATISFIED | 当前用户/RPC 和静态范围证据支持该义务。 |
| 自动化浏览器要求 | CC-TEST-002/010、CC §13 #6 | ATR `HttpCase.browser_js` SKIPPED | NOT SATISFIED | 负责人授权豁免记录 001；原结果保持 SKIPPED。 |
| 必需人工场景 | CC §11.1、CC §13 #6 | HVR-SCN-001–004 | NOT SATISFIED | 两个场景通过；两个场景未完整运行，见豁免记录 002。 |
| 阶段 3 前置 Gate 已处置 | CC §13 #8 / CC-M2-004-OPEN-001 | CC-M2-003 ATR 未含 XML-RPC 安装/升级证据 | NOT SATISFIED | 负责人批准仅对本 CC 记录豁免 003；阶段 3 Gate 仍 OPEN。 |

## 4. 实施与验证评估

实现范围见 IHR；Odoo 自动测试及执行结果见 ATR。最终已记录的自动化运行是 32 tests、0 failures、0 errors，包含 1 个 `HttpCase.browser_js` skip；不得将跳过项算作通过。Python、JS、XML、资产加载、权限与 Session 测试有相应证据。未调用真实 LLM/API。

内置浏览器人工证据确认：映射卡片显示、合法字段 `name` 选择、保存及确认；数据库 Session revision 与 confirmed_revision 相等。用户的“人工验证通过”按该实际覆盖范围登记。取消、不完整卡片补项和错误后发送普通聊天消息未由人工完整执行。

## 5. Open Issues / Evidence Gaps

| ID | 来源 | 缺口 | Closure Impact | 人类处置 |
|---|---|---|---|---|
| GAP-M2-004-001 | ATR CC-TEST-002/010 | 自动浏览器测试 SKIPPED | Blocking | 负责人按豁免 001 接受缺少自动浏览器回归的风险。 |
| GAP-M2-004-002 | HVR-SCN-003/004 | 人工取消/澄清和完整错误恢复场景未运行 | Blocking | 负责人按豁免 002 批准带缺项关闭；HVR 状态不变。 |
| GAP-M2-004-003 | Implementation Plan 阶段 3 Gate | XML-RPC 安装/升级证据缺失 | Blocking（计划 Gate） | 负责人按豁免 003 接受本 CC 行政关闭；阶段 3 Gate 仍 OPEN。 |

## 6. Done Criteria Assessment

| CC §13 标准 | 结果 | 证据/差异 |
|---|---|---|
| #1 变更完成且限于白名单 | SATISFIED | IHR/差异范围。 |
| #2 专用卡片及普通消息隔离 | NOT SATISFIED | 卡片显示有 HVR；普通消息回归浏览器证据不完整。 |
| #3 rpc 导入、资产及 JS/XML 检查 | SATISFIED | ATR 静态/模块加载记录。 |
| #4 端点授权、状态和 revision | SATISFIED | ATR TransactionCase/HttpCase。 |
| #5 非法 edits/旧 revision/跨用户拒绝 | SATISFIED | ATR CC-TEST-003–008。 |
| #6 HVR-SCN-001–004 和浏览器自动化 | NOT SATISFIED | HVR-SCN-003/004 未通过；browser_js SKIPPED。 |
| #7 最小化、无提权 | SATISFIED | ATR/IHR 静态与序列化检查。 |
| #8 IHR/ATR/HVR/FR 与阶段 3 Gate | NOT SATISFIED | 记录齐备；阶段 3 XML-RPC 证据缺失且仍 OPEN。 |

## 7. Final Closure Determination

**Final Closure Status: NOT SATISFIED**

至少一项强制自动化/人工验证证据及阶段 Gate 证据缺失。负责人已明确批准 CC-M2-004 以 `FROZEN WITH OPEN ITEMS` 处置并提交推送；完整授权见 `AUTHORIZATION_RECORDS.md`。该授权允许将本 CC 作为带未通过项的行政关闭记录保存，但不把任何子状态改为 PASS，不将 FR Closure Status 改为 SATISFIED，也不宣告 Implementation Plan 阶段 3/4 或 M2 完成。

| 人工交接 | 值 |
|---|---|
| Closure Assessment Complete | Yes |
| Human Review | 负责人已批准带未通过项关闭 |
| Merge / Release | 不在本 FR 的授权范围 |
| Freeze disposition | `FROZEN WITH OPEN ITEMS` |

## 附录 A — 证据索引

| 类型 | 引用 | 用途 |
|---|---|---|
| CC | [CC-M2-004_owl_mapping_card.md](CC-M2-004_owl_mapping_card.md) | 关闭义务来源 |
| IHR | [IHR-M2-004_owl_mapping_card.md](IHR-M2-004_owl_mapping_card.md) | 实施范围 |
| ATR | [ATR-M2-004.md](ATR-M2-004.md) | 自动化原始状态 |
| HVR | [HVR-M2-004_owl_mapping_card.md](HVR-M2-004_owl_mapping_card.md) | 人类验证范围与缺口 |
| Authorization | [AUTHORIZATION_RECORDS.md](AUTHORIZATION_RECORDS.md) | 永久豁免记录 001–003 |

## 附录 B — FR Version History

| 版本 | 日期 | Closure Status | 说明 |
|---|---|---|---|
| V1.0.0 | 2026-10-23 | NOT SATISFIED | 依据 CC-004、IHR/ATR/HVR 评估；负责人批准 FROZEN WITH OPEN ITEMS，底层证据状态保持不变。 |
