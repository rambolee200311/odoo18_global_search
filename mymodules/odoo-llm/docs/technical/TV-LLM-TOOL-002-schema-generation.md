# TV-LLM-TOOL-002：记录读取工具 Schema 生成技术核查

> 版本：v0.2 草稿
> 状态：已核实当前运行时缺陷；历史运行归因及真实 Provider 接受情况尚未核实
> 日期：2026-10-16
> 范围：`llm_tool` Schema 生成和 OpenAI 工具 Schema 转换
> 工作区集成基线：根仓库 `55a930fbb234f9b82c4a9a3f6292b8f081ac956a`；嵌套上游 checkout HEAD `609ec6dda3645165f6a4a843d7af5d286081a29d`

## TV-LLM-TOOL-002-01：已安装 MCP SDK 与 Schema 生成的兼容性

### 核查问题

当前 `llm.tool.get_input_schema()` 调用的 Schema 生成 API 是否存在于已安装的 MCP SDK？如果不存在，能否用运行时校验已有的 Pydantic 签名模型生成 retriever Schema，并由本地 OpenAI formatter 保留必填 `model`？

### 方法

- 检查 `llm.tool.get_input_schema()`、`get_pydantic_model_from_signature()`、`execute()` 和 `llm.provider._create_openai_tool_from_schema()`。
- 使用仓库 `venv` 和 `odoo.conf`，通过 `odoo-bin shell -c odoo.conf` 及 Odoo ORM 核查；不使用独立数据库客户端，不写记录，不调用外部 Provider。
- 只读依赖版本和工具 Schema 元数据；不读取或输出 API key、Prompt 或业务记录内容。
- 在内存中用现有签名 Pydantic 模型生成 Schema，并传入本地 OpenAI Schema formatter。

### 结果

| 核查项 | 结果 |
|---|---|
| 已安装依赖 | `mcp==2.3.0`、`pydantic==2.13.4`、`openai==2.54.0` |
| Retriever 数据库记录 | 有一条活动的 `odoo_record_retriever`；存储的 `input_schema` 为空 |
| 当前 `get_input_schema()` 导入 | `ModuleNotFoundError`：当前 MCP 2.x 环境没有 `mcp.server.fastmcp`；异常说明 FastMCP API 已改名 / 变化 |
| 当前 OpenAI formatter 行为 | `_openai_format_tool()` 捕获 Schema 生成异常，返回 `properties` 和 `required` 均为空的 fallback |
| 从签名生成的 Pydantic Schema | 生成成功；`model` 为必填；可选 `domain`、`fields`、`limit` 有对应类型及默认值 |
| 将签名 Schema 传入本地 formatter | 保留了必填 `model`，但当前递归 patch 给一个含 `anyOf` 的节点添加了 `type: string`，改变 `domain` 元素 Schema 含义 |
| 实际工具记录经 OpenAI formatter 的结果 | 输出 `type=function`，函数名为 `odoo_record_retriever`，但 `parameters` 的 `properties` 和 `required` 为空；原因是 `get_input_schema()` 抛错后 formatter 使用了空 Schema fallback |
| 相同显示名模型记录 | 数据库有两条活动 `gpt-5.6-luna` 模型记录，`model_use`、Provider 记录和 `reasoning_effort` 配置不同；历史对话未记 `llm.model` 行 ID，无法精确对照 |

### 只读运行时采集记录（2026-10-16）

命令使用 `./venv/bin/python odoo-bin shell -c odoo.conf`，通过 Odoo ORM 访问现有数据库 `odoo18ce`。首次在沙箱内启动时被 macOS 进程枚举权限拦截；获准执行同一只读 shell 命令后完成核查。未写入记录，也未发起 Provider HTTP 请求。

| 采集项 | 观测结果 |
|---|---|
| 环境 | `env.uid=1`；数据库 `odoo18ce`；PostgreSQL 16.14；`mcp==2.3.0`、`pydantic==2.13.4`、`openai==2.54.0` |
| 工具行 | `llm.tool` ID `1`，活动，未设置存储 Schema |
| 当前 `tool.get_input_schema()` | 在 `mcp.server.fastmcp.utilities.func_metadata` 导入处抛 `ModuleNotFoundError` |
| 签名派生 Schema | 根节点为 object；`required=["model"]`；`model` 为 string；`fields` 为 string array，默认 `[]`；`limit` 为 integer，默认 `100`；`domain` 为 array，元素为 array，内部 `anyOf` 包含 string / integer / boolean / number / null |
| 实际 `_openai_format_tool(tool)` | 返回 OpenAI function 定义，但 `parameters={"type":"object","properties":{},"required":[]}` |

### 结论

- **已核实：** 当前配置的运行时中，存储 Schema 为空时，`get_input_schema()` 导入 MCP 1.x 路径失败；OpenAI formatter 随后输出空 fallback Schema。这会使模型看不到必填参数，是当前可独立复现的缺陷。
- **已核实：** 现有签名派生 Pydantic 校验模型可以在不使用 FastMCP 导入的情况下生成必填 `model`。
- **已核实：** 当前本地 OpenAI formatter 会改变嵌套 `domain` union Schema 的意义：它在 `anyOf` 节点额外添加父级 `type: string`。该行为须由 TDD 和回归测试处置。
- **历史运行归因尚未确定：** 当前运行时缺陷与早先 `{}` 参数失败一致，但没有记录早先运行使用的模型行、存储 Schema 和代码基线。之后成功的对话不能证明当时 Schema 已被修复。
- **未核实：** 未向真实 Provider 发送请求，未验证 Provider 是否接受转换后的 `domain` union。

### 三段诊断证据状态

| 链路 | 当前证据 | 状态 |
|---|---|---|
| 源码生成 Schema 和本地 Provider 工具 Schema | 当前 ORM shell 采集：签名 Schema 有必填 `model`，实际 formatter 输出空字段 | **当前缺陷已核实** |
| Provider 返回的工具调用参数 | 早先失败记录包含 `{}`；后续截图显示工具调用成功，但未显示参数内容 | 历史证据不完整；未采集当前 Provider 返回 |
| Odoo `execute()` 收到的参数及校验 | 失败记录显示缺少必填 `model`；早先与后续 UI 证据分别呈现失败和成功 | 与 Pydantic 必填参数校验一致；成功调用的确切参数对象未采集 |

早先失败与成功两次运行的根因仍**不能确认**，因为失败运行的模型行、Schema 状态和代码基线没有记录。当前运行时的 Schema 生成 / formatter 缺陷则已独立核实，可作为修复依据；这两类结论不可混为一谈。

### 证据来源

- 源码：`llm_tool/models/llm_tool.py` 的 `get_input_schema()`、`get_pydantic_model_from_signature()`、`execute()`。
- 源码：`llm_openai/models/openai_provider.py` 的 `_openai_format_tool()`、`_recursively_patch_schema_items()`、`_create_openai_tool_from_schema()`。
- 只读 Odoo shell 观察结果如上；没有保存密钥、Prompt、完整 Provider payload 或业务结果。
- 历史观察：`IHR-CC-OPENAI-001.md` IHR-004 / IHR-005 和 `HVR-CC-OPENAI-001.md` HVR-RUN-001。

### 对 TDD 的影响

- 优先使用 `execute()` 同一签名派生 Pydantic model 生成 Schema；不要全局 pin / downgrade MCP 包，因为其他协议代码仍使用它。
- 移除静默空 Schema fallback。Schema 生成或转换失败时，必须在外部 HTTP 请求前终止，并返回受控错误。
- OpenAI formatter 必须保留 JSON Schema union 语义；不得向 `anyOf` 节点添加虚构父级类型。若指定 Provider 不接受该 Schema 子集，应停止并重新评估，而不是发送空 Schema。
- 保留存储 Schema 优先级和当前用户访问行为；本次核查不回填或修改数据库记录。
- 后续运行对照须捕获确切 `llm.model` 行和存储 Schema 状态，并遮蔽凭据及业务值。

## 版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-16 | 初始依赖、源码及内存 Schema 核查 | 草稿 |
| v0.2 | 2026-10-16 | 增加只读 ORM shell 采集、当前工具行、具体异常、签名 Schema、实际 formatter 输出及三段诊断证据状态 | 草稿 |
