<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# CC-M2-005：AI 映射到 M1 文件交付端到端链路

## 0. 文档治理

### 0.1 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-005` |
| Coding Contract | `CC-M2-005` |
| 模块 | `office_engine_m2` |
| 工作类型 | 新功能 / AI、Odoo Retriever 与 Office 引擎集成 |
| 变更类型 | 编排服务、当前用户授权取数、受控 M1 渲染和聊天附件交付 |
| 版本 | `V0.1` |
| 状态 | **Draft — 仅供评审；不授权冻结、实施或改动代码** |
| 目标 | 将当前用户的自然语言导出请求、真实授权 Retriever 数据、受约束 Mapping Proposal、确认卡片、M1 同步渲染/回读及线程附件交付串成可测试闭环，并为每次 Provider 调用记录最小 Usage 元数据。 |
| SRS 基线 | `SRS_office_engine_m2_ai_mapping.md V1.0.0 Frozen` |
| DDD | N/A；依据冻结 M2 TDD |
| TDD 基线 | `TDD_office_engine_m2.md V1.0.0 Frozen` |
| Implementation Plan 基线 | `IMPLEMENTATION_PLAN_office_engine_m2.md V1.0.0 Frozen`，阶段 5 / 拟建 CC-M2-005 |
| 前序 CC | CC-M2-001/002/003/004；CC-M2-004 的关闭处置为 FROZEN WITH OPEN ITEMS，不代表阶段 4 Gate 全部 PASS |
| CC-M2-004 实现基线 | `24d6d4c7a7b28172c156c0b58b46fa1ef78b869d`；ATR/HVR 保留 PARTIAL 状态和未完成场景 |
| 起草日期 | 2026-10-23 |

### 0.2 基线与冻结前门禁

- 本 CC Draft 仅把冻结 SRS/TDD/Plan 的阶段 5工作范围细化为可评审契约；不得将本稿作为实现授权。
- TDD 规定映射调用只使用已准入 OpenAI `gpt-5.6-luna`；M2-005 自动化测试使用 SDK/Provider Mock，不访问外网。人工集成如需真实 Provider，只能使用该模型与合成数据，并须满足 SRS 数据政策；不得发送真实客户数据或未批准的模板内容。
- SRS `OPEN-M2-002/003` 未关闭前，Provider 输入限合成或已书面批准的数据；本 CC 默认所有自动化和 HVR 样本均为合成数据。
- 阶段 5 的代码冻结/实施前，必须完成冻结 Implementation Plan 要求的阶段 3/4 Gate 处置，并在当前运行环境及当前用户权限下验证 M1 `_render_request_sync` 可调用。CC-M2-004 的 `FROZEN WITH OPEN ITEMS` 关闭不等同于 Plan 阶段 Gate PASS。此项是后续 CC 冻结/实施门禁，不阻止当前 Draft 评审。
- 若 M1 spawn 子进程不能在 Odoo 运行环境安全导入 `office_core` / `office_verify`，或当前用户无法通过 M1 持久化链路，必须停止并报告证据；不得绕过隔离在 Odoo Worker 内直接执行，也不得在本 CC 越权修改 M1。
- 本 CC 不改变 Odoo-LLM 工具白名单、Provider 请求契约、SRS/TDD 数据政策、M1 安全/回读/附件边界或 M2 八状态机。

## 1. 变更概述

阶段 5负责将 CC-M2-001 纯 Python 映射校验器、CC-M2-002 Usage 服务、CC-M2-003/004 Mapping Session 与卡片、既有 `odoo_record_retriever`、M1 `office_engine_odoo` 持久请求及 `office_core` / `office_verify` 串联。LLM 只给出不可信 Mapping Proposal；服务端校验、用户确认、实时授权取数后，才编译 M1 Mapping Plan。只有 M1 独立回读 PASS 且安全交付成功，才向线程提供输出附件。

本 CC 首期针对已准入的 `.xlsx` 模板与合成 Odoo 数据；不开放旧版 `.xls/.doc`。`.docx` 只有在冻结 Plan 所要求的 M1 UI HVR 前置证据已经满足并被确认开放后，才可由后续 CC 变更准入；不能由本 CC 测试夹具推定开放。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本 CC 的相关性 |
|---|---|---|
| `FR-M2-001/002` | 请求意图与模板结构收集 | 本 CC 接收现有 Thread/附件和服务端已识别上下文；无法确认的记录/模板信息须澄清。 |
| `FR-M2-003` | 授权数据字典 | 当前用户权限下调用 `odoo_record_retriever`，失败不编造数据。 |
| `FR-M2-004/005` | Proposal、完整性校验与澄清 | 最多一次修复重试；缺失/非法映射 fail-closed，转人工补全。 |
| `FR-M2-006/007` | 卡片展示与人工纠错 | 复用 CC-M2-004 卡片及 RPC；仅接入经校验 Proposal 和用户 edits。 |
| `FR-M2-008` | 明确确认、实时取数与生成交付 | 当前确认 revision 再校验权限、实时取数、调用 M1 并交付安全附件。 |
| `FR-M2-013` | 查询/Provider/渲染失败处理 | 区分澄清、无授权、Provider、M1 验证和交付失败；不得伪装成成功。 |
| `BR-M2-001/002/003/004` | 当前权限、仅使用真实事实、完整性、用户确认 | 映射 Proposal 不能作为记录/权限/输出事实。 |
| `NFR-M2-001/002/003/004/008` | 数据保密、隔离、可信、安全只读、可理解失败 | 本 CC 全链路适用。 |
| `AC-01–05/10–15/18–20` | 请求、授权、完整映射、生成/失败和隔离验收 | 按 CC 测试矩阵映射具体覆盖。 |

### 2.2 DDD

N/A。使用冻结 SRS 与 TDD 的需求/状态定义，不新增领域聚合或业务状态。

### 2.3 TDD 引用

| TDD 条款/ID | 标题 | 本 CC 应用 |
|---|---|---|
| §3.1–3.2 | 模块职责与请求数据流 | 编排服务调用现有服务，不复制 M1 或 Retriever 逻辑。 |
| §4.1–4.4 | Proposal、TargetManifest、M1 Plan 与纯 Python Validator | Proposal 与 M1 Plan 分离；只接受服务端 manifest/allowlist；先完整校验再确认。 |
| §5.1–5.2 | gpt-5.6-luna 与有限修复 | 非流式调用；初调加至多一次修复；失败进入澄清/失败状态。 |
| §6/§7 | 当前用户 Retriever、Provider Usage | 当前 `env`、受限模型/记录/字段；每次 Provider 调用调用 `record_usage()`。 |
| §8.1–8.2 | Session 数据最小化与八状态 | 不持久化 Prompt、模板全文、业务样例或值；仅使用冻结状态迁移。 |
| §9 | 同步执行与事务边界 | Provider/M1 有界同步调用；失败不得留下可下载输出；不增加队列。 |
| §10 | 卡片与 RPC | 复用 CC-M2-004 受控 message type 和 RPC 状态/revision 校验。 |
| §11–12 | 错误分类及安全边界 | 注入、Provider、权限、验证/交付失败均 fail-closed，错误不泄露内部细节。 |
| `T-M2-SEC-001/002/003/004` | Provider、发送数据、Proposal 与 Retriever 授权 | 固定模型、数据政策、服务端白名单和当前用户环境。 |
| `T-M2-MAP-001/002/003` | 映射编译、完整性和重试上限 | 缺项不进入 M1；一轮最多两次 Provider 调用；重试后仍缺项则手工补全。 |
| `T-M2-LLM-001` | Provider Usage | 原 `content/tool_calls` 不变；Usage 计量不泄漏聊天正文。 |
| `T-M2-DATA-002` | 数据最小化 | 不持久化或日志记录 Prompt/Completion、模板内容、样例与业务值。 |

### 2.4 Implementation Plan 引用

`IMPLEMENTATION_PLAN_office_engine_m2.md V1.0.0 Frozen` 阶段 5。其前置包括阶段 1–4 Gate 处置、M1 可调用/ACL 验证和 SRS 数据政策限制；本 Draft 不能解除这些前置条件，也不能把 CC-M2-004 的带未通过项处置改写成阶段 4 PASS。

## 3. 范围冻结

### 3.1 在范围内

- 新增 `office_engine_m2.services.ai_orchestrator`：绑定当前 Thread、消息、`.xlsx` 附件、Mapping Session 与已明确的目标模型/记录；调用现有授权 Retriever，构建最小 Prompt，调用唯一准入模型 `gpt-5.6-luna`，解析并校验 Proposal，必要时最多修复重试一次，再将合法 Proposal/澄清项交给既有卡片服务。
- 每一次 Provider 调用（首调、修复、失败）都调用 CC-M2-002 的 `record_usage()`，关联当前模型和 Thread，记录 attempt、耗时、Usage/status/outcome/error_code/response_id 等获准元数据；不得传入 Prompt、Completion、模板全文或业务字段值。
- 若 `record_usage()` 写入失败，停止本次后续修复调用和渲染，返回受控计量错误；不允许无计量地继续调用 Provider 或 M1。
- 新增 `office_engine_m2.services.render_bridge`：仅接受当前用户明确确认的 Session 和 `confirmed_revision`；再次校验 owner/company/thread/附件/目标记录、revision、字段权限和数据政策；通过当前用户环境实时读取最新数据，编译受限 M1 Mapping Plan。
- M1 桥接调用既有 `office.document.request._render_request_sync(request_uuid, source_attachment_id, mapping_plan, thread_id, input_message_id)`，保留 `office_engine_odoo` 的授权、同步预算、M1 引擎、`office_verify` 和私有附件/消息交付边界；不自行生成可交付附件。
- 另设纯 Python 集成验证直接调用 `office_core.inspect_document()`、`office_core.render_candidate()` 和 `office_verify.verify_output()`：使用有效合成 `.xlsx` bytes 生成候选文件并独立回读，核对目标值、公式及受支持结构；与 Odoo 数据模型/外网隔离。
- 对 TV-M2-001 5/20 负例：Mock 首次 Provider 仅返回 5/20 目标；确定性 Validator 必须识别并报告 15 个缺项，发起至多一次修复。修复返回完整且合法 Proposal 时可展示完整待确认卡片；修复仍不完整/非法时转 `needs_clarification`，不得静默“软件补齐”、确认、调用 M1 或交付文件。
- 用户确认完整映射后进行实时授权重取数；映射来源字段失效或权限撤销时停止并返回澄清/失败。
- M1 与 `office_verify` 均通过后，由既有 M1 服务把私有输出挂载到绑定的聊天 Thread；失败、验证未通过或交付异常时不得出现可下载输出附件。
- 在确认动作与现有卡片状态之间提供受控调用，使卡片明确显示处理中、成功附件、澄清或失败状态；仍由服务端作为状态/revision 权威。
- Odoo TransactionCase/HttpCase、Provider SDK Mock、纯 Python 真引擎集成测试、Playwright 以及内置浏览器 HVR；测试只使用唯一标记合成数据。

### 3.2 超出范围

- 私有/公共 Skill 保存、模板指纹匹配和复用（阶段 6 / CC-M2-006）。
- `.xls`、`.doc`、PDF、图片、PPT，以及未通过 M1 当前格式能力门禁的 Office 对象；不扩展 `.xlsx` 以外的 UI 格式。
- 改写 `office_mapping_verify` 校验契约、M1 `office_core`/`office_verify` 或 `office_engine_odoo`；不修改 `llm_openai`、`llm_assistant`、`llm_thread`、`llm_tool`、其他 Addon 或 Odoo 官方源码。
- 引入 Queue Job、异步任务框架、并行渲染、Provider 自动切换或额外模型。
- 新增 Mapping 编辑器、任意 ORM/domain 查询、自由 Python/表达式、业务模型写入、审批或业务分析。
- 把当前 CC-004 留下的 skipped/blocked 状态用本 CC 的测试结果追溯覆盖。

### 3.3 非目标

- 证明 LLM 对提示词注入具有统计学免疫力；安全判定由 Odoo 权限、Validator 白名单、完整性和 M1 回读确定。
- 以一个合成 `.xlsx` 的通过结果承诺所有工作簿、宏、外部链接或高级对象都无损。
- 以 Mock Provider 结果冒充真实模型或真实 Retriever 证据。

## 4. 变更边界

### 4.1 允许修改文件

所有实现代码限定在 `mymodules/office_engine_m2/`，以及该 CC 的记录文件：

| 路径 | 允许内容 |
|---|---|
| `mymodules/office_engine_m2/services/ai_orchestrator.py` | Provider 请求编排、严格解析/校验、有限修复、Usage 挂钩、状态/卡片调用。 |
| `mymodules/office_engine_m2/services/render_bridge.py` | 确认 revision/授权重验、实时取数、Mapping Plan 编译、调用现有 M1 Odoo 服务。 |
| `mymodules/office_engine_m2/services/mapping_service.py` | 仅扩展既有 Session/卡片服务的受控衔接，不改变 owner/company/revision/validator 契约。 |
| `mymodules/office_engine_m2/controllers/mapping_controller.py` | 仅在现有认证路由中增加启动映射/确认后有界渲染所需的受控调用；不接受客户端 UID/权限声明。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.js` | 卡片状态/成功附件和澄清反馈的最小联动。 |
| `mymodules/office_engine_m2/tests/test_ai_orchestrator.py` | Provider mock、Validator、重试、5/20 和 Usage Odoo 测试。 |
| `mymodules/office_engine_m2/tests/test_render_bridge.py` | 当前用户授权、实时重取数、Mapping Plan、M1 调用和失败无附件测试。 |
| `mymodules/office_engine_m2/tests/test_m2_end_to_end.py` | 合成 Odoo 全链路与 M1 服务交付集成测试。 |
| `mymodules/office_engine_m2/tests/test_office_core_integration.py` | 针对真实 `office_core`/`office_verify` API 的隔离 `.xlsx` 集成测试。 |
| `mymodules/office_engine_m2/tests/__init__.py` | 注册本 CC Odoo 测试。 |
| `mymodules/office_engine_m2/__init__.py` | 注册新增服务所需模块导入（如确有需要）。 |
| `mymodules/office_engine_m2/__manifest__.py` | 仅本 Addon 自有资产/数据声明确有新增需要时修改。 |
| `docs/implementation/CC-M2-005_ai_to_m1_end_to_end.md` | 本 CC 经批准后的版本历史与冻结记录。 |
| `docs/implementation/IHR-M2-005_ai_to_m1_end_to_end.md` | 实施历史。 |
| `docs/implementation/ATR-M2-005.md` | 自动化证据和每项原生测试状态。 |
| `docs/implementation/HVR-M2-005_ai_to_m1_end_to_end.md` | 人工验证记录、基线及截图引用。 |
| `docs/implementation/FR-M2-005_ai_to_m1_end_to_end.md` | 基于证据的关闭评估。 |

其他文件未列入本白名单；发现接口必须扩展到其他 Addon、M1 包或核心 Provider 时，先暂停并提交 TDD/CC 变更评审。

### 4.2 禁止修改

| 类型 | 禁止事项 |
|---|---|
| M1 包和 Odoo 服务 | 不修改 `mymodules/office_core/`、`office_verify/`、`office_engine_odoo/`；只调用它们已存在的接口。 |
| Provider / Odoo-LLM | 不修改 `mymodules/odoo-llm/`；复用 CC-M2-002 的 Usage 标准化，不改变消息 `content/tool_calls`。 |
| Validator | 不放宽 `office_mapping_verify` schema、未知字段/目标拒绝或完整性规则。 |
| 权限 | 不使用 `sudo()`、`env(su=True)`、`with_user()` 或 UID 切换读取 Thread、附件、业务记录或渲染；按 CC-M2-002 既定的 `record_usage()` 内部服务记录 Usage。 |
| 用户数据 | 不写入真实客户/订单数据到日志、测试快照或 Provider；不把 Prompt/Completion/模板全文/样例值持久化。 |
| 交付 | 不直接创建公开附件；不得绕过 M1 校验提前挂载 candidate 或生成成功消息。 |
| 异步/状态 | 不添加队列、Session 状态或状态迁移；使用既有八状态和同步预算。 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | Mapping 卡片只支持服务端测试 context，未接入真实意图、授权 Retriever 和 Provider Proposal。 | 从本 Thread/Session 的受控请求构建最小上下文；只调用已准入模型并把解析后的不可信 Proposal 交给独立 Validator。 | CC-CHANGE-001 |
| 2 | Provider 响应未形成 M2 重试/完整性状态流。 | 初调后严格解析、字段/目标/完整性校验；JSON/schema/缺项可修复时至多再调用一次，记录每次 Usage；仍失败转需澄清。 | CC-CHANGE-002 |
| 3 | 用户确认仅更新映射状态，尚不重新取数或调用 M1。 | 确认当前 revision 后按当前用户权限实时取数、编译 M1 Mapping Plan，调用既有 M1 同步渲染服务。 | CC-CHANGE-003 |
| 4 | M1 单元组件已独立存在，但未证明合法 `.xlsx` 从聊天输入到实际交付附件完整闭环。 | M1 `office_core` 真实生成候选、独立 `office_verify` PASS，再由 M1 Odoo 服务安全交付并挂到原 Thread。 | CC-CHANGE-004 |
| 5 | M1 / Provider / Retriever 错误与结果交付尚未形成单一可信聊天结果。 | 卡片显示服务端真实状态；只有 M1 verify 和交付都成功才显示附件，否则显示受控澄清/错误且无下载附件。 | CC-CHANGE-005 |

## 6. 既有行为保留（回归边界）

| ID | 行为/契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | CC-M2-001 严格解析、目标/字段/类型/完整性校验及未知项拒绝 | 阻止幻觉字段和遗漏流入 M1 | CC-PRESERVE-001 |
| 2 | CC-M2-002 非流式响应的 `content/tool_calls/usage/response_id` 兼容及 Usage ACL | 不得污染通用聊天正文或泄漏计量元数据 | CC-PRESERVE-002 |
| 3 | CC-M2-003/004 Session owner/company 隔离、八状态、revision、RPC 服务端校验和卡片范围 | 防越权、重放和普通聊天消息被卡片接管 | CC-PRESERVE-003 |
| 4 | M1 `office.document.request._render_request_sync` 当前用户权限、同步资源预算、idempotency、验证后附件交付契约 | M2 不得复制/绕过 M1 权限与校验 | CC-PRESERVE-004 |
| 5 | 非 Office 普通消息与既有附件流转、输入框可用性 | Office 功能失败不得破坏普通聊天 | CC-PRESERVE-005 |
| 6 | M1 仅开放已核验 `.xlsx` 能力；`.xls/.doc` 拒绝，`.docx` 受 Plan Gate 控制 | 防止把局部证据扩张为格式承诺 | CC-PRESERVE-006 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| `T-M2-SEC-001` | 适用 | Provider 选择和响应 | Mock 模型绑定测试；拒绝非 `gpt-5.6-luna`。 |
| `T-M2-SEC-002` | 适用 | Prompt 构建和检索入口 | 只用合成/已批准输入；未获准时 Provider 调用次数为 0。 |
| `T-M2-SEC-003` | 适用 | Proposal、模板文字、RPC 全部作为不可信输入 | 非法/注入 Proposal、未知字段/目标拒绝；无 M1 调用。 |
| `T-M2-SEC-004` | 适用 | Retriever 与渲染桥接 | 当前用户环境、绑定模型/记录/字段；跨用户和撤权后拒绝。 |
| `T-M2-MAP-001/002` | 适用 | Proposal → 用户确认 → 服务端 M1 Plan | 字段来源白名单、required 完整性、当前 revision 与 M1 计划测试。 |
| `T-M2-MAP-003` | 适用 | `ai_orchestrator.py` | 首调+最多一次重试；重试后不完整为需澄清；断言 provider 调用 <=2。 |
| `T-M2-LLM-001` | 适用 | 每次调用后 `record_usage()` | 正常/缺失 Usage、修复两次计量、原文未落库。 |
| `T-M2-DATA-002` | 适用 | 日志、消息、Session、Usage | 哨兵 Prompt/Completion/业务值扫描，不得出现原文。 |
| TDD §9 同步预算 | 适用 | Provider 与 M1 调用 | 超时/资源限额失败受控返回，不无限占用 Worker。 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | Draft 设计为否；优先复用既有 Session/M1 Request/Usage 模型 |
| 新模型/字段 | 未经 TDD 批准不得新增；若实现发现必需持久字段则停止并回 TDD |
| 恢复/回滚 | 使用 ORM 事务和 M1 自身 request/附件清理契约；失败候选不得与成功消息关联 |
| 验证 | 测试后查询唯一标记 Session/附件/Request/Usage；按 ORM 清理并确认无残留，禁止直接删 filestore |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| Provider | 只复用 Odoo-LLM 的当前已配置 `gpt-5.6-luna` 非流式标准化响应；不得直接引入第二套 OpenAI SDK 调用路径 |
| Retriever | 只复用已注册的 `odoo_record_retriever` 工具/服务；运行于当前用户 `env`，调用输入必须绑定 Session 的 model/record/allowlist。精确执行入口如与冻结 TDD 不同，先停止核验，不复制其搜索逻辑。 |
| 校验器 | 调用 `office_mapping_verify.parse_mapping_proposal()`、`validate_proposal()` 或既有兼容公开 API；不得复制校验逻辑。 |
| Usage | 每次 Provider 响应均调用 CC-M2-002 `record_usage(env, model, usage, elapsed_ms, attempt_no, outcome, error_code, response_id, thread)`；不得传入 prompt/response 正文。 |
| M1 独立纯 Python | `inspect_document(content, filename, mime_type, budget)`、`render_candidate(content, filename, mime_type, mapping, budget)`、`verify_output(source_bytes, candidate_bytes, filename, mime_type, mapping_plan, policy, budget)`；不接收 Odoo recordset/path。 |
| M1 Odoo 持久服务 | 复用 `env['office.document.request']._render_request_sync(request_uuid, source_attachment_id, mapping_plan, thread_id, input_message_id)`；请求 UUID 由本服务作为调用方稳定生成，重复提交使用同一映射 Session/revision 的幂等键。 |
| UI/RPC | 复用 CC-M2-004 卡片与服务端 context/update/confirm/cancel；新增联动只限本阶段有界生成，不接受身份/权限参数。 |
| 向后兼容 | 普通聊天、原 message body/content/tool_calls、M1 Request API 与卡片的既有安全校验不变。 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 无；沿用 Thread、Session、attachment、业务记录和 Usage 现有 ACL/Record Rules |
| 提权 | 本 CC 不添加 `sudo()`；只通过 CC-M2-002 既定的受限 `record_usage()` 写 Usage |
| 敏感数据 | Provider 只收到当前策略明确允许的最小合成/脱敏映射上下文；Prompt/Completion/业务值不持久化、不进入日志 |
| 模型输出 | Proposal 永远不可信；服务端重建 target manifest/allowed_fields，Retriever 权限检查后才重读值 |
| 模板注入 | 模板文字作为数据输入；即使模型遵循恶意文字，非法字段/目标/指令也不能越过纯 Python Validator 和 M1 Schema |
| 输出附件 | 只接受 M1 `_render_request_sync` 返回的已验证、当前用户可访问的私有交付；失败候选不可下载 |
| 失败文案 | 对用户提供稳定错误/澄清类别，不返回 traceback、Prompt、系统路径、未授权记录存在性或模型原始敏感正文 |

## 11. 测试契约

所有自动化网络调用使用 OpenAI SDK / Provider Mock。测试样本使用合成数据，`.xlsx` 文件由测试夹具确定性生成。用例必须验证真实 M1 Python 引擎调用；不能用 mock 代替 `office_core`/`office_verify` 的真实纯 Python 集成测试。与 Odoo 流程有关的测试在既有 Odoo 18 开发环境/TransactionCase/HttpCase 上执行，不创建隔离数据库。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | 初始映射请求与 Session 绑定 | CC-CHANGE-001；FR-M2-001/002；TDD §6/8 | TransactionCase + Mock | 仅当前 Thread 上传消息/附件可建映射；目标记录由用户明确指定且可读；伪造线程、附件或记录拒绝。 | 否 | 防错绑会话和越权。 |
| CC-TEST-002 | Retriever 授权数据收集 | CC-CHANGE-001；FR-M2-003；`T-M2-SEC-004` | Odoo integration | 在当前 `env` 调真实 Retriever 执行路径，字段仅为 server allowlist；无权/不存在记录、撤权、超时明确失败；不调用 Provider，不伪造数据。 | 否 | 证明真实工具链不靠 mock 通过。 |
| CC-TEST-003 | 初次 Provider Proposal、严格 JSON 与 Usage | CC-CHANGE-001/002；`T-M2-LLM-001` | Provider Mock + TransactionCase | 仅指定模型非流式调用；原始 content 进入严格解析，返回 Proposal；为调用写一条 Usage，不保存 Prompt/Completion；普通聊天正文不含 Usage。 | 否 | 固定 Provider 和计量契约。 |
| CC-TEST-004 | 一次修复与 5/20 缺项处理 | CC-CHANGE-002；FR-M2-004/005；`T-M2-MAP-002/003` | Provider Mock + Validator | 首次 5/20 时 validator 明确报告 15 个缺目标；仅发一次修复。修复完整合法时显示需用户确认卡片；若仍为 5/20/非法，则 `needs_clarification` 并列明缺项，Provider 总调用数=2、M1 调用数=0、无输出附件；绝不由服务端猜值自动补齐。 | 否 | 回归 TV-M2-001 的模型遗漏事实。 |
| CC-TEST-005 | 非法 JSON、未知字段/目标、注入 Proposal | CC-CHANGE-001/002；`T-M2-SEC-003` | Mock + Python/Odoo | 非法 JSON/Markdown/extra key/未知目标/字段/operation/type 均被拒绝；重试上限后澄清或受控失败；无 M1 调用/交付。 | 否 | 确定性安全边界不能依赖模型自觉。 |
| CC-TEST-006 | `record_usage()` 每次调用与错误语义 | CC-CHANGE-002；CC-M2-002；`T-M2-LLM-001` | TransactionCase + Provider Mock | 初调、修复、Provider 错误分别各记录一次；调用序号、耗时、Usage status/outcome 正确；Usage 缺失为 NULL/缺失状态；搜索日志/持久字段无哨兵 prompt、completion、字段样例或 API key。模拟 `record_usage()` 写入失败时，不再发起修复或 M1 调用，并返回受控失败。 | 否 | 计量完整与数据最小化。 |
| CC-TEST-007 | 真实 M1 纯 Python 读写及独立回读 | CC-CHANGE-004；TDD §4/§9 | 独立 Python 集成测试 | 直接调用实际 `office_core.inspect_document`、`render_candidate` 与 `office_verify.verify_output`；合法合成 `.xlsx` 写入命中目标，回读 PASS；公式/样式等夹具中声明要保留的结构按 M1 支持范围验证；M1 spawn/资源失败如实失败，不绕过隔离。 | 否 | 证明真实引擎链路，不以 Mock 伪装。 |
| CC-TEST-008 | 服务端 Mapping Plan 编译与确认绑定 | CC-CHANGE-003；FR-M2-008；`T-M2-MAP-001/002` | TransactionCase | 仅 `confirmed_revision == revision` 的完整映射可编译；字段来源、值类型、target、template hash 来自服务端；旧 revision、必填缺项、越权字段拒绝，M1 调用数=0。 | 否 | 用户确认是必要但非充分条件。 |
| CC-TEST-009 | M1 Odoo 持久渲染与附件交付 | CC-CHANGE-003/004；FR-M2-008 | Odoo integration / HttpCase | 由当前用户 env 调既有 `_render_request_sync`，真实请求状态进入生成；成功时只出现私有输出并关联原 Thread；下载内容回读匹配输入/计划；跨用户不可读。 | 否 | 端到端确认 Odoo 与引擎交付连接。 |
| CC-TEST-010 | 失败无输出及状态/清理边界 | CC-CHANGE-005；FR-M2-013；TDD §9/11 | TransactionCase | Provider/Retriever 超时、权限撤销、M1 错误、verify FAIL、附件交付异常均不得呈现成功/下载卡片；候选清理，错误类别稳定，状态合法。 | 否 | 保证没有半成品泄漏。 |
| CC-TEST-011 | 重复提交和映射 revision 幂等 | CC-PRESERVE-004；TDD M1 request UUID | TransactionCase 并发/重复请求 | 同一 session + confirmed revision 使用同一稳定 request UUID；重复调用返回同一 M1 请求/输出，最多一个有效输出；新 revision 使用新 idempotency key。 | 否 | 防双击/网络重试产生重复文件。 |
| CC-TEST-012 | UI 全链路与真实下载 HVR | CC-CHANGE-005、CC-PRESERVE-005；Plan 阶段 5 | Playwright + 内置浏览器 | 上传有效合成 `.xlsx`，发出意图，展示卡片，确认后看到处理中/最终附件；下载文件并独立检查写入值；错误分支不显示下载，输入框可继续使用；普通消息不被影响。 | 是 | 交付为可见用户功能，必须人工验证。 |

### 11.1 HVR 场景

| 场景 | Given / When | 必须观察到的结果 | 状态初始值 |
|---|---|---|---|
| HVR-SCN-001 成功导出 | 合成有效 `.xlsx`、已授权合成目标记录与合法完整 mapping；在内置浏览器上传并确认 | 映射卡片显示目标/字段，用户确认后出现完成状态和私有下载附件；下载文件目标值正确，公式/结构保持在测试契约范围内，无 JS 错误 | NOT RUN |
| HVR-SCN-002 5/20 澄清 | 专用测试 provider 返回 5/20，修复仍缺项 | 卡片列出未完成项并停在需澄清；没有“生成成功”或下载附件；用户可以手动补充/普通聊天继续 | NOT RUN |
| HVR-SCN-003 渲染/权限失败 | 构造 M1 回读失败或确认后权限撤销的受控测试情景 | 线程显示明确受控失败，无可下载 candidate；Session 不被谎报 completed | NOT RUN |

HVR 逐场景记录真实执行人、日期、代码基线、内置浏览器截图/观察和附件标识。自动化截图不得冒充人工签认。

## 12. 停止条件 / 升级闸门

| 触发条件 | 升级路径 |
|---|---|
| CC-M2-004 阶段 Gate 或 Implementation Plan Baseline validity 未完成正式处置 | 暂停本 CC 冻结/实施；先更新并重新批准计划基线或补齐 Gate 证据。 |
| `odoo_record_retriever` 不能在调用用户当前 env 下精确绑定目标 model/record/authorized fields | 停止；回到 TDD/权限设计，不得用任意 ORM 查询或 sudo 替代。 |
| `gpt-5.6-luna` Provider 路径拿不到规范化响应/Usage，或要修改 `llm_openai` | 停止；核对 CC-M2-002/TDD，不在本 CC 扩大依赖。 |
| Provider 数据政策未批准或需要发送真实业务数据 | 停止外发；只可继续合成测试，等待 SRS OPEN 项处置。 |
| M1 spawn/import、授权、资源预算或回读失败 | 停止交付；保存安全诊断和复现，回到 M1/TV 正确基线，不绕过 Worker 隔离。 |
| 需要修改 M1 包、Odoo-LLM、Provider、状态机或模型字段 | 停止并升级相应 TDD/CC；不得将 CC Draft 当变更授权。 |
| 5/20 缺项在一次修复后仍未闭合 | 停止自动渲染并转需澄清；禁止静默跳过、自动虚构值或直接进入 M1。 |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | CC-CHANGE-001–005 完成且只触及 §4 白名单 | 硬闸门 |
| 2 | Retriever 调用使用当前用户权限，并通过真实 Odoo 集成测试；无 sudo/身份切换 | 硬闸门 |
| 3 | 初调 + 最多一次修复上限、5/20 回归和不完整澄清路径均有 Mock 自动化证据 | 硬闸门 |
| 4 | 每次 Provider 调用调用 `record_usage()`；模型响应内容兼容；Prompt/Completion/业务值不落库/日志 | 硬闸门 |
| 5 | 实际 `office_core` 与 `office_verify` 对 `.xlsx` 候选运行成功并独立回读 PASS | 硬闸门 |
| 6 | M1 Odoo 私有请求路径以当前用户权限生成并交付到原线程；重复请求幂等 | 硬闸门 |
| 7 | 所有失败路径无可下载文件；ACL、状态/revision、资源预算与清理断言通过 | 硬闸门 |
| 8 | Playwright 自动 UI 流程及内置浏览器 HVR 成功场景均有证据；CC-TEST-012 的必要场景完成 | 硬闸门 |
| 9 | IHR、ATR、HVR、FR 完成；适用 Plan Gate 已通过或有正式基线化的授权处置 | 交付闸门 |

CC 冻结并实施需独立审批；Draft 不授权编码。关闭不自动宣告 M2 阶段完成、合并或发布。

## 14. 追溯矩阵

### 14.1 正向：In-Scope 上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| FR-M2-001/002/003 | CC-CHANGE-001 | 收集上下文及当前用户 Retriever。 |
| FR-M2-004/005 | CC-CHANGE-002 | 严格 JSON、有限修复与澄清。 |
| FR-M2-006/007/008 | CC-CHANGE-003/005 | 复用确认卡片、人工确认、实时取数和交付。 |
| FR-M2-013 | CC-CHANGE-005 | Provider/Retriever/M1 失败明确区分。 |
| NFR-M2-001/002/003/004/008 | CC-CHANGE-001–005 | 隐私、隔离、可信、只读及失败反馈。 |
| T-M2-SEC-001–004 / T-M2-MAP-001–003 / T-M2-LLM-001 / T-M2-DATA-002 | CC-CHANGE-001–005 | Provider、权限、完整性、计量和数据最小化。 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001/002 | FR-M2-001–005；TDD §§4–7 | SRS/TDD |
| CC-CHANGE-003/004 | FR-M2-008；T-M2-MAP-001/002；TDD §9 | SRS/TDD/M1 API |
| CC-CHANGE-005 | FR-M2-013；NFR-M2-003/008 | SRS |
| CC-PRESERVE-001/002 | CC-M2-001/002；T-M2-LLM-001/T-M2-DATA-002 | 前序 CC/TDD |
| CC-PRESERVE-003 | CC-M2-003/004；T-M2-SEC-004/T-M2-UI-001 | 前序 CC/TDD |
| CC-PRESERVE-004 | M1 `office_engine_odoo` request API / TDD §4/§9 | M1/TDD |
| CC-PRESERVE-005/006 | SRS §3、CC-M2-004、Implementation Plan 阶段 5 | SRS/前序 CC/Plan |

### 14.3 无 DDD

N/A；追溯链为 `SRS → TDD → Implementation Plan → CC → IHR/ATR/HVR → FR`。

## 附录 A — 实现级决策提案

| CC-DEC ID | 决策提案 | 替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | Provider 首调与修复都经既有 Odoo-LLM `gpt-5.6-luna` 路径；不直接创建平行 SDK client。 | 业务 Addon 自行调用 OpenAI SDK。 | 复用已批准的 Provider 选择、密钥和 Usage 标准化。 |
| CC-DEC-002 | 5/20 缺项由一次 Provider 修复决定是否补全；Validator 只报告差集，不自行生成字段映射。 | 后端根据字段名/标签猜测并填满 15 项。 | 防止语义猜测与幻觉被升级为事实。 |
| CC-DEC-003 | 用 `office_engine_odoo` 的 `_render_request_sync` 作为唯一持久交付入口；纯 Python 引擎直调只用于独立集成测试。 | 在 M2 中自行建立附件、消息或重复 M1 验证。 | 保持 M1 ACL、资源限制、回读和附件身份为唯一交付边界。 |
| CC-DEC-004 | 相同 Session/revision 的 M1 request UUID 稳定生成以支持重复请求幂等；新 revision 使用新键。 | 每次 UI 点击随机生成新 UUID。 | M1 Request 表要求调用方提供 UUID，稳定键能安全处理重复提交。 |

## 附录 B — 评审问题与冻结前决策

1. CC-M2-004 阶段 3/4 Gate 的正式处置及 Plan `Baseline validity` 是否有效，须先记录后方可冻结/实施。
2. 当前 Retriever 的真实调用契约、工具结果字段和用户环境绑定须在 CC 冻结前用代码证据确认；不得仅凭工具名称假定接口。
3. M1 子进程 spawn/import 在 Odoo 服务进程中的真实可调用性及资源预算须有实施级证据。
4. `.docx` 是否达到阶段 5 UI 前置门禁不得由本 CC 推定；未满足时保持关闭，只测 `.xlsx`。

## 附录 C — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-23 | Draft | 基于 M2 SRS/TDD/Implementation Plan 阶段 5 起草 AI→Validator→确认→当前用户 Retriever→M1 回读/交付闭环；带入前序真实 Gate 状态，不授权实施。 |
