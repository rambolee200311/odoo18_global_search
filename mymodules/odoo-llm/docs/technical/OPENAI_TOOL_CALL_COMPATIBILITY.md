# `llm_openai` 工具调用参数兼容性技术方案

> 文档版本：v1.0.0 Frozen
> 范围：上游 `odoo-llm/llm_openai` addon；独立于 `wd_global_search_llm` 桥接
> 起草日期：2026-10-16
> 冻结日期：2026-10-16
> 批准记录：用户于 2026-10-16 明确批准冻结本技术方案；冻结内容以原 v0.2 评审稿为准
> 代码基线：`odoo-llm` branch `18.0`，commit `609ec6dda3645165f6a4a843d7af5d286081a29d`

## 1. 请求来源核验（方案前置）

### 1.1 错误原文

用户在 Odoo 聊天线程选择 OpenAI Provider、模型 `gpt-5.6-luna`，启用 `odoo_record_retriever` 并发送“读取gemini的3个销售订单，返回链接”。API 返回：

```text
Error code: 400 - {
  'error': {
    'message': "Function tools with reasoning_effort are not supported for gpt-5.6-luna in /v1/chat/completions. To use /v1/responses or set reasoning_effort to 'none'.",
    'type': 'invalid_request_error',
    'param': 'reasoning_effort',
    'code': None
  }
}
```

### 1.2 已核实事实

| 核验项 | 结果 | 证据 |
|---|---|---|
| Odoo Provider 请求参数 | 当前 `openai_chat` 构造 `model`、`stream`、`messages`，有工具时再加入 `tools`、`tool_choice`；没有加入 `reasoning_effort`，也没有转发 `llm.model.parameters` | `llm_openai/models/openai_provider.py:150-196` |
| 模型参数字段 | `llm.model.parameters` 定义在 `llm/models/llm_model.py`，类型为 `fields.Text()`；核心没有格式约束，当前 OpenAI chat 路径没有使用 | `llm/models/llm_model.py:27-31`；全仓源码搜索 |
| 运行时 Provider 源文件 | Odoo 错误栈路径指向本地 checkout 的 `mymodules/odoo-llm/llm_openai/models/openai_provider.py`；本地 checkout commit 为上述基线 | `debug_logs/odoo_181.log:77471-77479`；错误栈 |
| 实际请求端点 | 日志记录请求发往 `https://api.openai.com/v1/chat/completions`，随后收到 HTTP 400 | `debug_logs/odoo_181.log:77480`；相邻请求也记录在 `77466-77469` |
| 实际 HTTP 请求体 | **未捕获**。Odoo / httpx 日志只有 URL 和响应码，没有 JSON body | `debug_logs/odoo_181.log` |
| 进程 / ORM 实时核验 | 未完成：沙箱禁止进程枚举；按 `odoo-bin shell -c odoo.conf` 的只读检查在启动时被 `psutil` 进程枚举权限拒绝 | 本次核验记录 |

### 1.3 核验结论与方案影响

当前源码没有由 `llm_openai` 写入 `reasoning_effort` 的路径；日志确认调用到本地 checkout 的 Provider，并且请求发往 OpenAI 官方 API 域名，没有证据指向中间网关。**来源不能完全定案**，因为实际 HTTP body 未记录；可能是 API 按模型默认推理级别拒绝工具调用，也可能是运行时 SDK / 扩展在请求序列化阶段加入了参数。

因此，不能把“网关注入参数”写成已证实事实。来源核验结果是：**源码没有显式设置；API 对当前 Chat Completions + function tools 请求要求 `reasoning_effort=none` 或 Responses API；显式设置 `none` 是当前唯一有错误文案直接支持的最小修复候选。** 实现前仍需用脱敏请求捕获确认最终 payload，并验证显式 `none` 在同一模型上可用。

核验记录格式为本节表格：记录源码基线、加载路径、请求 endpoint、payload 中该字段是否存在、结论和证据位置。实施时将脱敏 payload 断言与真实 Provider 结果分别记入该 CC 的 IHR / ATR；禁止记录 API key 或业务消息内容。

### 1.4 相邻但独立的日志问题

同一日志在 `77470-77479` 还记录 `llm_tool` 的 `get_input_schema()` 与已安装 `mcp` 2.x API 不兼容，工具 Schema 生成失败并进入 OpenAI Provider 的 fallback schema。它是工具执行链上的独立依赖兼容问题，不是本次 400 中 `reasoning_effort` 参数的来源，也不纳入本方案修复范围。后续真实工具 E2E 必须确认此问题已独立处置，或将 E2E 结果明确标为受阻。

## 2. 问题目标与边界

- 保留现有 Chat Completions 路径和 OpenAI function tool 格式。
- 允许对单个 OpenAI 模型显式设置 `reasoning_effort: none`。
- 不按模型名称硬编码，不改变未设置此参数的既有请求。
- OpenAI 专属配置与其他 Provider 参数隔离；其他 Provider 忽略 OpenAI 命名空间。
- 不无校验透传参数，不修改 `llm.model` 核心字段定义或已有模型数据。
- 不修改 `llm` / `llm_assistant` 核心，不修改桥接 addon。

## 3. 方案比较

| 方案 | 处理方式 | 影响与判断 |
|---|---|---|
| A. 在 `llm.model.parameters` 使用 Provider 命名空间 | JSON 形如 `{"openai":{"reasoning_effort":"none"}}`；仅 `llm_openai` 读取和应用 OpenAI 命名空间 | **推荐。** 不新增核心字段；可与其他 addon 的顶层命名空间共存；未配置时维持原请求。`parameters` 是自由文本，需在 OpenAI addon 增加保存时和请求时校验。 |
| B. 增加独立 `llm_openai` 模型字段 | 为 `llm.model` 增加 OpenAI 专属字段和视图 | 隔离性更强，但要增加数据库字段、视图、升级迁移和新配置 UI；对本次单参数修复偏重。只有现有 `parameters` 数据审计发现无法安全复用时再考虑。 |
| C. 所有带工具的请求固定为 `reasoning_effort=none` | 不读取模型配置，Provider 全局覆盖 | 不采用。会改变所有 OpenAI / OpenAI-compatible 模型的推理设置，也无法表达不同模型能力。 |
| D. 迁移 Responses API | 新增 endpoint 及消息、工具、流式事件和工具结果转换 | 暂不采用。API 错误直接提供 Chat Completions 下设为 `none` 的选项；Responses API 涉及更广的调用和流式处理改造。 |

## 4. 推荐设计

### 4.1 参数契约与 Provider 隔离

复用 `llm.model.parameters` 的 Text 字段，但为 OpenAI 配置定义专属命名空间：

```json
{
  "openai": {
    "reasoning_effort": "none"
  }
}
```

该命名空间只由 `llm_openai` 读取。其他 Provider 忽略 `openai` 命名空间；`llm_openai` 也忽略其他顶层命名空间。模型记录仍由 `provider_id` 绑定一个 Provider，命名空间用于保持参数来源清晰并兼容其他 addon 对同一 Text 字段的扩展。

行为约定：

| `parameters` 值 | 行为 |
|---|---|
| 字段值为 `False` / `None` / `""` | 不读取参数，保留现有请求 |
| JSON 字符串 `"{}"` | 合法空对象，不增加请求参数 |
| JSON 字符串 `"null"` | 非法；顶层必须为 JSON object |
| 非空非法 JSON | OpenAI 模型保存时拒绝；请求时再次校验并拒绝发起 API 请求 |
| `openai` 值不是 object | 配置错误 |
| `openai` 下未知键 | 忽略且不透传，保持对未来/其他 addon 键的兼容 |
| `openai.reasoning_effort` 缺失 | 不增加该请求参数 |
| `openai.reasoning_effort` 为字符串 `"none"` | 允许并显式写入 Chat Completions payload |
| `reasoning_effort` 为其他值、空字符串或非字符串 | 当前修复版本拒绝保存；如需其他值，先核实目标 Provider 支持并扩展契约 |
| 其他 Provider 的模型记录包含 `openai` 命名空间 | 该 Provider 忽略，不验证也不透传 |

白名单在 `llm_openai` 代码中固定为 `reasoning_effort`，首期仅放行值 `none`。未知键不报错、不透传，防止破坏由其他 addon 写入的同字段配置；`reasoning_effort` 类型或值错误则作为本 Provider 配置错误处理。

### 4.2 校验位置与用户反馈

- `llm.model.parameters` 的字段定义仍在核心 `llm/models/llm_model.py`，本方案不修改其字段定义或现存记录。
- `llm_openai` 继承 `llm.model`，在 `parameters` 或 `provider_id` 写入时，仅对 OpenAI Provider 的模型检查 JSON object 和本 addon 命名空间；错误通过 Odoo 配置表单的 `ValidationError` 显示。
- OpenAI 请求构造前重复校验，防止导入、直接 SQL 或其他绕过 ORM constraint 的错误配置触发外部请求。运行时错误以明确的 `UserError` 返回；现有聊天错误处理会将异常文本显示在对话中（当前标题为通用 `LLM API Error`）。本方案不修改 `llm_thread` 的错误标题逻辑。
- 未知 namespace / OpenAI 未知键均忽略；不把整个 `parameters` JSON 传给 SDK。

### 4.3 请求构造

在 `llm_openai.models.openai_provider.LLMProvider.openai_chat` 已有 `params` 构造之后、SDK 调用之前，读取经过校验的当前模型参数，仅当 `openai.reasoning_effort == "none"` 时执行：

```python
params["reasoning_effort"] = "none"
```

其余字段继续由 Provider 控制；模型参数不能覆盖 `model`、`messages`、`stream`、`tools` 或 `tool_choice`。同一设置对带工具 / 不带工具、流式 / 非流式请求一致生效。若 §1 的脱敏 payload 核验发现值并非来自 API 默认，而由其他 Odoo 扩展注入，则先修复真实来源，再评估是否仍需此显式配置。

## 5. 影响范围

预期文件边界：

- `llm_openai/models/openai_provider.py`：Provider 命名空间解析、校验、请求参数合并。
- `llm_openai/models/llm_model.py`（新增）及 `models/__init__.py`：通过 `_inherit = "llm.model"` 为 OpenAI 参数保存增加约束并注册扩展；不改核心 `llm.model` 定义。
- `llm_openai/views/llm_model_views.xml`：在模型设置表单说明 `parameters` 的 JSON 格式和 `openai.reasoning_effort` 用法（仅在适当上下文展示或添加帮助文案）。
- `llm_openai/tests/`：配置校验、请求 payload 和回归测试。
- `llm_openai/README.md`：补充模型配置示例及当前支持范围。

不新增数据库字段，不改变已有模型记录；新增约束可能影响已有 OpenAI 模型上非 JSON 的 `parameters` 文本。实施前需只读盘点该字段现值；若存在非空非 JSON 数据，应先确定兼容处置，不得静默覆盖或清除。

## 6. 验收设计

### 6.1 自动化请求与配置测试

1. `False` / `None` / `""` 和 `"{}"` 不增加 `reasoning_effort`；普通请求参数保持不变。
2. `{"openai":{"reasoning_effort":"none"}}` 在 SDK 请求 payload 中带 `reasoning_effort: none`，且 `model`、`messages`、`stream`、`tools`、`tool_choice` 不被覆盖。
3. 有工具 / 无工具、流式 / 非流式路径均按当前模型配置执行。
4. `"null"`、数组、非法 JSON、`openai` namespace 类型错误、空值或非 `none` effort 在 OpenAI 模型保存时失败；运行时再次校验失败时不发起 HTTP 请求，并将清晰错误显示给聊天用户。
5. 非 OpenAI Provider 忽略 `openai` 命名空间；未知顶层 namespace 和 `openai` 未知键不报错、不透传。

### 6.2 Provider 集成回归

1. 对目标 OpenAI 配置 `gpt-5.6-luna` 重发原始提示，确认 400 消失并收到有效的 function tool call 响应。
2. 使用一个支持工具调用且不设置该参数的 OpenAI 模型（首选 `gpt-4o`，以实际账户可用模型为准），确认原始请求行为保持不变。
3. 使用一个 OpenAI-compatible endpoint 上的工具调用模型（如 LiteLLM proxy；若当前环境未配置，记录 `NOT RUN`，不得声称通过），确认其他 endpoint 未配置 OpenAI 专属参数时行为不变。
4. 单独确认 `mcp` 依赖兼容问题已处置，或将真实 `odoo_record_retriever` 的端到端工具执行明确标为受阻；不得把“API 返回 tool call”误报为“工具已在 Odoo 执行成功”。

自动化层用 SDK 请求捕获 / mock 验证 payload；真实 Provider 场景必须通过当前 Odoo 实例发送请求。API key 和销售订单内容不得写入 ATR / 日志附件。

## 7. 风险与后续迁移条件

| 风险 / 未决项 | 应对 |
|---|---|
| 实际 payload 未捕获，API 对 `reasoning_effort` 的判定来源仍有不确定性 | 实施前捕获脱敏 HTTP body；若发现其他 Odoo 扩展注入该键，先修正真实来源。 |
| 现存 OpenAI 模型 `parameters` 可能有非 JSON 内容 | 实施前只读盘点；配置约束启用前先处理兼容性，不自动重写数据库数据。 |
| `odoo-llm` 上游升级可能覆盖或重复实现此修复 | 记录修复提交与依据；升级前检查上游等价能力。上游若已提供支持，迁移并删除本地重复补丁。 |
| `mcp` 2.x 与 `llm_tool` 当前 Schema 生成代码不兼容 | 作为独立依赖问题跟踪；它可能阻塞工具完整 E2E，但不是 `reasoning_effort` 修复的一部分。 |
| 后续模型或 endpoint 仍不能在 Chat Completions 下通过显式 `none` 使用工具 | 触发 Responses API 迁移评估；评估消息转换、流式事件解析、工具调用/结果循环和错误处理。由 `odoo-llm` 技术负责人决定是否立项。 |

## 8. 与桥接项目的关系及后续门禁

本方案只定义 `llm_openai` 自身兼容行为。桥接项目的 SRS / TDD 不作为其上游基线，也不在本方案中修改。若桥接之后仍选用受影响的 OpenAI 模型，在 Provider 修复及真实工具调用验证完成后，将验证状态同步到桥接 Implementation Plan §3 `Real provider readiness`；这只是相关依赖状态更新，不改变桥接需求或技术设计。

本文已冻结为技术基线。实施前仍须完成脱敏 payload 来源核验和 OpenAI `parameters` 现值盘点；CC §12 将这两项列为实施前门禁。冻结本方案不代表这些核验已完成，也不等于实现、模块升级或真实 API 验证已获执行结果。

## 9. 版本历史

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-16 | 初稿：提出模型级 `reasoning_effort` 参数及 Chat Completions 最小修复 | Draft |
| v0.2 | 2026-10-16 | 按评审重排来源核验；补足完整错误、实际日志证据、多 Provider 命名空间、未知参数兼容、校验反馈、回归范围、Responses 触发条件、升级风险及桥接 readiness 同步 | Draft |
| v1.0.0 | 2026-10-16 | 用户批准冻结 v0.2 技术方案；技术内容保持不变，登记来源核验和模型参数盘点为实施前门禁 | Frozen |
