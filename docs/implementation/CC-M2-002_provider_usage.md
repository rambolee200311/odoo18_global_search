<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# CC-M2-002：Provider Usage 兼容与计量记录

## 0. 文档治理

### 0.1 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-002` |
| Coding Contract | `CC-M2-002` |
| 模块 | 自有 `llm_openai` Provider 适配；新增 `office_engine_m2` Usage 计量模型 |
| 工作类型 | 新功能 / Provider 兼容 / Odoo 数据模型 |
| 变更类型 | 非流式响应增加可选 Usage 元数据；新增受限 Usage 记录与内部写入服务 |
| 版本 | V1.0.0 |
| 状态 | FROZEN |
| 目标 | 捕获 OpenAI SDK 非流式响应中的 token Usage，保持现有响应消费者兼容，并通过 `office_engine_m2` 内部服务持久化最小计量元数据。 |
| 背景 | 当前 `LLMProvider._openai_process_non_streaming_response()` 只标准化 `content` 和 `tool_calls`，丢弃 SDK 的 `response.usage`；M2 后续需要观察每次获准 Provider 调用的 token 数、耗时和结果状态。 |
| SRS 基线 | `SRS_office_engine_m2_ai_mapping.md` V1.0.0 FROZEN |
| TDD 基线 | `TDD_office_engine_m2.md` V1.0.0 FROZEN |
| Implementation Plan 基线 | `IMPLEMENTATION_PLAN_office_engine_m2.md` V1.0.0 FROZEN，阶段 2 / 拟议 CC-M2-002 |
| DDD | N/A；依据见 M2 TDD V1.0.0 |
| TV 基线 | M2 TV Report V1.1 FROZEN；本 CC 不发起外部网络请求，不改变原 TV 结论 |
| 起草日期 | 2026-10-23 |
| 批准记录 | 负责人于 2026-10-23 批准并冻结 CC-M2-002 V1.0.0，授权按本契约实施。 |

### 0.2 基线与阶段门禁

- M2 SRS、TDD 与 Implementation Plan 均以 V1.0.0 Frozen 为本 CC 上游基线；本 CC 不重新解释其业务或技术语义。
- CC-M2-001 已获负责人批准关闭；其纯 Python `office_mapping_verify` 包为本 CC 的前序阶段，不在本 CC 修改范围内。
- Implementation Plan 的 OIP-M2-003 基线门禁由负责人批准的本地基线提交解除；基线 commit 及工作树状态记录在 `IHR-M2-002_provider_usage.md`。实施补丁必须以该基线为父提交，并遵守 §4 文件白名单。
- OIP-M2-008 已由本 CC §4 的精确 Addon 路径、依赖和文件白名单闭环；本 CC 不修改冻结计划的其他内容。
- 负责人已裁定：Provider `usage.status` 只存在于返回字典；持久化复用 `error_code`，不得新增 `usage_status` 字段。
- 负责人已裁定：`base.group_system` 和 `office_engine_m2.group_office_usage_operator` 仅有 Read 权限；普通用户没有 Usage 模型访问权限。
- 负责人已裁定：持久化只通过内部 `record_usage()` 服务；必要提权严格局限于经过白名单验证的 `office.llm.usage` 创建，不得提权访问 thread、message 或业务模型。
- 本 CC 的 Provider 回归仅用 SDK Mock，不调用真实模型，不接触业务数据，不测试其他 Provider。真实 Provider 调用仍受 SRS/计划的数据政策门禁约束。

### 0.3 Draft 与冻结规则

本文件状态为 FROZEN V1.0.0，负责人已授权实施。测试状态仍须在 ATR 中依据实际执行证据记录；不得将测试设计写成测试结果。

## 1. 变更概述

### 1.1 目标

在自有 `llm_openai` 非流式响应标准化方法中增加可选 Usage 元数据，并新增 `office_engine_m2` 的 `office.llm.usage` 模型及仅供服务端内部调用的记录服务。Usage 记录只包含 token 计数、耗时、模型/Provider 标识、关联会话元数据及结果状态，不保存提示词、回答文本或业务内容。

Provider 仅负责将 SDK 响应转换成向后兼容的普通字典；它不得直接访问 Odoo ORM 或 Usage 模型。持久化由 `office_engine_m2` 的内部服务负责。映射编排器对该服务的产品级调用接入不属于本 CC，后续按 Implementation Plan 阶段 5 接入。

### 1.2 本 CC 依据

- M2 TDD V1.0.0：§§2.2、3.1–3.2、7.1–7.2、8.1、10、13.1、17、18；`T-M2-LLM-001`、`T-M2-DATA-002`、`T-M2-BASE-001`、`TD-M2-005`、`TD-M2-006`。
- M2 SRS V1.0.0：`FR-M2-013`、`NFR-M2-006`、`NFR-M2-007`、`AC-24`。其中 AC-24 只提供性能可观察性的相关业务背景，不被扩大解释为 token Usage 的单独验收条款。
- M2 Implementation Plan V1.0.0：阶段 2、§§7–8、§10–14，特别是 Mock SDK 回归、Usage ACL/最小化、安装升级及 OIP-M2-003 / OIP-M2-008。
- 当前源码检查证据：`openai_provider.py` 的 `openai_chat()` 非流式路径调用 `_openai_process_non_streaming_response(response)`；现方法只返回 `content` / `tool_calls`，标准化响应由 `llm_assistant._handle_non_streaming_response()` 读取这两个键。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本 CC 的相关性 |
|---|---|---|
| FR-M2-013 | 查询与 Provider 失败处理 | 计量记录只存受控结果状态/错误码；Provider 失败不得伪装成无数据或成功。 |
| NFR-M2-006 | 隐私最小化 | Usage 表禁止保存 Prompt、Completion、模板、业务样例、附件内容或密钥。 |
| NFR-M2-007 | 性能可观察性 | 记录调用耗时的受控元数据；不在本 CC 设定未经批准的性能 SLO。 |
| AC-24 | Skill 路径可观察性 | 仅作响应时间可观察性的相关验收背景；不将其改写为本 CC 的产品行为。 |

### 2.2 DDD 引用

N/A。负责人已批准 M2 DDD 不适用；本 CC 新增的是 Odoo 技术计量模型，不建立业务领域聚合。

### 2.3 TDD 引用

| TDD ID / 章节 | 标题 | 本 CC 落实范围 |
|---|---|---|
| `T-M2-LLM-001` | 非流式响应 Usage 标准化与兼容 | 从 SDK 响应提取白名单 token 指标；缺失不伪造为零；响应仍保留原 `content` / `tool_calls`。 |
| `T-M2-DATA-002` | Token/运行日志数据最小化 | Usage 记录不包含 Prompt/Completion、密钥、模板内容或业务样例；读取授权受限。 |
| `T-M2-SEC-001` | 获准 Provider / 模型限制 | 不改变 Provider/model 选择；本 CC 自动化测试使用 `gpt-5.6-luna` 的 Mock 语义，不测试其他 Provider。 |
| `T-M2-BASE-001` | 冻结基线要求 | 代码实施前核验可复现源码、冻结基线和补丁范围。 |
| TDD §§7.1–7.2 | Provider Usage / 计量记录 | 标准化字段、缺失语义、Usage 模型最小字段和运维组读取限制。 |
| TDD §13.1 第 7 项 | Usage 回归 | 覆盖有/无/非法 Usage、Provider 错误、重试记录与聊天响应兼容。 |

### 2.4 计划与 TV 引用

| 来源 | 状态 | 本 CC 处理 |
|---|---|---|
| Implementation Plan 阶段 2 / 拟议 CC-M2-002 | FROZEN V1.0.0 | 本 CC 覆盖 Provider 标准化、Usage 服务/模型、ACL 与 Mock/ORM 测试；不覆盖 Mapping Session。 |
| OIP-M2-003 | OPEN，阻塞本阶段干净源码基线 | 冻结/实施前记录 `llm_openai` 准确 commit 和差异；不得将 dirty tree 当成可复现基线。 |
| OIP-M2-008 | OPEN，阻塞本 CC 冻结前置闭环 | 本稿给出 Addon 路径、依赖和 Provider/Usage 分层；审批时核对其与计划一致。 |
| TV-M2-002 | 已有单次合成输入 Usage 快照 | 只作背景，不把 TV 数据复制成测试结果或生产性能承诺。 |
| TV 其他 Provider 覆盖 | 未测试 / 不适用 | 不拓展为其他 Provider 的兼容承诺。 |

## 3. 范围冻结

### 3.1 范围内

- 仅修改自有 `llm_openai` 文件中的 `LLMProvider._openai_process_non_streaming_response(response)` 方法体，使其额外返回可选、经白名单过滤的 `usage` 及可选 `response_id`。
- 新建 `office_engine_m2` 最小 Odoo Addon 壳及 `office.llm.usage` 模型；模型仅存 §5.2 列出的最小计量元数据。
- 提供一个非 RPC 暴露的内部 `record_usage()` 服务，供后续 M2 编排服务调用；校验/规范化允许的元数据后写入一条 Usage 记录。
- 为系统管理员和显式授权的 Office Usage 运维组提供只读 ORM 访问；普通业务用户无权 search/read/create/write/unlink Usage 记录。
- 编写 SDK Mock、响应消费者兼容、Odoo ORM、ACL、数据最小化及 Addon 安装/升级测试；测试不发起外部网络请求。

### 3.2 超出范围

- 修改 `openai_chat()`、请求参数、消息格式化、任何流式处理路径、`llm_assistant`、`llm_thread`、其他 Provider 或 Odoo 官方源码/官方 Addon。
- 在 Provider 层直接调用 Odoo ORM、`office_engine_m2`，或让 Provider 依赖 M2 Addon。
- 把 Usage JSON 写入 `mail.message.body_json`、聊天正文、工具调用参数或前端消息 payload。
- 将本 CC 的 Usage writer 接入 Mapping Orchestrator 的每次生产调用；该调用接入属于后续阶段 5。此处提供并测试内部服务契约。
- 创建 Mapping Session、Skill、业务字段快照、Prompt/Completion 日志、费用计算、趋势仪表盘、通用计费、其他 Provider 支持、Usage retention cron 或数据导出功能。
- 真实外部 API 调用、真实业务数据传输、模型效果/Token 容量测试。

### 3.3 非目标

- 不改变 OpenAI Provider 的选择、模型准入、工具调用策略、聊天响应内容或用户可见行为。
- 不规定 Usage 的长期保留期限；在隐私政策/OIP-M2-003 未获批准前，不得据本 CC 宣称生产长期留存已获批准。
- 不将 Usage 计数换算成费用，不根据 token 量拦截或调整模型请求。

### 3.4 追溯约束

本 CC 仅纳入 §2.1–2.3 明列的上游项。每项必须映射至 §5 的 CC-CHANGE；未列入范围的 M2 需求不因本 CC 获得实施授权。

## 4. 变更边界

### 4.1 允许修改或新增的文件

除测试发现必须修正的本 CC 范围内契约错误外，只允许以下文件；所有生产 Addon 代码必须位于 `mymodules/office_engine_m2/`，`llm_openai` 既有生产代码只允许修改指定方法。

| 动作 | 精确路径 | 允许内容 |
|---|---|---|
| 修改 | `mymodules/odoo-llm/llm_openai/models/openai_provider.py` | 仅修改 `LLMProvider._openai_process_non_streaming_response()` 方法体；不改类外常量、其他方法、imports（除非评审批准的必要且最小依赖）或文件其他区域。 |
| 新增 | `mymodules/office_engine_m2/__init__.py` | 导入本 Addon 的 models/services。 |
| 新增 | `mymodules/office_engine_m2/__manifest__.py` | 声明 Addon 元数据与 TDD §3.1 所列依赖；不添加非本 CC 的前端资产。 |
| 新增 | `mymodules/office_engine_m2/models/__init__.py` | 导入 Usage 模型。 |
| 新增 | `mymodules/office_engine_m2/models/office_llm_usage.py` | 定义 `office.llm.usage` 字段、约束及私有记录入口；不定义 Mapping Session/Skill。 |
| 新增 | `mymodules/office_engine_m2/services/__init__.py` | 导出内部 Usage 服务。 |
| 新增 | `mymodules/office_engine_m2/services/usage_service.py` | 定义仅供服务端 Python 调用的 `record_usage()`，执行数据白名单校验及最小化创建。 |
| 新增 | `mymodules/office_engine_m2/security/office_engine_m2_groups.xml` | 定义 `office_engine_m2.group_office_usage_operator`；不将其反向提升为系统管理员组。 |
| 新增 | `mymodules/office_engine_m2/security/ir.model.access.csv` | Usage 行读取仅授予 `base.group_system` 与专用运维组；普通用户无读/写/建/删权限。 |
| 新增 | `mymodules/office_engine_m2/tests/__init__.py` | 导入本 CC 的 Odoo 测试。 |
| 新增 | `mymodules/office_engine_m2/tests/test_provider_usage.py` | 用 SDK Mock 覆盖 Provider 非流式 Usage 提取和原响应兼容。 |
| 新增 | `mymodules/office_engine_m2/tests/test_office_llm_usage.py` | 覆盖 Usage writer、字段最小化、空值语义、权限与公司/线程关联边界。 |
| 新增 | `mymodules/office_engine_m2/tests/test_response_compatibility.py` | 覆盖 `llm_assistant` 非流式消费者与旧聊天/工具消息行为。 |

如果实现需要修改清单外文件、修改 `openai_chat()`/消费者、引入新的外部依赖或修改基线，应按 §12 停止并升级，不得自行扩展白名单。

### 4.2 禁止修改

| 类型 | 禁止内容 |
|---|---|
| 自有 Provider 代码 | 除 §4.1 指定方法外，不得改 `llm_openai` 其他生产方法、Manifest、模型配置、视图、通用 LLM 核心或 Provider 选择逻辑。 |
| 官方源码 | 不修改 Odoo 官方源码或官方 Addon。 |
| 其他 Provider | 不修改 Anthropic、DeepSeek、Ollama 或其他 Provider。 |
| 聊天响应 | 不改 `llm_assistant._handle_non_streaming_response()`、`llm_thread`、消息渲染、`body_json` schema 或 UI。 |
| M2 后续模型 | 不创建 Mapping Session、Skill、Retriever 编排、Mapping RPC/Card 或 M1 请求接入。 |
| 运行环境 | 不安装/升级生产依赖，不执行真实外网调用，不创建隔离数据库，不修改 `odoo.conf`。 |
| 未列文件 | 不修改上述白名单以外的任何路径。 |

### 4.3 Addon 依赖

新增 Addon 仅依赖 TDD V1.0.0 §3.1 中已列出的模块：`office_engine_odoo`、`llm_assistant`、`llm_tool`、`llm_openai`（及 Odoo manifest 所需的基础间接依赖）。不得借此创建阶段 3 的 Session/Skill 功能。若实际依赖解析要求新增未列模块，停止并回到 TDD/计划评审。

## 5. 必需的行为变更

| ID | 当前行为 / 缺口 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 非流式 Provider 标准化丢弃 SDK `response.usage` 与可用 response ID。 | 仅在 `_openai_process_non_streaming_response()` 对 SDK 返回的白名单 Usage 值做安全标准化，并作为额外可选 `usage` / `response_id` 返回；绝不修改已有 `content` / `tool_calls` 值或形状。 | CC-CHANGE-001 |
| 2 | M2 没有持久化 Provider 计量的 `office.llm.usage` 模型。 | 新建 §5.2 所列最小 Usage 模型；服务端生成 `call_uuid` 与 `created_at`；可空 token 值保持缺失语义；必要字段有数据库约束。 | CC-CHANGE-002 |
| 3 | 没有隔离于 Provider、可被后续编排调用的 Usage 写入服务。 | 提供非 RPC 的内部 `record_usage()`；只接收服务端已知的计量元数据，验证类型/范围并写入 Usage；不让 Provider 依赖 Addon/ORM，也不接受原始 prompt/response。 | CC-CHANGE-003 |
| 4 | Usage 模型的读取授权尚未建立。 | 只有 `base.group_system` 或 `office_engine_m2.group_office_usage_operator` 可读取；两组只读；普通用户无直接模型权限。内部记录写入仅经受控服务完成，服务不公开为 Odoo RPC。 | CC-CHANGE-004 |
| 5 | 缺少真实序列化消费者兼容、缺失 Usage、权限与安装回归证据。 | 增加 Mock SDK 与 Odoo 测试；证明 `llm_assistant` 仍只把 `content` / `tool_calls` 写入消息，streaming 不变，缺失/非法 Usage 不使有效内容失败；模块可在批准的开发库安装/升级。 | CC-CHANGE-005 |

### 5.1 非流式标准化响应契约

对 SDK 响应仅提取以下计量值：`prompt_tokens`、`completion_tokens`、`total_tokens`，以及 `completion_tokens_details.reasoning_tokens`（如 SDK 提供）；`response_id` 仅从 SDK `response.id` 读取。不得使用 `model_dump()` 或透传 SDK 的整个 Usage/response 对象。

| 输入状态 | 标准化行为 |
|---|---|
| SDK Usage 有效 | 返回原 `content` / `tool_calls`，并附加仅含白名单数值及 `status` 的 `usage` 字典；`response_id` 有合法值时一并附加。 |
| Usage 对象缺失或为 `None` | 保留原响应；省略 `usage` 键。调用写入服务时将计数写为缺失值并将稳定码记为 `error_code=usage_missing`，不得写成 0。 |
| 单项计数缺失 | 对应计数保持缺失，不根据其他 token 数推算；SDK 提供的有效计数照原值保留；Usage 字典状态为 `partial`。 |
| 单项计数类型非法、为负数或为 Boolean | 该值不作为 token 数；响应正文/工具调用仍须保留；Usage 字典状态为 `invalid`，不得因计量字段异常把有效 `content` / `tool_calls` 变成 Provider 错误。 |
| Usage 含未知字段 | 忽略未知字段，不持久化原始对象或附加文本。 |
| `content` / `tool_calls` 为空但 Usage 存在 | 只返回可选计量元数据；既有消费者仍按“无可展示内容/无工具调用”处理，不得把 Usage 当作聊天回复。 |

token 计数必须是 Python/JSON 整数且 `>= 0`，Boolean 不视为整数；不得将字符串/浮点数隐式转换。`reasoning_tokens` 可空。`total_tokens` 必须保留 Provider 原值，不自行重算。Usage 字典的 `status` 仅取 `available`、`partial`、`invalid`：必需计数齐全且合法为 `available`，SDK 对象存在但必需计数缺失为 `partial`，任一识别字段非法为 `invalid`（非法优先）；reasoning detail 缺失不单独导致 partial。新增 Usage 结构只在非流式响应出现；streaming 路径保持现状。

### 5.2 `office.llm.usage` 字段契约

| 字段 | 约束 |
|---|---|
| `call_uuid` | 必填、服务端生成、唯一；非授权凭证。 |
| `thread_id` | 可空，关联调用方已校验的 `llm.thread`；不在本 CC 新建 `office.mapping.session`。 |
| `owner_id` / `company_id` | 必填；由调用时的 Odoo `env.user` / `env.company` 在任何受限写入前生成，不接收客户端传值。 |
| `provider_code` | 必填；本阶段仅记录现有 OpenAI provider 标识，不开放其他 Provider。 |
| `model_name` | 必填，由服务端调用上下文中的当前模型确定；不得信任客户端传入模型名。 |
| `response_id` | 可空；仅存 SDK 响应 ID，不存 API key、Base URL 或请求头。 |
| `prompt_tokens`、`completion_tokens`、`total_tokens`、`reasoning_tokens` | 可空非负整数；`0` 是有效计数，缺失必须可与 0 区分；不得重算 Provider 数值。 |
| `elapsed_ms` | 可空非负整数；由可信服务端调用方按请求完整耗时提供，本 CC 不把响应解析耗时冒称为网络耗时。 |
| `attempt_no` | 可空正整数；由服务端调用方确定，不接受浏览器直接写入。 |
| `outcome` | 必填受限结果：`success`、`provider_error`、`processing_error`。 |
| `error_code` | 可空稳定短码；不保存异常全文、堆栈或用户输入。 |
| `create_date` | Odoo 自动服务端时间。 |

Usage 缺失时，四项计数均为 null，`outcome` 仍按调用实际成功/失败记录，`error_code=usage_missing`；部分/非法 Usage 分别以 `usage_partial` / `usage_invalid` 作为稳定码，调用结果仍以 `outcome` 独立表达。持久化模型不得新增 `usage_status` 字段；这与 TDD §7.2 现有字段表保持一致。

持久化模型不得存在 Prompt、Completion、模板文字、业务字段值/样例、文件 bytes、API key、自由文本请求/响应或原始 SDK JSON 字段。ORM 字段、`record_usage()` 参数和返回值均按此白名单封闭；未列入的参数拒绝，不得静默忽略。内部服务返回 `call_uuid` 或非敏感状态，不向调用方返回 Usage ORM 记录的特权 recordset。

### 5.3 内部记录服务及写入权限

`record_usage()` 必须是服务端 Python 内部入口，不通过 Controller、公开 RPC 模型方法、菜单按钮或用户可编辑表单暴露。它只创建 `office.llm.usage` 元数据行：

- 先在原始调用 `env` 下解析当前用户、公司及可选 thread 关联；若 `thread_id` 不属于当前调用可访问范围则拒绝关联。
- 严格挑选 §5.2 允许字段；调用方额外传入 Prompt/Completion/样例/文件/密钥字段或任意未知参数时必须拒绝，且在测试中证明不会落库。
- 如实现需要受限提权以写入只读 Usage 模型，提权只能用于经过白名单校验的 `office.llm.usage.create()`；不得对线程、消息、附件或业务模型 `sudo()`。普通用户不能直接 create/write/unlink Usage。
- 日志只记录可诊断的稳定码，不记录调用参数、原始异常消息、Prompt/响应或 token 之外的业务值。

## 6. 既有行为保留

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | OpenAI 非流式 `content` 原值、缺失时的既有行为和消息正文渲染保持不变。 | 现有 `llm_assistant`/聊天消费路径依赖该响应契约。 | CC-PRESERVE-001 |
| 2 | `tool_calls` 列表结构、顺序、ID、function name/arguments 保持不变。 | 工具执行循环依赖原始工具调用结构。 | CC-PRESERVE-002 |
| 3 | `_handle_non_streaming_response()` 只把 `content` 放入正文、只把 `tool_calls` 写入 `body_json`；新增 `usage` / `response_id` 不进入消息。 | 计量元数据不得成为用户聊天内容或工具调用数据。 | CC-PRESERVE-003 |
| 4 | Streaming 路径、其他 Provider、OpenAI 请求参数和模型选择行为保持不变。 | 本 CC 只改非流式响应标准化；无权扩大到其他路径。 | CC-PRESERVE-004 |
| 5 | 普通用户不能读取或直接改写 Usage；获授权管理员/运维组读取只读计量数据。 | TDD 的 Usage 数据隔离要求。 | CC-PRESERVE-005 |
| 6 | 缺失/非法 Usage 不能造成有效响应内容丢失，也不能伪造计数 0。 | Usage 是观测元数据，不应改变业务响应成功/失败事实。 | CC-PRESERVE-006 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| `T-M2-LLM-001` | 适用 | §5.1 标准化方法、响应兼容 | CC-TEST-001–004 |
| `T-M2-DATA-002` | 适用 | §5.2 数据字段、§5.3 服务白名单、无正文日志 | CC-TEST-005–007 |
| `T-M2-SEC-001` | 适用 | 不改 provider/model 准入；测试只使用获准模型的 Mock | CC-TEST-001、008 |
| `T-M2-BASE-001` | 适用 | §0.2 与 §12 源码基线门禁 | IHR/ATR 基线记录 |
| `T-M2-SEC-004` | 不适用 | 本 CC 不执行业务字段读取或 Retriever 查询 | — |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 是；通过新增 Odoo ORM 模型在模块安装/升级时创建新表，不手写 SQL DDL。 |
| 迁移脚本 | N/A；本 CC 不修改既有表结构或既有数据。 |
| 数据源 | 非流式 SDK response 的白名单 Usage 值及服务端调用上下文元数据。 |
| 目标 | 新模型 `office.llm.usage`。 |
| 恢复 / 回滚策略 | 本 CC 无数据升级迁移。测试数据使用 Odoo 测试事务回滚；如开发验证插入持久化记录，按唯一 `call_uuid` 通过 ORM 清理。不得手工删数据库表或 filestore。Addon 回滚/卸载不得作为生产数据保留策略。 |
| 验证 | 安装/升级后检查模型注册、字段、唯一约束、ACL；测试记录在事务结束后不残留。 |

留存期限仍服从 TDD §7.2 与获批部署政策；本 CC 不发明保留天数、自动删除规则或长期留存批准。生产调用接入前如留存政策仍未批准，按 §12 停止相关生产启用并升级处理。

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | N/A；不新增 HTTP/RPC endpoint。 |
| Provider 标准化结果 | 在现有非流式 dict 中增加可选 `usage` 与可选 `response_id`；原键及其值/类型不变。 |
| Usage 服务契约 | 内部 Python `record_usage(...)`；输入为调用方已验证的 Provider 元数据、服务器端计时/结果和可选可访问 thread；返回非敏感关联标识/状态。 |
| 向后兼容 | 是；原有消费者只读取 `content`/`tool_calls`，必须通过回归证明新键被忽略且不进入聊天内容。 |
| Adapter 变更 | `LLMProvider._openai_process_non_streaming_response(response)`，见 §4.1；无 Provider Adapter 请求契约变化。 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 新建 `office_engine_m2.group_office_usage_operator`；`base.group_system` 与该组只读 Usage。 |
| 变更的 ACL | 新模型只有上述授权组具有 read ACL；普通 `base.group_user` 不得读取/创建/修改/删除。运维组不得写或删。 |
| 记录创建 | 仅内部服务创建；若经受限提权，只能用于已清洗 Usage 元数据的新模型记录。不得提权读取 thread、message、附件或业务记录。 |
| 敏感数据暴露检查 | `T-M2-DATA-002` 已应用：不存 Prompt、Completion、API key、Base URL、模板或业务样例；错误码不得含原始异常文本。 |
| 数据可见范围 | 授权系统管理员/运维组可读计量行；普通用户不可通过 ORM search/read、RPC 或视图访问。 |

## 11. 测试契约

测试均使用项目 `venv`、当前批准的 `odoo.conf` 与既有开发数据库 `odoo18ce`；不得创建隔离数据库，不得发起真实外网请求。SDK 层以 Mock 响应验证，Odoo ORM/权限以 Odoo `TransactionCase`/模块安装升级测试验证。以下状态在 Draft 阶段均为 `NOT RUN`。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | 有效 Usage 提取 | `T-M2-LLM-001`、TDD §7.1 | Provider 单测 / SDK Mock | Mock ChatCompletion 含 content、多个 tool calls、prompt/completion/total/reasoning tokens 与 response ID；标准化输出精确保留旧 `content` / `tool_calls`，新增 usage 数值与 response_id 匹配；未知 SDK 字段不透传。无网络请求。 | N/A | 验证指标准确捕获且不扩大响应数据。 |
| CC-TEST-002 | Usage 缺失/部分缺失 | `T-M2-LLM-001` | Provider 单测 / SDK Mock | 覆盖无 `usage` 属性、`usage=None`、单项 token 缺失及无 reasoning detail；调用不崩溃、不将缺失转换为 0、不丢失有效 content/tool_calls；缺失计数到达服务后持久化为 null，并以 TDD 已列 `error_code=usage_missing` 或 `usage_partial` 表示。 | N/A | 防止 SDK 版本/响应差异破坏聊天或伪造用量。 |
| CC-TEST-003 | 非法 Usage 字段隔离 | `T-M2-LLM-001` | Provider 单测 / SDK Mock | 覆盖负数、Boolean、字符串、浮点数及异常属性访问；仅非法计量字段变为缺失/`invalid`，有效 content/tool_calls 不丢失、不转换、不抛出计量解析异常。 | N/A | 计量异常不能改变 Provider 业务响应事实。 |
| CC-TEST-004 | Chat Completions / 工具调用 / 无内容回归 | `T-M2-LLM-001`、CC-PRESERVE-001–004 | Odoo/Provider 回归 | 通过真实 `_openai_process_non_streaming_response` 和 `llm_assistant._handle_non_streaming_response()` 的现有路径，断言正文仍只有 content、`body_json` 仍只有 tool_calls、usage/response_id 从不序列化到消息；无内容但有 usage 时仍按既有“无响应内容”处理。另断言 streaming 行为未改变。 | N/A | 证明可选字段不污染用户聊天、工具循环或 streaming。 |
| CC-TEST-005 | Usage writer 数据白名单与精确落库 | `T-M2-DATA-002`、TDD §7.2 | Odoo `TransactionCase` | 通过内部 `record_usage()` 写入成功/部分/缺失/非法、provider_error 和 processing_error 样例；计数原值保存、0 与 null 可区分、elapsed/attempt/outcome/error code 满足边界；初调与修复调用分别产生独立 call_uuid/attempt_no；owner/company 从 env 生成；额外传入 Prompt、Completion、API key、模板/样例/文件字段或未知参数必须拒绝且不得落库；raw SDK object 不可序列化入库。 | N/A | 验证隐私最小化及数据完整性。 |
| CC-TEST-006 | 普通用户/系统管理员/运维组权限 | TDD §7.2、§11 | Odoo `TransactionCase` 权限矩阵 | 普通 `base.group_user` 对 Usage search/read 被 ACL 拒绝，且不能直接 create/write/unlink；`base.group_system` 与 `group_office_usage_operator` 可 read；两授权组仍不能 write/unlink。通过普通用户服务写入的 owner/company 保持为当前 env 用户/公司；未授权 thread 关联拒绝。不得用 `sudo()` 冒充普通用户权限测试。 | N/A | 证明仅获准运维角色能读，服务端写入不扩大业务记录权限。 |
| CC-TEST-007 | Addon 安装/升级与权限数据加载 | TDD §3.1、Implementation Plan 阶段 2 | Odoo 集成测试 | `office_engine_m2` 在既有 `odoo18ce` 可安装/升级；Usage 模型、表、ACL 与运维组注册正确；依赖不引入计划外 Addon；测试/验证数据经事务回滚或 ORM 精确清理。 | N/A | ORM 模型与 ACL 需由真实 Odoo 注册表验证。 |
| CC-TEST-008 | Provider SDK Mock 不访问网络 | Implementation Plan §§7–8 | 单测/集成测试 | 将 `client.chat.completions.create` 替换为 mock；断言调用只返回 mock 且无 HTTP/socket 连接；测试运行无 API key 依赖。 | N/A | 明确符合本 CC 无外网验证边界。 |

### 11.1 执行命令与证据

- Provider/Addon 自动化测试命令以仓库可用的 Odoo test runner 为准，必须使用 `venv/bin/python` 与 `odoo-bin -c odoo.conf -d odoo18ce`，不得临时换数据库。
- 需在 ATR 中记录实际命令、测试数据库、Odoo/Python/OpenAI SDK 版本、覆盖测试数量、模块安装/升级日志、Mock 使用证明、测试记录清理及 ACL 正反向结果。
- 不声明全仓库 100% 覆盖；本 CC 必须覆盖 Usage 新增逻辑的所有关键分支（有效、缺失、部分、非法、工具调用/无正文消费者、成功/失败写入和权限拒绝）。具体报告值以实际 ATR 为准。
- 若运行环境/数据库当前状态不允许安全安装或升级，记录为 `BLOCKED` 并停止，不改配置、不另建数据库、不把未执行项记为 PASS。

## 12. 停止条件 / 升级闸门

| ID | 触发条件 | 升级路径 |
|---|---|---|
| 1 | 无法确定 `llm_openai` 的 clean commit 与允许补丁差异，或 provider 文件中存在与本 CC 冲突的未提交修改 | → 先完成 OIP-M2-003 源码基线清理/登记；本 CC 不冻结或不实施 |
| 2 | 需要修改 `_openai_process_non_streaming_response()` 以外的 Provider 生产代码、`llm_assistant` 或 `llm_thread` 才能实现兼容 | → M2 TDD / Implementation Plan 影响评审；不得扩大文件白名单 |
| 3 | Usage 写入需增加 TDD 未定义的公开 RPC、业务字段或调用者权限 | → TDD 修订与重新批准 |
| 4 | Odoo 字段类型无法区分缺失与计数 0，或服务端无法安全限制 Usage 创建权限 | → TDD 技术补充/验证；不得以 0 或开放 ACL 兜底 |
| 5 | 需要确定/改变数据保留期限、长期存储策略或 provider 数据政策 | → 关闭对应 SRS/TDD OPEN 项并完成隐私审批；不得在本 CC 内猜测 |
| 6 | 发现 Prompt/Completion/业务值/API key 进入日志、异常文案或 ORM 字段 | → 立即停止并修复隐私问题；复测通过前不得继续 |
| 7 | 新增 `usage` 导致聊天正文、工具循环或 streaming 行为改变 | → 停止；保持旧响应契约并退回 TDD/CC 评审 |
| 8 | 需要改动 CC 白名单之外的文件、生产依赖、官方模块或其他 Provider | → CC/TDD 变更控制；禁止顺手修改 |
| 9 | 必须真实调用外部模型才能验证 SDK Usage | → 停止；本 CC 验收限定 SDK Mock；如确需真实调用须另有授权和获批合成数据窗口 |
| 10 | 测试要求隔离数据库或清理可能影响既有业务数据 | → 停止并改用回滚测试/精确合成记录方案；不得创建新 DB 或宽泛删除 |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | §5 CC-CHANGE-001–005 全部完成，实际差异严格限制在 §4.1 文件列表及指定 Provider 方法内 | 硬闸门 |
| 2 | CC-TEST-001–008 均有 ATR 原生状态和真实证据；适用项全部 PASS，未通过项按项目授权流程处理 | 硬闸门 |
| 3 | `content`、`tool_calls`、消息正文/`body_json` 及 streaming 回归通过；Usage 元数据不向聊天显示 | 硬闸门 |
| 4 | 缺失/非法 Usage 不伪造 0、不丢失有效响应；Usage 表只含白名单元数据 | 硬闸门 |
| 5 | 普通用户不能读/写 Usage；系统管理员和专用运维组可读但不可改写/删除；内部服务仅能创建经过验证的 Usage | 硬闸门 |
| 6 | Addon 在批准的现有 `odoo18ce` 环境安装/升级验证通过；测试数据无残留；ATR 绑定到实际源码与哈希基线 | 硬闸门 |
| 7 | IHR/ATR 完成；本 CC 不需用户可见 UI 时 HVR 记为 N/A 并说明理由；Final Report/FR 由后续批准流程处理 | 交付闸门 |

CC 完成不等于本 CC 自动关闭；关闭、提交或推送仍须负责人明确批准。

## 14. 追溯矩阵

### 14.1 正向：纳入范围的上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| `T-M2-LLM-001` | CC-CHANGE-001、005 | Provider Usage 标准化与响应兼容。 |
| `T-M2-DATA-002` | CC-CHANGE-002–004 | Usage 数据最小化、内部写入和访问控制。 |
| `NFR-M2-006` | CC-CHANGE-002–004 | 不保存敏感正文/业务内容。 |
| `NFR-M2-007` | CC-CHANGE-002、003 | 计量耗时可观察；不创建固定 SLA。 |
| `FR-M2-013` | CC-CHANGE-001、003、005 | 区分受控 Provider 失败状态。 |
| `T-M2-BASE-001` | CC-CHANGE-005 | 可复现源码与测试基线。 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001 | `T-M2-LLM-001`、TDD §7.1 | TDD |
| CC-CHANGE-002 | `T-M2-DATA-002`、TDD §7.2 / §8.1 | TDD |
| CC-CHANGE-003 | `T-M2-DATA-002`、TDD §3.2 / §7.2 | TDD |
| CC-CHANGE-004 | `T-M2-DATA-002`、TDD §7.2 | TDD |
| CC-CHANGE-005 | `T-M2-LLM-001`、`T-M2-BASE-001`、阶段 2 Gate | TDD / Plan |

### 14.3 无 DDD 路径

N/A。追溯链为 `SRS / TDD / Implementation Plan → CC → ATR/IHR → FR`；不虚构 DDD 编号。

## 附录 A — 实现决策（CC-DEC）

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | Provider 标准化与 ORM 持久化分层；Provider 只返回最小可选 Usage，`office_engine_m2` 内部服务负责持久化。 | 在 Provider 内直接依赖 ORM/Addon 写 Usage。 | 保持 Provider 边界、避免反向依赖；符合 TDD §§2–3。 |
| CC-DEC-002 | 对 SDK Usage 缺失/非法不伪造数值；计数缺失保持 null，Provider 字典用 `status` 表达部分/非法，持久化用 TDD 已列 `error_code` 记录 `usage_missing` / `usage_partial` / `usage_invalid`，不新增模型字段。 | 填 0、用总量推算，或未经 TDD 许可增加状态列。 | 0 是真实计数；TDD 现有 `error_code` 可承载稳定状态码，保持模型字段表不扩张。 |
| CC-DEC-003 | Usage writer 仅内部 Python 调用；若需提权，仅对白名单化计量模型执行 create。 | 给普通用户开放模型 create ACL 或公开 RPC。 | 防止普通用户伪造/修改计量行，同时不赋予业务记录提权。 |
| CC-DEC-004 | 本 CC 不增加 retention 时限、费用视图或定时清理。 | 在实现时自行选定保留天数/成本口径。 | 相关政策未由 SRS/TDD 冻结；不得在 CC 中代替业务/隐私负责人决策。 |

## 附录 B — 审批裁定

| 项目 | 已批准裁定 | 状态 |
|---|---|---|
| Usage 状态 | Provider 字典返回 `status`（`available` / `partial` / `invalid`）；落库复用 `error_code`（`usage_missing` / `usage_partial` / `usage_invalid`）；不得新增 `usage_status` ORM 字段。 | RESOLVED |
| 系统/运维读取组 | `base.group_system` 与 `office_engine_m2.group_office_usage_operator` 只授予 Read；均不可 Write/Unlink；普通用户无任何 Usage 模型访问权。 | RESOLVED |
| 受限创建 | 仅由内部 `record_usage()` 服务写入；必要 `sudo()` 仅限对 `office.llm.usage` 的白名单化 create，严禁对 thread、message 或业务模型提权。 | RESOLVED |
| Addon 依赖/路径 | Addon 固定为 `mymodules/office_engine_m2/`，依赖遵循 TDD §3.1 与 §4 白名单。 | RESOLVED |
| `llm_openai` 基线 | 以负责人指示创建的本地 baseline commit 为源码基线；准确 hash、`llm_openai` 文件状态及工作树状态记录于 IHR。 | RESOLVED — OIP-M2-003 |

## 附录 C — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-23 | Draft | 按负责人授权起草；依据 M2 SRS/TDD/Implementation Plan 冻结基线定义 Provider Usage、最小计量模型、内部记录服务、ACL 与 Mock/ORM 验收契约。 |
| V1.0.0 | 2026-10-23 | FROZEN | 负责人批准附录 B 四项裁定；OIP-M2-003 本地基线 hash 见 IHR；授权实施。 |

## 15. 关闭记录

负责人于 2026-10-23 批准关闭本 CC。CC-TEST-001–008 均为 PASS，ATR/IHR 已更新；需求追溯结论见 [`FR-M2-002_provider_usage.md`](FR-M2-002_provider_usage.md)。实施 commit `091942a2cd2b0feadf0a41c3c3c7fc345c4fc186` 已推送。契约基线保持 FROZEN V1.0.0；关闭批准不改变其规范范围。
