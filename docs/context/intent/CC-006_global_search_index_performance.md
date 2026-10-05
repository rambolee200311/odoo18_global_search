# CC-006 Global Search 索引与性能

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-006 |
| 版本 | v0.1 DRAFT |
| 状态 | Draft / Ready for Review |
| Intent ID | `GS-SEARCH-INDEX-PERFORMANCE` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 6 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN；[CC-004](./CC-004_global_search_preview_container.md) v0.2 FROZEN；[CC-005](./CC-005_global_search_workspace_query_refinement.md) v0.1 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 在隔离性能环境实现可验证的 PostgreSQL 原生索引策略、迁移/回滚和 NFR-001 性能补测 |
| 批准冻结 | 待评审 |

本 CC 只处理索引、容量探针和性能证据，不引入 Elasticsearch/OpenSearch、LLM、向量检索或外部搜索引擎，不改变业务权限语义。

## 1. 追溯与范围

### 1.1 SRS / TDD 追溯

| 来源 | 本 CC 落实 |
|---|---|
| SRS NFR-001 | 百万级首次结果和完整结果延迟、20 并发错误率 |
| SRS FR-L1、FR-L2 | 精确标识符和前缀查询性能 |
| SRS CFG-011 | 按字段用途选择索引策略 |
| SRS CON-003 | 不依赖外部搜索引擎 |
| TDD §8 | B-tree、`text_pattern_ops`、GIN trigram、GiST 选择条件 |
| TDD §11.4 | 迁移、回滚和写入影响 |
| TDD §12.3 | 性能、EXPLAIN、缓存和并发证据 |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- Exact Identifier B-tree；
- Prefix `text_pattern_ops`；
- Selective Contains GIN `gin_trgm_ops`；
- GiST 仅在明确范围/空间条件下选择；
- 隔离性能数据生成、百万级测试、冷/热缓存对照；
- 20 并发 P50/P95/P99、错误率和 Record Rule 额外开销；
- 索引迁移、校验、失败回滚和写入影响记录；
- EXPLAIN、索引大小、选择率和测试报告。

### 1.3 超出范围

- 修改官方 `odoo/` 或官方 addons；
- 修改业务权限、ACL、Record Rule 或 Published 配置语义；
- 外部搜索引擎、全文引擎、LLM、向量索引；
- 在生产库直接生成百万级数据或直接执行未经隔离验证的迁移；
- 为了满足阈值而隐藏权限过滤、减少结果或返回猜测数据。

## 2. 索引与迁移契约

| 查询用途 | 默认策略 | 选择条件 |
|---|---|---|
| Exact Identifier | B-tree | 精确匹配且字段选择率可接受 |
| Prefix | B-tree + `text_pattern_ops` | 前缀匹配且数据库排序规则满足条件 |
| Selective Contains | GIN + `gin_trgm_ops` | 选择率和写入成本经证据确认 |
| Range/空间 | GiST | 仅存在明确范围/空间查询且 TDD 条件满足 |

- 高选择率查询允许 Seq Scan，不得强制索引；
- 索引来源必须与 Published 字段用途配置一致；
- 迁移必须可重复、可检查、可回滚；
- 失败时删除新索引并恢复旧策略；
- 记录索引大小、创建耗时、写入影响和锁等待。

## 3. 性能验收契约

硬闸门：

- 百万级首次结果 P95 ≤ 2 秒；
- 百万级完整结果 P95 ≤ 5 秒；
- 20 并发错误率 ≤ 1%；
- 冷缓存和热缓存均有可复现结果；
- Record Rule 额外开销有单独对照。

软闸门：

- P50/P95/P99 全部记录；
- EXPLAIN、索引大小、选择率、数据库版本、数据规模和硬件环境完整记录；
- 不达标时输出瓶颈定位，不得用范围缩减伪造通过。

## 4. 必需变更

| ID | 变更 | 验证 |
|---|---|---|
| CC6-CHANGE-001 | 字段用途到索引策略的映射可审计 | CC6-TEST-001 |
| CC6-CHANGE-002 | 索引迁移支持校验和回滚 | CC6-TEST-002 |
| CC6-CHANGE-003 | 百万级隔离性能数据集和基线 | CC6-TEST-003 |
| CC6-CHANGE-004 | 冷/热缓存和 20 并发对照 | CC6-TEST-004 |
| CC6-CHANGE-005 | Record Rule 额外开销证据 | CC6-TEST-005 |

## 5. 测试契约

| ID | 内容 | 类型 | 预期 |
|---|---|---|---|
| CC6-TEST-001 | 索引策略与配置一致性 | 集成 | 每个索引均有字段用途和选择理由 |
| CC6-TEST-002 | 迁移成功、失败和回滚 | 集成 | 旧策略可恢复，无半成品索引 |
| CC6-TEST-003 | 百万级首次/完整结果 | 性能 | P95 阈值和 EXPLAIN 证据完整 |
| CC6-TEST-004 | 冷缓存/热缓存、20 并发 | 性能 | P50/P95/P99、错误率和缓存状态完整 |
| CC6-TEST-005 | Record Rule 额外开销 | 性能+权限 | 对照数据不绕过当前用户权限 |
| CC6-TEST-006 | 既有 Search/Workspace 回归 | Odoo+浏览器 | CC-001~005 行为不回归 |

## 6. 安全、数据和停止条件

- 性能环境与业务环境隔离，fixture 使用唯一标记并可清理；
- 性能数据不得进入生产库；
- 所有查询继续使用当前用户 ORM 和 CC-003 权限边界；
- 任何需要 `sudo()` 读取业务数据、修改官方代码或引入外部引擎的情况立即停止；
- 索引迁移失败不可恢复、锁影响不可接受、权限结果变化或数据泄露时立即停止；
- 百万级阈值无法达标时不得降低阈值，提交 NFR/架构评审。

## 7. 实施结构与证据

```text
services/index_strategy.py       # 配置到策略映射与校验
migrations/                       # 可回滚索引迁移
tests/performance/                # 隔离数据和性能测试
docs/context/history/             # IHR、ATR、性能报告
```

每次性能报告必须包含：commit、配置版本、数据库版本、数据规模、缓存状态、并发数、P50/P95/P99、错误率、EXPLAIN、索引大小、写入影响和 Record Rule 对照。

## 8. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC6-DEC-001 | 先做隔离性能证据再迁移生产 | 直接在业务库建索引 | 避免不可逆风险 |
| CC6-DEC-002 | 按用途选择索引 | 单一通用索引 | 符合 TDD §8 和选择率事实 |
| CC6-DEC-003 | 高选择率允许 Seq Scan | 强制使用索引 | 避免索引反而降低性能 |
| CC6-DEC-004 | Record Rule 单独测量 | 性能测试使用超级用户 | 保持权限边界真实 |

未经用户批准冻结，不得实施 CC-006。
