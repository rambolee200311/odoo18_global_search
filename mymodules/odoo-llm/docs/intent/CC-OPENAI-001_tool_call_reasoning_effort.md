# CC-OPENAI-001：OpenAI 工具调用 `reasoning_effort` 兼容修复

> 文档版本：v0.1 Draft  
> 状态：Draft（待评审；不构成实现授权）  
> 起草日期：2026-10-16  
> 模块：`llm_openai`  
> 上游技术基线：`docs/technical/OPENAI_TOOL_CALL_COMPATIBILITY.md` v1.0.0 Frozen  
> 代码基线：`odoo-llm` 18.0，commit `609ec6dda3645165f6a4a843d7af5d286081a29d`

---

## 0. 文档治理

### 0.1 目的

限定 `llm_openai` 中 OpenAI Chat Completions 工具调用兼容性修复的实现范围、文件边界、必需行为、回归要求和停止条件。

### 0.2 状态与冻结规则

本文是 CC 草案。只有经评审并明确批准冻结后，才成为本次实现契约。技术方案已冻结，但这不代表本 CC 已冻结，也不授权修改代码、升级模块或调用真实 Provider。

### 0.3 上游基线

- 本 CC 仅适用于技术方案列出的 `odoo-llm` 18.0 commit。
- 技术方案 v1.0.0 Frozen 是本次实现的唯一技术设计基线。
- 不存在适用于此独立 Provider bug fix 的桥接项目 SRS、DDD 或 Implementation Plan；不得把桥接文档当作本 CC 的需求来源。

### 0.4 编号

本 CC 使用 `CC-CHANGE`、`CC-PRESERVE`、`CC-TEST` 和 `CC-DEC` 编号。本文不另造 SRS、DDD 或 TDD 编号。

---

## 1. 变更概述

| 字段 | 值 |
|---|---|
| Intent ID | `CC-OPENAI-001` |
| 模块 | `llm_openai`（`odoo-llm` addon） |
| 工作类型 | Bug 修复 / Provider 兼容性 |
| 变更类型 | 行为修正；模型配置校验 |
| 目标 | 允许 OpenAI 模型通过 `llm.model.parameters` 明确配置 `openai.reasoning_effort = "none"`，并将其安全地加入 Chat Completions 请求，使受影响模型可以发起 function tool 请求；无此配置时维持原请求行为。 |
| 背景 | 对话请求使用 OpenAI Chat Completions 和工具时收到 HTTP 400：`Function tools with reasoning_effort are not supported for gpt-5.6-luna in /v1/chat/completions. To use /v1/responses or set reasoning_effort to 'none'.` 冻结方案记录了当前源码、端点和日志证据，同时注明最终 HTTP body 尚未捕获。 |

---

## 2. 上游基线与追溯

### 2.1 SRS 引用

**N/A。** 这是对既有 Provider function calling 能力的兼容性 bug 修复，不新增业务流程或业务语义。现有产品能力依据为 [llm_openai README 的 Function calling capabilities 与 OpenAI-compatible endpoints 说明](../../llm_openai/README.md)。缺少独立 SRS 不构成发明新行为的许可；实现行为必须受 §2.3 冻结技术方案约束。

### 2.2 DDD 引用

**N/A。** 此 Provider 局部修复不需要 DDD，也不创建领域模型。

### 2.3 TDD / 技术方案引用

| 基线 | 标题 | 本次相关性 |
|---|---|---|
| `OPENAI_TOOL_CALL_COMPATIBILITY.md` v1.0.0 Frozen §1 | 请求来源核验 | 必须先满足脱敏 payload 核验门禁；当前来源尚未完全定案。 |
| 同上 §2–§3 | 目标、边界与方案比较 | 采用 Provider 专属 JSON 命名空间；不迁移 Responses API。 |
| 同上 §4.1–§4.3 | 参数契约、校验和请求构造 | 规范保存时 / 请求时校验、命名空间隔离及 payload 合并行为。 |
| 同上 §5 | 影响范围 | 限定本 CC 的文件白名单。 |
| 同上 §6 | 验收设计 | 本 CC §11 将其拆成可验证测试契约。 |
| 同上 §7–§8 | 风险及后续门禁 | 约束 `mcp` 独立问题、升级风险及实施前门禁。 |

技术方案没有独立 `T-xxx` 编号。本 CC 只引用其章节，不伪造编号或重新定义技术设计。

### 2.4 Bug 证据

用户在 OpenAI Provider 下使用 `gpt-5.6-luna` 并启用 `odoo_record_retriever` 时，API 返回 §1 所列 HTTP 400。冻结技术方案 §1 记录了错误原文、当前源码构造的请求参数、命中端点和未捕获请求体的事实。该证据证明问题存在，不单独授权新增业务行为或更换 API 架构。

### 2.5 追溯规则

本 CC 的实现只能落实冻结技术方案 §2–§8。若最终 payload 核验表明 `reasoning_effort` 由其他 Odoo 层注入，必须先修正真实来源并重新评估 CC；不得继续按当前假设实现。若现有字段数据或实际 Provider 行为与方案冲突，按 §12 停止并升级。

---

## 3. 范围冻结

### 3.1 在范围内

- 在 `llm_openai` 读取并校验 `llm.model.parameters` 中的 `openai` 命名空间。
- 对 OpenAI 模型记录执行保存时约束；在每次 OpenAI chat 请求构造时重复校验。
- 仅当 `openai.reasoning_effort` 为字符串 `"none"` 时，将 `reasoning_effort="none"` 加入 Chat Completions payload。
- 覆盖带 / 不带工具、流式 / 非流式请求的参数合并行为。
- 为模型配置提供可理解的参数格式说明；更新 `llm_openai` README。
- 添加自动化校验、payload 构造和回归测试，并记录真实 Provider 验证结果或 `NOT RUN`。

本次纳入的技术方案章节：§4.1–§4.3、§5、§6。每项均在 §14.1 映射到 CC-CHANGE。

### 3.2 超出范围

- 修改 `llm` 核心模型、核心字段定义、`llm_thread`、`llm_assistant` 或 `llm_tool`。
- 修改 `wd_global_search`、`wd_global_search_llm` 或桥接项目文档。
- 迁移到 OpenAI Responses API，重写消息 / 流式事件 / 工具循环。
- 修复 `mcp` 2.x 与 `llm_tool` Schema 生成之间的兼容问题。
- 修改 API key、Provider base URL、数据库中的 Provider 记录或模型记录值；不得替用户更改运行环境配置。
- 以模型名称硬编码 `reasoning_effort`，或对所有 OpenAI 请求无条件写入 `none`。
- 将未知参数透传给 SDK；新增其他 reasoning effort 值或 OpenAI 参数。
- 更改权限、销售订单读取行为或聊天错误标题 / 展示流程。

### 3.3 非目标

- 证明所有 OpenAI-compatible 服务都支持 `reasoning_effort`。
- 将“API 返回 function tool call”声明为“Odoo 工具执行成功”。两者是不同验证结果。
- 将本 CC 当作真实 Provider 请求、数据库操作、模块升级或发布授权。

### 3.4 仅限范围的追溯

只有 §3.1 明确纳入的技术方案章节获得本次实施授权。其他章节或未来能力不因本 CC 而自动纳入。

---

## 4. 变更边界

### 4.1 允许修改的文件

| 类型 | 路径 | 限定用途 |
|---|---|---|
| 修改 | `llm_openai/models/openai_provider.py` | 校验 / 解析模型参数，并合并 `reasoning_effort` 到现有 Chat Completions 参数。不得改其他 Provider 操作或 API 端点。 |
| 新增 | `llm_openai/models/llm_model.py` | 通过 `_inherit = "llm.model"` 增加 OpenAI 模型参数约束；不得扩展核心字段定义。 |
| 修改 | `llm_openai/models/__init__.py` | 注册新增的模型扩展。 |
| 新增 | `llm_openai/views/llm_model_views.xml` | 继承现有模型表单，提供参数 JSON 用法说明；不得修改核心 `llm` view。 |
| 修改 | `llm_openai/__manifest__.py` | 注册新增的 OpenAI view 数据文件，不改依赖或模块版本，除非依赖条件触发 §12。 |
| 修改 | `llm_openai/README.md` | 记录命名空间示例、支持值及“不透传未知参数”的配置行为。 |
| 新增 / 修改 | `llm_openai/tests/__init__.py`、`llm_openai/tests/test_*.py` | 添加本 CC §11 所列自动化测试。 |

测试实现如确需增加同目录测试辅助文件，须仅服务于本 CC 的测试契约，不扩展生产代码边界。

### 4.2 禁止修改

| 类型 | 禁止范围 |
|---|---|
| 其他 addons | `llm/`、`llm_assistant/`、`llm_thread/`、`llm_tool/`、`wd_global_search/`、`wd_global_search_llm/` 及其他 Provider addon。 |
| 其他文件 | `odoo.conf`、依赖锁文件、数据库 / 生产配置、Provider 凭据及模型数据。 |
| API 行为 | Responses API、endpoint、消息结构、tool schema、`tool_choice`、stream 协议及错误 UI。 |
| 数据模型 | 新建数据库字段、迁移现有记录、自动改写或清空 `parameters`。 |

---

## 5. 必需的行为变更

| 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|
| Chat Completions 参数由 Provider 构造，未从模型 `parameters` 应用 OpenAI `reasoning_effort`。 | 若当前 OpenAI 模型 `parameters` 含有效 `openai.reasoning_effort: "none"`，同一请求中显式发送 `reasoning_effort: "none"`。 | CC-CHANGE-001 |
| `llm.model.parameters` 是自由文本；OpenAI 配置当前没有本 addon 的保存 / 请求校验。 | OpenAI 模型保存时校验非空 JSON、顶层对象、`openai` 对象类型及受支持的 effort 值；请求构造前重复校验。配置错误不得发出外部请求。 | CC-CHANGE-002 |
| 参数字段没有 OpenAI 专属配置用法说明。 | 模型表单和 README 给出 `{"openai":{"reasoning_effort":"none"}}` 示例，说明只有该配置键和值受支持。 | CC-CHANGE-003 |
| 本场景尚无针对参数合并、配置错误及回归边界的自动化契约。 | 增加 §11 列出的自动化测试，并将真实 Provider 的实际结果按 IHR / ATR 记录。 | CC-CHANGE-004 |

配置行为必须严格符合冻结技术方案 §4.1：`False` / `None` / `""` 表示未配置；`"{}"` 合法且不变更请求；`"null"`、非法 JSON 或非对象顶层对 OpenAI 模型无效；非 OpenAI provider 不解释、不应用 OpenAI 命名空间；未知顶层命名空间和 `openai` 未知键忽略、不透传；`reasoning_effort` 只接受字符串 `"none"`。

---

## 6. 既有行为保留（回归边界）

| 行为 / 契约 | 为什么不得改变 | ID |
|---|---|---|
| 未配置 `reasoning_effort` 时，请求不新增该参数。 | 保持现有模型和 Provider 行为。 | CC-PRESERVE-001 |
| Provider 自行控制的 `model`、`messages`、`stream`、`tools`、`tool_choice` 值不被模型 JSON 覆盖。 | 它们属于现有 Chat Completions 请求契约。 | CC-PRESERVE-002 |
| 非 OpenAI Provider 对 `openai` 命名空间不做校验或应用；其他 namespace 不影响 OpenAI 请求。 | 同一 Text 字段可由其他 addon / provider namespace 使用。 | CC-PRESERVE-003 |
| 未知配置键忽略且不发送到 OpenAI SDK。 | 避免无校验透传，并保留参数字段扩展兼容。 | CC-PRESERVE-004 |
| 继续使用当前 Chat Completions endpoint、消息格式及工具调用流程。 | Responses API 迁移不在本次修复范围。 | CC-PRESERVE-005 |
| API key、模型提示 / 业务内容及请求鉴权信息不得写入测试报告或日志附件。 | 凭据及业务数据保密。 | CC-PRESERVE-006 |

---

## 7. 适用的技术防护栏

冻结技术方案未定义编号化 `T-xxx` 防护栏。本次不创建虚构编号；以下边界直接受其章节约束：

| 技术方案引用 | 本次落实位置 | 验证方式 |
|---|---|---|
| §4.1 参数命名空间、兼容规则 | CC-CHANGE-002；CC-PRESERVE-003、004 | CC-TEST-001 至 CC-TEST-004 |
| §4.2 保存时及请求时校验 | CC-CHANGE-002 | CC-TEST-005、006 |
| §4.3 不覆盖 Provider 参数、仅有配置时加入 effort | CC-CHANGE-001；CC-PRESERVE-001、002 | CC-TEST-007 至 CC-TEST-010 |
| §6.2 真实 Provider 和 `mcp` 问题区分 | CC-CHANGE-004；§12 | 人工验证及独立 E2E 状态记录 |

---

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要数据库迁移 | 否；不新增字段、不迁移模型记录。 |
| 迁移脚本 | N/A |
| 配置读取 | 读取现有 `llm.model.parameters`；实现前只读盘点 OpenAI 模型的现存值。 |
| 数据修改 | 本 CC 不允许自动重写、清空或规范化已有记录。 |
| 回滚策略 | 若模块升级后需要撤销代码，移除 addon 扩展并恢复原代码；本方案不要求数据恢复，因为不写入模型参数。已有用户配置由用户明确管理，不由回滚逻辑删除。 |
| 验证 | 升级后确认无 schema 迁移；通过自动化测试及只读检查确认模型记录未被改写。 |

---

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的外部 API | 无 endpoint 变更；仅在符合配置时向既有 `/v1/chat/completions` 请求增加标准参数 `reasoning_effort="none"`。 |
| 向后兼容 | 是；未配置时参数与原请求一致。 |
| Adapter 变更 | 仅 `llm_openai` Provider 内部请求构造；不改公共 Adapter 接口。 |
| OpenAI-compatible endpoint | 配置只针对 OpenAI namespace 的模型；对其他 endpoint 不自动注入。只有经过用户显式配置且服务端接受时才发送。 |
| 外部验证限制 | 真实 Provider 请求必须由后续实现 / 验证流程执行，并遵守 CC 的凭据保护约束；起草本文时未调用外部 API。 |

---

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 / ACL | 无。 |
| 敏感数据 | API key、认证头、请求正文中的用户消息不得写入文档、测试断言输出或 ATR。 |
| 参数透传 | 只允许由 addon 解析并验证 `openai.reasoning_effort="none"`；不得把任意 JSON 展开给 SDK。 |
| 配置错误反馈 | 使用 Odoo 配置校验错误和请求前的受控运行时错误；不得包含 key、完整请求体、堆栈或本地路径。 |
| 日志 | 若为脱敏 payload 核验临时启用请求日志，须遮蔽鉴权信息和业务消息，核验后按项目规则处置临时日志。 |

---

## 11. 测试契约

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | 空值处理 | 技术方案 §4.1；CC-PRESERVE-001 | 单元 | `False`、`None`、`""` 不设置 `reasoning_effort`。 | 否 | 保留原请求行为。 |
| CC-TEST-002 | 空对象处理 | 技术方案 §4.1；CC-PRESERVE-001 | 单元 | `"{}"` 作为合法配置，不设置 effort。 | 否 | 明确空 JSON 行为。 |
| CC-TEST-003 | 命名空间隔离 | 技术方案 §4.1；CC-PRESERVE-003 | 单元 | 未知顶层 namespace 不报错、不应用；其他 Provider 不解释 OpenAI namespace。 | 否 | 验证多 Provider 共存边界。 |
| CC-TEST-004 | 未知键过滤 | 技术方案 §4.1；CC-PRESERVE-004 | 单元 | `openai` 下未知键忽略、不报错、不出现在 SDK 参数中。 | 否 | 防止无校验透传。 |
| CC-TEST-005 | JSON / 顶层类型错误 | 技术方案 §4.1–§4.2；CC-CHANGE-002 | ORM 单元 | 对 OpenAI 模型，非空非法 JSON、`null`、数组及非对象顶层在保存时给出配置错误。 | 否 | 保证配置可诊断。 |
| CC-TEST-006 | OpenAI namespace / effort 非法 | 技术方案 §4.1–§4.2；CC-CHANGE-002 | ORM 单元 | `openai` 非对象、effort 非字符串、空值或非 `none` 值保存失败；运行时遇到绕过约束的同类数据时拒绝请求。 | 否 | 保存和请求边界双重校验。 |
| CC-TEST-007 | effort 生效 | 技术方案 §4.3；CC-CHANGE-001 | 请求构造单元 | `{"openai":{"reasoning_effort":"none"}}` 使 SDK 请求恰好带有 `reasoning_effort="none"`。 | 否 | 核心修复断言。 |
| CC-TEST-008 | Provider 字段不被覆盖 | 技术方案 §4.3；CC-PRESERVE-002 | 请求构造单元 | 设置 effort 时，model、messages、stream、tools、tool_choice 均保持由 Provider 构造的原值。 | 否 | 防止参数注入覆盖请求核心字段。 |
| CC-TEST-009 | 请求形态矩阵 | 技术方案 §6.1；CC-PRESERVE-005 | 请求构造单元 | 带 / 不带工具与流式 / 非流式组合中，effort 只按当前模型配置生效，其他请求结构不变。 | 否 | 覆盖统一请求路径及分支。 |
| CC-TEST-010 | 配置错误不出网 | 技术方案 §4.2；CC-CHANGE-002 | 请求构造单元 | 无效配置在 SDK / HTTP 调用前失败；断言外部调用 mock 未被调用。 | 否 | 验证运行时二次校验。 |
| CC-TEST-011 | 目标模型真实 Provider 验证 | 技术方案 §6.2；CC-CHANGE-004 | 人工集成 | `gpt-5.6-luna` 在安全配置下不再收到该 400，并返回有效 function tool call；API key 与业务消息不进入报告。 | 是 | 真实 API 行为需实测，自动 mock 不足以证明。 |
| CC-TEST-012 | 其他模型 / endpoint 回归 | 技术方案 §6.2；CC-PRESERVE-001、005 | 人工集成 | 有可用账户时验证一个未配置 effort 的 OpenAI 工具调用模型及一个 OpenAI-compatible endpoint；不可用的场景记为 `NOT RUN`。 | 是 | 验证兼容性范围，避免无证据声称通过。 |
| CC-TEST-013 | Odoo 工具执行结果区分 | 技术方案 §1.4、§6.2 | 人工集成 | 单独记录 API tool call、Odoo 实际工具执行及回复三种结果；若 `mcp` Schema 问题未解决，真实工具 E2E 记为受阻，不能误报成功。 | 是 | 分离本次 Provider 修复与独立 `mcp` 问题。 |

---

## 12. 停止条件 / 升级闸门

以下门禁必须在本 CC 冻结后、开始实现前关闭。起草阶段状态均为待执行；不得在报告中标为已通过。

| 触发条件 / 门禁 | 要求及升级路径 |
|---|---|
| 脱敏请求体来源核验未完成 | 捕获并检查最终序列化请求，记录 endpoint、`reasoning_effort` 是否存在及来源；遮蔽 key、认证头和消息内容。若该参数来自其他 Odoo 层，先修正真实来源并修订 CC。证据进入 IHR / ATR。 |
| OpenAI 模型参数现值未盘点 | 使用用户指定的 `odoo-bin shell -c odoo.conf` 环境对 `odoo18ce` 做只读盘点；不得建隔离数据库，不得通过直接 SQL 读取或修改。若存在非空非 JSON 值，停止启用约束，先决策兼容处置并修订技术方案 / CC。 |
| 当前实现路径或代码基线与冻结基线不同 | 核验运行中的 checkout / commit。若与 `609ec6dda3645165f6a4a843d7af5d286081a29d` 不同，暂停并确认是否需更新上游基线。 |
| 需要改动 CC 白名单外文件、核心字段、公共接口或数据库数据 | 停止，先修订并批准 CC；架构或技术方案变化同时修订技术方案。 |
| 需要支持其他 effort 值、无条件注入、或迁移 Responses API | 停止；这些改变技术契约，必须先修订并批准冻结技术方案及 CC。 |
| 保存校验影响现存配置的兼容性未确定 | 停止启用严格校验；不得静默忽略、覆盖或清理记录。升级技术方案 / CC 后继续。 |
| `mcp` 兼容问题仍存在 | 可独立完成 Provider payload 自动化及人工 API tool-call 验证；完整 Odoo 工具执行 E2E 标记受阻。不得扩大本 CC 去修 `llm_tool`。 |
| 真实 Provider 需要使用密钥但验证环境未准备 | 记录对应人工验证为 `NOT RUN`，不可将自动化 mock 结果代替真实服务验收。 |

---

## 13. 完成定义 / 关闭标准

本 CC 只有在评审冻结并获实现授权后才可进入执行。执行关闭至少要求：

1. §12 的前置门禁已记录状态；要求为硬门禁的项目未通过时不得宣告完整实现关闭。
2. §4.1 白名单内变更均完成，且没有触碰 §4.2 禁止区域。
3. CC-TEST-001 至 CC-TEST-010 全部通过，并有可追溯的测试记录。
4. CC-TEST-011 至 CC-TEST-013 分别记录 `PASS`、`FAIL`、`BLOCKED` 或 `NOT RUN`，不混淆 Provider 响应与 Odoo 工具执行结果。
5. CC-PRESERVE-001 至 CC-PRESERVE-006 均有验证证据；未配置时原行为通过回归确认。
6. 没有将 API key、业务提示内容或敏感请求正文写入报告。
7. IHR / ATR 记录代码基线、实际文件、自动化测试结果、人工验证证据、未完成项和偏差；本 CC 草稿不填写执行结果。

---

## 14. 追溯矩阵

### 14.1 正向：纳入的技术方案 → CC

| 上游章节 | CC 项 | 备注 |
|---|---|---|
| 技术方案 §4.1 | CC-CHANGE-002、CC-CHANGE-003；CC-PRESERVE-003、004；CC-TEST-001 至 CC-TEST-006 | 参数契约、隔离、配置说明与校验。 |
| 技术方案 §4.2 | CC-CHANGE-002；CC-TEST-005、006、010 | 保存 / 请求时校验及错误处理。 |
| 技术方案 §4.3 | CC-CHANGE-001；CC-PRESERVE-001、002、005；CC-TEST-007 至 CC-TEST-010 | payload 构造和既有字段保留。 |
| 技术方案 §5 | CC-CHANGE-001 至 CC-CHANGE-004；§4.1–§4.2 | 文件级实现边界。 |
| 技术方案 §6 | CC-CHANGE-004；CC-TEST-001 至 CC-TEST-013 | 自动化、真实 Provider 和 E2E 验收。 |

### 14.2 反向：CC → 上游

| CC ID | 上游来源 | 类型 |
|---|---|---|
| CC-CHANGE-001 | 技术方案 §4.3 | 技术方案 |
| CC-CHANGE-002 | 技术方案 §4.1–§4.2 | 技术方案 |
| CC-CHANGE-003 | 技术方案 §5 | 技术方案 |
| CC-CHANGE-004 | 技术方案 §6 | 技术方案 |
| CC-PRESERVE-001 至 CC-PRESERVE-006 | 技术方案 §2–§6 | 技术方案 / 兼容性约束 |
| CC-TEST-001 至 CC-TEST-013 | 技术方案 §4、§6 | 验收设计 |

### 14.3 无 DDD 路径

本次无 DDD。追溯链为：既有 Provider 能力说明 / bug 证据 → 冻结技术方案 → 本 CC → 测试与执行记录。不得为填充追溯表虚构 SRS 或 DDD 编号。

---

## 附录 A — 变更决策（CC-DEC）

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | 复用现有 `llm.model.parameters`，仅由 `llm_openai` 解释 `openai` 命名空间。 | 新增核心字段；Provider 全局固定注入。 | 这是冻结技术方案选定的最小兼容边界；不增加核心 schema，也不改变无配置时行为。 |
| CC-DEC-002 | 首期只接受 `reasoning_effort="none"`，未知键忽略且不透传。 | 放行任意 SDK 参数或支持多个值。 | 避免配置绕过和未验证的 API 参数范围。 |
| CC-DEC-003 | `mcp` Schema 兼容作为独立问题，不扩入本 CC。 | 同一 CC 顺带修复工具执行链。 | 避免把 Provider 请求兼容和另一个 addon 的依赖兼容合并成不可审查的范围。 |

## 附录 B — CC 使用说明

- 本文需先完成评审并明确批准冻结，方可作为实施契约。
- 实施者先关闭 §12 的前置门禁，再严格遵守 §4 文件边界。
- 执行证据写入项目 IHR / ATR；不得在草案或测试计划中预填结果。

## 附录 C — 术语

| 术语 | 含义 |
|---|---|
| Provider tool call | LLM API 响应中返回的 function / tool call 指令。 |
| Odoo 工具执行 | Odoo 端解析并实际调用注册工具后产生的结果。 |
| 脱敏 payload | 保留参数结构及字段存在性、移除凭据和用户业务消息后的请求证据。 |
| `parameters` | 核心 `llm.model` 上已有的自由文本字段；本 CC 不变更其 schema。 |

## 附录 D — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-16 | 初稿：基于冻结技术方案限定 `llm_openai` 工具调用参数兼容修复的文件、行为、测试和实施门禁。 | Draft |
