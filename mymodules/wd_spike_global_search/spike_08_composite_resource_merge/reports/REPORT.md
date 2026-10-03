# SPIKE-GS-08 复合资源合并与排序报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-08 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 固定种子 | `20261008` |
| 复合资源 | 订单 |
| Technical Models | `sale.order` + `purchase.order` |
| 基准规模 | 每模型 100,000 条，共 200,000 条 |
| 数据写入 | 未写入共享数据库，内存生成 |

## 2. 摘要

本 Spike 使用固定种子的 200,000 条内存基准记录验证复合资源“订单”的合并、排序和计数，同时通过 Odoo ORM 读取真实模型字段元数据。

结果：

- 两个模型均完成标题、日期、状态和 Snapshot 映射；
- 10 万条/模型的 20 万条数据均可生成和排序；
- Technical Model 优先级 `sale.order=1`、`purchase.order=2` 唯一；
- 重复优先级配置被拒绝；
- 默认排序稳定；
- 199,980 条非空 Business Date 记录均排在 20 条空日期记录之前；
- 重复路径按 Result Identity 去重；
- “全部”计数等于两个分类计数之和。

整体结论：**有条件可行**。复合资源合并、统一映射、排序、优先级校验和计数规则均得到技术证据；真实数据库 20 万条业务写入未执行，仍需隔离性能环境验证 ORM/数据库性能。

## 3. SRS 追溯

- BR-003：复合资源合并规则；
- BR-003.1：复合资源默认排序；
- BR-013：Result Identity 计数；
- CFG-001：Business Resource 多模型配置；
- AC-025：复合资源订单；
- AC-042：复合资源默认排序；
- AC-043：空 Business Date 排序。

## 4. 字段映射

真实 Odoo ORM 元数据验证：

| 统一字段 | `sale.order` | `purchase.order` |
|---|---|---|
| 标题 | `name` | `name` |
| Business Date | `date_order` | `date_order` |
| 系统状态 | `state` | `state` |
| 关联实体 | `partner_id` | `partner_id` |
| 金额 Snapshot | `amount_total` | `amount_total` |

业务状态映射：

| 系统状态 | 统一业务状态 |
|---|---|
| `draft`、`sent`、`to approve` | 未完成 |
| `sale`、`purchase`、`done` | 已完成 |
| `cancel` | 已取消 |

结果：

```text
mapping_complete = true
```

## 5. 默认排序

实现排序键为：

```text
Business Date 非空优先
→ 相关性降序
→ Business Date 降序
→ Technical Model 优先级升序
→ Record ID 升序
```

其中“非空优先”是 BR-003.1 对空 Business Date 的显式约束；在非空记录内部保持 SRS 规定的相关性、日期、模型优先级和 Record ID 顺序。

配置：

```text
sale.order     priority = 1
purchase.order priority = 2
```

同分、同日期时，`sale.order` 优先于 `purchase.order`；同模型内再按 Record ID 升序。

## 6. 结果

### 6.1 规模

| 模型 | 记录数 |
|---|---:|
| `sale.order` | 100,000 |
| `purchase.order` | 100,000 |
| **合计** | **200,000** |

### 6.2 优先级校验

| 场景 | 结果 |
|---|---|
| `sale.order=1`、`purchase.order=2` | 通过 |
| `sale.order=1`、`purchase.order=1` | 拒绝 |
| 优先级唯一性 | `valid_unique=true` |
| 冲突配置拒绝 | `duplicate_rejected=true` |

### 6.3 空日期

测试数据中每 10,000 条产生一条空 Business Date，共 20 条：

| 检查项 | 结果 |
|---|---:|
| 非空记录数 | 199,980 |
| 空日期记录数 | 20 |
| 首个空日期排序位置 | 199,980 |
| 所有非空记录在空日期之前 | `true` |

符合 BR-003.1 和 AC-043。

### 6.4 稳定性

同一 200,000 条输入执行两次排序：

```text
stable_repeat = true
```

同分结果继续由 Business Date、Technical Model 优先级和 Record ID 决定，不依赖不稳定的输入顺序。

### 6.5 计数与去重

| 计数项 | 数值 |
|---|---:|
| 销售订单分类计数 | 100,000 |
| 采购订单分类计数 | 100,000 |
| 全部计数 | 200,000 |
| 重复路径原始命中 | 200 |
| 去重后 Result Identity | 100 |

Result Identity 使用：

```text
(Business Resource, Technical Model, Record ID)
```

由于两个模型属于同一复合 Business Resource，但 Technical Model 不同，因此两者记录仍是不同的 Result Identity；同一模型同一 ID 的重复路径只计一次。

## 7. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 标题字段统一映射 | 通过 | 两模型均有 `name` |
| 日期字段统一映射 | 通过 | 两模型均有 `date_order` |
| 状态映射统一 | 通过 | `mapping_complete=true` |
| Snapshot 字段统一 | 通过 | `name`、`partner_id`、`amount_total` |
| 默认排序 | 通过 | 排序键和样本结果 |
| 优先级唯一性 | 通过 | 冲突配置被拒绝 |
| 空日期排序 | 通过 | 20 条空日期全部置后 |
| 同分稳定 | 通过 | `stable_repeat=true` |
| Identity 去重计数 | 通过 | 200 原始重复命中降为 100 |
| 全部计数 | 通过 | 100,000 + 100,000 = 200,000 |

## 8. 限制与后续工作

1. 20 万条数据为固定种子的内存基准，不是共享数据库中的真实 ORM 持久化数据；
2. 需要在隔离数据库中验证真实 ORM 查询、分页、计数和排序性能；
3. 状态映射仍需由 CFG-001 配置驱动，不能硬编码；
4. 生产实现需要保存并校验排序优先级唯一性；
5. Snapshot 字段必须在运行时再次按当前用户权限过滤。
6. `pg_trgm` 扩展、GIN/GiST 索引和执行计划未在本项目中直接验证；该验证受数据库结构/索引禁止直接操作的项目纪律约束。

## 9. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_08_composite_resource_merge/scripts/run.py
```

## 10. 产出物

- `PLAN.md`
- `README.md`
- `scripts/run.py`
- `results/spike_result.json`
- `reports/REPORT.md`
