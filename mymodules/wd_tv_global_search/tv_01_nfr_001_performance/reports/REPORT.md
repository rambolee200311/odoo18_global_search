# TV-01 NFR-001 完整性能基线报告

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-01 |
| 名称 | NFR-001 完整性能基线 |
| 版本 | v0.2 |
| 状态 | 有条件通过 |
| 执行日期 | 2026-10-02 |
| 执行人 | Odoo 18 Technical Verification 助手 |
| 数据库 | `wd_tv_gs01_20261002_100k` |
| 随机种子 | 20261002 |

## 2. 摘要

### 核心结论

> **有条件通过。**

在独立数据库中使用真实 Odoo ORM 建立了 10 个逻辑 Business Resource、每个 100,000 条记录，共 1,000,000 条逻辑资源记录。20 并发 ORM 查询无错误，首次结果 P95 为 30.968 ms，完整结果 P95 为 159.302 ms，均低于 NFR-001 的 2 秒/5 秒阈值。

但本次实际规模是用户授权后的 100,000 条/资源，不是 NFR-001 要求的 1,000,000 条/资源；冷缓存、Record Rule 额外开销、SQL Plan 和索引使用未验证。因此不能将 NFR-001 标记为完全通过。

### 关键数据

| 指标 | 实际值 | NFR-001 标准 | 判定 |
|---|---:|---:|---|
| 逻辑资源数 | 10 | 10 | 通过 |
| 每逻辑资源记录数 | 100,000 | 1,000,000 | 未达到 |
| 总逻辑资源记录数 | 1,000,000 | 10,000,000 | 未达到 |
| 20 并发首次结果 P95 | 30.968 ms | <= 2,000 ms | 通过 |
| 20 并发首次结果 P99 | 38.135 ms | 未单独规定 | 记录 |
| 20 并发完整结果 P95 | 159.302 ms | <= 5,000 ms | 通过 |
| 20 并发完整结果 P99 | 183.759 ms | 未单独规定 | 记录 |
| 并发错误率 | 0% | <= 1% | 通过 |
| Relation Path 深度 2 P95 | 0.205 ms | 可复现且满足 NFR | 条件通过 |
| 冷缓存 | 未验证 | 必须有对照 | 未验证 |
| Record Rule 额外开销 | 未验证 | 必须有对照 | 未验证 |

### 对 SRS V1.4 的影响

- FR-L1、FR-L2 的真实 ORM 查询路径在 100,000 条/资源规模下通过本次测量；
- NFR-001 不得标记 VERIFIED，正式百万级基线仍需隔离性能环境；
- CFG-011 不能依据本次 ORM 测量确定生产索引策略；
- V1 范围不调整，不引入 Elasticsearch/OpenSearch/LLM/向量检索。

## 3. 验证问题回顾

| 问题 | 回答 | 数据 | 证据 |
|---|---|---|---|
| 单模型精确匹配 | 100,000 条规模下 P95 均低于 8 ms | `res.partner` 0.643 ms、`sale.order` 7.552 ms、`purchase.order` 6.410 ms、`account.move` 4.932 ms、`product.product` 0.340 ms、`project.task` 8.857 ms | [performance_result.json](../results/performance_result.json) |
| 单模型前缀匹配 | 100,000 条规模下 P95 均低于 33 ms | 最高 `res.partner` 32.724 ms | [performance_result.json](../results/performance_result.json) |
| 单模型包含匹配 | 100,000 条规模下 P95 为 55.093~134.463 ms | 最高 `project.task` 134.463 ms | [performance_result.json](../results/performance_result.json) |
| 20 并发跨资源 | 无错误，首次和完整结果均满足时间阈值 | P95 30.968/159.302 ms | [performance_result.json](../results/performance_result.json) |
| Relation Path 深度 2 | 可执行 | P95 0.205 ms，结果稳定为 1 | [performance_result.json](../results/performance_result.json) |
| Record Rule 额外开销 | 未执行 | 缺少受限用户专用 fixture | 结果中 `NOT_VERIFIED` |
| 冷/热缓存 | 热路径可测，冷缓存未执行 | 不清理数据库缓存 | 结果中 `NOT_VERIFIED` |
| 完整覆盖 | 10 个逻辑资源均达到 100,000 条 | 1,000,000 条逻辑记录 | [generation_result.json](../results/generation_result.json) |

## 4. 方法与执行

### 4.1 实际环境

| 项 | 值 |
|---|---|
| Odoo | 18.0 |
| Python | 3.11.9 |
| PostgreSQL | 16.x 项目实例 |
| CPU | 10 logical cores |
| 内存 | 16 GiB |
| 数据库 | `wd_tv_gs01_20261002_100k` |
| 业务读写 | Odoo ORM |
| `sudo()` | 未使用 |
| 裸 SQL/数据库驱动 | 未使用 |

### 4.2 逻辑资源

| 逻辑资源 | Technical Model | 实际数量 |
|---|---|---:|
| Partner | `res.partner` | 100,000 |
| Sales Order | `sale.order` | 100,000 |
| Purchase Order | `purchase.order` | 100,000 |
| Incoming Picking | `stock.picking` + `picking_type_code=incoming` | 100,000 |
| Outgoing Picking | `stock.picking` + `picking_type_code=outgoing` | 100,000 |
| Internal Picking | `stock.picking` + `picking_type_code=internal` | 100,000 |
| Invoice | `account.move` | 100,000 |
| Product | `product.product` | 100,000 |
| Project Task | `project.task` | 100,000 |
| Stock Quant | `stock.quant` | 100,000 |

### 4.3 与 PLAN 的差异

用户明确授权在百万级 ORM 生成耗时过高时降为 100,000 条/逻辑资源。原百万级尝试在独立数据库 `wd_tv_gs01_20261002` 中产生了部分数据后停止，未用于本报告；本报告使用重新初始化的干净数据库 `wd_tv_gs01_20261002_100k`。

此外，隔离数据库默认只有入库和出库 Picking Type。测试脚本通过 ORM 创建了合法的内部调拨类型和序列配置，随后完成 100,000 条内部调拨记录。

## 5. 结果

### 5.1 数据生成

| 项 | 值 |
|---|---:|
| 目标每资源 | 100,000 |
| 实际每资源 | 100,000 |
| 逻辑资源总数 | 10 |
| 逻辑记录总数 | 1,000,000 |
| ORM 写入 | true |
| 最终生成阶段耗时 | 165.009 秒 |
| 数据标记 | `TV01-` |

原始结果：[generation_result.json](../results/generation_result.json)

### 5.2 单模型首次结果（`search(limit=50)`）

| 模型 | 精确 P95 | 前缀 P95 | 包含 P95 |
|---|---:|---:|---:|
| `res.partner` | 0.310 ms | 31.207 ms | 0.817 ms |
| `sale.order` | 5.872 ms | 11.310 ms | 0.362 ms |
| `purchase.order` | 5.304 ms | 12.537 ms | 11.695 ms |
| `account.move` | 4.189 ms | 4.157 ms | 16.510 ms |
| `product.product` | 0.635 ms | 14.251 ms | 47.445 ms |
| `project.task` | 8.617 ms | 7.819 ms | 34.120 ms |

### 5.3 单模型完整结果（`search(limit=False)`）

| 模型 | 精确 P95 | 前缀 P95 | 包含 P95 |
|---|---:|---:|---:|
| `res.partner` | 0.643 ms | 32.724 ms | 69.531 ms |
| `sale.order` | 7.552 ms | 14.488 ms | 55.093 ms |
| `purchase.order` | 6.410 ms | 14.826 ms | 67.683 ms |
| `account.move` | 4.932 ms | 5.258 ms | 101.569 ms |
| `product.product` | 0.340 ms | 13.223 ms | 88.380 ms |
| `project.task` | 8.857 ms | 6.453 ms | 134.463 ms |

### 5.4 20 并发

| 场景 | 请求数 | 错误 | 错误率 | P50 | P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| 首次结果 | 20 | 0 | 0% | 13.276 ms | 30.968 ms | 38.135 ms |
| 完整结果 | 20 | 0 | 0% | 29.491 ms | 159.302 ms | 183.759 ms |

### 5.5 Relation Path 深度 2

采用 `res.partner -> sale.order -> partner_id` 的 ORM 关系扩展，每次重复 20 次：

- P50：0.163 ms；
- P95：0.205 ms；
- P99：1.490 ms；
- 结果计数：稳定为 1；
- 未使用 `sudo()`。

### 5.6 冷缓存、Record Rule 和 SQL Plan

| 项 | 结果 | 原因 |
|---|---|---|
| 冷缓存 | `NOT_VERIFIED` | 清理 PostgreSQL/OS 缓存需要直接数据库或系统操作，不符合当前 ORM-only 纪律 |
| Record Rule 额外开销 | `NOT_VERIFIED` | 本 TV 尚未建立独立受限用户 fixture；uid 1 测量不能代表受限用户 |
| SQL Plan | `NOT_VERIFIED` | 当前执行纪律禁止裸 SQL 和数据库驱动；ORM 结果不能替代 `EXPLAIN ANALYZE` |
| 索引使用 | `NOT_VERIFIED` | 未以数据库直写方式创建或检查索引 |

## 6. 分析

### 6.1 与通过标准对比

在 100,000 条/逻辑资源规模下：

- 10 个逻辑资源全部完成；
- 20 并发错误率为 0%，满足 <= 1%；
- 首次结果 P95 为 30.968 ms，满足 2 秒；
- 完整结果 P95 为 159.302 ms，满足 5 秒；
- Relation Path 深度 2 可重复执行；
- 结果排序和计数未作为本 TV 的主测量项。

### 6.2 与 Spike-GS-01 对比

GS-01 在约 5,000 条级别得到 20 并发 P95 6.300 ms。本次 100,000 条/逻辑资源得到首次结果 P95 30.968 ms、完整结果 P95 159.302 ms，延迟仍远低于 NFR 阈值，但不能线性外推到 1,000,000 条。

### 6.3 未预期发现

1. 隔离数据库没有默认内部 Picking Type，已通过 ORM 创建测试专用类型；
2. `stock.quant` 不接受非可库存产品，已通过 ORM 将 TV01 产品设置为 `is_storable=True`；
3. 百万级真实 ORM 生成在共享机器上耗时过高，用户授权后切换为 100,000 条基线；
4. 单模型包含匹配的完整结果中，`project.task` P95 最高，为 134.463 ms。

## 7. 结论

| 子问题 | 结论 | 条件 |
|---|---|---|
| 精确匹配 | 有条件通过 | 仅在 100,000 条/资源 |
| 前缀匹配 | 有条件通过 | `pattern_ops` 使用未通过 SQL Plan 验证 |
| 包含匹配 | 有条件通过 | `pg_trgm` 使用未通过 SQL Plan 验证 |
| 20 并发 | 有条件通过 | 规模低于 NFR-001，热路径测量 |
| 深度 2 关系 | 有条件通过 | 仅验证一条固定路径 |
| Record Rule 开销 | 未验证 | 缺少受限用户 fixture |
| 冷缓存差异 | 未验证 | 不执行缓存清理 |
| 完整模型覆盖 | 有条件通过 | 逻辑资源完整，但每资源为 100,000 |

### 整体结论

**有条件通过。**

条件是：

1. 结果只证明 100,000 条/逻辑资源规模；
2. 不得将本报告作为 NFR-001 百万级 VERIFIED 证据；
3. 生产索引策略仍需 TV-02；
4. 权限额外开销需 TV-04；
5. 冷缓存需在合规的隔离性能环境中补测。

## 8. 对 SRS 的影响

### 已获得技术事实

- FR-L1、FR-L2 的真实 ORM 查询形态在 100,000 条/资源下可运行；
- BR-012 的多资源基础查询可在 20 并发下执行；
- `project.task` 在安装 `project` 模块后可纳入资源；
- NFR-001 的时间阈值在本次缩小规模热路径中满足。

### 需要技术方案调整

- CFG-011 继续保留索引策略配置点，等待 TV-02；
- BR-012 需要在正式实现中保留每资源超时和部分失败隔离；
- 受限用户查询必须使用真实用户上下文，等待 TV-04；
- 深度 2 Relation Path 需要配置化并限制最大深度。

### 不修改事项

- 不修改 SRS V1.4 业务范围；
- 不引入外部搜索引擎、LLM、向量检索；
- 不把 NFR-001 标为完全通过。

## 9. 对技术方案的影响

| 领域 | 影响 |
|---|---|
| 索引策略 | 本 TV 不决定 B-tree、`pattern_ops`、GIN/GiST；交由 TV-02 |
| 数据模型 | 10 个逻辑资源可通过 Business Resource 配置表达；Picking 方向必须作为资源维度 |
| 权限边界 | 本 TV 未完成 Record Rule 对照；实现必须按当前用户执行并失败关闭 |
| Preview 容器 | 本 TV 不覆盖浏览器 Preview；继续由 TV-05 验证 |
| 失败隔离 | 多模型并发请求必须允许单资源失败而不泄露其他资源结果 |
| 数据规模 | 生产验收仍需独立性能环境，不得以共享库的 100,000 条测试代替 |

## 10. 未解决的问题

1. 每资源 1,000,000 条的真实 NFR-001 基线；
2. B-tree、`pattern_ops`、GIN/GiST `pg_trgm` 的 SQL Plan 和索引大小；
3. PostgreSQL/OS 冷缓存与热缓存差异；
4. 受限用户和复杂 Record Rule 的额外开销；
5. 10 个资源完整并发请求中包含 Picking、Quant 等所有资源的搜索查询；
6. 8 核/16 GiB/SSD 固定验收环境的可重复性；
7. 完整结果的内存峰值和磁盘 I/O。

## 11. 产出物清单

- [PLAN.md](../PLAN.md)
- [README.md](../README.md)
- [generate.py](../data/generate.py)
- [run.py](../scripts/run.py)
- [generation_result.json](../results/generation_result.json)
- [performance_result.json](../results/performance_result.json)
- 本报告

证据目录当前没有 SQL Plan 或缓存截图；对应缺失已在本报告明确标记为 `NOT_VERIFIED`。

## 12. 复现说明

在项目根目录执行，使用已初始化的隔离数据库：

```bash
TV_DB=wd_tv_gs01_20261002_100k TV_ROWS=100000 TV_CHUNK_SIZE=5000 \
  ./venv/bin/python odoo-bin shell -c odoo.conf \
  -d wd_tv_gs01_20261002_100k --no-http \
  < mymodules/wd_tv_global_search/tv_01_nfr_001_performance/data/generate.py

TV_DB=wd_tv_gs01_20261002_100k \
  ./venv/bin/python odoo-bin shell -c odoo.conf \
  -d wd_tv_gs01_20261002_100k --no-http \
  < mymodules/wd_tv_global_search/tv_01_nfr_001_performance/scripts/run.py
```

脚本会复用 `TV01-` 标记的已有记录，不应在共享数据库 `odoo18ce` 执行。

## 13. 参考

- `docs/requirement/SRS_global_search.md`：NFR-001、CFG-011、FR-L1、FR-L2、BR-012
- `docs/verification/SPIKE_global_search_report.md`：GS-01
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/reports/REPORT.md`
- `mymodules/wd_tv_global_search/tv_01_nfr_001_performance/PLAN.md`

## 14. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-02 | 创建 TV-01 报告结构 |
| v0.2 | 2026-10-02 | 完成 100,000 条/逻辑资源 ORM 基线、并发测量和条件结论 |
