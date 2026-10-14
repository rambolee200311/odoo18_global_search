# FR — CC-017 UI Layout Optimization Subgoal

## 0. 文档治理

本报告评估 [CC-017 v0.4 FROZEN UI 子目标](../intent/CC-017_ui_layout_optimization.md)。CC-017 明确不是独立 Coding Contract；本 FR 仅判断该冻结子目标是否有足够证据完成，不修改其要求。用户批准带例外行政收口，不替代冻结 Done Criteria，也不把未实现或未验证项改判为通过。

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `CC17-UI-LAYOUT` |
| FR Version | v0.1 |
| 基线 | CC-017 v0.4；CC-016 v0.2 |
| IHR | [IHR-GS-CC016-CC017.md](./IHR-GS-CC016-CC017.md) |
| ATR | [ATR-GS-CC016-CC017.md](./ATR-GS-CC016-CC017.md) |
| HVR | [HVR-GS-CC016-CC017.md](./HVR-GS-CC016-CC017.md) |
| 模块 | `wd_global_search` |
| 实现基线 | `2a360d0` |
| 评估日期 | 2026-10-14 |
| Prepared By | Copilot assistant |

## 2. 最终基线

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC-017 UI 子目标 | v0.4 FROZEN | 本报告评估依据 |
| CC-016 | v0.2 FROZEN | 兼容性权威 |
| SRS_global_search / TDD_global_search | v1.5 / v0.4 FROZEN | 上游语义和技术边界 |

## 3. Executive Closure Summary

| 字段 | 结果 |
|---|---|
| 严格 Closure Status | **NOT SATISFIED** |
| 当前代码基线 | `2a360d0` |
| 自动化/浏览器辅助验证 | **PARTIAL** |
| 人工 HVR | **BLOCKED**：缺正式逐项人类验证证据 |
| 已满足 | 已测字号/字体/留白/卡片边界；区域顺序；三个 disclosure 默认收缩及键盘切换 |
| 未满足 / 阻塞 | Query Understanding 响应 Count；卡片语义结构；完整分页交互；完整浏览器矩阵 |
| 未授权偏差 | 无；结构限制依 §17 停止 |
| Open Blocking Issues | 4 |
| 行政处置 | 用户批准带例外收口；不等于子目标 Done Criteria 全部满足 |

## 4. 子目标 Closure Matrix

| Obligation | 来源 | 证据 | 状态 | 说明 |
|---|---|---|---|---|
| 字号、字体、已存在角色颜色 | CC-017 §§3, 9–10；UI-TEST-001/007/008 | ATR §4；HVR §3 | PARTIAL | 可见角色通过观察；卡片 H3、Label/Value 不存在而不能验证 |
| 卡片主标题、Meta、摘要及 Label/Value 分离 | §§4–5；UI-TEST-002/003 | IHR-005；ATR §4 | BLOCKED | 只有单一 `snapshot.rendered_text`；禁止猜测 |
| 明细摘要与三项省略 | §6；UI-TEST-004 | IHR-005；ATR §4 | BLOCKED | 无可用结构化明细节点；按 §17 停止 |
| Query Understanding 样式和响应 Count | §7；UI-TEST-005 | ATR §4；HVR §3 | **NOT SATISFIED** | 位置和样式已做；“About X results”/响应 Count 未实现 |
| 间距、字体、卡片边框/阴影 | §§8–11；UI-TEST-006~009 | ATR §4 | PARTIAL / SATISFIED（所测范围） | 已测量元素符合；语义节点范围未覆盖 |
| 分页控件与分页行为 | §12；UI-TEST-010 | ATR §4 | NOT RUN | 当前两条结果没有可操作的分页按钮 |
| 七区顺序、三个默认收缩和键盘切换 | v0.4 Governance；UI-TEST-014~016 | ATR §4；HVR §3 | SATISFIED（agent-assisted observation） | 不作为正式人类 HVR PASS |
| CC-016/CC-015 语义与完整回归 | §§13–16；UI-TEST-011/012 | ATR §3 | PARTIAL | 仅有限页面和请求观察；无完整 Count、cursor、error、permission matrix |
| 浏览器兼容矩阵 | §15 UI-TEST-013 | ATR §4；HVR §4 | NOT RUN | 只观察 Chromium；Firefox/Safari/Edge 未运行 |
| IHR、ATR、HVR 和用户人工验收 | §18 | IHR/ATR/HVR | BLOCKED | 用户总体确认未形成可审计场景记录 |

## 5. Implementation Assessment

CC-017 可在 CSS/JS 和 Workspace markup 边界内实现的字号/字体/颜色/间距、无边框卡片外观、区域顺序和 disclosure 已完成。代码未修改 controller/service/model 的搜索业务逻辑、Search API、CC-016 条件语义或 Published schema。

## 6. Preservation & Guardrail Assessment

| 保留要求 | 状态 | 依据 |
|---|---|---|
| 不修改 CC-016、CC-015 搜索语义 | SATISFIED | IHR §3；有限 Search API 观察 |
| 不解析 rendered_text 猜字段 | SATISFIED | IHR-005；按 §17 停止 |
| 不改 controllers 的搜索逻辑、services、models、schema | SATISFIED | IHR §3 |
| 不引入外部技术栈、数据库/业务数据访问或权限旁路 | SATISFIED | IHR §3 |

## 7. Automated Verification Assessment

当前最终工作树有 34/34 Search Core 单元测试通过、Python/JavaScript 语法检查通过。浏览器 computed-style/DOM 观察只覆盖可见节点；CC17-UI-TEST-002~004、010、013 未通过或未运行，UI-TEST-005 已知未实现。总体为 **NOT SATISFIED**。

## 8. Human Verification Assessment

HVR 中记录了用户总体验收确认和 agent-assisted 页面观察，但缺完整测试 ID 对应的实际步骤、观察、Published checksum 和可审计人类 verifier。正式 HVR 为 **BLOCKED**；不以 agent 观察或自动化替代用户验收。

## 9. Deviation & Stop Condition Assessment

CC-017 §17 第 2–4 项适用：template-based 卡片只提供单一 `snapshot.rendered_text`，不能安全拆分字段或明细。实施已停止语义重排并记录为 BLOCKED，没有通过猜测或扩大边界绕行。用户的带例外行政收口不构成 CC 修订。

## 10. Open Issues / Evidence Gaps

| ID | 描述 | Closure Impact | Human Judgment Required | 依据 |
|---|---|---|---|---|
| CC17-GAP-001 | 卡片主标题、Label/Value、明细结构化显示无法在当前数据契约内完成 | Blocking | Yes（需上游契约/结构数据决策） | §§4–6、§17 |
| CC17-GAP-002 | About X results 使用响应 Count 未实现 | Blocking | No | §7、UI-TEST-005、§18 |
| CC17-GAP-003 | 分页交互与完整浏览器矩阵未验证 | Blocking | No | §15、§18 |
| CC17-GAP-004 | 正式人类 HVR 缺场景级可审计记录 | Blocking | No（需实际执行，不可豁免为 PASS） | §18 |

## 11. Evidence Baseline Consistency

| 来源 | 基线 | 有效性 |
|---|---|---|
| IHR | `2a360d0` | Yes |
| ATR-RUN-001 | `2a360d0` 对应工作树 | Yes（仅其范围） |
| HVR agent-assisted 页面 | 配置版本 191；代码观察树提交为 `2a360d0` | Partial；不构成人类 HVR |

## 12. Definition of Done Assessment

| Done Criterion | 状态 | 缺口 |
|---|---|---|
| 字号、颜色、字体、已测间距与无边框样式 | PARTIAL | H3/Label/Value 等不存在 |
| 卡片结构、字段分离、明细摘要 | BLOCKED | `rendered_text` 单节点；依 §17 停止 |
| Query Understanding 响应 Count | NOT SATISFIED | 未实现 “About X results” |
| Workspace 七区顺序和三个默认收缩区 | SATISFIED（agent observation） | 正式用户 HVR 仍缺 |
| 分页行为和浏览器矩阵 | NOT RUN | 缺实际分页控件场景与多浏览器 |
| CC-016/CC-015/CC-014 适用回归及 HVR | BLOCKED | 缺完整回归与正式 HVR |
| IHR/ATR/HVR/FR 证据与 Strict Closure | NOT SATISFIED | 证据文件齐备，义务未全部满足 |

## 13. Final Closure Determination

**Final Closure Status: NOT SATISFIED**

本轮视觉/布局已交付，且用户明确批准以带例外方式行政收口、提交和推送。严格 CC-017 子目标仍未满足：Count 展示缺失，卡片结构目标因 §17 停止，正式 HVR/分页/浏览器矩阵不完整。此结论不撤销用户的行政处置，也不把它改写为契约完成。

## 14. Handoff to Human Review

Closure Assessment Complete: Yes
Human Review Required: Yes

当前提交保留已实现范围和未完成项。若后续要求严格达成 CC-017，应先按 §17 对结构化卡片数据接口取得正式决策，再实现剩余目标、补齐矩阵与 HVR，并更新本 FR。
