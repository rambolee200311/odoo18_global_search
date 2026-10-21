<!-- 使用 Coding/IHR 模板；与 CC 实施并行更新，只记录实际事实。 -->

# IHR — OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE

## 0. 文档治理

本 IHR 记录 CC-OFFICE-M1-004 的实际实现历史，不证明测试通过、不代表人工验收或 CC 关闭。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE` |
| CC 引用 | [CC-OFFICE-M1-004](../../../../context/intent/CC-OFFICE-M1-004.md)，`v0.3 Frozen` |
| SRS / TDD / Plan 基线 | SRS V1.0.0 Frozen；TDD V0.4 Frozen；Implementation Plan V0.3 Frozen |
| 模块 | `mymodules/office_engine_odoo/` |
| 实施负责人 | Codex Agent；负责人 2026-10-21 批准冻结并授权实施 |
| 开始 / 最后更新 | 2026-10-21 / 2026-10-21 |
| 当前实施状态 | Closed by owner disposition; functional success-path gap remains open |
| 开始时 Git 基线 | `ea45974f8f38444d5aff250833b8dcae7ff0f92f`；工作区有其他既存变更，未触碰/暂存 |

## 2. Coding Contract 基线

| 项 | 引用 |
|---|---|
| Scope / Change Boundary | CC §§3—4 |
| Required Behavior | CC-CHANGE-001—008 |
| Preservation | CC-PRESERVE-001—007 |
| Test Contract | CC-TEST-001—016 |
| Stop / Done Criteria | CC §§12—13 |

## 3. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC-CHANGE 落实进度 | 8 / 8 代码路径已建立；验收未闭环，关键成功链路受阻 |
| Preservation Impact | Partial；纯 Python 包未修改，Odoo spawn 子进程无法导入动态注册的 addon namespace |
| Deviation | Known blocker：需单独解决纯 Python 包在 Odoo multiprocessing spawn 子进程中的可导入性；本 CC 不擅自修改冻结核心 |
| Stop Condition | Yes — successful core invocation is blocked by the spawn import failure; dependent success-path work awaits a separate technical baseline |
| Open Issues | 3：spawn 导入阻塞；生产资源预算未确认；P0-A/B 仍 Partial |
| Revert | No |
| 当前状态 | In Progress — core success integration blocked |

## 4. 实施历史条目（仅追加）

### IHR-001

| 字段 | 值 |
|---|---|
| 时间 / 阶段 | 2026-10-21 / Runtime reconnaissance |
| Action | 普通 sandbox 下 Odoo shell 在 shutdown 时因 psutil 进程枚举权限失败；同一只读检查在获准开发环境 shell 成功。确认 `office_core` / `office_verify` 顶层 import 不可用，但 `odoo.addons.office_core` / `odoo.addons.office_verify` 可由 Odoo addon loader 加载。 |
| Files / Components | Odoo Runtime `odoo18ce`；两个纯 Python 包 |
| Contract / Upstream | CC-CHANGE-002/003；TDD V0.4 §§2—3 |
| Result / Deviation | Completed，仅只读调查；无 DB 副作用；None |
| Follow-up | Wrapper 使用 addon namespace，不改包、不加 sys.path hack。 |

### IHR-002

| 字段 | 值 |
|---|---|
| 时间 / 阶段 | 2026-10-21 / Implementation |
| Action | 建立 `office_engine_odoo` Addon、owner-only 请求模型/同步服务/附件保护及初始 ORM 测试；完整实现和验证继续中。 |
| Files / Components | `mymodules/office_engine_odoo/` |
| Contract / Upstream | CC-CHANGE-001—008；TDD V0.4 §§5—7；Plan V0.3 Phase 4 |
| Result / Deviation | Partial / None identified |
| Follow-up | 完成 ORM/ACL/事务实现、运行 ATR 并更新本 IHR。 |

### IHR-003

| 字段 | 值 |
|---|---|
| 时间 / 阶段 | 2026-10-21 / ORM 实施与运行验证 |
| Action | 完成请求模型、唯一约束、owner 规则、附件私有/不可变保护、同步服务及 6 项 ORM 测试。运行模块安装/升级和失败格式探针；发现 Odoo `spawn` 子进程反序列化 `odoo.addons.office_core.service` 时无法解析动态 addon 路径，成功文件处理链路未通过。修正附件权限验证，改用 `ir.attachment.check('read')`；移除请求模型自定义无条件删除拒绝，依赖 ACL 限制普通用户，保留管理 ORM 清理路径。 |
| Files / Components | `mymodules/office_engine_odoo/`；`odoo18ce`；冻结 `office_core` / `office_verify` |
| Contract / Upstream | CC-CHANGE-001—008；CC-TEST-001—016；TDD V0.4 §§5—7 |
| Result / Deviation | ORM 模块升级与 6 项测试 PASS；CC-TEST-016 静态扫描 PASS（零匹配、退出码 1）；不支持 `.xls` 失败路径 PASS；成功处理集成 FAIL（spawn 导入错误）；无纯 Python 核心改动 |
| Follow-up | 暂停成功输出/附件事务/并发闭环。需建立独立技术变更基线解决 spawn 子进程包加载，再回到本 CC 重跑成功链路及关联门禁。 |

### IHR-004

| 字段 | 值 |
|---|---|
| 时间 / 阶段 | 2026-10-21 / 环境恢复与清理 |
| Action | 通过 ORM 删除唯一标记 `CC004-SMOKE-*` 合成附件；失败格式场景的请求/源附件亦使用 ORM 清理。按 `venv` + `odoo.conf` 恢复服务，升级后通过本地 HTTP 探测返回 200。未直接删除 filestore 文件。 |
| Files / Components | `odoo18ce` ORM；Odoo 8091 服务 |
| Contract / Upstream | CC-TEST-009/012 环境纪律；用户既有开发环境配置 |
| Result / Deviation | 清理 PASS；服务恢复 PASS；无未清理的本轮合成请求/附件 |
| Follow-up | 继续保留生产 GC 延迟语义，不运行全局 GC。 |

### IHR-005

| 字段 | 值 |
|---|---|
| 时间 / 阶段 | 2026-10-21 / 负责人关闭处置 |
| Action | 负责人明确批准关闭 CC-OFFICE-M1-004。按 ATR 保留成功生成链路失败和未执行测试的原始状态；未更改核心包、未声称输出生成可用，也未把 Phase 4 标为通过。 |
| Files / Components | 本 IHR、对应 ATR/HVR/FR 与 CC；`mymodules/office_engine_odoo/` |
| Contract / Upstream | CC-OFFICE-M1-004 v0.3 Frozen；TDD V0.4 Frozen；Implementation Plan V0.3 Frozen |
| Result / Deviation | 行政关闭获负责人授权；FR 结论为 NOT SATISFIED，功能缺口仍开放。此次关闭处置不修改冻结计划基线。 |
| Follow-up | 修复 spawn 子进程纯 Python 包可导入性，重新运行成功路径、输出交付、并发和事务测试；更新计划基线后再推进依赖阶段。 |

## 5. 实际变更清单（当前快照）

| 文件/组件 | 目的 | 追溯 |
|---|---|---|
| Addon manifest、初始化 | 自有 Odoo 模块及明确依赖 | CC-CHANGE-001/002 |
| `models/office_document_request.py` | 状态、UUID 唯一性、当前用户授权、同步 core/verify、附件持久化 | CC-CHANGE-001—008 |
| `models/ir_attachment.py` | 保护已生成附件的私有性/不可变性 | CC-CHANGE-004/007 |
| `security/**`、`tests/**` | ACL、owner rule、ORM 自动化测试 | CC-TEST-001—016 |
| 本目录 IHR/ATR/HVR | 实施与验证证据 | CC §13 |

## 6. 偏离与停止条件

| 事件 | 状态 | 处置 |
|---|---|---|
| Sandbox shell 的 psutil 权限错误 | Resolved | 获准 shell 只读重跑成功；失败尝试未执行 ORM 查询；ATR 保留两次状态。 |
| spawn 子进程不能导入动态注册的 `odoo.addons.office_core` | Open / Blocking | 成功路径实际失败；不更改冻结纯 Python 包，也不以 monkeypatch、fork 或扩大资源预算绕过。需单独技术基线决定包装/启动方式。 |
| 未批准 TDD 偏离 | None identified | 持续核对 CC 与冻结基线。 |

## 7. 遗留问题与后续

| ID | 描述 | 影响/处理 |
|---|---|---|
| OPEN-001 | TDD `OPEN-OFFICE-05` 的生产资源预算未关闭 | 限制文件/展开/时间/内存；超限拒绝；不宣称生产容量通过。 |
| OPEN-002 | P0-A/B 仍 Partial | 只允许既有 `.xlsx/.docx` 基础能力白名单；其他能力拒绝。 |
| OPEN-003 | Odoo spawn 子进程导入 `office_core` 失败 | 阻塞成功处理、输出附件事务与并发测试；需要独立技术方案/CC，未经批准不得更改冻结包。 |

## 8. 移交摘要

ORM 自动化与失败格式路径已有证据；成功 Office 处理链路因 spawn 导入错误失败。负责人随后批准本 CC 行政关闭，但 FR 保留 NOT SATISFIED；本次提交/推送仅纳入 CC-OFFICE-M1-004 和本轮 CC-005 Draft 所需文件，工作区其他变更未暂存。

## 附录 B — 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1 | 2026-10-21 | 初始基线及 runtime reconnaissance 事实。 |
| 0.2 | 2026-10-21 | 追加 ORM/静态/失败路径结果，记录 spawn 集成阻塞、附件专用权限检查修正、ORM 清理和服务恢复。 |
