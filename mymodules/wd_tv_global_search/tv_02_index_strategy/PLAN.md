# TV-02 索引策略对照

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-02 |
| 名称 | 索引策略对照 |
| 版本 | v0.1 |
| 状态 | Executed |
| 负责人 | Odoo 18 Technical Verification 助手 |
| 日期 | 2026-10-03 |

## 2. 背景与动机

验证 SRS NFR-001、CFG-011 在真实 PostgreSQL 数据规模下的索引选择。GS-01 已确认 `pg_trgm` 1.6 和 GIN `gin_trgm_ops` 技术路径可运行，但未完成百万级策略对照。

本 TV 使用 TV-01 已完成的独立数据库 fixture（100,000 条/逻辑资源，因用户授权的规模降级），不在共享数据库执行。索引 DDL 和 `EXPLAIN ANALYZE` 仅在该隔离数据库使用用户明确授权的临时权限。

## 3. 验证问题

1. 无索引的精确、前缀、包含匹配 P95 是多少？
2. B-tree 是否适合精确匹配？
3. `text_pattern_ops` 是否适合前缀匹配？
4. GIN `pg_trgm` 是否适合包含匹配？
5. GiST `pg_trgm` 是否适合包含匹配？
6. 在不同选择率下何时从 Seq Scan 切换到 Bitmap/Index Scan？
7. 每种索引的大小和构建开销是多少？
8. 冷缓存和热缓存差异是多少？

每个策略必须保存 P50/P95/P99、EXPLAIN JSON、扫描节点、索引大小和构建耗时。缺少独立冷缓存环境时，冷缓存判定为未验证。

## 4. 假设

### 技术

- `res_partner.ref` 是代表性 Identifier 字段。
- 精确使用 `=`，前缀使用 `LIKE 'prefix%'`，包含使用 `LIKE '%fragment%'`。
- `pg_trgm` 1.6 已安装。
- 临时索引只能创建在隔离数据库，并在测试结束后清理/恢复。

### 数据

- 使用 `TV01-PARTNER-` 100,000 条 `res.partner.ref` 数据。
- 数据来自独立数据库 `wd_tv_gs01_20261002_100k`。
- 代表性结果需在 TV-02 报告中明确不能外推为 1,000,000 条。

### 环境

- PostgreSQL 16.14；
- Odoo 18；
- 10 核、16 GiB；
- 当前数据库已有 Odoo 默认 `res_partner__ref_index`，基线阶段临时移除，完成后恢复。

## 5. 范围

### In Scope

- 无索引、B-tree、`text_pattern_ops`、GIN/GiST `gin_trgm_ops`；
- 热缓存重复测量；
- EXPLAIN ANALYZE、Buffers、索引大小、构建耗时；
- 选择率切换点的计划对照；
- 临时索引清理与默认索引恢复。

### Out of Scope

- 共享数据库；
- 业务数据裸 SQL 写入；
- Elasticsearch/OpenSearch/LLM/向量检索；
- 生产永久索引变更；
- 100 万条/资源的完整 NFR-001 证明；
- 未经授权的 OS/数据库缓存清理。

## 6. 方法

### 查询

- Exact：`ref = 'TV01-PARTNER-0000001'`
- Prefix：`ref LIKE 'TV01-PARTNER-0000001%'`
- Contains：`ref LIKE '%TV01-PARTNER%'`

每个策略/查询热身 5 次后测量 20 次，使用 `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` 记录执行时间和计划节点。

### 策略

1. No index；
2. `btree (ref)`；
3. `btree (ref text_pattern_ops)`；
4. `gin (ref gin_trgm_ops)`；
5. `gist (ref gist_trgm_ops)`.

每次切换前删除 TV-02 临时索引。默认 Odoo `res_partner__ref_index` 在无索引阶段移除，测试结束后恢复。

### 切换点

在代表性 B-tree、pattern_ops 和 GIN 索引存在时，使用不同前缀选择率执行 `EXPLAIN`，记录 Seq Scan、Index Scan 和 Bitmap Index Scan 的切换计划。

### 指标

- P50/P95/P99/max；
- execution time；
- planning time；
- shared hit/read blocks；
- 计划节点；
- 索引字节数；
- 构建秒数；
- 缓存模式。

## 7. 通过标准

| 子问题 | 通过标准 |
|---|---|
| 每种策略 P95 | 每种策略至少 20 次可复现，且原始 JSON 可追溯 |
| 推荐策略 | 根据实际计划、P95、索引大小和查询类型给出明确推荐 |
| 适用场景 | Exact/prefix/contains 均明确适用或不适用 |
| 切换点 | 至少记录三种选择率的实际计划 |
| 缓存 | 热缓存完成；冷缓存若无合规隔离环境则明确未验证 |

整体结论可为通过、部分通过或未验证；不能用单一策略结果替代全部对照。

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 临时删除 Odoo 默认索引 | 仅在隔离库执行，脚本 finally 恢复 |
| 索引构建时间过长 | 记录失败并清理已建索引 |
| 100,000 条不足以证明百万级 | 报告中明确规模限制 |
| 冷缓存需要越权操作 | 不清理缓存，标记未验证 |
| GIN/GiST 计划受选择率影响 | 保存完整 EXPLAIN JSON 和多选择率计划 |

## 9. 产出物

- `PLAN.md`
- `README.md`
- `scripts/run.py`
- `results/index_strategy_result.json`
- `evidence/*.json`
- `reports/REPORT.md`

## 10. 参考

- SRS NFR-001、CFG-011；
- `docs/verification/SPIKE_global_search_report.md` GS-01；
- TV-01 `generation_result.json`；
- PostgreSQL `pg_trgm` 1.6 文档。

## 11. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 创建 TV-02 计划 |
| v0.2 | 2026-10-03 | 完成 100,000 条/资源索引对照、ORM 写入测量和计划证据 |
