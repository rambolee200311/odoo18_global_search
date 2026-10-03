# Global Search Technical Verification 汇总报告

## 1. 摘要

### 1.1 整体结论

TV-01 至 TV-06 均已执行。当前没有任何 TV 可以被标记为“无条件完全通过”，但所有已执行范围均产生了可复现技术事实：

- TV-01、TV-02：100,000 条/资源规模下性能和索引策略满足目标，但百万级、冷缓存或完整权限对照未完成；
- TV-03：业务记录新鲜度满足初始 5 秒目标，配置发布/停用未验证；
- TV-04：复杂权限 fixture 无泄露，失败关闭通过，但真实 Global Search 服务尚未接入；
- TV-05：Preview 已实现并完成 Chromium 浏览器验证，但使用了用户授权的共享库 smoke 测试，Firefox/Safari 和运行时权限变化未验证；
- TV-06：ORM reference harness 的十项语义检查全部通过，但最终 Search Service 和真实 UI 错误展示未验证。

整体结论：**技术路线有条件可行，进入 TDD/服务实现阶段；不得将当前结果宣称为生产 Global Search 已全面验收。**

### 1.2 对 SRS V1.4 的影响

- NFR-001：在 100,000 条/资源规模满足本次测量阈值，但百万级仍需补测；
- NFR-002：业务记录提交后的 ORM 新鲜度满足 5 秒初始目标，配置发布/停用仍未验证；
- FR-PM-004、FR-PM-008、BR-012：复杂权限路径获得通过证据，需把 fixture 转为服务回归测试；
- FR-SW-004、FR-SW-007、CON-009：Preview 获得首轮浏览器证据，仍需隔离库、多浏览器和运行时权限回归；
- BR-009.1、BR-009.2、BR-010、FR-ER-003：语义 reference harness 全部通过，需接入真实 Search Service；
- CFG-011：应按查询类型选择索引，不应配置单一通用索引；
- AC-045、CON-010 以及配置发布相关要求仍不能关闭。

### 1.3 V1 范围决定

**不调整 SRS V1.4 业务范围。**

但必须把以下内容作为 V1 实现前置条件或验收门槛：

1. Search Service 的条件、时间和部分失败协议；
2. 配置模型、版本发布和缓存失效机制；
3. 权限边界和失败关闭；
4. Preview 的浏览器回归；
5. 百万级性能补测或明确 NFR-001 的最终容量边界。

## 2. TV 结果汇总表

| ID | 名称 | 结论 | 关键数据 | SRS 影响 |
|---|---|---|---|---|
| TV-01 | NFR-001 完整性能基线 | 有条件通过 | 10 个逻辑资源、100,000 条/资源；20 并发首次结果 P95 30.968 ms，完整结果 P95 159.302 ms，错误率 0% | NFR-001 百万级未验证；FR-L1/FR-L2 获得 100k 证据 |
| TV-02 | 索引策略对照 | 有条件通过 | B-tree Exact P95 0.033 ms；pattern_ops Prefix P95 0.036 ms；GIN Contains P95 9.226 ms；GiST Contains P95 8.805 ms | CFG-011 应按查询类型选索引；冷缓存/百万级未验证 |
| TV-03 | NFR-002 数据新鲜度 | 有条件通过 | 创建/更新/删除 P95 0.661/1.045/0.604 ms；20 并发错误率 0%，P95 239.615 ms | AC-044 业务记录部分通过；AC-045/CON-010 未验证 |
| TV-04 | 复杂权限场景 | 有条件通过 | `no_leakage=true`、`failure_closed=true`；覆盖 10 类复杂权限场景 | FR-PM-004、FR-PM-008、BR-012 获得证据；需固化规则合并约束 |
| TV-05 | Preview 浏览器验证 | 有条件通过 | 三模型 Form View 126/1305/700；375px 窄屏通过；控制台错误 0 | FR-SW-004、FR-SW-007、CON-009 首轮通过；隔离库/多浏览器/权限变化未验证 |
| TV-06 | 多值条件、时间语义、部分失败 | 有条件通过 | 10/10 semantic checks=true；三时区、两语言、部分失败/超时/配置错误均有结果 | BR-009.1/2、BR-010、FR-ER-003 harness 通过；服务层未验证 |

## 3. 每个 TV 的结论

### 3.1 TV-01 NFR-001 完整性能基线

**核心结论：有条件通过。**

实际使用 10 个逻辑资源，每个 100,000 条记录，共 1,000,000 条逻辑记录。20 并发：

- 首次结果 P95：30.968 ms；
- 完整结果 P95：159.302 ms；
- 首次结果错误率：0%；
- 完整结果错误率：0%；
- 深度 2 Relation Path P95：0.205 ms。

限制：用户授权后从 1,000,000 条/资源降为 100,000 条/资源；冷缓存、Record Rule 额外开销、SQL Plan 未验证。因此 NFR-001 不能关闭，只能作为 100k 基线。

SRS 影响：FR-L1、FR-L2 获得基础性能证据；NFR-001 和 CFG-011 仍需容量与索引补测。

### 3.2 TV-02 索引策略对照

**核心结论：有条件通过。**

推荐：

- Exact Identifier：B-tree；
- Prefix：`text_pattern_ops`；
- Selective Contains：GIN `gin_trgm_ops`；
- GiST `gist_trgm_ops`：可用但不作为默认策略。

关键数据：

- B-tree Exact P95：0.033 ms；
- pattern_ops Prefix P95：0.036 ms；
- GIN Contains P95：9.226 ms；
- GiST Contains P95：8.805 ms；
- GIN 大小：3.30 MiB；
- GiST 大小：11.14 MiB。

限制：测试规模为 100,000 条，冷缓存未验证。高选择率包含查询合理回退 Seq Scan。

SRS 影响：CFG-011 应定义按匹配类型选择索引；不引入外部搜索引擎。

### 3.3 TV-03 NFR-002 数据新鲜度

**核心结论：业务记录新鲜度有条件通过；配置新鲜度未验证。**

业务记录结果：

- 创建 P95：0.661 ms；
- 更新 P95：1.045 ms；
- 删除 P95：0.604 ms；
- 批量创建/更新/删除：0.487/0.582/1.025 ms；
- 20 并发错误率：0%，P95：239.615 ms。

更新后旧值不可见，删除后记录不可见。配置发布和停用没有可调用的配置模型/API，因此 AC-045、CON-010 未验证。

### 3.4 TV-04 复杂权限场景

**核心结论：有条件通过。**

覆盖共享记录、空公司、多公司用户、Portal 用户、字段值规则、时间规则、深度 2 Relation Path、关联记录部分无权、字段权限组合和运行时权限变化。最终：

- 无泄露：`true`；
- 失败关闭：`true`；
- 未授权关联计数：0；
- 无权限字段 `credit_limit`：不参与搜索。

重要发现：同一用户组中的多个 Group Rule 不能假设自动 AND；最终将依赖的硬边界合并为全局测试规则后通过。

### 3.5 TV-05 Preview 浏览器验证

**核心结论：有条件通过。**

用户授权后使用隔离的授权测试用户在 `odoo18ce` 完成 Chromium smoke 验证。Preview 通过 `/wd_global_search` 加载：

- `res.partner` Form View 126；
- `sale.order` Form View 1305；
- `stock.picking` Form View 700。

已验证只读展示、无写操作入口、记录切换、375px 单栏布局、Ctrl+S 拦截和控制台无错误。限制：

- 本次使用共享库，不是隔离库正式验收；
- Firefox/Safari 未执行；
- 记录打开后权限变化未执行。

### 3.6 TV-06 多值条件、时间语义、部分失败

**核心结论：reference harness 有条件通过。**

十项语义检查全部为 `true`：

- 同维度 OR；
- 日期 `[start,end)`；
- UTC/上海/洛杉矶时区；
- `en_US` 周日、`zh_CN` 周一；
- 跨午夜；
- 部分成功；
- 部分失败计数；
- 错误提示；
- 超时保留已完成结果；
- 配置错误失败关闭。

限制：最终 Search Service 尚未实现，真实 HTTP/UI 错误提示和计数未验证。

## 4. 对 SRS V1.4 的影响

### 4.1 已获得验证证据

| 需求 | 当前结论 |
|---|---|
| FR-L1、FR-L2 | 100k ORM 性能路径通过 |
| FR-PM-004、FR-PM-008、BR-012 | 复杂权限 fixture 通过 |
| FR-SW-004、FR-SW-007、CON-009 | 首轮 Chromium Preview 通过，有条件 |
| BR-009.1 | 周起始日按语言计算通过 |
| BR-009.2 | 时区和跨日计算通过 |
| BR-010 | 同维度 OR 通过 |
| FR-ER-003 | 部分成功/超时/配置错误协议通过 harness |
| AC-044 | 业务记录 ORM 新鲜度满足 5 秒初始目标 |

### 4.2 需要技术方案调整

| 需求 | 调整 |
|---|---|
| NFR-001、CFG-011 | 按 Exact/Prefix/Contains 选择 B-tree、pattern_ops、GIN；补测百万级和冷缓存 |
| NFR-002 | 增加配置版本、发布状态和多 worker 缓存失效机制 |
| FR-PM-004、FR-PM-008、BR-012 | 每个 Resource/Relation Path 使用当前用户；硬安全边界避免依赖 Group Rule OR/AND 假设 |
| FR-SW-007、CON-009 | Preview 容器默认只读，写操作、按钮、Chatter、附件、活动统一阻断 |
| FR-ER-003 | 结果聚合器返回状态、成功结果、失败模型、计数和显式错误码 |

### 4.3 仍需验证或修改

- NFR-001 百万级/冷缓存/Record Rule 性能；
- NFR-002 配置发布和停用；
- Preview 隔离数据库、多浏览器、运行时权限变化；
- Search Service 对 TV-06 语义和错误协议的真实接入；
- UI 对部分失败、超时和配置错误提示的验收。

## 5. 对技术方案的影响

### 5.1 索引策略

生产默认策略：

1. Identifier Exact 使用 B-tree；
2. Prefix 使用 `text_pattern_ops`；
3. Selective Contains 使用 GIN `gin_trgm_ops`；
4. GiST 仅在明确需要其特性且索引空间可接受时使用；
5. 高选择率查询允许 PostgreSQL 选择 Seq Scan。

不引入 Elasticsearch、OpenSearch、LLM 或向量检索。

### 5.2 数据模型

需要补充：

- Business Resource 的字段用途和 Business Date 配置；
- 配置版本、发布状态、生效时间；
- Technical Model 优先级唯一性校验；
- 部分失败模型的错误状态和可展示信息；
- Result Identity 去重键。

关联 SRS：CFG-001、CFG-011、NFR-002、BR-003、BR-011、BR-013、FR-ER-003。

### 5.3 权限边界

- 所有资源和关系跳转必须在当前用户上下文执行；
- 不使用 `sudo()` 绕过权限；
- 无权限字段必须从搜索字段集合排除；
- 权限异常失败关闭；
- 同一硬安全边界的公司、字段和时间条件不能依赖不明确的 Group Rule 组合。

关联 SRS：FR-PM-001~FR-PM-008、BR-012、CON-008、CON-011。

### 5.4 Preview 容器

- 真实 Form View 通过 ORM `get_view`/`read` 加载；
- 容器只读，不提供编辑、保存、删除和业务按钮；
- Chatter、附件和活动操作不暴露；
- 删除或权限变化进入统一安全状态；
- 桌面使用结果/Preview 分栏，窄屏降级为单栏；
- 必须补充 Firefox/Safari 和隔离库回归。

关联 SRS：FR-SW-004、FR-SW-007、CON-009。

## 6. 未解决的问题

1. 真实 Global Search Search Service 尚未完成；
2. NFR-001 百万级每资源、冷缓存、真实 Record Rule 额外开销未完成；
3. NFR-002 配置发布/停用和多 worker 即时生效未完成；
4. TV-05 Firefox/Safari、隔离库和运行时权限变化未完成；
5. TV-06 语义 harness 尚未接入真实服务和浏览器 UI；
6. 部分失败、超时和配置错误的最终 UX 文案尚未定稿；
7. 生产数据模型和配置版本机制尚未实现；
8. TV-04 发现的 Group Rule 组合风险需要配置生成器回归测试。

## 7. 下一步建议

| 优先级 | 建议 | 对应需求 |
|---|---|---|
| P0 | 进入 TDD，先定义 Search Service 的 Effective Conditions、错误协议、Result Identity 和权限边界 | BR-007、BR-010、BR-011、BR-012、BR-013、FR-ER-003 |
| P0 | 实现配置模型、版本发布和缓存失效机制 | CFG-001、NFR-002、AC-045、CON-010 |
| P0 | 将 TV-04 fixture 转为自动化权限回归测试 | FR-PM-001~FR-PM-008、CON-008、CON-011 |
| P0 | 将 TV-06 harness 规则接入真实 Search Service，并补充 UI 错误提示测试 | BR-009.1、BR-009.2、BR-010、FR-ER-003 |
| P1 | 在隔离性能环境完成百万级和冷缓存 TV-01/TV-02 补测 | NFR-001、CFG-011 |
| P1 | 在隔离数据库重跑 TV-05，并增加 Firefox/Safari 和权限变化 | FR-SW-004、FR-SW-007、CON-009 |
| P1 | 按推荐策略实现并验证索引迁移/回滚 | CFG-011、NFR-001 |
| P2 | 明确部分失败、超时和配置错误的产品文案与可观测性字段 | FR-ER-003、FR-ER-002 |
| P2 | 暂不调整 V1 业务范围，不引入外部搜索引擎 | SRS V1.4、NFR-001 |

## 8. 附录：报告、原始结果、证据和复现

### TV-01

- 报告：[TV-01 REPORT](../../mymodules/wd_tv_global_search/tv_01_nfr_001_performance/reports/REPORT.md)
- 原始结果：[generation_result.json](../../mymodules/wd_tv_global_search/tv_01_nfr_001_performance/results/generation_result.json)、[performance_result.json](../../mymodules/wd_tv_global_search/tv_01_nfr_001_performance/results/performance_result.json)
- 证据：原始结果 JSON 中的测量字段
- 复现脚本：[generate.py](../../mymodules/wd_tv_global_search/tv_01_nfr_001_performance/data/generate.py)、[run.py](../../mymodules/wd_tv_global_search/tv_01_nfr_001_performance/scripts/run.py)

### TV-02

- 报告：[TV-02 REPORT](../../mymodules/wd_tv_global_search/tv_02_index_strategy/reports/REPORT.md)
- 原始结果：[index_strategy_result.json](../../mymodules/wd_tv_global_search/tv_02_index_strategy/results/index_strategy_result.json)
- 证据：[evidence/](../../mymodules/wd_tv_global_search/tv_02_index_strategy/evidence/)
- 复现脚本：[run.py](../../mymodules/wd_tv_global_search/tv_02_index_strategy/scripts/run.py)、[orm_write_benchmark.py](../../mymodules/wd_tv_global_search/tv_02_index_strategy/scripts/orm_write_benchmark.py)

### TV-03

- 报告：[TV-03 REPORT](../../mymodules/wd_tv_global_search/tv_03_freshness/reports/REPORT.md)
- 原始结果：[freshness_result.json](../../mymodules/wd_tv_global_search/tv_03_freshness/results/freshness_result.json)
- 证据：原始结果中的时间戳和 P50/P95/P99 字段
- 复现脚本：[run.py](../../mymodules/wd_tv_global_search/tv_03_freshness/scripts/run.py)

### TV-04

- 报告：[TV-04 REPORT](../../mymodules/wd_tv_global_search/tv_04_complex_permissions/reports/REPORT.md)
- 原始结果：[permission_result.json](../../mymodules/wd_tv_global_search/tv_04_complex_permissions/results/permission_result.json)
- 证据：原始结果中的可见性、计数、失败关闭和权限切换字段
- 复现脚本：[run.py](../../mymodules/wd_tv_global_search/tv_04_complex_permissions/scripts/run.py)

### TV-05

- 报告：[TV-05 REPORT](../../mymodules/wd_tv_global_search/tv_05_preview_browser/reports/REPORT.md)
- 原始结果：[browser_result.json](../../mymodules/wd_tv_global_search/tv_05_preview_browser/results/browser_result.json)
- 证据：[evidence/](../../mymodules/wd_tv_global_search/tv_05_preview_browser/evidence/)
- 复现说明：[README.md](../../mymodules/wd_tv_global_search/tv_05_preview_browser/README.md)
- 实现入口：[main.py](../../mymodules/wd_global_search/controllers/main.py)

### TV-06

- 报告：[TV-06 REPORT](../../mymodules/wd_tv_global_search/tv_06_multi_value_time_failure/reports/REPORT.md)
- 原始结果：[tv06_result.json](../../mymodules/wd_tv_global_search/tv_06_multi_value_time_failure/results/tv06_result.json)
- 证据：原始结果中的十项 checks、时区、语言、错误协议字段
- 复现脚本：[run.py](../../mymodules/wd_tv_global_search/tv_06_multi_value_time_failure/scripts/run.py)
- 数据脚本：[generate.py](../../mymodules/wd_tv_global_search/tv_06_multi_value_time_failure/data/generate.py)

## 9. 报告变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 汇总 TV-01 至 TV-06 技术验证结果 |
