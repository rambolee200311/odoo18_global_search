# CC-M2-CB-06 — Finalize / Attachment Delivery

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-06 — Finalize / Attachment Delivery |
| 版本 | v0.2 |
| 状态 | **FROZEN V0.2 — CODING AUTHORIZED** |
| 设计基线 | Frozen TDD V2.0.3 及已批准的 CB-05 Existing Retriever Integration Change |
| 实施计划 | Frozen Implementation Plan V2.0.2 及 CB-05 Existing Retriever Integration Amendment |
| 依赖 | CB-01、CB-02、CB-03、CB-04、CB-05；依赖状态按其各自实际验收范围解释，见 §2 |
| 测试数据库 | 现有 Odoo 18 CE Demo 数据库 `odoo18ce` |

## 1. Contract Goal

完成 Candidate B 的正式文件交付闭环：用户已接受的 Candidate 成为 Accepted Current 后，用户明确要求正式交付时，系统将该 Current 版本正式化，并把对应 Office 文件作为私有附件关联到同一 Odoo Thread 的助手消息中。用户应能从聊天附件卡片直接打开或下载文件。

本 CC 只完成 Candidate B 的 Finalize / Attachment Delivery。它不重新编辑文件、不重新接受 Candidate、不创建另一条版本链，也不把内部 Candidate ID、版本号或文件 ID 当作交付成功。

### Accept 与 Finalize 的边界

| 阶段 | 权威事实 | 本 CC 的行为 |
|---|---|---|
| Candidate validation | CB-03 typed ValidationReceipt 及验证等级 | 原样保留；不重新定义验证结果 |
| Accept | CB-02 受控接受操作将 Candidate 变成 `accepted_current`，推进 Current / Last Valid / Document Revision | 必须已完成；Finalize 不替代 Accept |
| Finalize | CB-02 受控登记把符合规则的 Accepted Current 标记为 `finalized` | 只引用当前已接受版本，不改变文件字节或版本指针 |
| Delivery | 正式附件已关联到当前 Thread 消息，服务端可验证附件身份与字节 | 返回真实附件和消息事实；失败时不声称已交付 |

## 2. Existing Capability / Reuse Assessment

以下是对当前仓库代码、测试及验收记录的审计，不是本 CC 的运行测试结果。

| 能力 | 状态 | 代码/证据及边界 |
|---|---|---|
| Candidate B 当前版本解析、Session/Thread/用户/公司权限及 SHA 回读 | `IMPLEMENTED` | `mymodules/office_engine_m2/services/edit_orchestrator.py::_resolve_current`；不应在 CB-06 重写版本解析或读取权限 |
| Accepted Current 与 Last Valid、Document Revision、父链 | `IMPLEMENTED` | `services/workbook_version_service.py`、`models/office_workbook_version.py`；Accept 由 CB-02 服务执行，Finalize 不推进指针或 revision |
| 正式交付引用登记 | `IMPLEMENTED`（受理/绑定层） | `workbook_version_service.py::record_finalize_reference` 校验 Current、Thread/assistant 消息、附件可读性、公司、MIME 与接受版本 SHA；在 Session 锁下登记 `final_attachment_id`、`final_message_id`、`finalized_at` 和 `delivery_state=delivered`；相同引用可幂等重放。它不创建/发送交付消息 |
| 版本文件私有存储和不可变性 | `IMPLEMENTED` | `workbook_version_service.py::_create_version_attachment` 创建 `public=False` 且绑定版本的附件；`models/ir_attachment.py` 限制附件写入/删除；`office.workbook.version` 对输出及最终交付关系有约束 |
| M2 附件挂到 Thread 消息 | `IMPLEMENTED`（通用 Odoo/M1 模式） | `office_engine_odoo/models/office_document_request.py::_ensure_output_chat_message` 按 Thread/附件查重并 `message_post`；M1 输出路径已使用 |
| M1 初始版本登记及交付 | `IMPLEMENTED`（M1） | `services/render_bridge.py::_register_initial_workbook_version` 登记初始 V1，并调用 `record_finalize_reference`；不等于后续 Candidate B Current 的 Finalize 路由已接通 |
| M1 `office_finalize` | `IMPLEMENTED`（M1 Proposal/Render 流程） | `models/office_mapping_tools.py::office_finalize` / `_office_finalize`；验证 Session/Proposal revision 和 M1 Preview 确认，然后调用 `render_confirmed_mapping`。它不是 Candidate B 版本化 Current 的 Finalize 服务 |
| Candidate B 单一 `office` Facade | `IMPLEMENTED`（status/retrieve/plan/edit/accept/reject） | `office_mapping_tools.py::office` schema/`services/edit_orchestrator.py::dispatch_office_action`；动作枚举当前没有 `finalize`，dispatch 也没有对应分支 |
| Accepted Current 时的 Tool 可见性 | `IMPLEMENTED` | `models/llm_thread.py::_prepare_chat_kwargs` 对 versioned Current 仅向模型提供 `office`；`_execute_tool_call` 中的旧 `office_finalize` 分支不能被 Candidate B 当前 Tool 策略作为完成方案 |
| 交付消息进入实时聊天附件卡片 | `PARTIAL` | `llm_thread.py::_execute_tool_call` 对旧 `tool_name == "office_finalize"` 加载 M1 已提交消息；未发现 `office(action="finalize")` 的消息/Store 事件处理 |
| Candidate B Finalize 调用链 | `MISSING` | 缺少单一 `office` Facade 的 Finalize action、Accepted Current 文件 `message_post` 的 M2 路由及其实时附件卡片反馈 |
| 交付引用服务幂等登记 | `IMPLEMENTED`，完整交付幂等 `PARTIAL` | `record_finalize_reference` 能幂等重放相同附件和消息；尚未发现对 M2 `message_post` 本身的“先复用已交付消息、否则只建一次”完整入口 |

### 验收基线

- CB-01：`ATR-M2-CB-01.md` 记录负责人 `Final Accepted`；仅关闭 Responses Adapter 技术范围。
- CB-02：`ATR-M2-CB-02.md` 记录技术范围 `Final Accepted`，且后续 Intent Binding Amendment 有独立集成证据。版本、附件、权限、锁和 `record_finalize_reference` 是权威复用入口。
- CB-03：`IHR-M2-CB-03.md` 记录本地 Validator、typed Receipt 等限定技术范围 `Final Accepted`；不包含 Finalize/Browser 验收。
- CB-04：`IHR-M2-CB-04.md` / `ATR-M2-CB-04.md` 记录本地/Mock 与 Odoo 自动测试通过；最新 HVR-02 UI 下载、HVR-03 查看/接受、HVR-04 接受 V3、HVR-05 拒绝 V4 仍有 `NOT RUN / BLOCKED / PARTIAL` 项。不得把 CB-04 标成完整 UI HVR 已接受。
- CB-05：`FR-M2-CB-05_Existing_Retriever_Integration.md` 记录 `Final Accepted`；同一 Thread 两阶段 Retriever/Mock Candidate 接受和独立 XLSX 回读通过，但不含 Browser、Finalize 或正式交付。

因此，CB-06 需要在不重做 CB-02～05 的前提下，补齐 Candidate B 当前版本到 Thread 附件消息的最后一段调用链。

## 3. In Scope / Out of Scope

### 3.1 In Scope

- 从当前用户、当前 Thread 解析唯一的 Office Session 与 Accepted Current。
- 将 `finalize` 作为既有单一 Candidate B `office` Tool 的 action。
- 复用 CB-02 权限、Current/Last Valid/revision、附件 SHA、Session 锁、版本字段及 `record_finalize_reference`。
- 把 Accepted Current 已有的私有输出附件关联到该 Thread 的助手消息；优先复用现有字节，不无故复制附件。
- 让 `llm_thread` 将正式交付消息及附件序列化进实时 Discuss Store，使当前 Thread 显示可用附件卡片。
- 返回服务端实际确认的文件名、MIME、附件/消息引用、SHA 和交付状态。
- 对相同版本的重试保持幂等，保留当前版本权限和附件安全。
- 用 `odoo18ce` 的合成 XLSX、现有 CB-05 自动化联系人用例及正式 Accept/Finalize 服务验证交付。

### 3.2 Out of Scope

- Preview 功能、OnlyOffice Preview 对接及 Candidate B 预览 UI。
- Provider Adapter、Excel 编辑器、Retriever、Candidate Validator、Accept/Reject 或版本服务重构。
- 新版本管理/数据库模型、第二套 Receipt、通用审批/风险引擎、独立公开 Agent Tool。
- M1 Mapping/`office_finalize` 的语义或全局 M1 Tool Registry 迁移。
- 生产部署、真实业务附件、真实数据外发或生产留存/删除策略决定。
- 以 Finalize 代替 Candidate 接受，或将附件链接做成公开 URL。

## 4. Finalize Contract

### 4.1 输入及目标解析

`office(action="finalize")` 不接受 Agent/RPC 指定的任意 `version_id`、`attachment_id`、用户 ID、Thread ID、公司 ID 或 `delivered=true`。服务端从当前受信任 tool-call 上下文解析 Thread 与用户，再从该 Thread/用户拥有的 Session 读取 Current。

仅在以下条件成立时可继续：

1. Session、Thread、当前用户和当前公司范围匹配，ORM ACL/Record Rules 允许读写服务所需记录。
2. Current 与 Last Valid 是同一版本，且该版本属于本 Session/Thread。
3. 版本状态为经现有 CB-02 正式接受的 Current；候选仍待接受、已拒绝、失败、过期或非当前版本不得交付。Finalize 尊重已有 Accept 决定，包括已被有效 Accept 的 `PARTIALLY_VERIFIED` Current。
4. Current 输出附件可读、私有、类型与文件名一致、字节非空；独立计算的 SHA-256 与 `output_sha256` 一致。
5. 在发布前再次取得 Session 锁并核对 Current、Accepted Document Revision、附件 ID 和 SHA；竞态变化时以 stale/blocked 失败返回，不发布旧版本。
6. 用户在当前 Thread 明确提出正式生成或交付文件，即构成 Finalize 指令。请求绑定实际用户消息及当时解析出的 Thread、Current、Session、Revision 和 SHA；不要求固定确认短语，不要求重复 Accept，也不接受模型传入的用户身份或授权布尔值。

### 4.2 版本语义

- Finalize 不写 Workbook 内容，不运行 Provider/Validator，不创建新的 Candidate 或版本号。
- 成功后对同一版本记录 `state=finalized`、`delivery_state=delivered` 及附件、Thread 消息和时间引用；Current、Last Valid、Document Revision、文件 SHA 保持不变。
- 后续接受 V(n+1) 时，按 CB-02 既有生命周期处理前版为 `superseded`；历史正式附件和交付消息仍可审计/读取，不得被新版本改写。
- Finalize/Delivery 失败不得撤销已接受 Current、不得更改其文件字节，不得返回成功或声称可下载。

### 4.3 验证等级与最小设计同步

Finalize 尊重 CB-02 已记录的有效 Accept，不重新执行 Candidate Validator，不把 `PARTIALLY_VERIFIED` 提升为 `VERIFIED`，也不重新裁决用户已接受的业务结果。只做交付所需的现行权限、Current/Revision、附件身份和 SHA 一致性检查。输出及附件消息须如实保留原验证等级；正式交付不表示该等级或业务正确性得到提升。

冻结 TDD 与现行 CC-04/CB-02 接受行为存在相反条款。配套 TDD 变更只需修正以下位置，维持验证等级定义和 CB-03 行为不变：

| 冻结条款 | 最小同步内容 |
|---|---|
| TDD V2.0.3 §5.2 状态语义 | 删除“仅 VERIFIED 可成为 `accepted_current` / PARTIALLY_VERIFIED 不得推进 Current、Last Valid 或正式发布”的绝对限制；有效 CB-02 Accept 推进的指针保持有效，验证等级保留原值 |
| TDD V2.0.3 §6.3 `PARTIALLY_VERIFIED` 行 | 删除“不得 Finalize/正常交付”；明确有效 Accept 后可交付，Finalize 不重验或升等，结果继续标记 `PARTIALLY_VERIFIED` |
| TDD V2.0.3 Appendix A.3.1 生命周期 | 将 `partially_verified ... never accepted_current` 改为仅 `failed/stale` 永不接受；PARTIAL 是否成为 Current 由现有受控 Accept 决定 |
| TDD V2.0.3 Appendix A.3.2 / A.3.4 / A.5 | 同步验证等级接受表、`verify_and_accept` 输入资格及测试预期；有效 Accept 的 PARTIAL 可正式交付但不升等；保留 `FAILED` 不可接受、权限/安全/完整性门不可绕过 |

以上为设计文本同步，不在本 CC 中新增安全机制、验证器或用户审批层。

## 5. Attachment Delivery Contract

### 5.1 附件与消息

- 使用 Current 版本 `output_attachment_id` 所指向、已绑定版本的私有附件；其字节必须与 Current `output_sha256` 完全一致。
- 通过 Odoo Thread 的 `message_post` 关联文件到 `model="llm.thread"`、`res_id=<当前 Thread>` 的助手消息；复用 Odoo `ir.attachment` / `mail.message.attachment_ids`，不创建公开附件，不构造下载 URL。
- 若附件卡片需进入实时聊天 Store，复用 `llm_thread.py` 已有的消息/Store 序列化方式。只有 Store 载荷确实含相应 Thread 消息和 attachment 元数据，Facade 才可返回 `attachment_posted_to_thread=true`。
- 对外可理解结果至少包含：`status`/`operation_status`、`delivery_state`、版本 ID/版本号、文件名、MIME、SHA-256、附件 ID、消息 ID 及 `attachment_posted_to_thread`。不把附件 ID 当作下载凭据，不向模型输出公开访问地址。
- 成功结果按单一 `office` Outcome 表达：`status="completed"`、`operation_status="finalized"`、`artifact_state="finalized"`、`delivery_state="delivered"`、`operation_executed=true`。字段值须与现有 Facade 结果约定兼容；不得把原生 Tool 消息 `completed` 单独当作业务交付成功。

### 5.2 重试和失败

- 同一 Accepted Current 重复 Finalize/Delivery 时，返回并推送既有 `final_attachment_id` / `final_message_id`；不得产生附件副本或无故重复消息。
- 通过版本/Session 锁和已有交付引用查重实现幂等；优先复用 `record_finalize_reference`，不新增幂等框架或版本字段。
- 消息创建失败、消息缺附件、附件读取失败、SHA 不符、权限变化、版本竞争或 Store 卡片不可见时，返回准确的 `failed` / `blocked` / stale 结果。持久化 delivery 状态不得错误变为 `delivered`；已接受版本保留为 Current/Last Valid。
- 若消息与数据库记录在一个事务中提交，失败应回滚未完成的消息/登记；若实现复用隔离事务，则必须在重试时发现并复用已提交的同版本消息。不得让一次 Provider/Agent 后续响应超时诱发重复附件。
- 失败重试只重试交付，不重新编辑文件，不重新接受 Candidate，不重新运行 Validator。

## 6. Office Tool Integration

### 6.1 单一公开入口

Candidate B 当前已有的唯一公开入口是 `office`。在其现有 action schema 和 `dispatch_office_action` 中增加 `finalize` 路由；不新增 `office_finalize_candidate` 或其它公开 Tool。Accepted Current 后仍只向 Agent 暴露 `office`。现有 M1 `office_finalize` 保持兼容、只处理 M1 Proposal/Render，不作为 Candidate B 入口。

`finalize` action 只携带完成路由所需的最小参数；Current、用户、Thread、Session、版本与附件均由服务端受信任上下文解析。Agent 指引说明：只在用户明确要求正式生成/交付时 finalize；只有返回明确的 delivered 结果且附件已关联 Thread 后，才告知用户“文件已附在当前聊天中”。不要伪造 Markdown 链接、URL 或 `attachment://` 地址。

### 6.2 实时聊天反馈

`llm_thread._execute_tool_call` 当前只对旧 `tool_name == "office_finalize"` 推送 M1 正式附件卡片。CB-06 应为 `tool_name == "office"` 且结果 action/status 表示 Candidate B 正式交付的情况，复用该 Thread 消息的 Store 序列化并推送 `message_create`。如正式消息已提交，则用当前用户的新 cursor 读取并校验 Thread/消息/附件关联；如仍在同一事务，则不额外跨 cursor。不能仅在 Tool JSON 中回传附件 ID 就视为 UI 可见。

### 6.3 与接受流程的衔接

- 只有 CB-02 已接受的 Current 可 Finalize。对非当前 `verified` Candidate 的 Review、Accept、Reject、Revise 继续由 CB-04/CB-02 控制；Finalize 不代替用户选择，也不直接推进指针。
- 如果用户在一条消息中同时明确要求接受并交付，Facade/Agent 可按已存在的受控顺序先完成 Accept，再针对新 Current 执行 Finalize；第二步必须重新解析/校验当前版本，不复用旧 Candidate/父版本身份。
- 没有完成 Accept 的 Candidate 不能通过 Finalize 变成 Current；Finalization 失败不撤销已成功的 Accept。

## 7. Minimal Implementation Scope

以以下文件作为最小实施范围：

| 文件 | 最小职责 |
|---|---|
| `mymodules/office_engine_m2/models/office_mapping_tools.py` | 在 `office` action schema 与 facade 参数/结果映射中加入 `finalize`；M1 `office_finalize` 原样保持 |
| `mymodules/office_engine_m2/services/edit_orchestrator.py` | 在既有 dispatcher 中将 `finalize` 路由至受信任版本化交付服务；不复制版本解析、ACL 或 SHA 检查 |
| `mymodules/office_engine_m2/services/workbook_version_service.py`（如需） | 复用锁和 `record_finalize_reference`，仅补齐 Accepted Current 的消息复用/登记所必需逻辑；不改变 CB-02 的版本/接受语义 |
| `mymodules/office_engine_m2/models/llm_thread.py` | 为 `office(action=finalize)` 的真实交付结果推送当前 Thread Store 消息和附件卡片；保留 M1 路径 |
| `mymodules/office_engine_m2/models/office_workbook_version.py` / `models/ir_attachment.py` | 默认不修改；仅在必要时修复实测发现的当前交付引用/保护缺口，必须受限于本 CC 并另行说明 |
| `mymodules/office_engine_m2/tests/` | 增加 Finalize/Delivery TransactionCase、Facade/Thread Store、权限、失败和 M1 兼容回归 |
| `docs/implementation/IHR-M2-CB-06.md`、`ATR-M2-CB-06.md`、`HVR-M2-CB-06.md`、`FR-M2-CB-06_Finalize_Attachment_Delivery.md` 及 `evidence/CB-M2-CB-06/` | 仅追加实际实施、测试、HVR 和验收证据；不覆盖历史结果 |

不新建数据库、附件或版本模型；不修改 `office_tools.xml` 中的 M1 注册，不改 Provider/Mapping/Validator/Retriever。沿用既有版本和交付字段。

## 8. Automated Tests / HVR

### 8.1 自动化测试

使用现有 `odoo18ce` Demo 数据库和合成 XLSX，不创建数据库。运行必要的 CB-06 TransactionCase、Office Engine M1 附件/RenderBridge/Finalize 回归。接受版本可由现有 CB-02/CB-04/CB-05 正式服务及 Mock Candidate 适配产生；不得直接 ORM 写入 Candidate/Current/delivery 状态来伪造业务接受或交付。

至少覆盖：

1. Accepted Current + matching private attachment → `office(action="finalize")` 产出 Thread assistant 消息，正式引用记录及文件 SHA 完全匹配；Current、Last Valid、Document Revision 不变。
2. 非当前/未接受 Candidate、已拒绝/失败版本、Current/Last Valid 不一致、stale revision、错误 Thread/Session/公司、无权读取附件均不能 Finalize/Delivery。
3. 附件内容或 SHA 被篡改、消息未关联到当前 Thread、消息不是助手消息、附件缺失或 Store 无法读取时，不报告 `delivered`。
4. 同一版本重复调用并模拟工具调用后模型请求超时/重试：返回相同附件/消息 ID，不产生附件副本和重复交付消息。
5. 失败注入覆盖 `message_post`、引用登记、附件读取/哈希及并发 current 变化；已接受版本仍然可用，状态不伪报成功。
6. `office` schema 可见 `finalize`，Candidate B Thread 仍只向模型提供公开 `office`；M1 旧 `office_finalize` / Finalize 回归不变。
7. 新版本在 Finalize 后成为 Current 时，原版交付引用保持有效，新版必须按自己的 current SHA 独立交付。
8. Existing CB-02/03/04/05 与 M1 定向回归覆盖受影响入口；报告执行范围和测试数，不以历史报告代替本轮实跑结果。

### 8.2 HVR 场景

HVR 使用当前用户的真实 Odoo Discuss UI 验证最终文件从 Thread 附件卡片交付。可使用已接受的合成工作簿及 Mock 生成的 Candidate；真实 Provider 和 OnlyOffice Preview 不属于本 CC 的必要条件。

| 场景 | 操作 | 通过条件 |
|---|---|---|
| A — 正式完成 | 在同一用户 Thread 对已 Accepted Current 明确请求生成正式文件 | `finalize` 路由真实调用；Accepted Current 被绑定；版本/Current/Last Valid/Revision 不发生非预期变化 |
| B — Thread 附件交付 | 在 Odoo 聊天中看到正式附件卡片并通过当前用户会话下载 | 附件卡片可见；下载 HTTP 成功；实际 XLSX 字节 SHA 等于被接受版本 SHA；独立读取可打开，文件名/MIME 正确 |
| C — 两阶段联系人工作簿 | 复用 CC-05 同一 Thread 的联系人两阶段 HVR 产物或同等合成场景：V2 填姓名/电话/邮件，V3 补地址；通过正式业务 Accept 服务接受 V3 后 Finalize | 下载件与 V3 的输出 SHA/内容一致；A–C 保持、D 地址与已取数值一致；V1→V2→V3 lineage 与当前版本字段一致 |
| D — 重复交付 | 对已经 Delivered 的同一 Current 重放正式请求 | 返回同一最终附件和消息，不额外生成附件副本；Thread 不因重试收到重复附件卡片 |

记录并分别标注自动化测试与真实 UI 验证。HVR 必须实际观察 Discuss 附件卡片、通过当前用户会话下载交付文件，并对下载字节做独立 SHA 和 XLSX 回读；TransactionCase、服务调用或 Mock 测试不得冒充 UI/下载验证。CC-05 两阶段 Automated User Simulation 可复用为输入工作簿场景，但需在 CB-06 重新验证最终交付件。

### 8.3 M1 兼容

复跑与 Finalize/Thread 附件事件相关的 M1 `office.document.request`、`office_finalize`、RenderBridge、附件权限、下载及消息 Store 测试。M1 旧 Proposal 的精确确认、渲染/存档语义不得因新增 Candidate B action 改变。

## 9. Acceptance Criteria

满足以下条件后可提交 `READY FOR FINAL ACCEPTANCE`，最终状态由负责人决定：

- `office` facade 有单一、受控、可调用的 Candidate B `finalize` action；没有新增公开 Agent Tool。
- Finalize 只能引用服务端解析的当前 Accepted Current，包括通过现有正式流程接受的 `PARTIALLY_VERIFIED` 版本；原验证等级保持不变。用户明确的正式交付请求绑定当前用户、Thread、Session、Accepted Revision 和 SHA，不要求固定短语或重复 Accept。
- 正式附件的实际字节 SHA 等于 Accepted Current `output_sha256`；文件名与 MIME 正确；附件保持私有且同公司/Session/版本受控。
- 正式附件已关联到当前 Thread 的助手 `mail.message`，且聊天 Store/附件卡片提供当前用户可用的打开/下载入口。
- 下载的实际文件可读，内容等于 Accepted Current；不得以模型文本、Tool JSON、附件 ID 或数据库状态单独推断用户已收到文件。
- `Current == Last Valid`、`Document Revision` 和 Accepted Current 文件 SHA 在 Finalize 后保持一致；仅交付事实改变为 `finalized/delivered`。
- 相同 Current 重试返回相同附件/消息，未生成副本或重复卡片；失败/冲突不伪报 delivered，Accepted Current 可安全重试。
- CC-05 两阶段联系人工作簿最终 V3 经 Accept、Finalize、Thread 下载及独立读回通过。
- M1 Finalize、M1 附件权限与兼容性回归通过；IHR/ATR/HVR/FR 有证据索引。
- TransactionCase 和 M1 回归在现有 `odoo18ce` 执行，不新建数据库；HVR 有真实 Discuss 附件卡片、用户下载及独立 XLSX 回读证据，并与自动化测试结果分开记录。

## 10. Open Questions

本 CC 范围内无待负责人裁决的产品问题。冻结 TDD 的最小同步条款见 §4.3；实施和测试按本 v0.2 对 `PARTIALLY_VERIFIED`、Finalize 指令及 HVR 的明确规则执行。

---

## 变更记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-10 | DRAFT — NOT AUTHORIZED | 原始评审稿，保留历史。 |
| v0.2 | 2026-11-10 | FROZEN V0.2 — CODING AUTHORIZED | 负责人批准冻结并进入实施；明确有效 Accept（含 PARTIALLY_VERIFIED）的正式交付、用户明确 Finalize 指令，以及 `odoo18ce` TransactionCase/M1 回归/真实 Discuss 下载 HVR。 |
