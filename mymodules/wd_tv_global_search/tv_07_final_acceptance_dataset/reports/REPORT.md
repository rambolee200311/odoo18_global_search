# TV-07 Global Search Final Acceptance Dataset Report

## 执行环境

```text
Database: odoo18ce
Generator: data/generate.py
Configuration: global_search_baseline Version 4
```

本报告由 Odoo ORM 生成。生成器可重复执行，重跑后数量保持不变，不删除非
`GS-*` 数据。

## 实际创建/复用数量

| 类型 | 数量 |
|---|---:|
| 供应商 | 5 |
| 客户 | 5 |
| 产品 | 10 |
| 采购订单 | 100 |
| 入库单 | 100 |
| 销售订单 | 100 |
| 出库单 | 100 |

## 日期分布

| 月份 | PO | SO |
|---|---:|---:|
| 2025-10 | 15 | 15 |
| 2025-11 | 15 | 15 |
| 2025-12 | 15 | 15 |
| 2026-01 | 15 | 15 |
| 2026-02 | 15 | 15 |
| 2026-03 | 15 | 15 |
| 2026-04 | 10 | 10 |

日期字段为 `purchase.order.date_order` 和 `sale.order.date_order`，范围覆盖
2025-10-01 至 2026-04-30。

## 状态分布

由于每张订单都必须形成真实 picking 业务链，本数据集先完成确认流程：

```text
Purchase Order: purchase = 100
Sales Order: sale = 100
```

这是真实 Odoo 状态，不伪造不存在的状态。Draft/Sent 场景不能与“每张订单
必须有真实 Receipt/Delivery”同时满足，因此未人为制造孤立草稿单据。

## 业务关系验证

```text
Purchase Order -> Receipt: 100 / 100
Sales Order -> Delivery: 100 / 100
```

抽样关系：

| Purchase Order | Receipt |
|---|---|
| `GS-PO-0001` | `GS-IN-0001` |
| `GS-PO-0002` | `GS-IN-0002` |
| `GS-PO-0003` | `GS-IN-0003` |
| `GS-PO-0004` | `GS-IN-0004` |
| `GS-PO-0005` | `GS-IN-0005` |

| Sales Order | Delivery |
|---|---|
| `GS-SO-0001` | `GS-OUT-0001` |
| `GS-SO-0002` | `GS-OUT-0002` |
| `GS-SO-0003` | `GS-OUT-0003` |
| `GS-SO-0004` | `GS-OUT-0004` |
| `GS-SO-0005` | `GS-OUT-0005` |

关系通过 `stock.picking.purchase_id` 和 `stock.picking.sale_id` ORM 字段核验。

## Product 使用情况

每个产品均出现在 10 个采购订单和 10 个销售订单中：

```text
GS-PRODUCT-001 .. GS-PRODUCT-010: PO=10, SO=10
```

## Partner 使用情况

```text
GS-VENDOR-001 .. GS-VENDOR-005: PO=20 each
GS-CUSTOMER-001 .. GS-CUSTOMER-005: SO=20 each
```

## 建议 Global Search 手工验收 Query

### 精确业务标识

```text
GS-PO-0050
GS-IN-0050
GS-SO-0050
GS-OUT-0050
GS-VENDOR-003
GS-CUSTOMER-002
GS-PRODUCT-005
```

订单和 picking 的测试记录 `name` 已使用 `GS-*` 标识，Odoo sequence 定义未修改；
只对本数据集记录写入确定性名称。

### 日期 Refinement

```text
2025-10-01 ～ 2025-12-31
2026-01-01 ～ 2026-03-31
2026-04-01 ～ 2026-04-30
2025-10-01 ～ 2026-04-30
```

验收时按 `[start, end)` 检查月份边界，确认 2025-12-31、2026-03-31 和
2026-04-30 不重复、不遗漏。

## 配置限制说明

`global_search_baseline` Version 4 已增加并发布以下 Relation Path：

```text
purchase_order: partner_id, order_line.product_id
sale_order:     partner_id, order_line.product_id
stock_picking:  purchase_id, sale_id
```

这些路径已通过配置和权限校验，Search Executor 会将 Raw Query 扩展到已授权关系
的标识字段（例如 `partner_id.name`、`partner_id.ref`），因此可以验证客户/供应商
搜索命中关联订单。任意业务字段关系仍必须先进入 Published Configuration，不能由
客户端请求体临时指定。

## Chromium HVR 观察

在 `127.0.0.1:8091/wd_global_search` 使用当前 Odoo 用户验证：

| Query | Result Resource | 结果 |
|---|---|---|
| `GS-PO-0050` | `purchase_order` | PASS |
| `GS-IN-0050` | `stock_picking` | PASS |
| `GS-SO-0050` | `sale_order` | PASS |
| `GS-OUT-0050` | `stock_picking` | PASS |
| `GS-VENDOR-003` | `contact` | PASS |
| `GS-CUSTOMER-002` | `contact` | PASS |
| `GS-PRODUCT-005` | `product` | PASS |

`GS-IN-0050` Preview 已确认显示 `READ ONLY · FORM VIEW`、供应商、日期、状态和
源单据。当前 Preview serializer 只支持 Contact、Sales Order 和 Stock Picking；
Purchase Order 和 Product 的结果可以搜索，但点击 Preview 会返回
`PERMISSION_OR_DELETED`/不可用状态，这属于现有 Preview 配置限制，不是数据生成失败。

当前 Workspace 只提供 `Any time`、`Today`、`This week`、`This month` 四个日期
选项；用户要求的任意起止日期范围需要通过 API conditions/服务层验收，不能伪称为
当前浏览器下拉框已经支持。
