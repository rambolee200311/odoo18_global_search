# CC-014 — Result Card Template Designer & Live Preview

## 0. Governance

| 项 | 内容 |
|---|---|
| Coding Contract | CC-014 |
| 版本 | v0.1 |
| 状态 | FROZEN |
| Intent ID | `GS-SEARCH-RESULT-CARD-TEMPLATE-DESIGNER` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.5 FROZEN — AMENDMENT（规范基线；v1.4 为前序版本） |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.4 FROZEN — AMENDMENT（规范基线；v0.3 为前序版本） |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.3 FROZEN — AMENDMENT（规范基线；v0.2 为前序版本） |
| 前置 CC | CC-001 ~ CC-013；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 为 Global Search 建立 Published Configuration 驱动的搜索结果卡片模板设计器 |
| 批准冻结 | 用户批准；2026-10-10 |

本 CC 定义 Business Resource 的 Result Card 模板语法、配置界面、管理员预览、发布验证、
运行时模板渲染及相应安全/回归要求。本文已获用户批准冻结，不修改或取代上游冻结文档。

版本基线处理：任务最初指定 SRS v1.4、TDD v0.3、实施计划 v0.2；仓库已存在且冻结的
后续修订分别为 v1.5、v0.4、v0.3。经 §2.1 差异核查，后续修订改变了配置 Apply 生命周期
及主模型/关联搜索结果语义，均与本 CC 的 Published 模板及多模型 Resource 校验直接相关；
因此本契约采用当前最新冻结修订作为规范基线。若要求退回旧版，必须先做正式影响评审，
不得仅通过改写此处版本号来规避后续冻结契约。

## 1. Contract Goal

为 Global Search 建立统一的搜索结果卡片模板设计器。获授权的配置管理员可以在
Business Resource 上编写常量与字段变量组成的卡片模板，从字段列表插入变量，查看
实时预览，再按既有配置生命周期保存、校验并应用。

```text
配置管理员
    │
    ▼
Business Resource.card_template（暂存配置）
    ├── 常量："订单号："
    ├── 变量：{name}
    ├── 常量："\n客户："
    ├── 变量：{partner_id}
    ├── 常量："\n金额："
    └── 变量：{amount_total}
           │
           ├──────────────► 字段列表拖放 / 插入变量
           │
           ▼
    解析、验证、格式化、权限过滤
           │
           ├──────────────► 实时预览（当前配置管理员权限）
           │                    │ 修改 / 拖动 / 切换预览记录
           │                    └──────────────► 再次预览
           ▼
    保存为暂存配置 → 显式 Apply / Publish 校验
           ▼
    Published Configuration Snapshot
           ▼
    Search Service（当前用户授权记录和字段）
           ▼
    纯文本模板渲染 → Result Card
```

设计器预览只用于配置管理界面，不在 Search Workspace 中恢复或新增 Preview 面板。模板
不能改变搜索、资源选择、记录导航或用户权限。Result Card 仍为摘要；CC-013 的新 Tab
Native Form 导航继续独立生效。

## 2. Background and Acceptance Findings

### 2.1 Existing Implementation Findings

以下为草拟时对仓库实现的只读核查；这些验收发现不修改任何既有冻结文档。

| 发现 | 当前证据 | 核查方法 | 对 CC-014 的影响 |
|---|---|---|---|
| Card 配置 | `wd.gs.business.resource` 已有 `snapshot_field_ids`；Published Snapshot 输出字段、Label、Sequence、Visible、Format 和空值策略 | 检查 `models/configuration.py` 的 Resource/Snapshot Field 模型和 Snapshot builder | 可作为字段元数据与历史配置迁移输入；模板字符串及模板解析尚未定义 |
| Card 序列化 | `services/card.py` 按 Published Snapshot 字段和可读字段序列化，并使用 Odoo 日期、时间、数字格式化 helper | 检查 `services/card.py` 的 serializer、formatter 与调用点 | 应抽取/复用服务端格式化及字段权限边界，避免设计器和生产渲染分叉 |
| Search 权限 | `services/permission_boundary.py` 提供 Resource 与字段读取授权入口；搜索结果由当前用户环境读取 | 检查 `services/permission_boundary.py`、executor 和当前用户调用路径 | 模板仅组织已授权的值，不得创建新的权限授予路径 |
| 配置生命周期 | Published/Retired 修改采用暂存与显式 Apply；草稿通过既有 Publish 流程发布 | 检查配置版本/resource mutation mixin、`action_apply_changes`、Snapshot builder 和配置测试 | 设计器的“保存”不能隐式改写活动 Snapshot 或绕过 Apply |
| Preview 实现 | `services/preview.py` 使用固定模型/字段映射，不接受 Resource 的模板配置 | 检查 `services/preview.py` 中模型字段 allowlist 和 `load_preview` | 不能直接作为 CC-014 设计器预览实现；需使用 Resource、草稿模板和统一 renderer |
| 模板能力 | 当前没有 `card_template` 字段、模板语法解析器、模板安全验证或字段拖放设计器 | 检查 Resource model、services、controller、views、static assets 和 tests 中是否存在模板实现 | 属于 CC-014 的实现缺口 |
| 版本基线 | 仓库元数据为 SRS v1.5、TDD v0.4、计划 v0.3 | 检查三个文档的 Governance 元数据和变更历史，并对照修订 diff | 后续冻结修订改变 Apply 与主模型契约；本 CC 以最新版本作为规范基线 |

### 2.1.1 Frozen Baseline Delta

| 文档 | 前序版本 → 规范基线 | 已确认差异 | 对 CC-014 的影响 |
|---|---|---|---|
| SRS | v1.4 → v1.5 | 明确普通 Resource 的单一 Primary Model、Relation Path 命中仍返回主模型，以及复合 Resource 只合并独立模型；增加 Published 暂存/Apply 原子语义及 AC-046/AC-047 | 模板必须按模型映射验证变量；模板 Save/Apply 不能更改搜索结果模型或绕过原子配置应用 |
| TDD | v0.3 → v0.4 | 对齐 Primary Model/Relation Path；定义 Published/Retired 的 pending edit、完整校验、原子 snapshot/checksum 更新和旧/新 checksum 审计 | 作为 Preview/模板发布与字段验证的技术约束，不能退回 v0.3 生命周期假设 |
| 实施计划 | v0.2 → v0.3 | 增加主模型/关联结果及配置暂存/Apply 的实施任务、验收行为和 AC-046/047 追溯 | CC-014 的配置变更纳入既有阶段/门禁；不新增绕过计划的发布路径 |

核查范围是上述冻结修订的文档变更历史和差异；本节只记录与 CC-014 直接相关的差异，
不声称完整复述各上游版本的全部变更。

### 2.2 Implementation Gap

目前管理员不能在 Resource 上组合任意常量与字段变量，不能将字段插入模板，也不能以
草稿模板实时预览；现有 Card Field 配置只描述离散字段和值，不能表示固定文字、换行、
变量重复或自定义顺序。现有 Preview 服务也不是模板预览服务。

### 2.3 Existing Contract Support

- CC-001 的 Business Resource、Published Snapshot、暂存和显式 Apply 是唯一配置生命周期；
- CC-002 返回的 Resource/记录身份和分页协议保持不变；
- CC-003 的当前用户、公司、模型、记录、字段及关系权限是唯一业务数据读取边界；
- CC-007 的错误状态/安全错误 envelope 不由本 CC 重定义；
- CC-009 的服务端语言及时区格式化为 Card/Preview 的唯一格式化来源；
- CC-012 的 Resource key、选择、多选和计数语义保持不变；
- CC-013 的 configured Action、新 Tab 和打开时重新授权保持不变。

## 3. Scope

### 3.1 In Scope

- 在既有 Business Resource 配置上增加单一 `card_template` 文本字段；
- 仅由常量与静态字段变量组成的模板语法、解析、校验及长度/变量数限制；
- 模板编辑器、可访问字段列表、拖放/键盘插入和实时预览；
- 最近可读记录、管理员手动选择的可读记录、合成示例三种预览来源；
- 基于当前用户语言/时区与现有格式 helper 的模板渲染；
- Preview 与 Search 运行时共享的解析、字段授权、格式化及纯文本输出逻辑；
- 发布/Apply 时验证模板语法、变量、字段类型、格式和限制；
- 不同用户权限下的字段过滤、预览权限警告、HTML/XSS 防护；
- 模板升级/兼容策略及本 CC 测试矩阵要求。

### 3.2 Out of Scope

- CC-013 的 configured Action、新 Tab 导航及打开时授权；本 CC 不替代这些能力；
- CC-012 的 Resource Selector、count、选择和多选；
- CC-003 权限边界或 CC-007 错误协议的重设计；
- Search 查询、Refinement、Raw Query、Effective Conditions、Result Identity 或分页语义；
- 自然语言搜索、模糊匹配、聚合计算（L4）、Readonly Native Form；
- 任意 Python/JavaScript/模板引擎、HTML authoring、条件表达式、循环、函数或变量计算；
- 新建平行 Card Field Registry、权限 Registry、Search/Preview 架构或外部技术栈；
- 修改 SRS、TDD、Implementation Plan、既有 CC 或 Odoo 官方代码；
- Elasticsearch、OpenSearch、LLM、向量检索或绕过 Odoo ORM 的业务数据读取。

## 4. Card Template Syntax

### 4.1 Grammar

模板是 UTF-8 文本，由常量片段和字段变量依输入顺序拼接。变量不执行求值，只能使用
以下语法：

```text
template  := (text | variable)*
variable  := "{" field_name [ ":" format_key ] "}"
field_name := [A-Za-z_][A-Za-z0-9_]*
```

- `{field_name}`：使用该字段的默认类型格式；
- `{field_name:format_key}`：使用兼容字段类型的内建格式；
- `\n` 和 `\t`：分别表示换行和制表符；模板编辑器也可直接输入实际换行/制表符；
- 其他文字、空格、标点和分隔符均为常量，原样保留；
- 为表示字面花括号，`{{` 和 `}}` 分别渲染为 `{` 和 `}`；单独出现、未配对的花括号为语法错误；
- 字段名不接受点号或 relation path；例如 `{partner_id.name}` 无效；
- 一个变量只包含字段标识符及可选的内建格式键，不包含引号、参数、运算符或表达式。

内建 `format_key` 为 `text`、`integer`、`float`、`date`、`datetime`、`boolean`、
`selection`、`many2one`、`monetary`。格式键是封闭 allowlist，不可注册调用函数或添加
格式化参数。省略 format 时按 Odoo 字段类型选择唯一兼容的默认 formatter。

语法示例：

```text
# 简单模板
订单号：{name}
客户：{partner_id}

# 显式格式
订单号：{name:text}
金额：{amount_total:monetary}
下单时间：{date_order:datetime}

# 字面花括号
说明：{{literal braces}}
状态：{state:selection}
```

### 4.2 Compatibility

| 字段类型 | 默认显示 | 允许显式格式 |
|---|---|---|
| Char | 文本原值 | `text` |
| Text / Html | 纯文本 | `text`；Html 字段必须先转成纯文本，不执行或保留标签 |
| Integer | 本地化整数 | `integer`、`text` |
| Float | Odoo 用户语言数字格式 | `float`、`text` |
| Date | Odoo 用户语言日期格式 | `date`、`text` |
| Datetime | Odoo 用户语言和时区格式 | `datetime`、`text` |
| Boolean | 本地化“是/否” | `boolean`、`text` |
| Selection | 当前用户语言的 Selection Label | `selection`、`text` |
| Many2one | 当前用户可读的 `display_name` | `many2one`、`text` |
| Monetary | Odoo 货币格式及字段关联币种 | `monetary`、`float`、`text` |

未列出的关系、多值、二进制、Reference、One2many、Many2many 及未知字段类型不支持为
模板变量。格式与字段类型不兼容时，验证失败；不得静默回退至 Python `str()`、客户端
locale 或不同的 formatter。

### 4.3 Example

```text
订单号：{name}
客户：{partner_id}
金额：{amount_total:monetary}
下单时间：{date_order:datetime}
状态：{state:selection}
```

示例渲染（实际值、翻译、精度及显示格式取决于当前用户可读记录及其 Odoo locale）：

```text
订单号：S00042
客户：Azure Interior
金额：$ 1,234.50
下单时间：10/10/2026 4:30:00 PM
状态：已发送
```

边界示例（仅展示模板输出；真实值由权限及当前 Odoo locale 决定）：

```text
# 可读客户值为空
订单号：S00042
客户：—
金额：$ 1,234.50

# 配置管理员无客户字段读取权限的 Preview
订单号：S00042
客户：[无权访问]
金额：$ 1,234.50

# 搜索用户无客户字段读取权限的生产 Card（变量结果是空字符串）
订单号：S00042
客户：
金额：$ 1,234.50
```

## 5. Card Template Designer UI

### 5.1 Layout

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Business Resource: Sales Order                     [Save] [Apply]    │
├──────────────────────────────────┬───────────────────────────────────┤
│ Template editor                  │ Preview                            │
│                                  │ Source: [Latest readable record ▾] │
│ 订单号：{name}                   │                                   │
│ 客户：{partner_id}               │ 订单号：S00042                     │
│ 金额：{amount_total:monetary}    │ 客户：Azure Interior               │
│                                  │ 金额：$ 1,234.50                   │
│                                  │                                   │
│                                  │ [Permission may differ by user]    │
├──────────────────────────────────┴───────────────────────────────────┤
│ Available fields:                                                     │
│ name · Char · Order Reference   partner_id · Many2one · Customer     │
│ amount_total · Monetary · Total state · Selection · Status           │
└──────────────────────────────────────────────────────────────────────┘
```

布局可随窄屏调整，但必须保持编辑、字段查找和预览均可达；字段列表可置于右侧或编辑器
下方。界面不得把预览做成可执行 HTML 或允许其触发业务写入。

### 5.2 Interaction

1. 输入模板常量或 `{field_name}`；保存前及 Apply/Publish 时均由服务端解析和校验。
2. 从字段列表拖放字段时，将变量插入编辑器当前选区/光标位置；没有选区时插入光标末尾。
3. 提供键盘可达的“插入字段”操作，不能要求用户必须拖放。
4. 模板变化或字段拖放后刷新预览；有效编辑的预览请求允许短暂 debounce，但最终预览必须反映最新模板，不得显示较旧请求的晚到结果。
5. 切换预览来源/记录后刷新预览；配置保存或 Apply 前以待保存的完整模板再刷新一次。
6. 语法/字段错误在编辑器附近显示稳定、可操作的提示；无效模板不替换最后一次成功预览数据以外的已发布配置，也不得以“成功”响应掩盖错误。
7. `Save` 遵循 CC-001 的配置写入/暂存规则。对 Published/Retired 版本的修改先成为 pending change，只有显式 `Apply Changes` 完成完整校验后才更新活动 Snapshot/checksum；草稿沿既有 Publish 流程发布。

键盘操作：

- `Tab` / `Shift+Tab`：在编辑器、字段插入控件、预览来源、预览及 Save/Apply 控件间按可见顺序移动焦点；
- 在字段列表中使用方向键选择字段，`Enter` 将所选字段变量插入编辑器光标处；
- `Ctrl+S` / `Cmd+S`：焦点位于设计器时调用现有 Save 行为，不触发浏览器“另存网页”；
- `Ctrl+Enter` / `Cmd+Enter`：仅当用户有 Apply 权限且配置可应用时触发现有 Apply Changes 操作；
- `Escape`：关闭字段选择菜单或退出当前拖放/选择交互；不静默丢弃 Resource 上其他未保存配置。

快捷键处理仅作用于设计器，且不得覆盖输入法组合键或无关 Odoo 全局快捷键。

### 5.3 Available Field List

字段列表只列当前 Resource 所映射模型上存在且模板类型支持的字段，并显示：

- 技术字段名（变量插入使用的名称）；
- Odoo 字段类型；
- 当前服务端用户语言的字段 Label；
- 当前预览账号可读性状态；若元数据表明该字段受组约束，显示权限可能因用户而异的标记。

多模型 Resource 使用同一 Resource 级模板。字段列表只提供所有映射模型共有、且类型/格式
兼容的字段名；Publish 时必须对每个映射模型验证模板中的每个变量。若不存在符合业务需要
的共有字段，必须停止并评审模型专属模板契约，不得在模板中猜测当前模型或按结果动态选
模板。

## 6. Card Template Preview

### 6.1 Preview Sources

预览支持以下来源，预览页面清楚显示来源及记录/样例状态：

默认来源为**最近一条可读记录**。若当前账号下不存在可读记录，则自动回退为合成示例并
清楚显示“合成示例”；管理员可手动切换来源。

1. **最近一条可读记录**：通过当前配置管理员的普通 Odoo ORM 环境读取该 Resource 中符合
   Resource 的模型/公司边界且当前账号可读的最近记录；排序规则固定为写入/创建时间降序，
   再以记录 ID 降序作为稳定次序。具体时间字段采用模型已配置的业务日期映射；没有可用
   日期映射时使用 `write_date`，再回退 `create_date`。
2. **手动选择记录**：只可从同一 Resource 且当前配置管理员可读的候选记录中选择；搜索
   候选及读取字段使用普通 ORM/current-user environment。
3. **合成示例数据**：仅由字段类型及格式化器生成，不读真实业务记录，不写数据库；界面
   明确标记“合成示例”，不得伪装成真实记录。

资源没有当前账号可读的记录时，最近/手动来源显示通用空状态；不能换用 `sudo()`、超级用户、
其他用户环境或猜测记录。管理员可以切换到合成示例继续编辑。

### 6.2 Refresh and Permissions

- 编辑内容有效变化后实时刷新；无效语法显示验证错误，不向 renderer 提交。
- 拖放变量后刷新；记录/source 切换后刷新；Save/Apply/Publish 前刷新待提交值。
- 模板变化后 debounce 300 ms 再请求；防抖期间不发送额外 Preview 请求。
- 同一 Resource 最多保留一个有效预览请求；更新模板/source 时取消或作废前序请求，并以
  单调递增 request sequence 校验响应；旧请求晚到必须丢弃，不能覆盖最新预览。
- 已完成请求被 rate limit 时显示可恢复提示，不展示旧请求伪装为最新结果。
- Preview 使用当前已登录配置管理员的 session、公司、语言、时区及 ACL；不得使用
  superuser/admin substitute environment。
- 显示持续可见的权限警告：“预览按当前配置账号权限渲染；其他用户的字段/记录权限可能不同，
  搜索结果会按实际用户重新校验。”
- 对当前配置管理员无权读取的预览字段，变量位置显示 `[无权访问]`，并标示字段名及权限
  警告；不得读取该字段值作为占位符或从其他权限上下文补齐。
- CC-014 不要求也不得推断所有普通用户的具体权限。对于字段组元数据能确认的限制，字段
  列表可标记“受组限制”；运行时仍逐用户授权。
- 不同用户、公司、记录 Rule 或字段权限可能产生不同结果；配置预览不是对所有用户可见性
  的保证。

### 6.3 Record Rule Boundary

“预览不访问 Record Rule”仅表示 Preview 不读取、枚举、解释或返回 Record Rule 定义、
domain 或内部配置；它**不表示跳过 Odoo 的记录规则**。真实记录的候选搜索、选择和读取
必须经普通 ORM 执行并服从当前用户 Record Rule 与公司边界。不得提供无 Record Rule 的
业务数据预览模式。若评审要求预览读取规则保护之外的数据，该要求与 CC-003 冲突，必须
停止并走影响评审。

### 6.4 Formatting and Output Safety

- Preview 与生产 Search Renderer 调用同一个服务端 parser、field authorization、type
  formatter 和 plain-text renderer；
- formatter 使用当前服务端用户 `lang`/`tz` 与 Odoo 格式化实现，绝不以浏览器语言/时区替代；
- 空值使用 `—`；Preview 无权限字段使用 `[无权访问]`，生产无权限字段使用空字符串；
- 文本中的换行按预览及 Card 的换行样式显示，Tab 采用固定可读空白宽度，不创建表格/HTML；
- 响应为普通文本/结构化安全数据；如服务端模板输出进入 HTML context，必须 HTML-escape；
  客户端必须以文本节点/`textContent` 显示，禁止 `innerHTML`、内联事件或可执行标记；
- 预览不调用 Action XML ID，不读取 Odoo Action，不触发导航；
- 预览禁止 create/write/unlink、业务按钮、邮件、活动、附件写入或任何副作用。

## 7. Card Template Rendering

### 7.1 Rendering Rules

1. Renderer 读取当前资源的 Published Snapshot 模板；不读取浏览器传入的模板覆盖值。
2. 常量按模板顺序原样拼接；`{{`/`}}` 还原为字面花括号；`\n`、`\t` 按语法转换。
3. 每个变量只从该 Search 结果的当前模型、当前记录及授权字段值映射中读取。
4. 字段变量必须先经 CC-003 当前用户字段读取授权；未经授权时生产输出空字符串，不访问
   字段值、不返回 Label/类型/拒绝原因，也不因字段不可读跳过整个 Resource 或改变计数。
5. 字段为空时输出 `—`。Boolean 的 `False` 是有效值，按当前语言渲染“否”；其他类型
   `False`/`None`/空字符串视为空。
6. Many2one 只输出当前用户可读的 `display_name`；其关联读取仍遵守 ACL、Record Rule、
   公司边界及现有 relation authorization。权限失败不得回退到原始 ID。
7. 已授权字段按 §4.2 的显式/默认 formatter 格式化；格式化异常按 CC-007 安全失败语义处理，
   不返回 Python 异常、traceback、内部字段值或成功形状的默认值。
8. 最终结果为纯文本。HTML-escape 在 HTML 呈现边界执行一次；前端以 text node 展示，
   不在 JSON API 中进行二次 escape 导致显示出实体文本。

### 7.2 Empty and Unauthorized Values

| 情况 | Preview | Search Result Card |
|---|---|---|
| 字段有权且有值 | 格式化值 | 格式化值 |
| 字段有权但为空 | `—` | `—` |
| 配置管理员无字段读取权限 | `[无权访问]`，并显示权限警告 | 不适用 |
| 搜索用户无字段读取权限 | 不适用 | 该变量渲染为空字符串；字段值/Label/类型不进入响应 |
| 记录不存在、记录失权或 Resource 不可用 | 通用安全状态，按既有协议 | 按 CC-007/CC-003 既有安全协议处理 |

空值占位与未授权空字符串的差异仅用于避免将无权限字段伪装成普通空值；客户端不添加
字段内部错误详情。即使模板中存在该变量，当前用户也不能通过错误、Card 字段数量、日志或
响应 metadata 推断其字段权限。

### 7.3 Internationalization and Performance

- v0.1 的模板常量按配置内容原样显示，不自动按语言翻译；管理员须以目标语言编写常量。
- 字段值、Selection Label、Boolean、数字、货币、日期及时间由当前服务端用户 `lang`/`tz`
  处理；缺失的字段/选择翻译遵循既有 Odoo/i18n helper 和 SRS/CC-009 的 fallback 规则。
- Preview 与生产 Card 使用相同的格式化路径。语言/时区切换后使用新服务端 context 重新渲染，
  不复用另一语言的缓存文本。
- 性能软预算：模板解析 P95 ≤10 ms；单 Card 模板渲染 P95 ≤50 ms；Publish/Apply 模板校验
  P95 ≤100 ms；一次 Preview API 端到端 P95 ≤500 ms。
- 性能测试至少 100 次，记录样本数、环境、冷/热状态和 P95；预算是软门禁，未达标先分析
  parser、ORM、格式化和网络耗时，不得移除权限检查或输出 escaping 来达标。

## 8. Security Boundary

### 8.1 Template Injection and HTML Safety

- 模板由获授权配置管理员管理，但模板内容仍按不可信文本处理；
- 解析只接受 §4 定义的词法；不调用 `eval`、`safe_eval`、Python format expression、
  QWeb/Jinja、JavaScript 或 SQL；
- 模板不能执行代码、条件、循环、函数、属性访问、方法调用、索引、算术或 relation path；
- 只允许简单字段变量与封闭格式 allowlist；不接受用户运行时传入的 formatter；
- 模板常量及字段值都按纯文本处理；不得拼接成可信 HTML；
- HTML 呈现必须 escape 常量和字段值，前端只使用文本节点/`textContent`；
- 禁止模板变量访问 Record Rule 定义、Action XML ID、内部模型权限明细、服务对象、环境对象、
  request/session 或任意 Odoo model。

### 8.2 Field and Record Authorization

- 发布时字段必须属于 Resource 已配置模型、存在、类型受支持，且具有明确的运行时授权和
  formatter 策略；Publish 检查不替代运行时授权。
- 每次 Search Card 渲染均以当前用户执行模型/记录/字段读取授权；按 CC-003 及现有
  `permission_boundary` helper 失败关闭。
- Preview 使用配置管理员的实际 session ORM environment；不得用 `sudo()`、超级用户、构造的
  admin environment 或另一用户 context。
- Preview 的真实记录选择与值读取仍服从 ACL、Record Rule、多公司及字段组权限；不读取或
  泄露规则配置本身。
- 任一变量字段不可读时，不能通过缓存、旧 Preview 结果、Card fallback、关系 ID、上下文或
  日志取回其值。
- 设计器及 Preview endpoint 仅允许具有既有配置管理权限的用户调用；不得因能够搜索而获得
  配置、字段值或 Preview 权限。

### 8.3 Preview API Safety Contract

如实现采用独立 Preview API，接口必须符合以下约束：

```text
POST /wd_global_search/api/card_template/preview
Authenticated configuration manager session only
Request: resource_key, draft_template, preview_source, optional record_id
Response: status, rendered_plain_text, validation_errors, safe_preview_metadata
```

- `resource_key` 只定位当前用户有权管理的 Resource；`record_id` 只能选择该 Resource 中
  当前用户可读记录；
- 使用 Odoo 已认证 session cookie；只允许配置管理员 ACL/group 访问；不得接受客户端传入
  的 uid、user、groups 或“已认证”标记；
- 使用 Odoo 支持的 CSRF token 校验；跨站请求不得借用配置管理员 session 执行预览；
- 对每个已认证用户执行每分钟最多 60 次 Preview 请求的服务端限流；超限返回显式、可恢复
  的限流错误，不读取记录、不以旧 Preview 结果冒充本次成功；
- 复用现有 Odoo/部署限流能力，不新增独立服务或业务数据存储；若当前部署无可复用能力，
  必须在实施评审中明确限流实现边界后再进入开发；
- `draft_template` 是需要解析/验证的文本，不是执行代码；字段白名单从服务端 Resource 配置
  和模型元数据建立，不信任客户端传入字段数组；
- 不接受 model、action/action_id/XML ID、domain、context、字段值映射、任意语言/时区、
  superuser 标志或权限绕过标志；
- API 不返回字段内部 access exception、Record Rule/domain、Action 信息、不可读值或
  traceback；使用既有安全错误协议；
- 对 Preview 调用实施适当的长度、变量数、认证、CSRF/session 及请求频率限制；不得将草稿
  内容、记录 ID、字段值或权限错误详情写入非白名单日志。

### 8.4 Logging

- 复用 CC-008 已批准的 structured logging 与字段白名单；本 CC 不扩展白名单。
- 仅使用已批准的 `request_id`、`config_version`、`resource`、`latency_ms`、`status`、
  `error_code`、`retryable` 等字段；具体允许项仍以 CC-008 为准。
- 日志级别按现有规范区分成功、校验拒绝和内部失败；不得把用户输入或异常详情直接写入日志。
- 不记录模板原文、Rendered text、字段值、记录 ID、Record Rule 内容、Action XML ID、
  token、session cookie 或 Preview request body。
- `template_hash`、`variable_count` 不属于自动批准的日志字段；如需新增必须先走 CC-008
  影响评审。

## 9. Invariants

| ID | 冻结不变量 |
|---|---|
| CC14-INV-001 | 生产 Result Card 模板只来自当前活动 Published Configuration Snapshot。 |
| CC14-INV-002 | 模板语法只包含常量、换行/制表符和已验证的字段变量。 |
| CC14-INV-003 | 模板永远不执行代码、表达式、条件、循环、函数、属性访问或方法调用。 |
| CC14-INV-004 | 每个生产变量在取值前必须经当前用户字段权限过滤。 |
| CC14-INV-005 | 所有进入 HTML 呈现的模板常量与变量值必须 HTML-escape，前端不得把模板输出解释为 HTML。 |
| CC14-INV-006 | 模板不能读取当前用户无权读取的字段值或通过 fallback/metadata 泄露该值。 |
| CC14-INV-007 | 模板和 Preview 不读取、枚举、返回或绕过 Record Rule 定义；真实业务记录访问仍服从 Record Rule。 |
| CC14-INV-008 | 模板不能访问 Action XML ID、Action、任意路由或导航 context。 |
| CC14-INV-009 | 模板变量字段必须在 Publish 时对 Resource 的每个映射模型验证；模型专属字段不能被猜测绑定。 |
| CC14-INV-010 | 生产渲染与 Preview 使用当前服务端用户语言和时区。 |
| CC14-INV-011 | Preview 与生产 Card 共用 parser、授权、格式化及纯文本 renderer。 |
| CC14-INV-012 | Preview 使用配置管理员的普通权限；生产渲染使用 Search 请求用户的普通权限。 |
| CC14-INV-013 | Preview 持续显示其权限范围以及其他用户可见性可能不同的警告。 |
| CC14-INV-014 | Preview 输出进入 HTML 时必须 escape；客户端以文本节点显示。 |
| CC14-INV-015 | Preview 不执行模板代码或任何模板副作用。 |
| CC14-INV-016 | Preview 的真实记录搜索/读取服从 ORM ACL、Record Rule 和公司边界。 |
| CC14-INV-017 | Preview 不访问 Action XML ID，不触发 Native Form 导航或 Action。 |
| CC14-INV-018 | 模板编辑/Preview 不能直接改写 Published Snapshot；Published/Retired 必须遵守显式 Apply。 |
| CC14-INV-019 | 同一输入记录、Snapshot 和用户 locale 下，模板解析与格式化结果确定且顺序稳定。 |
| CC14-INV-020 | 用户不可由失败状态、Card 长度、字段 metadata、日志或 timing 区别推断未授权字段值。 |
| CC14-INV-021 | 模板 UTF-8 编码长度不得超过 8 KiB。 |
| CC14-INV-022 | 模板变量 occurrence 总数不得超过 50，重复引用逐次计数。 |
| CC14-INV-023 | 模板变量必须对 Resource 的每个模型映射分别验证，禁止按结果模型动态猜测。 |

## 10. Publish-time Validation

草稿保存可保留不完整文本以便继续编辑；任何 Publish 或 `Apply Changes` 必须对完整配置
执行以下校验。存在任一错误时不得更新 Published Snapshot/checksum，pending change 保留，
旧活动 Snapshot 继续生效，并沿 CC-001 配置错误语义返回可操作错误。

1. **模板存在**：每个启用且支持 Result Card 的 Resource 必须有非空模板；模板只含空白字符
   视为无效。
2. **Resource 模型集合**：Resource 至少映射一个模型；同一个模板必须适用于该 Resource
   的所有映射模型。
3. **语法正确**：花括号配对、变量名称格式、格式键 allowlist、转义、换行/制表符合法。
4. **字段存在**：每个变量在每个映射模型均存在且为具体字段；禁止点号 relation path、
   非存储虚拟字段（除经批准的安全 compute 规则外，本 v0.1 默认拒绝）及不存在字段。
5. **类型支持**：每个模型上同名字段类型均属于 §4.2 支持类型；跨模型字段类型/格式兼容。
6. **权限策略完整**：每个变量经既有字段权限 helper 检查；配置账号无权管理/读取字段时
   Publish 拒绝，管理员不能配置不可验证字段。运行时仍按每个 Search 用户重新授权。
7. **格式策略完整**：默认及显式格式均有唯一内建 formatter；Monetary 必须有 Odoo currency
   字段语义；Selection、Many2one 必须可通过当前用户安全读取/翻译。
8. **长度上限**：模板 UTF-8 编码不超过 8 KiB；按编码字节数计数。
9. **变量数上限**：变量 occurrence 总数不超过 50；重复引用同一字段也逐次计数。
10. **变量唯一解析**：每个 token 完整解析一次；格式错误、未闭合占位符、未知字段、未知格式
    不可作为常量静默输出。
11. **安全**：禁止执行 token、转义绕过、嵌套表达式、HTML raw/safe 标记、Action/Rule
    metadata 变量以及客户端 dynamic field registration。
12. **迁移完整性**：既有 `snapshot_field_ids` 若用于初始迁移，必须确定性转换为等价默认模板
    或要求管理员显式提供模板；不得静默丢弃现有 Card 内容。迁移后旧字段配置不得与模板
    同时成为两个运行时权威来源。

建议的默认迁移：依既有 Sequence 顺序输出每个可见字段的 Label、`: `、变量和换行；
Label 以纯文本常量转义，变量沿用字段格式。转换仅发生一次并留有可审计配置变更，不
重写历史 frozen CC-013。若迁移无法无损表达旧配置，升级必须阻止应用并提示管理员。

### 10.1 Template Versioning and Rollback

模板不引入独立版本号或平行发布机制；它随 CC-001 Configuration Version 与 Published
Snapshot 管理。成功 Publish/Apply 的历史审计及旧/新 checksum 按既有策略保留；回滚通过
既有草稿/配置修订、完整校验及正常 Publish/Apply 流程重新发布目标模板，不直接改写历史
Published Snapshot，也不从浏览器恢复任意历史 JSON。

## 11. Test Matrix

所有测试均使用 Odoo ORM/current-user environment，不使用 `sudo()` 证明业务权限行为。每个
安全测试必须至少覆盖成功路径与拒绝/失权路径；浏览器测试记录用户、语言、时区、窗口宽度、
浏览器版本及 Console/Network 结果。

| ID | 可执行场景 | 通过标准 |
|---|---|---|
| CC14-TEST-001 | 发布模板 A 后 Search；暂存模板 B 但不 Apply 后再次 Search | 输出仍使用 A；Apply B 后使用 B；checksum/pending 遵循 CC-001 |
| CC14-TEST-002 | 模板仅含中英文字、标点、空格、`\n`、`\t` 和 `{{`/`}}` 常量 | 结果保留顺序；换行/制表符及字面花括号正确；无 HTML 解释 |
| CC14-TEST-003 | 模板引用两个已授权字段并重复引用一个字段 | 每个变量按出现位置替换，顺序及重复值正确 |
| CC14-TEST-004 | 分别渲染 Integer、Float、Date、Datetime、Boolean、Selection、Many2one、Monetary 样例 | 使用正确的 Odoo locale/tz、Selection Label、可读 display_name 及货币格式 |
| CC14-TEST-005 | 用仅有部分字段权限的用户 Search | 可读变量正确；不可读变量为空且值/Label/type 不出现在 response |
| CC14-TEST-006 | 模板常量与字段值含 `<script>`, `<img onerror>`, `&`, 引号和 `</div>` | API 为纯文本；浏览器只显示文字，无节点注入、事件或脚本执行 |
| CC14-TEST-007 | 对草稿模板提交 `{__import__('os')}`, `{field.__class__}`, `{field()}`、未配对花括号及 `{{literal}}` | 执行/属性/函数/非法语法验证失败；`{{literal}}` 仅作为字面 `{literal}` 接受；全程无副作用 |
| CC14-TEST-008 | 鼠标拖动字段至模板开头、中间、末尾及已选区；键盘插入相同字段 | token 插入精确光标位置；键盘路径可用；无拖放导致的业务写入 |
| CC14-TEST-009 | 在管理员编辑器更改有效模板并观察预览 | 延迟刷新后渲染值与最新模板一致；无手工刷新依赖 |
| CC14-TEST-010 | 修改 Published Resource 模板并 Save，不 Apply；随后 Apply | Save 后为 pending 且运行时 Snapshot 未变；Apply 校验通过后原子更新模板/checksum |
| CC14-TEST-011 | 对含相同字段的结果修改模板顺序/常量/重复变量并 Apply | Search Card 按新模板更新；Search result identity/count/pagination 不变 |
| CC14-TEST-012 | 使用 CC-013 配置 Action 打开模板渲染 Card | Card 点击/双击/新 Tab 语义不变，导航仍解析已发布 Action 并重新授权 |
| CC14-TEST-013 | 多个 Resource、多选、count、清空选择及分页时应用模板 | CC-012 Selector key/count/选择及空 scope 结果不变 |
| CC14-TEST-014 | 模型 ACL、记录 Rule、字段组权限在 Search 前后变化 | 当前用户即时重新授权；字段/记录失权失败关闭，无旧 Preview/缓存值泄露 |
| CC14-TEST-015 | 对某个 Resource 注入读取/格式化/renderer 异常 | 沿 CC-007 区分 EMPTY/PARTIAL_SUCCESS/FAILED/TIMEOUT；不伪造成成功或泄露异常 |
| CC14-TEST-016 | 在桌面、平板、窄屏加载设计器 | 编辑器、预览和字段列表可达；无横向溢出，警告和错误不会遮挡核心编辑 |
| CC14-TEST-017 | 分别选最近记录、手动记录、合成示例 | 来源标签准确；记录来源只读且为当前管理员可访问 Resource 记录；合成数据不读写业务记录 |
| CC14-TEST-018 | 快速连续编辑模板并触发多个 Preview 请求，再切换记录 | 最终显示最新模板/记录结果；旧请求晚到不得覆盖新结果 |
| CC14-TEST-019 | 用配置管理员打开设计器并检查权限警告/受组限制字段标记 | 明确提示 Preview 是当前管理员视角，其他用户可能不同；不声称模拟所有用户 |
| CC14-TEST-020 | 将同一模板分别用于 Preview 与 Search Card，并设置 `lang`/`tz` | 两者使用同一服务端 formatter；date/datetime/number/monetary/selection 表示一致 |
| CC14-TEST-021 | 字段分别为空字符串、None、False（Boolean 和非 Boolean） | 空字段为 `—`；Boolean False 为本地化“否”；未授权字段不伪装为空值 |
| CC14-TEST-022 | 配置管理员或 Search 用户无变量字段读取权限 | Preview 明示 `[无权访问]`；生产变量为空；字段原始值、Label、类型及异常详情不泄漏 |
| CC14-TEST-023 | 预览中包含 HTML/XSS payload 并检查 DOM、Console、Network | 内容作为文字显示；没有 HTML 节点、script、事件 handler、Action 请求或写请求 |
| CC14-TEST-024 | 每个变量引用一个仅属于部分映射模型的字段 | Publish/Apply 被拒绝；活动 Snapshot 保持原 checksum/template |
| CC14-TEST-025 | 提交超过 8 KiB 模板、超过 50 个变量或未知 formatter | 对应限制稳定拒绝；错误可操作；旧 Published Snapshot 不变 |
| CC14-TEST-026 | 用普通搜索用户请求设计器/Preview API，或伪造 model/field list/context | 访问拒绝；服务端从配置构造字段集合；无任意模型/字段读取 |
| CC14-TEST-027 | 当前管理员的 record rule 隐藏最近记录/手选记录，并提供合成示例 | ORM 不返回不可读记录；UI 使用通用不可用状态；不得切换 sudo 或其他用户 |
| CC14-TEST-028 | 对历史 Snapshot 执行升级/确定性模板迁移，含隐藏字段、空值策略及重复 Sequence | 可见字段顺序/标签/格式可证明等价；失败时升级或 Apply 阻断并保留旧活动 Snapshot |
| CC14-TEST-029 | 仅用键盘操作字段选择、变量插入、Save、Apply 和 Escape | Tab 顺序合理；Enter 插入字段；Ctrl/Cmd+S 与 Ctrl/Cmd+Enter 调用预期授权动作；Escape 不丢弃 Resource 的其他未保存数据 |
| CC14-TEST-030 | 在固定测试 fixture 上分别测量 Parser、Renderer、Publish Validation、Preview API 至少 100 次 | 记录样本数/环境/P95；软预算分别为 Parser ≤10 ms、单 Card Renderer ≤50 ms、校验 ≤100 ms、Preview API ≤500 ms；超预算触发分析，不得降低权限检查 |
| CC14-TEST-031 | 无 session/配置管理员权限、缺失或无效 CSRF token、跨站 POST、每分钟第 61 次 Preview 请求 | 请求拒绝或限流；未发生业务记录读取；返回既有安全错误格式；日志不含 token、模板或字段值 |

### 11.1 Test Fixture Convention

- 建议根目录为 `mymodules/wd_global_search/tests/fixtures/template/`，存放非敏感模板样例/
  文本 fixture；业务记录和权限组合通过 Odoo test ORM 建立。
- 覆盖 Customer、Sales Order、Purchase Order、多种受支持字段类型、有权/无权/部分有权用户、
  简单/格式/转义模板及三种 Preview source。
- 每个测试使用唯一标记并在 Odoo 测试事务中创建数据；不得用 `sudo()` 建立或读取业务数据，
  不直接查询数据库，不使用真实客户/订单数据。
- 测试结束通过事务回滚/测试 teardown 清理，并断言本测试创建的 fixture 不残留；不得通过
  全库计数或删除其他测试/用户的数据来证明清理成功。

## 12. Regression Requirements

- **CC-002**：`resources[]`、record identity、cursor、分页、counts、timeout 及响应字段兼容；
  Card template 不改变搜索结果集合、顺序或 Query Protocol。
- **CC-003**：当前用户/company/model/record/field/relation 权限、Record Rule 和失败关闭兼容；
  模板绝不是权限配置。
- **CC-005**：Raw Query、Refinement、Effective Conditions、Results-only Workspace 保持不变；
  管理员预览不能出现在 Search Workspace。
- **CC-007**：EMPTY、PARTIAL_SUCCESS、FAILED、TIMEOUT、错误唯一性及安全 envelope 不变；
  Renderer 错误不返回 traceback/字段数据。
- **CC-008**：日志字段白名单、audit 语义不变；不记录模板原文、变量值、记录 ID、草稿预览
  payload 或权限错误细节。
- **CC-009**：Label、Selection、日期、时间、数字、货币格式以当前服务端 `lang`/`tz` 为唯一
  来源，浏览器 locale 不得覆盖。
- **CC-010**：Workspace/search 用户不能修改 Published checksum/version；Published/Retired
  模板编辑使用暂存、显式 Apply、校验、原子 Snapshot/checksum 更新和 audit。
- **CC-012**：Resource key、Selector、多选、动态 counts、空 scope 语义完全兼容。
- **CC-013**：模板不修改 Result Identity、Card 触发方式、server-side Action 解析、Open-time
  reauthorization、新 Tab/opener 安全边界；Native Form 仍由已发布 Action 控制。
- **CC-001**：管理员 ACL、版本身份、Publish/Apply、拒绝语义和历史快照不可变约束兼容。

## 13. Stop Conditions

出现任一项即停止实现/发布，并提交评审，不得通过降级权限或临时 fallback 继续：

1. 模板无法在 Publish/Apply 前由同一个确定性 parser 完整验证；
2. 任一变量无法证明先授权后读取，或跨字段/关联读取权限无法验证；
3. renderer 需要读取模板以外的字段、任意 relation path、Record Rule 内容或 Action metadata；
4. 模板或变量可能执行代码、表达式、HTML/QWeb、JavaScript、SQL 或 formatter 参数；
5. Preview 与 Search Card 无法共享相同的字段授权和格式化逻辑；
6. 真实 Preview 记录需要 `sudo()`、超级用户、构造 admin env 或跳过 ACL/Record Rule；
7. 多模型 Resource 的字段变量不能对所有映射模型确定绑定/验证；
8. 迁移不能保持旧 Published Card 可见字段及顺序，且没有经批准的显式管理迁移方案；
9. 需要更改 SRS/TDD/既有 CC 冻结语义或 Odoo 官方代码但未完成影响评审/批准；
10. 预览接口或 HTML 呈现无法实施认证、输出 escaping、请求限制或无副作用保证；
11. 模板失败会改变 CC-002/CC-007 的结果协议，或产生 success-shaped fallback；
12. 评审仍要求“预览真实记录但不应用 Odoo Record Rule”；
13. Preview 请求无法通过防抖/请求序列保证新输入优先，旧请求可能覆盖新模板/source 结果。

## 14. Definition of Done

- `card_template` 是生产 Card 的唯一 Published 模板来源，不存在双重 Card registry；
- 语法、兼容 formatter、8 KiB/50 变量限制和 Publish/Apply 校验已实现且有自动化证据；
- 设计器支持常量/变量编辑、字段拖放、键盘插入、实时预览、来源切换和错误提示；
- 最近/手选预览遵守管理员普通 ORM 权限；合成示例不读取/写入业务记录；
- Preview/Search 使用同一 parser、field authorization、formatter 与纯文本 renderer；
- 未授权值不读取、不输出；预览权限警告明确；生产失权字段输出符合 §7.2；
- XSS/模板注入测试证明不执行、不注入；日志无模板/变量/记录敏感内容；
- CC14-TEST-001 ~ CC14-TEST-031 全部有通过证据，或有通过既定变更流程的明确合同级延期；
- CC-001 ~ CC-013 回归要求有测试证据；
- IHR、ATR、HVR 均已记录实际代码基线、环境、运行结果和未覆盖项；
- 不修改 SRS/TDD/Implementation Plan/既有 CC/官方 addons；不引入新架构或外部技术栈；
- 本 CC 由用户明确批准冻结后才能作为实施授权。

### 14.1 Acceptance Scenarios

1. 配置管理员输入简单模板并得到与可读记录一致的 Preview；
2. 输入带日期、Selection、Many2one、货币格式的模板并得到 Odoo 当前 locale/tz 格式；
3. 输入转义花括号、换行、制表符，确认按常量显示；
4. 拖放或键盘插入字段后，变量出现在光标位置且 Preview 更新；
5. 切换最近记录、手选记录和合成示例，来源标签和值与选择一致；
6. Save 后 Published Snapshot 不变；显式 Apply 后 Search Card 才采用新模板；
7. 普通用户搜索时 Card 按该用户权限渲染模板；
8. 空字段显示 `—`，未授权字段不泄露值；
9. HTML/XSS payload 以文字显示，模板表达式被 Publish 拒绝；
10. 超长模板、超变量数或跨模型不兼容字段均拒绝应用并保留旧 Snapshot。

### 14.2 Human Verification Scenarios (HVR)

人工验收记录必须包含可识别的人工验证者、日期、浏览器/版本、设备/viewport、代码与
Published 配置基线、逐场景观察及结果；Agent 自动化不能冒充人工确认。

1. 打开设计器，检查编辑器/字段列表/预览布局和权限警告；
2. 手输常量、变量及格式，检查实时 Preview 和格式化；
3. 拖放字段并用键盘插入字段，检查光标位置和 Preview；
4. 输入无效模板，检查验证错误以及未发布配置仍保持；
5. 在最近记录、手动记录、合成示例之间切换；
6. Save 后确认 pending 标识及旧 Published Card 保持；
7. Apply 后搜索并确认 Card 新模板生效；
8. 检查空值、无权字段警示、普通用户 Card 不泄露；
9. 检查 XSS payload、Console/Network 及无业务写入；
10. 用 Tab/Enter/Ctrl-or-Cmd+S/Ctrl-or-Cmd+Enter/Escape 完成编辑流程。

### 14.3 Browser Compatibility Matrix

以下为待执行门禁，不代表已验证。每个格记录浏览器精确版本、viewport 尺寸、结果和缺陷
编号；不得用单一 Chromium 结果推定其他浏览器通过。

| 浏览器 | Desktop | Tablet | Narrow |
|---|---|---|---|
| Chrome 最新稳定版 | Required | Required | Required |
| Firefox 最新稳定版 | Required | Required | Required |
| Safari 最新稳定版 | Required | Required | Required |
| Edge 最新稳定版 | Required | Required | Required |

## 15. Decisions

| ID | 决策 | 理由 |
|---|---|---|
| CC14-DEC-001 | 生产卡片模板只来自 Published Configuration Snapshot | Search 结果必须可复现并遵循 CC-001 的版本生命周期。 |
| CC14-DEC-002 | 模板只由常量、换行/制表符和简单字段变量组成 | 覆盖业务摘要表达能力，同时保持确定性和可验证边界。 |
| CC14-DEC-003 | 不支持代码、条件、循环、函数、属性访问或 relation path | 避免表达式执行、隐式数据依赖和越权读取。 |
| CC14-DEC-004 | 每个变量在当前用户权限检查成功后才读取 | Published 时校验不能替代逐请求用户授权。 |
| CC14-DEC-005 | 模板渲染为纯文本；HTML 边界 escape、浏览器用 text node | 阻断 XSS，同时避免双重 escape 改变显示文本。 |
| CC14-DEC-006 | Preview 与 Search 共用 parser、authorization、formatter、renderer | 消除预览与生产展示的语义漂移。 |
| CC14-DEC-007 | Preview 只使用配置管理员当前普通权限；不模拟、更不提升到其他用户 | 符合 Odoo session/权限边界，避免泄露或误称全体用户可见。 |
| CC14-DEC-008 | Preview 常驻显示“权限按当前管理员，其他用户可能不同”警告 | 降低管理员将预览结果误当作普通用户结果的风险。 |
| CC14-DEC-009 | 真实预览记录通过普通 ORM，实际服从 Record Rule；不读取规则定义 | “不访问 Record Rule”不得被解释为安全绕过，避免与 CC-003 冲突。 |
| CC14-DEC-010 | 字段列表拖放只作为插入便利，另提供键盘操作 | 满足快速设计且不排斥键盘/辅助技术用户。 |
| CC14-DEC-011 | 模板变化、拖放及记录切换触发实时 Preview，旧请求不得覆盖新结果 | 保证编辑器中的结果与最后一次输入一致。 |
| CC14-DEC-012 | 变量语法为 `{field_name[:format_key]}`，格式键为固定 allowlist | 简单、可读、无需表达式 parser；防止动态调用。 |
| CC14-DEC-013 | 常量支持 UTF-8 文本、`\n`、`\t` 及 `{{`/`}}` 字面括号 | 满足业务标签/换行/分隔符需求且语法无歧义。 |
| CC14-DEC-014 | 不新增平行 Card Field Registry；新增 Resource 级 `card_template` | 保持配置单一权威来源，减少 Snapshot 与模板冲突。 |
| CC14-DEC-015 | 所有模型映射使用同一模板，Publish 对每个模型校验变量 | Resource 级配置保持简单、确定，不依据搜索结果猜模板。 |
| CC14-DEC-016 | 模板上限为 8 KiB UTF-8 和 50 次变量引用 | 对管理界面与渲染开销设可测试上界，同时足以容纳常见摘要卡。 |
| CC14-DEC-017 | 空值渲染 `—`；生产无权限变量渲染空字符串；管理员 Preview 无权限显示 `[无权访问]` | 兼容明确空值反馈，同时让管理员发现自己无法预览的变量，且不返回被拒绝值。 |
| CC14-DEC-018 | Save 不绕过 Published 配置暂存/Apply；Apply/Publish 校验失败不替换旧 Snapshot | 与现有配置生命周期、原子快照和失败关闭行为一致。 |
| CC14-DEC-019 | 旧 Snapshot Field 只作为一次性确定性迁移来源，不与模板并行渲染 | 实现 CC-013 Card 字段配置到 CC-014 模板的替代，避免双重真相。 |
| CC14-DEC-020 | 模板常量不自动翻译，按配置内容原样呈现；字段/选择/数值/日期时间变量使用当前服务端 locale/tz | v0.1 不引入每语言模板 Registry；管理员应按目标部署语言撰写常量。旧 translated Label 的迁移以指定基础语言转换；如必须保留每语言常量，须独立影响评审。 |
| CC14-DEC-021 | 模板不拥有独立版本状态；继承既有 Configuration Version/Snapshot/Apply/Audit/rollback | 避免引入平行生命周期与版本真相。 |
| CC14-DEC-022 | 采用 §7.3/§11 的解析、渲染、校验、Preview P95 软预算 | 给性能回归提供可测阈值；超限先分析，不通过删减权限检查达标。 |
| CC14-DEC-023 | 模板日志沿用 CC-008 字段白名单，不新增 `template_hash`/`variable_count` | 避免因本 CC 扩大日志数据面或记录未审查元数据。 |
| CC14-DEC-024 | 测试 fixture 使用 ORM 与测试事务隔离，标记唯一且 teardown/rollback 后不残留 | 可重复验证权限和格式，同时不污染共享数据库或读取其他测试数据。 |
| CC14-DEC-025 | 设计器快捷键调用既有 Save/Apply action，Escape 只取消局部交互 | 防止键盘便利行为绕过权限或意外丢弃整份配置。 |
| CC14-DEC-026 | Preview endpoint 使用 Odoo session、配置 ACL、CSRF 和每用户每分钟 60 次限流 | 防止跨站请求、身份伪造和资源滥用；前端防抖并合并请求以满足实时预览。 |

## 16. Implementation Structure

建议按现有目录及既有 helper 实施；目录/模块建议不构成新架构授权。

```text
mymodules/wd_global_search/
├── models/configuration.py              # Business Resource.card_template、字段/发布校验
├── services/template.py                 # 纯 parser、validator、formatter 与 plain-text renderer
├── services/preview.py                  # Resource 草稿模板 Preview，复用 template/permission helpers
├── controllers/main.py                  # 认证配置管理员的 Preview endpoint
├── views/configuration_views.xml        # Resource 编辑区、字段列表、Preview 容器
├── static/src/js/template_designer.js   # 编辑器、拖放/键盘插入、请求顺序控制
├── static/src/css/template_designer.css# 设计器/预览布局
└── tests/
    ├── test_template.py                # Grammar、限制、格式与 escaping
    ├── test_template_preview.py        # 权限、来源、Preview 安全
    └── test_template_ui.py             # 拖放、键盘、实时刷新及显示
```

不得为满足目录建议新增重复的 `template_preview.js` 与设计器脚本职责；实现可以按已有
前端 asset 组织合并文件。业务记录查询必须经现有用户环境和 ORM；不得直接读写数据库。

## 17. Appendix

### 17.1 Traceability Matrix

| CC-014 obligation | Upstream contract | Evidence |
|---|---|---|
| Resource 上的 Snapshot/Card 内容配置 | SRS CFG-003、FR-SW-003；TDD Business Resource / Published Snapshot | Resource 模板字段、迁移测试、Published Snapshot assertion |
| 卡片格式化及服务端 locale | SRS FR-PM、TDD locale/timezone formatting；CC-009 | 同一个 formatter 的 Preview/Search locale tests |
| 字段、记录、关系授权 | SRS FR-PM；TDD Permission Boundary；CC-003 | 当前用户 ACL/Record Rule/field group tests |
| 配置保存、Publish、显式 Apply | CC-001、CC-010 | pending/checksum/atomic apply tests |
| Search API、counts、错误结构不变 | CC-002、CC-007、CC-012 | Search protocol and regression tests |
| Result Card 与新 Tab Action 不变 | CC-013 | Card rendering plus configured navigation regression |
| XSS/模板注入防护 | SRS security/non-bypass constraints；CC-003/CC-008 | parser adversarial tests、DOM/Console tests、log assertions |

### 17.2 Interface Contracts

| Interface | Input authority | Required output/behavior |
|---|---|---|
| `BusinessResource.card_template` | 配置管理员草稿；发布后是 Published Snapshot | 单一模板文本；Published 版本只在既有 Apply/Publish 成功后改变 |
| Template parser | 服务端读取的草稿或 Published 模板文本 | 有序常量/变量 token；输入长度、变量数和语法错误显式返回 |
| Template validator | 服务端 Resource、模型字段元数据、配置用户权限 | 完整诊断；所有映射模型均匹配，否则拒绝 Publish/Apply |
| Production renderer | Published token、当前用户授权 values、服务端 locale/tz | 纯文本 Card；无权变量为空；无权限值不进入任何输出 |
| Preview endpoint | 已认证配置管理员、Resource key、草稿模板、受限 preview source/record | 纯文本预览/验证结果；当前权限标记；不执行、不写入、不导航 |
| Search result contract | CC-002 当前接口 | 保持 Resource identity、分页、counts 和 CC-007 状态语义；Card 不改变搜索协议 |
| Navigation contract | CC-013 `resource_key + record_id` | 不变；仍使用 Published Action 和打开时的安全授权 |

### 17.3 Glossary

| 术语 | 定义 |
|---|---|
| Card Template | Resource 上定义的纯文本常量与字段变量序列 |
| Variable | `{field_name[:format_key]}` 形式的静态字段引用 |
| Design-time Preview | 配置管理员预览草稿模板的只读管理界面 |
| Synthetic Example | 根据字段类型生成的非业务、非持久化示例数据 |
| Published Snapshot | 经 CC-001 Publish/Apply 后供生产搜索读取的不可变配置表示 |
| Unauthorized variable | 当前请求用户无权读取的模板字段变量 |

### 17.4 Version History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| v0.1 | 2026-10-10 | FROZEN | 用户批准冻结：定义模板语法、Resource 设计器、实时预览、权限/格式化/escaping、验证、测试和回归要求 |

### 17.5 Front-end and Preview Interface

设计器前端职责可由现有 JS asset 中的等价模块函数实现；以下是行为契约，不要求另建
平行模块或逐字使用函数名：

```text
insertField(fieldName) -> void
insertConstant(text) -> void
insertNewline() -> void
insertTab() -> void
insertLiteralBrace(openOrClose) -> void
previewTemplate(templateText, previewSource, optionalRecordId) -> Promise<PreviewResponse>
saveTemplate() -> Promise<SaveResponse>
applyTemplate() -> Promise<ApplyResponse>
switchPreviewSource(source, optionalRecordId) -> void
handleKeyboard(event) -> void
```

`fieldName` 必须来自服务端字段列表；插入函数只修改编辑器文本，不调用模型/API。Preview
Request 不携带客户端 user/model/domain/context/fields/value-map。最小响应契约：

```json
{
  "status": "SUCCESS",
  "rendered_plain_text": "订单号：S00042",
  "validation_errors": [],
  "safe_preview_metadata": {
    "source": "latest_readable_record",
    "display_label": "Sales Order",
    "permission_warning": true
  }
}
```

错误响应使用既有认证、配置校验、CC-007 安全错误语义；不得内嵌字段值、记录 ID、
Record Rule、Action metadata 或 traceback。Preview source 为固定枚举
`latest_readable_record`、`selected_readable_record`、`synthetic_example`。请求必须携带
Odoo session 与 CSRF token，并受 §8.3 的配置 ACL 和限流约束。

### 17.6 Legacy Card Field Migration Example

旧 CC-013 Published Card Field 配置：

| Field | Sequence | Label | Format |
|---|---:|---|---|
| `name` | 10 | Order | text |
| `partner_id` | 20 | Customer | text |
| `date_order` | 30 | Order Date | datetime |
| `state` | 40 | Status | selection |
| `amount_total` | 50 | Total | monetary |

推荐的基础语言目标模板：

```text
Order: {name}
Customer: {partner_id}
Order Date: {date_order:datetime}
Status: {state:selection}
Total: {amount_total:monetary}
```

迁移器按 Sequence、旧 Label 和字段 Format 确定性生成等价模板；常量需 escaping，隐藏字段
不得迁移，可见性/allow-empty 语义须被证明等价。由于 v0.1 模板常量不自动翻译，历史
translated Labels 以配置指定基础语言生成；无法保留旧语义时停止迁移，要求管理员审阅并
明确确认，不静默丢弃翻译或字段。

### 17.7 Review History

| 版本 | 日期 | 评审人 | 结论 | 处理 |
|---|---|---|---|---|
| v0.1 | 2026-10-10 | 用户 | 批准冻结 | CC-014 v0.1 冻结并进入实施 |

### 17.8 Review Change Log

| 版本 | 变更 |
|---|---|
| v0.1 review update | 明确规范上游修订基线及差异；增加核查方法、语法/边界示例、键盘交互、Preview 默认/防抖、session/CSRF/rate limit、长度/变量不变量、请求顺序停止条件、国际化/版本/性能/日志/fixture/HVR/浏览器矩阵/接口/迁移契约 |
