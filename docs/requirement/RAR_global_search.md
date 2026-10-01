# Odoo Global Search 需求分析报告（RAR）V0.2

> **文档性质：Requirement Analysis Report / 需求分析报告**
> **状态：ANALYSIS COMPLETE — FROZEN — NOT SRS — NOT AUTHORIZED FOR DEVELOPMENT**
> **版本：V0.2**
> **适用平台背景：Odoo 18**
> **目的：分析用户跨业务对象查找信息的真实需求，形成后续 SRS 的需求边界输入。**
> **仓库路径：`docs/requirement/RAR_global_search.md`**
>
> 本报告不定义技术实现，不构成软件需求规格说明书，不授权开发。
> PostgreSQL、Elasticsearch/OpenSearch、LLM、全文检索、索引结构、ORM/SQL、前端组件等均不在本阶段作技术选型。

---

# 1. 分析背景

## 1.1 问题来源

Odoo 的业务信息天然分布于不同应用、菜单、模型和单据中。

用户查找业务记录时，通常需要先知道：

* 应该进入哪个应用；
* 应该进入哪个菜单；
* 目标记录属于什么业务对象；
* 应该搜索哪个字段；
* 是否需要进入关联单据继续查找。

但真实业务用户的思考方式通常并非：

> "我要进入某个 Odoo Model，然后在某个字段上建立 Domain。"

而是：

> "我要找 MSCU1234567 这个柜。"

> "我要找 A客户的业务。"

> "我要看 A客户今年 6 月的所有订单。"

> "我要找未完成的入库。"

用户掌握的是**业务线索**，而不是系统的数据模型和导航结构。

因此提出 Odoo Global Search 需求，希望研究是否能够提供一个统一入口，让用户通过自己掌握的业务语言和业务线索发现相关业务记录。

---

# 2. RAR 分析目标

本报告重点回答以下问题：

1. 用户实际会使用什么信息进行搜索；
2. 用户输入的是简单关键词，还是业务线索组合；
3. 用户希望获得单条记录、关联记录、条件化记录集，还是业务答案；
4. 哪些搜索行为可以归属于统一的 Global Search / Discovery 产品；
5. 用户首次搜索后，是否需要继续对结果进行二次筛选；
6. 自然语言条件与结果页筛选条件之间是什么关系；
7. 哪些行为实际上已经进入 Business Answer 范畴；
8. 用户认知中的"客户、订单、入库、出库、柜子"等业务对象，与 Odoo Technical Model 之间存在什么差异；
9. Global Search 的候选产品形态是什么；
10. 哪些需求可以考虑进入后续 V1 SRS；
11. 哪些问题仍需业务确认或后续技术研究。

---

# 3. 本阶段不回答的问题

本 RAR 不决定：

* 使用 PostgreSQL 还是 Elasticsearch/OpenSearch；
* 是否采用 PostgreSQL Full Text Search；
* 是否使用 `pg_trgm`；
* 是否使用向量检索；
* 是否使用 LLM；
* 自然语言解析采用何种算法；
* 搜索索引如何建立；
* 搜索结果如何计算具体 Score；
* Odoo Model、技术表、字段及数据结构；
* ORM 与 SQL 的实现选择；
* 前端采用何种 OWL Component；
* Form Preview 的具体技术实现；
* 搜索索引同步机制；
* 性能优化方案。

上述内容只有在需求边界明确后，才能进入后续技术研究、Spike、DDD/TDD。

---

# 4. 当前搜索方式的核心问题

## 4.1 用户必须知道"东西在哪里"

传统 Odoo 搜索通常以当前业务对象为范围。

用户如果需要查找柜号、客户、订单、入库、运输、发票等跨领域信息，必须先知道目标业务属于哪个菜单。

这增加了系统学习成本。

---

## 4.2 一个业务线索可能横跨多个业务对象

例如：

`MSCU1234567`

可能同时出现在：

* 进口货代业务；
* 报关业务；
* 陆运业务；
* 入库业务；
* 出库业务；
* 其他关联记录。

用户实际想知道的是：

> "这个柜相关的业务在哪里？"

而不是：

> "在哪一个 Model 的哪个字段里存在 MSCU1234567？"

---

## 4.3 用户经常只掌握不完整信息

例如：

`A客户`

可能只是客户简称，而不是客户完整名称。

用户仍然期望系统能够找到正确客户，并进一步发现与该客户有关的业务记录。

---

## 4.4 用户输入可能包含多个业务条件

例如：

`A客户 6月`

包含：

* 客户；
* 时间。

而：

`A客户今年6月没完成的出库单`

同时包含：

* 客户；
* 时间；
* 状态；
* 业务对象类型。

因此用户输入并不总是一个"关键词"，而可能是一组**业务线索的自然组合**。

---

## 4.5 用户第一次输入不一定包含全部条件

真实搜索行为通常具有探索性。

用户可能首先输入：

`A客户`

看到结果后才进一步决定：

> "只看出库。"

然后：

> "只看 2026 年 6 月。"

最后：

> "只看未完成。"

因此 Global Search 不应要求用户在第一次输入时就准确表达全部业务条件。

搜索结果页需要具备进一步收窄结果范围的能力。

本报告将其称为：

> **Result Refinement / 搜索结果二次筛选**

---

# 5. Search Corpus

为避免从技术能力反推需求，本报告从"用户脑子里知道什么"出发，建立 40 条真实业务搜索场景。

这些场景是**需求分析语料库（Search Corpus）**，用于发现需求边界。

它们不是 V1 Acceptance Criteria，也不代表 40 条场景均已批准进入开发范围。

---

# 6. Identifier 类场景

| #  | 用户输入             | Intent               | Entity              | Expected Output    |
| -- | ---------------- | -------------------- | ------------------- | ------------------ |
| 1  | `MSCU1234567`    | FIND_RELATED_RECORDS | container           | 与该柜相关的运输、报关、出入库等记录 |
| 2  | `ABC123`         | FIND_RECORD          | pickup_code         | 对应运输业务             |
| 3  | `SO/2026/00391`  | FIND_RECORD          | sale_order          | 销售单及关联业务           |
| 4  | `PO/2026/00188`  | FIND_RECORD          | purchase_order      | 采购单及关联业务           |
| 5  | `WH/IN/00088`    | FIND_RECORD          | inbound             | 入库单                |
| 6  | `WH/OUT/00123`   | FIND_RECORD          | outbound            | 出库单                |
| 7  | `WH/INT/00045`   | FIND_RECORD          | internal_transfer   | 移库单                |
| 8  | `INV/2026/00712` | FIND_RECORD          | invoice             | 发票及付款状态            |
| 9  | `CUS/2026/00233` | FIND_RECORD          | customs_declaration | 报关单                |
| 10 | `SEAL998877`     | FIND_RELATED_RECORDS | seal                | 关联柜号与业务单据          |

### 分析发现

此类场景共同特征不是"一定找到一条记录"，而是：

> **用户通过高区分度业务标识符定位业务信息。**

因此本报告将其定义为：

**L1 — Identifier-based Discovery**

一个 Identifier 可能对应单一业务记录，也可能成为发现多个关联业务记录的入口。

---

# 7. Entity 类场景

| #  | 用户输入            | Intent               | Entity    | Expected Output |
| -- | --------------- | -------------------- | --------- | --------------- |
| 11 | `A客户`           | FIND_RELATED_RECORDS | customer  | 客户及相关订单、出入库、发票等 |
| 12 | `B供应商`          | FIND_RELATED_RECORDS | supplier  | 供应商及采购、入库、应付等   |
| 13 | `Vitamin D`     | FIND_RELATED_RECORDS | product   | 产品及库存、订单、采购、批次等 |
| 14 | `SKU-00392`     | FIND_RECORD          | product   | 产品记录            |
| 15 | `张三`            | FIND_RELATED_RECORDS | driver    | 司机及运输任务         |
| 16 | `粤B12345`       | FIND_RELATED_RECORDS | vehicle   | 车辆及运输记录         |
| 17 | `Rotterdam DC`  | FIND_RELATED_RECORDS | warehouse | 仓库及库存、出入库等      |
| 18 | `Project Alpha` | FIND_RELATED_RECORDS | project   | 项目及任务、工时、业务记录   |

### 分析发现

此类场景与 Identifier Search 存在明显区别。

用户可能只知道：

* 客户简称；
* 产品名称；
* 人员名称；
* 仓库名称；
* 项目名称。

系统首先需要识别用户所指的业务实体，然后才能进一步发现关联业务。

本报告将其定义为：

**L2 — Entity Discovery**

其基本用户意图可以描述为：

> Entity Resolution → Related Business Discovery

---

# 8. Structured / Conditional Search 场景

| #  | 用户输入                  | Entity                       | Time       | Resource         | State / Condition | Expected Output |
| -- | --------------------- | ---------------------------- | ---------- | ---------------- | ----------------- | --------------- |
| 19 | `A客户 6月`              | customer                     | 6月         | 多资源              | —                 | 该客户该期间业务记录      |
| 20 | `A客户今年6月所有订单`         | customer                     | 今年6月       | 订单类资源            | —                 | 指定期间相关订单        |
| 21 | `A客户 未完成`             | customer                     | —          | 多资源              | incomplete        | 未完成业务           |
| 22 | `Vitamin D Rotterdam` | product + warehouse/location | —          | inventory        | —                 | 产品在相关仓库的业务      |
| 23 | `MSCU1234567 A客户`     | container + customer         | —          | 多资源              | —                 | 两个实体共同关联业务      |
| 24 | `上个月 出库`              | —                            | prev_month | outbound         | —                 | 上月出库记录          |
| 25 | `未完成 入库`              | —                            | —          | inbound          | incomplete        | 未完成入库记录         |
| 26 | `A客户 Vitamin D`       | customer + product           | —          | sales/outbound 等 | —                 | 客户与产品共同相关记录     |
| 27 | `A客户 Rotterdam`       | customer + location          | —          | 多资源              | —                 | 与客户和地点相关业务      |
| 28 | `张三 本周`               | driver                       | this_week  | transport        | —                 | 司机本周运输任务        |
| 29 | `A客户上个月没完成的出库单`       | customer                     | prev_month | outbound         | incomplete        | 满足条件的出库记录       |
| 34 | `B供应商 Vitamin D`      | supplier + product           | —          | purchase         | —                 | 相关采购记录          |
| 35 | `逾期 发票`               | —                            | —          | invoice          | overdue           | 逾期发票            |
| 36 | `待处理 入库`              | —                            | —          | inbound          | pending           | 待处理入库           |
| 37 | `异常 出库`               | —                            | —          | outbound         | abnormal          | 异常出库            |
| 38 | `待确认 订单`              | —                            | —          | order            | to_confirm        | 待确认订单           |
| 39 | `缺货 Vitamin D`        | product                      | —          | inventory        | out_of_stock      | 缺货相关记录          |
| 40 | `待对账 B供应商`            | supplier                     | —          | purchase/finance | pending_reconcile | 待对账记录           |

### 分析发现

这些查询虽然表达越来越接近自然语言，但最终信息需求仍然是：

> **找到一组符合业务条件的记录。**

因此统一定义为：

**L3 — Conditional Discovery**

其典型组成可以包括：

* Entity；
* Identifier；
* Time；
* Business Resource；
* State / Condition；
* Location；
* Free Text；
* 其他业务条件。

---

# 9. Business Answer 场景

以下 4 个场景与前述 Search / Discovery 存在本质区别。

| #  | 用户输入                 | Intent      | Measure / Attribute | Expected Output |
| -- | -------------------- | ----------- | ------------------- | --------------- |
| 30 | `Vitamin D 上个月入库了多少` | AGGREGATE   | inbound quantity    | 汇总数量 + 来源记录     |
| 31 | `A客户 欠款`             | GET_BALANCE | receivable amount   | 应收余额 + 相关发票     |
| 32 | `MSCU1234567 到哪了`    | GET_STATUS  | status/location/ETA | 当前业务状态          |
| 33 | `今年6月 出库总量`          | AGGREGATE   | outbound quantity   | 汇总结果            |

这些问题的主要目标不是：

> 找记录。

而是：

> **得到一个业务答案。**

因此定义为：

**L4 — Business Answer**

L4 可能涉及：

* 聚合；
* 余额计算；
* 状态推导；
* 指标口径；
* 业务事实组合；
* 数据来源解释。

这些能力不应因为用户同样通过搜索框输入，就自动被视为 Global Search 的组成部分。

---

# 10. 能力分层

根据当前 40 条 Search Corpus，可以形成以下需求分析分层：

| Level | 名称                         | 本质                | 当前场景数 |
| ----- | -------------------------- | ----------------- | ----: |
| L1    | Identifier-based Discovery | 根据业务标识符发现记录       |    10 |
| L2    | Entity Discovery           | 根据业务实体发现自身及关联记录   |     8 |
| L3    | Conditional Discovery      | 根据多个业务条件发现记录集     |    18 |
| L4    | Business Answer            | 对业务事实进行回答、计算或状态解释 |     4 |

**L3 包含原 Exception/Todo 类场景（#35–40），因为它们最终信息需求仍是 FILTER_RECORDS，State/Condition 是修饰条件而非独立 Intent。**

当前 Corpus 中：

* **L1–L3：36 / 40**
* **L4：4 / 40**

### 当前分析结论

基于现有样本，用户需求主体明显集中在：

> **Search / Discovery**

而不是：

> **Business Answer**

因此，本 RAR 建议后续 V1 SRS 优先考虑 L1–L3。

L4 暂作为后续 Business Answer 能力候选，不建议直接并入 Global Search V1。

该结论属于**范围建议**，尚需业务评审确认，不构成冻结范围。

---

# 11. Business Search Intent

## 11.1 Search Intent

当前分析认为 Search / Discovery 可以主要归纳为三个顶层 Intent：

### FIND_RECORD

用户希望找到一个明确业务记录。

例如：

`SO/2026/00391`

### FIND_RELATED_RECORDS

用户从一个 Identifier 或 Entity 出发，希望发现与其相关的其他业务记录。

例如：

`MSCU1234567`

`A客户`

### FILTER_RECORDS

用户提供多个业务条件，希望获得满足条件的记录集合。

例如：

`A客户今年6月没完成的出库单`

---

## 11.2 State / Exception 不是独立顶层 Intent

以下表达：

* 未完成；
* 逾期；
* 异常；
* 待处理；
* 待确认；
* 缺货；
* 待对账；

当前分析更倾向于将其理解为：

> **State / Business Condition**

而不是独立的 Search Intent。

例如：

`逾期 发票`

可分析为：

* Intent：FILTER_RECORDS
* Resource：Invoice
* State / Condition：Overdue

这样可以避免随着业务异常类型增加而不断扩大顶层 Intent 类型。

---

## 11.3 Answer Intent

Business Answer 当前发现三种明显类型：

* AGGREGATE
* GET_BALANCE
* GET_STATUS

这些 Intent 暂不建议进入 Global Search V1 核心范围。

---

# 12. 用户表达的业务语义组成

当前 Corpus 表明，用户输入可以包含以下不同语义单元：

```
User Expression
       │
       ├── Identifier
       ├── Entity
       ├── Time
       ├── Business Resource
       ├── State / Condition
       ├── Location
       └── Free Text
```

例如：

`A客户今年6月没完成的出库单`

可以从需求分析角度观察为：

* Entity：A客户
* Time：今年6月
* Resource：出库单
* State：未完成
* Intent：FILTER_RECORDS

本 RAR 只描述这种业务语义现象。

如何识别这些语义，不在本阶段决定。

---

# 13. Business Resource 核心发现

## 13.1 用户不理解 Odoo Model，也不应该被要求理解

用户认知中的业务对象通常是：

* 客户；
* 供应商；
* 产品；
* 柜子；
* 订单；
* 运输；
* 入库；
* 出库；
* 移库；
* 发票；
* 项目。

这些业务概念与 Odoo Technical Model 并不天然一一对应。

因此 Global Search 不应要求用户：

> 先选择 Model，再搜索字段。

---

## 13.2 用户语言中的一个业务资源可能对应多个系统对象

例如用户说：

> `订单`

其业务含义可能包括：

* 销售订单；
* 采购订单；
* 运输订单；
* 入库订单；
* 出库订单；
* 移库订单；
* 其他业务订单。

具体范围需要由业务确认。

因此不能在 RAR 阶段直接假设：

> "所有订单"等于某几个固定 Odoo Model。

---

## 13.3 Business Resource Vocabulary

当前分析发现，Global Search 需要建立一种业务语言与系统数据之间的语义对应关系。

概念上：

```
用户语言
   ↓
业务资源概念
   ↓
实际系统业务对象
```

例如：

```
"出库"
"出库单"
"出库业务"
      ↓
Outbound Business Resource
      ↓
实际 Odoo 业务实现
```

本报告将此称为：

**Business Resource Vocabulary / Business Resource Concept**

这是需求分析发现，不代表后续技术设计必须建立名为 `BusinessResource` 的技术模型或架构层。

---

## 13.4 Business Resource 可配置性

**Business Resource Vocabulary 必须支持管理员配置。**

原因：

* 不同企业对"订单""出库"等词汇的定义不同；
* 不同行业对同一业务对象的认知不同；
* 制造业的"生产工单"、服务业的"服务工单"、零售的"销售单"都可以通过配置纳入搜索范围。

**这意味着 Global Search 不是物流行业专用模块，而是可配置的业务搜索平台。**

物流/贸易只是它的第一个验证场景。

---

# 14. Result Refinement — 搜索结果二次筛选

## 14.1 需求发现

用户第一次搜索时不一定知道或输入全部搜索条件。

例如用户首先输入：

`A客户`

系统发现该客户及大量相关业务后，用户可能继续表达：

> "只看出库。"

> "只看 2026 年 6 月。"

> "只看未完成。"

因此搜索不应被理解为一次性的：

> Query → Result

而更接近持续收窄范围的过程：

> **Search → Discover → Refine → Result**

---

## 14.2 二次筛选与重新搜索不同

二次筛选不要求用户修改原始搜索表达。

例如原始 Query：

`A客户`

用户随后选择：

* Resource：出库；
* Date：2026-06-01 ～ 2026-06-30；
* State：未完成。

原始 Query 仍然是：

`A客户`

当前结果范围则成为：

```
Query:
    A客户

Result Refinement:
    Resource = 出库
    Date = 2026-06-01 ~ 2026-06-30
    State = 未完成
```

这样用户可以保留最初的搜索上下文，同时逐步缩小结果。

---

## 14.3 Natural Language Query 与 Result Refinement

当前分析认为，两种用户路径应该能够趋向相同的业务结果。

### 路径 A — 一次表达多个条件

用户输入：

`A客户今年6月没完成的出库单`

系统识别：

* Customer：A客户；
* Resource：出库；
* Date：2026 年 6 月；
* State：未完成。

### 路径 B — 简单搜索后逐步筛选

用户输入：

`A客户`

然后依次选择：

> 出库 → 2026 年 6 月 → 未完成

两条路径最终表达的是相同的信息需求。

因此形成一个重要需求分析原则：

> **Natural Language Query 与 Result Refinement 是进入同一业务搜索条件空间的两种不同方式。**

Global Search 不应把成功完全依赖于用户第一次输入完整自然语言，也不应要求用户只能通过筛选器构造复杂条件。

---

# 15. 日期二次筛选

## 15.1 日期是重点二次筛选维度

当前 Corpus 中已经频繁出现：

* 6月；
* 今年6月；
* 上个月；
* 本周；
* 去年；
* 自定义时间范围。

因此日期应作为 Result Refinement 中重点研究的筛选维度。

---

## 15.2 候选交互

可参考用户熟悉的通用搜索产品体验，在结果页提供日期范围筛选。

例如：

```
日期
────────────────
不限
今天
本周
本月
上个月
今年
去年
自定义日期范围
```

用户也可以选择：

> 2026-06-01 ～ 2026-06-30

本 RAR 只确认这种交互方向具有需求价值，不冻结具体选项、排列方式或控件形式。

---

## 15.3 日期筛选不应要求用户理解数据库字段

用户想表达的是：

> "看 2026 年 6 月的出库。"

而不是：

> "对 `xxx_date` 字段建立 2026-06-01 至 2026-06-30 的 Domain。"

因此日期筛选应该使用用户理解的**业务日期语义**。

---

## 15.4 不同 Business Resource 可能具有不同业务日期

例如：

* 入库；
* 出库；
* 运输；
* 发票；

其用户理解的"日期"可能并不对应相同技术字段。

候选业务原则是：

> 每类 Business Resource 应具有业务上可以理解的默认日期语义。

例如：

```
入库 → 入库业务日期
出库 → 出库业务日期
运输 → 运输业务日期
发票 → 发票日期
```

具体日期定义需要业务确认。

本 RAR 不决定具体字段。

---

## 15.5 跨资源日期筛选

例如：

`A客户`

随后筛选：

> 2026 年 6 月

结果可能同时包含：

* 订单；
* 入库；
* 出库；
* 运输；
* 发票。

此时用户期望的是：

> 每种业务资源按照其合理的业务日期语义过滤，再共同组成 2026 年 6 月的搜索结果。

这进一步证明搜索结果应该围绕 Business Resource 组织，而不是要求用户理解不同 Model 的日期字段。

---

# 16. 其他候选二次筛选维度

除日期外，当前 Search Corpus 已经明确暴露出以下筛选需求。

## 16.1 Business Resource

例如：

```
全部
订单
入库
出库
运输
发票
```

用户可以从跨资源结果切换到某一业务范围。

---

## 16.2 State / Business Condition

例如：

* 未完成；
* 已完成；
* 待处理；
* 异常；
* 逾期；
* 待确认；
* 待对账。

具体选项可能因 Business Resource 不同而变化。

---

## 16.3 其他筛选维度

Customer、Supplier、Product、Warehouse、Location 等是否应该作为显式 Result Refinement，需要根据实际使用场景进一步确认。

RAR V0.2 不冻结完整筛选器清单。

---

# 17. Query Understanding 可见性

随着 Natural Language Query 与 Result Refinement 形成统一条件空间，一个新的候选 UX 是：

> 将系统当前理解的搜索条件显式展示给用户。

例如输入：

`A客户今年6月没完成的出库单`

结果页可能展示：

```
客户：A客户欧洲有限公司 ×
资源：出库 ×
日期：2026年6月 ×
状态：未完成 ×
```

用户可以：

* 查看系统如何理解 Query；
* 删除某个条件；
* 修改日期；
* 切换业务资源；
* 调整状态；
* 保留其他搜索条件。

这可以降低自然语言解析错误带来的不透明性。

是否作为 V1 正式需求，需要后续业务确认。

---

# 18. 状态语义问题

用户可能使用：

* 未完成；
* 已完成；
* 待处理；
* 异常；
* 逾期；
* 待确认；
* 待对账；
* 缺货。

这些是**用户业务语言**。

不同业务资源可能具有完全不同的系统状态。

例如：

> "未完成"

在运输订单、入库单、出库单和销售订单中可能对应不同的系统状态集合。

因此后续需求需要解决：

> 用户业务状态语言如何映射到不同 Business Resource 的实际业务状态。

该问题同时影响：

* Natural Language Query；
* Result Refinement。

两者原则上应该采用一致的业务状态语义。

本 RAR 不定义具体映射。

---

# 19. 关系发现问题

`A客户`

并不仅意味着：

> 找到客户档案。

用户可能希望继续看到：

* 订单；
* 入库；
* 出库；
* 运输；
* 发票；
* 应收；
* 其他关联业务。

同样：

`MSCU1234567`

可能需要发现：

* 进口业务；
* 报关；
* 运输；
* 入库；
* 出库。

因此 Global Search 存在明确的：

> **Related Business Discovery**

需求。

但当前 RAR 不假设系统应该无限自动遍历所有数据关系。

哪些关系具有业务意义、哪些关系应该进入搜索结果，需要在后续 SRS 中进一步定义。

---

# 20. Search 与 Business Answer 的边界

这是本次需求分析的重要结论。

## Search / Discovery

回答：

> **"相关业务记录在哪里？"**

主要输出：

* 业务对象；
* 记录集合；
* 分类；
* 快照；
* 关联记录；
* 可继续打开的业务记录。

Result Refinement 属于 Search / Discovery 范围。

---

## Business Answer

回答：

> **"业务事实的答案是什么？"**

例如：

* 入库了多少；
* 欠多少钱；
* 柜子现在到哪了；
* 总量是多少。

Business Answer 可能涉及：

* 聚合口径；
* 财务口径；
* 当前状态定义；
* 多来源数据；
* 业务计算；
* 数据可信度和解释。

因此虽然 Search 和 Business Answer 可以未来共享统一入口，但当前需求分析认为：

> **它们不应因为拥有同一个输入框，就被视为同一个 V1 产品范围。**

---

# 21. Search Workspace 候选产品形态

随着 Result Refinement 的加入，当前候选核心交互路径调整为：

> **Search → Discover → Refine → Preview → Open**

这比单纯：

> Search → Result

更符合真实用户搜索过程。

---

## 21.1 Search

用户可以从非常简单的线索开始：

`MSCU1234567`

`A客户`

`Vitamin D`

也可以直接输入多个条件：

`A客户今年6月没完成的出库单`

---

## 21.2 Discover

系统发现可能相关的：

* Business Resource；
* Entity；
* Business Record。

结果按用户能够理解的业务类别组织，而不是按 Technical Model 组织。

---

## 21.3 Refine

用户在不丢失当前 Query 的情况下继续收窄结果。

重点候选维度：

* Business Resource；
* Date；
* State / Condition。

例如：

```
[A客户________________________________]

全部   订单   入库   出库   运输   发票

资源：出库 ×
日期：2026年6月 ×
状态：未完成 ×
```

---

## 21.4 Snapshot

每条结果提供简洁业务快照，帮助用户判断：

> "是不是我要找的记录？"

Snapshot 与实际 Form View 是两个不同概念。

---

## 21.5 Preview

桌面端候选形态：

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
│ ...                     │                               │
└─────────────────────────┴───────────────────────────────┘
```

单击左侧结果：

> 在右侧 Preview 当前记录。

切换结果：

> 保留 Query、筛选条件和结果上下文，仅切换 Preview。

---

## 21.6 Open

当前候选行为：

* 单击：Preview；
* 双击：正常 Form View 新标签页打开；
* Ctrl/Cmd + Click：可考虑遵循浏览器新标签页习惯。

这些仍属于候选 UX，需要后续确认。

---

# 22. 搜索结果不应仅是"散落记录"

对于：

`A客户`

如果系统只返回大量不同类型记录混排，用户仍可能难以理解。

因此 Search Workspace 可能需要提供业务资源分类及数量，例如：

```
A客户欧洲有限公司

全部            126
订单             56
入库             22
出库             29
运输             11
发票              8
```

用户选择：

> 出库

再选择：

> 2026 年 6 月

结果集继续收窄。

因此候选信息路径可以进一步描述为：

> **Summary → Refine → Result Set → Record → Preview → Open**

这里的 Summary 是搜索结果范围摘要，不属于 L4 Business Answer。

---

# 23. 权限原则

Global Search 是新的信息发现入口，但不应改变用户原有业务权限边界。

需求原则上应满足：

> 用户通过 Global Search 能发现的信息，不应超过其通过正常 Odoo 权限能够访问的信息。

需要考虑：

* Model Access Rights；
* Record Rules；
* Multi-company；
* 用户业务范围；
* 其他已有数据隔离规则。

具体如何实现属于后续技术阶段。

---

# 24. 候选 V1 范围

根据当前 Search Corpus，本 RAR 建议后续 V1 SRS 优先评估：

### L1 — Identifier-based Discovery

通过明确业务标识符发现记录及相关业务。

### L2 — Entity Discovery

通过客户、供应商、产品、司机、车辆、仓库、项目等业务实体发现相关业务。

### L3 — Conditional Discovery

通过 Entity、Identifier、Time、Resource、State / Condition、Location、Free Text 等组合条件发现记录。

### Result Refinement

允许用户在首次搜索结果基础上继续收窄结果。

当前重点候选维度：

* Business Resource；
* Date；
* State / Condition。

其中 Date 是当前明确的重要二次筛选场景。

### Search Workspace

形成统一：

> **Search → Discover → Refine → Preview → Open**

工作空间。

---

# 25. 当前建议排除出 V1 的能力

以下能力建议暂不进入 Global Search V1：

### L4 — Business Answer

包括：

* 聚合计算；
* 财务余额回答；
* 当前状态推导；
* KPI；
* 分析型问题回答。

典型例子：

`Vitamin D 上个月入库了多少`

`A客户欠款`

`MSCU1234567 到哪了`

`今年6月出库总量`

这些场景可以作为未来 Business Answer / Business Insight 能力继续分析。

---

# 26. 当前明确不应提前冻结的事项

RAR 阶段不应提前冻结：

* 精确匹配算法；
* 模糊匹配算法；
* Search Score 公式；
* Field Weight；
* 搜索索引；
* 全文搜索方案；
* 自然语言解析方案；
* AI/LLM；
* PostgreSQL / Elasticsearch / OpenSearch；
* Search Resource 技术模型；
* 搜索数据同步机制；
* Form Preview 技术架构；
* Result Refinement 的前端控件实现。

这些问题需要以后基于冻结后的 SRS 和代表性 Search Corpus 进行技术研究。

---

# 27. 主要未决需求问题

进入 SRS 前至少需要进一步确认以下问题。

## Q1. "所有订单"的业务范围是什么？

`A客户今年6月所有订单`

其中"订单"可能包括：

* 销售订单；
* 采购订单；
* 运输订单；
* 入库订单；
* 出库订单；
* 移库订单。

具体业务含义需要确认。

---

## Q2. 日期应该对应什么业务日期？

例如：

`6月出库`

可能指：

* 指令创建日期；
* 计划出库日期；
* 实际出库日期；
* 完成日期。

需要确认每类 Business Resource 的默认业务日期语义。

---

## Q3. 日期二次筛选是否统一使用 Business Date？

需要确认：

> 用户选择"2026年6月"时，是否默认按照每种 Business Resource 自己定义的 Business Date 进行过滤。

---

## Q4. 是否允许用户切换日期口径？

例如在"出库"范围中，用户是否需要主动选择：

* 指令日期；
* 计划日期；
* 实际出库日期；

还是普通搜索只提供一个默认业务日期。

---

## Q5. 简称匹配存在多个实体时怎么办？

例如：

`ABC`

同时匹配多个客户。

系统应该自动选择、展示候选还是同时搜索，需要确认。

---

## Q6. 单独搜索实体时，关系扩展到什么程度？

例如：

`A客户`

默认应该展示哪些相关业务？

是否只扩展明确认可的业务关系？

---

## Q7. Result Refinement 的 V1 范围是什么？

当前明确候选：

* Resource；
* Date；
* State / Condition。

Customer、Supplier、Product、Warehouse、Location 等是否也进入 V1，需要进一步确认。

---

## Q8. 是否展示当前 Query Interpretation？

例如：

```
客户：A客户欧洲有限公司 ×
资源：出库 ×
日期：2026年6月 ×
状态：未完成 ×
```

是否需要让用户查看、删除和修改系统理解出的条件，需要确认。

---

## Q9. Form Preview 是否允许编辑？

尚未确认：

* 只读；
* 可编辑；
* Save；
* 业务按钮；
* Chatter。

---

## Q10. 搜索是否覆盖 Chatter / Attachment？

当前 Corpus 主要针对结构化业务记录。

Chatter、Attachment 文件名、PDF 正文等是否属于搜索范围，尚未确认。

---

## Q11. 自然语言程度应该达到什么水平？

需要区分：

* 简单 Identifier；
* 业务关键词组合；
* 半结构化自然语言；
* 完全自然语言问题。

V1 应支持到什么程度尚未冻结。

---

## Q12. 跨资源 Business Date 合并规则？

当用户搜 `A客户` 并筛选 `2026年6月` 时，订单按订单日期、出库单按实际出库日期、发票按发票日期分别过滤。

这三种"6月"是同一个 6 月吗？合并后的结果是否符合用户预期？

---

# 28. 后续技术研究问题

只有在 SRS 边界明确后，才进入技术阶段。

届时至少需要研究：

1. Identifier Search；
2. Entity Resolution；
3. Related Record Discovery；
4. Conditional Search；
5. Result Refinement；
6. Query 与 Refinement 条件统一表达；
7. 多业务资源统一检索；
8. Time Expression Resolution；
9. Business Date Semantics；
10. Business Resource Vocabulary；
11. State / Condition Mapping；
12. Search Ranking；
13. PostgreSQL 搜索能力；
14. Elasticsearch/OpenSearch 的适用性；
15. 自然语言 Query Understanding；
16. 是否需要 LLM；
17. 权限与 Record Rule；
18. Multi-company；
19. Search Index 与业务数据一致性；
20. Search Workspace 性能；
21. Odoo Form Preview 可行性。

本 RAR 不对上述技术路线作结论。

---

# 29. 建议的后续流程

当前建议流程：

```
RAR V0.2 (FROZEN)
   ↓
SRS V1.0 起草
   ↓
SRS 评审迭代（V1.1 / V1.2 / V1.3 ...）
   ↓
SRS Freeze
   ↓
Technical Research / Spike
   ↓
DDD
   ↓
TDD
   ↓
Implementation
```

如果在 RAR/SRS 阶段发现某项技术可行性会直接决定需求能否成立，可在进入正式设计前安排针对性 Spike，但 Spike 不反向替代业务需求定义。

---

# 30. RAR V0.2 核心结论

**结论一：用户输入的核心不是传统"关键词"，而是业务线索。**

业务线索可能包含 Identifier、Entity、Time、Resource、State、Location 和 Free Text。

---

**结论二：Global Search 的主要需求是 Business Discovery。**

40 个场景中，目前有 36 个最终目标仍然是发现一个或一组业务记录。

---

**结论三：Search 与 Business Answer 应分开。**

聚合、余额、状态回答等能力虽然可以通过相同搜索框触发，但业务性质明显不同，不建议直接并入 Global Search V1。

---

**结论四：用户不应该理解 Odoo Technical Model。**

Global Search 应围绕用户能够理解的 Business Resource 组织搜索范围和结果。

---

**结论五：Business Resource Vocabulary 是重要需求发现。**

"订单""出库""客户""柜子"等用户语言需要与实际业务对象建立明确语义关系，但具体技术实现不在 RAR 阶段决定。

---

**结论六：首次搜索不是搜索过程的终点。**

用户经常先使用一个简单业务线索进行发现，再根据结果逐步增加：

* Resource；
* Date；
* State / Condition；

等条件。

因此 Result Refinement 是 Search Workspace 的重要候选核心能力。

---

**结论七：日期是当前最明确的二次筛选维度之一。**

日期筛选应使用用户能够理解的业务日期语义，而不应要求用户理解底层技术字段。

不同 Business Resource 可以存在不同业务日期含义。

---

**结论八：Natural Language Query 与 Result Refinement 应趋向同一业务条件空间。**

例如：

> `A客户今年6月没完成的出库单`

与：

> `A客户` → `出库` → `2026年6月` → `未完成`

应表达相同的信息需求。

这使 Global Search 不必把用户体验完全依赖于一次性自然语言理解。

---

**结论九：Search Workspace 候选路径调整为：**

> **Search → Discover → Refine → Preview → Open**

对于范围较大的搜索，还可以形成：

> **Summary → Refine → Result Set → Record → Preview → Open**

两条路径共享同一 Refinement 机制，区别在于 Discover 阶段是否先返回结构化 Summary。

---

**结论十：当前建议 V1 聚焦 L1–L3 + Result Refinement。**

即：

* Identifier-based Discovery；
* Entity Discovery；
* Conditional Discovery；
* 搜索结果二次筛选；
* Search Workspace。

L4 Business Answer 暂作为后续能力候选。

---

**结论十一：现在仍不应该选择搜索技术。**

只有 SRS 明确：

* 搜索语义；
* Business Resource；
* 日期语义；
* 状态语义；
* Relation Discovery；
* Result Refinement；
* 自然语言支持范围；

之后，才有足够依据比较 PostgreSQL、全文搜索、Elasticsearch/OpenSearch、规则解析和 LLM 等技术路线。

---

# 31. 附录 A：已进入 SRS 的分析结论

以下 RAR 结论已被 SRS V1.x 引用：

| RAR 结论 | SRS 落点 |
|---|---|
| 结论一（业务线索） | §1.3 术语、FR-L3-001 |
| 结论二（Business Discovery） | §1.2 范围、L1–L3 功能需求 |
| 结论三（Search vs Answer） | CON-004 |
| 结论四（用户语言优先） | §2.4 设计原则、BR-001 |
| 结论五（Business Resource Vocabulary） | BR-001、CFG-001 |
| 结论六（首次搜索非终点） | FR-RF-001 |
| 结论七（日期二次筛选） | FR-RF-003、BR-009 |
| 结论八（两条路径汇合） | BR-008、FR-RF-009 |
| 结论九（Search Workspace） | FR-SW-001 ~ FR-SW-007 |
| 结论十（V1 聚焦 L1–L3） | §1.2 范围 |
| 结论十一（不提前选技术） | §3 本阶段不回答的问题 |

---

# 32. 附录 B：未进入 SRS 的分析结论

以下 RAR 内容作为后续演进候选，暂不进入 SRS V1：

| RAR 内容 | 状态 | 备注 |
|---|---|---|
| L4 Business Answer | OUT | 后续 Business Answer / Business Insight |
| 自然语言完整解析 | OUT | V1 仅有限语法 |
| Chatter / Attachment 搜索 | OUT | 后续能力候选 |
| 跨公司实体合并 | OUT | 权限模型需先明确 |
| 搜索历史 | OUT | V2 候选 |
| Filter 状态 URL 化 | OUT | V2 候选 |
| 个性化推荐 | OUT | V2 候选 |
| 搜索分析 | OUT | V2 候选 |
| 高级搜索语法 | OUT | 不支持布尔表达式、排除词、括号分组 |
| 搜索结果保存/分享 | OUT | V2 候选 |

---

# 33. 当前状态

**RAR V0.2：ANALYSIS COMPLETE — FROZEN**

本版本用于：

* SRS 起草输入；
* 需求分析追溯；
* 产品范围讨论；
* 业务语义确认。

本版本：

> **不是 SRS。**

> **不是技术设计。**

> **不授权开发。**

**下一阶段：**
1. SRS 起草（已完成 V1.0）
2. SRS 评审迭代（已完成 V1.1、V1.2）
3. SRS V1.3 重写
4. SRS Freeze
5. Technical Research / Spike
6. DDD / TDD
7. Implementation