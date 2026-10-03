# Global Search Spike 汇总报告

## 1. 报告信息

| 项 | 值 |
|---|---|
| 报告 | Global Search Spike 汇总报告 |
| 需求基线 | SRS V1.4 FROZEN |
| 覆盖范围 | SPIKE-GS-01 ~ SPIKE-GS-08 |
| 执行日期 | 2026-10-01 ~ 2026-10-02 |
| 平台 | Odoo 18.0 |
| 数据库 | `odoo18ce` |
| Python | 项目 `./venv` |
| 配置 | `./odoo.conf` |

## 2. 摘要

### 2.1 整体结论

8 个 Spike 均已执行，整体判定为：

> **技术路线有条件可行；SRS V1.4 的业务范围不需要扩大或缩减；NFR-001 尚未被完整验证。**

已获得证据的能力包括：

- Odoo ORM 跨模型查询和并发读取；
- Entity Resolution 评分、阈值和候选截断；
- 跨资源 Business Date 独立过滤与合并；
- Parsed Conditions 与 Refinement Conditions 合并；
- 公司 Record Rule、字段权限和失败关闭；
- 真实 Odoo Form View 只读加载；
- 中文有限语法词法切分；
- 复合资源字段映射、排序、优先级和计数；
- PostgreSQL `pg_trgm` 1.6 与 GIN `gin_trgm_ops` 索引路径。

### 2.2 对 SRS V1.4 的整体影响

| 事项 | 结论 |
|---|---|
| FR-L1 / FR-L2 | 有条件可行；GS-01 提供局部 ORM 证据，完整资源覆盖仍不足 |
| FR-L3 | 有条件可行；GS-07 在 100 条语料上达到 100% |
| FR-RF | 有条件可行；GS-03/GS-04 验证日期和条件合并语义 |
| FR-PM | 有条件可行；GS-05 未发现测试路径泄露 |
| FR-SW | 有条件可行；GS-06 验证真实 Form View 只读加载链路 |
| BR-003 / BR-003.1 | 有条件可行；GS-08 验证复合资源规则 |
| BR-013 | 已获得去重计数证据 |
| NFR-001 | **未验证**；缺少 10 个资源、每资源 100 万条的完整隔离性能基线 |
| NFR-002 | 未在本组 Spike 中完成新鲜度上限测量 |

### 2.3 是否调整 V1 范围

**不调整 V1 范围。**

Spike 没有证明必须引入外部搜索引擎、LLM、向量检索或 L4 Business Answer，也没有发现必须从 V1 删除 L1/L2/L3、Result Refinement 或 Search Workspace 的证据。SRS V1.4 继续作为需求基线；性能和权限限制转入 TDD/Technical Verification。

## 3. Spike 结果汇总

| ID | 名称 | 结论 | 关键数据 | SRS 影响 |
|---|---|---|---|---|
| GS-01 | 多模型搜索性能 | 有条件可行 / NFR 未验证 | 7/8 目标模型可用；客户、销售、采购各 5,000 条；20 并发 P95 6.300 ms；`pg_trgm` GIN 路径可运行 | FR-L1/L2、BR-012 有局部证据；NFR-001 仍未验证 |
| GS-02 | Entity Resolution 评分 | 有条件可行 | 1,000 条相似实体；识别评分 60/90/95/100/110；阈值 30/29 边界通过；候选 20→10；稳定性通过 | FR-L2-002/003、CFG-010 可进入 TDD；评分公式仍需配置化 |
| GS-03 | 跨资源 Business Date 合并 | 有条件可行 | 5 个资源；每资源日期分布；6 月合并 5 条；空日期排除；稳定重复 | FR-RF-003/004、BR-009.3/4/6 已有技术证据 |
| GS-04 | Query 与 Refinement 条件合并 | 有条件可行 | 17 条五资源记录；路径 A/B 等价；冲突 Refinement 优先；2 个重复命中去重为 1 | BR-007/008/010/011/013 可进入 TDD |
| GS-05 | 权限过滤完整性 | 有条件可行 | 2 公司、2 用户；外部结果/计数/Preview/理解均不可见；字段权限排除；关联外部计数 0；失败关闭 | FR-PM-001~008、CON-008/011 需在运行时设计中强制 |
| GS-06 | Form Preview 只读嵌入 | 有条件可行 | 3 个真实 Form View 加载；0 次 ORM 写入；只读策略通过；权限/删除安全状态；窄屏单栏降级 | FR-SW-004/007、CON-009 需前端动作层强制 |
| GS-07 | 中文连续文本词法切分 | 有条件可行 | 100/100 正确；识别率 100%；Free Text 安全降级 100%；重复稳定 | FR-L3-001、AC-008 获得有限语法证据；不扩展为完整 NLP |
| GS-08 | 复合资源合并与排序 | 有条件可行 | sale/purchase 各 100,000 条内存数据；映射完整；优先级冲突拒绝；空日期 20 条置后；计数 200,000 | BR-003/003.1、BR-013、CFG-001 获得规则证据；真实 ORM 性能仍需验证 |

## 4. 各 Spike 结论

### 4.1 SPIKE-GS-01 多模型搜索性能

**核心结论：** ORM 查询和 20 并发读路径可运行，但不能证明 NFR-001。

**关键数据：**

- `res.partner`、`sale.order`、`purchase.order` 均有 GS01 模拟数据各 5,000 条；
- 目标模型 8 个中 7 个可用，`project.task` 缺失；
- 20 并发 P50/P95/P99：2.464 / 6.300 / 6.618 ms；
- `pg_trgm` 1.6 已安装；
- 三个 GIN `gin_trgm_ops` 路径在强制索引计划中均出现 Bitmap Index Scan；
- 当前小数据自然计划仍选择 Seq Scan。

**SRS 影响：**

- FR-L1-001~003、FR-L2-001~004、BR-012：局部技术可行；
- NFR-001：仍为未验证，不得标记 VERIFIED；
- CFG-011：保留，默认值需在隔离性能环境确认；
- CON-003：未发现外部搜索引擎必要性。

### 4.2 SPIKE-GS-02 Entity Resolution 评分

**核心结论：** 评分、阈值、候选截断和稳定排序可实现。

**关键数据：**

- 1,000 条 `res.partner` 测试数据；
- 精确、大小写、简称/别名多字段、拼音近似分别产生可解释分值；
- 分差 30 判定唯一命中，分差 29 展示候选；
- 20 个候选返回 10 个并设置 `has_more=true`；
- 重复执行稳定。

**SRS 影响：**

- FR-L2-002/003、CFG-010、AC-005/006 可进入 TDD；
- 具体评分公式、字段权重、拼音算法不应写回 SRS 业务语义；
- 多公司简称隔离仍需权限 Spike 补充。

### 4.3 SPIKE-GS-03 跨资源 Business Date 合并

**核心结论：** 各资源可按独立 Business Date 过滤，再按统一日期范围合并。

**关键数据：**

- 5 个资源；
- `2026-06-01 <= Business Date < 2026-07-01`；
- 每资源命中 1 条 2026-06-30，共 5 条；
- 结果均包含 Business Date 和字段标注；
- 可为空的发票、出库单空日期均被排除；
- 销售/采购 `date_order` 的数据库非空约束已记录。

**SRS 影响：**

- FR-RF-003/004、BR-009.3/4/6、AC-023/028 获得证据；
- 动态日期、时区、多公司仍需继续验证。

### 4.4 SPIKE-GS-04 Query 与 Refinement 条件合并

**核心结论：** 两条路径可以归一到同一个 Effective Conditions 模型。

**关键数据：**

- 路径 A/B Effective Conditions 完全相同；
- Filtered Result Set 均为同一 `stock.picking` Identity；
- 冲突时 Refinement 覆盖 Parsed；
- 无效条件不进入 Effective Conditions；
- 删除条件不修改 Raw Query；
- 重复命中 2 条按 Result Identity 计为 1 条。

**SRS 影响：**

- BR-007、BR-008、BR-010、BR-011、BR-013 可作为 TDD 合并器和计数器约束；
- Query Understanding 必须展示冲突消解；
- 权限过滤需在合并前后均执行。

### 4.5 SPIKE-GS-05 权限过滤完整性

**核心结论：** 测试路径未发现跨公司结果、计数、Preview 或 Query Understanding 泄露。

**关键数据：**

- 两家公司、两个受限用户；
- 每个用户只看到本公司 1 个客户和 1 个订单；
- 外部结果和计数均为 0；
- 外部 Preview 和 Query Understanding 均不可见；
- `credit_limit` 对用户不可读并排除出 Searchable Field；
- 外部关联订单计数为 0；
- 权限异常返回 `PERMISSION_DENIED`、空结果、0 计数。

**SRS 影响：**

- FR-PM-001~008、FR-ER-003、CON-008、CON-011 必须作为运行时安全边界；
- 配置管理员字段权限不得替代最终用户运行时权限；
- 复杂 Record Rule、门户用户和多跳关联仍需继续验证。

### 4.6 SPIKE-GS-06 Form Preview 只读嵌入

**核心结论：** 真实 Form View 可加载；只读策略必须在客户端和动作层强制。

**关键数据：**

- `res.partner`、`sale.order`、`stock.picking` 三个真实 Form View 均加载；
- 0 次 ORM 写入；
- 未调用 onchange、保存、按钮、Chatter、附件和活动操作；
- 删除/权限变化统一显示 `PERMISSION_OR_DELETED`；
- 切换记录保留 Query/Refinement；
- 窄屏降级为单栏 Preview。

**SRS 影响：**

- FR-SW-004、FR-SW-007、CON-009 获得读取链路证据；
- 原始 View 仍包含按钮节点，TDD 必须定义隐藏和 RPC 动作拦截；
- 需浏览器 Human Review 验证真实 UI 行为。

### 4.7 SPIKE-GS-07 中文连续文本词法切分

**核心结论：** 有限词典和确定性规则达到识别目标，不代表完整中文 NLP。

**关键数据：**

- 100 条测试语料；
- 正确识别 100/100，识别率 100%；
- 核心连续文本正确识别 Entity + Time + State + Resource；
- Identifier + Location、Time + Resource、Entity + Time 均通过；
- Free Text 安全降级 100%；
- 同输入重复解析稳定。

**SRS 影响：**

- FR-L3-001、FR-L3-002、AC-008 获得有限语法证据；
- 不扩大 SRS 到否定词、布尔表达式、同义词推断或完整自然语言解析；
- 词典应配置化。

### 4.8 SPIKE-GS-08 复合资源合并与排序

**核心结论：** 复合资源映射、排序、优先级和计数规则可实现。

**关键数据：**

- `sale.order` 和 `purchase.order` 各 100,000 条固定种子内存数据；
- 总记录 200,000；
- 标题、日期、状态、Snapshot 映射完整；
- 重复优先级被拒绝；
- 199,980 条非空日期在 20 条空日期之前；
- 两次排序结果一致；
- 分类计数 100,000 + 100,000 = 全部 200,000；
- 200 个重复路径命中去重为 100 个 Identity。

**SRS 影响：**

- BR-003、BR-003.1、BR-013、CFG-001、AC-025/042/043 获得规则证据；
- 真实 20 万条 ORM 持久化数据的性能仍未验证；
- Snapshot 必须继续应用 FR-PM 权限过滤。

## 5. 对 SRS V1.4 的影响

### 5.1 已验证或获得局部证据

| SRS 区域 | 证据 | 处理 |
|---|---|---|
| L2 Entity Resolution | GS-02 | 进入 TDD，公式和权重技术化 |
| L3 有限语法 | GS-07 | 保持有限语法，不扩展自然语言承诺 |
| 日期语义 | GS-03 | 按 Business Resource 配置字段 |
| Query/Refinement | GS-04 | 归一化、冲突消解和 Identity 计数进入 TDD |
| 权限 | GS-05 | 运行时权限检查必须失败关闭 |
| Preview | GS-06 | 只读动作边界进入 TDD/前端验证 |
| 复合资源 | GS-08 | 字段映射、排序和计数进入配置模型 |

### 5.2 需要技术方案调整

1. **评分配置：** CFG-010 需要支持权重、阈值 30、候选上限 10 和稳定 tie-breaker。
2. **条件合并器：** BR-007/008/010 需要单一 Effective Conditions 模型。
3. **权限边界：** FR-PM-001~008、CON-008/011 必须在每个搜索、计数、Preview 和关联路径执行。
4. **复合资源配置：** CFG-001 需要保存模型字段映射、状态映射和唯一优先级。
5. **Preview：** FR-SW-007/CON-009 需要客户端 readonly、动作拦截和权限变化安全状态。
6. **索引策略：** `pg_trgm` 可作为技术候选，但不能仅凭当前 5 千级数据决定生产索引。

### 5.3 是否修改需求或范围

- SRS V1.4：**不修改业务需求基线**；
- V1 范围：**不调整**；
- NFR-001：**不标记 VERIFIED，也暂不修改目标值**；
- NFR-002：仍需单独的新鲜度 Technical Verification；
- 外部搜索引擎/LLM/向量检索：仍不引入。

## 6. 对技术方案的影响

| 技术事项 | 结论 | 对应需求 |
|---|---|---|
| Elasticsearch/OpenSearch | 不引入；当前没有必要性证据 | CON-003 |
| LLM/向量检索 | 不引入；L3 仍为有限语法 | FR-L3-001、CON-003 |
| PostgreSQL ORM 查询 | 保留为 V1 基础路径，但需隔离性能验证 | FR-L1、NFR-001 |
| `pg_trgm` | 1.6 已安装；GIN 路径已验证可运行；百万级效果未验证 | NFR-001、CFG-011 |
| 数据模型 | 不修改官方业务模型；配置模型需支持复合资源和映射 | CON-007、CFG-001 |
| 索引策略 | TDD/TV 定义；候选包括 B-tree、`pattern_ops`、GIN/GiST trigram | NFR-001 |
| 权限 | 全部结果和元数据路径使用当前用户上下文 | FR-PM-001~008、CON-008/011 |
| Preview | 使用真实 Form View，但强制只读动作边界 | FR-SW-004/007、CON-009 |

## 7. 未解决的问题

### 7.1 后续技术验证

1. **NFR-001 完整基线：** 10 个 Business Resource、每资源 1,000,000 条、20 并发、P95/P99；对应 NFR-001。
2. **索引规模对照：** 在隔离数据库比较无索引、B-tree、`pattern_ops`、GIN/GiST `pg_trgm`；对应 NFR-001、CFG-011。
3. **数据新鲜度：** 创建业务记录到搜索可见的最终上限；对应 NFR-002、AC-044。
4. **完整模型覆盖：** 补齐 `project.task` 等目标资源；对应 FR-L2-004、BR-012。
5. **权限扩展：** 深度 2 Relation Path、门户用户、共享记录、复杂 Record Rule；对应 FR-PM-004、FR-PM-008、BR-012。
6. **Preview 浏览器验证：** 验证按钮、键盘、RPC、Chatter 和附件动作不可用；对应 FR-SW-007、CON-009。
7. **多值条件：** 同维度 OR、多状态和部分失败模型；对应 BR-010、FR-ER-003。
8. **时间语义：** 用户时区、周起始日、动态“今天/本周/本月”；对应 BR-009.1、BR-009.2、FR-RF-003。

### 7.2 业务或产品确认

1. Entity Resolution 的最终权重和拼音策略；对应 CFG-010、FR-L2-002。
2. 空 Business Date 是否提供显式包含开关；对应 BR-009.4。
3. 复合资源状态和 Snapshot 的最终业务词汇；对应 BR-003、CFG-001。
4. Preview 权限变化时的最终用户提示文案；对应 FR-SW-007。
5. 20 并发和百万级资源是否为生产验收环境的固定基线；对应 NFR-001。

## 8. 下一步建议

### 推荐顺序

1. **进入 DDD：** 固化 Business Resource、复合资源、Effective Conditions、Result Identity 和权限边界；对应 BR-003、BR-007、BR-008、BR-011、BR-012。
2. **进入 TDD：** 定义配置模型、评分引擎、条件合并器、权限过滤器、Preview 只读容器和索引候选；对应 CFG-001、CFG-010、FR-PM-005、CON-009。
3. **先完成 Technical Verification：** 在隔离数据库执行 NFR-001/NFR-002，不以当前小规模 Spike 替代正式性能证明。
4. **建立 TDD 测试矩阵：** 将 GS-02、GS-04、GS-05、GS-06 的成功断言转为自动化测试；对应 FR-L2-003、BR-008、CON-008、CON-009。
5. **Human Review：** 对真实 Web Form Preview、候选列表、“还有更多候选”、Query Understanding 和窄屏降级进行人工验收；对应 FR-SW-004、FR-SW-007、FR-L2-003。
6. **暂不调整 V1 范围：** 只有 NFR-001 隔离验证失败，且确认无法通过 PostgreSQL/ORM/索引满足时，才回到 SRS 评审是否调整 NFR 或 V1 范围；对应 NFR-001、CON-003。

## 9. 附录 A：Spike 报告与原始结果

| Spike | 报告 | 原始结果 | 复现脚本 |
|---|---|---|---|
| GS-01 | [REPORT](../../mymodules/wd_spike_global_search/spike_01_multi_model_search/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_01_multi_model_search/results/spike_result.json)、[pg_trgm_result.json](../../mymodules/wd_spike_global_search/spike_01_multi_model_search/results/pg_trgm_result.json) | [generate.py](../../mymodules/wd_spike_global_search/spike_01_multi_model_search/data/generate.py)、[generate_orm.py](../../mymodules/wd_spike_global_search/spike_01_multi_model_search/data/generate_orm.py)、[run.py](../../mymodules/wd_spike_global_search/spike_01_multi_model_search/scripts/run.py) |
| GS-02 | [REPORT](../../mymodules/wd_spike_global_search/spike_02_entity_resolution/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_02_entity_resolution/results/spike_result.json)、[simulation_result.json](../../mymodules/wd_spike_global_search/spike_02_entity_resolution/results/simulation_result.json) | [generate_orm.py](../../mymodules/wd_spike_global_search/spike_02_entity_resolution/data/generate_orm.py)、[run.py](../../mymodules/wd_spike_global_search/spike_02_entity_resolution/scripts/run.py) |
| GS-03 | [REPORT](../../mymodules/wd_spike_global_search/spike_03_business_date_merge/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_03_business_date_merge/results/spike_result.json)、[simulation_result.json](../../mymodules/wd_spike_global_search/spike_03_business_date_merge/results/simulation_result.json) | [generate_orm.py](../../mymodules/wd_spike_global_search/spike_03_business_date_merge/data/generate_orm.py)、[run.py](../../mymodules/wd_spike_global_search/spike_03_business_date_merge/scripts/run.py) |
| GS-04 | [REPORT](../../mymodules/wd_spike_global_search/spike_04_query_refinement_merge/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_04_query_refinement_merge/results/spike_result.json)、[data_snapshot.json](../../mymodules/wd_spike_global_search/spike_04_query_refinement_merge/results/data_snapshot.json) | [generate_orm.py](../../mymodules/wd_spike_global_search/spike_04_query_refinement_merge/data/generate_orm.py)、[run.py](../../mymodules/wd_spike_global_search/spike_04_query_refinement_merge/scripts/run.py) |
| GS-05 | [REPORT](../../mymodules/wd_spike_global_search/spike_05_permission_integrity/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_05_permission_integrity/results/spike_result.json)、[simulation_result.json](../../mymodules/wd_spike_global_search/spike_05_permission_integrity/results/simulation_result.json) | [generate_orm.py](../../mymodules/wd_spike_global_search/spike_05_permission_integrity/data/generate_orm.py)、[run.py](../../mymodules/wd_spike_global_search/spike_05_permission_integrity/scripts/run.py) |
| GS-06 | [REPORT](../../mymodules/wd_spike_global_search/spike_06_form_preview_readonly/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_06_form_preview_readonly/results/spike_result.json)、[view_snapshot.json](../../mymodules/wd_spike_global_search/spike_06_form_preview_readonly/results/view_snapshot.json) | [generate_orm.py](../../mymodules/wd_spike_global_search/spike_06_form_preview_readonly/data/generate_orm.py)、[run.py](../../mymodules/wd_spike_global_search/spike_06_form_preview_readonly/scripts/run.py) |
| GS-07 | [REPORT](../../mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/results/spike_result.json)、[query_corpus.json](../../mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/results/query_corpus.json) | [generate.py](../../mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/data/generate.py)、[run.py](../../mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/scripts/run.py) |
| GS-08 | [REPORT](../../mymodules/wd_spike_global_search/spike_08_composite_resource_merge/reports/REPORT.md) | [spike_result.json](../../mymodules/wd_spike_global_search/spike_08_composite_resource_merge/results/spike_result.json) | [run.py](../../mymodules/wd_spike_global_search/spike_08_composite_resource_merge/scripts/run.py) |

## 10. 附录 B：统一复现约定

所有 ORM Spike 均使用：

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http < SCRIPT
```

GS-07 先生成语料：

```bash
python3 mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/data/generate.py
```

GS-01 的 `pg_trgm` 对照属于临时授权的数据库验证，结果已经持久化到 `pg_trgm_result.json`；临时索引已清理。该数据库扩展/索引对照不应在共享数据库重复执行，正式性能结论必须迁移到隔离 Technical Verification 环境。

