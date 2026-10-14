# CC-017-1 — Structured Result Card Template Output

## 0. Governance

| 字段 | 值 |
|---|---|
| Coding Contract | CC-017-1 |
| 版本 | v1.0.1 |
| 状态 | APPROVED / FROZEN；授权按本契约实施 |
| Intent ID | `GS-SEARCH-STRUCTURED-RESULT-CARD-TEMPLATE-OUTPUT` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.5 FROZEN（本 CC 不修改） |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.4 FROZEN（本 CC 不修改） |
| 前置 CC | CC-001 ~ CC-017、CC-014-1、CC-014-2 |
| 相关 CC | [CC-014](./CC-014_result_card_template_designer.md)、[CC-014-1](./CC-014-1_relation_field_multi_level.md)、[CC-017](./CC-017_ui_layout_optimization.md) |
| 模块 | `wd_global_search` |
| 目标 | 为 Result Card 增加显式结构化模板输出模式，同时保留纯文本模板及历史字段输出兼容 |
| 批准 / 冻结 | 用户于 2026-10-14 批准冻结并进入实施 |

**治理边界：** 本 CC 是新增的、独立的执行契约。它只定义 Result Card 的结构化配置、响应输出和呈现接口；不修订 SRS、TDD、CC-014、CC-014-1 或 CC-017。用户于 2026-10-14 选择：结构化配置采用 Resource 级对象，`title` / `meta` / `summary` 复用现有模板语法，`details` 使用 One2many loop 并最多输出 3 项及截断标记。

**版本基线处理：** 本稿基于 SRS v1.5 FROZEN、TDD v0.4 FROZEN，以及已冻结的 CC-014、CC-014-1、CC-017。CC-017-1 不改变这些文件的现有冻结语义；若评审或实施要求修改任何基线文件，必须先停止并做正式影响评审。

## 1. Contract Goal

**一句话目标：** 在不改变搜索执行语义的前提下，让管理员显式配置 Result Card 的主标题、Meta、摘要和明细语义区域，由服务端输出 `snapshot.card`，并由前端逐区渲染。

```text
Business Resource
  ├── 既有 card_template ───────────────► snapshot.rendered_text（保持 CC-014 纯文本行为）
  ├── 新 structured_card_template
  │     ├── title / meta / summary
  │     └── details（One2many loop）
  │             │
  │             ▼
  │      Publish 校验并写入 Published Snapshot
  │             │
  │             ▼
  │      当前用户授权 + 现有 formatter / loop renderer
  │             │
  │             ▼
  │      snapshot.card { title, meta, summary, details, details_truncated }
  │             │
  │             ▼
  │      独立 DOM 节点；沿用 CC-017 既有视觉规则
  └── 仅历史 Snapshot 的字段输出 ───────► snapshot.fields（保持兼容）
```

## 2. Background and Acceptance Findings

### 2.1 起草前核对

核对日期：2026-10-14。核对范围是仓库中的冻结契约、当前实现和测试；复核了 CC-017 §2.1 所记录的 Search Workspace 浏览器观察。本次起草未重新操作浏览器或生成新截图。

| 核对项 | 当前事实 | 证据 |
|---|---|---|
| CC-014 | `card_template` 的模板结果为纯文本；变量通过服务端授权和格式化，HTML 呈现边界 escape 一次，前端使用 text node。CC-014 的模板/格式/空值行为必须保留。 | [CC-014 §7](./CC-014_result_card_template_designer.md) |
| CC-014-1 | 关系路径和 One2many loop 扩展仍输出纯文本；loop 语法有关系深度、静态块数、嵌套层级和模板长度限制。既有 plain-text loop 不截断当前用户可读的全部关联行。 | [CC-014-1 §§4–7](./CC-014-1_relation_field_multi_level.md) |
| CC-017 | 模板卡片只有一个 `rendered_text` 文本节点；禁止按标签、冒号、分隔符或语言文字猜测字段语义。视觉目标要求明细最多显示 3 项，超出用 `...`。 | [CC-017 §§2.3、6、17](./CC-017_ui_layout_optimization.md) |
| Executor | [executor.py](../../../mymodules/wd_global_search/services/executor.py) 在模板模式只返回 `snapshot.rendered_text`；没有模板时返回 `snapshot.fields`。两种输出不可从字符串互相推导。 |
| Workspace | [preview.js](../../../mymodules/wd_global_search/static/src/js/preview.js) 将 `rendered_text` 作为单一文本块渲染；`snapshot.fields` 才有独立的字段 DOM。 |
| 模板测试 | [test_template.py](../../../mymodules/wd_global_search/tests/test_template.py) 覆盖纯文本模板、关系路径和 One2many 输出。 |
| 配置测试 | [test_configuration.py](../../../mymodules/wd_global_search/tests/test_configuration.py) 覆盖未知模板变量、缺少模板、格式键和 Publish 拒绝行为。 |
| 集成 / 回归测试 | [test_cc015_contract.py](../../../mymodules/wd_global_search/tests/test_cc015_contract.py)、[test_navigation.py](../../../mymodules/wd_global_search/tests/test_navigation.py) 覆盖 Search response 消费、权限/搜索契约和卡片导航。 |

**核对范围与方法：** 仅只读检查仓库中的冻结契约、服务端代码、前端代码和现有测试；复核 CC-017 已记录的页面观察。未修改配置、业务数据或既有文档，未直接读写数据库，未通过 Odoo ORM 执行运行时读写，也未在本次起草中重新打开浏览器或生成截图。所有实现差距均以已检查的源码/测试和 CC-017 记录为依据，不将未执行的运行时验收描述为已通过。评审补充项在本次修订中纳入契约；浏览器矩阵、自动化测试、性能数据和 HVR 均为实施验收项目，当前未宣称通过。

**评审记录：** 2026-10-14，用户批准修订后的 CC-017-1 冻结并进入实施。修订纳入版本基线与核对范围、明细截断及 schema mismatch 语义、模式切换/迁移、多语言、日志白名单、fixture 要求、验收/HVR、浏览器/viewport 矩阵和继承性能软预算。用户随后批准文档勘误，将 `sale.order.date_order` 示例格式键从 `date` 更正为 `datetime`；不改变 CC-014 formatter 或运行行为。该批准不构成实现测试或 HVR 已通过的证据。

### 2.2 Implementation Gap

当前模板仅表达一个有序纯文本流，不能让消费者确定某段文字属于标题、Meta、摘要或某个明细项。无模板字段输出虽然保留 Label/Value，却没有语义区域角色。CSS/JS 无法安全还原这些语义，因此管理员启用 CC-014 模板后，CC-017 所需的卡片层级无法仅靠样式完成。

### 2.3 Existing Contract Support

- SRS FR-SW-003 已要求每条结果提供由 Business Resource 配置决定的 Snapshot，但未规定结构化模板 response schema。
- CC-014 / CC-014-1 已提供纯文本 token、格式化、授权过滤及关系/loop 校验能力，可作为新结构的解析与值渲染基础。
- CC-017 已明确所需视觉分区、最多 3 条明细及超量省略符号；本 CC 仅提供可供其渲染的语义节点，不重定义颜色、字号、间距或字体。
- `snapshot.card` 是新增的 additive response shape，仅针对显式启用的新模式；不重定义 SearchRequest、Count、分页、cursor、错误 envelope、Resource 选择或条件语义。

**冻结文件声明：** 本文件不修改 SRS v1.5、TDD v0.4、CC-014、CC-014-1、CC-017 或其它既有冻结文件。若实施必须修改上述冻结文件，必须停止并另行走正式变更评审。

## 3. Scope

### 3.1 In Scope

- 在 Business Resource 上新增显式 `structured_card_template` 配置对象，并随既有配置生命周期发布。
- 定义 `title`、`meta`、`summary`、`details` 的配置、验证、授权和值语义。
- 为结构化模式新增 `snapshot.card` 响应对象。
- 为 `snapshot.card` 增加独立、纯文本的前端 DOM 区域。
- 保留 `snapshot.rendered_text` 和 `snapshot.fields` 两种已有输出的消费行为。
- 使用现有解析、formatter、ORM 权限、Published Snapshot 和 Search API 流程；通过 IHR、ATR 和 HVR 记录实施证据。

### 3.2 Out of Scope

- 修改现有纯文本模板语法、语义、性能预算、空值或权限行为。
- 根据字段 Label、模板文本、冒号、换行、`|`、`-` 或语言文案猜测字段角色。
- 修改 CC-017 的字号、颜色、字体、间距、分页和卡片视觉规则。
- 修改搜索 query、operator、field path、Resource 命中、搜索排序、Count、分页/cursor 或错误行为。
- 增加搜索索引、外部服务、新架构、LLM、向量检索、Elasticsearch 或 OpenSearch。
- 修改 `odoo/`、官方 addons、SRS、TDD 或既有 CC。

### 3.3 与 CC-014 / CC-014-1 的边界

CC-014/CC-014-1 的 `card_template` 仍是一份完整纯文本模板，输出仍为 `snapshot.rendered_text`；旧模板的 formatter、`—` 空值、生产无权变量为空字符串、HTML escaping 和 loop 全行行为均不变。

新模式另存 `structured_card_template`。它复用现有模板语法与字段解析规则，但服务端把显式配置区域分别序列化；只有新模式的 `details` 区域受 CC-017 的三项展示上限约束。该差异不反向作用于既有 `card_template`。

### 3.4 与 CC-017 的边界

CC-017 继续是结构和视觉目标的唯一依据。本 CC 不添加 CSS 设计决定，不改变既有视觉 token；前端只新增能承载既定视觉角色的 DOM 结构，并使用 CC-017 已规定的类/样式契约。结构无法验证时不得将视觉验收标为通过。

## 4. Structured Template Configuration

### 4.1 配置对象

每个 Business Resource 可选配置一个 `structured_card_template`。它是明确的 Resource 级对象，并作为同一 Published Configuration Snapshot 的组成部分；不新增独立 Registry、服务或发布生命周期。

```json
{
  "schema_version": 1,
  "title": "{name}",
  "meta": "Sales Order · {date_order:datetime}",
  "summary": "{partner_id} · {amount_total:monetary}",
  "details": "{order_line}{product_id.name} × {product_uom_qty}{/order_line}"
}
```

| 区域 | 类型 | 必需性 / 校验 |
|---|---|---|
| `schema_version` | 整数 | 必须为 `1`；不接受布尔值、未知版本或隐式降级 |
| `title` | 模板字符串 | 必填、非空白、至少包含一个字段变量；不能包含 One2many loop |
| `meta` | 模板字符串 | 可选；省略或空字符串表示不输出 Meta 区域；不能包含 One2many loop |
| `summary` | 模板字符串 | 可选；省略或空字符串表示不输出摘要区域；不能包含 One2many loop |
| `details` | 模板字符串 | 可选；省略或空字符串表示无明细。非空时须包含且只包含一个顶层 One2many loop；loop body 是单个明细项模板 |

四个文本区域使用 CC-014/CC-014-1 已定义的常量、转义、字段变量、格式键、路径深度、loop 标签和 formatter 规则。除本节指出的结构投影外，不定义或放宽任何既有模板语法。

**完整示例及语义：**

| 配置 | 业务含义 |
|---|---|
| `title: "{name}"` | 订单编号等记录主标识 |
| `meta: "Sales Order · {date_order:datetime}"` | Resource 类型和业务日期/时间 |
| `summary: "{partner_id} · {amount_total:monetary}"` | 客户和总额 |
| `details: "{order_line}{product_id.name} × {product_uom_qty}{/order_line}"` | 按当前用户可见顺序渲染明细，最多返回三项 |

以上是配置示例，不代表所有 Resource 都有相同字段名；实际变量必须在该 Resource 的 Published model mapping 上通过 §11 校验。

### 4.2 明确选择与互斥关系

- 新建或编辑的 Resource 必须明确选择一种 Publish 输出配置：既有 `card_template` **或** 新 `structured_card_template`，不能同时配置二者。
- 新对象是否存在是唯一的模式选择来源；不得通过模板文本内容、Label 或响应猜测模式。
- 既有 `card_template` 的配置和 Snapshot 不需迁移，继续按纯文本模式运行。
- 旧 Snapshot 若没有两种 template 配置，继续由现有兼容路径输出 `snapshot.fields`；本 CC 不新增可发布的 fields-only 配置模式。
- 两种模板同时存在、结构对象损坏或不支持的 schema version，Publish 必须拒绝；运行时异常 Snapshot 按既有配置错误安全路径失败，不回退到另一种输出模式。

### 4.3 模板长度、变量与 loop 预算

- 单个 Resource 的四个区域合计不得超过 CC-014 的 8 KiB UTF-8 模板预算及 50 次变量引用预算。
- `title`、`meta`、`summary` 不允许 loop block。
- `details` 最多 5 个静态 loop block、嵌套深度最多 2、每个 loop body 最多 1000 个 Unicode code point；遵循 CC-014-1 的闭合标签、One2many 类型、字段作用域和关系深度规则。
- 四区域总预算不可按区域分别重置；拒绝通过拆分区域绕过旧 parser 的资源预算。
- 原 CC-014/CC-014-1 的文本模板长度、变量、loop 及性能行为不改变。

### 4.4 多模型 Resource

- 配置作用域是单一 Business Resource；多 Resource 各自独立配置，响应按每条结果对应的 Resource 选择配置。
- 对 composite Resource，结构化配置必须在该 Resource 的每一个 Published model mapping 上通过字段路径、类型和 formatter 校验；不按命中模型猜测或动态更换区域定义。
- 某模型无法解析任一必需区域变量时，Publish 拒绝；不得发布后对该模型静默删除区域或输出成功形状的默认内容。

## 5. Structured Response Structure

### 5.1 Search Result API

不新增 endpoint 或 request 字段。每个搜索结果沿用现有身份字段、排序、分页和 Result Identity，只扩展 `result.snapshot`：

```json
{
  "id": 42,
  "_resource": "sale_order",
  "_model": "sale.order",
  "_record_id": 42,
  "snapshot": {
    "card": {
      "schema_version": 1,
      "title": "S00004",
      "meta": "Sales Order · Oct 1, 2026",
      "summary": "Gemini Furniture · 2,240.00 €",
      "details": [
        "Virtual Interior Design × 16",
        "Office Lamp × 10",
        "Large Meeting Table × 3"
      ],
      "details_truncated": true
    }
  }
}
```

| 属性 | 类型 | 不变量 |
|---|---|---|
| `schema_version` | 整数 | 固定为 `1` |
| `title` | 字符串 | 必须存在；仅含模板渲染后的纯文本，可为空字符串（例如当前用户无权读取唯一标题变量） |
| `meta` | 字符串 | 必须存在；未配置或渲染为空时为 `""` |
| `summary` | 字符串 | 必须存在；未配置或渲染为空时为 `""` |
| `details` | 字符串数组 | 必须存在，稳定顺序；最多 3 项；无明细时为 `[]` |
| `details_truncated` | 布尔值 | 必须存在；仅当存在第 4 个以上当前用户可见且可输出的明细项时为 `true` |

`details_truncated=true` 只表示卡片摘要没有显示全部可见明细；不得影响完整 Search 结果、Count、分页、cursor、record identity 或后续 Form 查看。

其判定严格为：`true` 表示存在第 4 个或之后的、当前用户可见且可输出的明细项；`false` 表示不存在这类额外可见项。响应不返回剩余明细数量，也不得依据无权记录或字段计算该标记。

### 5.2 Shape Exclusivity

一个结果只能包含一种既定 Snapshot 模式，不得将模板文字复制到 `card` 来伪造结构：

| 配置 / Snapshot 情况 | `snapshot` 输出 |
|---|---|
| 新 `structured_card_template` 模式 | 仅包含 `card` |
| 既有 CC-014/CC-014-1 `card_template` | 保持仅包含 `rendered_text` |
| 历史无 template、仍走既有字段 serializer | 保持仅包含 `fields` |

三种模式均为 `snapshot` 的互斥形式；`card` 不同时携带 `rendered_text`/`fields`。不得改变 legacy payload 的字段、顺序、默认值或字符串内容。

## 6. Structured Frontend Rendering

- Workspace 先检查 `snapshot.card.schema_version === 1`；匹配时只渲染结构化对象。未知版本不得按 `rendered_text` 或 `fields` 猜测回退。
- DOM 每个语义区域独立：

```html
<article class="wd-record-card">
  <h3 class="wd-card-title">…</h3>
  <div class="wd-card-meta">…</div>
  <p class="wd-card-summary">…</p>
  <div class="wd-card-details">
    <span class="wd-card-detail">…</span>
    <span class="wd-card-detail">…</span>
    <span class="wd-card-detail">…</span>
    <span class="wd-card-details-overflow">…</span>
  </div>
</article>
```

- `title` 写入独立 H3 节点；`meta`、`summary`、`details` 分别进入各自区域节点。
- `meta`、`summary` 为空字符串时省略对应 DOM 节点；`title` 为空时保留卡片与导航身份但省略可见标题文字，不造“Record”值、不展示内部字段名。
- 每个明细数组元素创建一个独立文本节点；相邻项目间的 `·` 和截断 `...` 作为纯文本节点插入，遵循 CC-017 的格式。
- 所有服务端值用 `textContent`/文本节点写入，禁止对字段值、标签、模板片段使用 `innerHTML`、动态 selector、事件属性或可执行 HTML。
- DOM 结构复用 CC-017 已冻结的字号/颜色/间距样式；本 CC 不新增或覆盖任何视觉 token。
- 卡片选择、键盘操作、点击/双击、Ctrl/Cmd+Click 和 Native Form 导航继续遵守 CC-013；渲染结构不得吞掉既有交互事件。

**Schema version 不匹配：** 服务端只允许 Publish `schema_version=1`，异常 Published 配置按既有配置错误路径失败。若前端收到未知 `snapshot.card.schema_version`（例如资产与 API 版本不匹配），不得渲染该对象，也不得退回解析 `rendered_text`/`fields`；仅在该卡片位置显示通用、无内部细节的安全提示（复用既有安全提示样式），保留 SearchResponse 状态、Count、分页及记录身份，不暴露未知版本值。

## 7. Backward Compatibility

| 既有消费者 / 数据 | 新契约要求 |
|---|---|
| `card_template` Published Snapshot | 内容和纯文本输出字节/语义保持不变；继续生成 `snapshot.rendered_text` |
| `snapshot.rendered_text` API 消费者 | 字段路径、格式化、换行、空值、无权字段、安全转义与错误行为不变 |
| 旧 `snapshot.fields` Consumer | 历史 Snapshot 按原结构、顺序、Label/Value、空值和无权字段行为继续输出及渲染 |
| 新结构化模式 Consumer | 只消费 `snapshot.card` schema version 1；不依赖 text parsing |
| 未知 schema version / malformed card | 未知版本按 §6 显示通用卡片级安全提示；服务端 Published 配置错误按既有配置错误路径拒绝；均不当作旧模式解释 |

- 三种模式共存于同一 Search API 消费链，但按 §5.2 对每个结果互斥选择。
- 新模式的新增字段对不认识 `snapshot.card` 的 API 消费者是 additive；前端版本发布须与可消费 `card.schema_version=1` 的资产版本保持一致。
- 不要求将旧 `card_template` 自动转换成语义槽；自动转换会依赖文本推断，禁止执行。
- 配置编辑切换模板模式时，必须经既有 Published/Retired pending edit、校验、Apply/Publish、snapshot/checksum 和审计流程；失败时旧活动模式继续有效。

### 7.1 模式切换与迁移策略

1. 管理员在现有 Resource 配置生命周期中编辑 Draft，或对 Published/Retired 版本建立 pending edit；不得直接修改活动 Snapshot。
2. 管理员显式填写 `structured_card_template` 并清除待发布版本中的 `card_template`，或清除结构对象并选择既有 `card_template`；不能同时保留两者。
3. 执行现有 Check/Apply/Publish；按 §11 验证所有 model mapping、预算、权限策略和 schema。
4. 只有校验与原子 Apply/Publish 成功后，新模式才对后续 Search 生效；记录既有版本、checksum 和审计信息。
5. 校验/Apply 失败时旧 Published mode、snapshot、checksum 和搜索行为继续有效，不产生部分切换。

既有数据库配置和已发布 Snapshot 无需数据迁移；历史 `card_template` 和 `snapshot.fields` 按原样消费。新模式只通过既有 ORM 配置/升级路径保存，不提供 SQL 迁移脚本、不自动转换模板，也不回写业务数据。

## 8. Details Rules

1. 新模式的 `details` 来自显式配置的唯一顶层 One2many loop，不从 `snapshot_fields`、明细 Label 或模板文本中提取。
2. 遵循 CC-014-1 的 One2many 字段类型、当前作用域、关系访问、Record Rule、公司边界和稳定 ORM 顺序；不允许使用 Many2many 作为 loop 集合。
3. 结构化输出最多包含前三个可显示明细项，顺序与当前用户可见 ORM 顺序一致。若发现第 4 个可显示项，停止生成更多卡片明细并设置 `details_truncated=true`。
4. 当前用户不可读取 loop 字段、子记录或某明细模板所引用的任一字段时，该不可读明细项整体不输出；其存在不得影响 `details` 数量或 `details_truncated`。授权判定失败时 Resource 按既有失败关闭路径处理。
5. 当前用户有权读取但值为空时，变量沿用 CC-014 的 `—` 格式化行为；`False` Boolean 沿用“否/No”格式化，不能误作空值。
6. 空集合、无可显示记录或未配置 `details` 时输出 `details: []`、`details_truncated: false`，不渲染空明细容器。
7. 截断仅用于 Result Card 展示；不修改或删除业务数据，不约束 legacy plain-text loop（legacy 模式继续依 CC-014-1 输出全部可读行），也不改变 Count、分页或记录导航。
8. 超量 UI 标识为 CC-017 规定的纯文本 `...`；JSON API 中不把省略号混入 `details` 项，不返回被省略项目数。
9. 模板常量按管理员写入配置的原文显示，不自动翻译；字段值、Selection Label、Boolean、数字、货币、日期和时间沿用当前请求用户的语言/时区及 CC-009/CC-014 formatter。结构化模式不得引入不同于纯文本模式的 formatter。

## 9. Permission and Security Boundary

- 每一个配置变量都须在 Publish 时按 Resource/model mapping 验证；每次 Search 渲染仍用当前用户的普通 ORM environment 做字段、记录、关系和公司权限检查。
- Preview/Search 不允许使用 `sudo()`、superuser、admin env、构造的管理员用户、缓存中其它用户的渲染值或直接数据库读取。
- 无权变量不得进入 `title`、`meta`、`summary`、`details`、额外 metadata、日志、Count、错误或截断标志推断。
- 结构化结果只包含纯文本字符串；不允许模板 HTML、脚本、表达式、函数调用、任意 Python/Odoo 访问或动态字段推断。
- API JSON 保持原始 Unicode 文本语义；HTML escaping 只在 HTML 呈现边界执行一次；前端用 `textContent`，不得双重 escape 或执行标记。
- 模板常量是管理员显式配置的可见文本，不代表字段值；字段值严格按用户权限过滤。不得因常量或占位文案暴露无权字段/行是否存在。
- 新模式 render/validation 故障使用 CC-007 和现有 Resource/Search error envelope；不得吞错、伪造成功响应或添加可区分的权限错误细节。

### 9.1 Internationalization

- `title` / `meta` / `summary` / `details` 中的常量按配置文本原样呈现；不根据管理员语言或浏览器语言自动翻译，不新增按语言索引的模板 Registry。
- 字段值、Selection Label、Boolean、“—”占位相关 formatter、日期/时间、数字和货币按 Search 当前用户的服务端 `lang`/`tz` 渲染，遵循 CC-009、CC-014 的既有 fallback。
- 同一个 Published 结构化模板在不同用户语言下可以产生不同字段格式，但不得改变字段授权、结果集合、Count 或分页；不复用其它用户/语言的已渲染字符串。
- 若实现要求自动翻译模板常量或引入每语言模板副本，超出本 CC，须停止并独立评审。

### 9.2 Observability and Logging

- 结构化卡片渲染复用 CC-008 既有 Search completion/resource event 与 `log_event` allowlist；允许记录既有 allowlist 内的 `request_id`、`config_version`、`resource`、`latency_ms`、`status`、`error_code`。
- 本 CC 不新增 `mode` 等日志字段、不扩展 CC-008 allowlist，也不新增日志事件类型；若确需 mode 专属指标，先作独立 observability 影响评审。
- 禁止记录 Raw Query、模板原文、模板常量、字段值、明细内容、Record Rule、权限明细、token 或其它业务敏感文本。字段不在 allowlist 时必须由既有 helper 丢弃，不能绕过 helper。

## 10. Invariants

| ID | 冻结不变量 |
|---|---|
| CC17-1-INV-001 | 不修改 CC-014/CC-014-1 既有纯文本模板语法、响应或运行语义。 |
| CC17-1-INV-002 | 不修改 CC-017 的视觉规则；结构化节点仅提供其消费所需语义。 |
| CC17-1-INV-003 | 既有纯文本模板作为兼容模式保留，输出仍是 `snapshot.rendered_text`。 |
| CC17-1-INV-004 | 结构化模板配置必须显式、Resource-scoped、Publishable 且属于 Published Snapshot。 |
| CC17-1-INV-005 | 不依赖 Label、冒号、换行、分隔符、语言文案或任意文本格式推断字段语义。 |
| CC17-1-INV-006 | 每个输出字段值在每次请求中均按当前用户授权过滤。 |
| CC17-1-INV-007 | `snapshot.card` 所有内容均为纯文本及有界数组，不包含 HTML。 |
| CC17-1-INV-008 | 模板不得执行 HTML/脚本/表达式/方法调用，不得使用 `eval` 或等价机制。 |
| CC17-1-INV-009 | HTML-escape 只在 HTML 呈现边界执行一次；前端以文本节点呈现。 |
| CC17-1-INV-010 | 不改变关键词解析、条件合并、关系匹配、结果集合、排序或搜索语义。 |
| CC17-1-INV-011 | 不改变当前用户、公司、模型、记录、字段和关联读取权限边界。 |
| CC17-1-INV-012 | 不改变现有 SearchResponse Count 及其作用域/计算来源。 |
| CC17-1-INV-013 | 不改变 page size、offset、cursor、分页顺序或总结果范围。 |
| CC17-1-INV-014 | 不改变现有错误 code、Resource/Search 状态、partial-failure 或 failure envelope。 |
| CC17-1-INV-015 | 不修改 `odoo/` 或官方 addons。 |
| CC17-1-INV-016 | `card_template` 与 `structured_card_template` 互斥；一个结果只携带一个 Snapshot mode。 |
| CC17-1-INV-017 | 新结构化明细最多 3 项；截断只影响摘要显示，并且不可依据无权数据设置标记。 |
| CC17-1-INV-018 | 历史 `snapshot.fields` payload 和 legacy plain-text loop 行为保持不变。 |

## 11. Publish-time Validation

Publish/Apply 必须在同一配置事务中完成下列检查；任一检查失败，返回现有配置错误结果，旧 Published snapshot/checksum/active mode 保持不变。

| 验证域 | 必须检查 |
|---|---|
| 模式互斥 | 同一 Resource 只能发布 `card_template` 或 `structured_card_template`；两者均无仅对历史 Snapshot 兼容，不允许新配置借此绕过既有配置校验 |
| Schema | 对象类型正确，`schema_version=1`；拒绝多余执行字段、未知字段、未知版本、非字符串区域 |
| 语义区域 | `title` 非空、含至少一个变量；`meta`/`summary` 可选；非空 `details` 恰有一个顶层 One2many loop |
| 字段与模型 | 每个变量路径在 Resource 的所有 model mapping 上存在、类型及 formatter 兼容，符合 CC-014/014-1/014-2 关系路径限制 |
| 深度 / 关系 | 当前 Published Resource 的 `max_relation_depth`、Many2one/Many2many/One2many 路径规则均被应用 |
| Details | loop 字段在每个 mapping 上都是允许的直接 One2many；body 字段作用域合法；禁止跨作用域引用和未闭合/交叉 loop |
| 预算 | 合计模板字节、变量数、loop 块数、嵌套深度、body 长度满足 §4.3 上限 |
| 权限策略 | 以现有发布校验用户 context 验证配置所需模型/字段；该检查不能替代运行时当前用户授权 |
| Snapshot | 配置包含在 canonical Published Snapshot、size/checksum、版本与审计里；不另建 cache/registry |
| 回滚安全 | 校验或 Apply 失败时保留旧 snapshot/checksum/template mode；不产生部分发布 |

Publish 不读取业务记录来预估明细数量或决定 `details_truncated`；截断只在当前用户 Search 执行时按可读记录计算。

## 12. Test Matrix

所有测试使用 Odoo ORM 测试环境及普通用户权限上下文；不直接读写数据库、不以 `sudo()` 绕过授权。每条测试须在代码落地后按给定 suite 运行并记录 ATR。

| ID | Suite / 测试 | 可执行步骤 | 通过标准 |
|---|---|---|---|
| CC17-1-TEST-001 | `tests/test_structured_card.py::test_publish_accepts_structured_template` | 创建含 title/meta/summary/details 的 draft Resource，执行既有 Publish/Apply 校验并读取 published snapshot | 配置通过；Snapshot 包含 schema version 1 和完整结构对象 |
| CC17-1-TEST-002 | `tests/test_structured_card.py::test_response_has_snapshot_card_schema` | 对 fixture 运行普通 Search，读取单条结果 JSON | `snapshot.card` 字段/类型与 §5.1 一致，不返回 rendered text 伪结构 |
| CC17-1-TEST-003 | `tests/test_structured_card.py::test_three_detail_limit_and_truncation` | 建立 0、1、3、4 个有权明细，分别搜索 | 输出数为 0/1/3/3；第 4 个可见项使标记为 true；其余为 false |
| CC17-1-TEST-004 | `tests/test_backward_compatibility.py::test_plain_text_template_payload_is_unchanged` | 使用已发布 `card_template` 执行测试前后同一 fixture query 并对 payload 做 exact equality | `snapshot.rendered_text` 文本完全一致；无 `card` key；Count 与结果身份一致 |
| CC17-1-TEST-005 | `tests/test_backward_compatibility.py::test_legacy_snapshot_fields_payload_is_unchanged` | 对不含 template 的历史 snapshot fixture 执行现有字段 serializer | `snapshot.fields` key/顺序/Label/Value 与原期望一致；无 `card` key |
| CC17-1-TEST-006 | `tests/test_structured_card.py::test_publish_rejects_ambiguous_or_invalid_regions` | 分别提交双模式、空 title、未知 schema、非法变量、循环标题、多个 details root loops | 每个用例均在 Publish/Apply 拒绝；旧 Published checksum 不变 |
| CC17-1-TEST-007 | `tests/test_structured_card.py::test_aggregate_template_budgets` | 分区域累积超过 8 KiB、50 variables、loop block/depth/body 上限 | 拒绝发布；拆分到多个 region 不能绕过总预算 |
| CC17-1-TEST-008 | `tests/test_structured_card.py::test_empty_values_and_empty_details` | 测试空 title/meta/summary、空集合、已授权空字段和 Boolean False | 区域空值处理符合 §5/§8；Boolean False 保持格式化；无空 details DOM |
| CC17-1-TEST-009 | `tests/test_structured_card.py::test_current_user_permissions_filter_each_region` | 发布用户可读模板字段，以无字段权、无关系权和 Record Rule 用户分别搜索 | 无权值/明细不进入 JSON；无权行不影响 truncated/Count；无 `sudo()` 回退 |
| CC17-1-TEST-010 | `tests/test_structured_card.py::test_company_scope_does_not_cross_records` | 同一用户切换允许的公司集合执行相同 Search | `snapshot.card` 不含其它公司记录字段/明细；Search 公司结果仍服从既有规则 |
| CC17-1-TEST-011 | `tests/test_structured_card.py::test_multiple_resources_use_own_templates` | 两个 Resource 各配置不同区域，在同一 Search response 返回两者结果 | 每条结果按 `_resource` 使用其自己的模板；不串值、不混用 region |
| CC17-1-TEST-012 | `tests/test_structured_card.py::test_composite_model_mappings_are_validated` | 为 composite Resource 配置一模型存在、另一模型缺失的字段路径 | Publish 拒绝；通过时每个模型按同一显式模板正确输出 |
| CC17-1-TEST-013 | `tests/test_structured_card.py::test_structured_output_does_not_change_count_or_pagination` | 在大小固定的数据集上分别用三个输出模式搜索并翻页 | `counts`、结果 identities、cursor、页长和排序完全一致 |
| CC17-1-TEST-014 | Browser / Playwright `test_structured_card_semantic_dom` | 加载结构化 response fixture，检查卡片 DOM 与文字节点 | title/meta/summary/details 有独立 DOM；HTML/script payload 只显示文本，无执行节点 |
| CC17-1-TEST-015 | Browser / Playwright `test_legacy_cards_render_unchanged` | 同页分别注入 rendered_text 与 fields fixtures 并验证点击/键盘/导航 | 两种 legacy 卡片的可见内容、选择、双击和新 Tab 交互保持原状 |
| CC17-1-TEST-016 | `tests/test_structured_card.py::test_structured_rendering_performance_p95` | 对每个性能阶段至少采集 100 次样本；分别测 parser、单卡渲染、Publish/Apply 校验及 Preview API 端到端 P95，记录 fixture 数据量、环境、冷/热状态 | 继承 CC-014 §7.3 软预算：parser ≤10 ms、单卡渲染 ≤50 ms、Publish/Apply 校验 ≤100 ms、Preview API ≤500 ms；关系读取、权限检查及循环计入对应阶段，不得降低检查或放宽阈值 |
| CC17-1-TEST-017 | `tests/test_structured_card.py::test_schema_mismatch_is_card_local` | 给前端未知版本和 malformed card fixtures，服务端 Publish 未知版本配置 | Publish 按既有配置错误拒绝；前端仅该卡片显示通用安全提示，不解析其他 Snapshot 字段，Search 状态/Count/分页/身份不变 |
| CC17-1-TEST-018 | `tests/test_structured_card.py::test_mode_switch_is_atomic_and_legacy_snapshot_is_unchanged` | 在纯文本、结构化和 fields-only 模式间分别成功及故意失败地 Publish/Apply | 仅成功原子发布切换；失败保留旧 Snapshot/checksum/活动模式；既有模板及历史 fields 不迁移、不改变 |
| CC17-1-TEST-019 | `tests/test_structured_card.py::test_locale_formats_values_but_not_template_constants` | 使用同一配置、不同 `lang`/`tz` 的普通用户执行 Search，模板含常量及日期、数字、Selection 值 | 常量保持配置原文；字段值仅按当前用户 locale/tz 格式化；不跨用户复用已渲染内容，权限/Count/分页不变 |
| CC17-1-TEST-020 | `tests/test_structured_card.py::test_structured_logging_uses_existing_allowlist` | 运行成功及失败的结构化卡片搜索并检查既有日志捕获器 | 只出现 CC-008 allowlist 字段；无 mode、新事件、模板/字段/明细/权限敏感内容 |
| CC17-1-TEST-021 | Browser / Playwright `test_structured_card_browser_matrix` | 按下方浏览器和 viewport 矩阵，运行 TEST-014/015 的 DOM、安全和 legacy 交互检查 | 每个矩阵组合记录浏览器/引擎版本、viewport、运行结果及截图证据；无一项预先视为通过 |
| CC17-1-TEST-022 | Manual HVR `HVR-CC-017-1` | 使用已发布结构化模板，在普通用户 Search Workspace 操作并逐项检查下方验收场景 | 验收人对每个场景记录 PASS/FAIL、环境、截图/录屏引用和日期；FAIL 项修复复测前不得关闭 HVR |

**Fixture 规范：** 自动化测试须使用代码管理的确定性 ORM fixture，明确记录用户、公司、模型映射、可见/不可见关联行、语言/时区及模板版本；每个权限案例明确区分“记录不存在”与“当前用户不可见”。Fixture 不得使用 `sudo()` 建立被测行为、读取生产数据、依赖环境现存业务记录或将敏感值写入日志。浏览器 fixtures 只放无敏感测试文本，并覆盖 `<script>`、HTML 属性/实体、空值、最大三条及截断场景。

**浏览器与 viewport 验证矩阵：**

| 浏览器引擎 | Desktop viewport | Narrow viewport | 版本 / 结果 |
|---|---:|---:|---|
| Chromium | 1440 × 900 | 390 × 844 | 实施时记录实际版本与 PASS/FAIL；当前待执行 |
| Firefox | 1440 × 900 | 390 × 844 | 实施时记录实际版本与 PASS/FAIL；当前待执行 |
| WebKit | 1440 × 900 | 390 × 844 | 实施时记录实际版本与 PASS/FAIL；当前待执行 |

浏览器验收不调整 CC-017 视觉 tokens。若项目自动化环境不支持某一引擎，记录阻碍和实际可执行组合，不得将未运行项标为 PASS；在 HVR 完成前该缺口仍开放。

**人工 HVR 验收场景：**

1. 结构化卡片分别呈现独立标题、Meta、摘要及 0/1/3 条明细；第 4 条可见明细以 `...` 标识，界面不显示明细总数。
2. 空 Meta/摘要/明细不出现伪造标签、空容器或内部字段名；空标题不丢失记录选择及导航能力。
3. `<script>` / HTML 测试字符串按纯文本显示且不执行；不发生双重 HTML escaping。
4. 旧 `rendered_text` 与 `fields` 卡片的文本、布局规则、键盘/点击/双击、新 Tab 导航保持原状。
5. 搜索结果、Count、分页、筛选、资源状态及打开记录行为与结构化输出前相同。

HVR 记录模板配置版本、普通用户及公司、用户 locale/timezone、浏览器/viewport、验收人、日期、每项结果和证据引用。该矩阵是待实施执行的验收计划，不是本稿已完成的视觉验证。

## 13. Regression Requirements

| 契约 | 回归要求 |
|---|---|
| CC-001 | Draft/Published/Retired 暂存、Apply/Publish、checksum、审计和失败原子性；structured config 走相同生命周期 |
| CC-002 | Search API 输入、结果身份、Count、cursor、分页和排序不变；仅结构化模式增加 `snapshot.card` |
| CC-003 | 用户、公司、模型、记录、字段及关系读取权限逐次执行；禁止 superuser fallback |
| CC-004 | 既有 Search Workspace / Form Preview 行为不变；不增加新 Preview service |
| CC-005 | Query、筛选、Resource 选择、折叠状态和结果状态顺序不变 |
| CC-006 | 搜索失败、partial success、timeout 和导航错误保持既有安全行为 |
| CC-007 | 继续使用现有错误 code/envelope；不泄露内部模板文本或权限细节 |
| CC-008 | 既有 observability allowlist 保持；不记录渲染字段值、模板变量值或业务明细 |
| CC-009 | locale/timezone formatter 使用当前用户 context；日期、数字、货币与 Selection 标签不变 |
| CC-010 | Snapshot/version/checksum 完整性及发布生命周期不变；结构化对象不得脱离 snapshot |
| CC-011 | 既有审计、性能/稳定性门禁不变；新增 render P95 纳入同等测量证据 |
| CC-012 | Resource selector、计数、过滤、Resource key 语义不变 |
| CC-013 | 卡片打开 Action、当前记录授权复查、新 Tab/键盘操作不变 |
| CC-014 | 纯文本配置和 `snapshot.rendered_text` 行为精确回归；模板安全与格式化不变 |
| CC-014-1 | 旧多级路径、M2M separator、One2many 全行纯文本 loop 精确回归 |
| CC-014-2 | Published field path 和 UI 业务标签不变；不得由 structured card 新增可搜索字段 |
| CC-015 | 多词 Contains、condition 合并、query understanding、Count、错误和 cursor 均不变 |
| CC-016 | Keyword chips、field selector、operator/value、条件分区展示和请求形状不变 |
| CC-017 | 已冻结字号、颜色、字体、间距、卡片无边框/阴影、分页和 DOM 顺序保持；只填充明确的语义节点 |

## 14. Stop Conditions

发生以下任一情形，停止实施并记录证据；不得猜测、放宽或以 fallback 隐藏失败：

1. 结构化配置不能在 Publish/Apply 时被确定性验证。
2. `title` / `meta` / `summary` / `details` 任一区域不能显式配置。
3. 实现需要根据字段 Label、模板文本或分隔符推断区域。
4. 实现需要修改 CC-014 或 CC-014-1 的纯文本输出/loop 契约。
5. 实现需要修改 CC-017 的任何视觉规则。
6. 实现需要引入新架构、独立 Registry、缓存系统或外部服务。
7. 实现需要 LLM、向量检索、Elasticsearch、OpenSearch 或外部搜索引擎。
8. 实现需要 `sudo()`、superuser、admin env、直接数据库读取或绕过 Odoo ORM 权限。
9. 实现需要修改 `odoo/` 或官方 addons。
10. 实现改变搜索语义、匹配字段、domain 或返回集合。
11. 实现改变用户/公司/记录/字段权限边界，或依赖无权数据计算明细截断。
12. 实现改变 Count、分页、cursor、结果身份/顺序或既有错误行为。
13. 历史 `rendered_text`、`snapshot.fields` 或 Published checksum 无法保持向后兼容。
14. 新配置不能对 composite Resource 的每个模型 mapping 验证。
15. 任何 HVR/权限测试无法通过普通 Odoo 用户环境可靠验证。
16. 结构化模式无法沿用当前用户 locale/timezone formatter，或要求自动翻译模板常量。
17. 未知/损坏 schema 无法限制为卡片级通用安全提示，或导致 SearchResponse 状态、Count、分页或记录身份改变。
18. 日志需求必须扩展 CC-008 allowlist、记录 mode、新事件或写入模板/字段/明细等敏感内容。
19. 任一继承性能预算无法满足，且只能通过放宽阈值、缩减权限检查、静默截断或隐藏失败来达成。
20. 现有配置生命周期无法保证模式切换原子性、失败回滚或历史 Snapshot 不迁移。
21. 浏览器矩阵存在未执行项被要求视为通过，或 HVR 缺少可复核的普通用户操作证据。

## 15. Definition of Done

- [ ] Resource 级结构化配置及版本 1 schema 已按本 CC 实现，字段区域均显式且通过 Publish/Apply 验证。
- [ ] `snapshot.card` schema 稳定，字符串/数组/bool 类型、最大 3 条 details 和截断标记通过测试。
- [ ] 前端为 title、meta、summary、details 创建独立 DOM，使用文本节点并保持 CC-017 样式与 CC-013 导航交互。
- [ ] `rendered_text` 和历史 `fields` 两种模式精确兼容；没有文本推断或静默 fallback。
- [ ] 每个输出值遵守当前用户权限；跨用户/公司、关联行、空值和恶意文本场景通过测试。
- [ ] Search 语义、Count、分页/cursor、错误行为及 CC-001~CC-017 回归通过。
- [ ] §12 可执行自动化测试及既有相关 suites 有 ATR 记录；至少 100 样本性能数据达到/报告既有软预算。
- [ ] IHR 记录实现文件、配置迁移/兼容、回滚方式；ATR 记录命令、结果、环境及失败；UI 有人工签署的 HVR。
- [ ] 所有 Stop Conditions 均未触发；用户正式批准本 CC 后方可宣布完成。
- [ ] 结构化模板常量/字段值分别遵循 §9.1 多语言规则；不同用户/公司/语言间无渲染值泄露。
- [ ] schema mismatch、原子模式切换、失败保留旧 checksum、现有日志 allowlist 通过 §12 自动化测试。
- [ ] 浏览器矩阵逐项记录实际版本/viewport/结果；未执行项明确标记未执行，不伪报 PASS。
- [ ] 人工 HVR 的五项场景均由验收人签署；截图/录屏仅作测试证据并避免业务敏感数据。
- [ ] 性能采样每阶段至少 100 次，记录环境、fixture 数据量、冷/热状态及 P95；超预算按 Stop Conditions 处理。

## 16. Decisions

| ID | 决策 | 理由 |
|---|---|---|
| CC17-1-DEC-001 | 新增 Resource 级 `structured_card_template` 对象 | 显式表达语义区域，不再把多个角色压成一个纯文本串 |
| CC17-1-DEC-002 | 新增 `snapshot.card`，schema version 为 1 | 为前端提供稳定、可校验的结构接口，避免解析旧文本 |
| CC17-1-DEC-003 | 前端为 title/meta/summary/details 创建独立 DOM | 满足 CC-017 的层级目标且不进行文本推断 |
| CC17-1-DEC-004 | 既有 `card_template` 继续作为纯文本兼容模式 | 保持 CC-014/014-1 冻结契约及已发布 Snapshot |
| CC17-1-DEC-005 | structured config 存在即显式选中结构化模式；与 `card_template` 互斥 | 消除双模式优先级歧义和模板内容启发式 |
| CC17-1-DEC-006 | 不从字段 Label 或模板文本推断 title/meta/summary/details | 本地化标签和任意常量不具备稳定字段语义 |
| CC17-1-DEC-007 | 每个区域字段在 Publish 验证、在运行时按当前用户重新授权 | Publish 权限不是 Search 用户的授权凭证 |
| CC17-1-DEC-008 | 每个区域值都输出纯文本 | 复用既有 XSS 防护边界，不引入可信 HTML 模板 |
| CC17-1-DEC-009 | HTML escaping 只在 HTML 呈现边界执行一次 | 避免脚本注入和双重 escaping |
| CC17-1-DEC-010 | 不修改 CC-014/014-1 的既有纯文本契约 | 新能力采用并行配置/响应模式，避免破坏历史模板和 loops |
| CC17-1-DEC-011 | structured `details` 最多 3 项；有第 4 个可见项时标记截断并由 UI 显示 `...` | 与 CC-017 的冻结视觉/内容规则一致，并限制卡片信息量 |
| CC17-1-DEC-012 | 未配置区域在响应中使用空字符串/空数组，布尔截断标记始终存在 | 稳定 JSON shape，前端不需猜测缺失 key 的语义 |
| CC17-1-DEC-013 | `details_truncated` 只依据第 4 个及后续当前用户可见且可输出的明细；不返回剩余数 | 避免通过摘要元数据泄露无权记录或行数 |
| CC17-1-DEC-014 | 未知 schema 由前端显示卡片级通用安全提示，不 fallback 到文本推断，也不改变 SearchResponse | 处理资产/API 版本错配且保持搜索状态、Count、分页和记录身份 |
| CC17-1-DEC-015 | 模式切换复用既有 pending edit、Publish/Apply、checksum 和审计；失败时旧 Snapshot 保持有效 | 不引入迁移/注册架构并保证活动配置原子性 |
| CC17-1-DEC-016 | 模板常量按配置原文显示，字段值按当前用户 locale/timezone 格式化 | 与 CC-014 DEC-020 及 CC-009 保持一致，不引入自动翻译 |
| CC17-1-DEC-017 | 日志只复用 CC-008 事件和 allowlist，不新增 mode 字段或敏感内容 | 避免超出冻结日志契约或暴露用户业务数据 |
| CC17-1-DEC-018 | 浏览器版本/viewport、性能结果和人工 HVR 必须实际测量后记录 | 评审计划不是验证证据，防止未执行项目被误报通过 |

## 17. Implementation Structure

以下是实现落点建议，不授权超出本 CC 的文件或系统范围：

| 路径 | 建议职责 |
|---|---|
| `mymodules/wd_global_search/models/configuration.py` | Resource 结构化配置字段、互斥检查、复用既有 Publish/Apply 与 Snapshot 生命周期 |
| `mymodules/wd_global_search/services/template.py` | 复用 parser/validator；为结构化区域提供聚合预算校验和可安全投影的 loop 结果，不改变旧 renderer 语义；沿用当前用户 locale/timezone formatter |
| `mymodules/wd_global_search/services/card.py` | 当前用户授权下渲染四区、明细列表和 truncation 标志；不得将渲染内容写入新增日志字段 |
| `mymodules/wd_global_search/services/executor.py` | 按显式 mode 生成 `snapshot.card`，保留 `rendered_text` / `fields` 分支 |
| `mymodules/wd_global_search/static/src/js/preview.js` | `snapshot.card` schema 检查、独立文本 DOM；未知版本卡片级安全提示；旧 mode 行为不变 |
| `mymodules/wd_global_search/tests/test_structured_card.py` | schema、Publish、权限、details、多语言、原子切换、allowlist 和分阶段性能测试 |
| `mymodules/wd_global_search/tests/test_backward_compatibility.py` | `rendered_text`、`snapshot.fields` 和错误/Count/page 回归 |
| Browser / Playwright tests | 确定性结构/legacy fixtures、恶意文本、浏览器矩阵和 DOM 自动化；人工 HVR 证据另行签署 |

不得新增后台 worker、队列、缓存服务、数据库直连、外部依赖或独立配置架构。实际实现文件可按现有代码结构调整，但每项调整必须仍满足契约接口和边界。

## 18. Appendix

### 18.1 SRS / TDD Traceability

| 上游依据 | 本 CC 追溯 | 限制 |
|---|---|---|
| SRS v1.5 FR-SW-003 Snapshot | §4–§9、§12 | 新对象是 Snapshot 的 additive 表现；不更改可搜索集合或结果身份 |
| SRS v1.5 Business Resource / Published Configuration | §4、§11 | 配置仍属于 Business Resource 并随 Published Snapshot 生效 |
| SRS v1.5 BR-006~BR-008 / Search permission constraints | §9、§13 | 当前用户权限始终有效，Count 和结果权限不变 |
| TDD v0.4 SearchService → SearchResponse | §5、§7 | 只新增结构化模式下的 snapshot 子对象，不改 request 或分页协议 |
| TDD v0.4 Published Snapshot/checksum/Apply | §4、§11 | 复用既有原子 Apply 和 checksum 生命周期 |
| TDD v0.4 authorization/error/security flow | §9、§11、§13 | 复用 permission boundary、ORM 和错误 envelope |
| TDD v0.4 UI/browser validation | §6、§12、§15 | 新 DOM 必须有自动化及人工 HVR 证据 |

本 CC 不重解释 SRS FR-SW-006 的 Resource Count/summary；本文件中的卡片 `summary` 是 Result Card 文本区域，不是 Count API。

### 18.2 Interfaces with Existing Contracts

| 接口 | CC-017-1 承诺 |
|---|---|
| Resource configuration → Published Snapshot | 新 `structured_card_template` 与原 Resource Snapshot 同生命周期、原子校验 |
| SearchService → response | 结构模式用 `snapshot.card`；原模板用 `snapshot.rendered_text`；历史 fields-only 用 `snapshot.fields` |
| Search result → frontend | 每条结果通过 Resource 配置决定模式；模式不可由文本推断 |
| Permission boundary → rendered values | 每次请求按当前 user/company/ACL/record rule/field access 检查 |
| Details → UI | 最多三项，稳定顺序，`details_truncated` 由更多可见项决定，UI 用 `...` |
| Errors → client | 保持 CC-007 既有 error/status/envelope，不新增成功形状的 fallback |
| Card → navigation | 保持 CC-013 的目标 Action、二次授权、键盘/点击/新 Tab 行为 |
| Structured DOM → styling | 由 CC-017 提供既有视觉规则；本 CC 不定义新的字号、色值、spacing 或分页样式 |

### 18.3 Glossary

| 术语 | 含义 |
|---|---|
| Structured Card | 使用 `snapshot.card` 显式输出语义区域的 Result Card |
| Region | `title`、`meta`、`summary` 或 `details` 中的一个模板化区域 |
| Structured Details Item | One2many loop 中单条当前用户有权读取、输出为一个字符串的明细 |
| `details_truncated` | 至少还有一个可见明细未放入前三项的布尔标记，不含剩余总数 |
| Legacy plain-text mode | CC-014/014-1 的 `card_template` → `snapshot.rendered_text` |
| Legacy fields mode | 历史无 template Snapshot → `snapshot.fields` |
| Mode inference | 从 Label、文字、分隔符或值内容猜卡片角色；本 CC 禁止 |

### 18.4 Version History

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-14 | 初稿；采用 Resource 级显式对象、复用现有模板语法、明细 loop 最多输出 3 项并标记截断 | DRAFT / SUPERSEDED |
| v1.0 | 2026-10-14 | 纳入评审修订：基线与核对声明、schema mismatch、原子模式切换/迁移、多语言、日志边界、fixture、浏览器/viewport、性能门槛、HVR 验收；用户批准冻结并授权实施 | APPROVED / FROZEN |
| v1.0.1 | 2026-10-14 | 按用户批准修正示例中 datetime 字段的格式键为 `datetime`；不改变执行契约 | APPROVED / FROZEN |

### 18.5 Review Record

- 2026-10-14：用户评审后要求纳入补充并批准冻结进入实施；本版本记录该批准。
- 实施测试、性能数据和人工 HVR 尚待完成；详见 §12 和 ATR/HVR，不由冻结状态推定为 PASS。
