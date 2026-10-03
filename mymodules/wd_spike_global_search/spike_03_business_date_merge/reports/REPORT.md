# SPIKE-GS-03 跨资源 Business Date 合并报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-03 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 数据库 | `odoo18ce` |
| 用户 | Odoo ORM 当前用户，UID 1 |
| 数据标记 | `GS03-` |

## 2. 摘要

本 Spike 在 5 个 Business Resource 中建立 2026-05、2026-06、2026-07 的日期分布，并对可为空的 Business Date 建立空值记录。用户选择 `2026-06` 时，各资源分别按自己的 Business Date 过滤，再合并结果。

结果：

- 5 个资源各返回 1 条 2026-06-30 记录；
- 合并总数为 5；
- 每条结果均标注 Business Date 和使用的字段；
- 合并结果重复执行完全一致；
- 空 Business Date 的发票和出库单均被排除；
- `2026-06-01` 包含、`2026-07-01` 排除，边界符合 BR-009.3。

整体结论：**有条件可行**。跨资源独立日期过滤、统一月份范围、稳定合并、日期标注和空日期排除均得到验证。

## 3. SRS 追溯

- FR-RF-003：按日期范围筛选；
- FR-RF-004：使用 Business Resource 配置的默认业务日期；
- BR-009.3：起始日期包含、结束日期次日排除；
- BR-009.4：空日期默认不出现在日期筛选结果；
- BR-009.6：各资源独立过滤后合并并标注 Business Date；
- AC-023：跨资源日期筛选；
- AC-028：空日期。

## 4. Business Date 映射

| Business Resource | Technical Model | Business Date 字段 |
|---|---|---|
| 销售订单 | `sale.order` | `date_order` |
| 采购订单 | `purchase.order` | `date_order` |
| 发票 | `account.move` | `invoice_date` |
| 出库单 | `stock.picking` | `date_done` |
| 库存移动 | `stock.move` | `date` |

测试日期为：

- 2026-05-31；
- 2026-06-30；
- 2026-07-01；
- 空值（适用于允许空值的模型）。

## 5. 合并规则

本 Spike 使用：

```text
start_inclusive = 2026-06-01
end_exclusive   = 2026-07-01
```

每个资源独立读取其配置字段，只有满足：

```text
2026-06-01 <= Business Date < 2026-07-01
```

的记录进入结果。合并排序键为：

```text
(business_date, technical_model, record_id)
```

该排序用于验证稳定性；生产排序仍需结合 BR-003.1 的完整排序规则。

## 6. 结果

### 6.1 各资源过滤结果

| 模型 | 6 月命中数 | 空日期排除数 |
|---|---:|---:|
| `sale.order` | 1 | 0 |
| `purchase.order` | 1 | 0 |
| `account.move` | 1 | 1 |
| `stock.picking` | 1 | 1 |
| `stock.move` | 1 | 0 |
| **合计** | **5** | **2** |

销售订单和采购订单的 `date_order` 在 Odoo 数据库中为非空字段，因此无法合法建立空值记录；这属于模型约束证据。发票 `invoice_date` 和出库单 `date_done` 的空值记录已验证默认排除。

### 6.2 合并结果标注

5 条结果全部包含：

- Business Resource；
- Technical Model；
- Record ID；
- Business Date；
- 使用的 Business Date 字段；
- 业务标记。

因此 UI 可以在结果卡片中明确显示该记录实际使用的业务日期。

### 6.3 稳定性与边界

| 检查项 | 结果 |
|---|---|
| 合并记录数 | 5 |
| 重复执行一致 | `true` |
| 全部结果为 2026-06 | `true` |
| 全部结果有日期标注 | `true` |
| 2026-05-31 | 排除 |
| 2026-06-30 | 包含 |
| 2026-07-01 | 排除 |
| 空 Business Date | 排除 |

## 7. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 各资源独立日期字段 | 通过 | 5 个模型的 Business Date 映射和单独命中数 |
| 三种“6 月”统一 | 通过 | 五个资源均按同一 `[2026-06-01, 2026-07-01)` 范围命中 |
| 合并稳定 | 通过 | `stable_repeat=true` |
| 日期标注 | 通过 | `all_results_annotated=true` |
| 空日期处理 | 通过（受模型约束） | 可为空字段的记录均排除；非空约束已记录 |

## 8. 限制与后续工作

1. 本 Spike 验证的是技术日期映射和合并语义，不实现前端日期筛选控件；
2. `sale.order.date_order` 和 `purchase.order.date_order` 为非空字段，生产配置应禁止将其配置为空日期测试；
3. 尚未验证用户时区、“今天/本周/本月”动态范围和多公司规则；
4. 生产排序应继续纳入相关性、Business Date 降序、Technical Model 优先级和 Record ID；
5. 若产品需要展示空日期记录，应实现 BR-009.4 允许的显式配置开关。

## 9. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_03_business_date_merge/data/generate_orm.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_03_business_date_merge/scripts/run.py
```

## 10. 产出物

- `PLAN.md`
- `README.md`
- `data/generate_orm.py`
- `scripts/run.py`
- `results/simulation_result.json`
- `results/spike_result.json`
- `reports/REPORT.md`

