# SPIKE-GS-04 Query 与 Refinement 条件合并

## 1. Spike 标识

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-04 |
| 名称 | Query 与 Refinement 条件合并 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 日期 | 2026-10-02 |

## 2. 验证问题

验证 Parsed Conditions 与 Refinement Conditions 合并后，是否稳定产生 Effective Conditions，并保证路径 A/B 等价：

1. 同维度无冲突是否 AND 合并；
2. 同维度冲突是否由 Refinement 优先；
3. 同维度重复是否去重；
4. 不同维度是否 AND 合并；
5. 解析失败条件是否不进入 Effective Conditions；
6. 删除 Refinement 后是否只移除该条件且 Raw Query 不变；
7. 路径 A/B 是否产生相同 Effective Conditions 与结果集；
8. Result Identity 去重后的计数是否正确。

## 3. SRS 追溯

- BR-007
- BR-008
- BR-010
- BR-011
- BR-013
- FR-RF-009
- AC-009
- AC-011
- AC-012

## 4. 测试数据

复用 SPIKE-GS-03 通过 ORM 创建的 `GS03-` 标记数据，覆盖 5 个 Business Resource：

- `sale.order`
- `purchase.order`
- `account.move`
- `stock.picking`
- `stock.move`

运行时再次通过 ORM 读取，不直接访问数据库。

## 5. 合并规则

- 同维度 Refinement 存在时覆盖 Parsed Conditions；
- 同维度相同条件去重；
- 不同维度保留并按 AND 解释；
- 无效/解析失败条件丢弃；
- 删除条件从 Effective Conditions 删除，Raw Query 保持不变；
- 结果按 `(resource, model, record_id)` 作为 Result Identity 去重；
- 计数为去重后的 Identity 集合大小。

## 6. 成功标准

| 项目 | 成功标准 |
|---|---|
| 路径 A/B 等价 | Effective Conditions 和 Result Identity 集合 100% 相同 |
| 冲突消解 | Refinement 覆盖 Parsed 条件 |
| 去重 | 重复条件和重复命中不增加计数 |
| 解析失败 | 不进入 Effective Conditions |
| 删除条件 | Raw Query 不变，条件从 Effective Conditions 移除 |
| 计数 | 按 BR-011 Identity 去重并符合 BR-013 |

