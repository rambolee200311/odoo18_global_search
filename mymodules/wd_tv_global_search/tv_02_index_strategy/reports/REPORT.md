# TV-02 索引策略对照报告

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-02 |
| 名称 | 索引策略对照 |
| 版本 | v0.2 |
| 状态 | 有条件通过 |
| 执行日期 | 2026-10-03 |
| 执行人 | Odoo 18 Technical Verification 助手 |
| 数据库 | `wd_tv_gs01_20261002_100k` |
| 表/字段 | `res_partner.ref` |
| 数据规模 | 100,000 条 |
| PostgreSQL | 16.14 |
| `pg_trgm` | 1.6 |

## 2. 摘要

### 核心结论

> **有条件通过。**

在隔离数据库的 100,000 条 `res_partner.ref` 数据上，索引策略差异可复现：

- 精确匹配推荐 B-tree；
- 前缀匹配推荐 `text_pattern_ops`；
- 选择性包含匹配推荐 GIN `gin_trgm_ops`；
- GiST `gist_trgm_ops` 可以工作，但本次索引更大、构建更慢；
- 高选择率/全表匹配时 PostgreSQL 正确回退到 Seq Scan；
- 热缓存下每种策略均完成 20 次测量并保存 EXPLAIN JSON。

本次数据规模是 100,000 条/资源，不是 NFR-001 要求的 1,000,000 条/资源；冷缓存未验证。因此本报告不能单独证明 NFR-001，也不能直接冻结生产索引参数。

### 关键结果

| 策略 | Exact P95 | Prefix P95 | Contains P95 | 索引大小 | 构建耗时 |
|---|---:|---:|---:|---:|---:|
| 无索引 | 13.526 ms | 13.576 ms | 15.014 ms | 0 | - |
| B-tree | 0.033 ms | 0.017 ms | 16.443 ms | 4,087,808 B | 0.054 s |
| `pattern_ops` | 0.025 ms | 0.036 ms | 15.885 ms | 4,087,808 B | 0.053 s |
| GIN `pg_trgm` | 10.901 ms | 10.378 ms | 9.226 ms | 3,457,024 B | 0.227 s |
| GiST `pg_trgm` | 6.799 ms | 5.785 ms | 8.805 ms | 11,673,600 B | 0.456 s |

### 对 SRS V1.4 的影响

- CFG-011 应明确按查询类型选择索引，而不是配置单一通用索引；
- NFR-001 仍未完全验证，因为本次为 100,000 条/资源；
- 不引入 Elasticsearch/OpenSearch/LLM/向量检索；
- V1 范围不调整。

## 3. 验证问题回顾

| 问题 | 回答 | 数据/证据 |
|---|---|---|
| 无索引 P95 | 可复现，但三个查询均 Seq Scan | [no_index.json](../evidence/no_index.json) |
| B-tree 精确匹配 | P95 0.033 ms，Index Scan | [btree.json](../evidence/btree.json) |
| `pattern_ops` 前缀匹配 | P95 0.036 ms，Bitmap Heap + Bitmap Index | [pattern_ops.json](../evidence/pattern_ops.json) |
| GIN 包含匹配 | P95 9.226 ms，Bitmap Heap + Bitmap Index | [gin_trgm.json](../evidence/gin_trgm.json) |
| GiST 包含匹配 | P95 8.805 ms，Bitmap Heap + Bitmap Index | [gist_trgm.json](../evidence/gist_trgm.json) |
| Seq Scan/Bitmap 切换 | 低选择率使用索引，全量匹配回退 Seq Scan | [selectivity_plans.json](../evidence/selectivity_plans.json) |
| 索引大小/构建开销 | 已测量 | [index_strategy_result.json](../results/index_strategy_result.json) |
| 冷/热缓存 | 热缓存已测，冷缓存未验证 | 结果字段 `cold_cache.status=NOT_VERIFIED` |

## 4. 方法与执行

### 4.1 数据与环境

- 数据库为 TV-01 的隔离 100,000 条 `res.partner.ref` fixture；
- 共享数据库 `odoo18ce` 未使用；
- 原有 Odoo `res_partner__ref_index` 在测试前临时移除，结束后恢复；
- 所有业务测试写入（1,000 条临时 Partner 的创建和删除）使用 Odoo ORM；
- 仅索引 DDL、`EXPLAIN ANALYZE`、索引大小使用用户授权的隔离数据库 PostgreSQL 操作；
- 未执行 OS/PostgreSQL 缓存清理。

### 4.2 查询

| 查询 | SQL 形态 | 预期结果 |
|---|---|---:|
| Exact | `ref = 'TV01-PARTNER-0000001'` | 1 |
| Prefix | `ref LIKE 'TV01-PARTNER-0000001%'` | 1 |
| Contains | `ref LIKE '%PARTNER-0000%'` | 999 |

每个策略先热身 5 次，再执行 20 次 `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`。

### 4.3 与 PLAN 的差异

- 按用户授权使用 100,000 条/资源，而非 1,000,000 条/资源；
- 冷缓存未执行，因为当前环境没有独立缓存清理边界；
- 写入开销采用 Odoo ORM 创建/删除 1,000 条临时 Partner，以及索引构建时间；未使用 SQL 直接插入业务数据。

## 5. 结果

### 5.1 查询 P50/P95/P99

| 策略 | 查询 | P50 | P95 | P99 | 计划节点 |
|---|---|---:|---:|---:|---|
| 无索引 | Exact | 11.889 ms | 13.526 ms | 14.049 ms | Seq Scan |
| 无索引 | Prefix | 11.905 ms | 13.576 ms | 14.039 ms | Seq Scan |
| 无索引 | Contains | 12.453 ms | 15.014 ms | 16.493 ms | Seq Scan |
| B-tree | Exact | 0.022 ms | 0.033 ms | 0.036 ms | Index Scan |
| B-tree | Prefix | 0.015 ms | 0.017 ms | 0.020 ms | Index Scan |
| B-tree | Contains | 13.972 ms | 16.443 ms | 17.362 ms | Seq Scan |
| `pattern_ops` | Exact | 0.019 ms | 0.025 ms | 0.029 ms | Index Scan |
| `pattern_ops` | Prefix | 0.022 ms | 0.036 ms | 0.040 ms | Bitmap Heap + Bitmap Index |
| `pattern_ops` | Contains | 13.756 ms | 15.885 ms | 16.798 ms | Seq Scan |
| GIN `pg_trgm` | Exact | 8.079 ms | 10.901 ms | 11.296 ms | Bitmap Heap + Bitmap Index |
| GIN `pg_trgm` | Prefix | 8.724 ms | 10.378 ms | 11.283 ms | Bitmap Heap + Bitmap Index |
| GIN `pg_trgm` | Contains | 7.898 ms | 9.226 ms | 9.766 ms | Bitmap Heap + Bitmap Index |
| GiST `pg_trgm` | Exact | 5.278 ms | 6.799 ms | 7.300 ms | Index Scan |
| GiST `pg_trgm` | Prefix | 5.376 ms | 5.785 ms | 6.109 ms | Bitmap Heap + Bitmap Index |
| GiST `pg_trgm` | Contains | 7.849 ms | 8.805 ms | 9.308 ms | Bitmap Heap + Bitmap Index |

完整原始结果：[index_strategy_result.json](../results/index_strategy_result.json)

### 5.2 选择率和计划切换

| 策略 | 9 条 | 99 条 | 999 条 | 全量 |
|---|---|---|---|---|
| B-tree | Index Scan | Index Scan | Index Scan | Seq Scan |
| `pattern_ops` | Bitmap Heap + Bitmap Index | Bitmap Heap + Bitmap Index | Bitmap Heap + Bitmap Index | Seq Scan |
| GIN `pg_trgm` | Bitmap Heap + Bitmap Index | Bitmap Heap + Bitmap Index | Bitmap Heap + Bitmap Index | Seq Scan |

实际选择率样本分别为 9、99、999 和 100,000 行；PostgreSQL 会按成本估算选择 Seq Scan 或索引路径，不能强制所有包含查询使用索引。

### 5.3 索引大小与构建开销

| 索引 | 字节 | 约 MiB | 构建秒数 |
|---|---:|---:|---:|
| B-tree | 4,087,808 | 3.90 | 0.054 |
| `pattern_ops` | 4,087,808 | 3.90 | 0.053 |
| GIN `pg_trgm` | 3,457,024 | 3.30 | 0.227 |
| GiST `pg_trgm` | 11,673,600 | 11.14 | 0.456 |

### 5.4 ORM 写入开销

每种策略使用 Odoo ORM 创建并删除 1,000 条临时 Partner：

| 策略 | 创建秒数 | 删除秒数 |
|---|---:|---:|
| 无索引 | 1.698 | 12.279 |
| B-tree | 1.513 | 12.143 |
| `pattern_ops` | 1.606 | 12.186 |
| GIN `pg_trgm` | 1.633 | 12.316 |
| GiST `pg_trgm` | 1.542 | 12.180 |

在本次样本中 ORM 业务逻辑耗时显著高于索引差异，不能据此证明高写入吞吐下的长期维护成本；生产写入压力仍需独立验证。

### 5.5 冷缓存

| 项 | 结果 |
|---|---|
| 热缓存 | 已完成，20 次测量 |
| 冷缓存 | `NOT_VERIFIED` |
| 原因 | 未执行 PostgreSQL/OS 缓存清理，避免超出隔离运行边界 |

## 6. 分析

### 6.1 适用场景

- **B-tree：** 精确 Identifier 查询首选；本次 `Index Scan`，P95 0.033 ms。
- **`text_pattern_ops`：** 前缀匹配首选；本次低选择率使用 Bitmap Index Scan，全量匹配回退 Seq Scan。
- **GIN `gin_trgm_ops`：** 选择性包含匹配首选；索引最小于 GiST，包含 P95 9.226 ms。
- **GiST `gist_trgm_ops`：** 包含查询可用，本次包含 P95 8.805 ms，但索引约为 GIN 的 3.38 倍，构建约 2 倍，暂不推荐作为默认策略。
- **无索引：** 仅适用于小表、低频查询或临时基线。

### 6.2 与通过标准对比

- 每种策略均有 20 次 P95/P99 和完整 EXPLAIN JSON；
- 每种策略均有实际计划节点；
- 索引大小和构建时间可复现；
- ORM 写入创建/删除已对照；
- 热缓存已完成；
- 冷缓存未完成；
- 数据规模为 100,000 而非 1,000,000。

因此策略推荐已满足，但 NFR-001 百万级结论仍为条件性结论。

### 6.3 未预期发现

1. `LIKE '%TV01-PARTNER%'` 命中全部记录时，GIN/GiST 均合理选择 Seq Scan；包含查询必须考虑选择率。
2. `pattern_ops` 的前缀查询可走 Bitmap Heap/Bitmap Index，而不一定显示单纯 Index Scan。
3. GIN 索引大小小于 B-tree，而 GiST 明显更大；本次样本不支持默认 GiST。

## 7. 结论

| 子问题 | 结论 |
|---|---|
| 无索引 P95 | 通过，结果可复现，但仅作基线 |
| B-tree 精确 | 通过，推荐 |
| `pattern_ops` 前缀 | 通过，推荐 |
| GIN `pg_trgm` 包含 | 通过，推荐 |
| GiST `pg_trgm` 包含 | 有条件通过，可用但不推荐默认 |
| Seq/Bitmap 切换 | 通过，已记录四种选择率 |
| 索引大小/构建 | 通过 |
| 冷/热缓存 | 有条件通过，冷缓存未验证 |

### 整体结论

**有条件通过。**

推荐的生产候选策略为：

1. Identifier 精确字段：B-tree；
2. Identifier 前缀字段：`text_pattern_ops`；
3. 任意包含匹配字段：GIN `gin_trgm_ops`；
4. GiST 仅在后续写入/更新模型证明其空间或更新特性有优势时采用。

## 8. 对 SRS 的影响

### 已验证

- CFG-011 可以按查询类型选择索引；
- NFR-001 的索引路径在 100,000 条/资源热缓存样本上满足时间量级；
- PostgreSQL 原生索引足以支持当前 V1 技术路线的候选方案。

### 需要技术方案调整

- Business Resource 配置需要声明 Identifier 的匹配模式；
- 索引迁移必须按字段用途选择 B-tree、`pattern_ops` 或 GIN；
- 生产配置应保留索引创建失败的显式诊断；
- 不应强制全量 `%...%` 查询使用 trigram 索引。

### 仍未验证

- 1,000,000 条/资源；
- 冷缓存；
- 长时间写入维护成本；
- 多字段、多模型同时建立 trigram 索引的总空间和并发影响。

## 9. 对技术方案的影响

| 领域 | 影响 |
|---|---|
| 索引策略 | 按匹配类型拆分，不使用单一通用索引 |
| 数据模型 | Searchable Field 配置需声明 exact/prefix/contains 能力 |
| 权限边界 | 索引不绕过 Odoo Record Rule；搜索仍必须在当前用户上下文过滤 |
| 写入 | 索引维护成本不能从本次 1,000 行 ORM 样本外推；需结合 TV-01/后续写入 TV |
| Preview | 本 TV 不覆盖 Preview，继续由 TV-05 验证 |

## 10. 未解决的问题

1. 1,000,000 条/资源的最终切换点和 P95；
2. 冷缓存与热缓存差异；
3. 10 个资源全部建立候选索引后的空间预算；
4. 真实高频业务写入下 GIN/GiST 维护成本；
5. 多公司 Record Rule 与索引条件组合；
6. PostgreSQL 参数、统计信息和数据分布改变后的计划稳定性。

## 11. 产出物清单

- [PLAN.md](../PLAN.md)
- [README.md](../README.md)
- [run.py](../scripts/run.py)
- [orm_write_benchmark.py](../scripts/orm_write_benchmark.py)
- [index_strategy_result.json](../results/index_strategy_result.json)
- [no_index.json](../evidence/no_index.json)
- [btree.json](../evidence/btree.json)
- [pattern_ops.json](../evidence/pattern_ops.json)
- [gin_trgm.json](../evidence/gin_trgm.json)
- [gist_trgm.json](../evidence/gist_trgm.json)
- [selectivity_plans.json](../evidence/selectivity_plans.json)

TV-02 脚本结束时已删除临时索引并恢复 `res_partner__ref_index`。

## 12. 复现说明

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
TV_DB=wd_tv_gs01_20261002_100k \
  ./venv/bin/python mymodules/wd_tv_global_search/tv_02_index_strategy/scripts/run.py
```

脚本需要已授权的隔离数据库 PostgreSQL 索引 DDL 和 EXPLAIN 权限。业务临时记录仍由 Odoo ORM 创建/删除。不要在共享数据库 `odoo18ce` 执行。

## 13. 参考

- `docs/requirement/SRS_global_search.md`：NFR-001、CFG-011；
- `docs/verification/SPIKE_global_search_report.md`：GS-01；
- `mymodules/wd_tv_global_search/tv_01_nfr_001_performance/reports/REPORT.md`；
- PostgreSQL 16.14 `pg_trgm` 1.6。

## 14. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 创建 TV-02 报告结构 |
| v0.2 | 2026-10-03 | 完成热缓存索引策略、计划、大小和 ORM 写入对照 |
