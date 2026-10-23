<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# CC-M2-004：Owl 映射卡片与 RPC 服务端校验

## 0. 文档治理

### 0.1 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-004` |
| Coding Contract | `CC-M2-004` |
| 模块 | `office_engine_m2` |
| 工作类型 | 新功能 / Owl UI 与 Odoo RPC 安全校验 |
| 变更类型 | 在现有 Addon 中增加专用消息卡片、映射修改 RPC 和服务端验证 |
| 版本 | V1.0.0 |
| 状态 | **FROZEN V1.0.0 — 负责人于 2026-10-23 批准冻结并实施** |
| 目标 | 在 Odoo-LLM 聊天流中仅为受控 M2 映射消息展示 Owl 卡片；业务用户可修改映射并提交，经当前用户上下文和 `office_mapping_verify` 重新验证后保存，且确认操作绑定到当前 Session revision。 |
| 背景 | CC-M2-003 已建立 Mapping Session、owner/company 隔离与 revision；本阶段将其用于正式映射卡片和编辑 RPC。 |
| SRS 基线 | `SRS_office_engine_m2_ai_mapping.md` V1.0.0 Frozen |
| DDD | N/A；依据 M2 TDD V1.0.0 |
| TDD 基线 | `TDD_office_engine_m2.md` V1.0.0 Frozen |
| Implementation Plan 基线 | `IMPLEMENTATION_PLAN_office_engine_m2.md` V1.0.0 Frozen，阶段 4 / CC-M2-004 |
| 前序 CC | `CC-M2-001`、`CC-M2-002`、`CC-M2-003` 已关闭；CC-M2-003 FR/IHR/ATR 已推送至 `origin/main` |
| 起草日期 | 2026-10-23 |
| DDD 判定 | N/A；无独立领域模型，沿用冻结 M2 TDD 判定 |

### 0.2 基线与阶段门禁

- 本 CC 仅引用冻结 SRS/TDD/Implementation Plan，不改变业务语义、Mapping Proposal 契约、八状态集合、权限模型或 Provider 准入。
- CC-M2-003 的代码基线为 `1e33a25148f29ef7de6dfa25de8a9be973384b8b`；其关闭文档提交为 `edb5501`。前序源代码和关闭证据已推送。
- Implementation Plan 阶段 3 Gate 列明的 XML-RPC 安装/升级记录在 CC-M2-003 ATR 中缺失。负责人于 2026-10-23 明确批准本 CC 冻结并实施；该批准仅授权本 CC 继续，不把阶段 3 证据缺口改写为 PASS，也不表示 Implementation Plan 阶段 Gate 已通过。该缺口保留在附录 B 和 ATR 中。
- 本文中业务映射数据仅可经 `office_mapping_verify.validate_user_revision()` 校验；客户端 payload 不是权限或字段白名单来源。
- 此 CC 完成不意味着 M2 AI 生成或 M1 文件生成链路已经接通；AI→卡片供数及 M1 渲染端到端属于 CC-M2-005。

### 0.3 负责人冻结裁定

| 项目 | 本稿提案 | 依据 / 冻结前条件 |
|---|---|---|
| 映射规则与确认字段 | 新增 `mapping_rules_json`（Text）、`confirmed_revision`（Integer）和 `context_json`（Text）；普通 `write()` 一律拒绝，只有服务端内部方法可写。有效映射更新递增 `revision` 并清除旧确认。 | 负责人裁定；符合 TDD §8.1 最小映射规则持久化和 §8.2 revision。 |
| 未授权请求响应 | 每个 RPC 端点用当前 `request.env` 校验 Session owner/company；不匹配抛 Odoo `AccessError`。JSON-RPC 的 HTTP 状态码不作为安全判据，HttpCase 检查 Odoo 错误类型。 | 负责人裁定；防止通过 HTTP 状态码差异泄露 Session。 |
| TargetManifest / allowed_fields 来源 | 仅由后端内部服务写入 `context_json`，context RPC 读取；客户端不得提供或改写该授权上下文。首期使用服务端合成上下文验证卡片。 | 负责人裁定；真实 AI/Retriever 上下文由后续 CC 接入。 |
| 卡片数据 | `mail.message.body_json` 只存消息类型、Session ID 和 revision；候选字段/目标定义从授权 context RPC 获取，不把业务样例或 Prompt 持久化。 | 负责人裁定；遵循 TDD `T-M2-DATA-002`。 |

以上裁定已作为负责人决策纳入本 CC 的 Frozen 基线。若后续实现与冻结 TDD 的准确字段、HTTP 错误类型或会话存储契约冲突，必须暂停并升级至 TDD/Plan，不得以本 CC 的行政关闭处置扩大授权。

## 1. 变更概述

CC-M2-004 实现阶段 4 的专用映射卡片、用户字段选择与保存、确认/取消入口，以及 JSON-RPC 服务端授权、完整性、状态和 revision 校验。卡片使用服务端提供的映射上下文；浏览器仅负责显示和提交用户修改。

本 CC 不调用 LLM、不生成 Mapping Proposal、不执行 Retriever 取数编排、不调用 M1 渲染，也不交付下载文件。测试使用 Odoo 受控 fixture 和 Mock/测试上下文，不将这些证据表述为 M2 端到端完成。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本 CC 的相关性 |
|---|---|---|
| `FR-M2-006` | 映射卡片确认与纠错 | 在范围内：显示目标/字段候选，用户可修正、确认或取消。 |
| `FR-M2-007` | 用户修改映射 | 在范围内：修改仅限合法字段/目标，服务端重新校验。 |
| `FR-M2-008` | 确认映射并进入生成流程 | 部分：确认绑定当前映射 revision；实际取数与 M1 生成由 CC-M2-005 完成。 |
| `FR-M2-013` | 查询与 Provider 失败处理 | 部分：以稳定错误结果呈现 RPC/权限/版本失败；不实现 Provider 调用。 |
| `BR-M2-003/004` | 映射服务端校验及明确确认 | 在范围内：客户端不得使未校验映射成为可执行确认。 |
| `NFR-M2-002/003/008` | 权限隔离、结果可信、状态可理解 | 在范围内：消息作用域、拒绝路径、卡片状态与输入恢复。 |
| `AC-07/08/09` | 卡片呈现、非法修改拒绝、合法修改确认 | 在范围内，按 §11 自动化及人工测试。 |
| `AC-16/20` | 用户/公司隔离 | 在范围内：跨用户/公司 Session 访问拒绝。 |

### 2.2 DDD

N/A。采用冻结 M2 TDD 对 DDD 适用性的判定；不创建领域编号。

### 2.3 TDD 引用

| TDD ID / 条款 | 标题 | 本 CC 应用 |
|---|---|---|
| §4.2–4.4 | Mapping Proposal、TargetManifest 与纯 Python 校验器 | `validate_user_revision()` 只接收服务端当前 proposal、manifest、授权字段集和客户端 edits；校验器失败不得写入。 |
| §8.1–8.2 | Mapping Session 数据最小化、状态/revision | Session 只保留映射规则和必要版本状态，不存样例/实际值；严格沿用八状态。 |
| §9 | 同步生命周期与并发 | RPC 以 expected revision 乐观并发校验；不等待 LLM 或 M1。 |
| §10.1–10.3 | Owl 卡片与 RPC 服务端验证 | 直接从 `@web/core/network/rpc` 导入 `rpc`；经 `Message.components` 注册；每个动作校验当前身份、Session、company、状态、revision 和 allowlist。 |
| §12 | 错误类别与用户反馈 | 使用稳定错误类别，不向用户泄露 traceback、无权资源存在性或内部细节。 |
| `T-M2-SEC-003` | 不可信 Proposal/前端输入校验 | 所有端点参数、用户 edits、message payload 均须服务器校验。 |
| `T-M2-SEC-004` | 当前用户环境与无提权 | 所有 Session/关联对象检查使用 `request.env` 当前用户；无 `sudo()`/su/UID 切换。 |
| `T-M2-MAP-002` | 完整性 fail-closed | 必填目标未闭合或澄清未解决时，不接受确认。 |
| `T-M2-UI-001` | Owl 与 RPC revision 安全 | 采用 TDD 所列 Owl 扩展与服务端 revision 校验。 |
| `T-M2-DATA-002` | 数据最小化 | 样例不得持久化到聊天消息、日志或 Session。 |
| `T-M2-BASE-001` | 设计基线一致性 | 状态、schema 或 HTTP/RPC 语义不足时停止并上游升级。 |

### 2.4 Implementation Plan 引用

`IMPLEMENTATION_PLAN_office_engine_m2.md` V1.0.0 Frozen，阶段 4“ Odoo Owl 映射卡片与 RPC 服务端校验”。Plan 要求真实产品卡片、编辑/澄清/确认/取消、权限及 revision 负向测试、Playwright 和 Codex 内置浏览器 HVR。阶段 3 XML-RPC 子门禁须按 §0.2 先行处置；本 CC Draft 本身不授权实施。

## 3. 范围冻结

### 3.1 在范围内

- 在现有 `office_engine_m2` Addon 的 backend bundle 中加入 `OfficeMappingCard` Owl/QWeb 组件。
- 使用已批准的 `Message.components` 注册机制，仅对服务端生成的专用 mapping message type 呈现；普通消息保持原样。
- 卡片显示服务器识别的模板目标（只读）、当前映射字段、候选字段下拉选择（`<select>`）、字段类型/校验状态及服务器返回的预览样例。
- 支持“保存修改”“确认映射”“取消”按钮及待确认、需澄清、修改中、错误/完成等可理解 UI 状态；确认按钮只确认当前 revision，不在本 CC 启动 M1 渲染。
- 由卡片使用显式导入的 `rpc` 调用后端 context/update/confirm/cancel 路由；拒绝 `useService("rpc")`。
- 后端用 `request.env` 读取 Session 和上下文，校验 owner/company、thread/消息/附件关联、目标记录访问权、状态、expected revision 及服务端字段/目标白名单。
- 更新请求调用 `office_mapping_verify.validate_user_revision()`；拒绝额外键、未知/无权字段、未知目标、类型不兼容、重复元素或非法状态，且拒绝时不改变映射、revision、状态或确认标记。
- 合法的部分映射可以保存为需澄清状态；缺少必填目标本身不是授权错误，但在目标清单闭合前不得确认。未授权字段/目标不得作为部分映射保存。
- 映射规则以 CC 冻结后的 Session 字段契约保存；不保存业务实际值、字段样例、模板原文、Prompt、LLM 内容或附件 bytes。
- 保存成功后以响应返回服务端权威 state/revision，并更新 UI；revision 冲突提示用户刷新，不能静默覆盖。
- 确认操作必须重新验证完整性、权限和 expected revision，并将确认绑定到被确认映射的当前 revision；修改后确认标记失效。取消走受控状态服务进入 `cancelled`。
- 通过 Odoo HttpCase/HTTP 测试及 Playwright 验证跨用户拒绝、过期 revision 和完整编辑保存交互；提供 UI HVR。

### 3.2 超出范围

- LLM Provider 调用、AI 生成 Proposal、JSON 修复重试或 Usage 计量改造。
- 真实 `odoo_record_retriever` 调用编排、安全字段基线配置或外发数据政策的建立；仅使用当前服务端 context provider 给出的授权字段集。
- M1 `office_core` 渲染、`office_verify` 回读、输出附件创建/下载和完整导出闭环；由 CC-M2-005 完成。
- Skill 保存、匹配、修改、停用及自动复用。
- 修改 `mymodules/odoo-llm/`、其他 Addon、Odoo 官方源码或 `llm_thread` 核心文件。
- 任意模型/域查询、任意工具调用、客户端自定义 TargetManifest/allowed_fields 或自由 HTML。
- 在浏览器本地把卡片编辑标成“已授权/已校验”；前端状态不是权限或确认事实。

### 3.3 非目标

- 本 CC 不证明模型输出可靠、映射内容完整或 M1 生成成功。
- 本 CC 不引入异步队列、刷新恢复以外的复杂协作、分页、并发协同编辑或多标签自动合并。
- 本 CC 不保存映射样例或任何业务数据快照。

## 4. 变更边界

### 4.1 允许修改文件

本 CC 所有代码必须且只能位于 `mymodules/office_engine_m2/`。下表构成本次 Draft 文件白名单；冻结时按最终实际 API/测试路径收紧或确认：

| 路径 | 允许内容 |
|---|---|
| `mymodules/office_engine_m2/__manifest__.py` | 将本 Addon 自有 JS/XML/SCSS 注册至 `web.assets_backend`。 |
| `mymodules/office_engine_m2/controllers/__init__.py` | 注册本 Addon Controller。 |
| `mymodules/office_engine_m2/controllers/mapping_controller.py` | Authenticated JSON-RPC context/update/confirm/cancel 路由；只允许本 CC 路由。 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 增加 `mapping_rules_json`、`confirmed_revision`、`context_json` 和受控更新/确认支持；不得开放直接 ORM/RPC 写入。 |
| `mymodules/office_engine_m2/services/mapping_service.py` | 加入卡片上下文、映射更新、确认与取消的授权/校验流程。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.js` | Owl 组件；`rpc` 必须从 `@web/core/network/rpc` 导入。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.xml` | 卡片 QWeb 模板与 `Message.components` 注册扩展。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.scss` | 卡片的最小布局/状态样式（如有必要）。 |
| `mymodules/office_engine_m2/tests/test_mapping_rpc.py` | TransactionCase/HttpCase：RPC 权限、白名单、revision、状态与数据隔离。 |
| `mymodules/office_engine_m2/tests/__init__.py` | 注册本 CC 后端测试。 |
| `mymodules/office_engine_m2/static/tests/**` | Owl/前端组件测试，仅测试本 CC 卡片。 |
| `docs/implementation/CC-M2-004_owl_mapping_card.md` | 经批准后的冻结契约及实际版本历史。 |
| `docs/implementation/IHR-M2-004_owl_mapping_card.md` | 实施记录。 |
| `docs/implementation/ATR-M2-004.md` | 自动化验证记录。 |
| `docs/implementation/HVR-M2-004_owl_mapping_card.md` | 人工浏览器验证记录与截图引用。 |
| `docs/implementation/FR-M2-004_owl_mapping_card.md` | 负责人授权关闭后生成的关闭评估。 |

测试支持文件只允许在 `office_engine_m2/tests/` 或该 Addon 的 `static/tests/` 下新增。任何新增目录/文件必须能追溯至上表的允许类型。

### 4.2 禁止修改

| 类型 | 禁止事项 |
|---|---|
| 上游模块 | 不得修改 `mymodules/odoo-llm/`、`llm_thread`、Odoo 官方代码或其他 Addon。 |
| 模型与权限 | 不得更改 owner/company Record Rule、CC-M2-002 Usage ACL/模型，或扩展管理员的业务数据权限。 |
| 提权 | 不得对 Session、thread、mail.message、ir.attachment、业务记录使用 `sudo()`、`env(su=True)`、`with_user()` 或 UID 切换。 |
| 前端 RPC | 禁止 `useService("rpc")`；禁止客户端传 owner/uid/company/权限结论/TargetManifest/allowed_fields。 |
| 消息判定 | 禁止通过模型输出 HTML、自由文本 marker 或用户可伪造正文触发组件；只能用服务器定义的专用类型/受控 payload。 |
| 敏感数据 | 禁止保存 Prompt、字段样例明文、业务实际值、模板全文、文件 bytes、LLM 原始输出；禁止把这些内容写入日志或持久聊天 JSON。 |
| 功能扩张 | 禁止在本 CC 实现 AI 调用、Retriever/Provider 编排、M1 渲染、输出附件、Skill 或异步任务。 |
| 依赖 | 不新增 pip/npm 依赖；使用 Odoo 已有 Owl、QWeb、RPC 和测试能力。 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 聊天流中没有受控 M2 mapping card。 | 服务端专用类型消息只在对应消息位置渲染映射卡片；普通消息、附件和工具消息不被影响。 | CC-CHANGE-001 |
| 2 | 用户无专用方式查看映射目标和合法 Odoo 字段候选。 | 卡片显示只读目标、映射字段下拉、候选字段的服务器标签/类型及获准样例；样例仅按当前权限实时返回，不持久化到 `mail.message`。 | CC-CHANGE-002 |
| 3 | 前端编辑尚无可靠持久化边界。 | 保存请求只携带 Session ID、expected revision 和 edits；服务端重新构造授权上下文，调用 `validate_user_revision()`，只保存安全映射规则并递增 revision。 | CC-CHANGE-003 |
| 4 | 服务端不能保证 RPC 调用者属于 Session owner/company。 | Controller 由认证用户环境读取 Session；跨用户/公司访问统一拒绝且不泄露记录是否存在。 | CC-CHANGE-004 |
| 5 | 确认、取消和旧 revision 处理尚未接入卡片。 | 确认只绑定当前已校验 revision，取消使用受控状态机；旧 revision、错误状态或不完整映射拒绝且不改变状态。确认不触发 M1。 | CC-CHANGE-005 |
| 6 | 卡片/RPC 错误反馈与后续输入恢复尚未验证。 | 错误以稳定、非敏感的 UI 状态展示；RPC 失败后按钮/选择器解除等待态，用户可以继续编辑/发送普通聊天消息。 | CC-CHANGE-006 |

## 6. 映射卡片与 RPC 契约

### 6.1 专用消息与卡片数据

- 只接受服务器端生成的专用 mapping message type；具体 type 常量在 CC 实施中固定，不能由模型/用户正文设定。
- 持久化消息只携带卡片类型、`session_id`、`revision` 和最少 UI 状态引用；不得在 `mail.message.body_json` 保存业务样例、候选字段值或完整 Mapping Proposal。
- Owl 卡片 mount 后经认证 RPC 获取当前显示上下文。响应由后端按当前用户实时构造，至少包含：模板目标（稳定 `element_id` 与安全 label，只读）、当前映射字段、合法字段候选（field ID、label、允许类型）、所需样例/说明及服务端状态/revision。
- 客户端显示的数据只用于交互；更新请求不得回传候选清单、样例、当前授权集合或权限声明。服务器重新计算/读取这些权威数据。
- 文本采用安全转义，不使用 `t-raw` 展示模型或模板内容；不将模板指令解释为 UI/服务器命令。

### 6.2 RPC 路由

按冻结 TDD 的 authenticated JSON-RPC 路径命名；本稿建议：

| 路由 | 请求最小字段 | 服务器行为 |
|---|---|---|
| `/office_engine_m2/mapping/context` | `session_id`、`expected_revision` | 当前用户读取 Session，校验 owner/company/thread/source message/attachment/target；返回安全卡片上下文。 |
| `/office_engine_m2/mapping/update` | `session_id`、`expected_revision`、`edits` | 校验类型/长度/键集合，重新读取当前 proposal、manifest 与 allowlist，调用 validator；合法可保存的映射更新 revision 并使旧确认失效。 |
| `/office_engine_m2/mapping/confirm` | `session_id`、`expected_revision` | 重新校验 owner/company、状态、revision、TargetManifest 完整性及字段权限；服务端确认当前映射版本。此阶段不取最终业务数据、不调用 M1。 |
| `/office_engine_m2/mapping/cancel` | `session_id`、`expected_revision` | 当前用户对 Session 进行受控取消；仅允许冻结状态机允许的 `cancelled` 转换。 |

除表列参数外的键一律拒绝。每个 endpoint 使用 Odoo 当前 authenticated `request.env`；不能接受客户端 `uid`、owner/company、任意模型/记录 ID、状态目标、允许字段集合、必填标志、模板哈希或确认结果。`expected_revision` 必须是严格整数（拒绝 Boolean、字符串、负数/零）。

### 6.3 服务端更新与状态语义

1. 先以当前用户访问 Session，核对公司和关联 Thread/source message/source attachment/target record；无权对象以不泄露存在性的受控拒绝响应。
2. 校验 Session 当前状态只能处于 TDD 允许修改映射的状态；不接受失败、取消、完成或渲染中 Session 的修改。
3. 在后端锁定 Session/校验 `expected_revision`，防止两个请求同时覆盖。
4. 后端自行取得当前 revision 对应 Proposal、目标 manifest、获准字段集合与字段类型；不得接受客户端提供这些校验基准。
5. 调用 `office_mapping_verify.validate_user_revision(revision, edits, target_manifest, allowed_fields)`。未知字段/目标、非法结构/类型、重复 target 等安全/结构错误必须拒绝、不写库；可识别但尚缺必填目标的有效部分结果可以保存为需澄清状态。
6. 成功保存时只持久化 schema 允许的映射关系/澄清状态，不持久化样例或业务值；更新 revision 并清除旧确认标记。返回纯 allowlist 状态、错误代码和新 revision。
7. 映射完整且无未答澄清时，用户点击确认后后端再次验证同一 revision；确认只可记录对该版本的明确确认并返回已确认 revision，不触发生成。任何后续编辑都使确认失效。CC-M2-005 才可消费该确认并连接实时取数/M1。
8. 用户取消时经 `mapping_service` 调用受控状态转换，不直接 `write()` state。

对并发竞态若不能在本 Addon ORM 服务内确保“同一 expected revision 最多一次更新生效”，停止并回到 TDD，不得用仅前端禁用按钮兜底。

### 6.4 错误与 UI 状态

| 错误类别 | 客户端表现 | 持久副作用 |
|---|---|---|
| `MAPPING_REVISION_STALE` | 提示刷新/重新载入卡片；不覆盖当前显示内容 | 无映射/状态/确认变化 |
| `MAPPING_SOURCE_UNKNOWN` / `MAPPING_TARGET_UNKNOWN` | 行级拒绝或重新选择合法项 | 无非法映射写入 |
| `MAPPING_INCOMPLETE` | 标记待澄清目标；允许补齐，不可确认 | 仅合法部分映射可存；state 为 TDD 允许的需澄清状态 |
| `ACCESS_DENIED` / 不可用 Session | 显示通用无权限/不可用信息，不透露资源存在性 | 无变化 |
| `INVALID_REQUEST` | 显示请求无效；清除 RPC loading | 无变化 |
| 网络/服务器错误 | 可见通用失败信息，恢复选择器和按钮，允许继续普通聊天 | 不把当前卡片标成已保存/已确认 |

## 7. 既有行为保留

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | 普通聊天消息、附件卡片和工具消息按原 `mail.Message` 渲染。 | 本 CC 只匹配专用 mapping message type。 | CC-PRESERVE-001 |
| 2 | Session owner/company、source binding、八状态及受控 transition 保持 CC-M2-003 行为。 | 跨用户/公司隔离为上游既有安全边界。 | CC-PRESERVE-002 |
| 3 | `office_mapping_verify` 保持纯 Python 契约，RPC 使用其公开 validator；不修改 schema 以放宽拒绝。 | CC-M2-001 已冻结/关闭。 | CC-PRESERVE-003 |
| 4 | `office.llm.usage`、Provider 响应与 `mail.message.body_json` 既有 Usage 隔离不变。 | CC-M2-002 已关闭；不将新的 UI 字段混入聊天正文/Usage。 | CC-PRESERVE-004 |
| 5 | M1 附件准入与 Office 拦截行为不变。 | UI/RPC 不扩大 M1 格式范围。 | CC-PRESERVE-005 |

## 8. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| `T-M2-SEC-003` | 适用 | 所有 RPC 请求、消息类型、mapping edits 服务端校验 | CC-TEST-001–009 |
| `T-M2-SEC-004` | 适用 | 当前 request.env、无提权访问 Session/关联对象 | CC-TEST-004/005/008；静态检查 |
| `T-M2-MAP-002` | 适用 | 不完整 TargetManifest/未答澄清不可确认 | CC-TEST-003/006/007 |
| `T-M2-UI-001` | 适用 | 直接 `rpc` import、Message.components、旧 revision 服务端拒绝 | CC-TEST-001/002/005/009/010 |
| `T-M2-DATA-002` | 适用 | 消息/日志/Session 不存样例或业务值 | CC-TEST-008/010 |
| `T-M2-BASE-001` | 适用 | 修改冻结 schema/状态/RPC 契约前停止升级 | CC-TEST-009/§12 |

## 9. 数据与迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 是；新增 `mapping_rules_json` Text、`confirmed_revision` Integer、`context_json` Text。 |
| 迁移脚本 | N/A；使用 Odoo ORM 模块升级。 |
| 数据源 | 服务端生成并经 `office_mapping_verify` 校验的 Mapping Proposal；客户端仅提交 edits。 |
| 目标 | 当前 Session 的最小映射关系、当前 `revision` 和按 revision 绑定的确认标记。 |
| 恢复 / 回滚策略 | 测试数据由 TransactionCase 回滚/HttpCase 唯一标记 ORM 清理；禁止手动数据库/filestore 删除。开发升级失败时向前修复，不删除既有 Session 或 Usage 数据。 |
| 验证 | 既有 `odoo18ce` 的模块升级、字段/索引核验、RPC 事务回滚/拒绝无写入、无样例持久化检查。 |

## 10. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 新增 `/office_engine_m2/mapping/context`、`/update`、`/confirm`、`/cancel` authenticated JSON-RPC (`type="json"`) 路由。 |
| 向后兼容 | 是；普通聊天消息和现有 Thread 组件行为不变。 |
| Adapter 变更 | 新增 backend message component，不改 `llm_thread` 源码；由 `Message.components` 扩展点注册。 |
| 前端 RPC | `import { rpc } from "@web/core/network/rpc"`；禁止 `useService("rpc")`。 |
| 新公开数据面 | 仅本 Addon 的认证用户映射路由；不公开给 portal/public，不暴露原始业务样例持久接口。 |

## 11. 测试契约

测试使用项目 `venv`、批准的 `odoo.conf`、既有 `odoo18ce`；不创建隔离数据库，不安装依赖，不调用真实 LLM/外网。浏览器路径须使用项目要求的 Codex 内置浏览器完成 HVR；Playwright 可用于自动化关键 journey。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | 专用消息卡片渲染 | `CC-CHANGE-001`、`T-M2-UI-001` | Owl/QUnit/浏览器 | 专用 mapping type 显示 `<select>` 卡片；普通文本、附件、工具消息均不实例化卡片；无 JS console error。 | 是 | 验证 Message.components 条件隔离。 |
| CC-TEST-002 | 真实编辑保存 RPC | `CC-CHANGE-002/003`、SRS AC-07/09 | Playwright + Odoo HttpCase | 在真实聊天页面打开测试卡片，选择一个 server-provided 合法字段，点击保存；后端捕获 RPC，Session 映射及 revision 更新；返回 UI 展示服务器新状态。 | 是 | 覆盖实际选择、提交、服务端持久化的完整阶段 4 路径。 |
| CC-TEST-003 | 未知/无权字段、目标和非法 edits | `T-M2-SEC-003`、SRS AC-08 | validator/Odoo 测试 | `validate_user_revision()` 拒绝未授权 source field、未知 element、重复 target、额外键、错误类型；Session mapping、state、revision 和确认标记保持不变。 | 否 | 客户端 payload 完全不可信。 |
| CC-TEST-004 | Session owner/company/关联授权 | `T-M2-SEC-004`、SRS AC-16/20 | HttpCase/TransactionCase | 用户 B 通过正常 RPC 读取或更新用户 A Session 被拒绝（HTTP 403，或 Odoo JSON-RPC AccessError 的等价拒绝响应）；不泄露 Session 是否存在；记录无任何修改。 | 否 | 验证 Record Rule 与 HTTP 入口组合，不使用 sudo 模拟。 |
| CC-TEST-005 | 过期 revision | `CC-CHANGE-003/005`、TDD §9/§10 | HttpCase/TransactionCase | 先以 revision r 保存一次，再以 r 提交旧请求，服务端返回 `MAPPING_REVISION_STALE`；数据库只保留第一笔更新，第二笔不修改任何内容。 | 否 | 确保并发/重复请求不静默覆盖。 |
| CC-TEST-006 | 不完整目标与需澄清卡片 | `T-M2-MAP-002`、SRS AC-06/07 | Owl + service tests | 合法但缺必填项的 proposal 可显示需澄清并允许补齐；确认请求拒绝，Session 不进入 rendering，M1 调用计数为 0。 | 是 | 缺项不是“部分成功”或可绕过门禁。 |
| CC-TEST-007 | 确认、取消和旧确认失效 | `CC-CHANGE-005`、TDD §8.2/10.3 | TransactionCase/HttpCase | 确认绑定当前 revision；映射更新后旧确认标记清除；旧 revision 确认被拒绝；取消只通过受控服务进入 cancelled；失败/取消/完成 Session 不能被改写。 | 否 | 防止重放与状态绕行。 |
| CC-TEST-008 | 样例/业务值不持久化 | `CC-CHANGE-002/003`、`T-M2-DATA-002` | Odoo serialization/ORM 测试 | 持久 `mail.message` payload、Session 字段和日志中不存在样例值、Prompt、模板内容或完整 proposal 的业务值；RPC context 仅在当前授权响应中提供样例。 | 否 | 避免聊天历史扩大敏感值留存。 |
| CC-TEST-009 | RPC 异常后交互恢复 | `CC-CHANGE-006`、SRS NFR-M2-008 | Owl/QUnit + Playwright | stale/access/network error 显示受控状态；loading 清除、选择器可重新操作、可继续发送普通文本消息；不显示红色错误后卡死输入。 | 是 | UI 错误不能破坏 Thread。 |
| CC-TEST-010 | 资产加载与真实人工 HVR | `CC-CHANGE-001`、Plan 阶段 4 | 模块升级 + 内置浏览器 | manifest 资产加载无 JS/XML 错误；实际聊天流截图证明映射卡片、下拉选择、保存反馈可见；HVR 记录当前代码基线与证据图。 | 是 | Spike 不代替产品级 UI 验收。 |

### 11.1 HVR 场景

| 场景 | Given / When | 必须观察到的结果 | 状态初始值 |
|---|---|---|---|
| HVR-SCN-001 专用卡片 | 已有带专用 mapping type 的服务端测试消息；打开目标 `llm.thread` | 仅该消息位置出现映射卡片和 `<select>`；普通聊天消息照常显示；无 JS 错误 | NOT RUN |
| HVR-SCN-002 真实编辑保存 | 在卡片选择另一条后端候选字段并点击“保存修改” | UI 显示已保存/新 revision；刷新后从服务端重新读取仍显示保存后的选择 | NOT RUN |
| HVR-SCN-003 确认/取消与澄清 | 对完整与不完整测试卡片分别确认/取消/补项 | 完整当前 revision 反馈已确认；不完整卡片不能确认；取消进入已取消反馈；本 CC 不显示文件生成成功 | NOT RUN |
| HVR-SCN-004 错误恢复 | 提交旧 revision 或模拟服务端拒绝，随后发送普通聊天文本 | 显示受控错误；输入框仍可用，第二条普通消息正常进入消息流 | NOT RUN |

HVR 使用 Codex 内置浏览器；保存截图、线程/消息标识（脱敏）、浏览器观察、测试/实现 commit hash。不得声称人工通过，直到真实浏览器观察完成。

### 11.2 执行记录要求

- ATR 记录命令、Odoo/Python/PostgreSQL/浏览器版本、HttpCase/Owl/Playwright 结果、跨用户拒绝的真实协议响应、旧 revision 数据库前后值和清理证据。
- HVR 逐个记录场景原生状态、执行人、日期、真实截图路径及代码基线；自动化截图不能冒充人工观察。
- 对每个验证项另外填写工作流统一 `Workflow Evidence Status`：`Passed / Failed / Skipped / Blocked / Missing`；HVR `N/A` 不适用于本 CC。
- 真实 API / LLM 均不调用；测试数据必须合成且不得包含客户真实值。

## 12. 停止条件 / 升级闸门

| 触发条件 | 升级路径 |
|---|---|
| 阶段 3 XML-RPC 安装/升级 Gate 缺口仍未补齐或正式处置 | 停止本 CC 冻结/实施；依 Plan 补证或修订 Plan。 |
| Mapping Session 无法安全保存规则，必须加入 TDD 未定义的原始 Proposal/样例/业务值字段 | 停止并升级 TDD 数据模型设计。 |
| 卡片必须读取当前 session 的 `TargetManifest`/allowlist，但不存在合规的服务端来源 | 停止；不得接受客户端清单，回到 TDD/CC-005 确认受控上下文接口。 |
| `validate_user_revision()` 的入参/返回契约与冻结 TDD 或已关闭 CC-M2-001 不符 | 停止并升级 TDD/CC-001，不修改校验器 schema 以迁就 UI。 |
| JSON-RPC 认证路由不能在 Odoo 中按所需方式阻断跨用户并可测试证明 | 停止；先核验 Odoo 路由语义并修订 TDD/接口设计。 |
| 需要修改 `llm_thread`、Message 核心源码或其他 Addon 才可注册卡片 | 停止；评估 TDD 架构，不得扩大白名单。 |
| 为实现确认按钮必须调用 M1 或创建输出文件 | 停止；该行为属于 CC-M2-005，不得提前扩张本 CC。 |
| 必须新增 Addon、依赖、状态或授权规则 | 停止并走 TDD/Plan/CC 变更批准流程。 |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | CC-CHANGE-001–006 均完成，且变更严格限于 §4 白名单 | 硬闸门 |
| 2 | 专用 mapping 消息通过 `Message.components` 渲染；普通聊天/附件/工具消息无回归 | 硬闸门 |
| 3 | 使用导入的 `rpc`；无 `useService("rpc")`；资产加载与 JS/XML 检查通过 | 硬闸门 |
| 4 | 更新/确认/取消端点在当前用户身份、owner/company/绑定对象、状态和 expected revision 下完成服务端授权 | 硬闸门 |
| 5 | 未知或无权字段/目标、额外键、旧 revision、跨用户请求拒绝且无 Session/映射变更；`validate_user_revision()` 真实路径已测试 | 硬闸门 |
| 6 | HVR-SCN-001–004 均 PASS；Playwright/HttpCase 自动验证按 §11 留有证据 | 硬闸门 |
| 7 | 样例/业务值没有进入 Session/持久消息/日志；无 `sudo()`/su/用户切换 | 硬闸门 |
| 8 | IHR、ATR、HVR 和基于其证据的 FR 完成；阶段 3 先决 Gate 已处置 | 交付闸门 |

本 CC 冻结或关闭不等于 M2 阶段完成；关闭、提交和推送仍由负责人明确批准。

## 14. 追溯矩阵

### 14.1 正向：本 CC 纳入的上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| `FR-M2-006` / `AC-07` | CC-CHANGE-001/002 | 专用映射卡片与字段选项展示。 |
| `FR-M2-007` / `AC-08/09` | CC-CHANGE-003/004 | 编辑、字段授权复验和 revision 更新。 |
| `FR-M2-008` / `BR-M2-004` | CC-CHANGE-005 | 当前映射版本明确确认；实际取数/M1 调用留 CC-M2-005。 |
| `NFR-M2-002` / `AC-16/20` | CC-CHANGE-004 | 用户、公司及对象访问隔离。 |
| `NFR-M2-003` / `T-M2-SEC-003` | CC-CHANGE-003/004 | 前端与模型输入服务端确定性校验。 |
| `NFR-M2-008` | CC-CHANGE-001/006 | 可理解 UI 状态及失败后的交互恢复。 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001/002 | `FR-M2-006`、`AC-07`、`T-M2-UI-001` | SRS/TDD |
| CC-CHANGE-003/004 | `FR-M2-007`、`AC-08/09`、`T-M2-SEC-003/004` | SRS/TDD |
| CC-CHANGE-005 | `FR-M2-008`、`BR-M2-004`、TDD §§8.2/10.3 | SRS/TDD |
| CC-CHANGE-006 | `FR-M2-013`、`NFR-M2-008` | SRS |
| CC-PRESERVE-001–005 | TDD §§8–10、CC-M2-001/002/003 | TDD/前序 CC |

### 14.3 无 DDD

N/A。追溯链为 `SRS → TDD → Implementation Plan → CC → IHR/ATR/HVR → FR`。

## 附录 A — 本次实现决策（草案）

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | 卡片由受控 message type 注册，消息持久化仅保存 Session 引用/revision；样例由当前用户 context RPC 获取。 | 将整个卡片数据与样例写进 `mail.message.body_json`。 | 避免业务样例进入聊天持久历史；符合 TDD 数据最小化与服务端授权。 |
| CC-DEC-002 | 编辑 RPC 调用 `office_mapping_verify.validate_user_revision()`，候选集合只由后端重建。 | 前端传完整 mapping/allowlist/manifest 后校验。 | 客户端内容不作为安全事实。 |
| CC-DEC-003 | CC-M2-004 的确认只登记当前映射 revision；M1 调用由 CC-M2-005 接入。 | 在此 CC 提前做 AI、Retriever 或渲染集成。 | 遵循 Implementation Plan 阶段 4/5 边界。 |
| CC-DEC-004 | 未授权 Session 访问使用受控拒绝；测试记录 Odoo 实际 HTTP/JSON-RPC 错误表示，并断言无数据泄露/无副作用。 | 仅在前端隐藏按钮、不测试后端拒绝。 | UI 隐藏不是权限边界；不同路由协议的状态码须以真实 HttpCase 证据为准。 |

## 附录 B — 评审前置与未决项

| 编号 | 事项 | 状态 | 影响 |
|---|---|---|---|
| `CC-M2-004-OPEN-001` | Implementation Plan 阶段 3 XML-RPC 安装/升级证据缺失。 | **OPEN — 负责人已于 2026-10-23 明确批准本 CC 冻结/实施；证据缺口仍保留，阶段 3 Gate 不得记为 PASS。** | 本次审批仅授权本 CC 按计划阶段 4 范围实施；阶段证据缺口须在项目追溯/计划 Gate 中单独处置。 |
| `CC-M2-004-OPEN-002` | `office.mapping.session` 映射字段及写入入口。 | **RESOLVED — 负责人裁定增加 `mapping_rules_json` Text、`confirmed_revision` Integer、`context_json` Text；公开 `write()` 禁止改动。** | 仅服务端内部服务允许写入；更新规则时 revision 控制，修改后确认标记清零。 |
| `CC-M2-004-OPEN-003` | JSON-RPC 未授权 Session 响应契约。 | **RESOLVED — 负责人裁定 owner/company 不匹配抛 Odoo `AccessError`。** | 不承诺或依赖 HTTP 403；HttpCase 检查 JSON-RPC 中 Odoo `AccessError`，并验证无副作用。 |
| `CC-M2-004-OPEN-004` | TargetManifest / allowed_fields context 来源。 | **RESOLVED — 负责人裁定由服务端写入 `context_json` 作为首期模拟上下文。** | 浏览器不能提供或修改候选字段、manifest 或授权结论；正式 AI/Retriever 数据供给留后续 CC。 |
| `CC-M2-004-OPEN-005` | 卡片消息的持久化数据边界。 | **RESOLVED — 负责人裁定 `mail.message.body_json` 仅保存消息类型、Session ID 和 revision。** | 候选字段和目标定义由当前用户的授权 context RPC 提供；禁止在消息、Session 或日志中持久化 Prompt、模板全文或业务样例明文。 |

负责人于 2026-10-23 批准冻结并实施本 CC。附录 B 的 OPEN-001 是未关闭的计划证据缺口，不因本次批准变更为 PASS。

## 附录 C — 关闭处置（冻结基线之后追加）

负责人于 2026-10-23 明确批准“cc-004允许关闭，提交推送git”。本 CC 据此按 **FROZEN WITH OPEN ITEMS** 作行政关闭处置；此批准不把 `ATR-M2-004` 的 `PARTIAL`、`HttpCase.browser_js` 的 `SKIPPED`、未完整人工验证的 HVR 场景或 Implementation Plan 阶段 3 Gate 改写为通过。

豁免登记：[`AUTHORIZATION_RECORDS.md`](AUTHORIZATION_RECORDS.md)，`EXEMPTION-CC-M2-004-001` 至 `EXEMPTION-CC-M2-004-003`。证据关闭评估见 [`FR-M2-004_owl_mapping_card.md`](FR-M2-004_owl_mapping_card.md)，其 Final Closure Status 如实为 `NOT SATISFIED`；阶段 3 Gate 仍为 OPEN，M2 阶段及项目不因此宣告完成。

## 附录 D — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-23 | Draft | 基于冻结 M2 SRS/TDD/Implementation Plan 起草阶段 4 Owl 卡片、RPC 校验、revision/权限边界及测试/HVR 契约。 |
| V1.0.0 | 2026-10-23 | Frozen | 记录负责人对 Session 字段/禁止直接写入、AccessError、服务端 context_json 来源、卡片消息最小持久化边界及继续实施裁定；阶段 3 XML-RPC 证据缺口如实保留。 |
| 2026-10-23 | FROZEN WITH OPEN ITEMS | 负责人批准 CC-M2-004 带未通过项关闭；未通过证据继续保留，详见附录 C、授权登记册与 FR。 |
