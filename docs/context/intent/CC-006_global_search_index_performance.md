# CC-006 Global Search 索引与性能

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-006 |
| 版本 | v0.1 DRAFT |
| 状态 | FROZEN，进入实施（可选） |
| Intent ID | `GS-SEARCH-INDEX-PERFORMANCE` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 6 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN；[CC-004](./CC-004_global_search_preview_container.md) v0.2 FROZEN；[CC-005](./CC-005_global_search_workspace_query_refinement.md) v0.1 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 在开发环境完成轻量性能验证，确认搜索在真实数据量下可用 |
| 批准冻结 | 2026-10-05 22:06，用户确认冻结并进入实施（可选） |

本 CC 为可选工作。如 CC-001~CC-005 已通过且轻量验证足够，可跳过并在上线后监控。本 CC 只处理索引、容量探针和性能证据，不引入 Elasticsearch/OpenSearch、LLM、向量检索或外部搜索引擎，不改变业务权限语义。

## 1. 追溯与范围

### 1.1 SRS / TDD 追溯

| 来源 | 本 CC 落实 |
|---|---|
| SRS NFR-001 | 5 万级首次结果延迟、5 并发错误率；按 3PL 内部使用场景调整基线 |
| SRS FR-L1、FR-L2 | 精确标识符和前缀查询性能 |
| SRS CFG-011 | 按字段用途选择索引策略 |
| SRS CON-003 | 不依赖外部搜索引擎 |
| TDD §8 | B-tree、`text_pattern_ops`、GIN trigram 选择条件 |
| TDD §11.4 | 索引创建和写入影响 |
| TDD §12.3 | 性能、EXPLAIN、热缓存和并发证据 |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- Exact Identifier B-tree；
- Prefix `text_pattern_ops`；
- Selective Contains GIN `gin_trgm_ops`（仅在需要时）；
- 开发环境性能数据生成、5 万级测试、热缓存；
- 5 并发 P50/P95/P99 和错误率；
- 索引创建、校验和写入影响记录；
- EXPLAIN、索引大小和测试报告。

### 1.3 超出范围

- 修改官方 `odoo/` 或官方 addons；
- 修改业务权限、ACL、Record Rule 或 Published 配置语义；
- 外部搜索引擎、全文引擎、LLM、向量索引；
- 在生产库直接生成数据或直接执行未经验证的迁移；
- 为了满足阈值而隐藏权限过滤、减少结果或返回猜测数据。
- 冷缓存测试；
- 20 并发测试；
- Record Rule 单独对照；
- 独立索引迁移/回滚演练。

## 2. 索引契约

| 查询用途 | 默认策略 | 选择条件 |
|---|---|---|
| Exact Identifier | B-tree | 精确匹配且字段选择率可接受 |
| Prefix | B-tree + `text_pattern_ops` | 前缀匹配且数据库排序规则满足条件 |
| Selective Contains | GIN + `gin_trgm_ops` | 选择性包含匹配 |

- 高选择率查询允许 Seq Scan；
- 索引来源必须与 Published 字段用途配置一致；
- 索引创建可在维护窗口执行；
- 记录索引大小和创建耗时。

## 3. 性能验收契约

硬闸门：

- 5 万级首次结果 P95 ≤ 2 秒；
- 5 并发错误率 ≤ 1%。

软闸门：

- P50/P95/P99 记录；
- EXPLAIN、索引大小、数据库版本、数据规模和硬件环境记录；
- 不达标时输出瓶颈定位。

## 4. 必需变更

| ID | 变更 | 验证 |
|---|---|---|
| CC6-CHANGE-001 | 字段用途到索引策略的映射可审计 | CC6-TEST-001 |
| CC6-CHANGE-002 | 索引创建和校验 | CC6-TEST-002 |
| CC6-CHANGE-003 | 5 万级性能数据集和基线 | CC6-TEST-003 |
| CC6-CHANGE-004 | 5 并发对照 | CC6-TEST-004 |

## 5. 测试契约

| ID | 内容 | 类型 | 预期 |
|---|---|---|---|
| CC6-TEST-001 | 索引策略与配置一致性 | 集成 | 每个索引均有字段用途和选择理由 |
| CC6-TEST-002 | 索引创建和校验 | 集成 | 索引创建成功，无锁表问题 |
| CC6-TEST-003 | 5 万级首次结果 | 性能 | P95 ≤ 2 秒，EXPLAIN 证据完整 |
| CC6-TEST-004 | 5 并发 | 性能 | P50/P95/P99、错误率完整 |
| CC6-TEST-005 | 既有 Search/Workspace 回归 | Odoo+浏览器 | CC-001~005 行为不回归 |

## 6. 安全、数据和停止条件

- 性能数据在开发环境生成，不进入生产库；
- 所有查询继续使用当前用户 ORM 和 CC-003 权限边界；
- 任何需要 `sudo()` 读取业务数据、修改官方代码或引入外部引擎的情况立即停止；
- 索引创建失败、锁影响不可接受、权限结果变化或数据泄露时立即停止；
- 5 万级阈值无法达标时，记录瓶颈并提交评审。

## 7. 实施结构与证据

```text
services/index_strategy.py       # 配置到策略映射与校验
tests/performance/                # 开发环境性能测试
docs/context/history/             # IHR、ATR、性能报告
```

每次性能报告必须包含：commit、配置版本、数据库版本、数据规模、并发数、P50/P95/P99、错误率、EXPLAIN 和索引大小。

## 8. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC6-DEC-001 | 在开发环境做轻量验证 | 在生产环境做正式验证 | 内部系统数据量小，无需正式性能环境 |
| CC6-DEC-002 | 按用途选择索引 | 单一通用索引 | 符合 TDD §8 |
| CC6-DEC-003 | 高选择率允许 Seq Scan | 强制使用索引 | 避免索引反而降低性能 |
| CC6-DEC-004 | 5 并发，不做 20 并发 | 20 并发 | 内部使用并发 5~10 |
| CC6-DEC-005 | 热缓存，不做冷缓存 | 冷/热缓存 | 内部系统持续运行 |
| CC6-DEC-006 | Record Rule 合并到主测试 | 单独对照 | 内部系统权限简单 |
| CC6-DEC-007 | 索引创建在维护窗口 | 在线迁移 | 内部系统可安排维护窗口 |
| CC6-DEC-008 | CC-006 为可选 | 必须执行 | 内部系统性能不是当前上线阻塞项 |

## 9. 可选执行说明

- 预计工作量：0.5~1 人天；
- CC-006 可跳过，不阻塞 CC-001~CC-005 的上线；
- 若执行，通过后作为上线前轻量证据；若跳过，上线后通过监控观察性能；
- 若 5 万级轻量验证不达标，记录瓶颈并决定修复或延期，不降低既定阈值。
