# TV-01 NFR-001 完整性能基线

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-01 |
| 名称 | NFR-001 完整性能基线 |
| 版本 | v0.1 |
| 状态 | Executed with reduced scale |
| 负责人 | Odoo 18 Technical Verification 助手 |
| 日期 | 2026-10-02 |

## 2. 背景与动机

验证 SRS NFR-001、CFG-011、FR-L1、FR-L2 和 BR-012 在真实 Odoo ORM、真实数据规模、20 并发和真实权限上下文下是否满足首次结果 P95 <= 2 秒、完整结果 P95 <= 5 秒。

对应 Spike：GS-01 已证明小规模 ORM 查询和 `pg_trgm` 索引路径可运行，但未验证百万级数据、10 个 Business Resource、项目任务模型、深度 2 关联和完整性能环境。

## 3. 验证问题

1. 单模型 Identifier 精确匹配的 P95 是否满足 NFR-001。
2. 单模型 Identifier 前缀匹配的 P95 是否满足 NFR-001。
3. 单模型 Identifier 包含匹配的 P95 是否满足 NFR-001。
4. 10 个逻辑 Business Resource、20 并发下 P95/P99 和错误率是多少。
5. 深度 2 Relation Path 是否可执行以及耗时是多少。
6. 应用 Record Rule 后的额外开销是多少。
7. 冷缓存与热缓存差异是多少。
8. `project.task` 是否补齐并纳入真实数据规模。

子问题只有在数据规模、环境规格、ORM 查询和对应证据均存在时才判定通过。缺少索引计划或冷缓存证据时判定为未验证，不以替代指标推断通过。

## 4. 假设

### 技术

- 业务数据创建、读取和权限验证全部使用 Odoo ORM。
- 每个并发请求使用独立 ORM cursor 和 Environment。
- 不使用 `sudo()`、裸 SQL、数据库驱动或直接数据库读写。
- 索引是否被使用只能通过允许的 ORM 测量和 Odoo 日志记录；在当前项目纪律下不能生成 SQL Plan。

### 数据

- 10 个逻辑资源为：`res.partner`、`sale.order`、`purchase.order`、`stock.picking.incoming`、`stock.picking.outgoing`、`stock.picking.internal`、`account.move`、`product.product`、`project.task`、`stock.quant`。
- 三个 picking 资源共享 `stock.picking` 模型，但按 `picking_type_code` 独立计数。
- 每个逻辑资源目标 1,000,000 条，固定种子 20261002。

### 环境

- 使用项目 `./venv` 和 `./odoo.conf`。
- 数据必须位于独立数据库，不能污染共享数据库 `odoo18ce`。
- 目标环境是 8 核、16 GiB、SSD；本次实际规格记录在结果中。

假设不成立时，整体只能判定为有条件通过或不通过，不能宣称 NFR-001 通过。

## 5. 范围

### In Scope

- 隔离数据库中的 10 个逻辑资源。
- 固定种子、百万级 ORM 数据写入和计数。
- 精确、前缀、包含匹配。
- 20 并发搜索、P50/P95/P99、错误率。
- 深度 2 关联读取。
- 真实用户 `with_user()` 权限读取。
- 热缓存重复测量、可记录的冷缓存替代/限制说明。

### Out of Scope

- 修改 `odoo/` 或官方 addons。
- Elasticsearch、OpenSearch、LLM、向量检索。
- 直接数据库读写、裸 SQL、SQL Plan、`sudo()`。
- 生产模块实现。
- 将小规模或模拟数据作为 NFR-001 通过证据。

## 6. 方法

### 测试数据

使用 `data/generate.py`，固定种子 20261002，以 ORM 分块写入。每个逻辑资源使用 `TV01-` 标记，重复执行复用已存在记录。销售、采购、发票、出库和任务记录建立最小有效业务字段；picking 按入库、出库、内部三类分配。

### 测试场景

1. 资源和字段能力预检。
2. 每个逻辑资源精确、前缀、包含查询。
3. 20 并发跨资源查询。
4. 深度 2 `res.partner -> sale.order -> partner` 关系查询。
5. 普通用户与受限用户对同一查询的对照。
6. 首轮热身后重复执行热缓存测量。

### 指标

- 数据行数和资源覆盖率；
- P50/P95/P99、最大值；
- 首次返回（`search(limit=50)`）耗时；
- 完整返回（`search(limit=False)`）耗时；
- 错误数和错误率；
- 权限过滤前后耗时差；
- 数据写入耗时；
- CPU、内存和磁盘可用空间快照。

### 执行步骤

1. 使用 Odoo CLI 在隔离数据库安装所需官方模块。
2. 通过 Odoo shell 执行 `data/generate.py`。
3. 通过 Odoo shell 执行 `scripts/run.py`。
4. 将 JSON、CSV、日志和环境快照写入 `results/` 与 `evidence/`。
5. 根据真实结果生成 `reports/REPORT.md`。

## 7. 通过标准

| 子问题 | 通过 | 不通过/未验证 |
|---|---|---|
| 单模型精确/前缀/包含 | 目标资源均有百万级真实 ORM 数据，P95 <= 2 秒 | 数据不足、模型缺失、P95 超标或索引证据缺失 |
| 20 并发 | P95 首次 <= 2 秒，完整 <= 5 秒，错误率 <= 1% | 任一指标超标或数据规模不足 |
| 深度 2 关系 | 真实关系查询有可复现 P95/P99 且满足 NFR | 路径不可用或缺少真实数据 |
| 权限开销 | 有普通/受限用户可复现对照且无泄露 | 权限异常、泄露或无对照证据 |
| 冷/热缓存 | 两类测量均有证据 | 当前环境无法安全清理缓存时单独标记未验证 |
| 完整覆盖 | 10 个逻辑资源各 1,000,000 条 | 任一资源缺失或不足 |

整体判定：

- **通过**：所有子问题通过并满足 NFR-001。
- **有条件通过**：核心 ORM 路径满足，但存在未验证的缓存、索引、权限或环境条件。
- **不通过**：明确超出 NFR 或出现泄露/错误率超标。

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 11,000,000 条业务记录超过磁盘或时间预算 | 先记录容量和写入进度；不足时停止并报告阻塞，不在共享库降级冒充 |
| 业务模型约束导致批量创建失败 | 保留已完成批次，记录模型错误和最小有效字段 |
| 隔离库初始化失败 | 报告环境阻塞，不写共享数据库 |
| 冷缓存清理需要直接数据库操作 | 不执行清缓存；标记冷缓存子问题未验证 |
| ORM 并发资源泄露 | 每个线程使用独立 cursor，异常显式记录 |

## 9. 产出物

- `PLAN.md`
- `README.md`
- `data/generate.py`
- `scripts/run.py`
- `results/*.json`
- `evidence/*.log`
- `reports/REPORT.md`

## 10. 参考

- `docs/requirement/SRS_global_search.md`：NFR-001、CFG-011、FR-L1、FR-L2、BR-012
- `docs/verification/SPIKE_global_search_report.md`：GS-01
- `mymodules/wd_spike_global_search/spike_01_multi_model_search/reports/REPORT.md`
- `odoo.conf`

## 11. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-02 | 创建 TV-01 验证计划 |
| v0.2 | 2026-10-02 | 经用户授权将实际基线降为每逻辑资源 100,000 条；完成 ORM 数据和性能测量 |
