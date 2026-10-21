# FR — CC-OFFICE-M1-004 Odoo 请求模型与 Office 附件封装

## 0. 文档治理

本 FR 按冻结 CC 及当前 IHR/ATR/HVR 评估实现义务。负责人于 2026-10-21 明确批准关闭 CC；该治理决定没有改写自动化证据。本 FR 仍按三态规则给出 **NOT SATISFIED**，不把行政关闭解释为功能验收通过。

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE` |
| FR ID | `FR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE` |
| FR Version | `v1.0` |
| Closure Status | **NOT SATISFIED** |
| CC | [CC-OFFICE-M1-004](../../../context/intent/CC-OFFICE-M1-004.md) `v0.3 Frozen`，由负责人批准行政关闭 |
| IHR / ATR / HVR | [IHR](IHR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) / [ATR](ATR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) / [HVR](HVR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) |
| 模块 | `mymodules/office_engine_odoo/` |
| 当前代码基线 | `office_engine_odoo` 源码快照 SHA-256 `68ccb4809e03095aa66f415a079de7e5fae0a06e590eb5f9b3bfcc7a7e723f60`；基于 commit `ea45974f8f38444d5aff250833b8dcae7ff0f92f` 的工作树快照 |
| 评估人 / 日期 | Codex Agent / 2026-10-21 |

## 2. 最终基线

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC | `v0.3 Frozen` | 关闭义务的唯一来源；关闭决定由负责人直接授权 |
| SRS | `V1.0.0 Frozen` | 业务需求与验收语义 |
| DDD | N/A | 负责人确认 M1 不适用 |
| TDD | `V0.4 Frozen` | 技术约束与服务边界 |
| Implementation Plan | `V0.3 Frozen` | 阶段与依赖；本次未修改该冻结基线 |

## 3. 执行摘要

| 项 | 结论 |
|---|---|
| FR Closure Status | **NOT SATISFIED** |
| 负责人 CC 处置 | 已授权行政关闭本 CC；不表示技术义务均已满足 |
| CC-CHANGE | 8 项均有代码或测试证据，但成功交付关键义务未满足 |
| CC-PRESERVE | 部分有证据；成功路径相关保留要求未验证 |
| 自动化验证 | **NOT SATISFIED** — ATR 含成功链路 FAIL、BLOCKED 和 NOT RUN |
| 人工验证 | N/A — 冻结 CC 未要求 UI 场景；N/A 不等于 PASS |
| 未批准偏离 | 未发现代码偏离；负责人行政关闭不改变技术基线 |
| 阻塞性功能缺口 | Odoo spawn 子进程不能导入 `odoo.addons.office_core`，因此真实成功渲染/交付未通过 |
| 证据基线 | 部分有效；可绑定当前 Addon 快照；受阻/缺失项不因此变成通过 |

## 4. Coding Contract Closure Matrix

| CC 义务 | 证据 | 结果 | 说明 |
|---|---|---|---|
| CC-CHANGE-001：最小请求模型、状态和 owner ACL | IHR-003；ATR-TEST-001—003/013 | PARTIAL | 模块安装/升级、基础字段和 owner 隔离有证据；完整状态与成功生命周期未闭环 |
| CC-CHANGE-002：当前用户授权附件快照并调用核心 | IHR-003；ATR-RUN-004/005 | NOT SATISFIED | 不支持格式拒绝通过；受支持文件成功路径被 spawn 导入错误阻断 |
| CC-CHANGE-003：显式 Mapping Plan 校验与传递 | ATR-TEST-006 | BLOCKED | 未验证真实请求经包装层进入核心；无 LLM/业务查询边界已由静态/代码检查部分支持 |
| CC-CHANGE-004：回读 PASS 后结果附件交付 | ATR-TEST-007/008/009 | NOT SATISFIED | `CC-TEST-007` 原生 FAIL；没有成功生成并关联输出附件的证据 |
| CC-CHANGE-005：事务外处理与短事务状态协调 | ATR-TEST-011 | BLOCKED | 成功路径未达，附件 create-to-commit 实测时间缺失 |
| CC-CHANGE-006：UUID 并发及结果幂等 | ATR-TEST-004/005 | NOT SATISFIED | 唯一约束拒绝重复键有部分证据；双 cursor 竞态及最终相同 output id 未运行 |
| CC-CHANGE-007：失败无可访问输出并遵守延迟 GC | ATR-RUN-005；CC-003 FR | PARTIAL | `.xls` 真实 ORM 拒绝后无输出；成功回滚/输出存储失败与本 CC GC 路径未验证 |
| CC-CHANGE-008：资源、稳定错误和失败安全 | ATR-RUN-004/005；TEST-010/015 | PARTIAL | 核心启动异常和不支持格式均 fail closed；超限和完整交付错误路径证据不足 |
| CC-TEST-001—016 自动化契约 | ATR §4—9 | NOT SATISFIED | 保留各测试原生结果；`CC-TEST-007` FAIL，005/010/012 NOT RUN，006/011 BLOCKED，其余多项 PARTIAL |
| HVR | HVR §2—4 | N/A | 本 CC 无 UI；没有声称人工验证通过 |

## 5. 实施与保留要求评估

Addon、请求模型、安全附件检查、ACL/Record Rule、事务协调及错误记录已实现。Odoo 安装/升级和 6 项 TransactionCase 运行通过；静态隔离扫描无 Odoo import；`.xls` 失败关闭路径也有真实 ORM 证据。

然而 CC-TEST-007 的成功路径探针证明 spawn 子进程反序列化时发生 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`。系统正确将请求标为失败且未关联输出，但这只证明错误路径 fail closed，不能证明文件写入、独立回读、附件成功交付、跨用户成功下载或输出幂等。故关键功能义务未满足。

## 6. 自动化与人工验证

- ATR 原生状态保留为：`PASS 5 / FAIL 1 / PARTIAL 5 / BLOCKED 2 / NOT RUN 3`；该汇总不把 PARTIAL 计为通过。
- 最新 Odoo 升级命令 exit 0，6 个 TransactionCase 通过；这是模型/权限子集证据，不覆盖 Office 成功路径。
- 静态隔离扫描通过（零匹配）；不支持 `.xls` 的失败路径通过。
- 成功文件路径探针失败；并发、资源边界、GC 回滚、成功附件事务耗时未取得完整证据。
- HVR 为 N/A，来源是冻结 CC 的人工验证适用性，不是浏览器或人工 PASS。

## 7. 偏离、停止条件与未决事项

| 事项 | 状态 | 影响 |
|---|---|---|
| spawn 子进程不能导入 Odoo 动态 addon namespace | Open / Blocking | 阻止成功渲染及输出附件交付；须另行批准技术基线并重新验证 |
| 两 cursor UUID 并发、资源上限及附件 GC 失败路径 | NOT RUN / BLOCKED | 不得宣称幂等、容量和失败事务完整符合 |
| TDD `OPEN-OFFICE-05` 生产预算、P0-A/B Partial | Open | 不得外推为生产容量或通用格式支持 |
| Implementation Plan V0.3 仍将 CC-004 列为 Draft | 未修订 | 本次不静默修改冻结计划；阶段映射需在后续计划影响复核中更新 |

没有发现可用未批准代码偏离。主要缺口是已执行失败和未运行验证，属于有证据的未满足，不属于无法判断的纯证据缺失。

## 8. Done Criteria Assessment

| CC §13 标准 | 评估 | 结果 |
|---|---|---|
| #1 冻结基线、Addon 路径、安装及资源策略证据 | 基线和路径可追溯；资源门禁不完整 | NOT SATISFIED |
| #2 延迟 GC 产品语义及产品失败路径 | 语义已确认；本 CC 的完整交付失败路径未验证 | NOT SATISFIED |
| #3 UUID 唯一约束和并发/最终结果幂等 | SQL 唯一约束有部分证据；并发和最终附件 ID未验证 | NOT SATISFIED |
| #4 请求/附件授权和跨用户访问 | owner ACL/附件拒绝部分通过；成功输出下载路径未验证 | NOT SATISFIED |
| #5 事务外处理及 create-to-commit 计时 | 成功附件创建路径未达到 | NOT SATISFIED |
| #6 回读 PASS 后仅创建结果附件，失败无结果 | 失败无输出样例通过；成功准入测试 FAIL | NOT SATISFIED |
| #7 资源与错误/清理证据 | 仅部分失败错误有证据；预算、GC 等缺失 | NOT SATISFIED |
| #8 PRESERVE 与 TEST 均有当前结果、AC 不误标 | 结果有记录但多项失败/缺失 | NOT SATISFIED |
| #9 IHR/ATR/HVR/FR 完整且 FR SATISFIED | 报告齐备；FR 按证据为 NOT SATISFIED | NOT SATISFIED |
| #10 纯 Python 自动静态扫描零匹配 | ATR-RUN-003 PASS | SATISFIED |

## 9. 最终关闭评估

```text
Final FR Closure Status: NOT SATISFIED
Owner Contract Disposition: CLOSED BY OWNER on 2026-10-21
Basis:
- The owner explicitly authorized CC-OFFICE-M1-004 closure.
- The authorization does not change ATR statuses or establish a successful render/delivery path.
- CC-TEST-007 is FAIL; key tests remain BLOCKED / NOT RUN / PARTIAL.
- Office generation and output attachment delivery are not verified or ready for user use.

This is an owner-directed administrative contract closure with an open functional gap.
It is not a SATISFIED FR, Phase 4 PASS, M1 completion, merge/release approval, or SRS acceptance.
```

## 10. 后续处理

在任何聊天集成或用户可用文件生成前，需建立单独的批准技术变更，解决 spawn 子进程对纯 Python Office 包的导入方式；随后重新运行真实 Odoo ORM 成功渲染、verify、附件提交/读取、并发 UUID、资源限制及失败回滚测试。完成后更新对应 ATR/IHR，并按受影响的冻结计划完成影响复核和阶段追溯。不得沿用本 FR 将后续证据预先标记通过。

## 附录 — 证据索引

| 证据 | 引用 |
|---|---|
| Frozen CC | [CC-OFFICE-M1-004](../../../context/intent/CC-OFFICE-M1-004.md) |
| 实施历史 | [IHR](IHR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) |
| 自动化验证 | [ATR](ATR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) |
| 人工验证适用性 | [HVR](HVR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) |
| 实现 | `mymodules/office_engine_odoo/` |

## 附录 — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v1.0 | 2026-10-21 | NOT SATISFIED | 记录 CC 证据评估和负责人行政关闭决定；不将失败/缺失项改写为 PASS。 |
