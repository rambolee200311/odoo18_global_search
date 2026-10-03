# SPIKE-GS-04 Query 与 Refinement 条件合并报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-04 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 数据库 | `odoo18ce` |
| 数据来源 | SPIKE-GS-03 ORM 测试数据 |
| 读取方式 | Odoo ORM |

## 2. 摘要

本 Spike 使用 5 个 Business Resource 的 17 条真实 ORM 记录，验证 Parsed Conditions 与 Refinement Conditions 的合并规则。

结果：

- 路径 A 与路径 B 产生完全相同的 Effective Conditions；
- 两条路径产生相同的 Result Identity 集合；
- 同维度冲突时 Refinement 覆盖 Parsed 条件；
- 重复条件被去重；
- 不同维度条件共同生效，相当于 AND；
- 解析失败条件不进入 Effective Conditions；
- 删除条件后 Raw Query 保持不变；
- 重复命中路径按 Result Identity 去重，计数从 2 个原始命中降为 1。

整体结论：**有条件可行**。条件模型、冲突消解、路径等价、删除行为和 BR-013 去重计数均获得证据。

## 3. SRS 追溯

- BR-007：Effective Conditions 合并、去重和冲突消解；
- BR-008：两条路径映射到同一条件模型；
- BR-010：不同维度 AND、同维度多值 OR；
- BR-011：Result Identity 去重；
- BR-013：精确计数；
- FR-RF-009：Query 与 Refinement 两条路径汇合；
- AC-009：解析失败；
- AC-011：路径 A/B 等价；
- AC-012：Query 与 Refinement 冲突。

## 4. 测试数据

数据复用 SPIKE-GS-03 已通过 ORM 创建的 `GS03-` 标记记录：

| Business Resource | Technical Model | 记录数 |
|---|---|---:|
| 销售订单 | `sale.order` | 3 |
| 采购订单 | `purchase.order` | 3 |
| 发票 | `account.move` | 4 |
| 出库单 | `stock.picking` | 4 |
| 库存移动 | `stock.move` | 3 |
| **合计** |  | **17** |

运行时通过 Odoo ORM 重新读取并生成 [data_snapshot.json]，未使用裸 SQL 或数据库驱动。

## 5. 合并规则验证

测试实现采用以下规则：

1. Refinement 存在同维度条件时，移除 Parsed 的同维度条件；
2. Parsed 与 Refinement 保留不同维度，作为 AND 条件；
3. 完全相同的条件按 `(dimension, operator, value)` 去重；
4. `parsed=false` 的条件不进入 Effective Conditions；
5. 删除维度从 Effective Conditions 移除，Raw Query 独立保留；
6. Result Identity 使用 `(Business Resource, Technical Model, Record ID)`；
7. 重复命中只计一次。

## 6. 结果

### 6.1 路径 A/B 等价

路径 A：

```text
GS03 Partner 出库 2026-06 draft
```

Effective Conditions：

```text
entity = GS03 Partner
resource = 出库单
month = 2026-06
state = draft
```

路径 B：

```text
GS03 Partner → 出库单 → 2026-06 → draft
```

两条路径均返回：

```text
("出库单", "stock.picking", 31)
```

结果字段：

| 检查项 | 结果 |
|---|---|
| Path A Effective Conditions | 4 条 |
| Path B Effective Conditions | 4 条 |
| Effective Conditions 相同 | `true` |
| Filtered Result Set 相同 | `true` |
| 每条路径结果数 | 1 |

### 6.2 冲突、去重和失败解析

| 场景 | 输入 | 实际结果 |
|---|---|---|
| 同维度冲突 | Parsed=`出库单`，Refinement=`入库单` | 只保留 `入库单` |
| 同维度重复 | 两次 `month=2026-06` | 只保留 1 条 |
| 解析失败 | `state=unknown` 且 `parsed=false` | 不进入 Effective Conditions |
| 不同维度 | entity + resource + month + state | 全部保留并共同过滤 |

### 6.3 用户删除条件

删除 `state=draft` 后：

- Raw Query 仍为 `GS03 Partner 出库 2026-06 draft`；
- Effective Conditions 只剩 entity、resource、month；
- `state` 已从 Effective Conditions 移除。

这符合 BR-007 的 Query 与 Refinement 状态分离规则。

### 6.4 Result Identity 与计数

同一结果通过两条命中路径产生 2 个原始命中，但两者的 Result Identity 相同：

```text
("出库单", "stock.picking", 31)
```

计数结果：

| 项 | 数值 |
|---|---:|
| 原始重复命中 | 2 |
| 去重后 Result Identity | 1 |
| BR-013 计数正确 | `true` |

## 7. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 同维度无冲突 | 通过 | Parsed 条件保留 |
| 同维度冲突 | 通过 | Refinement 优先 |
| 同维度重复 | 通过 | 2 条降为 1 条 |
| 不同维度 | 通过 | 4 个维度共同生效 |
| 解析失败 | 通过 | `unknown` 未进入结果 |
| 用户删除条件 | 通过 | Raw Query 不变，state 移除 |
| 路径 A/B 等价 | 通过 | Effective Conditions 和结果集均相同 |
| 计数去重 | 通过 | 2 个原始命中计为 1 |

## 8. 限制与后续工作

1. 本 Spike 验证条件模型和结果集合语义，不实现 Query Understanding UI；
2. 同维度多值 OR 的复杂组合需在后续测试中增加更多状态样本；
3. 真实权限过滤、无权字段排除和 partially failed model 尚未在本 Spike 验证；
4. 生产实现需要将冲突消解信息暴露给 Query Understanding；
5. 生产实现应确保计数不受分页影响。

## 9. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_04_query_refinement_merge/data/generate_orm.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_04_query_refinement_merge/scripts/run.py
```

## 10. 产出物

- `PLAN.md`
- `README.md`
- `data/generate_orm.py`
- `scripts/run.py`
- `results/data_snapshot.json`
- `results/spike_result.json`
- `reports/REPORT.md`

