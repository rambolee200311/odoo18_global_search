# CC-M2-CB-01 — Responses Provider Adapter

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-01 — Responses Provider Adapter |
| 版本 | v0.1 |
| 状态 | **DRAFT — AUTHORIZED FOR REVIEW — NOT AUTHORIZED FOR EXECUTION** |
| 上游实施计划 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` — FROZEN V2.0.1，仅为计划基线 |
| 上游设计 | `docs/design/TDD_office_engine_m2_v2.0.2.md` — FROZEN，仅为设计基线 |
| 起草日期 | 2026-11-06 |
| 负责人 | 待登记 |

> 本稿只定义拟议契约，等待人工评审、冻结及单独 Coding Authorization。计划冻结不授权编码、测试副作用、Provider 请求、服务操作、模块升级、数据库变更或发布。本契约与只读审计 `CC-M2-B-01_Runtime_Baseline_Alignment_v0.2.md` 是不同工作项；后者保持原范围、状态和证据，不由本稿覆盖。

## 1. 目标与验收边界

在现有 OpenAI Provider 既有凭据和配置边界内，为 Candidate B 提供隔离的 Responses API + Code Interpreter 请求/文件返回适配能力，并保持普通 Chat Completions 行为兼容。

本 CC 的 Adapter 职责止于：受控请求、响应及工具结果规范化、下载真实文件字节、最小 Provider 元数据及错误分类。Provider 返回文件不代表候选已接受；文件版本登记、业务风险确认、候选接受、Preview/Finalize 和附件交付分别由后续 CC 的职责决定。

契约不能证明模型能完成任意 Excel 编辑。一次合成文件的真实接口验证只证明对应模型、请求和文件断言；不得外推为多轮编辑、复杂工作簿保真、Odoo 端到端或生产可用。

## 2. 上游证据与强制门禁

### 2.1 证据基线

- `TV_LLM_OFFICE_EDITING_PHASE1A2_REPORT_v0.2.md`：已记录 3 次真实 Responses 请求；其中一次返回并下载真实合成 XLSX，独立回读支持该次简单文件编辑断言。不能代表 Odoo 集成、多轮、复杂工作簿、附件交付或长期可靠性。
- `TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D_REPORT_v0.2.md`：2 次请求遭遇 `APIConnectionError`，没有收到服务端响应或候选文件；后续阶段未运行。该记录为历史 `Integration Blocked / NOT RUN`，不是模型或 Adapter 能力 `FAIL`。
- `mymodules/odoo-llm/llm_openai/models/openai_provider.py` 的当前 Chat Completions 路径通过 `client.chat.completions.create()`。现有聊天路径和 Responses 文件编辑路径必须分离。
- TDD V2.0.2 §3、§4、§6 和实施计划 V2.0.1 §0、§3.3、§4 是本稿的架构与验收边界。

### 2.2 编码前置门禁

冻结及实施本 CC 前须确认：

1. SRS 对托管文件编辑路径的正式版本化变更已获批；TDD 中的变更提案不能替代 SRS 决议。
2. 安全/数据负责人已批准本 CC 实际外发的数据类别、处理目的、Provider 留存/删除政策、容器网络和文件资源边界。测试期间合成数据批准不等于真实 Odoo 文件或业务数据获准外发。
3. 适用于本 CC 的 TDD OPEN 项已裁定，尤其是 Provider 可执行的资源/费用边界与文件特性支持范围。若要求硬预算，必须存在可执行且可核实的上限；本地估算不得冒称硬保证。
4. 代码实施前记录精确 Git、Addon、Python/SDK 和依赖基线。若验收依赖运行服务，须另外证明运行时实际加载代码身份；工作区路径或重启记录不能替代 Loaded Module 证据。
5. 本 CC 独立冻结并获得 Coding Authorization。任何真实 Provider 请求另须有效的模型、请求数、预算、超时/重试、数据范围和操作窗口授权；历史 TV 授权不可复用为持续授权。

未满足门禁时可在后续授权下完成不触发副作用的静态审查或离线契约工作；不得上传文件或声称真实集成通过。

## 3. 范围

### 3.1 范围内

- 提供独立的 Responses API + Code Interpreter Adapter，消费现有 OpenAI Provider 的 API 配置与安全凭据；不得另存、打印或回传 Secret。
- 普通 Chat Completions 入口、消息格式、`content`、`tool_calls`、streaming 和既有使用方保持兼容。
- 接受调用方提供的合成 XLSX 字节（可带输入 SHA-256、请求关联 ID、经批准的指令/计划和资源策略）；Adapter 不判定该版本在 Session 中是否 current，也不持有业务授权。
- 只调用本次独立授权指定的 Provider、模型和 Responses 工具。不得因接口/模型错误静默切换 Provider、模型或编辑方案。
- 通过受支持的 Provider 文件接口下载真实输出文件字节；区分远端文件 ID、下载成功、候选文件基本格式检查和最终业务接受。
- 以显式配置控制 Responses 请求数量、SDK 重试、超时、输入/输出大小及输出 Token 等能力；记录服务端实际返回的请求/响应/工具/容器/文件/Usage 信息（仅在实际可得时）。
- 对请求被本地门禁阻断、连接异常、Provider 拒绝、响应不完整、未返回文件、下载失败、文件损坏、Usage 缺失和远端清理失败提供结构化、脱敏结果。
- 评估并复用现有 Usage 标准化/记录边界；不得由 OpenAI Provider 模块直接依赖 `office_engine_m2`、调用其 ORM 或保存 Prompt、Completion、业务内容或文件字节。

### 3.2 范围外

- Odoo ORM、业务模型查询、ACL/Record Rules 决策或 Data Tool JSON Refresh。
- Workbook Version Service、Session/Proposal 生命周期、版本接受/last-valid 推进、Confirmation Gate 或文件内容语义验证。
- 首轮 Mapping/M1 渲染、对本地工作簿执行模型生成代码、在 Odoo 进程中运行 Code Interpreter 代码。
- Preview、Finalize、Attachment / `mail.message` 发布、Thread UI、浏览器下载及其 HVR。
- 多轮编辑、排序/结构改变等复杂文件能力的产品承诺；这些由后续 CC/集成回归验证。
- Candidate C、其他 Provider/模型、通用 Excel 编辑 DSL、公式重算引擎或业务专用分支。

## 4. Adapter 接口契约（拟议）

### 4.1 输入

Adapter 接收已验证的调用参数，至少包括：

| 字段 | 类型/语义 | 约束 |
|---|---|---|
| `provider_key` | Provider 配置标识 | 只引用既有安全配置，不接受明文密钥 |
| `model` | 字符串 | 必须等于该次批准的模型；不得静默替换 |
| `input_xlsx` | bytes 或内部短期文件句柄 | 必须是调用方提供的实际文件；不得以文本、路径字符串或模型生成代码代替 |
| `input_sha256` | 64 位十六进制字符串 | 有提供时，Adapter 在发出请求前核对输入字节 |
| `instruction` | 字符串 | 调用方传入；Adapter 不自行推断或扩大业务意图 |
| `request_context` | 受限结构 | 仅允许本 CC 定义的关联/计划/授权引用；不得包含 ORM recordset、凭据或多余业务数据 |
| `limits` | 有类型的资源/预算配置 | 由有效授权提供；无可执行硬上限时不得声称已具备硬保证 |
| `correlation_id` | 不透明 ID | 用于关联本次结果，不得代替版本/确认授权 |

实际字段名、类型和 Python 方法签名在编码前由实现审查收敛；不可改变以上安全和语义不变量。

### 4.2 结果

Adapter 返回一个可序列化的内部结果对象，至少表达：

| 项 | 语义 |
|---|---|
| `operation_status` | `candidate_received`、`blocked`、`failed` 或 `indeterminate`；不得直接等同用户任务 `completed` |
| `candidate_bytes` / `candidate_ref` | 成功下载后的真实字节或本地受控短期引用；仅在实际下载成功时存在 |
| `input_sha256` / `candidate_sha256` | 本次输入及下载字节摘要；不代替版本服务或 Validator |
| `provider_response_id` / `request_id` | 仅在 Provider 实际返回时记录；缺失保持未知，不合成 ID |
| `tool_call_ids` / `container_id` / `provider_file_ids` | 最小必要的不透明审计标识，按外部数据/留存政策保存 |
| `usage` | 白名单标准化 token 字段；每项可为已知非负整数或未知；缺失不得改写为 `0` |
| `duration_ms` | 本地测量的请求总耗时 |
| `cleanup_state` | `not_required`、`completed`、`cleanup_pending` 或 `unknown`；资源清理失败不被隐瞒 |
| `error` | 脱敏 `category` 与 `retryable`/`retry_decision`；不含密钥、原始提示词或业务文件内容 |

仅当 Provider 真实返回文件引用、Adapter 成功下载非空字节且最小 XLSX 容器检查通过时，`operation_status` 可为 `candidate_received`。如果该检查失败，返回 `failed`，不伪造候选。`candidate_received` 仍不代表语义验证、授权、版本接受、Preview 或交付成功；最终独立验证归 CB-03。

## 5. 重试、错误与资源策略

| 情况 | Adapter 结果与约束 |
|---|---|
| 本地模型/数据/预算/权限策略不满足 | `blocked`；不得发出 Provider 请求 |
| API 连接异常且没有可信服务端响应证据 | `indeterminate`（报告层可记 `Integration Blocked`）；保留异常类别/耗时；不归因于模型能力，不盲目重发 |
| Provider 返回明确拒绝或错误 | `failed` 并记录脱敏的 Provider 错误类别/响应标识（如有） |
| 收到完成/不完整 Response 但无输出文件 | `failed`；不得以文字答复、代码块或文件名冒充 XLSX |
| Provider 有文件引用但下载失败 | `failed`；保留远端 ID 和可恢复诊断信息（依留存政策） |
| 下载到空字节、损坏或非有效 XLSX 容器 | `failed`；不得升级为候选或交付 |
| Usage 字段缺失/非法 | 保留未知或标记无效 Usage；不能把缺失数值设为 0，也不能因 Usage 缺失篡改文件成功事实 |
| 容器/文件删除失败 | 记录 `cleanup_pending` 和资源 ID（若有）；按政策受控重试清理。若政策要求保证删除而当前能力无法保证，则上传前阻断 |

SDK 隐式重试须关闭或通过可验证配置禁用；测试需证明不会自动追加请求。连接结果不确定时，仅在能证明远端未执行、幂等条件成立且仍在明确请求/预算限额内时，才可由显式调用方发起新的独立请求。每次请求均计入授权上限并留有记录。

Code Interpreter 的 `max_tool_calls` 不得视为硬成本/调用数上限；已有 TV 观察到该参数未能可靠限制实际工具调用次数。记录实际可获得的 Usage、请求数和费用可见性；本地估算不能宣称是账户账单保证。若该次授权要求硬预算，执行前必须确认存在可执行的 Provider/账户级门限，或确认保守最大成本有可证明上界，否则不得调用。

## 6. 安全与兼容不变量

1. 不在 Odoo 进程执行模型返回的 Python、Shell、宏或其他任意代码；Code Interpreter 仅限 Provider 托管隔离环境。
2. 不向托管环境提供 Odoo API 凭据、数据库连接、服务文件路径或非本次授权数据；不得扩大当前用户 ORM 权限。
3. 不使用 `sudo()`、SQL/cursor 或旁路读取业务数据；本 CC 不应读取业务数据。
4. 不把 Adapter 文本或 Provider 工具消息直接作为业务完成反馈；服务端执行事实必须与用户结果分离。
5. Provider 输出是候选；版本/Session/确认/Validator/交付安全门不得被 Adapter 绕过。
6. 普通 Chat Completions 请求、非流式响应、流式响应及其既有消费者结构必须保持向后兼容。
7. 日志限于脱敏且最小必要的关联元数据；不得记录密钥、Authorization/Cookie、完整 Prompt/Completion、XLSX 字节、敏感业务值。

## 7. 预期修改文件边界

以下为提案中的最小候选文件范围，冻结 CC 前需由只读代码审查确认；一旦冻结，范围外修改必须停止并提交变更申请，不得由实施者自行扩展。

| 操作 | 候选路径 | 允许内容 |
|---|---|---|
| 修改（如确有必要） | `mymodules/odoo-llm/llm_openai/models/openai_provider.py` | 仅增加 Responses Adapter 的安全接入/共用客户端能力；保持原 Chat Completions 行为兼容 |
| 新增 | `mymodules/odoo-llm/llm_openai/services/__init__.py` | 暴露本 Addon 内部服务 |
| 新增 | `mymodules/odoo-llm/llm_openai/services/responses_adapter.py` | Responses 请求、文件输入/下载、结构化结果及错误分类；不访问 ORM |
| 修改（仅由调用方审查证明必要时） | `mymodules/odoo-llm/llm_openai/__init__.py` | 导入新增服务包；不改其他 Addon 注册行为 |
| 修改（仅为 Usage 白名单兼容且必要时） | `mymodules/office_engine_m2/models/office_llm_usage.py`、`mymodules/office_engine_m2/services/usage_service.py` | 仅兼容 Responses 的最小 Usage 元数据；不存储提示词/文件内容，不让 Provider 直接调用 ORM |
| 新增 | `mymodules/odoo-llm/llm_openai/tests/test_responses_adapter.py` | SDK Mock、请求/响应、异常、隐式重试和 Chat Completions 兼容测试 |
| 新增 | `mymodules/office_engine_m2/tests/test_responses_usage_compatibility.py` | 仅在 Usage writer 有必要变更时覆盖 ORM 记录、安全和缺失 Usage 语义 |
| 新增（真实合成调用授权后） | `docs/verification/evidence/TV_LLM_OFFICE_EDITING_CB01/` | 合成 XLSX、独立回读脚本、脱敏请求摘要、哈希和清理记录；不得存真实业务文件/密钥 |
| 新增（执行后） | `docs/implementation/IHR-M2-CB-01.md`、`docs/implementation/ATR-M2-CB-01.md` | 实际执行/测试/异常/差异证据；不得在执行前填造 PASS |

不得修改 Odoo 官方 Addon、其他 Provider、`llm_assistant` 消费逻辑、Chat Completions 配置、`office_engine_m2` Mapping/Session/Render/Finalize、冻结 SRS/TDD/计划或其他 CC 文件。若代码调查证明上述候选文件范围不适配，停止并经评审修订本契约。

## 8. 验证矩阵与状态口径

| 层级 | 必须验证 | 允许结论 |
|---|---|---|
| 静态/契约测试 | 输入参数与 SDK 请求形状；批准模型/工具策略；隐式重试关闭；真实附件字节下载接口；Usage 缺失/非法；所有错误分类；Chat Completions content/tool_calls/streaming 消费者兼容；无密钥/Prompt/文件落日志 | `Contract Verified` 仅代表契约和本地替身/Mock 层通过 |
| Provider Adapter 单元测试 | SDK Mock 覆盖真实文件引用/下载字节与输入、空响应、无文件、远端拒绝、超时/连接不确定、下载失败、损坏 XLSX、清理待办；断言无未授权重试、无 ORM/文件版本副作用 | 仅验证 Adapter 逻辑，不证明 Provider、模型或 Project 能力 |
| Odoo/Usage 集成（若修改 Usage） | 当前权限、最小 Usage 字段、未知值语义及普通用户权限；Provider 与 Usage ORM 通过调用方边界解耦 | Odoo 集成仅限实际覆盖模块，不证明 Browser/E2E |
| 真实 Provider 合成文件测试 | 单独有效授权后，使用批准 Provider/模型与合成 XLSX；记录响应/工具/文件 ID、请求计数、耗时、用量和清理；下载真实字节、SHA-256、ZIP/XLSX 独立读取并核对指令指定值及非目标断言 | 对该单次合成文件用例 `Integration Passed`；不得宣称多轮、复杂结构、Odoo Preview/Finalize 或浏览器通过 |
| IHR/ATR | IHR 登记实际基线和范围差异；ATR 逐项列命令、结果、日志/证据路径、失败根因/未验证及准确状态。无运行证据时不得代填 | `Final Accepted` 还需本 CC 全部强制范围证据和负责人接受；不代表其他 CC 或生产发布 |

状态区分：

- **`Contract Verified`**：本 CC 声明的静态/契约与 Mock 行为测试实际通过；不等同真实 Provider、Odoo 集成或端到端通过。
- **`Integration Pending`**：真实 Provider/文件输出/独立回读所需条件尚未获得、尚未执行或证据不完整。
- **`Integration Blocked`**：连接/权限/政策/预算/环境阻止获得有效服务端结果；不推断模型或适配器本身失败。
- **`Integration Failed`**：服务端确实返回结果但适配器、下载、文件有效性或断言实际失败；保留原始脱敏证据。
- **`Final Accepted`**：上游门禁已满足、CC 范围内契约测试通过、真实 Provider 合成 XLSX 返回和下载/独立读取证据通过、适用的 Usage/兼容验证通过、IHR/ATR 完成并由负责人接受。不得用局部模拟、历史 TV 单次结果或 Provider 文本替代缺失证据。

不要求为本 CC 单独重跑已结束的 TV Phase 1；可复用其夹具与断言作为参考。真实 API 调用仍须本 CC 执行授权下的独立逐次/逐轮预算和数据批准。

## 9. IHR/ATR 交付与停止条件

如未来取得执行授权，IHR 至少记录：开始前 Git branch/HEAD/status、基线文件差异、Python/SDK/Addon 指纹、Provider/model 解析方式（无密钥）、权限/数据/费用门禁及本 CC 文件范围。

ATR 至少分别报告契约测试、Odoo/Usage 集成、真实 Provider 合成文件、下载/独立回读和资源清理；列明请求 ID/工具/文件 ID（若实际获得）、输入输出 SHA-256、请求次数、Usage/费用可核实性、错误与恢复结果。不能取得的 ID/账单标记 `UNVERIFIED`，不得生成占位成功证据。测试、API、Runtime 和 UI 证据等级不得混淆。

遇到范围外文件修改、实际数据政策不明、凭据不安全、请求次数/预算不能执行、输出身份/版本不匹配、自动重试无法关闭或必须削弱安全约束时，停止相关工作并保留现场；不跳到 Browser、Finalize、Data Tool 或 Candidate C。

## 10. 人工评审项

1. 确认本 CC 与 TDD V2.0.2 / Implementation Plan V2.0.1 的范围和错误状态契约一致。
2. 确认真实 Provider 调用的前置 SRS 变更、数据/留存政策、模型及费用授权完成路径。
3. 只读检查第 7 节拟议文件清单及 Responses SDK 集成位置；必要时先修订 CC 文件范围，再冻结。
4. 审查 Integration Blocked 与 Integration Failed 的证据门槛，以及 `Final Accepted` 所需的真实文件验证范围。
5. 冻结后如需编码，另行给出明确 Coding Authorization；本稿当前不授权执行。
