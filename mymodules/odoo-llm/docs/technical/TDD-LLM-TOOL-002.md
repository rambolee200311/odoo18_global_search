# `odoo_record_retriever` 工具 Schema 技术设计说明书（TDD）

> 文档版本：v1.0.0
> 状态：Frozen（已批准冻结；本文件是 CC-LLM-TOOL-002 的技术实施基线）
> Intent：`CC-LLM-TOOL-002`
> 模块：`llm_tool`；OpenAI Schema 消费方：`llm_openai`
> 日期：2026-10-16
> 工作区集成基线：根仓库 commit `55a930fbb234f9b82c4a9a3f6292b8f081ac956a`；嵌套上游源码 checkout `mymodules/odoo-llm` HEAD `609ec6dda3645165f6a4a843d7af5d286081a29d`
> 技术模板：`docs/skill/odoo-project-workflow/references/templates/Designing/TDD模板.md` v1.0.0 Frozen（同步检查通过）
> 冻结批准：用户于 2026-10-16 明确批准冻结

## 0. 文档说明

### 0.1 文档定位

本文定义 `odoo_record_retriever` 动态参数 Schema 的生成、Provider Schema 转换和运行时参数校验契约，不定义新业务流程或数据模型。

### 0.2 上游基线与适用性

| 项目 | 基线 / 状态 |
|---|---|
| SRS | N/A：与 CC §2.1 一致；这是既有工具契约的技术兼容性修复，不增加业务流程或业务语义 |
| DDD | N/A：不引入领域概念、聚合或业务不变量 |
| 技术核查 | `TV-LLM-TOOL-002-01` v0.2 草稿；已核实 MCP Schema 导入不兼容和 OpenAI 转换语义损坏；历史两次运行仍无法逐项比较 |
| CC | `CC-LLM-TOOL-002` v0.5 草稿；须引用本 TDD 基线，并完成适用计划门禁后另行冻结 |

### 0.3 冻结与变更

本文已由用户批准冻结，版本为 v1.0.0。SRS N/A 适用性与 CC §2.1 对齐。冻结后的偏移必须按工作流授权并反向生成新 TDD 版本；CC 和实施须引用本冻结基线，不得继续引用先前草稿。

## 1. 技术上下文与基线

| 层次 | 当前基线 | 说明 |
|---|---|---|
| Odoo | 18.0 | 当前项目运行版本 |
| Python | 3.11.9 | 仓库 `venv` 运行时 |
| MCP | 2.3.0 | 当前代码引用的 FastMCP 1.x 导入路径不可用；本 TDD 只修复该路径导致的 Schema 生成失败，不评估或修改其他 MCP 协议类型；其他功能仍使用该依赖 |
| Pydantic | 2.13.4 | 用于当前签名参数校验，也可生成 JSON Schema |
| OpenAI SDK | 2.54.0 | 本设计不升级 SDK，只调整传给它的工具 Schema |
| PostgreSQL | 16.14 | 从 `odoo-bin shell -c odoo.conf` 当前连接元数据只读获取；本设计不改表和数据 |

这些版本来自当前仓库 `venv` 和 Odoo shell。实施开始前须再次确认实际服务运行环境。不得 pin / downgrade 全局 MCP 包，也不得删除该依赖，因为其他代码仍使用 `mcp.types` 及 MCP server 功能。其他 MCP API 路径若有不兼容问题，应另开 TDD 处理，不纳入本范围。

## 2. 模块目录与影响范围

代码变更候选严格限定到下表中的方法；不授权修改整文件：

| 路径 | 方法 / 元素 | 具体变更 | 修改边界 |
|---|---|---|---|
| `llm_tool/models/llm_tool.py` | `get_input_schema()` | 移除 FastMCP 1.x 导入路径；存储 Schema 为空时由签名 Pydantic model 生成；非法存储 Schema 报错停止 | 不改其他 `llm.tool` 行为 |
| `llm_tool/models/llm_tool.py` | `get_pydantic_model_from_signature()` | 当前源码不依赖 MCP，TV 已成功用该函数派生 Schema；本设计默认不改此方法 | 只有测试证明其本身有缺陷时，先修订 TDD / CC |
| `llm_tool/models/llm_tool.py` | `execute()` | 当前无已核实缺陷，默认不改；用于验证 Schema/runtime parity | 若符合 Schema 的 Provider 参数却被错误拒绝，暂停并重新定界 |
| `llm_openai/models/openai_provider.py` | `_openai_format_tool()` | 生成 / 转换失败时不再返回空 `properties` / `required` fallback；抛受控错误阻止 HTTP 请求 | 仅影响 OpenAI 工具 Schema 组装 |
| `llm_openai/models/openai_provider.py` | `_recursively_patch_schema_items()` | 移除向 union 节点猜测补 `type: string` 的行为，保留 `anyOf` 语义 | 不改变消息或工具循环 |
| `llm_openai/models/openai_provider.py` | `_create_openai_tool_from_schema()` | 以不改变输入对象语义的方式构造 `parameters`；不静默丢弃约束 | 仅按 Schema 转换契约调整 |
| `llm_tool/tests/`、`llm_openai/tests/` | 精确测试文件 / 方法 | 增加第 14 节列出的生成、转换、错误通路与 E2E 验证 | 不改无关测试 |

不修改 XML 数据、manifest 依赖、公共工具 API、模型字段、权限、`llm_thread`、`llm_assistant`、界面或搜索桥接。若实施证据要求扩大范围，必须暂停并修订 TDD / CC。

## 3. ORM 模型设计

不适用。无新模型、字段、关系或 ORM 行为；继续使用现有 `llm.tool.input_schema`。

## 4. 数据约束与索引

不适用。无数据库结构、索引、约束或迁移；不回填或修改现有 `input_schema` 记录。

## 5. JSON Schema 契约

### 5.1 Schema 来源及优先级

1. 若 `input_schema` 非空，则解析并校验其 JSON object。该字段表示管理员显式配置；解析或结构校验失败必须报受控错误，不得静默回退。
2. 若 `input_schema` 为空，则解析工具实现 callable，使用现有 `get_pydantic_model_from_signature()` 创建 Pydantic model，再用 `model_json_schema(by_alias=True)` 生成 Schema。
3. Schema 生成不再导入 `mcp.server.fastmcp.utilities.func_metadata`。生成和 `execute()` 参数校验共用同一签名模型来源。

源码核查确认 `get_pydantic_model_from_signature()` 只依赖 Python 类型签名与 Pydantic，不依赖 MCP；TV 已实际调用该方法生成 Schema。当前 `venv` 中的 Pydantic 2.13.4 接受 `model_json_schema(by_alias=True)` 并成功返回 Schema。因此本次不需要修改签名模型生成方法，也不新增 MCP 兼容性目标。

### 5.2 当前 fallback 与目标 Schema 对比

| 参数 | 当前 `input_schema` 为空时的 Provider fallback | 目标 Provider Schema |
|---|---|---|
| `model` | 不在 `properties` 中，也不在 `required` 中 | `properties.model.type=string` 且 `required=["model"]` |
| `domain` | 不在 `properties` 中 | array；内部数组元素保留字符串 / 整数 / 布尔 / 数字 / null 的 union |
| `fields` | 不在 `properties` 中 | string array，默认 `[]` |
| `limit` | 不在 `properties` 中 | integer，默认 `100` |

### 5.3 `odoo_record_retriever` 参数语义

| 参数 | Callable 语义 | Provider Schema / 执行要求 |
|---|---|---|
| `model: str` | 无默认值 | 必填字符串；缺失时失败，不猜测默认模型 |
| `domain: list[list[str \| int \| bool \| float \| None]] = []` | 可省略 | 嵌套列表的类型和 union 分支必须与签名兼容；不得改变 `anyOf` 节点语义 |
| `fields: list[str] = []` | 可省略 | 字符串数组；省略时沿用空列表默认值 |
| `limit: int = 100` | 可省略 | 整数；省略时沿用 `100` 默认值 |

Schema 的 `required` 必须与 callable 中没有默认值的参数完全一致。可选参数省略后的执行语义必须与 callable 默认值一致。字段描述不得承诺 callable 未实现的搜索或权限语义。

### 5.4 OpenAI function Schema 转换

保留现有 Chat Completions function tool 外层结构。转换后的 `parameters` 必须保留会影响运行语义的 `type`、`properties`、`required`、`items`、`anyOf` / 其他支持的组合、`enum`、`description` 和 `default`。转换不得原地修改源 Schema，不得删除或猜测补写类型。避免原地修改是为了防止同一 Schema 多次转换时语义漂移，并便于测试明确比较转换前后的结构与语义。

技术核查已发现当前递归 patch 会给含 `anyOf` 的数组元素节点添加 `type: string`，改变其 union 语义。修复需用固定期望 Schema fixture 验证转换前后的含义一致。无法保留某项约束时，必须在请求发出前明确失败；不得生成空 `properties` / `required` 后继续请求。

本设计不假定所有 OpenAI-compatible Provider 都接受该 union 结构。须通过获准的 Provider E2E 验证远端接受情况。若真实 Provider 拒绝 union Schema，候选方向包括简化 `domain` 参数类型、迁移 Responses API，或暂停并重新设计；这些选择会改变本 TDD 的契约或范围，当前均不授权实施，必须先修订并重新冻结 TDD / CC。不能静默弱化 Schema。

## 6. 行为实现

### 6.1 调用流程

```text
get_input_schema(tool):
  如果 input_schema 非空：
      解析 JSON 并校验根节点为 object；失败则抛受控错误，停止当前 Provider 请求
      记录失败阶段和错误码，不记录 Schema 内容；Provider HTTP 调用次数必须为零
  否则：
      取得工具 callable
      使用 get_pydantic_model_from_signature(callable) 生成 model
      用 model.model_json_schema(by_alias=True) 生成 Schema
  返回已校验 Schema

_openai_format_tool(tool):
  schema = get_input_schema(tool)
  parameters = 保持语义的 Schema 转换(schema)
  转换失败时：在 HTTP 请求前抛出受控错误
  返回 OpenAI function tool 定义

execute(arguments):
  用 callable 签名构造同一 Pydantic model
  校验参数
  以校验后的值调用 callable
```

### 6.2 错误处理

Schema 解析、生成或转换失败时，必须阻止当前带工具的 Provider 请求进入 HTTP client。源码中的现有路径是 `llm_assistant/models/llm_thread.py:_generate_assistant_response()` 捕获 Provider 调用异常，再调用 `llm_thread/models/llm_thread.py:_post_error_message()` 将 `str(error)` 显示到聊天消息。因此 Schema 层必须抛出不含内部细节的受控异常文案；不能把底层解析异常、原始 Schema 或 Python traceback 直接传到该路径。`TEST-LLM-TOOL-011` 将故意触发 Schema 转换失败，断言聊天产生受控错误消息、Provider HTTP mock 调用次数为零，且错误消息不含 traceback、文件路径、凭据、完整 Schema 或业务数据。若当前异常路径无法满足这些断言，应停止并修订 TDD，不得自行新增界面或 API。

Provider 返回 `{}`、格式错误参数或不符合 callable 签名的参数，继续由现有 JSON / Pydantic 校验拒绝。只有参数校验通过后才能搜索业务模型。日志只记录工具技术名称、失败阶段和受控错误码。

### 6.3 根因分类标准

| 观察结果 | 判定 |
|---|---|
| 源 Schema 缺少必填 / 类型定义，或 Schema 生成报错 | Schema 生成缺陷 |
| 源 Schema 正确，但序列化到 Provider `tools` 后语义改变或变为空 fallback | Schema 转换缺陷 |
| 发给 Provider 的 Schema 正确，但 Provider 返回不符合 Schema 的参数 | Provider 参数生成行为；留证，不归咎于 Odoo runtime |
| Provider 参数符合 Schema，但 `execute()` 校验拒绝 | Odoo 运行时参数校验缺陷；按实际偏差修复或重新定界 |
| 历史运行缺模型行、Schema 或 commit | 未知；不能推断具体配置导致成功或失败。历史归因未知写入 ATR，不阻塞针对当前已复现 Schema 缺陷的修复与验收 |

## 7. 外部服务 Adapter

不新增 Adapter、HTTP endpoint 或 Provider。现有 OpenAI Chat Completions 客户端只接收已校验的工具 Schema；Schema 错误须发生在请求发出前。MCP 包保留给现有协议类型和 server 功能。

## 8. 队列、Worker、Cron

不适用。工具 Schema 在同步聊天请求中生成，不新增队列、Worker、Cron 或可靠投递机制。

## 9. 状态技术态

不适用。不引入持久化状态机或新的工具执行状态；继续使用现有 `requested / executing / completed / error` 消息状态，本设计不改变这些状态的含义。

## 10. 并发、事务与锁

不增加锁、并发或事务机制，沿用当前聊天事务和工具执行 savepoint。Schema 校验失败发生在 Provider HTTP 请求前；参数校验失败发生在业务模型搜索前。

## 11. 异常、错误码与告警

不新增公共错误码。Schema 解析、生成或转换错误归类为工具定义配置 / 服务端 Schema 错误，使用现有受控 Odoo 错误路径，必要时只增加内部稳定诊断标识。日志不得记录密钥、Prompt、业务参数值、完整 Provider payload 或返回记录。如果实现时发现现有错误通路无法安全展示，应触发 TDD 变更，不得在 CC 内扩大范围。

## 12. 安全与权限

- 不增加 `sudo()`，不接收或构造调用者 UID。
- `execute()` 继续在当前线程用户的 `env` 中执行，保留 ACL、record rules 和现有访问错误。
- Schema 仅来源于工具签名或显式存储的 Schema，不注入业务记录样本。
- 参数缺失或类型校验失败时，必须在任何 `search` / `search_read` 前拒绝。
- 诊断和日志须脱敏，不留存 API key、完整聊天内容、业务值或记录结果。

## 13. UI 契约

不适用。无 Owl、QWeb、视图或导航变化。错误沿用现有聊天错误展示，只显示受控文案，不显示内部 traceback。

## 14. 测试设计

### 14.1 自动化测试矩阵

| 测试 ID | 场景 | 通过标准 |
|---|---|---|
| `TEST-LLM-TOOL-001` | retriever 存储 Schema 为空时动态生成 | 精确断言根节点 `type=object`；`required=["model"]`；`properties.model.type=string`；`domain` 为数组且 `items` 保留签名对应的 union；`fields` 为字符串数组；`limit` 为整数且默认值 `100`；不导入 FastMCP |
| `TEST-LLM-TOOL-002` | 存储有效 `input_schema` | 返回已存 Schema，不被动态 Schema 覆盖 |
| `TEST-LLM-TOOL-003` | 存储 Schema 为非法 JSON 或非 object | 返回受控错误，不回退空 Schema；断言 Provider HTTP mock 调用次数为零 |
| `TEST-LLM-TOOL-004` | OpenAI formatter 转换数组和 `anyOf` | 期望 fixture 中类型、`required`、`items` / union 保持，不产生虚构类型 |
| `TEST-LLM-TOOL-005` | 让设计实际使用的签名模型生成函数抛错 | Provider HTTP mock 调用次数为零；错误不包含内部细节 |
| `TEST-LLM-TOOL-006` | `execute({})` 或缺少 `model` | Pydantic 校验失败，业务 `search` mock 调用次数为零 |
| `TEST-LLM-TOOL-007` | 合法参数及省略可选参数 | 校验成功；callable 收到的值与签名及默认值一致 |
| `TEST-LLM-TOOL-008` | 无关工具的 formatter 回归 | 预先只读快照中非目标工具 Schema 不变；既有工具仍可格式化 |
| `TEST-LLM-TOOL-009` | stub Provider 返回符合 Schema 的参数 | 参数可到达 `execute()` 并通过校验；不访问外部网络 |
| `TEST-LLM-TOOL-010` | 内置浏览器 E2E 读取少量授权记录 | 脱敏捕获到非空且符合已发送 Schema 的 Provider 工具参数（含必填 `model`）；参数到达 `execute()` 并通过校验；Odoo 返回当前用户可访问的真实数据。若 Provider 参数为空或不符合 Schema，记录为 Provider 生成问题，不得误判为 Odoo runtime 缺陷。只验证工具调用、执行和数据，不验证链接渲染 |
| `TEST-LLM-TOOL-011` | Schema 生成 / 转换失败的聊天错误路径 | Provider HTTP mock 调用次数为零；现有聊天错误路径向用户显示受控提示，不显示 traceback、路径、凭据、完整 Schema 或业务数据 |

### 14.2 诊断证据记录

当前 TV 记录了依赖版本、存储 Schema 状态、生成异常、formatter 输出差异和历史运行缺项。实施验证的 ATR 使用同一个 `ATR-RUN`，按以下顺序记录四段脱敏证据；后续步骤仅在前置步骤成功且实际发生时适用：

1. **Schema 生成**：记录 `get_input_schema()` 成功返回的结构摘要，或失败阶段 / 受控错误码。若失败，后续 Provider Schema、Provider 参数和 `execute()` 证据标记为“不适用”，不能伪造。
2. **Provider Schema 序列化**：仅在步骤 1 成功时记录实际序列化到 Provider `tools` 的 Schema 摘要，并比较其是否保留源 Schema 语义。
3. **Provider 工具参数**：仅在步骤 2 成功且 Provider 返回工具调用时记录脱敏参数形态；没有工具调用时记录实际响应状态，不得声称已验证参数。
4. **运行时执行**：仅在步骤 3 获得参数时记录 `execute()` 收到的参数结构、Schema 符合性、Pydantic 校验结果及是否触达业务搜索。

历史失败和成功运行的具体模型行、存储 Schema、Provider 外发 payload 与源码 commit 如无法追回，仍标为未知；该未知项不阻塞对当前已复现 Schema 缺陷的修复与验收，也不得用于推断历史因果。按本节采集结果写入 ATR，不能以历史未知替代当前证据。

### 14.3 环境和执行记录

实现后按冻结 CC / 实施计划指定环境运行测试，记录 Odoo、Python、PostgreSQL、依赖版本和 commit。浏览器 E2E 使用用户指定的内置浏览器及现有 `odoo18ce` 开发库，不创建隔离数据库。真实 Provider 验证仅在已授权窗口执行，证据脱敏。未执行项如实标记 `NOT RUN` / `BLOCKED`，不得标为通过。

## 15. 可观测性

日志允许记录工具技术名称、Schema 阶段、稳定错误标识及是否发起 HTTP（布尔值）。禁止记录完整 Schema、API key、完整 Prompt、业务参数值和返回记录。ATR 可保留脱敏的 Schema 结构、字段名、类型和校验结果。

## 16. 部署与运行前置

- 无数据迁移、字段升级或 manifest 依赖变更；不更新 MCP 版本。
- 使用项目 `venv`、`odoo.conf` 和现有开发数据库，按 `odo-validate-loop` 执行 Odoo 模块升级、日志和 ORM 核验。
- 升级前通过只读 ORM 快照记录 `llm.tool` 名称和 `input_schema`；升级后确认只有批准范围内的目标记录发生预期变化。本设计默认不改任何数据库记录。
- 实施记录须分别引用工作区集成基线和嵌套上游源码 commit，并记录 Provider 验证条件及内置浏览器 E2E 前置。

## 17. 技术风险与防护

| 风险 | 防护 / 停止条件 |
|---|---|
| OpenAI-compatible Provider 不接受 union Schema | 经授权的真实 Provider E2E 验证；失败则暂停并修订 TDD，不删除或弱化约束 |
| 现存其他工具依赖当前 formatter patch | 实施前快照并逐项回归；若影响超出目标工具，停止扩大范围 |
| 历史失败和成功运行未记录完整配置 | 不作因果推断；以当前复现和脱敏捕获判断 |
| Schema 错误不能经现有 UI 受控展示 | 实施前由测试核验；若需新 UI / API，暂停并重设设计 |
| 其他功能仍依赖 MCP | 不从 manifest / requirements 删除依赖，不全局降级 |

## 18. Implementation Guardrails

| 编号 | 强制约束 |
|---|---|
| `T-TOOL-SCHEMA-001` | 动态 Schema 必须由 `execute()` 共用的签名 Pydantic model 派生；不得依赖当前环境不可用的 FastMCP 1.x 导入路径 |
| `T-TOOL-SCHEMA-002` | 存储 Schema 非空时优先使用；无效存储 Schema 必须 fail-closed；在无效 JSON / 非 object 测试中断言 Provider HTTP 调用次数为零 |
| `T-TOOL-SCHEMA-003` | Provider 转换须保留类型、`required`、默认值、数组 `items` 和 union 语义；不得猜测修补或静默发送空 Schema |
| `T-TOOL-SCHEMA-004` | Schema 失败时 Provider HTTP 请求次数为零，并返回受控错误 |
| `T-TOOL-SEC-001` | 保留调用用户环境、ACL 和 record rules；不得 `sudo()` 或绕过授权 |
| `T-TOOL-SEC-002` | 参数校验必须先于任何业务记录搜索 |
| `T-TOOL-REG-001` | 为无关工具建立 formatter / 存储 Schema 回归基线 |
| `T-TOOL-LOG-001` | 日志和 ATR 不得记录凭据、Prompt、业务参数值或完整返回数据 |

本 TDD v1.0.0 Frozen 后，这些约束是实施基线。实施仍须由单独冻结的 CC 授权，并满足适用的 Implementation Plan 门禁。

## 19. 需求追溯

| CC 条款 | TDD 设计 / 验证 | TDD Guardrail 反向映射 |
|---|---|---|
| `CC-CHANGE-001a` | §6.3 根因判定；§14.2 四段诊断证据 | `T-TOOL-SCHEMA-001`–`004`；`TEST-LLM-TOOL-001`–`005` |
| `CC-CHANGE-001b` | §5–§6 修复边界；诊断不支持时停止并重新定界 | `T-TOOL-SCHEMA-001`–`004`；`TEST-LLM-TOOL-002` / `003` / `005` |
| `CC-CHANGE-002` | §5.2 一致性；`TEST-LLM-TOOL-001`–`007` | `T-TOOL-SCHEMA-001` / `003` |
| `CC-CHANGE-003` | §6、§11、§15；`TEST-LLM-TOOL-003` / `005` / `011` | `T-TOOL-SCHEMA-002` / `004`；`T-TOOL-LOG-001` |
| `CC-PRESERVE-001` | §12；`TEST-LLM-TOOL-007` / `010` | `T-TOOL-SEC-001` |
| `CC-PRESERVE-003` | §16、`TEST-LLM-TOOL-008` | `T-TOOL-REG-001` |
| `CC-PRESERVE-004` | §5.2、§12、`TEST-LLM-TOOL-006` | `T-TOOL-SEC-002` |

反向追溯按 TDD Guardrail 汇总如下，确保每项技术约束都能回到冻结 CC 的授权条款：

| TDD Guardrail | CC 授权条款 | 主要验证 |
|---|---|---|
| `T-TOOL-SCHEMA-001` | `CC-CHANGE-002` | `TEST-LLM-TOOL-001` / `005` |
| `T-TOOL-SCHEMA-002` | `CC-CHANGE-003` | `TEST-LLM-TOOL-002` / `003`（无效存储 Schema 时 Provider HTTP 为零） |
| `T-TOOL-SCHEMA-003` | `CC-CHANGE-002` | `TEST-LLM-TOOL-002` / `004` / `006` |
| `T-TOOL-SCHEMA-004` | `CC-CHANGE-003` | `TEST-LLM-TOOL-003` / `005` / `011` |
| `T-TOOL-SEC-001` | `CC-PRESERVE-001` | `TEST-LLM-TOOL-007` / `010` |
| `T-TOOL-SEC-002` | `CC-PRESERVE-004` | `TEST-LLM-TOOL-006` |
| `T-TOOL-REG-001` | `CC-PRESERVE-003` | `TEST-LLM-TOOL-008` |
| `T-TOOL-LOG-001` | `CC-CHANGE-003` | `TEST-LLM-TOOL-011` |

## 附录 A：技术决策

| 编号 | 决策 | 理由 |
|---|---|---|
| `TD-001` | 由共用签名 Pydantic model 生成 Schema，不降级 MCP | 当前 `mcp==2.3.0` 不提供代码所调用的 FastMCP 路径；其他功能仍用 MCP 类型 |
| `TD-002` | 非空存储 Schema 是显式覆盖；解析失败即停止 | 防止错误配置被空 Schema 或动态 Schema 静默掩盖 |
| `TD-003` | OpenAI formatter 无损保留受支持的 JSON Schema 语义，不能转换则 fail-closed | 当前 `anyOf` item 被补为 `type:string`，破坏 Schema 含义 |
| `TD-004` | 不改 `llm.tool` 记录和公共 API，不做数据库 Schema 回填 | 当前缺陷来自通用代码生成 / 转换路径；回填只修复单条或有限记录，会掩盖通用缺陷、无法覆盖新建或其他动态工具，也会把代码修复变成数据维护；统一修复签名生成和 formatter 才能覆盖所有符合契约的工具 |

## 附录 B：版本变更

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-10-16 | 草稿 | 根据 TV-LLM-TOOL-002-01 起草；待适用性、异常传播路径和技术方案评审 |
| v0.2 | 2026-10-16 | 草稿 | 对齐 CC 的 SRS N/A 判定；补充 FastMCP 影响范围、方法级改动、Schema 对比、结构断言、union 风险与数据回填决策 |
| v0.3 | 2026-10-16 | 草稿 | 纳入复审：明确聊天错误链路与安全断言、历史未知不阻塞、分阶段 ATR、E2E 参数证据、双向追溯和 TV 一致性门禁 |
| v1.0.0 | 2026-10-16 | Frozen | 用户批准冻结；作为 `CC-LLM-TOOL-002` 的技术实施基线 |

## 冻结前门禁

- [x] SRS N/A 适用性与 CC §2.1 对齐；不作为待确认门禁。
- [x] 已复核 TDD 修复目标与 `TV-LLM-TOOL-002-01` 当前已复现的 Schema 生成 / 转换缺陷一致；历史归因未知明确为不阻塞本次修复。
- [x] 用户已评审并批准 §5–§18 设计及方法级文件白名单。
- [x] 错误路径和安全要求已定义为 `TEST-LLM-TOOL-011` 实施验收项；测试须证明现有 `_generate_assistant_response()` / `_post_error_message()` 路径只展示受控文案，且 Schema 失败时 Provider HTTP 调用次数为零，不新增 UI / API。该测试尚未执行，不属于设计冻结前的缺失证据。
- [x] 已通过 Odoo shell 采集当前环境版本：PostgreSQL 16.14；工作区集成基线 `55a930f`，嵌套上游源码 HEAD `609ec6dd`。实施时仍需确认运行代码无额外变化。
- [x] 用户于 2026-10-16 批准冻结；TDD v1.0.0 Frozen。
