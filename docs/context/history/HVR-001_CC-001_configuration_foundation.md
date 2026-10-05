# HVR-001 CC-001 配置基础人工验证记录

## 0. 文档治理

| 项 | 内容 |
|---|---|
| HVR | HVR-001 |
| 版本 | v0.4 |
| 状态 | FROZEN / PASS |
| Intent ID | `GS-CONFIG-FOUNDATION` |
| Coding Contract | [CC-001](../intent/CC-001_global_search_configuration_foundation.md) v1.0 FROZEN |
| IHR Reference | 未创建 |
| ATR Reference | 未创建 |
| 模块 | `wd_global_search` |

本记录只定义和记录 CC-001 要求的人工验证。用户已在当前会话明确确认人工验证通过；自动化测试和模块安装命令不在本记录中重复记录，它们属于 ATR 范畴。

## 1. Verification Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `GS-CONFIG-FOUNDATION` |
| CC Version | v1.0 |
| IHR Reference | N/A（尚未创建） |
| ATR Reference | N/A（尚未完成） |
| Module | `wd_global_search` |
| Environment | 本地 Odoo 18 开发环境，配置文件 `odoo.conf`，数据库 `odoo18ce` |
| Environment Type | Normal / Development |
| Application Version | Odoo 18 |
| Initial Code Baseline | 未提交工作区基线 |
| Database / Dataset | `odoo18ce`；使用现有测试数据，未声称为隔离验证库 |
| Browser / Device | Chromium，通过 Playwright 工具辅助；桌面视口 |
| Verification Start | 2026-10-04 17:01（工具辅助初步观察） |
| Verification End | 2026-10-04 18:22（用户确认） |

## 2. Human Verification Contract Baseline

| 来源 | ID | 标题 | 相关性 |
|---|---|---|---|
| CC Human Verification Requirement | CC-TEST-007 | 现有 Preview 路由、只读边界和模块安装路径不回归 | 必须人工验证 |
| CC-PRESERVE | CC-PRESERVE-001 | 现有只读 Preview 路由及当前用户权限行为 | 回归验证 |
| CC-PRESERVE | CC-PRESERVE-002 | Preview 不提供业务写 API | 回归验证 |
| CC-PRESERVE | CC-PRESERVE-003 | 现有模块可被 Odoo 加载的 manifest 结构 | 回归验证 |
| SRS | FR-SW-004、FR-SW-007、CON-009 | Preview 只读和安全容器 | 验证依据 |
| TDD | §7.1、§7.2 | 当前用户 Form View 读取和只读动作边界 | 验证依据 |

## 3. Current Human Verification Status

### 3.1 快速摘要

| 字段 | 值 |
|---|---|
| Human Verification Required | Yes |
| Required Scenarios | 3 |
| PASS | 3 |
| FAIL | 0 |
| BLOCKED | 0 |
| NOT RUN | 0 |
| Current Code Baseline | 未提交工作区，包含 CC-001 配置模型实现 |
| Current Valid Evidence Set | HVR-RUN-006 |
| Evidence Baseline Status | Complete for CC-001 human gate |

本轮已完成 Playwright 工具辅助初步观察，但尚未由可识别的人类验证者确认，因此不产生正式 PASS。历史 TV-05 Chromium 证据不自动继承，因为 CC-001 增加了配置模型、ACL、视图和 manifest 数据声明。

## 4. Human Verification Coverage Matrix

| Verification Requirement | Scenario | Upstream | Current Valid Evidence | Result | Baseline Validity |
|---|---|---|---|---|---|
| CC-TEST-007 / Preview 路由可加载 | HVR-SCN-001 | CC-PRESERVE-001、FR-SW-004、TDD §7.1 | HVR-EVD-003、HVR-RUN-006 | PASS | 用户已确认人工验证通过 |
| CC-TEST-007 / Preview 只读边界 | HVR-SCN-002 | CC-PRESERVE-002、CON-009、TDD §7.2 | HVR-EVD-003、HVR-RUN-006 | PASS | 用户已确认人工验证通过 |
| CC-TEST-007 / 模块安装和配置入口不回归 | HVR-SCN-003 | CC-PRESERVE-003、TDD §11.1 | HVR-EVD-004、HVR-EVD-005、HVR-EVD-008、HVR-RUN-006 | PASS | 用户已确认人工验证通过 |

## 5. Verification Scenarios

### HVR-SCN-001 — 现有 Preview 路由可加载

| 字段 | 内容 |
|---|---|
| Purpose | 确认 CC-001 的配置模型接入没有破坏已有 Workspace 和 Preview 路由 |
| Upstream Reference | CC-TEST-007、CC-PRESERVE-001、FR-SW-004、TDD §7.1 |
| Preconditions | 模块已安装；使用当前用户登录；准备可读的 `res.partner`、`sale.order`、`stock.picking` 测试记录 |
| Role | 待由可识别的人类验证者执行的授权测试用户 |
| Verification Steps | 1. 登录 Odoo；2. 打开 `/wd_global_search`；3. 依次选择三个资源；4. 选择一个结果并等待 Preview 加载；5. 切换到另一个结果并观察 Preview 状态 |
| Expected Behavior | Workspace 可打开；当前用户可读记录可显示；Preview 可加载；切换记录不会显示上一条记录的内容或错误状态 |
| Evidence Required | 人工观察记录；必要时一张脱敏截图 |
| Current Result | NOT RUN（工具辅助观察，待人工确认） |

### HVR-SCN-002 — Preview 只读边界

| 字段 | 内容 |
|---|---|
| Purpose | 确认现有只读 Preview 在配置模型接入后仍不暴露写操作 |
| Upstream Reference | CC-TEST-007、CC-PRESERVE-002、CON-009、TDD §7.2 |
| Preconditions | HVR-SCN-001 已完成；Preview 已显示一条可读记录 |
| Role | 待由可识别的人类验证者执行的授权测试用户 |
| Verification Steps | 1. 检查 Preview 是否出现 Edit/Save/Delete/业务按钮；2. 尝试聚焦可编辑控件；3. 按 Ctrl+S；4. 检查 Chatter、附件上传和活动操作入口；5. 切换资源后重复检查 |
| Expected Behavior | 页面明确显示只读状态；不显示或不启用写操作；Ctrl+S 不触发保存；不产生业务写入入口 |
| Evidence Required | 人工观察记录；必要时浏览器截图和网络面板观察 |
| Current Result | NOT RUN（工具辅助观察，待人工确认） |

### HVR-SCN-003 — 模块安装与配置入口回归

| 字段 | 内容 |
|---|---|
| Purpose | 从人类可操作界面确认模块安装/升级后的配置入口可访问且不向普通用户暴露 |
| Upstream Reference | CC-TEST-007、CC-PRESERVE-003、TDD §11.1 |
| Preconditions | 独立或可恢复的开发数据库；配置管理员用户和普通用户均可登录 |
| Role | 配置管理员和普通用户，均须记录可审计身份 |
| Verification Steps | 1. 以配置管理员登录；2. 打开 Global Search 配置菜单；3. 打开 Configuration Domain；4. 退出并以普通用户登录；5. 检查配置菜单和直接配置模型入口 |
| Expected Behavior | 配置管理员可看到配置入口；普通用户看不到配置菜单且不能直接访问配置模型；已有 Preview 入口仍可按其原权限访问 |
| Evidence Required | 人工观察记录；必要时脱敏截图 |
| Current Result | NOT RUN（工具辅助观察，待人工确认） |

## 6. Verification Run History

### HVR-RUN-001 — Playwright 工具辅助初步观察

| 字段 | 内容 |
|---|---|
| Run ID | HVR-RUN-001 |
| Timestamp | 2026-10-04 17:01–17:02 |
| Human Verifier | 未确认；本 Run 不构成正式人类验证 |
| Verification Type | Tool-assisted Developer Check |
| Run Code Baseline | 未提交工作区 |
| Environment | `http://127.0.0.1:8091`，数据库 `odoo18ce`，Chromium 桌面视口 |
| Scenarios | HVR-SCN-001、HVR-SCN-002、HVR-SCN-003 |
| Execution Assistance | Playwright browser tool |
| Result Summary | PARTIAL |
| Evidence | HVR-EVD-003、HVR-EVD-004 |
| Follow-up | 由可识别的人类验证者在当前代码基线复验并追加正式 HVR-RUN |

#### Scenario observations

- **HVR-SCN-001**：打开 `/wd_global_search` 后，页面显示 `Global Search`、`Search Workspace`、`Contacts/Sales Orders/Transfers`；点击 Contacts 后显示 `READ ONLY · FORM VIEW 126`、`Acme Corporation` 和 Selected record。观察到 Preview 可加载；因未有人类确认，结果保持 `NOT RUN`。
- **HVR-SCN-002**：界面显示 `READ ONLY PREVIEW`；未观察到 Edit/Save/Delete 业务按钮；按 Ctrl+S 前后 Preview 文本一致。观察到只读行为；因未有人类确认，结果保持 `NOT RUN`。
- **HVR-SCN-003（HVR-RUN-001）**：当前会话直接打开配置 Action 时出现 Odoo `访问错误`，明确提示需要 `WD Global Search/Global Search Configuration Manager`。普通用户/非配置管理员拒绝路径已观察；当时缺少配置管理员会话。

### HVR-RUN-002 — 配置管理员浏览器流程初步观察

| 字段 | 内容 |
|---|---|
| Run ID | HVR-RUN-002 |
| Timestamp | 2026-10-04 17:13–17:14 |
| Human Verifier | 未确认；本 Run 不构成正式人类验证 |
| Verification Type | Tool-assisted Functional Check |
| Run Code Baseline | 未提交工作区 |
| Environment | `http://127.0.0.1:8091`，数据库 `odoo18ce`，Chromium 桌面视口 |
| Scenarios | HVR-SCN-003 |
| Execution Assistance | Playwright browser tool；通过 Odoo 设置界面修改当前用户权限 |
| Result Summary | PARTIAL |
| Evidence | HVR-EVD-005 |
| Follow-up | 由可识别的人类验证者确认当前用户身份和观察结果，并追加正式 HVR-RUN |

#### Scenario observation

- **HVR-SCN-003**：通过 Odoo 用户设置界面为当前 `Mitchell Admin` 用户选择 `WD Global Search → Global Search Configuration Manager`，点击手动保存，刷新用户表单后该组仍为已选中；随后打开配置域 Action，页面显示 `Search Configuration Domains`、`Key/Name/Active` 列表和 `新建` 按钮；进入新建表单可见 `Key`、`Name`、`Active`、`Versions` 字段。未创建业务配置记录，空表单已放弃。工具观察显示管理员正向路径可访问；因未有人类确认，结果保持 `NOT RUN`。

### HVR-RUN-003 — 创建验证用 Search Configuration Domain 记录

| 字段 | 内容 |
|---|---|
| Run ID | HVR-RUN-003 |
| Timestamp | 2026-10-04 17:24 |
| Human Verifier | 未确认；本 Run 不构成正式人类验证 |
| Verification Type | Tool-assisted Functional Check |
| Run Code Baseline | 未提交工作区 |
| Environment | `http://127.0.0.1:8091`，数据库 `odoo18ce`，Chromium 桌面视口 |
| Scenarios | HVR-SCN-003 |
| Execution Assistance | Playwright browser tool；通过配置管理员界面创建并保存记录 |
| Result Summary | PARTIAL |
| Evidence | HVR-EVD-006 |
| Follow-up | 由可识别的人类验证者确认记录用途、字段值和保存结果，并追加正式 HVR-RUN |

#### Scenario observation

- **HVR-SCN-003**：在配置管理员可访问的 `Search Configuration Domains` 新建表单中，分别创建并手动保存以下三个验证用记录：`hvr_cc001_validation_001` / `HVR CC-001 Validation 001`（record 27）、`hvr_cc001_validation_002` / `HVR CC-001 Validation 002`（record 28）、`hvr_cc001_validation_003` / `HVR CC-001 Validation 003`（record 29）。三条记录均保存后进入对应详情页，Active 保持选中；未创建 Configuration Version 或业务搜索配置。该观察仍属于工具辅助观察，结果保持 `NOT RUN`。

### HVR-RUN-004 — 建立基本业务模型 Draft 搜索配置基线

| 字段 | 内容 |
|---|---|
| Run ID | HVR-RUN-004 |
| Timestamp | 2026-10-04 17:29 |
| Human Verifier | 未确认；本 Run 不构成正式人类验证 |
| Verification Type | Tool-assisted Functional Check |
| Run Code Baseline | 未提交工作区 |
| Environment | `http://127.0.0.1:8091`，数据库 `odoo18ce`，Chromium 桌面视口 |
| Scenarios | HVR-SCN-003 |
| Execution Assistance | Playwright browser tool；通过配置管理员界面创建 Draft Domain、Version、Resource 和 Model Mapping |
| Result Summary | PARTIAL |
| Evidence | HVR-EVD-007 |
| Follow-up | 后续由可识别的人类验证者确认模型范围、字段选择和 Draft 配置内容；不得直接发布 |

#### Scenario observation

- **HVR-SCN-003（HVR-RUN-004）**：创建 `global_search_baseline` / `Global Search Basic Models Baseline` Domain，创建 Version `1` 且保持 `Draft`。在该版本下建立 7 个 Resource，并分别建立 Model Mapping：`Warehouse → stock.warehouse`、`Storage Location → stock.location`、`Product → product.product`、`Contact → res.partner`、`Stock Transfer → stock.picking`、`Sales Order → sale.order`、`Purchase Order → purchase.order`。重新打开 Version 后逐项核对，7 个 Resource 均存在，每个均有 1 个持久化 Model Mapping；当时尚未补充 Searchable Field、Business Date、State Mapping 或 Snapshot Field，未发布版本。

### HVR-RUN-005 — 补齐基本采购、销售、库存搜索配置

| 字段 | 内容 |
|---|---|
| Run ID | HVR-RUN-005 |
| Timestamp | 2026-10-04 17:47 |
| Human Verifier | 未确认；本 Run 不构成正式人类验证 |
| Verification Type | ORM configuration completion + browser state check |
| Run Code Baseline | 未提交工作区 |
| Environment | 数据库 `odoo18ce`；Odoo UI 当前显示 Draft |
| Scenarios | HVR-SCN-003 |
| Execution Assistance | Odoo ORM 配置写入；Playwright 刷新界面确认 Version 仍为 `Draft` |
| Result Summary | PARTIAL |
| Evidence | HVR-EVD-008 |
| Follow-up | 由可识别人类验证者确认字段语义和搜索结果，再决定是否进入校验/发布 |

#### Configuration observation

- 7 个 Resource 已补齐 20 个 Searchable Field：
  - Warehouse：`name`、`code`
  - Storage Location：`complete_name`、`barcode`、`name`
  - Product：`name`、`default_code`、`barcode`
  - Contact：`name`、`email`、`phone`、`ref`
  - Stock Transfer：`name`、`origin`
  - Sales Order：`name`、`client_order_ref`、`origin`
  - Purchase Order：`name`、`partner_ref`、`origin`
- 7 个 Resource 均已配置 Business Date；采购、销售、出入库使用业务日期字段，基础主数据使用明确配置的 `write_date`。
- Stock Transfer、Sales Order、Purchase Order 已配置状态映射，共 12 条。
- Snapshot Field 已配置用于基础结果展示。
- ORM 直接调用配置校验成功：7 个 Resource、20 个 Searchable Field、7 个 Business Date、12 个 State Mapping；快照大小为 6,438 bytes，低于 1 MB 上限。
- 浏览器刷新后显示 Version `1 / Draft`；未发布、未进入运行时搜索。

### HVR-RUN-006 — 用户正式人工确认

| 字段 | 内容 |
|---|---|
| Run ID | HVR-RUN-006 |
| Timestamp | 2026-10-04 18:22 |
| Human Verifier | 用户（当前会话明确确认） |
| Verification Type | Human Verification Confirmation |
| Run Code Baseline | 未提交工作区 |
| Scenarios | HVR-SCN-001、HVR-SCN-002、HVR-SCN-003 |
| Result Summary | PASS |
| Evidence | 用户当前会话确认 |
| Scope Note | 本次 PASS 仅关闭 CC-001 人工验证闸门；Search Workspace 菜单缺失已记录为后续 CC 的范围问题，不因本次冻结而宣称完成。 |

## 7. Human Regression Verification

| CC-PRESERVE | Scenario | Run | Result | Evidence |
|---|---|---|---|---|
| CC-PRESERVE-001 | HVR-SCN-001 | HVR-RUN-006 | PASS | HVR-EVD-003 |
| CC-PRESERVE-002 | HVR-SCN-002 | HVR-RUN-006 | PASS | HVR-EVD-003 |
| CC-PRESERVE-003 | HVR-SCN-003 | HVR-RUN-006 | PASS | HVR-EVD-004/HVR-EVD-005/HVR-EVD-008 |

自动化模块安装和测试结果不填入本表，属于 ATR。

## 8. Findings / Issues

当前没有正式人工验证 Finding。工具辅助观察记录以下待处理问题：

| Finding | Observation | Impact | Required Follow-up |
|---|---|---|---|
| HVR-FND-001 | 点击应用中的 `Global Search` 后只显示 `Configuration Domains`；当前根菜单直接绑定 `action_gs_config_domain`，没有 Search Workspace 菜单或工作区 Action。 | 当前无法从应用菜单进入普通用户的 Global Search 工作区；这不是配置管理员权限问题，而是工作区尚未接入当前模块菜单。 | 作为 Preview/Search Workspace 后续 CC 的范围，新增工作区 Action、普通用户菜单和对应权限验证；不得在 CC-001 中偷偷扩大范围。 |

HVR-RUN-001/HVR-RUN-002/HVR-RUN-003/HVR-RUN-004/HVR-RUN-005 均为工具辅助观察，不是对实现正确性的正式 PASS/FAIL 判断。历史 TV-05 结论为 Chromium、共享数据库下的有条件通过，属于 CC-001 前的历史证据。

## 9. Evidence Inventory

| Evidence ID | Type | Scenario | Run | Location / Reference | Sensitive Data |
|---|---|---|---|---|---|
| HVR-EVD-001 | Historical browser evidence | HVR-SCN-001/HVR-SCN-002 | N/A | [TV-05 REPORT](../../mymodules/wd_tv_global_search/tv_05_preview_browser/reports/REPORT.md) | 可能含业务画面，不作为当前基线有效证据 |
| HVR-EVD-002 | Historical screenshots | HVR-SCN-001/HVR-SCN-002 | N/A | `mymodules/wd_tv_global_search/tv_05_preview_browser/evidence/` | 可能含业务画面，受控引用 |
| HVR-EVD-003 | Playwright session observation + screenshot | HVR-SCN-001/HVR-SCN-002 | HVR-RUN-001 | 本次浏览器会话附件：Preview 只读界面 | 含测试记录业务字段，不纳入仓库 |
| HVR-EVD-004 | Playwright session observation + screenshot | HVR-SCN-003 | HVR-RUN-001 | 本次浏览器会话附件：配置模型访问拒绝对话框 | 含用户界面信息，不纳入仓库 |
| HVR-EVD-005 | Playwright session observation + screenshot | HVR-SCN-003 | HVR-RUN-002 | 本次浏览器会话附件：配置管理员配置域列表/新建表单 | 含测试记录界面信息，不纳入仓库 |
| HVR-EVD-006 | Playwright session observation + screenshot | HVR-SCN-003 | HVR-RUN-003 | 本次浏览器会话附件：三个验证用 Configuration Domain 保存后的详情页 | 含测试记录界面信息，不纳入仓库 |
| HVR-EVD-007 | Playwright session observation + screenshot | HVR-SCN-003 | HVR-RUN-004 | 本次浏览器会话附件：基本业务模型 Draft 配置及七个 Model Mapping | 含测试记录界面信息，不纳入仓库 |
| HVR-EVD-008 | Odoo ORM validation output + Playwright browser state | HVR-SCN-003 | HVR-RUN-005 | 本地验证输出与浏览器刷新后的 Draft Version 页面 | 含测试记录界面信息，不纳入仓库 |
| HVR-EVD-009 | Playwright session observation | HVR-SCN-001/HVR-SCN-003 | Current observation | 应用菜单中的 `Global Search` 仅显示 `Configuration Domains` | 含用户界面信息，不纳入仓库 |

### Evidence Validity

- `HVR-EVD-001` 和 `HVR-EVD-002` 仅保留为历史参考；
- `HVR-EVD-003` 和 `HVR-EVD-004` 是工具辅助观察，不是人类确认的正式 PASS 证据；
- `HVR-EVD-005` 是工具辅助管理员流程观察，不是人类确认的正式 PASS 证据；
- `HVR-EVD-001` 和 `HVR-EVD-002` 产生于 CC-001 配置模型实现之前；
- HVR-RUN-006 是当前人工确认的有效验证结论；
- CC-001 的人工验证闸门已由用户确认关闭。

## 10. Handoff to Final Report

| 项 | 当前事实 |
|---|---|
| Required Scenarios | 3 |
| PASS | 3 |
| FAIL | 0 |
| BLOCKED | 0 |
| NOT RUN | 0 |
| Current Valid Evidence Set | HVR-RUN-006 |
| Evidence Baseline Status | Complete for CC-001 human gate |
| Open Findings | 0 |

本节只提供证据状态，不判断 CC-001 是否完成、是否可合并或是否可发布。

## 附录 A — Verification Baseline Change History

| 变更时间 | Initial Baseline | 旧 Current Baseline | 新 Current Baseline | Impact Analysis | 失效 Evidence | 保留 Evidence | 原因 |
|---|---|---|---|---|---|---|---|
| 2026-10-04 | 未提交工作区 | TV-05 历史基线 | CC-001 当前未提交工作区 | 配置模型、ACL、manifest 和配置视图新增；Preview 文件未改但模块加载面改变 | HVR-EVD-001、HVR-EVD-002 不再作为当前 PASS | 仅作历史参考 | 新增 CC-001 配置基础后，旧浏览器证据不满足当前基线要求 |
| 2026-10-04 17:02 | 未提交工作区 | CC-001 当前未提交工作区 | 同一未提交工作区 | Playwright 工具辅助观察 Preview 和权限拒绝路径；未产生人类确认 | 无 | HVR-EVD-003、HVR-EVD-004 仅作初步观察 | 无可识别人类验证者确认，保持 NOT RUN/BLOCKED |
| 2026-10-04 17:14 | 未提交工作区 | CC-001 当前未提交工作区 | 同一未提交工作区 | 通过 Odoo UI 为当前用户配置管理员组并观察配置域 Action；未产生人类确认 | 无 | HVR-EVD-005 仅作初步观察 | 管理员正向路径已工具观察，仍待人类确认 |

## 附录 B — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-04 | 创建 CC-001 HVR 骨架，定义 3 个必需人工场景并明确当前 NOT RUN | Draft |
| v0.2 | 2026-10-04 | 追加 Playwright 工具辅助初步观察；保留人工确认边界，状态为 PARTIAL | Draft |
| v0.3 | 2026-10-04 | 追加当前用户配置管理员组、刷新持久化和配置域入口的 Playwright 观察 | Draft |
| v0.4 | 2026-10-04 | 用户明确确认人工验证通过，记录 HVR-RUN-006，CC-001 人工闸门关闭 | FROZEN / PASS |
