# Odoo Global Search 软件需求规格说明书（SRS）V1.4

> **文档性质：Software Requirements Specification / 软件需求规格说明书**
> **状态：FROZEN — 需求基线已冻结 — 不授权直接编码**
> **版本：V1.4**
> **适用平台：Odoo 18 Community / Enterprise**
> **上游输入：RAR V0.2（ANALYSIS COMPLETE — FROZEN）**
> **仓库路径：`docs/requirement/RAR_global_search.md`**
> **评审输入：SRS V1.0/V1.1/V1.2/V1.3 评审结论**
> **目的：将 RAR 中已确认的需求边界转化为可验证、可追溯、可冻结的软件需求。**
>
> 本 SRS 不定义技术实现，不构成技术设计文档（TDD），不授权编码。
> PostgreSQL、Elasticsearch/OpenSearch、LLM、全文检索、索引结构、ORM/SQL、前端组件等均不在本阶段作技术选型。
>
> **规范性词汇：** MUST / MUST NOT / SHOULD / SHOULD NOT / MAY
> **需求优先级：** MUST（V1 必须）/ SHOULD（V1 应）/ MAY（V1 可选）/ OUT（V1 明确排除）
> **引用规则：** 本 SRS 内部引用统一使用需求编号（如 BR-007），不使用章节编号。
>
> **需求来源分类：**
> - **RAR**：RAR V0.2 已确认的结论
> - **SRS-DEC**：SRS 阶段的产品决策（RAR 未确认）
> - **SRS-CLAR**：SRS 对 RAR 的澄清
> - **TECH**：技术约束（不属于业务需求）
> - **OPEN**：尚未决定
>
> 每条需求标注来源类型，便于评审者判断哪些是 RAR 确认的、哪些是 SRS 新增的。

---

# 1. 引言

## 1.1 目的

本文档定义 Odoo Global Search 模块（暂定名 `wd_global_search`）的软件需求规格，作为后续技术研究、DDD/TDD 和实现的需求输入。

目标读者：业务方、产品方、技术方、测试方。

## 1.2 范围

Global Search 是配置驱动的统一搜索入口，允许用户通过业务线索（标识符、实体、时间、资源、状态等）跨业务对象发现记录，并通过二次筛选收窄结果集。

**V1 范围（MUST）：** 【来源：SRS-DEC，RAR §24 建议】

- L1 Identifier-based Discovery
- L2 Entity Discovery
- L3 Conditional Discovery（有限语法，见 FR-L3-001）
- Result Refinement
- Search Workspace

**V1 明确排除（OUT）：**

| 排除项 | 说明 | 来源 |
|---|---|---|
| L4 Business Answer | 聚合、余额、状态回答、KPI、分析型问答 | RAR |
| 完整自然语言解析 | 仅支持 FR-L3-001 定义的有限语法 | SRS-DEC |
| Chatter / Attachment 搜索 | 不搜索消息、附件名、附件正文、PDF 内容 | SRS-DEC |
| 外部搜索引擎 | 不引入 Elasticsearch / OpenSearch / 向量检索 | RAR |
| LLM | 不引入大模型 | RAR |
| 跨公司实体合并 | 实体解析按当前用户公司上下文 | SRS-DEC |
| 搜索结果保存/分享 | V2 候选 | RAR |
| 搜索历史 | V2 候选 | RAR |
| Filter 状态 URL 化 | V2 候选 | RAR |
| 个性化推荐 | V2 候选 | RAR |
| 搜索分析 | V2 候选 | RAR |
| 高级搜索语法 | 不支持布尔表达式、排除词、括号分组 | SRS-DEC |

**V1 非目标（明确不做，也不承诺）：**

- 替代业务模块自己的 List/Search View
- 替代 Many2one Record Picker
- 建立跨模型业务关系
- 修改原业务模型数据结构
- 绕过 Odoo 权限体系

## 1.3 术语与缩写

| 术语 | 定义 |
|---|---|
| **Business Resource** | 用户认知中的业务对象（如"出库单"、"客户"）。可为单模型资源、复合资源或关联资源（见 §1.3.1） |
| **单模型资源** | 对应一个 Odoo Technical Model 的 Business Resource |
| **复合资源** | 由多个 Technical Model 组成、对用户呈现为单一业务对象的 Business Resource（如"订单"） |
| **关联资源** | 通过 Relation Path 从其他资源扩展出来的资源 |
| **Business Resource Vocabulary** | 用户语言与系统数据之间的语义对应关系，可配置 |
| **Identifier** | 高区分度的业务标识符（如柜号、单号、提货码） |
| **Entity** | 业务实体（如客户、产品、司机、仓库） |
| **Location** | 业务地点（如港口、仓库地点、城市） |
| **Raw Query** | 用户在搜索框中的原始输入 |
| **Parsed Conditions** | 系统从 Raw Query 解析出的结构化条件 |
| **Refinement Conditions** | 用户在结果页通过 facet 添加的条件 |
| **Effective Conditions** | Parsed Conditions 与 Refinement Conditions 合并、去重、冲突消解后的最终条件 |
| **Result Refinement** | 在搜索结果页对结果进行二次筛选 |
| **Filtered Result Set** | Effective Conditions 作用后的结果集 |
| **Limited Query Input** | V1 支持的有限语法输入（见 FR-L3-001） |
| **Business Date** | 每种 Business Resource 默认用于时间筛选的业务日期字段 |
| **Snapshot** | 搜索结果的业务摘要卡片，用于快速判断 |
| **Search Workspace** | 搜索结果工作区（左侧结果 + 右侧 Preview） |
| **Result Identity** | 搜索结果的唯一标识（见 BR-011） |
| **Relation Path** | Business Resource 之间的关联路径（见 BR-012） |
| **L1/L2/L3/L4** | RAR 定义的能力分层 |

### 1.3.1 Business Resource 类型

| 类型 | 定义 | 示例 |
|---|---|---|
| **单模型资源** | 一个 Business Resource 对应一个 Technical Model | 客户 → `res.partner` |
| **复合资源** | 一个 Business Resource 由多个 Technical Model 组成 | 订单 → `sale.order` + `purchase.order` |
| **关联资源** | 通过 Relation Path 从其他资源扩展出来的资源 | 客户的订单 → 通过 `partner_id` 关联 |

Business Resource 的类型决定了 CFG-001 的配置模型必须支持多模型。

## 1.4 需求来源与追溯

本文档所有需求条目可追溯到 RAR V0.2（仓库路径 `docs/requirement/RAR_global_search.md`）。

- FR-xxx：功能需求
- BR-xxx：业务规则
- CFG-xxx：配置需求
- NFR-xxx：非功能需求
- CON-xxx：约束

**需求来源分类：**

| 来源 | 定义 |
|---|---|
| **RAR** | RAR V0.2 已确认的结论 |
| **SRS-DEC** | SRS 阶段的产品决策（RAR 未确认） |
| **SRS-CLAR** | SRS 对 RAR 的澄清 |
| **TECH** | 技术约束（不属于业务需求） |
| **OPEN** | 尚未决定 |

追溯矩阵见 §11.1，其中包含"来源类型"列。

---

# 2. 总体描述

## 2.1 产品定位

Global Search 是 Odoo 内部的统一搜索入口，让用户通过业务语言和业务线索发现相关业务记录。

**产品是：**

- 跨业务对象的记录发现工具
- 配置驱动的搜索平台
- 支持渐进式收窄的搜索工作区

**产品不是：**

- 业务问答系统（L4）
- 全文搜索引擎
- 跨模型业务关系建立工具
- 权限绕过工具

## 2.2 用户特征

| 用户类型 | 特征 | 主要场景 |
|---|---|---|
| **业务操作员** | 知道业务线索，不知道系统结构 | 查柜号、查客户、查单号 |
| **业务管理员** | 需要跨模块查看关联业务 | 查客户相关业务、查异常记录 |
| **配置管理员** | 维护 Global Search 配置 | 配置 Business Resource、字段、Snapshot |

## 2.3 假设与依赖

- 用户已登录 Odoo，具有正常业务权限
- Odoo 18 标准 Web Client 可用
- PostgreSQL 数据库正常
- V1 不依赖外部搜索引擎

## 2.4 设计原则

| 原则 | 说明 | 优先级 | 来源 |
|---|---|---|---|
| **配置驱动** | 管理员决定搜哪些业务资源、哪些字段、显示什么 | MUST | RAR |
| **用户语言优先** | 用户看到业务语言，不是 Odoo 模型名 | MUST | RAR |
| **权限不扩大** | 搜索结果不超过用户正常权限可访问范围 | MUST | RAR |
| **安全失败关闭** | 权限相关异常必须失败关闭，不返回未经权限确认的数据 | MUST | SRS-DEC |
| **无权限字段不参与搜索** | 用户无权访问的字段不得参与搜索、排序、计数 | MUST | SRS-DEC |
| **Query 与 Refinement 分离** | Raw Query 不变，筛选条件可叠加 | MUST | RAR |
| **渐进式收窄** | 不要求用户一次表达完整条件 | SHOULD | RAR |
| **失败安全（非权限）** | 单个模型/字段失败不影响整体搜索 | SHOULD | SRS-DEC |

---

# 3. 功能需求

## 3.1 L1 — Identifier-based Discovery

### FR-L1-001 标识符搜索 【MUST】【RAR】

系统 MUST 支持用户通过业务标识符搜索记录。

**输入示例：** `MSCU1234567`、`SO/2026/00391`、`ABC123`

**验收：**

- 用户在搜索框输入标识符
- 系统在管理员配置的 Identifier 字段中匹配
- 返回匹配记录及关联业务记录

**追溯：** RAR §6、§11

### FR-L1-002 标识符匹配规则 【MUST】【SRS-DEC】

系统 MUST 支持按字段配置的标识符匹配规则。

**每条 Identifier 字段 MUST 支持以下配置：**

| 配置项 | 取值 | 默认 |
|---|---|---|
| 匹配类型 | 精确 / 前缀 / 包含 | 精确 |
| 最小输入长度 | 整数 | 1 |
| 忽略大小写 | 是 / 否 | 是 |
| 忽略空格 | 是 / 否 | 否 |
| 忽略连字符 | 是 / 否 | 否 |
| 前导零归一化 | 是 / 否 | 否 |
| 匹配优先级 | 整数 | 100 |

**系统 MUST NOT 对所有标识符默认启用"包含匹配"或"格式标准化"。**

**用户可观察的排序行为：**

- 精确命中优先于前缀命中
- 前缀命中优先于包含命中
- 同类型命中按字段优先级降序

**具体评分公式、Field Weight 数值、索引方式不在 SRS 定义，属于技术研究范围。**

**追溯：** RAR §11.1、SRS V1.0 评审 P1-8、SRS V1.3 评审 P0-3

### FR-L1-003 标识符关联记录发现 【MUST】【RAR】

对于标识符，系统 MUST 能发现其关联的业务记录。

**示例：** `MSCU1234567` → 运输、报关、入库、出库等记录

**关联范围由 Relation Path 配置决定（见 BR-012）。**

**追溯：** RAR §6、§19

## 3.2 L2 — Entity Discovery

### FR-L2-001 实体搜索 【MUST】【RAR】

系统 MUST 支持用户通过业务实体名称搜索。

**输入示例：** `A客户`、`Vitamin D`、`张三`、`Rotterdam DC`

**验收：**

- 用户在搜索框输入实体名称
- 系统先解析实体（Entity Resolution）
- 再发现该实体的关联业务记录（Related Business Discovery）

**追溯：** RAR §7、§11.1

### FR-L2-002 实体匹配规则 【MUST】【SRS-DEC】

系统 MUST 支持以下实体匹配能力：

| 能力 | 优先级 | 来源 |
|---|---|---|
| 精确匹配 | MUST | RAR |
| 大小写不敏感 | MUST | SRS-DEC |
| 简称匹配 | SHOULD | RAR |
| 别名匹配 | SHOULD | RAR |
| 拼音匹配 | MAY | OPEN |
| 中英文混合 | MAY | OPEN |

**实体匹配范围 MUST 按当前用户公司上下文过滤。**

**追溯：** RAR §4.3、§7、SRS V1.3 评审 P1-6

### FR-L2-003 实体歧义处理 【MUST】【SRS-DEC】

当多个实体命中时，系统 MUST 明确处理方式。

**用户可观察的行为：**

| 情况 | 行为 |
|---|---|
| 唯一命中 | 直接使用该实体 |
| 多个命中且最高分明显高于次高 | 使用最高分实体，并在 Query Understanding 中显示可修改 |
| 多个命中且分差接近 | **MUST 展示候选实体列表**，由用户选择 |
| 无命中 | **统一作为 Free Text 处理**（见 FR-L3-005） |

**候选实体列表 MUST 显示：** 实体名称、关键识别字段（如编号、地址）、匹配类型。

**候选截断后 MUST 提示"还有更多候选"。**

**简称匹配 MUST NOT 跨公司。**

**具体评分阈值、评分公式、候选最大数量由技术研究确定，由 CFG-010 管理。**

**追溯：** RAR §7、SRS V1.0 评审 P1-9、SRS V1.3 评审 P0-3

### FR-L2-004 关系扩展 【MUST】【RAR】

系统 MUST 支持从实体扩展关联业务记录。

**扩展范围由 Relation Path 配置决定（见 BR-012）。**

**扩展规则：**

- 扩展深度 MUST 有上限（由 BR-012 配置决定）
- 每一跳 MUST 应用 Record Rule
- 关联记录无权访问时 MUST 跳过（见 FR-PM-004）
- 同一记录通过多路径命中时 MUST 去重（见 BR-011）

**追溯：** RAR §19

## 3.3 L3 — Conditional Discovery

### FR-L3-001 V1 支持的查询语法 【MUST】【SRS-DEC】

系统 MUST 支持以下有限语法，MUST NOT 承诺完整自然语言解析。

**支持的语义单元：**

| 单元 | 示例 | 识别方式 |
|---|---|---|
| Identifier | `MSCU1234567` | 匹配配置的 Identifier 字段格式 |
| Entity | `A客户` | 匹配配置的 Entity 字段 |
| Time | `6月`、`上个月`、`本周`、`2026-06` | 匹配时间表达词典 |
| Business Resource | `出库`、`订单`、`发票` | 匹配配置的 Business Resource Vocabulary |
| State | `未完成`、`逾期` | 匹配配置的 State 映射 |
| Location | `Rotterdam` | 匹配配置的 Location 字段 |
| Free Text | 其他 | 见 FR-L3-005 |

**输入约定：**

```
系统 MUST 支持以空格分隔的半结构化输入，例如：
    A客户 今年 6月 未完成 出库

系统 SHOULD 识别中文连续文本输入，例如：
    A客户今年6月没完成的出库单

系统 MUST NOT 要求用户使用布尔操作符、字段名或特殊查询语法。
```

**中文连续文本的词法规则（SHOULD）：**

系统 SHOULD 支持以下确定性切分：

| 规则 | 说明 |
|---|---|
| 时间表达优先 | `今年6月`、`上个月`、`本周` 优先识别为完整时间单元 |
| 状态词优先 | `没完成`、`未完成`、`待处理` 优先识别为 State |
| 资源词优先 | `出库单`、`入库单`、`订单` 优先识别为 Business Resource |
| 助词忽略 | `的`、`了` 等助词 SHOULD 被忽略 |
| 空格可选 | `今年6月` 与 `今年 6月` SHOULD 等价 |

**如果实现中文连续文本识别，MUST 保证上述示例可被稳定识别。**

**V1 不承诺的输入（OUT）：**

- 否定词（如"不是 A客户"）
- 布尔表达式（AND / OR / NOT）
- 括号分组
- 引号短语
- 排除词（如 `-出库`）
- 同义词推断（除词法规则已覆盖的）
- 复杂自然语言句式（如"帮我找一下上个月 A客户那些还没处理完的出库"）

**追溯：** RAR §12、SRS V1.0 评审 P0-1、SRS V1.2 评审 P0-4、SRS V1.3 评审 P1-4

### FR-L3-002 条件解析 【MUST】【SRS-DEC】

系统 MUST 能解析用户输入中的业务条件，形成 Parsed Conditions。

**解析结果示例：**

```
Raw Query: A客户 今年 6月 未完成 出库
Parsed Conditions:
  Entity:   A客户（customer）
  Time:     2026-06（year=2026, month=6）
  Resource: 出库（outbound）
  State:    未完成（incomplete）
```

**解析失败处理：**

| 失败类型 | 行为 |
|---|---|
| 完全无法识别 | 作为 Free Text 处理 |
| 部分识别 | 已识别条件生效，未识别部分作为 Free Text |
| 歧义（如 `6月` 缺年份） | 使用默认推断规则（见 FR-L3-004），并在 Query Understanding 中显示可修改 |
| 冲突（如 Query 说"出库"但 Resource 匹配到"入库"） | 以最高分匹配为准，并在 Query Understanding 中显示 |

**`没完成` 映射失败时 MUST：**

- 不返回宽泛结果
- 在 Query Understanding 中显示"未识别状态"，不应用 State 条件
- 用户可在 Refinement 中手动选择状态

**追溯：** RAR §12、SRS V1.0 评审 P0-1

### FR-L3-003 State / Condition 语义 【MUST】【RAR】

系统 MUST 支持业务状态语义的筛选。

**示例：** 未完成、已完成、待处理、异常、逾期、待确认、待对账、缺货

**映射规则：**

- 用户看到的是业务状态语言
- 系统映射到具体 Business Resource 的系统状态
- 映射关系由 Business Resource 配置决定
- 同一业务状态在不同 Business Resource 上可映射到不同系统状态集合

**追溯：** RAR §10.2、§18、BR-005

### FR-L3-004 时间条件 【MUST】【SRS-DEC】

系统 MUST 支持时间条件的解析与筛选。

**支持的时间表达：**

| 类型 | 示例 | 基准 |
|---|---|---|
| 绝对月份 | `2026年6月`、`2026-06` | 明确 |
| 绝对日期 | `2026-06-15` | 明确 |
| 相对月份 | `上个月`、`本月` | 当前用户时区 |
| 相对周 | `本周`、`上周` | 当前用户时区，周起始日见 BR-009 |
| 相对年 | `今年`、`去年` | 当前用户时区 |
| 范围 | `2026-06-01 ~ 2026-06-30` | 明确 |

**缺少年份时 MUST 按以下确定性规则推断：**

```
缺少年份时默认使用当前用户时区的当前年份；
如果解析结果为未来日期，不自动回退；
在 Query Understanding 中展示完整日期范围，允许用户修改。
```

**系统 MUST NOT 使用"用户历史行为偏好"或类似机制推断年份。**

**追溯：** RAR §15、BR-009、SRS V1.1 评审 P0-5

### FR-L3-005 Free Text 匹配 【MUST】【SRS-DEC】

Free Text 是 V1 的兜底匹配方式，当输入不匹配 Identifier、Entity、Time、Resource、State、Location 时使用。

**匹配范围：**

| 配置项 | 默认 | 说明 |
|---|---|---|
| 参与匹配的字段 | 管理员配置的 Text 字段 | 仅配置为 Free Text 的字段 |
| 匹配方式 | 包含匹配 | 具体检索方式由技术研究确定 |
| 大小写 | 不敏感 | |
| 中文分词 | 否 | V1 不支持 |
| 多词组合 | AND | 多个词 MUST 同时匹配 |
| 跨关联字段 | 否 | 不跨关联字段 |
| 最小输入长度 | 2 | |

**范围边界：**

- Free Text 只匹配管理员配置的 Text 字段
- V1 不承诺 Chatter、附件和 PDF 内容
- 具体检索方式由技术研究确定

**用户可观察的排序行为：**

- Free Text 命中优先级低于 Identifier / Entity / Resource / State
- 同类型命中按字段优先级降序

**Free Text 与 Identifier / Entity 命中的合并：**

- 同一记录同时被 Free Text 和 Identifier 命中时，MUST 只出现一次
- 排序以最高相关性为准

**追溯：** RAR §12、SRS V1.1 评审 P1-9、SRS V1.3 评审 P1-5

## 3.4 Result Refinement

### FR-RF-001 二次筛选机制 【MUST】【RAR】

系统 MUST 支持在搜索结果页对结果进行二次筛选，且不修改 Raw Query。

**核心规则：**

- Raw Query 与 Refinement Conditions 分离
- Refinement Conditions 可叠加、可删除
- Refinement 不改变 Raw Query
- 结果实时收窄

**追溯：** RAR §14、BR-006

### FR-RF-002 Business Resource 筛选 【MUST】【SRS-DEC】

系统 MUST 支持按 Business Resource 筛选结果。

**UI 形态：** Tab 切换

**显示规则：**

```
仅显示当前结果集中实际存在的 Business Resource。
即：如果某 Business Resource 在当前 Effective Conditions 下计数为 0，
则该 Tab MUST NOT 显示。
```

**示例：**

```
[全部 56] [订单 18] [入库 22] [出库 31] [发票 14]
```

**计数规则见 BR-013。**

**追溯：** RAR §16.1、SRS V1.2 评审 P0-2

### FR-RF-003 日期筛选 【MUST】【RAR】

系统 MUST 支持按日期范围筛选结果。

**时间范围选项：**

- 不限
- 今天
- 本周
- 本月
- 上个月
- 今年
- 去年
- 自定义日期范围

**追溯：** RAR §15

### FR-RF-004 业务日期语义 【MUST】【RAR】

系统 MUST 使用 Business Resource 配置的默认业务日期进行时间筛选。

**示例：**

- 入库 → 入库业务日期
- 出库 → 出库业务日期
- 运输 → 运输业务日期
- 发票 → 发票日期

**用户 SHOULD NOT 被要求理解底层数据库字段。**

**追溯：** RAR §15.4、BR-004

### FR-RF-005 状态筛选 【MUST】【RAR】

系统 MUST 支持按业务状态筛选结果。

**状态选项因 Business Resource 不同而变化。**

**追溯：** RAR §16.2

### FR-RF-006 日期口径切换 【MAY】【OPEN】

系统 MAY 允许用户切换日期口径。

**如果实现，MUST 在 Query Understanding 中显示当前口径。**

**追溯：** RAR §15、SRS V1.3 评审 P1-6

### FR-RF-007 Refinement 初始状态 【MUST】【SRS-DEC】

用户首次搜索后，Refinement 各维度的初始值 MUST 为：

| 维度 | 初始值 |
|---|---|
| Business Resource | 全部 |
| Date | 不限 |
| State | 全部 |

**追溯：** RAR §14

### FR-RF-008 Refinement 状态管理 【MUST】【SRS-DEC】

系统 MUST 明确定义 Refinement 与 Query、结果、Preview 的状态关系。

| 用户操作 | Raw Query | Refinement | 左侧结果 | 右侧 Preview |
|---|---|---|---|---|
| 修改搜索框 | 更新 | 重置 | 更新 | 清空 |
| 切换 Tab | 不变 | 更新 | 更新 | 保持/清空 |
| 修改 Date | 不变 | 更新 | 更新 | 保持/清空 |
| 修改 State | 不变 | 更新 | 更新 | 保持/清空 |
| 切换选中记录 | 不变 | 不变 | 不变 | 切换 |

**"保持/清空"规则：**

- 如果选中记录仍在新结果集中 → 保持
- 如果不在 → 清空

**追溯：** RAR §14

### FR-RF-009 两条路径汇合 【MUST】【RAR】

系统 MUST 支持两条路径到达同一 Filtered Result Set。

**路径 A：** 一次组合表达（`A客户 今年 6月 未完成 出库`）

**路径 B：** 简单搜索 + 二次筛选（`A客户` → 出库 → 2026年6月 → 未完成）

**两条路径 MUST 产生相同的 Effective Conditions，进而产生相同的 Filtered Result Set。**

**"相同"的定义见 BR-008。**

**追溯：** RAR §14.3、SRS V1.0 评审 P0-2

## 3.5 Query Understanding 可见性

### FR-QU-001 查询理解展示 【MUST】【SRS-DEC】

系统 MUST 将当前 Effective Conditions 显式展示给用户。

**展示形式：**

```
客户：A客户欧洲有限公司 ×
资源：出库 ×
日期：2026年6月 ×
状态：未完成 ×
```

**用户操作：**

- 查看系统如何理解 Query
- 删除某个条件
- 修改日期
- 切换业务资源
- 调整状态

**理由：** 如果解析结果不可见，用户无法纠错，L3 不可验收。AC-008 和 AC-012 依赖此能力。

**追溯：** RAR §17（建议）、SRS V1.3 评审 P0-1

### FR-QU-002 条件可编辑 【SHOULD】【RAR】

用户 SHOULD 能从 Query Understanding 展示中直接编辑条件。

**删除条件后，Raw Query MUST 不变。**

**追溯：** RAR §17

## 3.6 Search Workspace

### FR-SW-001 统一搜索入口 【MUST】【RAR】

系统 MUST 提供统一的搜索入口。

**输入：**

- 简单标识符：`MSCU1234567`
- 实体：`A客户`
- 组合条件：`A客户 今年 6月 未完成 出库`

**追溯：** RAR §21.1

### FR-SW-002 结果发现 【MUST】【RAR】

系统 MUST 返回匹配的业务资源和业务记录。

**结果组织：**

- 按用户理解的业务类别组织，不按 Technical Model
- 提供 Business Resource 分类及数量

**追溯：** RAR §21.2、§22

### FR-SW-003 Snapshot 展示 【MUST】【RAR】

每条搜索结果 MUST 提供业务摘要（Snapshot）。

**Snapshot 内容由 Business Resource 配置决定。**

**Snapshot MUST NOT 泄露用户无权访问的字段。**

**追溯：** RAR §21.4、SRS V1.0 评审 P0-4

### FR-SW-004 Form Preview 【MUST】【RAR】

桌面端 MUST 提供左右分栏的 Search Workspace。

**布局：**

```
┌─────────────────────────────────────────────────────────┐
│ Search anything...                                      │
├─────────────────────────────────────────────────────────┤
│ 全部  订单  入库  出库  运输  发票      日期 ▾ 状态 ▾   │
│ 客户：A客户 ×   资源：出库 ×   日期：2026年6月 ×        │
├─────────────────────────┬───────────────────────────────┤
│ Search Results          │ Form Preview                  │
│                         │                               │
│ Result A                │ Actual Odoo Form             │
│ Result B                │                               │
│ Result C                │                               │
└─────────────────────────┴───────────────────────────────┘
```

**交互：**

- 单击左侧结果 → 右侧 Preview 当前记录
- 切换结果 → 保留 Query 和 Refinement 条件，仅切换 Preview
- Preview 不因切换导致重新执行完整搜索

**Preview 编辑能力见 FR-SW-007。**

**追溯：** RAR §21.5

### FR-SW-005 打开完整记录 【MUST】【RAR】

用户 MUST 能从搜索结果打开完整记录。

**交互方式：**

- 双击 → 新浏览器 Tab 打开
- Ctrl/Cmd + Click → 新浏览器 Tab 打开（遵循浏览器习惯）

**要求：**

- 原 Search Workspace 状态保持
- 新 Tab 进入标准 Odoo Form View
- 新 Tab 继续执行原有权限和业务逻辑

**追溯：** RAR §21.6

### FR-SW-006 结果摘要 【MUST】【RAR】

对于范围较大的搜索，系统 MUST 提供结构化摘要。

**示例：**

```
A客户欧洲有限公司

全部            126
订单             56
入库             22
出库             29
运输             11
发票              8
```

**用户点击某一类别后，结果集收窄。**

**计数规则见 BR-013。**

**追溯：** RAR §22

### FR-SW-007 Form Preview 编辑能力 【MUST】【SRS-DEC】

**V1 决定：Preview MUST 为只读。**

| 能力 | V1 决定 |
|---|---|
| 只读 | MUST |
| 编辑 | MUST NOT |
| 保存 | MUST NOT |
| 执行业务按钮 | MUST NOT |
| Chatter 操作 | MUST NOT |
| 附件操作 | MUST NOT |
| 活动操作 | MUST NOT |

**Preview MUST 显示记录被删除或权限变化时的安全提示。**

**追溯：** RAR §21.5（Open）、SRS V1.3 评审 P0-1

## 3.7 权限

### FR-PM-001 权限继承 【MUST】【RAR】

Global Search MUST 遵守当前登录用户的 Odoo 权限。

**需继承：**

- Model Access Rights
- Record Rules
- Multi-company Context
- 其他适用于当前记录的标准 Odoo 权限约束

**追溯：** RAR §23

### FR-PM-002 权限不扩大 【MUST】【RAR】

用户通过 Global Search 能发现的信息 MUST NOT 超过其通过正常 Odoo 权限能够访问的信息。

**追溯：** RAR §23

### FR-PM-003 无权记录不泄露 【MUST】【RAR】

用户无权访问的记录 MUST NOT 出现在：

- 搜索结果
- Snapshot
- Preview
- 分类计数
- Query Understanding
- 任何匹配提示中

**追溯：** RAR §23、SRS V1.0 评审 P0-4

### FR-PM-004 关联扩展权限 【MUST】【RAR】

关联扩展过程中每一跳 MUST 应用 Record Rule。

**规则：**

- 主记录可访问但关联记录不可访问 → 关联记录跳过
- 关联记录跳过不影响主记录返回
- 关联记录跳过 MUST NOT 通过分类计数泄露数量

**追溯：** RAR §23、SRS V1.0 评审 P0-4

### FR-PM-005 字段权限 【MUST】【SRS-DEC】

用户无权访问的字段 MUST NOT 出现在：

- Snapshot
- Preview
- Query Understanding
- 搜索结果

**字段权限分为三类（重要）：**

| 字段用途 | 无权限时的行为 |
|---|---|
| **Snapshot 展示字段** | 省略字段，记录可返回 |
| **搜索字段（Searchable Field）** | 从当前用户的搜索范围中排除；MUST NOT 参与搜索、排序、相关性计算、命中高亮、Query Understanding、分类计数；不得因为该字段命中而返回记录 |
| **权限判断字段** | 失败关闭，不返回相关记录 |

**搜索字段的排除规则见 CON-011。**

**追溯：** RAR §23、SRS V1.0 评审 P0-4、SRS V1.2 评审 P0-1

### FR-PM-006 配置权限 【MUST】【SRS-DEC】

配置维护权限与业务数据权限 MUST 分离。

**规则：**

- 配置管理员可维护配置
- 普通用户只读配置
- 配置 read ACL 不授予业务数据访问权
- **配置管理员的字段读取权限不代表所有用户的字段读取权限**
- 运行时 MUST 按当前用户权限过滤

**配置时的字段校验：**

- 配置管理员 MUST NOT 配置自己无权读取的字段
- 这是配置时的校验，不代表运行时其他用户的权限

**最终安全边界是运行时按用户过滤。**

**追溯：** RAR §23、SRS V1.0 评审 P0-4、SRS V1.3 评审 P1-7

### FR-PM-007 Refinement 与权限交互 【MUST】【SRS-DEC】

Refinement 的每个维度（Resource / Date / State）在执行时 MUST 应用当前用户的权限过滤。

**具体表现：**

| 情况 | 行为 |
|---|---|
| 用户对某 Business Resource 无访问权 | 该 Tab MUST NOT 显示 |
| 用户对某 Business Resource 有访问权且当前结果集有数据 | Tab 显示 |
| 用户对某 Business Resource 有访问权但当前结果集为空 | Tab MUST NOT 显示（与 FR-RF-002 一致） |
| 用户对某记录无访问权 | 记录 MUST NOT 出现在结果中 |

**追溯：** RAR §23、SRS V1.0 评审 P0-4、SRS V1.2 评审 P0-2

### FR-PM-008 多公司 【MUST】【RAR】

系统 MUST 遵守 Multi-company Context。

**规则：**

- 实体解析 MUST 按当前用户公司上下文
- 搜索结果 MUST 按当前用户公司上下文
- 共享记录 MUST 按 Odoo 标准规则处理
- 公司为空的记录 MUST 按 Odoo 标准规则处理

**追溯：** RAR §23、SRS V1.0 评审 P0-4

## 3.8 无结果与异常

### FR-ER-001 无结果提示 【MUST】【RAR】

当没有记录满足搜索条件时，系统 MUST 明确显示：

> No results found.

**追溯：** RAR §18

### FR-ER-002 结果状态 【MUST】【SRS-DEC】

系统 MUST 区分以下结果状态：

| 状态 | 含义 | 用户可见 |
|---|---|---|
| 完整成功 | 所有模型搜索成功 | 结果正常 |
| 部分成功 | 部分模型搜索失败，部分成功 | 结果 + 提示"部分模型搜索异常" |
| 完全失败 | 所有模型搜索失败 | 错误提示 |
| 配置错误 | 配置无效 | 提示配置问题 |
| 权限拒绝 | 权限不足 | 安全提示 |
| 超时 | 搜索超时 | 超时提示 + 已返回结果 |

**追溯：** RAR §18、SRS V1.0 评审 P0-4

### FR-ER-003 错误分类与部分成功 【MUST】【SRS-DEC】

系统 MUST 明确定义各错误类型是否允许返回部分结果。

**按字段用途区分：**

| 字段用途 | 读取异常行为 |
|---|---|
| Snapshot 展示字段 | 省略字段，记录可返回 |
| 搜索字段 | 当前模型标记异常或跳过该字段 |
| Business Date / State 映射字段 | 该资源标记部分失败 |
| 权限判断字段 | 失败关闭，不返回相关记录 |
| Relation Path 字段 | 跳过关联路径，不泄露数量 |

**按错误类型区分：**

| 情况 | 是否允许返回部分结果 |
|---|---|
| 普通模型超时 | 可以 |
| 配置错误（单模型） | 可以，跳过该模型 |
| 配置错误（全局） | 不可以 |
| 主记录权限校验失败 | 不可以 |
| 关联记录无权访问 | 可跳过，不得泄露数量 |
| 字段读取异常 | 按字段用途区分（见上表） |
| 字段权限不足 | 按字段用途区分（见上表） |
| RPC 异常（单模型） | 可以，跳过该模型 |
| RPC 异常（全局） | 不可以 |

**权限相关异常 MUST 失败关闭（见 CON-008）。**

**追溯：** SRS V1.1 评审 P1-11、SRS V1.2 评审 P1-7

---

# 4. 业务规则

## BR-001 Business Resource Vocabulary 【MUST】【RAR】

用户语言与系统数据之间的语义对应关系 MUST 可配置。

**配置层级：**

```
用户语言（"出库单"）
    ↓
Business Resource（Outbound）
    ↓
Odoo 实现（stock.picking）
```

**追溯：** RAR §13

## BR-002 业务资源类型 【MUST】【RAR】

Business Resource MUST 支持以下类型：

| 类型 | 定义 | 配置要求 |
|---|---|---|
| 单模型资源 | 一个 Business Resource 对应一个 Technical Model | 一个模型 |
| 复合资源 | 一个 Business Resource 由多个 Technical Model 组成 | 多个模型 + 合并规则 |
| 关联资源 | 通过 Relation Path 从其他资源扩展 | Relation Path 配置 |

**追溯：** RAR §13.2、SRS V1.0 评审 P0-3

## BR-003 复合资源合并规则 【MUST】【SRS-DEC】

复合资源 MUST 定义以下合并规则。

**配置示例：**

```
订单（复合资源）
├── sale.order
│   ├── 标题字段：name
│   ├── 日期字段：date_order
│   ├── 状态映射：sale → 未完成 / 已完成 / 已取消
│   └── Snapshot 字段：name, partner_id, amount_total
└── purchase.order
    ├── 标题字段：name
    ├── 日期字段：date_order
    ├── 状态映射：purchase → 未完成 / 已完成 / 已取消
    └── Snapshot 字段：name, partner_id, amount_total
```

**合并规则配置项：**

| 配置项 | 说明 |
|---|---|
| 各模型标题字段 | 统一映射到复合资源的标题 |
| 各模型日期字段 | 统一映射到复合资源的 Business Date |
| 各模型状态映射 | 统一映射到复合资源的业务状态 |
| 各模型 Snapshot 字段 | 统一映射到复合资源的 Snapshot 格式 |
| 排序规则 | 各模型记录如何统一排序（见 BR-003.1） |
| 计数规则 | 见 BR-013 |

### BR-003.1 复合资源默认排序 【MUST】【SRS-DEC】

复合资源 MUST 支持默认排序：

```
相关性降序
→ Business Date 降序
→ Technical Model 优先级（由配置决定）
→ Record ID 升序
```

**Technical Model 优先级规则：**

- 复合资源的 Technical Model 优先级 MUST 唯一
- 配置保存时 MUST 禁止重复优先级
- 未配置时 MUST 按模型技术名称稳定排序

**其他规则：**

- Business Date 为空时排在非空之后
- 同分时 MUST 保证结果稳定
- 复合资源 MAY 覆盖默认排序

**单模型资源使用相同默认排序，但跳过"Technical Model 优先级"步骤。**

**追溯：** SRS V1.1 评审 P0-3、SRS V1.2 评审 P0-3、SRS V1.3 评审 P1-8

## BR-004 Business Date 【MUST】【RAR】

每种 Business Resource MUST 定义默认业务日期语义。

**示例：**

- 入库 → 实际入库日期
- 出库 → 实际出库日期
- 发票 → 发票日期

**复合资源 MUST 定义每个组成模型的 Business Date。**

**追溯：** RAR §15.4、SRS V1.0 评审 P0-5

## BR-005 State 映射 【MUST】【RAR】

用户业务状态语言 MUST 映射到不同 Business Resource 的系统状态。

**示例：**

```
未完成 → 运输订单: state in [...]
        → 入库单: state in [...]
        → 出库单: state in [...]
        → 销售订单: state in [...]
```

**映射关系 MUST 由管理员配置。**

**追溯：** RAR §18

## BR-006 Query 与 Refinement 分离 【MUST】【RAR】

Raw Query 是用户原始输入，Refinement Conditions 是二次筛选条件。两者 MUST 独立管理。

**追溯：** RAR §14.2

## BR-007 Effective Conditions 【MUST】【RAR】

Effective Conditions MUST 通过以下链路产生：

```
Raw Query
    ↓
Parsed Conditions（系统解析）
    ↓
Refinement Conditions（用户筛选）
    ↓
Effective Conditions（合并、去重、冲突消解）
    ↓
Filtered Result Set
```

**合并规则：**

| 情况 | 规则 |
|---|---|
| 同维度无冲突 | AND 合并 |
| 同维度冲突（Query 说"出库"，Refinement 选"入库"） | Refinement 优先 |
| 同维度重复 | 去重 |
| 不同维度 | AND 合并 |
| 解析失败的条件 | 不进入 Effective Conditions |
| 用户删除的条件 | 从 Effective Conditions 移除，但 Raw Query 不变 |

**冲突消解后 MUST 在 Query Understanding 中显示。**

**追溯：** RAR §14.2、SRS V1.0 评审 P0-2

## BR-008 两条路径等价 【MUST】【RAR】

Limited Query Input 与 Refinement Conditions MUST 映射到同一条件模型。

**等价定义：**

- 路径 A（一次组合表达）和路径 B（简单搜索 + 二次筛选）MUST 产生相同的 Effective Conditions（维度值相同）
- 如果 Effective Conditions 相同，则 Filtered Result Set MUST 相同（记录 ID 集合相同）
- 如果 Effective Conditions 不同，则结果不同是允许的，但 MUST 在 Query Understanding 中可见

**追溯：** RAR §14.3、SRS V1.0 评审 P0-2

## BR-009 日期规则 【MUST】【SRS-DEC】

### BR-009.1 周起始日

`本周`、`上周` 的周起始日 MUST 按当前用户的 Odoo 语言/区域设置确定。

### BR-009.2 时区

- `今天`、`本周`、`本月`、`今年` MUST 使用当前用户时区
- DateTime 转日期 MUST 使用当前用户时区
- 服务器时区 MUST NOT 作为默认

### BR-009.3 日期范围语义

日期范围 MUST 从业务语义定义：

```
包含 2026-06-01 至 2026-06-30 的全部业务时间。
```

**具体实现（起始日期包含、结束日期次日排除等）不在 SRS 定义，属于技术研究范围。**

### BR-009.4 空日期

日期字段为空的记录：

- 默认 MUST NOT 出现在日期筛选结果中
- 用户 MAY 通过配置选择是否包含空日期记录

### BR-009.5 财年

`今年` 默认 MUST 使用日历年。
如果公司配置了财年，系统 SHOULD 允许配置为财年。

### BR-009.6 跨资源合并 【SRS-DEC】

跨资源日期筛选时，各资源 MUST 按其 Business Date 独立过滤，再合并。
合并后 MUST 标注每条记录使用的 Business Date。

**追溯：** RAR §15、SRS V1.0 评审 P0-5、SRS V1.2 评审 P1-9、SRS V1.3 评审 P0-1

## BR-010 条件组合规则 【MUST】【SRS-DEC】

- 不同维度之间 MUST 为 AND
- 同维度内多值 MUST 为 OR（如 State 选中"未完成"和"异常"）
- 不支持否定条件（V1 OUT）
- 不支持布尔表达式（V1 OUT）

**追溯：** SRS V1.0 评审 P0-2

## BR-011 结果去重与 Result Identity 【MUST】【SRS-DEC】

**Result Identity = (Business Resource, Technical Model, Record ID)**

**去重规则：**

- 同一记录通过多个字段或路径命中时 MUST 只出现一次
- 去重依据为 Result Identity
- 保留最高相关性
- 保留所有命中信息（用于排序和展示）

**展示规则：**

- 同一 `Technical Model + Record ID` 属于两个 Business Resource 时，MUST 分别展示（属于不同 Result Identity）
- 复合资源内部多个模型的记录 MUST 分别有各自的 Result Identity

**追溯：** SRS V1.0 评审 P1-11、SRS V1.1 评审 P1-10

## BR-012 Relation Path 【MUST】【SRS-DEC】

Business Resource 之间的关联路径 MUST 可配置。

**配置项：**

| 配置 | 说明 |
|---|---|
| 源资源 | 从哪个资源扩展 |
| 目标资源 | 扩展到哪个资源 |
| 关联字段 | 通过哪个字段关联 |
| 关联方向 | Many2one / One2many / Many2many |
| 是否允许中间模型 | 是否允许经过中间模型 |
| 中间模型字段 | 如果允许中间模型，指定中间模型的关联字段 |
| 最大深度 | 扩展深度上限，默认 2 |
| 优先级 | 多路径时的优先级 |

**规则：**

- 每一跳 MUST 应用 Record Rule
- 关联记录无权访问时 MUST 跳过
- 扩展深度 MUST 有上限
- 循环关联 MUST 被检测并终止

**追溯：** RAR §19、SRS V1.0 评审 P0-3、SRS V1.3 评审 P1-6

## BR-013 Result Count 【MUST】【SRS-DEC】

**计数规则：**

| 计数项 | 规则 |
|---|---|
| 分类计数 | 按 Result Identity 去重后计数 |
| "全部"计数 | 等于当前用户可见、满足 Effective Conditions 的所有 Result Identity 的集合大小 |
| 复合资源内部 | 各模型记录分别计数，汇总到复合资源 |
| 关联资源 | 计入目标资源，不计入源资源 |
| 计数受分页影响 | MUST NOT 受分页影响 |
| 计数受 Refinement 影响 | MUST 反映当前 Refinement 条件下的数量 |
| 无权记录计数 | MUST NOT 泄露（不显示、不计数） |
| 无权限字段命中 | MUST NOT 计入（见 CON-011） |
| Partially failed model | MUST 有单独状态，不计入"全部"总数 |

**计数 MUST 为精确值。V1 不支持近似计数。**

**每个 Tab 的计数范围：**

- 分类 Tab：该 Business Resource 下的 Result Identity 数量
- "全部" Tab：所有可见 Result Identity 数量（各分类去重后之和）

**追溯：** SRS V1.1 评审 P1-10、SRS V1.2 评审 P1-8

## BR-014 配置生命周期 【MUST】【SRS-DEC】

配置 MUST 支持以下状态和操作：

| 操作 | 效果 |
|---|---|
| 保存草稿 | 不生效 |
| 发布配置 | 立即生效 |
| 停用配置 | 立即失效 |
| 回滚配置 | 恢复到指定已发布版本，立即生效 |

**补充规则：**

- 发布和回滚权限 MUST 由配置管理员组控制
- 配置版本 MUST 保留最近 10 个版本（默认值，可配置）
- 回滚 MUST 立即生效
- 配置变更审计由项目现有 `audit_log` 模块负责记录
- Global Search 不定义审计日志保留周期；保留策略由 `audit_log` 模块负责

**追溯：** SRS V1.1 评审 P0-2、P1-10、SRS V1.2 评审 P1-11

## BR-015 配置校验 【MUST】【SRS-DEC】

配置保存前 MUST 校验：

| 校验项 | 规则 |
|---|---|
| 模型存在 | 引用的 ir.model 必须存在 |
| 字段存在 | 引用的 ir.model.fields 必须存在 |
| 字段类型 | 字段类型必须支持展示/搜索 |
| 字段所属模型 | 字段必须属于配置的模型 |
| View 与模型匹配 | 配置的 View 必须属于配置的模型 |
| 重复字段 | 同一配置不重复字段 |
| 资源唯一 | 同一 Resource 名称唯一 |
| 优先级唯一 | 复合资源的 Technical Model 优先级唯一 |
| 管理员权限 | 配置管理员不能配置自己无权读取的字段 |

**校验失败 MUST 阻止保存并提示。**

**追溯：** SRS V1.1 评审 P1-10、SRS V1.3 评审 P1-8

## BR-016 Vocabulary 配置 【MUST】【SRS-DEC】

Business Resource Vocabulary MUST 支持以下配置：

| 配置项 | 说明 |
|---|---|
| 显示名称 | 用户看到的业务名称 |
| 别名 | 用户可能使用的其他名称 |
| 语言 | 该词汇适用的语言 |
| 公司范围 | 该词汇适用的公司 |
| 优先级 | 多词汇匹配时的优先级 |
| 生效状态 | 启用 / 停用 |

**Vocabulary 配置 MUST 支持多语言。**

**追溯：** SRS V1.3 评审 P1-6

## BR-017 Entity 字段配置 【MUST】【SRS-DEC】

Entity 匹配的字段来源 MUST 可配置：

| 配置项 | 说明 |
|---|---|
| 匹配字段 | 参与 Entity 匹配的字段 |
| 别名来源 | 别名来自哪个字段或关联模型 |
| 简称来源 | 简称来自哪个字段或关联模型 |
| 拼音来源 | 拼音来自哪个字段或自动生成 |
| 匹配权重 | 各字段的匹配权重 |

**追溯：** SRS V1.3 评审 P1-6

---

# 5. 配置需求

## CFG-001 Business Resource 配置 【MUST】【RAR】

管理员 MUST 能配置 Business Resource。

**配置项：**

| 配置 | 说明 | 适用类型 |
|---|---|---|
| Resource 名称 | 用户看到的业务名称 | 所有 |
| Resource 类型 | 单模型 / 复合 / 关联 | 所有 |
| Odoo 模型 | 实际模型（可多个） | 单模型 / 复合 |
| Identifier 字段 | 用于标识符匹配的字段 | 所有 |
| Entity 关联 | 关联的实体模型和字段 | 所有 |
| Business Date | 默认业务日期字段 | 所有 |
| State 映射 | 业务状态到系统状态的映射 | 所有 |
| Snapshot 配置 | 结果摘要展示字段 | 所有 |
| Relation Path | 从该资源可扩展的关联业务 | 所有 |
| 合并规则 | 复合资源的合并规则（见 BR-003） | 复合 |
| 排序规则 | 复合资源排序覆盖（见 BR-003.1） | 复合（可选） |
| 优先级 | 多资源匹配时的优先级 | 所有 |

**追溯：** RAR §13、SRS V1.0 评审 P0-3

## CFG-002 Searchable Fields 配置 【MUST】【RAR】

管理员 MUST 能为每个 Business Resource 配置可搜索字段。

**配置项：**

| 配置 | 说明 |
|---|---|
| 字段 | 可搜索字段 |
| Search Type | Identifier / Entity / Location / Text |
| Weight | 搜索权重 |
| 匹配类型 | 精确 / 前缀 / 包含（仅 Identifier） |
| 最小输入长度 | 仅 Identifier |
| 忽略大小写 | 仅 Identifier |
| 忽略空格/连字符 | 仅 Identifier |
| 是否用于 Snapshot | 是否在结果摘要中展示 |

**Search Type MUST 包含 Location 类型。**

**Location 类型的匹配方式：**

- 匹配配置的 Location 字段
- 默认匹配方式为"包含匹配"
- 大小写不敏感
- 可配置最小输入长度

**追溯：** RAR §13、SRS V1.0 评审 P1-8、SRS V1.2 评审 P1-5

## CFG-003 Snapshot 配置 【MUST】【RAR】

管理员 MUST 能为每个 Business Resource 配置结果摘要格式。

**配置项：**

- 展示字段
- 展示顺序
- 展示格式

**Snapshot MUST NOT 泄露用户无权访问的字段。**

**追溯：** RAR §21.4、SRS V1.0 评审 P0-4

## CFG-004 Preview Form View 配置 【MUST】【RAR】

管理员 MUST 能为每个 Business Resource 指定 Preview 使用的 Form View。

**如果未指定，按默认规则选择可用 Form View。**

**追溯：** RAR §21.5

## CFG-005 配置权限 【MUST】【SRS-DEC】

配置维护权限与业务数据权限 MUST 分离。

**规则：**

- 配置管理员可维护配置
- 普通用户只读配置
- 配置 read ACL 不授予业务数据访问权
- 配置管理员 MUST NOT 配置自己无权读取的字段
- **最终安全边界是运行时按用户过滤**

**追溯：** RAR §23、SRS V1.0 评审 P0-4、SRS V1.3 评审 P1-7

## CFG-006 默认值配置 【MUST】【SRS-DEC】

管理员 MUST 能配置：

- Refinement 初始值
- 时间范围默认选项
- 状态默认选项

**追溯：** RAR §14

## CFG-007 配置生命周期 【MUST】【SRS-DEC】

配置 MUST 支持：

- 启用 / 停用
- 草稿 / 发布 / 回滚
- 冲突检测
- 字段类型校验
- 模型 / 字段删除后的处理
- View 与模型不匹配处理

**详见 BR-014。**

**追溯：** SRS V1.1 评审 P0-2

## CFG-008 配置隔离 【MAY】【OPEN】

配置 MAY 支持按公司或用户组隔离。

**追溯：** SRS V1.1 评审 P1-10

## CFG-009 计数配置 【MUST】【SRS-DEC】

V1 不支持近似计数配置。所有计数 MUST 为精确值。

**追溯：** SRS V1.1 评审其他建议

## CFG-010 实体评分配置 【MUST】【SRS-DEC】

管理员 MUST 能配置实体评分规则。

**配置项：**

| 配置项 | 默认值 | 说明 |
|---|---|---|
| 唯一命中阈值 | 30 | 最高分与次高分分差 |
| 候选最大数量 | 10 | 超过则截断 |
| 评分权重 | 由管理员配置 | 各匹配类型的相对权重 |

**用户可观察的排序行为：**

- 精确匹配优先于简称匹配
- 明确匹配优先于模糊匹配
- 分差不足时展示候选
- 排序必须稳定

**具体评分公式、分值、匹配算法不在 SRS 定义，属于技术研究范围。**

**追溯：** SRS V1.2 评审 P1-6、SRS V1.3 评审 P0-3

## CFG-011 性能配置 【MUST】【SRS-DEC】

管理员 MUST 能配置：

- 每资源最大返回记录数（默认 50）
- 单模型超时阈值（默认 3 秒）
- 关系路径最大深度（默认 2）

**追溯：** NFR-001、BR-012

## CFG-012 Vocabulary 配置 【MUST】【SRS-DEC】

管理员 MUST 能配置 Business Resource Vocabulary。

**配置项见 BR-016。**

**追溯：** SRS V1.3 评审 P1-6

## CFG-013 Entity 字段配置 【MUST】【SRS-DEC】

管理员 MUST 能配置 Entity 匹配字段来源。

**配置项见 BR-017。**

**追溯：** SRS V1.3 评审 P1-6

---

# 6. 非功能需求

## NFR-001 性能 【MUST】【SRS-DEC】

Global Search 是高频交互功能，性能 MUST 可测试。

**测试基线（Benchmark Profile）：**

| 项 | 基线值 | 说明 |
|---|---|---|
| Odoo 版本 | Odoo 18 | 固定 |
| Python 版本 | 3.11+ | 固定 |
| PostgreSQL 版本 | 15+ | 固定 |
| 性能验证环境 | 以实际执行环境为准 | 必须在 Technical Verification 报告中记录 |
| Business Resource 数量 | 10 | 全部启用 |
| 每个 Business Resource 数据量 | 100 万条 | 每个资源，不是每个模型 |
| 关系路径最大深度 | 2 | |
| 并发用户 | 20 | 并发执行 |
| 典型查询 | 实体 + 日期 + 资源 | 混合查询集合 |
| 测试数据分布 | 生产同等级冷热缓存状态 | 分别测试冷/热缓存 |
| 生产数据脱敏 | 是 | MUST 脱敏复制 |
| 采样次数 | P95 / P99 各 1000 次 | |

**性能指标：**

| 指标 | 目标 |
|---|---|
| 首次结果返回 | P95 ≤ 2 秒 |
| 完整结果返回 | P95 ≤ 5 秒 |
| Refinement 响应 | P95 ≤ 1 秒 |
| Preview 加载 | P95 ≤ 1 秒 |
| 每资源最大返回记录数 | 默认 50，可配置 |
| 超时阈值 | 单模型 3 秒 |
| 分页 / 游标 | MUST 支持 |
| 结果数量精确性 | MUST 精确 |

**"完整结果返回"定义：** 所有配置的 Business Resource 均返回结果或超时。

**性能失败降级行为：**

- 单模型超时 → 返回部分结果 + 提示
- 全局超时 → 错误提示

**追溯：** RAR §19、SRS V1.0 评审 P0-6、SRS V1.3 评审 P1-9

## NFR-002 数据新鲜度 【MUST】【SRS-DEC】

| 数据类型 | 新鲜度要求 |
|---|---|
| 业务记录 | 提交成功后，Global Search 必须在 Technical Verification 确定的最终上限内可见 |
| 配置变更 | 发布成功后，搜索请求无需重启即可使用新配置 |

**初始目标为 5 秒；最终可接受上限由性能 Spike / Technical Verification 确定并记录。**

**追溯：** SRS V1.3 评审 P1-10

## NFR-003 权限安全 【MUST】【RAR】

权限继承 MUST 完整，无泄露风险。

**安全相关异常 MUST 失败关闭（见 CON-008）。**

**无权限字段 MUST NOT 参与搜索（见 CON-011）。**

**追溯：** RAR §23、SRS V1.0 评审 P0-4、SRS V1.2 评审 P0-1

## NFR-004 可用性 【SHOULD】【RAR】

- 搜索入口 SHOULD 易于发现
- 结果 SHOULD 易于理解
- Refinement SHOULD 直观
- Preview SHOULD NOT 影响主业务操作

**追溯：** RAR §21

## NFR-005 响应式 【MUST】【RAR】

桌面端 MUST 使用左右分栏布局。

**窄屏 MUST 安全降级，不覆盖主业务区。**

**追溯：** RAR §21.5

## NFR-006 可扩展性 【MUST】【RAR】

新增 Business Resource 时，MUST 无需修改核心搜索逻辑即可纳入搜索范围。

**追溯：** RAR §13

## NFR-007 可维护性 【MUST】【RAR】

配置 MUST 由管理员维护，不需要开发介入。

**追溯：** RAR §13

## NFR-008 可观测性 【SHOULD】【SRS-DEC】

系统 SHOULD 提供：

- 搜索性能指标
- 搜索错误日志
- 配置变更审计日志
- 权限拒绝日志

**追溯：** SRS V1.0 评审 P2

---

# 7. 约束

## CON-001 不修改 Odoo 官方代码 【MUST】【TECH】

正式定制 MUST 放入独立模块。

## CON-002 不绕过权限 【MUST】【SRS-DEC】

所有搜索 MUST 以当前用户的有效权限执行。

MUST NOT 返回超出用户权限范围的数据。

**具体实现手段（ORM / RPC / 服务端方法）不在 SRS 约束范围。**

**追溯：** SRS V1.1 评审补充 1

## CON-003 不依赖外部搜索引擎 【MUST】【RAR】

V1 MUST NOT 引入 Elasticsearch / OpenSearch / 向量检索。

## CON-004 不做 L4 Business Answer 【MUST】【RAR】

聚合、余额、状态回答 MUST NOT 进入 V1。

## CON-005 不做完整自然语言解析 【MUST】【SRS-DEC】

V1 MUST 仅支持 FR-L3-001 定义的有限语法。

**追溯：** RAR §27 Q11（Open）、SRS V1.3 评审 P0-1

## CON-006 不覆盖 Chatter / Attachment 【MUST】【SRS-DEC】

V1 MUST NOT 搜索 Chatter 消息和附件内容。

**追溯：** RAR §27 Q10（Open）、SRS V1.3 评审 P0-1

## CON-007 不修改原业务模型 【MUST】【TECH】

Global Search MUST NOT 改变原模型的数据结构。

## CON-008 安全失败关闭 【MUST】【SRS-DEC】

权限相关异常 MUST 失败关闭，MUST NOT 返回未经权限确认的数据。

**"失败安全"原则 MUST NOT 应用于权限相关异常。**

**权限相关异常包括：**

- 主记录权限校验失败
- 权限判断字段读取失败
- Record Rule 校验失败

**追溯：** SRS V1.2 评审 P0-4

## CON-009 Preview 只读 【MUST】【SRS-DEC】

Preview MUST 为只读，MUST NOT 允许编辑、保存、执行业务按钮。

**追溯：** RAR §27 Q9（Open）、SRS V1.3 评审 P0-1

## CON-010 配置变更立即生效 【MUST】【SRS-DEC】

配置发布后 MUST 立即生效，无需重启。

**详见 BR-014。**

## CON-011 无权限字段不参与搜索 【MUST】【SRS-DEC】

用户无权访问的字段 MUST NOT 参与：

- 搜索匹配
- 排序
- 相关性计算
- 命中高亮
- Query Understanding
- 分类计数

**不得因为该字段命中而返回记录。**

**这条约束与 FR-PM-005 配套。**

**追溯：** SRS V1.2 评审 P0-1

---

# 8. 验收标准

## AC-001 标识符搜索 【MUST】

**Given** 用户输入 `MSCU1234567`
**When** 系统执行搜索
**Then** 返回与该柜相关的业务记录，高相关记录优先展示

## AC-002 部分匹配 【MUST】

**Given** Identifier 字段配置为"前缀匹配"或"包含匹配"
**And** 用户输入 `MSCU123`
**When** 系统执行搜索
**Then** 返回包含 `MSCU1234567` 的记录

## AC-003 精确匹配 【MUST】

**Given** Identifier 字段配置为"精确匹配"
**When** 用户输入 `MSCU123`
**Then** MUST NOT 返回 `MSCU1234567`

## AC-004 实体搜索 【MUST】

**Given** 用户输入 `A客户`
**When** 系统执行搜索
**Then** 返回客户及其相关业务记录

## AC-005 实体歧义 【MUST】

**Given** `ABC` 同时匹配多个客户，最高分与次高分分差 < 30
**When** 用户输入 `ABC`
**Then** 系统 MUST 展示候选实体列表，由用户选择

## AC-006 实体唯一命中 【MUST】

**Given** `ABC` 匹配多个客户，最高分与次高分分差 ≥ 30
**When** 用户输入 `ABC`
**Then** 系统使用最高分实体，并在 Query Understanding 中显示可修改

## AC-007 多条件组合（半结构化） 【MUST】

**Given** 用户输入 `A客户 今年 6月 未完成 出库`
**When** 系统执行搜索
**Then** 返回满足所有条件的出库记录

## AC-008 中文连续文本（SHOULD） 【SHOULD】

**Given** 用户输入 `A客户今年6月没完成的出库单`
**When** 系统执行搜索
**Then** 系统 SHOULD 识别为 `A客户` + `2026-06` + `未完成` + `出库`，并在 Query Understanding 中显示

**如果系统无法识别，MUST 将未识别部分作为 Free Text，MUST NOT 返回错误结果。**

## AC-009 解析失败 【MUST】

**Given** 用户输入 `A客户 6月 未知状态`
**When** 系统执行搜索
**Then** 已识别条件（A客户、6月）生效，"未知状态"作为 Free Text，MUST NOT 返回宽泛结果

## AC-010 二次筛选 【MUST】

**Given** 用户搜索 `A客户`
**When** 用户点击"出库"Tab 并选择"2026年6月"
**Then** 结果收窄为 A客户 2026年6月的出库记录，Raw Query 保持为 `A客户`

## AC-011 两条路径等价 【MUST】

**Given** 路径 A：输入 `A客户 今年 6月 未完成 出库`
**And** 路径 B：输入 `A客户` → 出库 → 2026年6月 → 未完成
**When** 两条路径都执行
**Then** 产生相同的 Effective Conditions 和 Filtered Result Set

## AC-012 Query 与 Refinement 冲突 【MUST】

**Given** Raw Query 为 `A客户 出库`
**When** 用户在 Refinement 中选择"入库"
**Then** Refinement 优先，结果显示入库记录，Query Understanding 显示冲突已消解

## AC-013 结果预览 【MUST】

**Given** 用户在搜索结果中单击某条记录
**When** 系统加载 Preview
**Then** 右侧显示该记录的 Form View，搜索页不离开

## AC-014 Preview 只读 【MUST】

**Given** Preview 显示某条记录
**When** 用户尝试编辑
**Then** MUST NOT 允许编辑、保存或执行业务按钮

## AC-015 打开完整记录 【MUST】

**Given** 用户双击搜索结果
**When** 系统打开记录
**Then** 在新浏览器 Tab 中打开标准 Form View，原搜索页状态保持

## AC-016 权限继承 【MUST】

**Given** 两个具有不同 Record Rule 的用户搜索相同关键词
**When** 系统执行搜索
**Then** 各自只能看到本人有权访问的记录

## AC-017 关联记录无权 【MUST】

**Given** 用户能访问主记录但不能访问关联记录
**When** 系统执行关联扩展
**Then** 关联记录跳过，主记录正常返回，分类计数不泄露关联记录数量

## AC-018 字段无权 【MUST】

**Given** 用户无权访问 Snapshot 配置中的某字段
**When** 系统展示 Snapshot
**Then** 该字段省略，其余字段继续展示

## AC-019 搜索字段无权 【MUST】

**Given** 用户无权访问某 Searchable Field
**When** 用户输入可能命中该字段的关键词
**Then** 该字段 MUST NOT 参与搜索、排序、计数、Query Understanding，MUST NOT 因该字段命中而返回记录

## AC-020 配置驱动 【MUST】

**Given** 管理员新增一个 Business Resource 并配置 Searchable Fields 和 Snapshot
**When** 配置发布
**Then** 该资源立即生效，无需重启

## AC-021 无结果 【MUST】

**Given** 用户输入无匹配的关键词
**When** 系统执行搜索
**Then** 明确显示 "No results found."

## AC-022 部分成功 【MUST】

**Given** 某个模型搜索异常，其他模型成功
**When** 系统执行搜索
**Then** 返回成功模型的结果，提示"部分模型搜索异常"

## AC-023 跨资源日期筛选 【MUST】

**Given** 用户搜索 `A客户` 并筛选 `2026年6月`
**When** 系统执行搜索
**Then** 各 Business Resource 按其默认 Business Date 过滤，合并结果并标注每条记录的 Business Date

## AC-024 多公司 【MUST】

**Given** 当前公司上下文为公司 A
**When** 用户搜索实体
**Then** 结果仅包含公司 A 上下文可访问的记录

## AC-025 复合资源 【MUST】

**Given** "订单"配置为复合资源（sale.order + purchase.order）
**When** 用户搜索"订单"
**Then** 返回两个模型的记录，按 BR-003 配置的合并规则展示，按 BR-003.1 默认排序

## AC-026 配置校验失败 【MUST】

**Given** 管理员配置的字段不属于配置的模型
**When** 管理员保存配置
**Then** 保存被阻止并提示错误

## AC-027 配置权限 【MUST】

**Given** 配置管理员对某字段无读取权限
**When** 管理员尝试配置该字段
**Then** 配置被阻止并提示

## AC-028 空日期 【MUST】

**Given** 某记录的 Business Date 字段为空
**When** 用户按日期筛选
**Then** 该记录默认不出现在结果中

## AC-029 周起始日 【MUST】

**Given** 用户语言设置为周起始日为周日
**When** 用户搜索 `本周`
**Then** 范围按周日到周六计算

## AC-030 时区 【MUST】

**Given** 用户时区为 UTC+8
**When** 用户搜索 `今天`
**Then** 范围按 UTC+8 的今天计算

## AC-031 年份推断 【MUST】

**Given** 当前用户时区为 2026 年，用户输入 `6月`
**When** 系统解析时间
**Then** 解释为 2026-06，在 Query Understanding 中显示完整日期范围

## AC-032 配置草稿不生效 【MUST】

**Given** 管理员保存配置草稿
**When** 用户执行搜索
**Then** 草稿配置不生效

## AC-033 配置发布立即生效 【MUST】

**Given** 管理员发布配置
**When** 用户执行搜索
**Then** 新配置立即生效，无需重启

## AC-034 配置回滚 【MUST】

**Given** 管理员回滚配置到之前版本
**When** 用户执行搜索
**Then** 回滚后的配置立即生效

## AC-035 计数去重 【MUST】

**Given** 同一记录通过多个字段命中
**When** 系统计数
**Then** 该记录只计一次

## AC-036 无权记录计数不泄露 【MUST】

**Given** 用户无权访问某记录
**When** 系统执行搜索并计数
**Then** 该记录不出现在结果中，也不计入任何计数

## AC-037 Free Text 匹配 【MUST】

**Given** 用户输入不匹配任何 Identifier、Entity、Time、Resource、State、Location
**When** 系统执行搜索
**Then** 按 FR-L3-005 的 Free Text 规则匹配配置的 Text 字段

## AC-038 复合资源计数 【MUST】

**Given** 复合资源"订单"包含 sale.order 和 purchase.order
**When** 用户搜索"订单"
**Then** 各模型记录分别计数，汇总到复合资源

## AC-039 错误分类 【MUST】

**Given** 主记录权限校验失败
**When** 系统执行搜索
**Then** MUST NOT 返回部分结果，MUST 失败关闭

## AC-040 Business Resource Tab 显示 【MUST】

**Given** 用户搜索 `A客户`，结果中有订单、出库、发票，但没有入库
**When** 结果页渲染
**Then** Tab 显示 `[全部] [订单] [出库] [发票]`，MUST NOT 显示 `[入库]`

## AC-041 Location 匹配 【MUST】

**Given** Location 字段配置为"Rotterdam"
**When** 用户输入 `Rotterdam`
**Then** 系统匹配配置的 Location 字段并返回相关记录

## AC-042 复合资源默认排序 【MUST】

**Given** 复合资源"订单"包含 sale.order 和 purchase.order
**When** 用户搜索"订单"
**Then** 结果按 BR-003.1 默认排序：相关性降序 → Business Date 降序 → Technical Model 优先级 → Record ID 升序

## AC-043 空 Business Date 排序 【MUST】

**Given** 复合资源中某记录 Business Date 为空
**When** 系统排序
**Then** 该记录排在非空记录之后

## AC-044 数据新鲜度 【MUST】

**Given** 用户提交一条业务记录
**When** 系统执行搜索
**Then** 该记录在 Technical Verification 确定的最终上限内可见（初始目标为 5 秒）

## AC-045 Vocabulary 配置生效 【MUST】

**Given** 管理员为某 Business Resource 配置了别名
**When** 用户使用别名搜索
**Then** 系统匹配到该 Business Resource

---

# 9. 冻结决策与开发前问题

以下 P0 决策已在 SRS V1.4 冻结前收口；其余 P1 问题仍需在进入实现前确认。

## P0：已收口

| # | 问题 | 影响 | 负责人 | 截止日期 | RAR 对应 |
|---|---|---|---|---|---|
| Q1 | 配置版本保留数量默认值 | 10 个版本 | 已确认 | 2026-10-01 | RAR 无 |
| Q2 | 审计日志保留周期 | 由 `audit_log` 模块负责，Global Search 不定义 | 已确认 | 2026-10-01 | RAR 无 |
| Q3 | 性能测试环境硬件规格 | 以实际性能验证环境为准，并在 Technical Verification 报告中记录 | 已确认 | 2026-10-01 | RAR 无 |
| Q4 | 数据新鲜度最终上限 | 初始目标 5 秒，最终上限由性能 Spike / Technical Verification 确定 | 已确认 | 2026-10-01 | RAR 无 |

## P1：开发前解决

| # | 问题 | 影响 | 负责人 | 截止日期 | RAR 对应 |
|---|---|---|---|---|---|
| Q5 | 实体简称匹配是否支持拼音？ | FR-L2-002 | 待定 | 待定 | RAR Q5 |
| Q6 | 日期口径切换是否进入 V1？ | FR-RF-006 | 待定 | 待定 | RAR Q4 |
| Q7 | 配置是否按公司隔离？ | CFG-008 | 待定 | 待定 | RAR 无 |
| Q8 | Preview 是否需要保留未保存状态？ | FR-SW-007 | 待定 | 待定 | RAR Q9 |

**RAR 中已解决但未在 SRS 体现的 Open Decision：**

| RAR Q# | 问题 | SRS 状态 |
|---|---|---|
| RAR Q1 | "所有订单"业务范围 | 由 Business Resource Vocabulary 配置解决（BR-001） |
| RAR Q2 | 日期对应业务日期 | 由 BR-004 Business Date 解决 |
| RAR Q3 | 日期二次筛选是否统一使用 Business Date | 由 BR-009.6 解决 |
| RAR Q6 | 单独搜索实体时关系扩展程度 | 由 BR-012 Relation Path 解决 |
| RAR Q7 | Result Refinement V1 范围 | 由 FR-RF-001 ~ FR-RF-009 解决 |
| RAR Q8 | 是否展示 Query Interpretation | 由 FR-QU-001（SRS-DEC）解决 |
| RAR Q10 | 是否覆盖 Chatter / Attachment | 由 CON-006（SRS-DEC）解决 |
| RAR Q11 | 自然语言程度 | 由 FR-L3-001（SRS-DEC）解决 |
| RAR Q12 | 跨资源 Business Date 合并规则 | 由 BR-009.6（SRS-DEC）解决 |

---

# 10. 后续技术研究问题

SRS 冻结后，进入技术研究阶段。至少需要研究：

1. Identifier Search 实现方式
2. Entity Resolution
3. Related Record Discovery
4. Conditional Search
5. Result Refinement
6. Query 与 Refinement 条件统一表达
7. 多业务资源统一检索
8. Time Expression Resolution
9. 中文连续文本词法切分
10. Business Date Semantics
11. Business Resource Vocabulary
12. State / Condition Mapping
13. Search Ranking
14. 具体评分公式与 Field Weight
15. PostgreSQL 搜索能力
16. 搜索性能验证（Spike）
17. 权限与 Record Rule
18. Multi-company
19. Search Index 与业务数据一致性
20. Search Workspace 性能
21. Odoo Form Preview 可行性
22. Refinement 前端控件实现
23. 日期范围实现方式
24. Free Text 具体检索方式

**特别提醒：** 在进入 TDD / Implementation 前，MUST 完成最小性能 Spike，验证"不依赖外部搜索引擎"与"跨大量模型、字段、关系执行搜索"的可行性。

---

# 11. 附录

## 11.1 RAR 追溯矩阵

**RAR 原文仓库路径：** `docs/requirement/RAR_global_search.md`

| RAR 章节 | SRS 需求 | 来源类型 | 验证方式 |
|---|---|---|---|
| §6 Identifier | FR-L1-001 ~ FR-L1-003 | RAR | AC-001 ~ AC-003 |
| §7 Entity | FR-L2-001 ~ FR-L2-004 | RAR | AC-004 ~ AC-006 |
| §8 Conditional | FR-L3-001 ~ FR-L3-005 | RAR + SRS-DEC | AC-007 ~ AC-009 |
| §12 语义单元 | FR-L3-001 | RAR | AC-007、AC-008 |
| §13 Business Resource | BR-001 ~ BR-003、CFG-001 | RAR + SRS-DEC | AC-020、AC-025 |
| §14 Result Refinement | FR-RF-001 ~ FR-RF-009、BR-006 ~ BR-008 | RAR | AC-010 ~ AC-012 |
| §15 日期筛选 | FR-RF-003 ~ FR-RF-006、BR-009 | RAR + SRS-DEC | AC-023、AC-028 ~ AC-031 |
| §16 其他筛选 | FR-RF-002、FR-RF-005 | RAR + SRS-DEC | AC-010、AC-040 |
| §17 Query 可见性 | FR-QU-001 ~ FR-QU-002 | SRS-DEC | AC-012 |
| §18 状态语义 | FR-L3-003、BR-005 | RAR | AC-009 |
| §19 关系发现 | FR-L2-004、BR-012 | RAR + SRS-DEC | AC-017 |
| §20 Search vs Answer | CON-004 | RAR | — |
| §21 Search Workspace | FR-SW-001 ~ FR-SW-007 | RAR + SRS-DEC | AC-013 ~ AC-015 |
| §22 结果摘要 | FR-SW-006、BR-011、BR-013 | RAR + SRS-DEC | AC-013、AC-035 ~ AC-036 |
| §23 权限 | FR-PM-001 ~ FR-PM-008 | RAR + SRS-DEC | AC-016 ~ AC-019、AC-024 |
| §24 V1 范围 | §1.2 | SRS-DEC | — |
| §25 排除能力 | CON-004 ~ CON-009 | RAR + SRS-DEC | — |
| §26 不应提前冻结 | §10 | RAR | — |
| §27 Open Decisions | §9 | RAR | — |

## 11.2 评审追溯矩阵

| 评审项 | SRS 落点 | 处理结果 |
|---|---|---|
| V1.0 P0-1 自然语言矛盾 | FR-L3-001、FR-L3-002、CON-005 | 已处理 |
| V1.0 P0-2 查询语义模型 | BR-006、BR-007、BR-008、BR-010、BR-011 | 已处理 |
| V1.0 P0-3 Business Resource 配置 | BR-002、BR-003、BR-012、CFG-001 | 已处理 |
| V1.0 P0-4 权限与异常 | FR-PM-001 ~ FR-PM-008、FR-ER-002、FR-ER-003、CON-008 | 已处理 |
| V1.0 P0-5 日期语义 | BR-009、FR-L3-004、FR-RF-004 | 已处理 |
| V1.0 P0-6 性能 | NFR-001、§10 特别提醒 | 已处理 |
| V1.0 P0-7 RAR 追溯 | §11.1、§11.2 | 已处理 |
| V1.0 P1-8 标识符匹配 | FR-L1-002、CFG-002 | 已处理 |
| V1.0 P1-9 实体歧义 | FR-L2-003 | 已处理 |
| V1.0 P1-10 配置生命周期 | BR-014、BR-015、CFG-007 | 已处理 |
| V1.0 P1-11 Snapshot/计数/排名/分页 | BR-011、BR-013、NFR-001 | 已处理 |
| V1.0 P1-12 Preview 编辑能力 | FR-SW-007、CON-009 | 已处理 |
| V1.1 P0-1 §9 冲突 | §9 | 已处理 |
| V1.1 P0-2 配置生命周期矛盾 | BR-014 | 已处理 |
| V1.1 P0-3 复合资源合并 | BR-003、BR-003.1 | 已处理 |
| V1.1 P0-4 Free Text 或无结果 | FR-L2-003、FR-L3-005 | 已处理 |
| V1.1 P0-5 年份推断 | FR-L3-004 | 已处理 |
| V1.1 P0-6 性能基线 | NFR-001 | 已处理 |
| V1.1 P1-7 交叉引用 | 全文使用需求编号引用 | 已处理 |
| V1.1 P1-8 Natural Language Query | BR-008 | 已处理 |
| V1.1 P1-9 Free Text 定义 | FR-L3-005 | 已处理 |
| V1.1 P1-10 Result Identity 和计数 | BR-011、BR-013 | 已处理 |
| V1.1 P1-11 权限异常与部分成功 | FR-ER-003 | 已处理 |
| V1.1 P1-12 AC-002 冲突 | AC-002、AC-003 | 已处理 |
| V1.1 P1-13 空格分隔矛盾 | FR-L3-001 | 已处理 |
| V1.1 补充 1 CON-002 措辞 | CON-002 | 已处理 |
| V1.1 补充 2 FR-QU-001 优先级 | FR-QU-001 | 已处理 |
| V1.2 P0-1 无权限字段泄露 | FR-PM-005、CON-011、AC-019 | 已处理 |
| V1.2 P0-2 Tab 规则矛盾 | FR-RF-002、FR-PM-007、AC-040 | 已处理 |
| V1.2 P0-3 复合资源排序 | BR-003.1、AC-042、AC-043 | 已处理 |
| V1.2 P0-4 语法示例超范围 | FR-L3-001、AC-007、AC-008 | 已处理 |
| V1.2 P1-5 Location 配置 | CFG-002、AC-041 | 已处理 |
| V1.2 P1-6 实体评分配置 | CFG-010 | 已处理 |
| V1.2 P1-7 字段读取异常 | FR-ER-003 | 已处理 |
| V1.2 P1-8 计数集合定义 | BR-013 | 已处理 |
| V1.2 P1-9 日期范围 | BR-009.3 | 已处理 |
| V1.2 P1-10 性能基线 | NFR-001 | 已处理 |
| V1.2 P1-11 版本/日志默认值 | BR-014 | 已处理 |
| V1.2 文档一致性 12 | 全文修正引用 | 已处理 |
| V1.2 文档一致性 13 | §11.1 RAR 路径 | 已处理 |
| V1.3 P0-1 MUST 超范围 | 全文增加来源分类 | 已处理 |
| V1.3 P0-2 P0 待确认项 | §9 | 已处理 |
| V1.3 P0-3 提前冻结评分规则 | FR-L1-002、FR-L2-003、FR-L3-005、CFG-010 | 已处理 |
| V1.3 P1-4 中文连续文本等级 | FR-L3-001、AC-008 | 已处理 |
| V1.3 P1-5 Free Text 实现约束 | FR-L3-005 | 已处理 |
| V1.3 P1-6 配置模型不完整 | BR-016、BR-017、CFG-012、CFG-013 | 已处理 |
| V1.3 P1-7 配置管理员规则 | FR-PM-006、CFG-005 | 已处理 |
| V1.3 P1-8 复合资源排序冲突 | BR-003.1、BR-015 | 已处理 |
| V1.3 P1-9 性能基线模糊 | NFR-001 | 已处理 |
| V1.3 P1-10 数据新鲜度 | NFR-002、AC-044 | 已处理 |
| V1.3 文档一致性 11 | 全文修正引用 | 已处理 |
| V1.3 文档一致性 12 | §9 增加 RAR 对应列 | 已处理 |
| V1.3 文档一致性 13 | §11.1 增加来源类型列 | 已处理 |

## 11.3 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V1.0 | 2026-10-01 | DRAFT | 基于 RAR V0.2 收口版 |
| V1.1 | 2026-10-01 | DRAFT | 闭合 V1.0 评审 P0×7、P1×5、P2 |
| V1.2 | 2026-10-01 | DRAFT | 闭合 V1.1 评审 P0×6、P1×7、补充 2、其他建议 |
| V1.3 | 2026-10-01 | DRAFT | 闭合 V1.2 评审 P0×4、P1×7、文档一致性×2 |
| V1.4 | 2026-10-01 | **FROZEN** | 闭合 V1.3 评审 P0×3、P1×7、文档一致性×3；收口配置保留、audit_log 职责、性能验证环境和数据新鲜度决策 |

---

# 12. 当前状态

**SRS V1.4：FROZEN**

本版本用于：

- 需求基线
- 技术可行性评估输入
- DDD / TDD 设计输入

本版本：

> **不是技术设计。**

> **不授权绕过 TDD / Coding Contract 直接编码。**

**下一阶段：**

1. Technical Research / Spike
2. 最小性能 Spike（进入 TDD / Implementation 前 MUST 完成）
3. DDD（如适用）
4. TDD
5. Coding Contract
6. Implementation