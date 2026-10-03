# SPIKE-GS-01 多模型搜索性能

## 1. Spike 标识

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-01 |
| 名称 | 多模型搜索性能 |
| 版本 | v0.1 |
| 状态 | Planned |
| 负责人 | Odoo 18 技术 Spike 助手 |
| 日期 | 2026-10-01 |

## 2. 背景与动机

验证不引入 Elasticsearch、OpenSearch、LLM 或向量检索时，使用 PostgreSQL 原生能力与 Odoo ORM 执行跨 Business Resource 搜索是否能支撑 SRS NFR-001。

对应需求：

- SRS FR-L1-001 ~ FR-L1-003
- SRS FR-L2-001 ~ FR-L2-004
- SRS NFR-001
- SRS BR-012
- SRS CFG-011
- RAR §6、§7、§19、§24、§28

如果目标标准模型、数据规模或权限上下文无法建立，必须将其作为不可行性证据，而不是用缩小后的实验冒充 NFR 验证。

## 3. 验证问题

核心问题：不引入外部搜索引擎，跨 10 个 Business Resource 的 Identifier + Entity 搜索能否达到 NFR-001？

子问题：

1. 可用模型上的 Identifier 精确、前缀、包含匹配延迟是多少？
2. 当前 Odoo 数据库是否具备 10 个目标模型和可复现的测试数据基础？
3. 20 并发读查询在当前 ORM/数据库环境下的延迟和错误率是多少？
4. Relation Path 深度 2 的搜索路径是否能在当前环境中建立？
5. 现有环境是否足以验证 NFR-001 的百万级数据和索引假设？

## 4. 假设

### 技术假设

- Odoo 18 ORM 是唯一业务读取入口。
- 查询仅使用 ORM domain，不使用裸 SQL、数据库驱动或 `sudo()`。
- PostgreSQL 原生能力可通过 Odoo 标准 ORM 查询间接使用。

### 数据假设

- 目标资源应包含 `res.partner`、`sale.order`、`purchase.order`、`stock.picking`、`account.move`、`product.product`、`project.task`、`stock.quant` 等模型。
- 目标 Benchmark Profile 为 10 个资源、每个资源 100 万条数据。
- 本次预检不得在共享数据库中写入百万级数据；如环境不满足，必须记录为阻塞事实。

### 环境假设

- 使用项目 `./venv`、`./odoo.conf`。
- Odoo 配置数据库可通过 ORM 只读访问。
- 数据生成使用固定随机种子；本次基准默认不写入业务数据。

假设不成立时，影响是只能得出环境可行性或查询形态的局部结论，不能宣称 NFR-001 已验证。

## 5. 范围

### In Scope

- Odoo 18/当前项目数据库的目标模型预检。
- 可用模型的 ORM Identifier 精确、前缀、包含查询。
- 20 个并发只读 ORM 查询的测量。
- 查询结果数量、P50/P95/P99、错误和模型缺失记录。
- 目标数据规模与索引验证能力的差距分析。

### Out of Scope

- 生产模块代码。
- `odoo/` 和官方 addons。
- Elasticsearch、OpenSearch、LLM、向量检索。
- 裸 SQL、数据库驱动、`sudo()`。
- 共享数据库中的大规模持久化测试数据。
- 直接证明百万级数据下的 NFR-001（当前环境不满足时只记录阻塞）。

### 与 SRS 边界关系

本 Spike 验证 SRS NFR-001、FR-L1/FR-L2、BR-012 和 CFG-011 的技术可行性，不改变这些需求的业务语义。

## 6. 方法

### 测试数据设计

- `data/generate.py` 使用固定随机种子 `20261001` 生成确定性的查询语料。
- 不创建业务记录；查询语料使用稳定的标识符和实体词。
- 实际可见记录数量由 ORM 运行时读取并记录。

### 测试场景

1. 模型/模块可用性预检。
2. 每个可用目标模型的精确、前缀、包含查询。
3. 20 个并发只读 ORM 查询。
4. Relation Path 深度 2 的模型/字段可用性预检。

### 测量指标

- 每个场景的执行次数、结果数量和耗时。
- P50、P95、P99、最大值。
- 并发错误数和异常类型。
- 目标模型缺失数、目标资源缺失数。
- 是否能够建立目标数据规模和索引验证条件。

### 对照组

- 精确匹配、前缀匹配、包含匹配三种 ORM domain。
- 串行查询与 20 并发查询。
- 当前数据库实际数据规模与 SRS Benchmark Profile。

### 执行步骤

1. 用 `data/generate.py` 生成固定查询语料。
2. 用 Odoo shell 执行 `scripts/run.py`。
3. 将 JSON 原始结果写入 `results/`。
4. 基于真实结果生成 `reports/REPORT.md`。

## 7. 成功标准

| 子问题 | 成功标准 | 判定 |
|---|---|---|
| Q1 查询延迟 | 可用模型完成三类查询并有 P50/P95/P99 | 有条件可行；不能替代 NFR |
| Q2 模型/数据基础 | 10 个目标资源均可用且规模满足 Benchmark Profile | 可行；否则不可行/阻塞 |
| Q3 并发 | 20 并发查询有可复现延迟和错误率 | 有条件可行；需结合规模判断 |
| Q4 关系扩展 | 深度 2 的路径配置和 ORM 读取可建立 | 有条件可行或不可行 |
| Q5 NFR 验证条件 | 真实环境具备目标数据规模、索引和性能环境 | 可行；否则 NFR 未验证 |

整体判定：

- **可行**：所有必要条件满足，且指标达到 NFR-001。
- **有条件可行**：查询形态可运行，但数据规模、模型、索引或环境不足以证明 NFR-001。
- **不可行**：出现明确的性能、权限、模型能力或执行错误，且无法通过本技术路线满足。
- **未验证**：关键证据缺失，不能可靠判断。

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 共享数据库写入污染 | 本 Spike 默认只读，不生成业务记录 |
| 目标模块未安装 | 记录缺失模块，不伪造资源覆盖 |
| 数据量远低于基线 | 明确标记 NFR 未验证，后续使用隔离性能环境 |
| ORM 环境并发游标不安全 | 每个线程创建独立 ORM cursor/environment |
| 现有数据包含敏感信息 | 只记录模型计数、耗时和错误摘要，不导出业务字段 |

失败后的下一步：补齐隔离性能数据库和模块依赖，或调整 SRS NFR-001 的可验证基线后重新执行。

## 9. 产出物

- `PLAN.md`
- `README.md`
- `data/generate.py`
- `scripts/run.py`
- `results/query_corpus.json`
- `results/spike_result.json`
- `reports/REPORT.md`

## 10. 参考

- `docs/requirement/SRS_global_search.md`
- `docs/requirement/RAR_global_search.md`
- SRS FR-L1-001 ~ FR-L1-003
- SRS FR-L2-001 ~ FR-L2-004
- SRS NFR-001
- SRS BR-012
- SRS CFG-011
- Odoo 18 ORM API

## 11. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-01 | 初始 Spike Plan |
| v0.2 | 2026-10-01 | 用户授权启用销售采购模块并通过 ORM 模拟带标记数据 |
