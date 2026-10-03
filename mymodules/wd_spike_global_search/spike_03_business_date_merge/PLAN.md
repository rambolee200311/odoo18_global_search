# SPIKE-GS-03 跨资源 Business Date 合并

## 1. Spike 标识

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-03 |
| 名称 | 跨资源 Business Date 合并 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 日期 | 2026-10-02 |

## 2. 验证问题

验证多个 Business Resource 按各自 Business Date 独立过滤后再合并，是否符合用户预期：

1. 订单、出库单、发票等资源是否使用各自配置的日期字段；
2. 三种“2026 年 6 月”是否形成同一个包含范围；
3. 合并结果是否稳定可复现；
4. 每条结果是否标注使用的 Business Date；
5. Business Date 为空时是否按 BR-009.4 排除。

## 3. SRS 追溯

- FR-RF-003
- FR-RF-004
- BR-009.3
- BR-009.4
- BR-009.6
- AC-023
- AC-028

## 4. 测试资源与日期字段

| Business Resource | Technical Model | Business Date |
|---|---|---|
| 销售订单 | `sale.order` | `date_order` |
| 采购订单 | `purchase.order` | `date_order` |
| 发票 | `account.move` | `invoice_date` |
| 出库单 | `stock.picking` | `date_done` |
| 库存移动 | `stock.move` | `date` |

每个资源创建 2026-05、2026-06、2026-07 和空日期记录。

## 5. 成功标准

| 项目 | 成功标准 |
|---|---|
| 独立过滤 | 每个资源只按自身 Business Date 过滤 |
| 月份语义 | 2026-06-01 至 2026-06-30，结束边界排除 |
| 合并 | 五个资源的 6 月记录合并为稳定结果 |
| 标注 | 每条结果包含 resource、model、record_id、business_date |
| 空日期 | 默认不进入日期筛选结果 |

