# 盲盘（Blind Stock Count）技术设计说明书（TDD）

## 文档状态

**Draft / Blocked — 待 SRS 版本基线确认**

用户指定的上游基线为 **SRS v1.8**，但主工作区现有
[SRS_blind_count.md](/Users/lijianqiang/Documents/odoo18_blind_count/docs/requirement/SRS_blind_count.md)
文件头部标识为 **v1.7**。本 TDD 因此不能宣称已经基于仓库冻结的 v1.8 完成。

本文档按以下事实起草：

- 当前仓库 SRS 文件内容；
- 用户提供的 SRS v1.8 版本声明；
- TV-01 至 TV-20 报告；
- Odoo 18 Community Edition 源码行为。

在 SRS 版本差异解决前，本文档不得作为最终 Coding Contract 的唯一授权基线。

---

# 1. 概述

## 1.1 目的

本文档定义 Odoo 18 Community Edition 盲盘模块的技术设计，覆盖：

```text
工作包
→ PDA 盲盘
→ 可选 PDA 复核
→ 主管审核
→ 库存清除
→ 按审核结果重新入库
→ 分步回滚
```

本文档将 SRS 的业务要求转化为：

- Odoo ORM 模型；
- 状态机；
- 事务和库存移动边界；
- 并发约束；
- OWL/PDA UI 契约；
- 权限和安全边界；
- 自动化测试和 E2E 验证策略。

本文档只做技术设计，不实现生产代码。

## 1.2 范围

### 在范围内

- 工作包和产品大类关联；
- 按货位创建盲盘单；
- PDA 盲盘扫描；
- Lot、Serial、无追踪产品；
- 批量 Serial 扫描；
- PDA 撤销上一条；
- 可选 PDA 复核；
- 主管审核；
- Step 1 库存清除；
- Step 2 按审核结果入库；
- Step 1/Step 2 独立回滚；
- Recount；
- 角色、ACL、记录规则和路由保护；
- Python ORM、OWL/QUnit、并发和 Playwright E2E 测试。

### 不在范围内

- 标准 Odoo 盘点流程；
- 库位主数据配置；
- 产品主数据维护；
- PDA 硬件驱动；
- 客户合同和计费；
- 离线盘点；
- 通过独立消息队列、Worker 或微服务执行库存重建。

对应 SRS：§1.2、§2.5、§4.3.13。

## 1.3 输入

| 输入 | 版本/状态 | 用途 |
|---|---|---|
| SRS | 用户声明 v1.8；仓库文件当前 v1.7 | 业务和验收权威 |
| TV-01 | 已完成 | 库存清除 |
| TV-02 | 已完成 | Lot/SN 匹配或创建 |
| TV-03 | 已完成 | 按货位入库 |
| TV-04 | 已完成 | 事务边界 |
| TV-05 | 已完成 | 反向库存移动 |
| TV-06 | 已完成 | 多次回滚和重执行 |
| TV-07 | 已完成 | Serial 唯一性查询 |
| TV-08 | 已完成 | 并发 Serial |
| TV-09 | 已完成 | Serial 索引和性能 |
| TV-10 至 TV-15 | 已完成 | PDA OWL、路由和扫码 |
| TV-16 至 TV-17 | 已完成 | PDA 复核 |
| TV-18 至 TV-20 | 已完成 | 状态机和并发约束 |
| Odoo 18 CE 源码 | 18.0 | ORM、库存和 Web 框架行为 |

## 1.4 输出：设计决策清单

| ID | 设计决策 | 追溯 |
|---|---|---|
| TD-001 | 盲盘事实不保存账面数量、库存移动、预留或现有 SN 状态 | SRS C1-C5、P1-P3、AC1-AC6 |
| TD-002 | 库存清除和重建统一通过 `stock.move`/`stock.move.line` | TV-01、TV-03、SRS C15、AC21-AC24 |
| TD-003 | `stock.quant.quantity` 不作为业务写入口 | TV-01 |
| TD-004 | `stock.return.picking` 不作为库存调整回滚入口 | TV-05 |
| TD-005 | 回滚由项目业务方法创建关联的反向 move | TV-05、SRS C20-C24 |
| TD-006 | Serial 唯一性由后端查询 + 数据库并发约束共同保证 | TV-07、TV-08、TV-09 |
| TD-007 | Lot/SN 主数据仅在 Step 2 匹配或创建 | SRS C3-C4、AC15、TV-02 |
| TD-008 | 工作包、盲盘单、复核、处理分为独立模型和业务动作 | SRS P4、AC4、AC70 |
| TD-009 | Step 1 与 Step 2 是独立事务，Step 2 依赖 Step 1 成功 | SRS C18-C22、TV-04 |
| TD-010 | PDA 使用独立 `auth='user'` 路由和 OWL 状态机 | SRS C7、TV-10、TV-15 |
| TD-011 | 产品条码查询缓存仅限当前工作包，不能替代后端校验 | SRS R9-R15、TV-12 |
| TD-012 | Recount 创建新轮次，历史盲盘单保持只读 | SRS C32-C34、TV-19、TV-20 |
| TD-013 | 不引入独立 Worker、消息队列或额外持久化层 | Odoo Engineering Guidelines、SRS 范围 |

---

# 2. 设计约束

## 2.1 来自 SRS 的约束

### 数据隔离

- 盲盘阶段禁止读写库存数量、余额、库存移动、预留和现有序列号状态；
- 批次和序列号只保存为 `lot_name` 文本；
- 盲盘阶段不查询、不创建 `stock.lot`；
- PDA 和后台盲盘界面不得显示账面数量、差异数量或预期 Lot/SN。

对应：SRS C1-C5、P1-P3、AC1-AC6、AC15。

### 范围和扫描

- 一个工作包只对应一个产品大类；
- 一个盲盘单只对应一个货位；
- 扫描顺序固定为货位、托盘、产品、Lot/SN 或数量；
- 产品条码查不到或超出工作包范围必须阻断；
- Serial 固定数量为 1；
- Lot 和无追踪产品允许数量累加；
- 支持空盘和撤销上一条。

对应：SRS C8-C14、C25-C29、C35、R1-R30、AC7-AC20、AC67。

### 处理和回滚

- Step 1 清除，Step 2 入库；
- 两步独立且各自可回滚；
- Step 1 回滚前必须先回滚 Step 2；
- 回滚不删除原库存移动；
- 回滚记录人、时间和原因；
- 只有主管或管理员可回滚。

对应：SRS C15-C24、C30-C34、AC21-AC32、AC56-AC65。

## 2.2 来自 TV 的约束

- 只能通过 Odoo 原生库存移动更新库存，不能直接改 quant 数量（TV-01、TV-03）；
- `stock.return.picking` 只适合有 picking 的流程，不适合作为库存调整移动的通用回滚（TV-05）；
- 反向 move 必须保留每条原始 move line 的产品、数量、UoM、Lot/SN、owner、货位等维度（TV-05）；
- 多次回滚会累积审计移动，不能以“移动数量不增加”定义幂等（TV-06）；
- Serial 唯一性不能只依赖 ORM `search()` + `create()`（TV-07、TV-08）；
- 性能在当前无盲盘明细模型时不能宣称已通过，必须在真实规模数据上验证（TV-09）；
- 前端状态机、焦点和缓存不能替代后端校验（TV-10 至 TV-15）；
- 复核异常记录不阻断，但货位不一致仍阻断（TV-16、TV-17）；
- 状态、轮次和一货位一轮一单需要数据库并发保护（TV-18 至 TV-20）。

## 2.3 来自 Odoo 18 CE 的约束

- 业务模型使用 Odoo ORM；
- 库存写入必须通过 `stock.move`/`stock.move.line` 和 `_action_done()`；
- `stock.quant` 的 `inventory_quantity`/`action_apply_inventory()` 是原生库存调整入口；
- `stock.lot` 的 `name` 和 `product_id` 是必填语义；
- Odoo 的标准 `stock.return.picking` 需要 `stock.picking`；
- Controller 的 `auth='user'` 只表示登录认证，不代替模型 ACL 和记录规则；
- Odoo 事务由请求/测试事务管理，业务方法禁止主动 `commit()`；
- 不修改 Odoo 官方核心或官方模块；
- 不使用裸 SQL 绕过 ORM 进行业务数据读写；
- 数据库索引如需要自定义，必须通过模块升级路径可重复创建，且不能隐藏业务约束。

---

# 3. 模型设计

## 3.1 模型总览

建议自定义模块名称：`blind_count`。

| 模型 | 技术模型名 | 责任 |
|---|---|---|
| 工作包 | `blind.count.work.package` | 顶层范围和完成状态 |
| 盲盘单 | `blind.count` | 单货位、单轮次的盲盘事实 |
| 盲盘明细 | `blind.count.line` | 产品、托盘、Lot/SN 文本和数量 |
| 复核单 | `blind.count.review` | 可选复核任务和结论 |
| 复核明细 | `blind.count.review.line` | 复核输入、匹配和异常 |
| 处理单 | `blind.count.processing` | 主管审核和重建总控 |
| 处理明细 | `blind.count.processing.line` | 冻结后的入库事实 |
| 清除记录 | `blind.count.clear` | Step 1 执行、move 和回滚历史 |
| 入库记录 | `blind.count.restock` | Step 2 执行、move 和回滚历史 |

处理单不是新增业务流程，而是 SRS §5.4 所要求的处理模块父对象；清除记录和入库记录用于避免把两种不同的可回滚步骤压缩为不透明字段。

## 3.2 工作包：`blind.count.work.package`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `name` | Char | 是 | `ir.sequence` | 工作包号 |
| `date` | Datetime | 是 | `fields.Datetime.now` | 创建/作业时间 |
| `product_categ_id` | Many2one `product.category` | 是 | 用户 | 产品大类 |
| `partner_id` | Many2one `res.partner` | 是 | related | 从产品大类/业务主数据带出，只读；具体来源需 CC 决定 |
| `state` | Selection | 是 | `draft` | `draft/in_progress/done/cancel` |
| `user_id` | Many2one `res.users` | 是 | 当前用户 | 创建人 |
| `note` | Text | 否 | 空 | 备注 |
| `blind_count_ids` | One2many | 否 | 空 | 盲盘单 |
| `processing_ids` | One2many | 否 | 空 | 处理单 |
| `active` | Boolean | 是 | True | 非物理删除控制 |

约束：

- `product_categ_id` 一旦存在业务子单，不可修改；
- `done` 后禁止新增盲盘单；
- `done` 必须满足所有有效处理单完成；
- `cancel` 后禁止任何作业动作；
- 创建权限只给仓库主管和管理员。

## 3.3 盲盘单：`blind.count`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `name` | Char | 是 | `ir.sequence` | 盲盘单号 |
| `work_package_id` | Many2one | 是 | 用户/父单 | 工作包 |
| `product_categ_id` | Many2one | 是 | related/store | 从工作包带出，只读 |
| `partner_id` | Many2one | 是 | related/store | 从工作包带出，只读 |
| `location_id` | Many2one `stock.location` | 是 | 用户 | 盘点货位 |
| `round` | Integer | 是 | 1 | 盘点轮次，最小 1 |
| `state` | Selection | 是 | `draft` | `draft/counting/done/cancel` |
| `location_scanned` | Boolean | 是 | False | 是否扫描正确货位 |
| `requires_review` | Boolean | 是 | False | 是否需要复核 |
| `is_replaced` | Boolean | 是 | False | 是否被 Recount 替代 |
| `replaced_by_id` | Many2one `blind.count` | 否 | 空 | 替代单 |
| `source_recount_id` | Many2one `blind.count` | 否 | 空 | 来源单 |
| `operator_ids` | Many2many `res.users` | 否 | 空 | 参与盘点用户 |
| `note` | Text | 否 | 空 | 备注 |
| `line_ids` | One2many | 否 | 空 | 盲盘明细 |
| `completed_by_id` | Many2one `res.users` | 否 | 空 | 完成人 |
| `completed_at` | Datetime | 否 | 空 | 完成时间 |

约束：

- 工作包、产品大类、客户必须一致；
- 货位必须是可作业货位；
- `round >= 1`；
- 同一工作包、货位和轮次只允许一个有效进行中单据；
- `done`、`cancel` 或 `is_replaced` 后只读；
- 不能通过后台表单人工新增或编辑明细；
- 复核人不得是原盘点人。

对应：SRS F1.1-F1.9、C33-C34、AC16、AC43、AC52-AC55。

## 3.4 盲盘明细：`blind.count.line`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `blind_count_id` | Many2one | 是 | 当前单 | 所属盲盘单 |
| `product_id` | Many2one `product.product` | 是 | 扫描产品 | 只读来源事实 |
| `product_barcode` | Char | 否 | 产品条码 | 快照，不用于重新识别 |
| `package_code` | Char | 否 | PDA 输入 | 托盘文本，不关联 `stock.quant.package` |
| `lot_name` | Char | 否 | PDA 输入 | Lot/SN 文本，不关联 `stock.lot` |
| `quantity` | Float | 是 | Serial=1，其余=1 | 实盘数量 |
| `tracking` | Selection | 是 | 产品追踪方式快照 | `none/lot/serial` |
| `operator_id` | Many2one `res.users` | 是 | 当前用户 | 盘点人 |
| `scanned_at` | Datetime | 是 | 当前时间 | 盘点时间 |
| `scan_sequence` | Integer | 是 | 单内递增 | 撤销顺序 |
| `state` | Selection | 是 | `valid` | `valid/undone` |
| `undone_at` | Datetime | 否 | 空 | 撤销时间 |
| `undone_by_id` | Many2one `res.users` | 否 | 空 | 撤销人 |
| `note` | Text | 否 | 空 | 备注 |
| `serial_uniqueness_active` | Boolean | 是 | 由后端维护 | Serial 并发唯一性状态 |

禁止字段：

- 账面数量；
- 差异数量；
- 预期 Lot/SN；
- `stock.quant`、`stock.move`、`stock.lot` 关联；
- 库存预留；
- 当前库存状态。

约束：

- Serial 的 `quantity` 必须为 1；
- Lot/无追踪数量必须大于 0；
- 产品必须属于工作包产品大类；
- `lot_name` 只做文本存储；
- Serial 有效记录跨工作包、货位、托盘唯一；
- 同一盲盘单中 Lot 按产品、托盘、Lot 累加；
- 无追踪产品按产品、托盘累加；
- 撤销后释放 Serial 唯一性占用。

## 3.5 复核单：`blind.count.review`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `name` | Char | 是 | `ir.sequence` | 复核单号 |
| `blind_count_id` | Many2one | 是 | 用户选择 | 来源盲盘单 |
| `work_package_id` | Many2one | 是 | related/store | 工作包 |
| `product_categ_id` | Many2one | 是 | related/store | 产品大类 |
| `partner_id` | Many2one | 是 | related/store | 客户 |
| `location_id` | Many2one | 是 | related/store | 货位 |
| `round` | Integer | 是 | related/store | 轮次 |
| `state` | Selection | 是 | `draft` | `draft/counting/done` |
| `reviewer_id` | Many2one `res.users` | 是 | 当前用户 | 复核人 |
| `reviewed_at` | Datetime | 否 | 完成时 | 复核时间 |
| `conclusion` | Selection | 是 | `pending` | `pending/passed/failed/uncertain` |
| `conclusion_note` | Text | 否 | 空 | 结论备注 |
| `location_scanned` | Boolean | 是 | False | 货位校验 |
| `line_ids` | One2many | 否 | 空 | 复核明细 |

约束：

- 来源盲盘单必须 `done`；
- 复核人不能是任一原盘点人；
- 货位不匹配阻断；
- 复核结论完成后只读；
- 一个来源盲盘单的有效复核单原则上最多一个，具体重做策略属于未决问题。

## 3.6 复核明细：`blind.count.review.line`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `review_id` | Many2one | 是 | 当前复核单 | 所属复核 |
| `product_id` | Many2one | 否 | 扫描/匹配 | 不存在产品时为空 |
| `product_barcode` | Char | 否 | 输入 | 原始条码 |
| `package_code` | Char | 否 | 输入 | 原始托盘码 |
| `lot_name` | Char | 否 | 输入 | 原始 Lot/SN |
| `review_quantity` | Float | 否 | 输入 | 复核数量 |
| `blind_quantity` | Float | 否 | 匹配带出 | 仅用于复核结果显示 |
| `match_status` | Selection | 是 | `not_matched` | `matched/not_matched/out_of_scope/not_in_blind/not_covered` |
| `exception_type` | Selection | 否 | 空 | 异常类型 |
| `reviewed_at` | Datetime | 是 | 当前时间 | 复核时间 |
| `reviewer_id` | Many2one | 是 | 当前复核人 | 复核人 |
| `note` | Text | 否 | 空 | 异常备注 |

复核明细不修改 `blind.count.line`。

## 3.7 处理单：`blind.count.processing`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `name` | Char | 是 | `ir.sequence` | 处理单号 |
| `work_package_id` | Many2one | 是 | 来源盲盘单 | 工作包 |
| `blind_count_id` | Many2one | 是 | 来源盲盘单 | 有效来源盲盘单 |
| `product_categ_id` | Many2one | 是 | related/store | 产品大类 |
| `partner_id` | Many2one | 是 | related/store | 客户 |
| `location_id` | Many2one | 是 | related/store | 货位 |
| `round` | Integer | 是 | related/store | 轮次 |
| `state` | Selection | 是 | `draft` | `draft/review/approved/processing/done/cancel` |
| `is_valid` | Boolean | 是 | True | 是否有效处理单 |
| `review_required` | Boolean | 是 | 来源盲盘单 | 是否必须先复核 |
| `approved_by_id` | Many2one `res.users` | 否 | 审核时 | 主管审核人 |
| `approved_at` | Datetime | 否 | 审核时 | 审核时间 |
| `clear_state` | Selection | 是 | `pending` | `pending/done/rolled_back` |
| `restock_state` | Selection | 是 | `pending` | `pending/done/rolled_back` |
| `processing_line_ids` | One2many | 否 | 空 | 冻结处理明细 |
| `clear_record_ids` | One2many | 否 | 空 | 清除记录 |
| `restock_record_ids` | One2many | 否 | 空 | 入库记录 |

约束：

- 一个货位最终只能有一个有效处理单；
- 只有审核通过的盲盘单才能生成；
- `approved` 后处理明细冻结；
- Step 2 必须在 Step 1 `done` 后执行；
- Step 1 回滚前 Step 2 必须已回滚；
- 处理单 `done` 后禁止重新写入盲盘事实。

## 3.8 处理明细：`blind.count.processing.line`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `processing_id` | Many2one | 是 | 当前处理单 | 处理单 |
| `source_line_id` | Many2one | 是 | 盲盘明细 | 来源事实 |
| `product_id` | Many2one | 是 | 来源明细 | 产品 |
| `product_barcode` | Char | 否 | 来源快照 | 条码 |
| `package_code` | Char | 否 | 来源事实 | 不进入库存维度 |
| `lot_name` | Char | 否 | 来源事实 | 文本 |
| `quantity` | Float | 是 | 来源事实 | 实盘数量 |
| `lot_id` | Many2one `stock.lot` | 否 | Step 2 匹配/创建 | none 时为空 |
| `lot_match_state` | Selection | 是 | `pending` | `pending/matched/created/not_required` |
| `approval_state` | Selection | 是 | `pending` | `pending/approved/rejected` |
| `approval_note` | Text | 否 | 空 | 审核备注 |

`lot_id` 只能在处理阶段写入，不能回写盲盘明细。

## 3.9 清除记录：`blind.count.clear`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `processing_id` | Many2one | 是 | 当前处理单 | 处理单 |
| `state` | Selection | 是 | `pending` | `pending/done/rolled_back` |
| `scope_category_id` | Many2one | 是 | 工作包 | 产品大类 |
| `scope_location_ids` | Many2many | 是 | 有效货位集合 | 清除范围快照 |
| `move_ids` | Many2many `stock.move` | 否 | Step 1 | 原始清除移动 |
| `reverse_move_ids` | Many2many `stock.move` | 否 | 回滚时 | 反向移动 |
| `executed_by_id` | Many2one | 否 | 执行时 | 执行人 |
| `executed_at` | Datetime | 否 | 执行时 | 执行时间 |
| `rollback_by_id` | Many2one | 否 | 回滚时 | 回滚人 |
| `rollback_at` | Datetime | 否 | 回滚时 | 回滚时间 |
| `rollback_reason` | Text | 否 | 回滚时必填 | 回滚原因 |
| `operation_key` | Char | 是 | 服务器生成 | 幂等键 |

## 3.10 入库记录：`blind.count.restock`

| 字段 | 类型 | 必填 | 默认/来源 | 说明 |
|---|---|---:|---|---|
| `processing_id` | Many2one | 是 | 当前处理单 | 处理单 |
| `state` | Selection | 是 | `pending` | `pending/done/rolled_back` |
| `move_ids` | Many2many `stock.move` | 否 | Step 2 | 原始入库移动 |
| `reverse_move_ids` | Many2many `stock.move` | 否 | 回滚时 | 反向移动 |
| `executed_by_id` | Many2one | 否 | 执行时 | 执行人 |
| `executed_at` | Datetime | 否 | 执行时 | 执行时间 |
| `rollback_by_id` | Many2one | 否 | 回滚时 | 回滚人 |
| `rollback_at` | Datetime | 否 | 回滚时 | 回滚时间 |
| `rollback_reason` | Text | 否 | 回滚时必填 | 回滚原因 |
| `operation_key` | Char | 是 | 服务器生成 | 幂等键 |

## 3.11 约束和索引

### 普通索引

```text
blind.count.work.package:
    state
    product_categ_id

blind.count:
    work_package_id
    location_id
    state
    (work_package_id, location_id, round)

blind.count.line:
    blind_count_id
    (product_id, lot_name)
    serial_uniqueness_active

blind.count.review:
    blind_count_id
    reviewer_id

blind.count.processing:
    work_package_id
    blind_count_id
    state
    (work_package_id, location_id, is_valid)
```

### 并发唯一性

需要数据库级有效记录唯一策略：

```text
有效 Serial：
    product_id + lot_name + serial_uniqueness_active

有效盲盘单：
    work_package_id + location_id + round + round_uniqueness_active

有效处理单：
    work_package_id + location_id + valid_processing_active
```

Odoo 普通 `_sql_constraints` 无法表达所有“仅有效记录参与”的条件。最终实现必须在 CC 前确定可重复升级的数据库索引方案；见第 7 章和第 13 章。

---

# 4. 状态机设计

## 4.1 工作包

```text
draft ──> in_progress ──> done
   │           │
   └───────────┴──> cancel
```

推进：

- `draft → in_progress`：主管启动；
- `in_progress → done`：所有有效盲盘单已审核，所有有效处理单 Step 1 和 Step 2 完成；
- `draft/in_progress → cancel`：主管或管理员取消。

禁止：

- `done` 回退；
- `done` 新增盲盘单；
- `cancel` 恢复。

## 4.2 盲盘单

```text
draft ──> counting ──> done
   │           │
   └───────────┴──> cancel
```

- `draft → counting`：正确扫描绑定货位；
- `counting → done`：盘点员完成盘点，明细冻结；
- `draft/counting → cancel`：按权限取消；
- `done` 不回退；
- Recount 不改变原单状态，而创建新轮次并把原单标记 `is_replaced=True`。

## 4.3 复核单

```text
draft → counting → done
```

- 来源盲盘单必须 `done`；
- 复核异常不回退盲盘单；
- 完成时必须填写复核结论；
- 已完成复核单只读。

## 4.4 处理单及步骤

```text
draft → review → approved → processing → done
   │       │
   └───────┴──> cancel
```

步骤状态：

```text
清除：pending → done → rolled_back
入库：pending → done → rolled_back
```

`processing` 仅表示当前正在执行 Step 1 或 Step 2；每一步完成后写回独立记录状态。

## 4.5 回退规则

- 业务状态不允许任意回退；
- Step 2 通过反向移动回滚；
- Step 1 回滚前必须先回滚 Step 2；
- 回滚不是把业务状态直接改回 pending，而是新建反向 move 后再设置 `rolled_back`；
- 失败由事务回滚，不进入成功状态。

---

# 5. 库存清除与重建设计

## 5.1 清除范围

Step 1 由工作包产品大类和有效盲盘货位确定范围：

```python
[
    ('product_id.categ_id', 'child_of', work_package.product_categ_id.id),
    ('location_id', 'child_of', location_ids),
    ('quantity', '!=', 0),
]
```

清除前必须检查：

- 公司；
- 正库存和负库存；
- Lot/SN；
- `reserved_quantity`；
- 并发库存变化；
- 货位是否仍可作业。

预留库存如何处理是第 13 章的未解决问题。

## 5.2 清除事务设计

逻辑步骤：

```text
创建清除记录 pending
    ↓
锁定/重新读取范围
    ↓
校验处理单 approved
    ↓
对每个目标 quant 设置 inventory_quantity = 0
    ↓
调用 Odoo 原生 action_apply_inventory()
    ↓
收集生成的 stock.move / stock.move.line
    ↓
写入清除记录
    ↓
清除记录 done
```

禁止：

- 直接写 `stock.quant.quantity`；
- 删除 quant；
- 删除原始 move；
- 中途主动 `commit()`；
- 用成功形状的 fallback 掩盖部分失败。

## 5.3 入库事务设计

逻辑步骤：

```text
校验 Step 1 = done
    ↓
读取冻结的处理明细
    ↓
按 (product, lot_name, location) 汇总
    ↓
tracked 产品匹配/创建 stock.lot
    ↓
生成 stock.move / stock.move.line
    ↓
目标货位为原盲盘货位
    ↓
不设置托盘库存维度
    ↓
调用 _action_done()
    ↓
记录所有 move
    ↓
入库记录 done
```

汇总规则：

- none：产品 + 货位；
- lot：产品 + Lot + 货位；
- serial：产品 + SN + 货位，数量固定 1；
- 托盘码不进入库存维度。

## 5.4 两步之间的状态保存

两步之间保存：

- 清除记录和原始 move；
- 清除状态；
- 审核后的处理明细；
- Lot/SN 匹配状态；
- 入库状态；
- 执行人和时间。

Step 2 不重新读取已冻结的盲盘事实，也不依赖当前 PDA 状态。

## 5.5 事务边界

Step 1 和 Step 2 是两个独立事务：

```text
Step 1 成功提交
    ↓
Step 2 后续单独执行
```

Step 2 失败只回滚本次 Step 2，不自动回滚已经完成的 Step 1。主管可在满足回滚顺序的情况下手动回滚 Step 1。

## 5.6 与 Odoo 原生 inventory adjustment 的区别

项目复用 Odoo 的库存移动实现，但不直接复用后台库存调整 UI：

| Odoo 原生库存调整 | 盲盘处理 |
|---|---|
| 用户直接录入盘点数量 | 数量来自已审核的独立盲盘事实 |
| 通常按 quant 操作 | 按工作包、产品大类和货位范围操作 |
| 不区分盲盘、复核和主管审核 | 严格职责分离 |
| 使用库存调整移动 | 仍使用 `stock.move`，但由处理业务生成 |
| 标准 UI 可编辑 inventory quantity | PDA/处理界面受限，盲盘事实冻结 |

---

# 6. 回滚设计

## 6.1 反向 move 生成机制

回滚记录保存原始 move 集合。回滚时逐条生成方向相反的 move：

```text
原始 location_id       → 原始 location_dest_id
反向 location_dest_id  → 原始 location_id
```

每个原始 move line 应复制：

- 产品；
- 数量；
- UoM；
- Lot/SN；
- owner；
- package（若业务设计允许）；
- 公司；
- 源和目标货位。

反向移动完成后才将对应回滚记录设置为 `rolled_back`。

## 6.2 与 picking 的关系

标准 `stock.return.picking` 仅适用于有 `stock.picking` 的操作。盲盘清除/入库使用库存调整移动，通常没有 picking，因此：

- 不调用 `stock.return.picking` 作为通用回滚；
- 不伪造 picking 以适配标准向导；
- 使用项目处理单关联的自定义反向 move 业务动作；
- 如未来某种入库流程真正产生 picking，应单独评估是否使用标准退货。

## 6.3 幂等性

每个清除/入库记录只能有一个当前有效执行周期：

```text
pending → done
done → rolled_back
rolled_back → 允许新执行周期
```

禁止：

- `done → done` 重复执行；
- `rolled_back → rolled_back` 重复回滚；
- 在原始 move 未回滚时再执行同一步；
- 用“当前 quant 数量”猜测是否已经执行。

每次重新执行都创建新的 move 集合并关联新的操作周期。

## 6.4 回滚后的 quant / lot

预期：

- quant 数量通过反向 move 恢复；
- 原始 `stock.lot` 保留；
- 回滚不删除 Lot/SN；
- 回滚不保证外部业务已经改变库存后的任意状态可恢复；
- 如果原始库存已被其他业务消耗，反向 move 必须阻断并报告。

恢复验证按：

```text
产品 + 货位 + Lot/SN + owner + package
```

维度比较，不只比较产品总量。

## 6.5 审计链

```text
处理单
 ├── 清除记录
 │    ├── 原始 move_ids
 │    └── reverse_move_ids
 └── 入库记录
      ├── 原始 move_ids
      └── reverse_move_ids
```

每次执行和回滚记录：

- 人；
- 时间；
- 原因；
- 操作键；
- 原始 move；
- 反向 move；
- 状态。

---

# 7. 并发约束设计

## 7.1 Serial 唯一性

有效 Serial 唯一键：

```text
product_id + lot_name
```

有效范围：

- 跨工作包；
- 跨盲盘单；
- 跨货位；
- 跨托盘。

排除：

- cancel；
- 已处理完成；
- 被替代；
- 已撤销明细。

盲盘阶段不得查询 `stock.lot` 或库存 quant 判断唯一性。

## 7.2 一货位一轮一单

有效唯一键：

```text
work_package_id + location_id + round
```

`round` 创建和 Recount 递增必须在数据库并发保护下进行，不能仅使用 `max(round) + 1`。

## 7.3 数据库约束

建议在自定义模型中保存有效性字段：

```text
serial_uniqueness_active
round_uniqueness_active
valid_processing_active
```

然后建立只针对有效记录的唯一索引。

由于 Odoo 普通 `_sql_constraints` 不表达所有条件唯一性，实际索引创建方案必须：

- 可重复执行；
- 可升级；
- 可回滚；
- 不依赖人工数据库操作；
- 通过模块技术迁移或初始化机制维护。

该索引实现是 CC 前必须确认的未决设计问题。

## 7.4 应用层锁

应用层职责：

- 先查找并返回友好错误；
- 按业务动作锁定状态转移；
- 将数据库唯一冲突转换为 `UserError`；
- 防止同一 HTTP 请求重复提交；
- 记录冲突日志。

应用层 Python 锁和前端缓存不能作为最终并发保证。

对尚不存在的 Serial，行锁无法锁住“空记录”，所以必须依赖数据库唯一策略、advisory lock 或独立锁记录。

## 7.5 冲突处理

伪代码：

```text
接收扫描
    ↓
校验工作包、产品、状态
    ↓
查询有效重复
    ↓
尝试创建
    ↓
唯一冲突？
    ├── 是：回滚当前事务，返回重复 Serial 错误
    └── 否：返回成功
```

不得宽泛捕获异常，不得把唯一冲突转换为成功。

---

# 8. 前端设计

## 8.1 路由设计

建议：

```text
GET  /blind_count/pda
POST /blind_count/pda/scan
POST /blind_count/pda/undo
POST /blind_count/pda/finish
GET  /blind_count/pda/review
POST /blind_count/pda/review/scan
POST /blind_count/pda/review/finish
```

所有路由：

- `auth='user'`；
- 通过模型 ACL 和记录规则；
- 不使用 `sudo()` 绕过业务权限；
- 修改请求保持 CSRF 保护；
- 使用 Odoo Session；
- 通过模块 assets bundle 加载 OWL。

## 8.2 OWL 组件设计

建议组件：

```text
BlindCountPdaRoot
 ├── WorkPackageSelector
 ├── BlindCountHeader
 ├── ScanStepIndicator
 ├── ScannerInput
 ├── CurrentProductPanel
 ├── CurrentLinesPanel
 ├── ScanErrorBanner
 └── UndoButton
```

复核使用独立根组件，不能复用会显示账面数据的处理组件。

## 8.3 扫描状态机

```text
SCAN_LOCATION
    ↓
SCAN_PACKAGE
    ↓
SCAN_PRODUCT
    ├── tracking=serial → SCAN_SERIAL
    ├── tracking=lot    → SCAN_LOT
    └── tracking=none   → INPUT_QUANTITY
```

非法输入不推进状态。Lot/SN 状态接收到新值时，先按当前工作包产品条码识别规则判断是否为新产品。

## 8.4 输入焦点管理

使用 OWL `useRef` 和生命周期钩子：

- 页面进入后聚焦扫描输入；
- Enter 作为一次扫描提交边界；
- RPC 期间防止重复提交；
- 成功或错误后恢复焦点；
- 不使用 `networkidle` 或固定 sleep 作为业务就绪条件。

输入框：

```text
autocomplete=off
autocorrect=off
autocapitalize=off
spellcheck=false
```

## 8.5 产品条码缓存

缓存键：

```text
work_package_id + barcode
```

缓存值只保存产品识别结果，不保存库存数量、Lot/SN 或唯一性结论。

缓存失效：

- 切换工作包；
- 工作包被取消或完成；
- 产品范围发生变化；
- 后端返回产品不存在或超范围；
- 会话重新开始。

后端始终重新校验产品范围。

## 8.6 撤销机制

按钮只撤销最近一条有效扫描：

```text
前端请求 undo
    ↓
后端按 scan_sequence 找到最后有效行
    ↓
校验状态和权限
    ↓
标记 undone
    ↓
释放 Serial 有效占用
    ↓
返回新的明细摘要
```

完成盲盘后禁止撤销。

## 8.7 UI 测试契约

建议固定 `data-testid`：

```text
blind-count-pda
blind-count-work-package
blind-count-location
blind-count-scan-input
blind-count-step
blind-count-current-product
blind-count-line-count
blind-count-error
blind-count-undo
blind-count-finish
blind-review-scan-input
blind-review-conclusion
```

---

# 9. 权限与安全设计

## 9.1 用户组

建议自定义组：

| 组 | 角色 |
|---|---|
| `group_blind_count_operator` | 盘点员 |
| `group_blind_count_reviewer` | 复核员 |
| `group_blind_count_supervisor` | 仓库主管 |
| `group_blind_count_admin` | 盲盘管理员 |

管理员还应继承 Odoo 设置权限，而不是仅依赖自定义组。

## 9.2 ACL

| 模型 | 盘点员 | 复核员 | 主管 | 管理员 |
|---|---|---|---|---|
| 工作包 | 读 | 读 | 增删改 | 全部 |
| 盲盘单 | 读/执行 | 读 | 读/管理 | 全部 |
| 盲盘明细 | 由业务动作写 | 读 | 读 | 全部 |
| 复核单 | 无 | 执行 | 读/管理 | 全部 |
| 处理单 | 无 | 无 | 增删改/执行 | 全部 |
| 清除/入库记录 | 无 | 无 | 读/执行/回滚 | 全部 |

不允许盘点员直接创建或编辑明细模型。

## 9.3 记录规则

- 盘点员只能看到自己参与的进行中工作包/盲盘单；
- 复核员只能看到被分配或允许复核的盲盘单；
- 主管可看到所属公司范围；
- 管理员可跨范围管理；
- 记录规则不得暴露库存余额或差异字段；
- 多公司记录必须遵守 company_id。

## 9.4 字段级权限

- 清除、入库和回滚字段只对主管/管理员可见；
- `lot_id` 只在处理阶段对主管/管理员可见；
- 盲盘明细的账面数量和差异字段不创建；
- `stock.move` 详情不应在 PDA 盲盘页面暴露。

## 9.5 路由权限

`auth='user'` 只验证登录。每个 Controller 方法仍需：

1. 检查模型访问权限；
2. 检查记录规则；
3. 检查业务角色；
4. 检查状态；
5. 检查工作包归属；
6. 检查输入数据。

---

# 10. 国际化设计

## 10.1 文案清单

至少覆盖：

- 产品条码无法识别；
- 产品不属于本次盘点范围；
- 请先扫描正确货位；
- 货位不匹配；
- 该序列号已被盘点；
- 序列号数量必须为 1；
- 数量必须大于 0；
- 批量 Serial 不能为空；
- 批量 Serial 存在重复；
- 盲盘已完成，不能修改；
- 复核异常；
- 清除前存在预留库存；
- 必须先完成库存清除；
- 不能重复执行；
- 必须先回滚入库；
- 回滚原因不能为空；
- 没有权限执行该操作。

## 10.2 翻译键设计

Python Model/Controller 使用：

```python
_("Cannot scan this product outside the work package.")
```

OWL 使用模块翻译服务，不硬编码中文或荷兰语。

建议业务错误码同时保留稳定键：

```text
BLIND_COUNT_LOCATION_MISMATCH
BLIND_COUNT_PRODUCT_OUT_OF_SCOPE
BLIND_COUNT_SERIAL_DUPLICATE
BLIND_COUNT_REBUILD_ORDER
BLIND_COUNT_ROLLBACK_ORDER
```

错误码用于测试和前端分支，显示文案交给翻译系统。

## 10.3 PO 文件结构

建议模块翻译文件：

```text
blind_count/i18n/zh_CN.po
blind_count/i18n/nl_NL.po
```

每个 PO 文件包含：

- `msgctxt`：业务场景；
- `msgid`：稳定英文源文案；
- `msgstr`：目标语言；
- Python/JS 来源注释；
- 错误码对应的上下文。

---

# 11. 测试策略

## 11.1 单元测试

Python ORM 测试覆盖：

- 工作包字段带出；
- 工作包状态推进；
- 盲盘单状态推进；
- 货位扫描校验；
- 产品大类范围；
- Lot/无追踪累加；
- Serial 数量固定 1；
- 批量 Serial 原子性；
- 盲盘完成后只读；
- Recount 轮次；
- 复核异常不阻断；
- 审核前置条件；
- 处理步骤顺序；
- 回滚原因和权限；
- 空盘。

每个测试映射 SRS AC 和 TDD 决策 ID。

## 11.2 集成测试

使用真实 Odoo ORM 和库存模型验证：

- Step 1 产生 inventory `stock.move`；
- Step 2 按产品、Lot/SN、货位入库；
- 托盘不进入库存维度；
- Lot/SN 匹配或创建；
- Step 1/Step 2 独立事务；
- 回滚产生反向 move；
- 原始 move 不被删除；
- quant 快照恢复；
- Lot 主数据保留。

不使用裸 SQL 修改验证结果。

## 11.3 并发测试

至少测试：

1. 两个事务同时扫描同一产品 Serial；
2. 两个事务同时创建同一货位轮次；
3. 两个事务同时生成 Recount；
4. 两个事务同时执行同一处理步骤；
5. 一个事务回滚时另一个事务重试。

验收：

- 只有一个事务成功；
- 冲突事务明确失败；
- 无部分明细；
- 无重复处理 move；
- 状态与约束一致。

## 11.4 OWL/QUnit 测试

- 状态转移；
- 非法输入阻断；
- Enter 提交；
- 输入焦点恢复；
- Lot/SN 状态识别产品码；
- 批量 Serial 拆分；
- 空值和重复；
- 错误提示；
- 撤销按钮；
- 产品缓存按工作包隔离。

## 11.5 E2E 测试

角色旅程：

### 主管

```text
登录
→ 建立工作包
→ 指定产品大类
→ 启动作业
→ 审核盲盘单
→ 执行清除
→ 执行入库
→ 回滚并重新执行
```

### 盘点员

```text
登录
→ 打开进行中工作包
→ 扫货位
→ 扫托盘
→ 扫产品
→ 扫 Lot/SN 或输入数量
→ 撤销上一条
→ 完成盲盘
```

### 复核员

```text
登录
→ 选择已完成盲盘单
→ 扫货位
→ 记录正常或异常复核
→ 填写结论
```

E2E 规则：

- 使用真实角色；
- 使用稳定 `data-testid`；
- 等待业务 UI 状态；
- 不使用 `networkidle` 或任意 sleep；
- Save/Submit 后刷新或重新打开验证持久化；
- 失败保留 trace、截图和控制台证据。

## 11.6 测试数据

需要隔离 Fixture：

- none、lot、serial 三类产品；
- 同产品不同 Lot；
- 不同产品同名 Lot；
- 多个货位；
- 多托盘；
- 产品大类子分类；
- 正库存、负库存、预留库存；
- 空盘；
- 重盘；
- 取消、替代、已处理记录；
- 1 万条以上 Serial 性能数据。

---

# 12. 对 SRS 的偏离说明

## 12.1 偏离清单

| 偏离 ID | SRS 内容 | TDD 设计 | 类型 | 理由 |
|---|---|---|---|---|
| DEV-001 | SRS 数据模型将清除/入库字段放在处理单 | 增加独立清除记录和入库记录模型 | 技术分解 | 支持两步独立回滚和审计，不改变业务语义 |
| DEV-002 | SRS 写明“反向库存移动”，未规定实现入口 | 不使用 `stock.return.picking`，自建反向 move 动作 | 技术实现偏离 | TV-05 证明标准退货向导不适用库存调整 move |
| DEV-003 | SRS 要求唯一性，但未指定数据库策略 | 增加有效性物化字段和数据库唯一策略 | 技术补充 | TV-08 证明 ORM 查询不能解决并发 |
| DEV-004 | SRS 将 lot_name 作为文本 | 处理明细另存 `lot_id` | 阶段性扩展 | 只允许 Step 2 使用，保持盲盘隔离 |
| DEV-005 | SRS 表格未区分扫描审计和撤销状态 | 盲盘明细增加 `scan_sequence/state/undone_*` | 技术补充 | 支持撤销、审计和并发幂等 |
| DEV-006 | SRS v1.8 声明与仓库文件 v1.7 不一致 | TDD 标记 Draft/Blocked | 基线偏离 | 必须由上游确认，不能由 TDD 自行调和 |

## 12.2 不构成业务偏离的技术细化

以下属于实现细化，不改变 SRS：

- 使用 `stock.move` 而不是直接写 quant；
- 使用 OWL `useState/useRef`；
- 使用独立 Controller 路由；
- 使用有效性字段支持条件唯一；
- 保存库存 move 关联；
- 使用稳定错误码和翻译键。

## 12.3 需要 SRS 更新的条目

建议 SRS 后续版本补充：

1. Step 1/Step 2 通过 `stock.move` 完成；
2. 禁止直接写 `stock.quant.quantity`；
3. 标准 `stock.return.picking` 不作为库存调整回滚机制；
4. 回滚必须保存原始和反向 move 关联；
5. Serial 和一货位一轮一单必须有数据库并发保证；
6. 撤销是“作废并审计”，不是无痕删除；
7. 产品大类和货位查询包含子级；
8. 预留库存处理规则；
9. SRS v1.8 文件正式冻结并替换/确认当前 v1.7 文件。

---

# 13. 未解决的设计问题

这些问题不能由本文档擅自决定，必须在 CC 前确认。

| ID | 问题 | 影响 | 决策人/阶段 |
|---|---|---|---|
| OPEN-001 | 主工作区 SRS 是 v1.7，用户声明为 v1.8，哪一个是最终权威？ | 影响全部追溯和验收 | 项目负责人，CC 前 |
| OPEN-002 | 产品大类到客户的正式来源是什么？`product.category` 没有标准客户字段 | 工作包 `partner_id` 来源和约束 | 业务负责人，CC-模型 |
| OPEN-003 | 清除范围中的“货位”是工作包所有盲盘货位，还是产品大类下全部内部货位？ | 直接决定 Step 1 库存范围 | 业务负责人，CC-处理 |
| OPEN-004 | 清除前存在 `reserved_quantity` 时，是阻断、取消预留，还是允许清除？ | 影响库存一致性和现场作业 | 仓库主管，CC-处理 |
| OPEN-005 | Step 2 失败后是否允许不回滚 Step 1 直接重试？ | 影响处理状态和操作 UX | 业务负责人，CC-处理 |
| OPEN-006 | `stock.lot` 名称唯一性在多公司下的精确定义是什么？ | 影响 Lot/SN 建立和唯一索引 | 技术负责人，CC-处理 |
| OPEN-007 | 条件唯一索引的模块升级实现方式是什么？ | 影响并发保证和升级路径 | 技术负责人，CC-模型 |
| OPEN-008 | 复核单是否允许同一盲盘单多次复核？ | 影响复核唯一性和历史 | 业务负责人，CC-复核 |
| OPEN-009 | Recount 后原盲盘单是否永远排除，还是主管可重新接受？ | 影响唯一性、处理有效性和工作包完成 | 业务负责人，CC-状态 |
| OPEN-010 | 反向 move 遇到外部库存消耗时，是阻断、部分回滚还是生成差异任务？ | 影响回滚安全性 | 仓库主管，CC-回滚 |
| OPEN-011 | PDA 产品条码查询是否允许批量预加载当前工作包产品？ | 影响 <500ms 目标和缓存策略 | 技术负责人，CC-PDA |
| OPEN-012 | 批量 Serial 二维码的最大数量是多少？ | 影响请求大小和 UI 提示 | 业务负责人，CC-PDA |
| OPEN-013 | 盘点员“仅自己参与”的参与关系如何建立？ | 影响记录规则和工作包分配 | 业务负责人，CC-权限 |
| OPEN-014 | 主管审核是逐行审核后整体确认，还是直接整单确认？ | 影响处理明细状态和 UI | 业务负责人，CC-审核 |
| OPEN-015 | 仓库主管与 Odoo `stock.group_stock_manager` 的映射是什么？ | 影响库存移动执行权限 | 技术负责人，CC-权限 |

在这些问题确认前，不能冻结最终 CC。

---

# 14. 对 CC 的输入

## 14.1 编码顺序建议

### CC-01：模块骨架和权限

- 模块清单和依赖；
- 用户组、ACL、记录规则；
- 序列；
- 基础菜单和后台只读视图；
- SRS 版本基线确认。

### CC-02：工作包、盲盘单和明细

- 工作包；
- 盲盘单；
- 盲盘明细；
- 状态机；
- 一货位一轮一单；
- Serial 并发唯一性；
- Python ORM 测试。

### CC-03：PDA 盲盘

- Controller 路由；
- OWL 状态机；
- 扫码输入；
- 产品条码查询和缓存；
- Lot/SN/无追踪规则；
- 批量 Serial；
- 撤销；
- QUnit 和 Playwright。

### CC-04：复核

- 复核单和明细；
- 宽松校验；
- 双向匹配；
- 复核结论；
- 复核员权限；
- E2E 复核流程。

### CC-05：处理审核

- 处理单和处理明细；
- 主管逐行/整单审核；
- Lot/SN 匹配或创建；
- 有效处理单；
- Step 1/Step 2 前置条件。

### CC-06：库存清除和入库

- Step 1 原生 inventory adjustment move；
- Step 2 move/move line；
- 事务边界；
- 库存快照；
- 预留库存决策；
- 集成测试。

### CC-07：回滚和项目级 E2E

- 自研反向 move；
- 回滚顺序；
- 幂等；
- 多次回滚和重执行；
- 审计；
- 主管完整旅程；
- Final Baseline Regression。

## 14.2 关键决策点

编码开始前必须确认：

1. SRS v1.7/v1.8 最终基线；
2. 产品大类与客户来源；
3. 清除范围；
4. 预留库存策略；
5. 条件唯一索引的升级实现；
6. 反向 move 处理外部库存变化；
7. Recount 和复核重做规则；
8. 盘点员参与关系；
9. 批量 Serial 数量上限；
10. 主管审核粒度。

## 14.3 风险提示

- 不得先写生产代码再补齐 OPEN 问题；
- 不得以 ORM 搜索代替并发约束；
- 不得直接改 quant；
- 不得把标准 picking return 当作库存调整回滚；
- 不得把盲盘明细关联到 `stock.lot`；
- 不得让前端状态机成为唯一业务校验；
- 不得在未有真实盲盘数据时宣称性能达标；
- 不得把 TV 报告中的“可行”误写成“已实现”。

---

# 附录 A：追溯索引

| TDD 区域 | SRS/TV 来源 |
|---|---|
| 模型隔离 | SRS C1-C5、P1-P4、AC1-AC6 |
| 盲盘状态 | SRS F1.1-F3.3、AC51-AC55 |
| 扫描状态机 | SRS C7-C11、R1-R15、AC8-AC20；TV-10 至 TV-15 |
| Serial 唯一性 | SRS R16-R30、AC33、AC35；TV-07 至 TV-09 |
| 复核 | SRS R31-R38、AC42-AC50；TV-16、TV-17 |
| 库存清除 | SRS C15-C18、AC21、AC24、AC57；TV-01 |
| 入库 | SRS C16-C18、AC22-AC32、AC58；TV-02、TV-03 |
| 回滚 | SRS C19-C24、AC59-AC64；TV-04 至 TV-06 |
| 状态和 Recount | SRS C30-C34、AC51-AC56、AC65；TV-18 至 TV-20 |
| 权限安全 | SRS §7、N7；TV-15 |
| 国际化 | SRS N9 |
| 测试 | SRS N1-N12、§9；TV-09、TV-10、TV-13、TV-20 |

# 附录 B：文档门禁

本文档只有在以下条件满足后才能升级为 Frozen：

- SRS 版本差异已解决；
- OPEN-001 至 OPEN-015 已作出记录化决策，或明确标记为不适用；
- 条件唯一索引的升级方案已验证；
- 预留库存和清除范围已冻结；
- 反向 move 设计通过集成验证；
- TDD 追溯矩阵与最终 SRS 一致；
- 对应 Coding Contract 已引用本 TDD 的冻结版本。
