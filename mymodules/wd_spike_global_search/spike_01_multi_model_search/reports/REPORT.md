# SPIKE-GS-01 多模型搜索性能报告

## 1. Spike 标识

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-01 |
| 名称 | 多模型搜索性能 |
| 版本 | v0.2 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-01 |
| 执行人 | Odoo 18 技术 Spike 助手 |
| 对应 Plan | `PLAN.md` v0.1 |

## 2. 摘要

本报告记录启用销售采购模块并通过 Odoo ORM 写入模拟业务数据后的第二轮基准。目标数据库可以通过 Odoo 18 ORM 访问，销售订单和采购订单已可用；`project.task` 仍缺失，且实际数据规模远低于 NFR-001 的百万级 Benchmark Profile。因此本轮不能证明 NFR-001；整体结论为 **有条件可行 / NFR 未验证**。

关键事实：

1. 目标数据库可通过 `./venv` 与 `./odoo.conf` 正常启动 ORM。
2. `sale` 和 `purchase` 模块已通过 Odoo 官方模块安装流程启用；`res.partner`、`sale.order`、`purchase.order`、`stock.picking`、`account.move`、`product.product`、`stock.quant` 可用，`project.task` 仍不可用。
3. 本轮通过 ORM 写入 5,000 个客户、5,000 个销售订单和 5,000 个采购订单，使用固定标记 `GS01-`，并已提交事务。
4. 客户、销售订单和采购订单查询均有预期命中；串行查询 P95 为 `0.166–2.613 ms`，20 并发 P95 为 `6.300 ms`。

## 3. 验证问题回顾

| 问题 | 回答 | 数据依据 |
|---|---|---|
| Q1 查询延迟 | 仅对当前可用模型做了 ORM 只读基准，不能外推百万级 NFR | `results/spike_result.json` |
| Q2 模型/数据基础 | 部分满足：8 个目标技术模型中 7 个可用，销售/采购各写入 5,000 条，但仍远低于每资源百万级目标且缺失 `project.task` | `installed_models`、`model_counts`、`simulation_result.json` |
| Q3 20 并发 | 20 个独立 ORM cursor 查询成功，P50 `2.464 ms`、P95 `6.300 ms`、P99 `6.618 ms`；不是目标规模证明 | `concurrent_queries` |
| Q4 深度 2 Relation Path | `res.partner` 到 `sale.order`、`purchase.order` 的关系路径可用；完整深度 2 与 `project.task` 仍未验证 | `relation_paths` |
| Q5 NFR 验证条件 | 未满足：缺少完整模型、百万级数据、索引基线和隔离性能环境 | NFR-001 Benchmark Profile 对照 |

## 4. 方法与执行

### 4.1 实际执行方法

- 使用 `data/generate.py` 以固定种子 `20261001` 生成查询语料。
- 使用 Odoo shell 加载 `scripts/run.py`；销售采购模块已预先通过 Odoo 模块安装流程启用。
- 所有业务查询使用 Odoo ORM `search` / `search_count`。
- 并发测试为每个线程创建独立 Odoo cursor 和 Environment。
- 模拟业务数据使用 `data/generate_orm.py` 通过 ORM 创建并提交；未使用 `sudo()`，未执行裸 SQL。

### 4.2 与 PLAN 的差异

- PLAN 目标是 10 个资源和百万级数据；当前数据库不满足模型和数据条件，因此未伪造该基准。
- 未能验证特定 B-tree、`pattern_ops`、`pg_trgm` 索引的效果；本轮没有为生产模块或数据库创建索引。
- 只读基准使用当前数据库实际记录，结果仅代表当前环境。

### 4.3 实际环境规格

| 项 | 实际值 |
|---|---|
| Odoo | 18.0 |
| 数据库 | `odoo18ce` |
| 数据库连接 | `odoo.conf` 指定的本地端口 |
| Python | 项目 `./venv` |
| 实际业务数据写入 | 5,000 客户 + 5,000 销售订单 + 5,000 采购订单 |
| 目标资源数量 | 10 |
| 实际可用目标模型 | `res.partner`、`sale.order`、`purchase.order`、`stock.picking`、`account.move`、`product.product`、`stock.quant` |
| 实际目标模型记录数 | `5044`、`5024`、`5011`、`17`、`48`、`43`、`38` |

## 5. 结果

### 5.1 模型可用性

完整模型可用性、记录数量和关系路径状态见：

- `results/spike_result.json`

本轮确认，8 个目标技术模型中 7 个可用：

| 模型 | 可用 | 记录数 |
|---|---:|---:|
| `res.partner` | Yes | 5044 |
| `sale.order` | Yes | 5024 |
| `purchase.order` | Yes | 5011 |
| `stock.picking` | Yes | 17 |
| `account.move` | Yes | 48 |
| `product.product` | Yes | 43 |
| `project.task` | No | — |
| `stock.quant` | Yes | 38 |

因此不能把当前可用模型结果解释为跨 10 Resource、每资源百万记录的结果。

### 5.2 延迟统计

每个查询执行 20 次。结果如下：

| 查询 | P50 ms | P95 ms | P99 ms | Max ms |
|---|---:|---:|---:|---:|
| Identifier exact | 0.235 | 0.354 | 0.435 | 0.435 |
| Identifier prefix | 1.747 | 2.613 | 2.885 | 2.885 |
| Identifier contains | 0.217 | 0.224 | 0.260 | 0.260 |
| Entity exact | 0.174 | 0.187 | 0.193 | 0.193 |
| Entity contains | 0.204 | 0.221 | 0.231 | 0.231 |
| Product identifier contains | 0.205 | 0.316 | 1.674 | 1.674 |
| Sale identifier contains | 0.155 | 0.166 | 0.427 | 0.427 |
| Purchase identifier contains | 1.660 | 1.841 | 2.426 | 2.426 |

20 并发查询结果：

| 请求数 | P50 ms | P95 ms | P99 ms | Max ms | 错误 |
|---:|---:|---:|---:|---:|---:|
| 20 | 2.464 | 6.300 | 6.618 | 6.618 | 0 |

20 并发读查询的统计写入 `concurrent_queries`。

由于当前数据规模不满足 NFR-001，所有延迟数据只能作为当前小规模 ORM 查询基线，不作为：

- 百万级数据性能结论；
- 首次结果 P95 达标证明；
- 完整结果 P95 达标证明；
- 索引方案证明。

### 5.3 SQL Plan

本轮不执行裸 SQL，也未引入生产索引，因此没有可报告的 SQL Plan。需要后续在隔离技术验证环境中，通过受控技术验证方式补充数据库计划和索引对照。

### 5.4 pg_trgm 验证结果

在用户临时授权下，本次执行了受控 PostgreSQL 扩展和 GIN `gin_trgm_ops` 对照；结果见 `results/pg_trgm_result.json`。

环境事实：

| 项目 | 结果 |
|---|---|
| PostgreSQL | 16.14 |
| `pg_trgm` | 已安装，版本 1.6 |
| 测试查询 | 三个 `ILIKE '%GS01-%'` 查询 |
| 测试数据 | 当前 GS01 客户、销售订单、采购订单数据 |
| 临时索引 | 已创建、测试后已清理 |

自然优化器计划在当前约 5,000 条/模型的小规模数据上仍选择 `Seq Scan`；这不表示 GIN 索引不可用，而是当前规模下顺序扫描成本更低：

| 查询 | 无索引执行时间 | 有索引自然计划 | 强制索引计划 |
|---|---:|---|---|
| `res.partner.ref` | 1.266 ms | Seq Scan | Bitmap Index Scan |
| `sale.order.client_order_ref` | 0.361 ms | Seq Scan | Bitmap Index Scan |
| `purchase.order.partner_ref` | 0.348 ms | Seq Scan | Bitmap Index Scan |

强制索引对照均实际出现：

```text
Bitmap Heap Scan
└── Bitmap Index Scan (... gin_trgm_ops)
```

对应临时索引大小约为 248–280 kB，测试结束后均已删除。该结果证明 `pg_trgm` 扩展和 GIN `gin_trgm_ops` 索引路径可工作，但不能证明当前小规模数据会自动选用索引，也不能证明百万级 NFR-001。

后续仍需在隔离性能数据库中执行：

1. 10 个资源、每资源百万级数据；
2. 无索引、GIN `gin_trgm_ops`、必要时 GiST 对照；
3. 相同查询语料、并发、冷/暖缓存条件；
4. 记录执行计划、P50/P95/P99、CPU、IO 和索引体积；
5. 不将小规模结果外推到生产。

### 5.4 副作用与边界案例

- 缺失模型：明确记录 `MODEL_MISSING`，不静默跳过；当前为 `project.task`。
- `res.partner` 到销售、采购订单的关系路径已确认可用，其他目标关系仍需补充。
- 模拟业务写入使用 `GS01-` 标记并可重复复用，避免重复创建。
- 当前数据量不足：阻止将小规模结果外推到 NFR。

## 6. 分析

### 6.1 与成功标准对比

- Q1：部分满足。查询可执行且可测量，但不满足规模条件。
- Q2：不满足。目标模型集合和数据规模不完整。
- Q3：部分满足。并发机制可执行，但不具备目标数据基线。
- Q4：部分满足。销售、采购关系路径可用，但完整深度 2 和项目任务关系未验证。
- Q5：不满足。无法在当前环境完成 NFR-001 的必要验证。

### 6.2 与 SRS 对比

- SRS FR-L1/FR-L2 的业务搜索范围依赖可配置 Business Resource；当前环境无法提供完整资源集合。
- SRS NFR-001 要求固定 Benchmark Profile 和 P95/P99 指标；当前环境不具备完整 Profile。
- SRS BR-012 的 Relation Path 深度 2 需要完整关联模型和权限上下文；本轮未建立。
- SRS CFG-011 的资源数、超时和最大返回量可以作为后续执行参数，但尚未验证其技术可行性。

### 6.3 未预期发现

项目数据库当前仍不是完整的 Global Search 目标模块测试基线，`project.task` 等标准业务模型未安装。这是进入 TDD 前必须解决的环境问题，而不是可以由 Spike 脚本绕过的问题。

## 7. 结论

| 子问题 | 结论 |
|---|---|
| Q1 | 有条件可行：ORM 查询可运行，但性能不可外推 |
| Q2 | 不可行于当前环境：模型和数据基线不完整 |
| Q3 | 有条件可行：20 独立 ORM cursor 可执行，但规模不足 |
| Q4 | 部分验证：销售、采购关系路径可用，完整深度 2 未验证 |
| Q5 | 未验证：NFR-001 的完整验证条件不成立 |

整体结论：**当前环境不能证明 SPIKE-GS-01 成功，也不能证明 NFR-001 达标。** 销售采购模块和业务数据路径已证明 ORM 查询可执行，但仍必须在隔离性能环境中补齐目标模块、百万级数据规模和索引对照后再作最终判断。

## 8. 对 SRS 的影响

- SRS FR-L1-001 ~ FR-L1-003：查询能力仍需在完整资源集合上验证。
- SRS FR-L2-001 ~ FR-L2-004：实体和关系扩展仍需完整模型验证。
- SRS NFR-001：不能标记为 VERIFIED；需要补充性能 Spike。
- SRS BR-012：已获得销售、采购关系路径的部分证据，仍需要补充深度 2 Relation Path 验证。
- SRS CFG-011：配置项可保留，但默认值需在技术验证环境中验证。
- V1 范围：本轮没有足够证据要求调整，但不能进入“性能已证明”的状态。

## 9. 对技术方案的影响

| 事项 | 结论 |
|---|---|
| 外部搜索引擎 | 未引入；本轮未证明必须引入 |
| LLM | 未引入 |
| NFR-001 | 暂不修改；补充隔离性能 Spike |
| 数据模型 | 不因本轮 Spike 新增模型；通过官方模块启用销售采购 |
| 索引策略 | `pg_trgm` + GIN 路径已在小规模数据验证；百万级效果未验证 |
| 权限模型 | 仅使用当前 ORM 用户上下文，未完成跨公司/Record Rule Spike |

## 10. 未解决的问题

1. 如何提供 10 个目标 Resource 的完整 Odoo 模块依赖（当前 `project.task` 仍缺失）。
2. 如何建立每资源 100 万条的隔离、可复现、脱敏性能数据库。
3. 如何在不修改生产模块的前提下验证 B-tree、`pattern_ops`、`pg_trgm` 对照。
4. 如何建立深度 2 Relation Path 并纳入 Record Rule。
5. 如何在实际性能环境中确定 NFR-002 的最终数据新鲜度上限。

## 11. 产出物清单

- `mymodules/wd_spike_global_search/spike_01_multi_model_search/PLAN.md`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/README.md`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/data/generate.py`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/scripts/run.py`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/results/query_corpus.json`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/results/spike_result.json`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/results/pg_trgm_result.json`
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/reports/REPORT.md`

## 12. 复现说明

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
python3 mymodules/wd_spike_global_search/spike_01_multi_model_search/data/generate.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_01_multi_model_search/scripts/run.py
```

预期输出：

- 生成 `results/query_corpus.json`
- 生成 `results/spike_result.json`
- 终端打印结果文件路径

## 13. 参考

- `docs/requirement/SRS_global_search.md`
- `docs/requirement/RAR_global_search.md`
- SRS FR-L1-001 ~ FR-L1-003
- SRS FR-L2-001 ~ FR-L2-004
- SRS NFR-001
- SRS BR-012
- SRS CFG-011

## 14. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-01 | 初始报告；记录模型预检和当前环境局部 ORM 基准 |
| v0.2 | 2026-10-01 | 启用销售采购并通过 ORM 写入模拟数据；补充销售、采购查询和第二轮基准结果 |
