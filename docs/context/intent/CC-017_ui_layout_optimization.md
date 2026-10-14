# CC-017 UI 子目标 — Search Workspace 排版优化

## 0. Governance

| 字段 | 值 |
|---|---|
| 文档类型 | CC-017 UI 子目标意图（不是独立 Coding Contract） |
| 版本 | v0.4 |
| 状态 | APPROVED / FROZEN；已授权视觉样式、完整 Workspace 顺序及三个默认收缩分区；卡片语义重排仍受 §17 阻塞 |
| 子目标 ID | `CC17-UI-LAYOUT` |
| 兼容基线 | [CC-016 v0.2 FROZEN](./CC-016_condition_builder_visualization.md) |
| 上游基线 | SRS_global_search v1.5 FROZEN；TDD_global_search v0.4 FROZEN |
| 前置契约 | CC-001~CC-016、CC-014-1、CC-014-2 |
| 前置状态 | CC-015 已由 [FR v0.1](../history/FR-GS-MULTI-CONDITION-SEARCH.md) 判定 SATISFIED；不代表本子目标已批准 |
| 模块 | `wd_global_search` |
| 目标 | 按 Search Workspace、Search query、Resource Selector、Search by field、Date and state filters、Query Understanding、Accessible records 的顺序展示；三个条件/理解分区默认收缩且可展开/收缩，不改变搜索语义 |
| 批准 / 冻结 | 用户于 2026-10-14 批准视觉样式和交互顺序；Search by field、Date and state filters、Query Understanding 默认收缩；当前 v0.4 已冻结 |

**治理边界：** 本文件定义本轮 CC-017 的排版优化 UI 子目标，不新增独立 CC、业务行为、Search API、Published 配置或搜索语义。CC-016 是上一轮已冻结的兼容基线；本文件不得修改、取代或重新解释 CC-016、CC-015、CC-014-2。`CC17-UI-DEC-*` 与 `CC17-UI-TEST-*` 仅为本子目标的追溯 ID，不是新增的 CC-DEC 或父契约测试 ID。

## 1. Purpose

**一句话目标：** 参照 Google 搜索结果页的层级、留白和简洁视觉组织现有 Search Workspace，按用户指定顺序排列七个区域，并让 Search by field、Date and state filters 与 Query Understanding 默认收缩、可由用户展开，同时完全保留 CC-016 条件构建契约和既有搜索行为。

关键词 chip、字段选择器、条件分区及其搜索行为仍以 CC-016 v0.2 为唯一契约；折叠状态和资源位置只影响 Workspace 展示，不改变搜索请求或结果。

## 2. Background and Findings

### 2.1 起草前实际页面核对

2026-10-14 在内置 Chromium 的当前授权浏览器页面只读观察：

| 项 | 实际观察 |
|---|---|
| 页面 | `http://127.0.0.1:8091/wd_global_search`，共享页面 ID `1b6d6f2f-0ea2-4e3b-8314-ed76bd8193c2` |
| 场景 | 提交 `001 chair`；Sales Order 结果数 11；显示 `Showing 1–10 of 11` |
| 页面截图 | 本会话截图显示 Search Workspace、折叠的 Date and state filters、Query Understanding、首张结果卡片及分页；没有另存截图文件 |
| 首张结果 | `S00001`；客户 `Acme Corporation`；总金额 `1,740.00 €`；日期 `Sep 1, 2026, 3:43:00 PM` |
| 明细样例 | 产品名、`数量：`、`单价：`、`金额：`以 `-` 与 `|` 混排在长行中 |
| 操作范围 | 只读 Search API / 页面观察；未读写数据库、未改业务数据或 Published 配置、未使用 `sudo()` |

页面计算样式和 Workspace DOM 的核验结果（此项测量仅对应本次浏览器视口，`body` 宽 784 CSS px、高 856 CSS px）：

| 元素 | 当前实测 |
|---|---|
| 全局字体 | `Inter, system-ui, sans-serif`；正文 16px |
| 页面 H1 / 分区 H2 | H1 28px / 700；H2 18px / 700；颜色 `#243447` |
| 模板卡片正文 | `snapshot.rendered_text` 渲染为单一 `.wd-card-template-text` 文本块，16px / 400；字段名、字段值继承相同样式 |
| Query Understanding | 13px / 400，颜色 `#6b7785`；位于结果区之前，但标签和条件摘要同一行 |
| 结果卡片 | 1px `#dfe5ec` 边框；本视口 `padding: 12px`、顶部间距 12px；卡片本身 `box-shadow: none` |
| 外层面板 | Workspace 的 header/query/refinement/understanding/layout 面板有浅边框及 `0 2px 8px rgba(29, 48, 68, .06)` 阴影 |
| 分页 | 保留 Rows per page、Showing 和 First/Previous/页码/Next/Last；按钮高 34px、圆角 6px，当前页紫色高亮；按钮计算字体为 Arial，而正文为 Inter |

### 2.2 问题核对

| # | 用户指出的问题 | 核验结论 |
|---:|---|---|
| 1 | 整屏几乎只有一种字号、层级没有拉开 | **部分成立。** 页面存在 28/18/16/13px 的基础字号，但卡片正文及字段名/值集中为 16px，缺少卡片标题、摘要和辅助信息层级。 |
| 2 | 卡片内容全部挤成一行，没有标题 + 摘要 | **部分成立。** 卡片文本按换行显示，但内容是未分层的模板文本；每条明细仍是一条很长的混合字段行。 |
| 3 | 缺少主标题，第一眼是字段名：字段值 | **成立。** 首张卡片第一行是 `订单编号：S00001`，没有独立视觉标题。 |
| 4 | 字段名和值没有视觉区分 | **成立。** 模板文本以同一个 DIV、同一字号和字重呈现。 |
| 5 | 明细像日志，分隔符混用 | **成立。** 实测明细使用行首 `-`，字段之间用 `|`，且字段名与数量/价格/金额并列。 |
| 6 | Query Understanding 缺少辅助信息层级 | **部分成立。** 其 13px 确实小于卡片 16px；但它已经在结果列表之前，调整重点是视觉样式而非移动位置。 |
| 7 | 卡片和内部间距偏小 | **成立（本次视口）。** 卡片顶部间距 12px、内部 padding 12px；明细行呈现为紧凑长文本。 |
| 8 | 字体不统一 | **成立（控件层）。** 正文为 Inter 栈，分页按钮计算字体为 Arial。 |
| 9 | 卡片边框和阴影使视觉偏重 | **部分成立。** 结果卡片有 1px 边框但自身没有阴影；外层 Workspace 面板才有浅阴影。不可把现状记录成“结果卡片有阴影”。 |
| 10 | 分页样式与 Odoo 原生不一致 | **需限定。** 当前是独立 Workspace 的自定义按钮，视觉为 6px 圆角、当前页紫色；本次未与 Odoo webclient 控件做并排视觉验收。目标是采用简洁、一致的分页样式，不声称已验证某个 Odoo 原生 widget。 |
| 11 | 页面分区未按用户指定顺序排列 | **成立。** 冻结顺序为 Search Workspace → Search query → Resource Selector → Search by field → Date and state filters → Query Understanding → Accessible records。 |

### 2.3 卡片结构可实现性边界

本次读取到的客户端渲染路径表明：有 `card_template` 的结果以 `snapshot.rendered_text` 作为一个字符串返回，前端将其放入单个 `.wd-card-template-text` 元素；只有无 template 的结果才使用 `snapshot.fields`。因此，当前 Sales Order 卡片没有可供 CSS/JS 安全区分的标题、日期、客户、金额和明细字段节点。

**数据边界：** 不解析 `rendered_text`、不以标签文案或分隔符猜测字段语义；若卡片语义重排或明细摘要无法从现有 DOM 安全完成，必须停止，不得扩大到 service/model 或 SearchResponse 修改。§4–6 的卡片语义布局是期望视觉目标，不是对当前文本协议的解析授权。用户已批准只在 controller 的现有 HTML 模板中使用原生 disclosure markup 和调整现有块顺序；不得修改 controller 逻辑。用户于 2026-10-14 批准 v0.1 视觉样式，随后要求 Search by field 与 Query Understanding 默认收缩、可展开/收缩，并将可选资源放在 Search query 下方。用户于 2026-10-14 批准冻结本意图，并授权先实施不依赖卡片数据结构的视觉样式。

### 2.4 参照原则与非目标

本子目标将用户提供的 Google 搜索结果页排版作为视觉参照，不复制品牌资产，不引入外部依赖，不要求像素级仿制。**不修改 CC-016 的契约内容，不增加搜索语义，不改变 CC-015 或 CC-014-2 `field_path`。**

## 3. Typography Scale

以下是目标样式。字号、字重和颜色只控制视觉表达；不代表链接、字段权限或结果身份发生变化。

| 层级 | 用途 | 字号 | 字重 | 颜色 |
|---|---|---:|---:|---|
| H1 | 页面标题 `Search Workspace` | 32px | 400 | `#202124` |
| H2 | 分区标题 `Accessible records` | 20px | 500 | `#202124` |
| H3 | 结果卡片主标题 | 20px | 400 | `#1a0dab` |
| Body | 卡片摘要/主要内容 | 14px | 400 | `#4d5156` |
| Meta | Resource、日期等辅助信息 | 12px | 400 | `#70757a` |
| Label | 必须保留的字段名 | 12px | 500 | `#70757a` |
| Value | 字段值 | 14px | 400 | `#202124` |

**层级不变量：** H3 大于 Body；Body 大于 Meta；Label 不得与 Value 混成无法区分的一串同样式文本。若浏览器默认样式覆盖这些值，必须由 CSS 明确设置并以计算样式测试确认。

## 4. Card Structure

### 4.1 目标层级

结构化卡片数据可安全映射到独立 DOM 节点时，目标显示顺序为：

```text
S00001                                      主标题 / H3
Sales Order · Sep 1, 2026                  Meta（Resource · 日期）
Acme Corporation · 1,740.00 €              摘要 / Body（客户 · 总额）
Acoustic Bloc Screens × 3 · Office Lamp × 5 · Office Chair × 2
                                              明细摘要
```

映射关系：

| Google 结果页角色 | Workspace 卡片角色 |
|---|---|
| 标题 | 当前已发布卡片数据中的主标识（如订单编号） |
| URL / 来源行 | Resource 与可用日期等 Meta；不是新的真实 URL 或导航目标 |
| 摘要 | 客户、总额等现有摘要字段 |
| 摘要续行 | 当前已显示的明细项摘要 |

### 4.2 兼容边界

- 主标题只使用当前结果中已可见、已授权的字段；不得增加结果字段或查询字段。
- Resource、日期、摘要及明细只能来自当前 SearchResponse / 已批准的显示字段；不得通过新的 ORM 读取、客户端请求或 Published 配置猜值。
- 蓝色是视觉色彩，不能新增 anchor、改变单击/双击/键盘行为、导航 Action 或可访问性角色。
- 当前结果由 `rendered_text` 提供且无法可靠分区时，禁止用正则、冒号、`|`、换行、字段名或语言文案进行解析；按 §17 停止。

## 5. Field Name and Value Separation

- 主标题字段可不显示冗余 Label，**前提是**它由已有的稳定字段结构明确标识为主标识，而非从文本内容猜测。
- 其他字段若 Label 对理解值仍有帮助，则显示 12px、500 字重、灰色 Label，Value 用 14px 正常字重；Label 与 Value 使用独立 DOM 节点。
- 只有明确无歧义的已批准字段可省略 Label；不得全面删除 Label 造成数字、日期或状态含义不明。
- 不改变 Label 的来源、语言、权限过滤、格式化或显示顺序。
- 当前模板卡片只有一个 `rendered_text` 文本节点，无法安全完成上述语义拆分；此限制不由本节放宽。

## 6. Detail Row Format

目标是将每条明细表示为精简摘要，例如：

```text
Acoustic Bloc Screens × 3 · Office Lamp × 5 · Office Chair × 2
```

- 移除紧凑摘要里的重复 Label（如“数量：”“单价：”“金额：”），以 `×` 表示数量、`·` 分隔项目。
- 摘要优先保留已有且可安全识别的产品名与数量；不新增价格、金额、税额或其他字段读取。
- 默认最多展示 3 个明细项；更多项目以 `...` 结尾。省略仅影响卡片摘要展示，不删除结果数据；原配置表单的既有查看能力不变。
- 若不能无歧义地区分名称、数量和金额，或省略会隐藏当前契约要求保留的卡片信息，必须停止；不得拆解任意模板字符串。

## 7. Query Understanding Style

- 位于结果列表之前，保持 CC-005/CC-016 现有区域顺序；不把 Query Understanding 移到搜索框或筛选器之上。
- 使用 14px、400 字重、`#4d5156`，作为轻量辅助说明；标签与摘要可以分开，但不得加重为主标题。
- 示例：`About 11 results · keywords: 001 AND chair`。Count 必须取自现有 SearchResponse，不得客户端估算或自行计数。
- “About X results”仅用于现有响应可显示有效 Count 的状态；空、部分失败、整体失败、超时或无效查询继续按 CC-002/005/007/015 显示原状态，不伪造成功摘要。
- 条件摘要、关键词顺序、AND/同维度 OR 表达和错误处理继续服从 CC-016、CC-015 与 CC-005；只改变排版。

## 8. Spacing

| 位置 | 目标间距 |
|---|---:|
| 结果卡片之间 | 28px |
| 卡片内部默认间距 | 8px |
| 主标题与 Meta/URL 行 | 4px |
| Meta/URL 行与摘要 | 4px |
| 主标题到摘要（两段间隔合计） | 8px |
| 摘要与明细摘要 | 8px |

上述值是目标 CSS 间距；标题至摘要的总视觉间隔为 8px，其中 Meta/URL 行位于两者之间，且摘要与 Meta/URL 行相距 4px。组件层级与 DOM 若不能安全确定，不以负 margin、伪元素或字符串换行模拟语义层级。窄屏可调整外层布局，但不得挤压文字、隐藏必要控件或改变交互。

## 9. Font

全 Workspace 使用统一字体栈：

```css
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
```

- Body、button、input、select、pagination 和结果文本均显式继承统一字体。
- 不依赖某台设备安装 `Google Sans`，不下载 web font，不引入外部字体资源。
- 字体只影响视觉；不得改写内容、语言来源、日期/数字格式或字段值。

## 10. Color

| 用途 | 目标颜色 | 限定 |
|---|---|---|
| 标题视觉色 / 交互卡片主标识 | `#1a0dab` | 只改变颜色，不新增链接行为 |
| 已访问链接 | `#660099` | 仅适用于当前 UI 已有真实链接；不新增访问历史 |
| URL | `#006621` | 仅用于真实 URL；Resource/date Meta 不伪装成 URL |
| 正文主文字 | `#202124` | H1/H2/Value |
| 摘要 | `#4d5156` | Body / Query Understanding |
| Meta / Label | `#70757a` | 辅助信息与字段名 |
| 分隔线 | `#dadce0` | 非卡片边框的弱分隔 |
| 背景 | `#ffffff` | 内容表面 |

不得改变错误、权限、选中、焦点、禁用或结果状态的既有可辨识状态。颜色之外必须保留现有可访问的状态提示。

## 11. Card Border and Shadow

- 目标结果卡片不使用边框和阴影；以 28px 间距和内容层次分卡。
- 本次实际页面核验到结果卡片有 `1px solid #dfe5ec` 边框，但没有卡片自身阴影；外层 Workspace 面板有浅阴影。后续实现应分别处理，不得把外层面板误认作卡片阴影。
- 不在结果卡片上增加 hover 阴影。可保留必要的键盘焦点、选中态和可见状态反馈。
- 本节不授权删除 Workspace 外层结构边界；若需要删除外层边框/阴影或改变布局容器，应先补充影响评审。

## 12. Pagination

- 保留 `Rows per page`、`Showing X–Y of N`、First/Previous/Next/Last 与页码的现有语义和显示信息。
- 按钮视觉可用圆形或方形；建议统一为清晰的方形/轻圆角按钮，并突出当前页。
- 字体继承全站字体栈；禁用、焦点、当前页状态保持可辨识和键盘可用。
- 不改变页大小选项、Count、页码、offset/cursor、导航顺序、请求次数或无结果状态。
- 按钮采用统一方形轻圆角，目标 `border-radius: 4px`；当前页使用蓝色背景和白色文字突出。本稿不采用改动分页语义的 Google 品牌图形。

## 13. CC-016 Compatibility Baseline

- 不修改 CC-016 v0.2 冻结契约内容、关键词 chip 编辑规则或服务端 parser 权威。
- 不改变字段选择器的候选来源、权限过滤、标签到完整 Published `field_path` 的映射、operator/value 约束。
- 不改变 Query Understanding 的关键词 / structured conditions / Refinement 分区、有效条件来源、AND/OR 说明或失败状态规则。
- 不把 CSS 布局分区实现成新的条件分区协议；不新增 SearchRequest/Response 字段、route、descriptor 或配置 schema。
- 关键词 chips、字段选择器、条件分区的现有功能、无障碍操作和 CC16-TEST-001~027 回归必须保持。

## 14. CC-015 Compatibility

- 不改变多词 Contains-on-text、token AND、单 token 兼容、结构化条件、错误拒绝或 Unicode 规则。
- 不改变当前用户/公司权限、关系 hop、Record Rule、Resource scope、Result Identity 或 Count。
- 不改变分页、cursor 绑定、部分成功、错误码、Query Understanding 有效条件或审计/日志行为。
- 不将日期、状态、卡片摘要或可视化 chips 转成 Raw Query token 或新的 `conditions[]`。
- 不改变 CC-014-2 `field_path`、关系深度、末端类型、operator_set、`collection_match` 或 Published 校验。

## 15. Test Matrix

`CC17-UI-TEST-*` 是本子目标本地测试 ID，不取代 CC-016 的 CC16-TEST-001~027。浏览器测试使用现有授权 Workspace 与既有 Search API，不新增接口、不写业务数据。

| 测试 ID | 类型 | 操作 / 测量 | 预期 / 判定 |
|---|---|---|---|
| CC17-UI-TEST-001 | 浏览器 + computed style | 测量 H1/H2/H3/Body/Meta/Label/Value 的计算字号、字重、颜色 | 每个角色符合 §3；H3 > Body > Meta；不以截图主观感受代替样式值 |
| CC17-UI-TEST-002 | 浏览器 DOM + SearchResponse shape | 打开 template-based 结果卡，检查是否有可明确区分的主标题、Meta、摘要、明细节点 | 若响应只有 `snapshot.rendered_text`，结果必须为 STOP/BLOCKED；不得正则解析后记 PASS |
| CC17-UI-TEST-003 | 浏览器 | 对可结构化的字段卡检查 Label/Value DOM、计算样式和标题 Label 省略条件 | Label/Value 分离；只在无歧义时隐藏冗余 Label；Label 来源和可见字段不变 |
| CC17-UI-TEST-004 | 浏览器 + fixture | 检查明细项分隔符、最多 3 项显示与 `...` | 结构数据可安全映射时显示 `名称 × 数量 · ...`；超 3 项有省略标记；只有任意文本时必须 STOP |
| CC17-UI-TEST-005 | 浏览器 + computed style | 检查 Query Understanding 在结果列表前的位置、14px/`#4d5156` 和响应 Count | 样式/位置达标；About X 使用响应 Count；错误、timeout、无效查询无成功式伪摘要 |
| CC17-UI-TEST-006 | 浏览器 + bounding box | 测量卡片间距、内部间距、主标题/Meta、Meta/摘要、摘要/明细间距 | 分别符合 28px、8px、4px、4px、8px；主标题至摘要总间隔 8px；窄屏无溢出或控件遮挡 |
| CC17-UI-TEST-007 | 浏览器 + computed style | 比较 body、结果卡、Search 输入、button、select、分页字体 | 都使用 §9 字体栈；不出现默认 Arial 与正文混用 |
| CC17-UI-TEST-008 | 浏览器 + computed style | 检查标题、正文、Meta、Label、Value、分隔线、背景颜色 | 对应 §10 色值；选中、禁用、焦点、错误状态仍可辨识 |
| CC17-UI-TEST-009 | 浏览器 + computed style | 检查结果卡 border/box-shadow、间距和外层容器样式 | 结果卡无边框/阴影并通过留白区分；外层容器未被意外拆除 |
| CC17-UI-TEST-010 | 浏览器交互 + computed style | 改变页大小、翻页并检查按钮形状、当前页、禁用态 | `border-radius: 4px`；当前页蓝底白字；Rows per page/Showing/页码功能、Count 与结果身份不变；键盘可操作 |
| CC17-UI-TEST-011 | 浏览器回归 | 执行 CC-016 keyword chip、字段选择器、条件分区的必需场景 | CC16-TEST-001~027 适用场景保持；Raw Query 和 `conditions[]` 请求不被排版代码改写 |
| CC17-UI-TEST-012 | API/浏览器回归 | 比对样式优化前后的多词、单词、Count、分页/cursor、错误和资源权限结果 | 请求语义、响应状态、Count、Result Identity、权限与错误行为一致 |
| CC17-UI-TEST-013 | 浏览器兼容性矩阵 | Chrome、Firefox、Safari、Edge × Desktop、Tablet、Narrow | 字号、换行、对比、焦点、分页和卡片结构无遮挡、溢出或不可操作；逐项记录浏览器版本/视口 |
| CC17-UI-TEST-014 | 浏览器 + 键盘 | 首次加载后检查 Search by field、Date and state filters、Query Understanding 的默认状态，并分别用指针和键盘切换 | 三者初始均收缩；原生 disclosure 可展开/收缩、焦点可见；内部条件值保留 |
| CC17-UI-TEST-015 | 浏览器 DOM | 检查七个 Workspace 区域的文档顺序 | Search Workspace → Search query → Resource Selector → Search by field → Date and state filters → Query Understanding → Accessible records；窄屏顺序一致 |
| CC17-UI-TEST-016 | 浏览器 + 请求断言 | 只切换两个 disclosure 并观察 Search API、Raw Query 与 conditions[] | 折叠/展开不发起搜索、不改写输入或条件、不改变结果和分页状态 |

## 16. Regression Requirements

- **CC-002~CC-005：** 保留 SearchRequest、Raw Query/Refinement 分离、合并、Count、分页、cursor、状态机和键盘/屏幕可理解性。
- **CC-006~CC-009：** 保留导航、Resource/字段权限、错误聚合、服务端语言/时区和 Query Understanding 安全行为。
- **CC-010~CC-015：** 保留 Published Snapshot、Resource 选择、Card/关系字段显示、field_path、Contains、单词兼容、审计与边界验证。
- **CC-016：** 关键词 chip、字段选择器、条件分区、授权可见性、操作符映射、搜索状态和禁止语义继续通过 CC16-TEST-001~027。
- **CC-014 / CC-014-1：** 本子目标不得以“摘要简化”为由更改已发布 Card 字段权限、模板执行、关系路径权限、表单 Action、导航或一对多数据权威；展示截断仅为卡片视觉呈现。
- **当前结构限制：** 由于 template-based `snapshot.rendered_text` 当前是单一文本节点，CC17-UI-TEST-002/004 不得以字符串猜测取得 PASS；按 §17 升级。

## 17. Stop Conditions

出现以下任一情形，停止相关实现并返回用户/契约评审，不得静默绕过：

1. H1/H2/H3/Body/Meta 等字号层级无法通过 DOM 和计算样式验证。
2. 卡片标题、Meta、摘要和明细无法从现有稳定 DOM/结构数据区分；特别是只收到 `snapshot.rendered_text` 时，禁止解析文本猜语义。
3. 字段 Label/Value 分离需要读取当前 SearchResponse 未提供的字段，或需要修改 `controllers/main.py`、`services/`、`models/` 才能取得数据。
4. 明细格式优化需要解析任意 template 字符串、推断语言标签、改变 Published Card Template 或丢弃权限过滤字段。
5. 去掉字段名、价格或明细会改变 CC-014/CC-014-1 明确要求的显示内容，或无法保证完整详情仍可从既有表单访问。
6. Query Understanding 样式要求更改 Raw Query、有效条件、Count、状态、错误或条件分区。
7. 分页样式要求改变 page size、Count、offset/cursor、请求节奏或页码结果。
8. 需要修改 CC-016、CC-015、CC-014-2、SRS、TDD、Published schema，或新增搜索/网络协议。
9. 需要 `sudo()`、直接数据库读写、业务数据读取补字段，或修改 `odoo/` / 官方 `addons/`。
10. 需要 Elasticsearch、OpenSearch、LLM、向量检索、外部字体/API 或其它新搜索架构。
11. 浏览器兼容性、键盘/焦点或窄屏布局无法满足且修复要求扩大当前 UI-only 边界。

## 18. Definition of Done

只有本子目标获批且以下适用证据齐备后，方可标记完成：

- H1/H2/H3/Body/Meta/Label/Value 层级及指定字号、字重、颜色经 computed style 验证。
- 卡片结构、字段名和值分离、明细摘要分别通过 §15 的 DOM/数据契约测试；不得把从 `rendered_text` 猜测出的结果算作通过。
- Query Understanding 使用 14px 灰色辅助样式并位于结果列表上方；错误、空结果、部分失败行为不变。
- 卡片间距 28px、内部间距 8px、标题/摘要 8px、摘要/Meta 4px 通过可复核测量。
- 全站字体栈、颜色、结果卡边框/阴影、分页样式符合 §§9–12；用户交互和焦点状态保留。
- 页面按七个规定区域顺序展示；Search by field、Date and state filters 与 Query Understanding 初始收缩且可通过键盘/指针展开、收缩；切换不触发 Search API 请求或改变条件状态。
- CC-016、CC-015、CC-014、CC-014-1、CC-014-2 适用回归通过；无新增 Search API 或查询语义。
- §15 Test Matrix 有实际执行记录；浏览器/版本/视口逐项记录；不得将 STOP/BLOCKED 标作 PASS。
- IHR、ATR 和适用 HVR 记录实现、回归和人工视觉验收；证据只覆盖实际运行的代码和页面。
- 未修改官方 Odoo 代码、数据库、业务数据、Published schema、services、models 或 controller；未引入禁止依赖。
- 父 CC-016 契约未被修改；最终 Closure 由 FR 评估，本子目标和自动化截图不替代 HVR/FR。

**当前已知闸门：** 现有 template-based 结果只有 `rendered_text`；在不扩展 CSS/JS-only 边界的前提下，卡片结构、Label/Value 分离和明细摘要仍为 STOP 条件。除非实现时现有 DOM 已提供可识别结构，不能宣称上述三项 DoD 已满足。

## 19. Decisions

以下 `CC17-UI-DEC-*` 已随本子目标于 2026-10-14 获用户批准并冻结；不修订父 CC-016。结构化卡片目标仍受 §17 的实现停止条件约束。

| Decision ID | 决定 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC17-UI-DEC-001 | 采用 §3 的 7 级字号层次。 | 保持当前 28/18/16/13px 粗粒度层级。 | 让页面标题、结果标题、正文和辅助信息可快速扫读。 |
| CC17-UI-DEC-002 | 结果卡片的目标是标题、来源/日期 Meta、摘要和明细摘要。 | 保持一段同字号模板文本。 | 对齐搜索结果页常见扫描顺序；仅在现有结构数据可用时实施。 |
| CC17-UI-DEC-003 | 主标识可省略冗余 Label；其它字段默认以小灰 Label 和正常 Value 区分。 | 隐藏所有字段名或保留全部同样式文本。 | 保留可读性，避免日期/金额/状态失去语义。 |
| CC17-UI-DEC-004 | 明细摘要用 `×`、`·`，最多三项后用 `...`。 | 全量展示 `-`、`|` 与数量/单价/金额标签。 | 将长明细转成紧凑摘要；不删除数据，且仅在结构可安全识别时实施。 |
| CC17-UI-DEC-005 | Query Understanding 以 14px 灰色显示在结果列表之前，并引用服务端 Count。 | 保持当前 13px inline 样式或移动到搜索区。 | 强化辅助说明，保持语义和现有区域顺序。 |
| CC17-UI-DEC-006 | 使用 28px 卡片间距、8px 内距、8px 标题/摘要间隔及 4px 摘要/Meta 间隔。 | 保持紧凑的 12px 卡片间距。 | 增加卡片分组和内容呼吸空间。 |
| CC17-UI-DEC-007 | Workspace 全部控件显式继承指定系统字体栈。 | 仅设置正文根字体，保留 UA button 字体。 | 消除当前正文 Inter、分页按钮 Arial 的不一致。 |
| CC17-UI-DEC-008 | 使用 §10 的中性 Google-inspired 色板。 | 保留当前紫灰色主题色。 | 建立标题、摘要、辅助信息和背景的阅读层次；不复制品牌资产。 |
| CC17-UI-DEC-009 | 结果卡取消自身边框/阴影，以留白分组；不自动移除 Workspace 容器边界。 | 保留每卡边框或删掉所有外层分隔。 | 当前结果卡确有边框但无自身阴影；差异化处理可避免过度清除布局结构。 |
| CC17-UI-DEC-010 | 保留分页信息与行为；按钮统一为 `border-radius: 4px` 的方形轻圆角样式，当前页蓝底白字。 | 改为 Google 风格页码图形或重写分页结构。 | 保留 Odoo 用户熟悉的 Rows per page / Showing 和既有键盘、Count、cursor 行为，同时让分页控件简洁一致。 |
| CC17-UI-DEC-011 | Search by field 与 Query Understanding 使用原生 disclosure，默认收缩且允许用户展开/收缩。 | 默认展开或由 JS 手工模拟折叠。 | 满足用户要求并保留键盘可操作性；不改变搜索条件或请求。 |
| CC17-UI-DEC-012 | Resource Selector 紧随 Search query，位于 Search by field 之前。 | 保持原有顺序。 | 用户可在设置字段条件前选择目标资源；仅调整现有界面块顺序。 |
| CC17-UI-DEC-013 | Workspace 按 Search Workspace、Search query、Resource Selector、Search by field、Date and state filters、Query Understanding、Accessible records 顺序展示。 | 保持之前的布局顺序。 | 用户明确指定各交互区与结果区的扫描顺序；不改变各区内部搜索语义。 |

## 20. Implementation Structure

本节是 UI-only 边界；本意图已获批准，按表中职责实施。

| 现有位置 | 允许的职责 | 禁止事项 |
|---|---|---|
| `mymodules/wd_global_search/static/src/css/preview.css` | 字号、字体、颜色、间距、边框/阴影、分页按钮视觉样式、原生 disclosure 展示 | 不以伪元素/换行伪造字段语义 |
| `mymodules/wd_global_search/static/src/js/preview.js` | 当前获批视觉范围不需要修改 JS | 不解析 `snapshot.rendered_text`、不合成数据、不修改 SearchRequest/Response、不改条件或分页行为 |
| `mymodules/wd_global_search/tests/` | 验证计算样式、DOM层级、响应保持、键盘和浏览器矩阵 | 测试不读写共享业务数据，不使用 sudo，不依赖未发现的测试文件 |

`controllers/main.py` 只允许在现有 HTML 模板中加入原生 disclosure 结构、重排 Resource Selector 和 Search by field，并将 `preview.css` 静态资源 URL 更新为 `cc017-v03` 以绕过已核实的 7 天浏览器缓存；不得修改 controller 逻辑、Search API 或响应。仍禁止修改 `services/`、`models/`、Views/Published schema、`odoo/` 或官方 `addons/`。若当前接口无法提供卡片语义层级所需的结构化节点，按 §17 停止；本稿不授权补充 adapter，也不授权从数据库/服务端额外取值。

## 21. Appendix

### 21.1 SRS / TDD Traceability

| 上游 | 追溯项 | 本子目标关系 |
|---|---|---|
| SRS_global_search v1.5 | FR-SW-001~003 | 仅调整现有 Search Workspace 展示；不改变 Resource/Search 行为 |
| SRS_global_search v1.5 | FR-RF-001~009 | 保持既有 Refinement 展示状态与输入语义 |
| SRS_global_search v1.5 | FR-QU-001、BR-006~008 | 条件摘要视觉增强；仍按服务端已完成的有效条件显示 |
| TDD_global_search v0.4 | §3.4 | Raw Query、Parsed Conditions、Refinement 合并仍由既有 Effective Conditions 流程负责 |
| TDD_global_search v0.4 | §6.5 | 不改变服务端权限和失败关闭 |
| TDD_global_search v0.4 | §§8、10 | 只调整 Workspace 的表现层，不修改服务端 ORM/执行流程 |
| TDD_global_search v0.4 | §12.5 | 通过浏览器和适用 HVR 检查 UI，不以截图替代契约回归 |

### 21.2 与 CC-016 / CC-015 的接口契约

| 接口 | 保持项 |
|---|---|
| Raw Query | 原始字符串原样交给 CC-015；不新建 tokenizer 或语法 |
| 关键词 chips | 完全沿用 CC-016 chip 与既有 parser 行为 |
| `conditions[]` | 外层结构、完整 Published `field_path`、operator/value 不变 |
| SearchResponse | 继续消费既有 `results`、`counts`、`effective_conditions`、`errors`、cursor 等；不增字段 |
| `snapshot.rendered_text` | 保持原样呈现；禁止将任意配置文本解析成标题、Label、Value 或明细字段 |
| Card selection/navigation | 点击、双击、Enter、Space、焦点和目标 Action 按 CC-013/014 保持 |

### 21.3 Google-inspired 对照

| 搜索结果页视觉角色 | Workspace 目标 |
|---|---|
| 大标题 | `Search Workspace` H1 |
| 搜索分区标题 | `Accessible records` H2 |
| 蓝色结果标题 | 结果主标识 H3（仅现有且可安全识别的数据） |
| 来源/日期行 | Resource 与现有日期 Meta，不造 URL |
| 摘要 | 客户、总额等现有可见信息 |
| 摘要续行 | 最多三条可安全识别的明细 |
| 大留白 | 28px 卡片间距及规定的内部层级间距 |
| 简洁分页 | 保留 Odoo 用户需要的 Rows per page / Showing 与当前页高亮 |

### 21.4 Glossary

| 术语 | 含义 |
|---|---|
| H1/H2/H3 | 页面、分区、结果主标题的视觉字号层级 |
| Body | 摘要及主要卡片内容 |
| Meta | Resource、日期等辅助信息；不是新的 URL 或条件 |
| Rendered text | 服务端按既有 Card Template 渲染并返回的单一文本值 |
| UI-only | 仅修改展示层；不变更搜索请求、响应权威或业务数据 |
| Stop Condition | 触发后暂停实现，不能自行猜测数据结构或扩大范围 |

### 21.5 Version History

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-14 | 根据 8091 实际 Search Workspace 截图/DOM 核对起草；记录 template-based 卡片语义重排的 stop boundary | APPROVED / FROZEN |
| v0.2 | 2026-10-14 | 用户批准视觉样式并要求 Search by field 与 Query Understanding 默认收缩、可展开/收缩 | APPROVED / FROZEN |
| v0.3 | 2026-10-14 | 用户要求将 Resource Selector 移至 Search query 下方；明确只调整现有模板块顺序，不改变搜索语义 | APPROVED / FROZEN |
| v0.4 | 2026-10-14 | 用户明确完整七区顺序，并要求 Date and state filters 默认收缩；冻结三个 disclosure 的默认状态 | APPROVED / FROZEN |
