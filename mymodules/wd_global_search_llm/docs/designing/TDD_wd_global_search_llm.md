<!--
Template source: docs/skill/odoo-project-workflow/references/templates/Designing/TDD模板.md
Template source version/status: v1.0.0; Frozen
Template sync check: PASS on 2026-10-15
This project document is Frozen as the v1.0.0 technical baseline by explicit user approval on 2026-10-15.
-->

# wd_global_search_llm 技术设计说明书（TDD）

> 文档路径：`mymodules/wd_global_search_llm/docs/designing/TDD_wd_global_search_llm.md`  
> 模块名称：`wd_global_search_llm`  
> 文档版本：v1.0.0  
> 状态：**FROZEN — 技术设计基线；实施仍须通过 Implementation Plan / 首个 CC 门禁**  
> 技术负责人：待项目负责人指定  
> 基线日期：2026-10-15
> 批准记录：用户于 2026-10-15 明确批准冻结（本对话）

## 0 文档说明

### 0.1 文档定位

本文记录自然语言聊天与 `wd_global_search` 搜索服务之间的技术桥接设计，供后续实施计划与 Coding Contract 引用。本文不是业务需求规格；冻结本 TDD 不代替 Implementation Plan 批准或首个 CC 门禁。

### 0.2 上游基线与阻塞项

| 项 | 基线 / 状态 |
|---|---|
| 全局搜索需求 | [SRS_global_search.md](../../../../docs/requirement/SRS_global_search.md) V1.5，FROZEN；明确将 LLM 和完整自然语言解析排除在原模块 V1 范围外 |
| 全局搜索技术设计 | [TDD_global_search.md](../../../../docs/design/TDD_global_search.md) v0.4，FROZEN；定义既有搜索服务边界，不含 LLM 桥接 |
| 桥接功能需求 | [SRS_wd_global_search_llm.md](SRS_wd_global_search_llm.md) v1.0.0，FROZEN；用户于 2026-10-15 明确批准 |
| Technical Verification | [TV_wd_global_search_llm.md](../../../../docs/verification/TV_wd_global_search_llm.md) TV-LLM-01/02，CLOSED — source-level verification; runtime tests remain in implementation |
| 代码核查输入 | 当前工作区 `wd_global_search`、`odoo-llm` 的源码接口审查；未做桥接运行时集成验证 |

**基线门禁：** 现有 Global Search SRS 明确排除 LLM；桥接 SRS v1.0.0 已独立冻结，因此本文 §5–§19 为桥接技术基线，不扩展既有 `wd_global_search` 的业务需求。源码级验证已关闭 `TD-009`；桥接运行时集成测试尚未执行，属于实施阶段的验证项。开始实现前仍须完成已批准的 Implementation Plan、部署版本确认和首个 Coding Contract 门禁。

### 0.3 本文回答什么 / 不回答什么

| 回答（技术设计） | 不回答（需上游需求决定） |
|---|---|
| 如何用当前用户 `env` 直调 `SearchService` | 哪些用户应获得自然语言搜索功能 |
| 工具输入如何受资源描述和搜索服务校验 | 面向用户的完整意图识别及澄清产品流程 |
| 如何在请求暴露与工具执行两处强制白名单 | 专用助手的最终名称、角色文案和业务验收标准 |
| 如何整理服务端结果及生成安全链接 | 结果卡片、摘要长度、排序和分页的产品体验 |

本文是冻结的技术设计基线，不替代桥接功能的 SRS，也不定义或改变其中的业务需求和验收标准。

### 0.4 内容治理：三类划分

| 类别 | 本设计中的内容 |
|---|---|
| ① 工程强制标准 | 使用发起聊天用户的环境；业务搜索不使用 `sudo()`；服务器端校验工具白名单；不得由模型生成计数、记录身份或链接 |
| ② 模板变量 | 本地设计环境为 Python 3.11.9 / PostgreSQL 客户端 16.14；目标部署的精确服务版本、具体 provider 和模型须在实施计划基线中锁定 |
| ③ 项目技术决策 | 独立 addon、直调 `SearchService`、同步只读工具、当前用户可用资源范围、双重白名单、服务端链接校验 |

本文冻结的技术决策以 `TD-001` 至 `TD-009` 记录；桥接业务行为以冻结 SRS 为唯一权威。

### 0.5 冻结与变更规则

遵循 TDD 母模板 v1.0.0 §0.5。本文 v1.0.0 已冻结。上游需求变更先更新 SRS，再递增本文件版本；纯技术变更按 TDD 变更流程递增版本；不得覆盖或删除既有冻结版本。

### 0.6 编号规则

本文使用 `T-LLM-*` 表示桥接实现门禁、`SVC-LLM-*` 表示服务契约、`API-LLM-*` 表示工具输入输出契约、`SEC-LLM-*` 表示安全契约、`TEST-LLM-*` 表示实施阶段验证项、`TD-*` 表示已冻结的技术决策。编号固定，不回收。

### 0.7 规范措辞

“必须 / 禁止”表示强制实现门禁；“应”表示原则性要求；“待部署确认”表示实现前需要绑定具体运行环境，不得据此改变本文已冻结的技术契约。所有 TD 均为本版本冻结决策。

### 0.8 SSOT

| 实现事实 | 唯一定义位置 |
|---|---|
| 搜索服务真实输入输出 | §5.1、§5.2 |
| 工具执行和用户环境 | §6、§12 |
| 工具白名单 | §12.2、§18 |
| 搜索结果与链接 | §5.2、§6.2 |
| 拟定测试覆盖 | §14、§19.2 |

## 1 技术上下文与基线冻结

### 1.1 技术栈

| 层次 | 选型 / 版本 | 状态 |
|---|---|---|
| 平台 | Odoo 18.0 | 项目目标平台 |
| 语言 | Python 3.11（本工作区解释器 3.11.9） | 实施环境须与 Odoo 18 支持版本匹配；运行实例精确补丁版本待部署确认 |
| 数据库 | 本工作区 PostgreSQL 客户端 16.14 | 桥接不新增表；目标数据库服务端版本待部署确认 |
| 聊天 / 工具 | `llm_thread`、`llm_assistant`、`llm_tool` | 源码路径已核查；实际部署版本待核实 |
| Provider | 由专用 Assistant 选择支持 Tool Calling 的 provider；现有 `llm_openai` 可作为部署选项 | 桥接不直接调用 provider API |
| 搜索 | `wd_global_search.services.facade.SearchService` | 源码 API 已核查；桥接运行时兼容测试列为实施验证 |

实施计划基线及首个 CC 前必须记录目标 Odoo 实例的 Python / PostgreSQL 服务端精确版本，并确认兼容本表版本约束；该部署绑定信息不改变本 TDD 的技术决策。

### 1.2 模块依赖

| 依赖 | 类型 | 用途 | 必需 | 版本约束 |
|---|---|---|---|---|
| `wd_global_search` | 自研 Odoo addon | `SearchService`、`SearchRequest`、资源描述和导航校验 | 是 | 与目标 Odoo 18 部署使用的服务 API 兼容；精确版本待部署确认 |
| `llm_tool` | Odoo addon | 注册、Schema 校验和执行工具 | 是 | 与 odoo-llm `18.0` 分支兼容；核查 clone commit `609ec6dd`，addon 版本 `18.0.4.1.2` |
| `llm_assistant` | Odoo addon | 专用助手、线程助手关联 | 是 | 与 odoo-llm `18.0` 分支兼容；核查 addon 版本 `18.0.1.5.4` |
| `llm_thread` | Odoo addon（由 `llm_assistant` 依赖） | 聊天线程与工具调用扩展点 | 是 | 与 odoo-llm `18.0` 分支兼容；核查 addon 版本 `18.0.1.4.5` |
| Provider addon（如 `llm_openai`） | Odoo addon | 执行支持 Tool Calling 的 LLM 请求 | 按部署配置 | 与 odoo-llm `18.0` 分支兼容；核查 `llm_openai` addon 版本 `18.0.1.4.0` |

以上版本是当前本地 clone 的核查基线（branch `18.0`，commit `609ec6dda3645165f6a4a843d7af5d286081a29d`），不是任意上游升级的兼容保证。实施前应确认运行实例模块版本与之匹配。桥接采用 `llm_tool` 的注册机制，不依赖 `llm_openai` 的内部 API。部署所选 Provider 必须支持工具调用；Provider 网络超时和重试由对应 provider addon 管理。

### 1.3 关键非功能约束

桥接安全约束对应冻结 SRS 的 `NFR-LLM-01` 至 `NFR-LLM-04`；工具白名单、错误边界及游标校验由本 TDD §12 细化。

## 2 模块目录结构

```text
mymodules/wd_global_search_llm/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── llm_search_tool.py       # 只读工具及请求适配
│   ├── llm_thread.py            # provider 工具列表过滤及当前用户资源描述注入
│   └── mail_message.py          # 工具执行入口白名单校验
├── data/
│   └── llm_assistant_data.xml   # 专用搜索工具 / Assistant 配置
├── tests/
│   ├── test_search_tool.py
│   └── test_tool_allowlist.py
└── docs/
    └── designing/
        ├── SRS_wd_global_search_llm.md
        └── TDD_wd_global_search_llm.md
```

本结构是 v1.0.0 技术设计基线。实现可在不改变服务端执行入口校验等冻结约束的前提下安排文件，但任何技术契约变更须走 TDD 变更流程。

`TD-009` 还要求对现有依赖 addon 做一项向后兼容的接口扩展：`mymodules/wd_global_search/services/facade.py` 的 `_resource_descriptor` 增加 `date_supported` 布尔值，并在 `wd_global_search` 的服务测试中覆盖有 / 无 Business Date 配置的资源。该变更属于 Phase 2 / `CC-WGSL-002` 交付范围，不新增模型或数据库字段。

## 3 ORM 模型设计

### 3.1 模型映射

桥接不创建业务 ORM 模型或持久化搜索历史。工具记录、助手和线程均使用依赖模块既有模型：`llm.tool`、`llm.assistant`、`llm.thread`。

### 3.2 字段契约

无新增数据库字段。工具及助手配置通过 addon 数据记录管理；线程 `tool_ids`、`assistant_id` 是现有字段，桥接只在生成和执行路径做校验，不把其客户端值视为安全授权事实。

### 3.3 方法契约

| 方法职责 | 输入环境 | 输出 / 约束 |
|---|---|---|
| 执行全局搜索工具 | `llm.tool` 注册方法的当前 `env` | 调服务端搜索适配，返回 JSON 可序列化字典 |
| 过滤模型可见工具 | `llm.thread._prepare_chat_kwargs(message_history, use_streaming)` | 专用助手线程只向 provider 暴露搜索工具；方法在 `llm_assistant/models/llm_thread.py` 定义且允许继承扩展 |
| 校验工具执行 | 继承 `mail.message._execute_tool_with_context(tool_name, arguments_str, thread_model=None)` | 专用助手仅允许白名单工具；`llm_tool` 执行时使用原工具记录环境，不提权 |

上述方法签名与调用顺序已通过本地 `odoo-llm` 源码核实；实现阶段仍须以 `TEST-LLM-TOOLS-*` 集成测试确认目标安装版本行为。

## 4 数据约束与索引

无新增表、字段、索引或业务数据迁移。搜索执行使用既有已发布配置和搜索服务约束。

## 5 JSON / 报文 Schema

### 5.1 工具契约

工具名建议使用稳定技术名 `wd_global_search`。复杂嵌套参数使用显式 JSON Schema，并同时由服务端进行语义校验。

| 字段 | 类型 | 规则 |
|---|---|---|
| `query` | string | 必填，作为用户原始意图/关键词；不得超过 SearchService 边界 |
| `resources` | array[string] | 可选；每个 key 必须属于本次当前用户 `resource_descriptors` 返回的资源；省略时桥接使用该响应中的全部资源 key |
| `conditions` | array[object] | 可选；使用现有 `dimension`、`operator`、`value` 形态；不得包含 `model`、`action`、`domain` 或 `relation_expression` |
| `refinement_conditions` | array[object] | 可选；仍须由 SearchService 校验 |
| `limit` | integer | 1–50 的工具默认上限；SearchService 上限为 200，桥接默认取更小值 |
| `cursor` | string | 可选；仅透传 SearchService 签名游标，不自行解码或构造 |

最小条件对象 Schema（合法值按每次用户资源描述动态收窄）：

```json
{
  "type": "object",
  "properties": {
    "dimension": {"type": "string"},
    "operator": {"type": "string"},
    "value": {
      "oneOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {
          "type": "object",
          "properties": {
            "start": {"type": "string", "format": "date"},
            "end": {"type": "string", "format": "date"}
          },
          "required": ["start", "end"],
          "additionalProperties": false
        }
      ]
    }
  },
  "required": ["dimension", "operator", "value"],
  "additionalProperties": false
}
```

`dimension` 对自定义字段必须来自 `resource_descriptors.resources[].searchable_fields[].dimension`；`operator` 必须与该字段描述中的 `operator` 一致（当前可见值为 `=`、`prefix` 或 `contains`）。状态条件仅使用描述中的 `states` 且 operator 为 `=`；多资源状态范围只能使用选中资源状态集合的交集。字段条件只作用于描述中提供该 dimension 的资源；若模型请求的范围包含不支持该 dimension 的资源，桥接应收窄到匹配资源或要求用户澄清，不得把有歧义的条件静默用于其他资源。日期条件使用 `dimension="date"`、`operator="between"` 和 `{start,end}` ISO 日期对象；仅对资源描述标明 `date_supported=true` 的资源启用。若用户选定的资源范围同时包含支持 / 不支持日期条件的资源，桥接必须缩小至支持资源或先澄清，不得静默忽略该条件或资源。SearchRequest 边界不接受通用数组作为 `value`；多个独立条件应使用多个 condition 对象。

`domain_key` 不由模型提供，由桥接固定为服务端常量，见 §12.2 `T-LLM-SEC-002`。

模型可见资源描述每项包含 `key`、`label`、`states`、`searchable_fields` 和 `date_supported`。`date_supported` 是 SearchService 根据该授权资源已发布快照中的 `business_dates` 计算的布尔值；不得向模型暴露底层模型 / 字段名、时区策略或空日期策略。

LLM 可根据用户表达在本次提供给它的资源描述中提出范围；桥接必须重新读取当前用户的资源描述并验证。未指定范围时，桥接显式填入所有当前用户可访问且已发布配置允许搜索的资源 key，因为 SearchService 的空 `resource_scope` 不表示“全部资源”。未授权或已失效的 key 不得被静默忽略后继续搜索；应返回不泄露资源存在性的安全校验结果。

### 5.2 请求和响应映射

桥接直接构造 `SearchRequest(raw_query, parsed_conditions, refinement_conditions, resource_scope, limit, cursor)`，调用 `SearchService.search(env, request, DOMAIN_KEY)`。`DOMAIN_KEY` 固定为经部署确认的域（当前代码默认 `global_search_baseline`），不得由模型或用户请求任意指定。

| `SearchResponse` 来源 | 工具返回字段 | 转换规则 |
|---|---|---|
| `status` | `status` | 原样保留，包括 `SUCCESS`、`EMPTY`、`PARTIAL_SUCCESS`、错误状态 |
| `request_id` | `request_id` | 原样保留 |
| `counts` | `counts` | 原样保留，不由桥接或模型重算 |
| `meta.effective_conditions` | `effective_conditions` | 原样保留服务端认可的有效条件 |
| `results[].id` / `results[]._record_id` | `results[].record_id` | 取服务端记录 ID；不回传内部 `_model`，不得由模型补造 |
| `results[]._resource` | `results[].resource` | 保留资源 key；展示 label 使用本次授权资源描述 |
| `results[].snapshot` | `results[].snapshot` | 保留服务端快照的 `fields`、`rendered_text` 或 `card` 形态，不补读其他字段 |
| `errors` | `errors` | 保留服务端错误码；用户文案由桥接映射，避免暴露内部细节 |
| `meta.next_cursor` | `next_cursor` | 原样透传，不解码、不改写 |
| `resolve_form_navigation(...)` | `results[].navigation_url` | 仅成功时附加，其他状态不返回 URL |

`SearchResponse.results[].snapshot` 没有通用 `display_name` 字段；桥接不应虚构该值。计数、资源 key、记录 ID 和状态来自服务响应，不采信模型自行编造的结果。

对可导航结果，桥接用当前用户环境调用 `resolve_form_navigation(env, resource_key, record_id, DOMAIN_KEY)`。仅当服务端返回 `SUCCESS` 时输出 `navigation_url`；不支持的复合资源或权限校验失败时不生成链接。

## 6 领域行为实现

本 addon 是技术适配层，不创建新的领域服务或业务模型。

### 6.1 服务映射

| 行为 | 具体实现 | 契约 |
|---|---|---|
| 聊天上下文准备 | 专用线程的 `_prepare_chat_kwargs(message_history, use_streaming)` 扩展 | 用当前用户环境读取资源描述并注入 provider 上下文；只暴露描述中列出的资源、字段、状态及日期支持布尔值 |
| 资源发现 | `SearchService.resource_descriptors(env, DOMAIN_KEY)` | 每次工具执行重新读取当前用户可访问且发布配置允许搜索的资源 |
| 搜索 | `SearchService.search(env, SearchRequest, DOMAIN_KEY)` | 不复制过滤、计数或权限逻辑，不经内部 HTTP |
| 链接校验 | `resolve_form_navigation(...)` | 服务端确认记录、动作及当前用户权限 |
| 工具调用 | `@llm_tool` 函数工具注册 | 只读、同步、结果为 JSON 兼容结构 |

### 6.2 伪代码契约

```python
def search_with_current_user(self, query, resources=None, conditions=None,
                             refinement_conditions=None, limit=20, cursor=None):
    env = self.env  # 来自实际聊天工具调用，不接受 uid，不 sudo()
    descriptors = search_service.resource_descriptors(env, DOMAIN_KEY)
    authorized_keys = {item["key"] for item in descriptors["resources"]}
    selected = validate_requested_scope(resources, authorized_keys)
    if resources is None:
        selected = authorized_keys  # 显式全局搜索范围；不传空 tuple
    request = SearchRequest(
        raw_query=query,
        parsed_conditions=tuple(validate_shape(conditions)),
        refinement_conditions=tuple(validate_shape(refinement_conditions)),
        resource_scope=tuple(selected),
        limit=clamp_limit(limit),
        cursor=cursor,
    )
    response = search_service.search(env, request, DOMAIN_KEY)
    return serialize_server_response(env, response)
```

`validate_shape` 只做边界结构检查：顶层参数类型、condition 是对象、`dimension` 和 `operator` 是非空字符串、`value` 存在且为允许的 JSON 标量或日期范围对象，并拒绝执行字段（如 `model`、`action`、`domain`、`relation_expression`）。它不判断某个 dimension/operator/state 是否业务有效；这些候选值来自当前用户上下文中注入的 `resource_descriptors` 描述，最终语义校验由 SearchService 执行。结构错误返回稳定 `INVALID_REQUEST` 工具结果，不抛异常或把 traceback 交给模型/用户。现有 `llm_tool` Schema 是工具记录的输入 Schema；若实现不能按请求动态改写 provider Schema，则固定 Schema 负责类型形状、资源描述上下文给出本次可选值、SearchService 拒绝无效值。

`validate_requested_scope` 只能缩小到授权描述中的资源；请求非法时返回稳定错误，不透露其他用户可访问的资源是否存在。搜索执行仍由 SearchService 做最终配置和权限校验。`clamp_limit` 只将请求限制到桥接默认值与服务端上限之间，不改变搜索含义。

**`TD-009` 冻结决策 — Business Date 支持描述：** `wd_global_search.services.facade._resource_descriptor` 为每个授权资源增加服务端计算的 `date_supported: boolean`，值为 `bool(resource.get("business_dates"))`。只公开是否支持，不公开模型名、字段名、时区行为或 Business Date 私有映射。`resource_descriptors` 返回的资源已按当前用户权限过滤；日期搜索仍由现有 `SearchService.search` 校验和执行。桥接不得从私有配置自行推断，也不得复制日期执行逻辑。无日期映射资源返回 `false`；空资源描述集合安全返回空集合。该响应契约扩展不改变搜索执行语义。

## 7 外部服务 Adapter

桥接 addon 不直接调用外部网络服务，因此自身无外部 Adapter、重试或幂等键。LLM Provider 调用由 `llm_assistant` / 已选 Provider addon 负责。进入实现前应确认部署 Provider 的超时、错误呈现和 Tool Calling 支持；不得在桥接中另行建立 Provider HTTP 客户端。

## 8 异步队列、Worker、Cron

### 8.1 执行方式评估

搜索为聊天请求内同步只读调用；没有本地后台任务、重试队列或定时工作。用户可见的 LLM 生成由 `llm_thread` 现有流式请求负责。单次搜索超时继承 SearchService 的边界；Provider 超时由 Provider addon 管理。

### 8.2 队列 / Worker

不适用：桥接不持久化待执行任务。

### 8.3 Cron

不适用：无周期性工作。

### 8.4 可靠投递

不适用：无异步消息投递或需要与业务提交保持一致的任务。聊天断连和 LLM 重试策略归属 `llm_thread` / Provider addon。

## 9 状态机技术态

不适用：桥接不创建执行状态模型。单次请求状态取 SearchResponse 的 `status`，工具执行状态由 `llm_tool` 现有工具消息生命周期管理；桥接不得重定义其枚举。

## 10 并发、事务与锁

### 10.1 并发策略

桥接无共享可变业务状态，不增加锁。并发请求由 Odoo 请求事务及 SearchService 既有每用户限流、游标上下文校验和超时机制管理。

### 10.2 Guardrails

搜索方法不得执行写业务数据；不得在工具方法中跨线程保存当前用户授权快照；每次调用重新取资源描述并让 SearchService 重新校验。

### 10.3 幂等

搜索为只读操作，重复调用不产生业务副作用。游标由 SearchService 签名并绑定用户上下文；桥接不重放或改写游标内容。

## 11 异常、错误码与告警

| 情况 | 对聊天返回 |
|---|---|
| 参数格式或范围无效 | 稳定的 `INVALID_REQUEST` 类结果；不返回 traceback |
| 资源、字段或条件未获当前用户授权 | 由 SearchService 返回的权限/请求错误；不扩权、不改用 `sudo()` |
| 无结果 | 保留 SearchService `EMPTY` 和真实计数 |
| 部分资源失败 | 保留 `PARTIAL_SUCCESS`、错误资源和已成功结果 |
| 限流或超时 | 保留服务端状态；不把错误伪装成无命中 |
| 工具白名单失败 | 拒绝执行，写受控诊断日志，不返回内部实现细节 |
| 搜索配置不可用 | 返回配置不可用的安全提示，不猜测默认模型/字段 |

工具白名单校验失败的默认安全文案建议为“此助手仅支持全局搜索，请重新发起搜索。”，不暴露工具名、线程配置或内部异常。其他错误文案、用户澄清行为和部分成功呈现方式需在桥接 SRS 中确定。

## 12 安全与权限

### 12.1 权限映射

| 操作 | 身份和权限来源 |
|---|---|
| 聊天生成 | `/llm/thread/generate` 的登录用户；源码以原 `env.uid` 和 `env.context` 重建环境 |
| 工具执行 | 关联 `llm.thread` 的 `self.env`；源码路径未对工具执行调用 `sudo()` |
| 搜索资源和记录 | 将工具当前 `env` 原样交给 SearchService；沿用 ACL、Record Rules、资源配置和字段授权 |
| 搜索配置读取 | SearchService 按其现有实现读取已发布配置；桥接不得自行复制或提升权限 |
| 表单链接 | `resolve_form_navigation` 在当前用户环境检查记录访问及动作；其内部对动作元数据的 sudo 读取不代表业务记录权限提升 |

以上结论来自源代码审查，不等同于目标数据库上的运行时权限证明；须由集成验证确认。

### 12.2 安全 Guardrails

| 编号 | 规则 |
|---|---|
| `T-LLM-SEC-001` | 搜索工具只能使用当前线程用户环境，禁止对业务模型或 SearchService 使用 `sudo()` |
| `T-LLM-SEC-002` | 搜索域固定为服务端常量；不得由模型传递任意 `domain_key` |
| `T-LLM-SEC-003` | 资源 key 必须属于本次 `resource_descriptors`；SearchService 保留最终授权判断 |
| `T-LLM-SEC-004` | 专用助手的 provider 请求只暴露搜索工具；执行入口再次校验助手身份和工具白名单 |
| `T-LLM-SEC-005` | `read_only_hint` 仅作工具元数据；只读属性必须由实现代码和服务端白名单保证 |
| `T-LLM-SEC-006` | 模型不能产生命中数、有效条件、record ID 或导航 URL；这些值只能来源于服务端搜索结果/导航校验 |
| `T-LLM-SEC-007` | 结果只输出搜索服务提供的可见快照字段；禁止补读未配置字段或绕过字段权限 |
| `T-LLM-SEC-008` | 错误和日志不得暴露 token、内部异常、SQL、受限资源清单 |

资源描述注入发生在专用线程构造 provider 请求时；该处只使用当前用户环境生成上下文，并同步过滤 `thread.tool_ids`。工具实际执行时重新获取 descriptors，防止提示词与调用之间权限或发布配置变化。两层校验的具体扩展点如下：

| 层 | 桥接实现文件 | Odoo 模型 | 重写方法 | 校验内容 |
|---|---|---|---|---|
| Provider 工具列表过滤 + 用户资源描述注入 | `models/llm_thread.py` | `llm.thread` | `_prepare_chat_kwargs(self, message_history, use_streaming)` | 对专用 `assistant_id` 只传搜索工具；用当前用户 descriptors 构造可见资源/字段/状态上下文 |
| 实际工具执行白名单 | `models/mail_message.py` | `mail.message` | `_execute_tool_with_context(self, tool_name, arguments_str, thread_model=None)` | 在 `super()` 之前检查线程助手身份和工具名；非白名单调用拒绝 |

以上方法名取自当前核查的 odoo-llm `18.0` 源码。升级上游后须重新核实签名和调用顺序。仅靠助手 XML 配置、前端隐藏、`read_only_hint` 或 provider Schema 均不充分。

## 13 UI 契约

MVP 复用 `llm_thread` 原生聊天界面，通过数据记录提供专用搜索工具和 Assistant。暂不新增结果卡片、搜索工作区或 Owl 组件。由于现有线程 UI 可修改 `tool_ids`，UI 可见工具列表不作为安全控制；服务端双重白名单为强制约束。结果卡片和更丰富的分页交互需由 SRS 决定是否纳入后续阶段。

## 14 测试设计

### 14.1 测试分层

采用 Odoo `TransactionCase` 验证工具适配、资源授权及 SearchService 交互；工具白名单用线程 / 工具执行路径集成测试验证。按冻结 SRS 和 Implementation Plan 决定是否需要浏览器端到端验证。

### 14.2 追溯要求

冻结 SRS 的所有 AC、§18 的关键安全门禁都必须对应自动化验证。桥接代码尚未实现，测试矩阵项均为 NOT RUN；不得将设计测试项表述为通过。

### 14.3 测试矩阵

| TEST | 契约 | Given / When / Then | 状态 |
|---|---|---|---|
| `TEST-LLM-ENV-001` | `T-LLM-SEC-001`、`AC-01` | 普通用户发起搜索工具调用；SearchService 接收同一 uid/context 并返回真实搜索结局 | NOT RUN — 实施验证 |
| `TEST-LLM-RES-002` | `T-LLM-SEC-003`、`AC-02` | 请求包含未在当前用户资源描述中的 key；不得搜索该资源或泄露其存在 | NOT RUN — 实施验证 |
| `TEST-LLM-TOOLS-003` | `T-LLM-SEC-004`、`AC-07` | 修改线程 `tool_ids` 加入创建/更新工具；provider 列表不含它，伪造调用被执行入口拒绝且业务记录保持不变 | NOT RUN — 实施验证 |
| `TEST-LLM-COND-004` | `T-LLM-SEC-006`、`AC-04` | 提交不支持的状态/字段，或在混合支持 / 不支持日期的资源范围使用日期条件；澄清 / 拒绝前不猜值、不静默丢弃条件或资源 | NOT RUN — 实施验证 |
| `TEST-LLM-RESULT-005` | `T-LLM-SEC-006/007`、`AC-05` | 工具响应中的 count、condition、id、snapshot 与 SearchResponse 一致 | NOT RUN — 实施验证 |
| `TEST-LLM-LINK-006` | `T-LLM-SEC-006`、`AC-05` | 单模型可访问记录产生经校验链接；无权、删除或复合资源不输出 URL | NOT RUN — 实施验证 |
| `TEST-LLM-PAGE-007` | §5.2 | 用户上下文变更后重放先前 next_cursor；SearchService 拒绝该游标，不返回跨上下文结果 | NOT RUN — 实施验证 |
| `TEST-LLM-NORMAL-008` | `T-LLM-002`、`AC-01` | 配置一条可读命中记录；提交普通关键词；工具结果与 SearchService 的真实命中、计数和快照一致 | NOT RUN — 实施验证 |
| `TEST-LLM-MULTI-009` | `T-LLM-002/003` | 用户对多个授权资源发起全局搜索；返回跨资源聚合结果和由服务端生成的分类/总计数 | NOT RUN — 实施验证 |
| `TEST-LLM-CURSOR-010` | §5.2 | 首次调用返回 next_cursor；同一用户上下文使用该游标继续请求时页次连续、结果不重复且映射正确 | NOT RUN — 实施验证 |
| `TEST-LLM-EMPTY-DESC-011` | `T-LLM-003` | 当前用户 resource_descriptors.resources 为空；返回安全的空范围结果，不抛异常、不传空 scope 执行“全资源”搜索 | NOT RUN — 实施验证 |
| `TEST-LLM-DATE-DESC-012` | `TD-009`、`T-LLM-003` | 已配置 Business Date 的授权资源描述为 `date_supported=true`，未配置资源为 `false`；公开描述不泄露映射字段及策略 | NOT RUN — 实施验证 |
| `TEST-LLM-AND-013` | `BR-LLM-02`、`AC-03` | 提交两个受支持条件；只返回同时满足全部条件的真实命中，并回显服务端有效条件 | NOT RUN — 实施验证 |
| `TEST-LLM-OUTCOME-014` | `FR-LLM-06`、`AC-06` | 分别模拟 EMPTY、PARTIAL_SUCCESS 和 FAILED / unavailable；用户反馈能区分无命中、部分失败和服务不可用，部分成功保留 | NOT RUN — 实施验证 |
| `TEST-LLM-INTENT-015` | `FR-LLM-01`、`AC-08` | 提交无法识别为搜索意图的输入；请求澄清且不调用搜索、不生成虚构记录 | NOT RUN — 实施验证 |
| `TEST-LLM-REFINE-016` | `FR-LLM-08`、`AC-09` | 上一条搜索成功后，用户明确追问；只继承已确认条件并应用新条件；新主题或失败搜索不继承 | NOT RUN — 实施验证 |
| `TEST-LLM-CONFLICT-017` | `BR-LLM-03`、`AC-10` | 提交互斥日期范围或状态；先澄清，澄清前不执行二选一搜索 | NOT RUN — 实施验证 |
| `TEST-LLM-FAILURE-018` | `FR-LLM-06`、`AC-06` | 搜索服务异常；回复明确表示暂时无法完成，不伪装为零结果，不暴露内部异常 | NOT RUN — 实施验证 |

## 15 可观测性

搜索请求的 `request_id`、SearchService 状态和延迟由既有搜索服务记录。桥接日志只记录工具名、线程 ID、请求 ID、结果状态和耗时等最少诊断信息；不记录完整原始提示、敏感结果快照、token 或模型密钥。日志保留和访问策略继承部署方现行 Odoo 日志基线，待 SRS 明确用户审计要求。

## 16 部署与运行前置

### 16.1 运行前置

| 前置 | 要求 |
|---|---|
| Odoo addons path | 同时包含 `mymodules`、`mymodules/odoo-llm` |
| 已安装模块 | `wd_global_search`、`llm_thread`、`llm_tool`、`llm_assistant` |
| Provider | Assistant 配置到支持 Tool Calling 的模型；OpenAI 部署需安装并配置 `llm_openai` |
| 已发布搜索配置 | `global_search_baseline` 存在有效已发布版本；当前用户可以没有可搜索资源，桥接须按 §14.3 安全处理空资源描述 |
| 搜索域确认 | 已确认桥接固定的 `DOMAIN_KEY` 与部署环境一致，且该域存在有效已发布配置；当前拟值 `global_search_baseline` |
| 兼容版本 | Odoo 18.0、Python 3.11（本工作区 3.11.9）、PostgreSQL 客户端 16.14；目标部署实例的 Python / PostgreSQL 服务端准确版本须在实施计划基线前登记并确认兼容 |

### 16.2 配置项

| 配置 | 载体 | 默认 / 限制 |
|---|---|---|
| 专用搜索助手 | `llm.assistant` 数据记录 | 绑定唯一搜索工具；面向用户的名称与提示词按已冻结 SRS 的交互边界配置 |
| 搜索工具 | `llm.tool` 装饰器注册记录 | 只读实现；固定工具标识 |
| 搜索域 | 桥接模块常量 | `global_search_baseline`；须经 §16.1 部署前置确认 |
| 最大结果数 | 工具参数服务端 clamp | 建议默认 20；不得超过 SearchService 接受上限 |

### 16.3 数据迁移

无桥接业务数据表，No Migration。Addon 安装时新增助手/工具配置记录，卸载/升级行为需通过 Odoo 模块数据定义及实际升级流程验证；不得删除用户历史聊天。

## 17 技术风险与防护

| 风险 | 触发条件 | 防护 |
|---|---|---|
| 原 SRS 明确排除 LLM | 将本文误当作既有需求授权 | 桥接 SRS v1.0.0 独立冻结；本 TDD 仅针对桥接 addon，不扩展既有 SRS |
| 用户修改线程工具列表 | `tool_ids` 写入其他工具 | provider 列表过滤 + 执行入口白名单；两者均服务端实施 |
| 资源或字段范围误判 | 模型虚构 key、字段、状态或提示上下文已过期 | 每次从当前用户 descriptors 派生/验证范围，SearchService 做最终校验 |
| 工具结果被模型改写 | 摘要与真实 count、ID、链接不一致 | UI/调用方以工具结构化结果作为事实来源；模型文本只作解释 |
| provider 无 Tool Calling 或 schema 兼容 | 模型不能正确生成工具调用 | 选择兼容 provider；真实 provider 的 schema、流式调用须集成验证 |
| 搜索条件跨资源不兼容 | 字段只在部分资源有效 | 依 SearchService 的错误/部分成功协议返回；产品处理策略由 SRS 决定 |
| `resolve_form_navigation` 不支持复合资源 | 多模型结果 | 不输出链接；后续 UI 能力另行评审 |

## 18 Implementation Guardrails / Coding Contract Baseline

以下规则为本 TDD 冻结的 Coding Contract 技术基线；实施阶段的 CC 必须引用其适用项。

| 编号 | 规则 | 强度 |
|---|---|---|
| `T-LLM-001` | 工具实现不得使用 `sudo()` 搜索业务记录；`SearchService` 必须接收线程用户 `env` | MUST |
| `T-LLM-002` | 桥接必须直调 `SearchService`，不得复制搜索执行逻辑或用内部 HTTP 调用 | MUST |
| `T-LLM-003` | `domain_key` 由服务端固定；资源范围仅来自当前用户授权 descriptors | MUST |
| `T-LLM-004` | 专用助手 provider 工具列表与工具执行入口都必须校验白名单 | MUST |
| `T-LLM-005` | 模型只提供搜索意图和候选条件；计数、有效条件、记录身份和 URL 必须来自服务端 | MUST |
| `T-LLM-006` | 仅返回配置快照允许且当前用户可读的结果字段 | MUST |
| `T-LLM-007` | 任何失败不得通过扩大范围、改变用户环境或改用 `sudo()` 降级 | MUST |
| `T-LLM-008` | `read_only_hint`、前端隐藏和 Assistant 默认 `tool_ids` 均不得作为唯一执行授权 | MUST |

每个 Coding Contract 应引用本次适用的规则、变更文件范围和 §14 测试项；须在实施计划门禁通过后创建。

## 19 需求追溯矩阵

### 19.1 上游输入 → TDD

| 上游输入 | 类型 | 本 TDD 落地 | 状态 |
|---|---|---|---|
| SRS Global Search V1.5 的 LLM / 完整 NL 明确排除项 | 冻结 SRS 约束 | §0.2：桥接需求必须独立建立基线；本 TDD 不扩展既有业务范围 | 已核对既有 SRS |
| Bridge SRS v1.0.0 Frozen | 冻结桥接业务基线 | §5–§18 技术设计与 SRS AC / NFR 建立追溯 | 已冻结；TDD v1.0.0 依赖 |
| TV-LLM-01/02 | 源码级技术验证 | Business Date 元数据来源、资源权限过滤、线程工具列表钩子和执行入口签名 | CLOSED — 见 [TV_wd_global_search_llm.md](../../../../docs/verification/TV_wd_global_search_llm.md)；运行时集成验证留在实施阶段 |
| 用户确认：直调 SearchService、保留当前用户、不扩展资源、服务端生成可信结果 | 技术设计输入；相关业务含义映射至冻结 SRS | §5、§6、§12、§18 | 用户批准并纳入冻结 TDD |
| 用户确认：专用助手只读且双层工具白名单 | 技术设计输入；业务只读对应 `FR-LLM-07` / `NFR-LLM-04` | §12.2、§14.3、§18 | 用户批准并纳入冻结 TDD；尚未实现/运行验证 |

现有 Global Search SRS 不涵盖桥接功能需求；桥接 SRS v1.0.0 独立冻结。TDD 的技术约束仅用于实现该桥接需求，不改变现有全局搜索 SRS。

### 19.2 TDD → TEST

| TDD 契约 | 验证 | 状态 |
|---|---|---|
| `T-LLM-001` / `T-LLM-003` | `TEST-LLM-ENV-001`、`TEST-LLM-RES-002`、`TEST-LLM-EMPTY-DESC-011` | NOT RUN — 未实现 |
| `T-LLM-004` / `T-LLM-008` | `TEST-LLM-TOOLS-003` | NOT RUN — 未实现 |
| `T-LLM-005` / `T-LLM-006` | `TEST-LLM-RESULT-005`、`TEST-LLM-LINK-006` | NOT RUN — 未实现 |
| 分页上下文校验 | `TEST-LLM-PAGE-007`、`TEST-LLM-CURSOR-010` | NOT RUN — 未实现 |
| `T-LLM-002` / `T-LLM-003` | `TEST-LLM-NORMAL-008`、`TEST-LLM-MULTI-009`、`TEST-LLM-AND-013` | NOT RUN — 未实现 |
| `TD-009` 日期描述契约 | `TEST-LLM-DATE-DESC-012` | NOT RUN — 未实现 |
| `T-LLM-SEC-006` | `TEST-LLM-COND-004`、`TEST-LLM-OUTCOME-014`、`TEST-LLM-FAILURE-018` | NOT RUN — 未实现 |
| `FR-LLM-01`、`FR-LLM-08`、`BR-LLM-03` | `TEST-LLM-INTENT-015`、`TEST-LLM-REFINE-016`、`TEST-LLM-CONFLICT-017` | NOT RUN — 未实现 |
| `T-LLM-SEC-004` | `TEST-LLM-TOOLS-003`；白名单拒绝用 §11 默认安全文案并记录受控诊断 | NOT RUN — 未实现 |

## 附录 A 术语表

| 术语 | 含义 |
|---|---|
| 桥接工具 | `llm_tool` 注册的只读函数，将聊天输入转换为现有搜索请求 |
| 用户环境 | Odoo `env` 中当前请求用户、上下文和公司信息 |
| 资源描述 | SearchService 按发布配置和当前用户权限返回的可搜索资源元数据 |
| 双层工具白名单 | Provider 请求工具列表过滤和服务端执行入口再次校验 |

## 附录 B 技术决策记录

| 编号 | 冻结决策 | 选项评估 | 理由 | 章节 |
|---|---|---|---|---|
| `TD-001` | 新建独立 addon `wd_global_search_llm` | 合并进搜索模块 / 合并进 LLM 模块 / 独立桥接 | 保持依赖可选、职责边界清楚 | §1–2 |
| `TD-002` | 直接调用 SearchService | 内部 HTTP / 复制搜索逻辑 / Python 服务调用 | 同进程复用事务、用户环境和既有校验 | §5–6 |
| `TD-003` | 搜索执行只使用当前线程用户 `env` | 使用服务账号或 `sudo()` | 保持 ACL、Record Rules 和用户上下文 | §12 |
| `TD-004` | 专用 Assistant + provider 列表过滤 + 执行入口校验 | 仅依赖 XML 默认配置或 UI 限制 | 线程工具列表可编辑，元数据标记不执行授权 | §12.2 |
| `TD-005` | 资源范围由每次调用的用户 descriptors 限定 | 让模型任意传资源/model/domain | 防止越权扩展并复用 SearchService 最终校验 | §5–6 |
| `TD-006` | 只把服务端结果字段视为可信事实 | 让模型生成 count、ID 或链接 | 避免编造搜索结果及导航地址 | §5.2、§12 |
| `TD-007` | MVP 不新增聊天 UI | 新建结果卡片 / 前端搜索工作区 | 先复用原生聊天和工具输出，展示需求待 SRS 决定 | §13 |
| `TD-008` | 桥接不绑定 OpenAI provider | 强制依赖 `llm_openai` | Tool Calling 由 Assistant/provider 能力决定，桥接保持 provider-agnostic | §1.2 |
| `TD-009` | SearchService 资源描述增加服务端计算的 `date_supported: boolean` | 从私有配置推断 / 未经描述直接暴露日期条件 / 移除日期搜索 | 用户资源描述由已授权快照生成；只披露能力，不泄露日期字段配置；搜索语义仍由 SearchService 执行 | §5.1、§6.2 |

上述决策由用户于 2026-10-15 明确批准并随 TDD v1.0.0 冻结。`TD-009` 的代码变更和 `TEST-LLM-DATE-DESC-012` 属后续 CC 实施与验证范围，不代表已修改或验证运行时代码。

## 附录 C 版本变更记录

| 版本 | 日期 | 变更摘要 | 决策人 |
|---|---|---|---|
| v0.1.0 | 2026-10-15 | 创建技术核查稿；记录 SearchService/llm_tool 接口、权限边界、双重白名单和未决上游需求 | Draft；未批准 |
| v0.1.1 | 2026-10-15 | 根据评审补充 Draft 效力边界、工具 Schema 与响应映射、白名单扩展点、错误文案、正常路径测试和追溯；记录 TD-009 未决项 | Draft；未批准 |
| v0.1.2 | 2026-10-15 | 新增桥接 SRS v0.1.0 Draft 上游引用，明确其未批准 / 未冻结，更新需求追溯和 SRS 基线门禁 | Draft；未批准 |
| v0.1.3 | 2026-10-15 | 更新上游需求至 SRS v0.1.1 Draft，记录多轮追问、条件冲突及只读 / 可信事实要求仍待业务批准 | Draft；未批准 |
| v1.0.0 | 2026-10-15 | 用户批准 SRS v1.0.0 与 TDD 冻结；闭合 TD-009，固定 `date_supported` 描述契约、工具调用扩展点及桥接实现门禁 | 用户明确批准（本对话） |

## 填写自查清单

- [x] TDD 母模板同步检查通过（2026-10-15）。
- [x] 所有模板适用性项目均有结论；无 ORM 新模型、异步任务、Cron、状态机或历史数据迁移，并说明理由。
- [x] 技术决策已记录为 `TD-001` 至 `TD-009`，并由用户明确批准冻结。
- [x] LLM 在既有搜索 SRS 中属于排除项；桥接 SRS v1.0.0 是独立冻结基线，不扩展既有业务范围。
- [x] 权限、结果、白名单和链接测试已列出，尚无桥接代码的实施测试明确标为 NOT RUN。
- [x] 桥接 SRS v1.0.0 已批准并冻结。
- [x] TDD v1.0.0 已由用户明确批准并冻结。
- [x] 工具名、固定域、资源默认范围、只读边界及交互最低验收要求均在 SRS / TDD 有明确契约。
- [x] 技术栈基线已明确为 Odoo 18.0、Python 3.11.9（本地）、PostgreSQL 客户端 16.14；目标实例的精确服务端版本作为实施计划 / 首个 CC 前置条件登记并核对兼容。
- [x] Implementation Plan v0.4 当前仍是 Draft；该下游门禁已明确记录，计划获批并通过首个 CC gate 前不得创建 CC 或进入编码。
