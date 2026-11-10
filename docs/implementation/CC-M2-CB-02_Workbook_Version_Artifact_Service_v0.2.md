# CC-M2-CB-02 — Workbook Version & Artifact Service

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-02 — Workbook Version & Artifact Service |
| 版本 | v0.2 |
| 状态 | **DRAFT — PENDING FINAL REVIEW** |
| 上游设计 | `docs/design/TDD_office_engine_m2_v2.0.2.md` — FROZEN |
| 上游计划 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` — FROZEN |
| 前置 CC | `CC-M2-CB-01` — Final Accepted by project owner on 2026-11-06 |
| 起草日期 | 2026-11-06 |

> 本文件是 CB-02 契约草案，不冻结、不授权编码、模块升级、数据库迁移或部署。冻结 TDD V2.0.2 §5.4 的历史版本恢复范围与本草案建议存在未解决冲突；在负责人裁定并按需修订上游基线前，不得冻结或签发 Coding Authorization。

## 1. 目标与验收边界

建立 Odoo 侧工作簿版本与文件制品的权威谱系，使首轮 M1 验证通过的文件可作为 V1，后续每个文件候选都能明确记录父版本、真实字节哈希、状态、验证引用和附件来源，并仅在服务端版本条件满足时原子推进当前有效版本。

本服务管理文件身份、来源和生命周期元数据；**不编辑工作簿内容，不调用 Provider，不替代 Validator，也不自行批准业务风险。** Session/Proposal revision、Provider Response ID 和 Workbook Version ID 是不同身份，不得互相代用。

本 CC 的完成只表示版本服务契约及其 Odoo 持久化行为通过。它不表示真实 Provider 编辑、多轮 LLM 行为、Preview/Finalize UI 或生产发布通过。

## 2. 权威依据、前置条件与冻结原则

### 2.1 架构依据

- TDD V2.0.2 §5.1–§5.4：父子版本链、版本状态、current/last-valid、不依赖聊天历史恢复文件、Finalize 引用已接受版本、失败候选不推进；§5.4 明确要求显式历史版本切换或创建恢复版本并重新验证。该要求与本 v0.2 建议的 CB-02 首期不提供用户主动恢复相冲突，按 §13 列为 BLOCKER，不修改冻结 TDD。
- TDD V2.0.2 §6：只有 `VERIFIED` 候选可被接受为 `accepted_current`；`PARTIALLY_VERIFIED`、`FAILED` 或未验证候选不得覆盖 last-valid 或进入 Finalize。
- TDD V2.0.2 §8.1：逻辑 `verify_and_accept` 由 Validator 与版本提交协作；CB-02 提供验证结果受理接口和版本提交原语，不实现文件/Effect Validator。CB-02 的 Odoo TransactionCase 使用仅在测试目录存在的可信 Validator 替身；真实 CB-03 Validator 的生产集成不属于 CB-02 关闭声明。
- Implementation Plan V2.0.1 §5、§11–§13：本 CC 负责版本/哈希/父链/current/last-valid、乐观并发、旧 Session/附件兼容及不破坏性迁移；CB-03 验证候选，CB-06 负责 Preview/Finalize/Delivery。
- CB-01 已真实验证 Adapter 能返回并下载合成 XLSX 候选，且独立回读通过；该证据只供候选输入接口参考，不将候选自动视为版本或已验证文件。

### 2.2 编码前置 Gate

编码授权签发前必须满足：

1. 项目负责人已批准适用于 Candidate B 后续文件编辑的版本化 SRS 变更。TDD 和 Implementation Plan 不替代该变更。
2. 负责人单独冻结 CB-02 契约并签发 Coding Authorization；本 v0.2 草案本身不具备该效力。
3. 本 v0.2 已完成 §2.4 所列只读代码差异审计；实施时只按 §9 白名单修改。若要改变本契约语义，先提交契约修订，不由编码者自行决定。
4. 记录 branch、HEAD、工作区状态、Odoo/Addons/Python 依赖和相关测试基线。不得清理、覆盖、暂存或提交既有用户修改。
5. 确认本次迁移涉及的模块及其数据安全、附件留存、恢复和维护窗口；不得读取或写入超出已批准范围的数据。

### 2.3 当前实现的只读对照证据

- `mymodules/office_engine_m2/models/office_mapping_session.py:85-143`：`office.mapping.session` 已有 owner/company/thread/source message/source attachment、Session `revision`、`proposal_revision`、Proposal/history、preview attachment、confirmed revision 和模板/数据指纹；`:215-266` 禁止普通 `write()` 并以服务迁移和行锁推进 Session revision。没有 Workbook Version 父链、独立 `document_revision` 或 current/last-valid 指针。
- `mymodules/office_engine_m2/services/mapping_service.py:18-67`：创建 Session 前在当前 ORM 环境校验 Thread、用户消息、附件、目标记录可读性和关联；`:559-581` 通过 Session 完成状态、稳定 request UUID 和 ACL 检索 M1 输出。它可复用为绑定校验入口，但不代表已有版本谱系。
- `mymodules/office_engine_odoo/models/office_document_request.py:175-205`：`office.document.request` 有唯一 `request_uuid`、owner/thread/message/source/output attachment、请求状态和 input/output SHA。`:433-447` 检查 `verify_output` 的 `PASS` 与输出 SHA；`:693-748` 将私有附件、SHA、`generated` 状态和 `readback` 返回值提交。验证报告目前仅随本次返回值传递，模型未持久化报告 ID 或 validator policy/version，因此历史请求不能仅凭 `state=generated` 或输出 SHA 认定为 V1 已验证。
- `mymodules/office_engine_odoo/models/office_document_request.py:65,268-326`：请求 create/write 受 Python `ContextVar` 内部变更范围及字段/状态迁移约束保护；它不是 `env.context` 标志。该机制仅为现状参考，不能单独充当候选验证证明。
- `mymodules/office_engine_odoo/models/ir_attachment.py:10-22`：只将绑定到 `office.document.request` 的输出附件设为普通 ORM 用户不可写/删除；新绑定到 `office.workbook.version` 的附件当前不在该保护范围，且现有保护在 `env.su` 下可绕过。CB-02 不得使用 superuser mode；需要为版本附件增加适用的常规 ORM 不可变保护。
- `mymodules/office_engine_m2/__manifest__.py:7-20` 依赖 `office_engine_odoo` 并已加载 M2 ACL/规则；`models/__init__.py` 注册 Session、Usage、Skill、Thread 和工具模型。`office_engine_m2/security/ir.model.access.csv:4` 授予内部用户 Session CRUD（unlink=0），`office_mapping_session_rules.xml:3-7` 限制 owner 与允许公司。`office_engine_odoo/security/ir.model.access.csv:2` 授予 document request 用户 CRUD（unlink=0），其规则 `office_document_request_rules.xml:3-8` 为 owner-only。审计范围内未发现专门的 `ir.attachment` Record Rule；附件访问仍须按 Odoo 标准附件安全检查及绑定关系实际测试。
- M1 `office_verify.VerificationReport`（`mymodules/office_verify/models.py:58-83`）包含 status、格式、输入/输出 SHA、目标/公式计数和警告，但无稳定 report ID 或 policy/version 字段。`VerificationPolicy` 当前为配置对象，亦无自身版本标识。V1 只能在受信任 M1 调用链仍持有成功回读证据，或已有可验证持久证据时登记；历史记录缺少该证据时必须保持 legacy。

### 2.4 现有能力与目标版本模型差异

| 现有能力 | 可复用字段/模型 | 缺失能力 | 建议新增/修改 |
|---|---|---|---|
| Session owner/company/thread/source/Proposal 与预览绑定 | `office.mapping.session` 的 owner、company、thread、source attachment/message、revision、proposal_revision、preview attachment | 文档版本 revision、父链、current/last-valid 指针 | 新 `office.workbook.version`；Session 增加独立 document revision 与 current/last-valid 关系字段，不合并现有两类 revision |
| 单次 M1 请求、稳定 UUID 与实际输入/输出 SHA | `office.document.request`、`request_uuid` 唯一约束、私有 output attachment | 跨多轮 parent/version lineage；可恢复的 M1 验证证明元数据 | 保留 request 作为 M1 处理审计源；在受限写入中持久化 M1 policy/version 与 report digest/ID，供同一会话注册 V1；不能把 request UUID 当 version ID |
| M1 文件回读 | `verify_output` 返回 `VerificationReport`；输出 SHA 与附件字节在 `_deliver_result` 核验 | 稳定 policy/version 和 report ID；历史 request 当前未保存 readback | 新 V1 登记仅接受受信任内部验证收据；可从规范化报告摘要生成 report ID，附显式版本化 policy ID；老记录无证据则不回填 |
| Preview/Finalize 附件 | `office.mapping.session.preview_attachment_id`；`office.document.request.output_attachment_id` | 附件绑定 version、私有 version ACL/Record Rule、version 附件不可变 | 每个版本附件绑定 `office.workbook.version`、private 且 company/session scoped；扩展自定义附件不变性检查，不依赖 `sudo()` |
| 幂等和当前并发控制 | `office.document.request.request_uuid` 全局唯一；Session service 使用当前用户 ORM 访问后锁行并核验 revision | 版本层候选幂等键、同键同 payload 判重、同键不同 SHA 拒绝、版本 current 唯一提交 | 在版本模型加 Session 范围唯一 idempotency key 和 version number；锁 Session 行后重读 ORM 状态并在同一事务提交指针 |
| 旧 Session/Proposal/history | 当前模型与 JSON 历史继续可读 | 旧记录不能自动证明符合 V1 验证契约 | 旧 Session 继续走 M1 兼容路径；缺少可验证 proof 的附件维持 legacy，不自动注册 |
| Addon 注册与 ACL | `office_engine_m2` 已依赖 `office_engine_odoo`；manifest 加载 ACL 与 XML rule | Version model 注册、owner/company/session 范围规则及测试导入 | M2 模型、manifest、`models/__init__.py`、ACL、Record Rule 和 TransactionCase |

#### 版本和 revision 存储不变量

- `office.workbook.version` 是父子文件谱系与单个候选生命周期的权威记录；`office.mapping.session` 持有 current/last-valid 指针以及单独的 `document_revision`。现有 `revision` 与 `proposal_revision` 保持原含义。
- 每个版本保存其捕获的 Session revision、Proposal revision（适用时）和 Document revision。候选登记键为 Session 范围唯一的 idempotency key；同一键同一规范化输入 SHA/父版本/操作请求时返回同一候选，不新增有效版本；同一键而输入或输出 SHA 不一致必须拒绝。
- Version number 在 Session 内唯一；候选尝试可以留下序号空洞，序号不得重用。parent_version 指向实际输入版本。`current/last-valid` 是 Session 单行的关系指针，避免在多版本行上维护多个 current 标志；接受事务中推进指针并将旧版本转为 superseded。
- 数据库唯一约束保证 `(session_id, version_no)` 与 `(session_id, idempotency_key)` 不重复。两个同 parent 候选并发时，通过 Session 行锁/等效条件更新，在锁后 ORM 重读 parent 和 Document revision；只有一个事务能推进单行指针，另一个返回 stale，不得自动重基。此数据库竞争保证必须用隔离数据库、独立连接验证，不可由顺序 TransactionCase 推断。
- V1 的验证依据必须是 M1 成功回读：`office.document.request` 为 `generated`、output attachment 绑定正确且 `public=False`、真实字节 SHA 与请求输出 SHA 一致，验证报告结果为 M1 支持等级中的通过，并绑定显式 M1 validator policy/version、报告 ID/摘要及 Session/Proposal revision。现有 `VerificationReport` 缺少 report ID/policy version，需由受信任调用链登记的证明适配器产生并持久保存；单有 `generated`、预览附件或模型回复均不够。历史请求若没有可复核 readback/policy 证据，不得登记为 V1。
- `office_mapping_session.py:154-170` 当前含有旧 Session state 的 `init()` SQL 映射；此为既有模块迁移逻辑，不构成 Workbook Version 数据契约。新版本迁移只加表/字段/约束，不沿用该状态重写去伪造 V1 或 validation proof。

## 3. 职责边界

### 3.1 范围内

- 为已经通过适用初始文件验证的 M1 输出登记 V1；不根据“存在预览附件”推定验证通过。
- 登记 Responses Adapter 下载后的真实候选附件及其父版本、输入/输出 SHA-256、调用关联和不可信 Provider 元数据。
- 维护 Session 内的版本编号/父链、候选及接受状态、current/last-valid 指针、乐观并发 revision、私有附件绑定和只读历史查询。
- 实现受控的验证结果接收契约、绑定核验、状态迁移与原子接受。实际文件/结构/Effect/支持矩阵判定归 CB-03；CB-02 不实现 Validator，也不从普通字符串、report ID 或候选状态推断验证成功。
- 记录 Finalize 对已接受版本的引用及交付关联元数据；正式文件发布和消息交付由 CB-06 执行。
- 通过当前用户 ORM 环境执行版本/附件读取授权；维护 owner、Thread、Session 和 company 边界。
- 在 Odoo TransactionCase 使用只存在于测试代码的可信 Validator 替身，验证版本服务的 proof 绑定和接受行为；该替身不打包、不注册、不被生产入口导入或调用。
- 以加法方式保存新版本谱系；旧 Session、Proposal、Preview、request 和 attachment 保持原读写语义。

### 3.2 范围外

- XLSX/DOCX 编辑、格式转换、公式计算、Provider API/Code Interpreter 调用。
- 用户自然语言意图、风险分类、确认授权或 Confirmation Gate；属于 CB-04。
- 文件内容、Effect、结构或支持矩阵验证；属于 CB-03。CB-02 只提供无公开 RPC/工具入口的服务端受控 proof 接收与 accept 原语；生产候选在 CB-03 可用前不能通过真实 Validator 进入 current。
- Data Tool JSON Refresh；属于 CB-05。
- Preview UI、Finalize 执行、Thread 消息发布、浏览器附件展示和下载；属于 CB-06。
- 删除或重写旧 Session/Proposal/附件历史；破坏性迁移。
- 将 Proposal revision、Session revision、`office.document.request` UUID 或 Provider Response ID 冒充版本号。
- 生产发布、旧记录全量自动回填、自动恢复/重新激活旧确认、Candidate C 或新的全局状态框架。
- 按当前建议，CB-02 首期不提供用户主动切换/恢复历史版本、不重写父链、不自动重新激活确认；该范围与冻结 TDD §5.4 冲突，未获正式上游变更前为冻结阻塞项，见 §13。

## 4. 最小版本记录契约

最终字段需经 §2.2 只读审计后冻结；实现可复用现有字段或新增专用模型，但不得省略以下语义。字段值除被明确标为可空外，缺失保持未知，不能伪造默认成功值。

| 信息 | 最小语义 |
|---|---|
| 版本身份 | `session_id`、唯一 `version_id`、同一 Session 内版本/候选序号、`parent_version_id`；V1 无父编辑版本 |
| 业务边界 | Session owner、company、Thread 关联；继承并核验有效 Session，不让模型/客户端任意指定 owner |
| 字节来源 | 私有 `input_attachment_id` / `output_attachment_id`、`input_sha256` / `output_sha256`、文件类型/字节大小；哈希从实际 ORM 取得字节计算 |
| 指令关联 | 用户 `message_id` 或最小关联引用；不重复存完整 Prompt/Completion |
| 意图与授权关联 | `intent_effect_digest` 及确认收据 ID（如适用）；CB-02 仅存引用，不验证语义、不签发确认 |
| Provider 追踪 | 可获得的 Provider/model/request/response/tool/file ID、usage/cost estimate、起止时间、cleanup 状态；只存最小必要的非秘密元数据 |
| 验证 | Validator 结果等级、报告引用/摘要、验证完成时间；CB-02 不自行生成通过结论 |
| 生命周期 | version state、delivery state（由交付层回写/关联）、最后错误阶段/稳定错误码（如适用） |
| 并发 | Session 文档版本 revision 或等价乐观并发代号；与 Session/Proposal revision 分开 |

文件内容只能留在当前用户有权访问的私有 `ir.attachment` 或经批准的受控存储中。附件必须在实际写入后重新计算并比对 SHA；附件 ID、Provider file ID、文件名和模型回复都不是内容身份的替代证明。

不得在版本记录保存 API Key、Authorization/Cookie、完整提示词/模型回复、无关 Odoo 业务记录字段或任意模型生成代码。

### 4.1 验证证明与信任边界

验证证明必须绑定以下不可拆分字段：

| 绑定字段 | 校验要求 |
|---|---|
| Candidate Version ID | 必须与待接受的候选记录完全相同；不得将证明从另一候选复制 |
| Candidate Output SHA-256 | 接受时从绑定私有附件的实际 `raw` 字节重新计算，且与候选记录、证明和附件长度一致 |
| Validator Policy/Version | 使用受控发布版本标识；修改验证语义时必须更新。M1 与 CB-03 可有不同 policy/version |
| Validation Report ID | 报告的稳定 ID/摘要由受信任服务端验证调用生成，不接受调用方任意字符串作为证明 |
| Validation Result | 必须为 `VERIFIED`；`PARTIALLY_VERIFIED`、`FAILED`、`REJECTED` 均不得推进 |
| Session / Document Revision | 绑定 Session ID、当时 Session revision、独立 Document revision 及适用的 Proposal revision；接受前重新读取比较 |
| Parent / Input binding | 绑定 parent version ID、其输入附件和输入 SHA；接受时 parent 仍须为 current |

Odoo 18 信任边界：外部 JSON-RPC/RPC、LLM 工具参数、普通用户对 ORM `create/write` 的输入均是不可信输入。`readonly=True` 只影响界面，不是授权边界；禁止公共模型方法接收 `verified=True`、report ID 或验证 JSON 后直接推进状态。受理接口是由 CB-03/受信任 M1 服务在同一 Odoo Python 进程中直接调用的内部服务函数，参数为不可从 JSON-RPC 编码重建的服务端 `ValidationReceipt` 类型；该对象仅在验证调用完成后创建，绑定本次验证上下文。公共 `create/write/unlink` 必须拒绝直接设置验证字段、状态、current/last-valid 和 revision 指针。内部 ORM 操作仍以当前用户 `env` 执行 ACL、Record Rules 与字段访问校验，禁止 `sudo()`、superuser mode、直接 SQL 数据读写、用户可控 `env.context` 标志或布尔参数作为证明。

下划线私有方法和 Python 类型不是针对已安装恶意 Odoo addon 的安全边界；Odoo 服务器中已安装并执行的 addon 代码属于受信任部署代码。这里的安全目标是阻断用户/RPC/LLM 输入伪造及常规业务路径越权。代码评审与部署权限负责限制服务器代码变更。现有 `office.document.request` 的 `ContextVar` 是服务器进程局部内部变更保护，不能单独替代上述 proof 绑定。

`ValidationReceipt` 只能由受信任 M1 适配器/后续 CB-03 验证调用在验证完成后创建。报告 ID 可由服务端对规范化报告内容生成稳定 digest；policy/version 使用显式发布版本标识，验证语义变更时必须更新。现有 `office_verify` `PASS` 不可被 RPC 直接提交为通用 `VERIFIED`；受信任 M1 适配器须验证报告状态、输入/输出 digest、策略标识和调用来源后，才为 V1 创建绑定收据。

CB-02 的生产接口不暴露可供用户调用的 `record_validation(report_id, result)` RPC。只读状态查询可通过有 ACL 的服务入口提供。测试替身放在 `mymodules/office_engine_m2/tests/support/`，不由 `models/__init__.py`、`services/__init__.py` 或生产服务导入；它仅在 TransactionCase 中构造测试 receipt。不存在“生产接受任何测试证明”的开关或上下文标记。

## 5. 状态与原子指针不变量

### 5.1 版本状态

遵循 TDD V2.0.2 §5.2 的状态语义：`candidate_requested`、`awaiting_confirmation`、`provider_running`、`candidate_received`、`verifying`、`verified`、`partially_verified`、`rejected`、`failed`、`accepted_current`、`superseded`、`finalized`。实际持久化可使用稳定内部 enum/现有字段映射，但每个迁移必须在契约/ATR 中对应到上述语义；不能因为实现困难而合并掉“候选、验证、接受、正式化”边界。

服务端仅允许显式合法迁移。不得由 RPC/LLM 客户端直接写状态、指针或哈希。`partially_verified`、`failed`、`rejected`、`candidate_received`、`verifying` 或确认待处理的记录绝不能成为可供下一轮编辑或 Finalize 使用的 current。

### 5.2 current 与 last-valid

- `current_version_id` 表示下一次编辑读取的当前有效文件；`last_valid_version_id` 表示最近一次已验证且服务端接受的有效文件。正常接受一份新 `VERIFIED` 版本时，两者在同一事务中指向该版本。
- 登记、下载、验证中、确认等待、失败、拒绝、部分验证和附件发布失败均不得移动 current/last-valid。
- 接受前必须重新核对 Session、预期 parent、输入附件和输入 SHA、当前 document revision、候选实际附件及输出 SHA、Validator 的 `VERIFIED` 证明引用，并确认 parent 仍是当前有效版本。
- 旧 current 版本改为 `superseded` 不能删除或修改原字节；版本行和历史附件保持可审计、只读。
- Finalize 仅将正式化事实关联到已接受版本，默认最终文件 SHA 必须与接受版本一致；不得另造一个内容不同、却仍引用原版本的正式附件。
- 本 v0.2 建议首期只支持 V1→V2→V3…正向链、历史版本授权只读及 current/last-valid 原子推进；不支持用户主动切换历史版本、不重写父链、不自动恢复/重新激活旧确认。该建议与冻结 TDD V2.0.2 §5.4 明确要求的历史版本切换/恢复版本冲突；在正式修订 TDD 与 Implementation Plan 或按冻结 TDD 纳入恢复能力前，不得冻结本契约或编码。不得以本 CC 改写上游基线。

### 5.3 并发与幂等

- 新候选必须声明它实际读取的 parent version 与 document revision。若服务端当前值已经变化，拒绝提交为 current；保留诊断信息，不覆盖较新版本。
- 接受操作以单一事务完成：验证调用前置事实、写入受控状态迁移、标记旧 current superseded、更新 current/last-valid/revision。事务失败时指针保持原值。
- 候选必须有 Session 范围唯一的 `idempotency_key`。相同 key、parent、输入 SHA 与规范化请求摘要重放时返回既有候选/结果，不重复创建或推进；同一 key 对应不同 parent、输入 SHA 或输出 SHA 必须拒绝并保留冲突证据。不能用 `office.document.request.request_uuid` 替代此 key，因为它标识单次 M1 请求。
- 并发的两个候选即使父版本相同，也最多一个能在 parent/revision 条件满足时成为 current；另一个保留为非当前的 stale/failed 候选，不得自动重基或重放。
- 同一 Session 内 `(session_id, version_no)` 与 `(session_id, idempotency_key)` 必须由数据库唯一约束保护。接受依赖 Session 单行锁或等价条件更新；取得锁前先通过当前用户 ORM 检查访问，取得锁后通过 ORM 刷新重读 revision/指针，最后用 ORM 在同一事务写状态及指针。若使用 SQL，只能用于在 ACL 校验之后获取必要行锁，不能借此读写/绕过业务权限。两条并发事务须在隔离数据库以独立 cursor/connection 竞争验证。

## 6. 服务接口语义

以下为职责级契约，不要求照搬函数名；具体方法由实现前调用链审计和 CC 冻结确定。

| 逻辑操作 | 输入与前置条件 | 成功结果 | 拒绝/失败保证 |
|---|---|---|---|
| `register_initial_v1` | 已授权 Session；实际 M1 输出附件；权威初始验证通过引用；真实附件字节及 digest | 建立无父版本 V1，并在首次有效登记后设为 current/last-valid | 无验证证明、附件不属于会话、哈希不符或无权限时不登记 current |
| `register_candidate` | Session/current parent/revision、输入附件/hash、实际 Adapter 候选字节、请求关联和最小必要 metadata | 新候选状态记录，独立私有附件和 output hash；不推进指针 | 重复/不同哈希冲突、父版本陈旧、附件访问不符时安全拒绝 |
| `receive_validation_receipt`（仅进程内内部服务） | 候选、当前 ORM env、服务端 typed receipt；receipt 含 §4.1 全部绑定 | 经绑定及授权检查后登记验证事实；不提供 RPC/LLM 调用入口 | 缺失/类型错误/伪造字段、跨候选复用、SHA/Revision/parent 不符或非 `VERIFIED` 时拒绝 |
| `accept_verified_candidate`（同一受信服务事务内） | 已登记 receipt 的候选、parent/current/revision、附件真实字节 | 重新校验所有 proof 绑定与 ACL 后原子推进 current/last-valid 并 supersede 旧 current | 任何绑定失配、非 `VERIFIED`、并发冲突、附件变化或越权均不推进 |
| `record_finalize_reference` | CB-06 调用；目标必须是 current 且已接受版本；最终 attachment/hash 与接受版本相符 | 记录正式化版本及交付引用，不自行发布消息 | 版本过期、附件越权或字节/hash 不一致时拒绝登记正式化 |
| `get/list_version` | 当前用户有权读取该 Session 与相关版本/附件 | 返回允许消费的版本 metadata/受控附件引用 | 跨 owner/company/thread/session 的读取按不可读处理，不泄露是否存在或详情 |

版本服务结果区分 `created/candidate_recorded/accepted/blocked/failed/stale` 等服务端事实；不返回 Agent 的自然语言 `completed`，不把 `candidate_received` 当作 `verified`。

## 7. 权限、附件与数据完整性

1. 所有业务与附件读取/写入通过当前用户 Odoo ORM 环境及 ACL/Record Rules 执行；不得 `sudo()`、`env.su`、直接 SQL 数据读写、数据库驱动或其他权限旁路。为并发互斥而使用的行锁必须发生在 ORM 权限校验之后，锁后重读/变更仍经 ORM；若无法实现则阻断，不降低权限边界。
2. 每次请求校验当前用户、Session owner、Thread 关系、company、消息/附件来源和目标版本；不能因为可读源 Session 就推定所有版本附件都可读。
3. 输入和候选附件保持 `public=False`，附件 `res_model/res_id` 或等效关系必须绑定正确的私有版本/Session；严禁用公开链接代替访问授权。
4. 附件 create/read/write/unlink ACL 与记录规则需单独测试。新版本附件按 `res_model='office.workbook.version'`、`res_id=version.id`、`public=False` 绑定，并继承 Session owner/company 范围；用户可读取的元数据范围不得比其对所属 Session/attachment 的现有权限更宽。版本登记后附件字节与绑定不可变。当前 `ir_attachment.py` 未保护该新模型的附件，须在 §9 白名单内扩展保护；不得使用 `env.su` 作为普通服务写入/删除的开关。
5. SHA-256 对实际字节计算；空字节、大小超限、附件字节无法读取、digest 不匹配或附件版本被替换时，不接受版本。
6. Provider 元数据与外部传入的报告 ID/等级均为不可信输入；不以其 ID 决定 Odoo 访问权、current 指针、验证等级或用户确认状态。Validator receipt 必须从受信任同进程调用链直接到达内部接收函数。
7. 文件存储与元数据持久化失败时，不得留下 current 指针指向缺失/损坏附件；事务回滚或候选标为失败，旧有效版本保持可用。

## 8. 旧 Session 与迁移兼容

- 迁移采用加法策略：新表/字段/索引/访问规则必须可升级；不重写 Proposal JSON、Proposal history、旧 request、旧附件或 Session 状态历史。
- 未创建 Workbook Version 的旧 Session 继续按现有 M1/M2 初始 Mapping 流程读取/操作。不得只因旧 session 已有 `preview_attachment_id` 就自动标为 V1/`VERIFIED`。
- V1 仅在受信任 M1 调用链提供成功 readback 结果、实际输出附件、匹配 SHA、M1 validator policy/version 及 report ID/摘要时登记。当前 `office.document.request` 历史行仅保存 generated 状态与输出 SHA，readback 没有持久化；缺少报告与策略证明的旧 request、Session preview 和附件均维持 legacy，不自动回填、不推断 VERIFIED。
- 版本文档 revision 独立保存在 Session 的新增 `document_revision` 字段；现有 `revision` 与 `proposal_revision` 含义不变。Version row 保存创建时捕获的三类 revision（适用项）供校验/诊断，不能用 Proposal revision 替代 Document revision。
- 本 v0.2 提议不支持用户主动恢复旧版本、不重写父链、不自动恢复或重新激活旧确认；历史版本只读。此范围与 TDD V2.0.2 §5.4 的显式历史切换要求冲突，故是冻结 BLOCKER。上游变更获批前不得按此缩减范围；若负责人选择遵循 TDD，则需在 CB-02 加入经权限/哈希复核后创建明确 recovery version 或切换 current 的服务端语义，旧确认失效，且纳入专门测试。
- 新入口关闭或升级回退时，不删除新版本/附件或审计记录，不把新工作簿误认为旧 Proposal 文件，不覆盖既有 M1 路径。回退须关闭调用入口并保持历史只读；数据迁移真正回滚必须单独验证不会丢失或断开附件。
- 模块升级的可逆性、索引/字段降级及旧记录可读性在执行计划明确之前，不执行破坏性降级。

## 9. 候选文件与实施边界

以下是本次只读审计后建议的**明确实施白名单**。白名单不代表编码已授权；若实现证明还需其他文件，先修订/重审契约，不得自行扩展。

| 动作 | 路径 | 限定用途 |
|---|---|---|
| 新增 | `mymodules/office_engine_m2/models/office_workbook_version.py` | 新 `office.workbook.version` 模型、受保护字段、候选/有效状态与唯一约束；不含实际 XLSX Validator |
| 新增 | `mymodules/office_engine_m2/services/workbook_version_service.py` | 当前用户 ORM、M1 V1 收据适配、候选登记、typed receipt 接收、重验和原子接受/只读历史；无 RPC 可伪造 proof 的入口 |
| 修改 | `mymodules/office_engine_m2/models/office_mapping_session.py` | 增加独立 Document revision/current/last-valid 关系及受控原子迁移；保留 M1 Session/Proposal 语义 |
| 修改 | `mymodules/office_engine_m2/services/mapping_service.py` | Session 绑定、授权版本读取/列表的最小 service 接口；禁止 LLM 直接写状态/指针/proof |
| 修改 | `mymodules/office_engine_m2/services/render_bridge.py` | 在 M1 完成并拿到真实 readback/输出后，受控登记 V1；失败不得改变当前有效指针或原有 M1 返回语义 |
| 修改 | `mymodules/office_engine_odoo/models/office_document_request.py` | 仅持久化可用于 V1 证明的 M1 policy/version、readback report ID/digest/result；沿用当前用户 ACL、现有状态机和内部写入保护，不改变 Mapping 渲染语义 |
| 修改 | `mymodules/office_engine_odoo/models/ir_attachment.py` | 扩展对 `office.workbook.version` 绑定附件的不可变/私有保护；不得用 `env.su` 或 sudo 作为正常写入路径 |
| 修改 | `mymodules/office_engine_m2/models/__init__.py` | 注册新版本模型 |
| 修改 | `mymodules/office_engine_m2/services/__init__.py` | 注册受授权的版本服务调用方；不得导出 proof 接收/接受函数至任何 RPC/tool surface |
| 修改 | `mymodules/office_engine_m2/__manifest__.py` | 加载新版本 Record Rule XML；依赖不新增，继续依赖 `office_engine_odoo` |
| 修改 | `mymodules/office_engine_m2/security/ir.model.access.csv` | 新版本模型最小 ACL，实际读写仍受保护 service/CRUD 约束 |
| 新增 | `mymodules/office_engine_m2/security/office_workbook_version_rules.xml` | 限定 Session owner、company 和 Thread 继承范围 |
| 修改 | `mymodules/office_engine_m2/tests/__init__.py` | 只导入以下 Odoo TransactionCase；不导入生产模块中的 test validator |
| 新增 | `mymodules/office_engine_m2/tests/test_workbook_version_contract.py` | 中性 Python 契约、typed receipt 与幂等规则 |
| 新增 | `mymodules/office_engine_m2/tests/support/__init__.py`、`tests/support/validator_stub.py` | 测试专用 receipt 构造器；仅在测试目录，不注册、不被生产路径导入 |
| 新增 | `mymodules/office_engine_m2/tests/test_workbook_version_access.py` | Odoo TransactionCase；测试专用 Validator 替身、ACL/Record Rules、绑定、拒绝路径、回滚 |
| 新增 | `mymodules/office_engine_m2/tests/test_workbook_version_state.py` | Odoo TransactionCase；链、原子推进、revision、附件失败、失败等级和幂等 |
| 新增 | `mymodules/office_engine_m2/tests/integration/test_workbook_version_race.py` | 隔离测试数据库独立连接并发测试；不加入普通回滚 TransactionCase 作为并发通过证据 |
| 修改/新增 | `mymodules/office_engine_odoo/tests/test_office_document_request.py` | 如持久化 M1 V1 proof 元数据，验证只有内部 M1 验证流可写、返回/重试仍兼容；不改普通 Chat Completions |
| 修改/新增 | `mymodules/office_engine_m2/tests/test_render_bridge.py` | V1 登记挂接、失败不推进、重复 finalize 幂等及旧 Session 回归 |

明确禁止修改：Odoo 官方模块、CB-01 Adapter、`office_verify`/CB-03 实际 Validator、一般 Chat Completions 行为、`office_core` 编辑器、Canonical Operations、Provider/模型设置、无关 M2 工具/业务规则、manifest/ACL 之外的模块依赖及冻结上游文档。若版本证明无法在此白名单内安全完成，停止并申请契约变更。

## 10. 测试与验收矩阵

| 层级 | 必测范围 | 可得结论 |
|---|---|---|
| 静态/Schema/纯 Python Contract | 文件 SHA、唯一版本标识、父链无环、状态迁移、类型化 proof 结构、Revision/Effect 绑定、幂等键同载荷重放与异载荷冲突；中性数据，不使用业务模型/模板/坐标 | `Contract Verified`；不证明 Odoo ORM ACL/Record Rules |
| Odoo TransactionCase（仅测试 Validator 替身） | 真正 Odoo ORM 模型/附件、当前用户 ACL/Record Rules、私有绑定、字段写保护、proof 登记/重验/原子接受、事务回滚。Stub 仅在 tests 代码中产生可信类型 receipt，不被生产注册/导入 | `CB-02 Odoo Integration Verified`；证明版本服务受理边界与持久化，不代表真实 CB-03 Validator 已接入 |
| 防伪造与越权 | 直接 RPC/ORM create/write 设置 `verified`、accepted/current/last-valid、Document revision 或 proof 被拒；客户端布尔/JSON/仅 report ID 被拒；跨候选复用、SHA 修改、过期 Session/Document revision、错误 parent、非 VERIFIED 被拒；owner/company/Thread/Session 越权拒绝 | 只有具体实际执行的 TransactionCase 可报告通过；不凭方法名/只读 UI 属性推断安全 |
| 版本生命周期/故障 | M1 验证证据登记 V1；V1→V2→V3；附件保存失败、部分/失败/拒绝结果、旧确认或过期 revision 均不推进；事务回滚后 last-valid 可读；历史附件字节不可变；重复请求不重复有效版本；同键异 SHA 拒绝 | 只证明版本服务及 Odoo 状态行为；不得声称真实 Validator 文件效果已通过 |
| 数据库并发（隔离数据库） | 两个独立 Odoo cursor/connection 同时接受同 parent 不同候选，竞争同一 Session Document revision；恰一提交为 current，另一因 stale/约束失败；检查唯一约束与事务隔离后的实际指针 | 必须在 disposable/isolated Odoo test DB 运行；普通 `TransactionCase` 内顺序调用只算逻辑覆盖，不算并发安全证据 |
| 升级兼容与旧记录 | 在隔离 DB 执行模块升级；旧 Session、Proposal、request、附件仍可按原权限读取；无 proof 的历史产物维持 legacy，不能自动伪造 V1；回滚/升级失败时原数据仍可用 | 仅证明执行过的数据库版本与迁移行为，不等同生产发布 |
| Provider/Browser/CB-03 Validator | 不属于 CB-02。本 CC 不调用 Provider、不跑 UI，也不接入真实 CB-03 Validator；CB-01 证据仅证明 Adapter，不作为 V1/version-service acceptance evidence | `NOT RUN / OUT OF SCOPE`；CB-02 Final Accepted 不代表这些阶段完成 |

必须保留所有测试发现数、失败、skip 和日志。不要减少既有测试或降低断言。ORM 集成使用 Odoo TransactionCase 回滚并记录数据库环境；并发测试只能在独立 disposable test DB，禁止共享开发/生产库。模拟 Validator 不可写入生产包、manifest、ACL 或运行时 import 路径。

TransactionCase 必须逐项覆盖：

1. M1 输出由匹配的测试 proof 登记 V1，然后受控创建 V2、V3；三者附件真实字节、SHA、parent 与 revision 对应。
2. 同一 parent 的两个候选并发竞争 current，只接受一个；顺序模拟只覆盖 stale 逻辑，不可报告数据库并发通过。
3. 过期 Document revision、Session revision、parent/current 不匹配均拒绝接受。
4. 同一 idempotency key + 相同输入重放不重复生成有效版本；同 key + 不同 input/output SHA 必须拒绝。
5. Attachment create/write 失败时事务回滚且 current/last-valid 不变。
6. `PARTIALLY_VERIFIED`、`FAILED`、`REJECTED` 不能推进；跨 candidate 复用、仅 report ID、JSON proof、错误 validator policy/version 或输出 SHA 不匹配均拒绝。
7. 接受事务回滚后原 current/last-valid 仍可读；历史 version row 与 attachment 字节不可变。
8. 多用户、跨公司、跨 Thread、跨 Session 对版本 metadata/proof/attachment 的读写拒绝，且不泄露不可访问版本是否存在。

## 11. 状态、交付与关闭标准

- **`Contract Verified`**：纯 Python/schema 契约和服务端 proof 绑定规则通过；不等于 Odoo 集成完成。
- **`Integration Pending`**：Odoo TransactionCase、隔离数据库并发、附件/ACL、升级兼容等本 CC 自身证据尚未全部完成。
- **`Integration Blocked`**：权限、数据库/模块升级授权、SRS/数据策略或安全条件阻断；准确列出执行过的无副作用检查。
- **`Integration Failed`**：版本链错接、当前指针被失败候选推进、越权读写、附件/hash 不一致或兼容断言真实失败；保留证据。
- **`Final Accepted — CB-02 scope only`**：CB-02 合约、使用 tests-only Validator 替身的 TransactionCase、防伪造/权限、版本链/原子性、附件回读、隔离 DB 真实并发及旧 Session 兼容均有真实 PASS，IHR/ATR 完成并经负责人接受。它允许独立关闭 CB-02，但明确不宣称真实 CB-03 Validator 生产集成、CB-03 文件内容验证、Provider/Browser E2E 或生产发布完成。

CB-02 不要求人工 HVR，因为本 CC 不交付用户可见界面。版本选择/恢复如需 UI 属于另行授权范围；不因本契约包含服务层状态接口而默认实现 UI。当前历史恢复冲突仍按 §13 阻止冻结。

## 12. 失败、隔离与安全回退

1. 创建版本元数据/附件失败：事务回滚或标记候选失败；current/last-valid 保持不变，已接受附件不得删除/重写。
2. Validator 缺失、receipt 无效/伪造/不匹配、非 `VERIFIED`、父版本或 Session/Document revision 失配：不允许接受；不自动重跑编辑、不切换 parent、不清理历史有效版本。
3. 并发 revision 冲突：保留候选为非 current 的 stale/failed 诊断状态；必须由后续调用方重新向当前有效文件发起明确编辑，不静默重基。
4. 迁移或升级出错：停止后续升级/新版本流量，保留现有模型与附件；不使用 destructive downgrade 或删除版本数据作为回退。
5. 新入口关闭与数据回退分开处理：关闭新版本服务调用不意味着可以删除附件或回滚历史版本；若要回滚 schema，必须先有单独、验证过的数据保全/可逆迁移计划。
6. 任何路径都不得让失败/未验证候选进入 Preview/Finalize，也不得使服务端成功结果早于实际附件字节与状态事务完成。

## 13. 人工评审与冻结项

1. **BLOCKER — 历史版本恢复**：冻结 TDD V2.0.2 §5.4 要求可显式切换历史版本或创建恢复版本；本 CC 建议首期排除用户恢复。负责人必须选择：(A) 通过正式版本化 TDD 与 Implementation Plan 变更将恢复延期；或 (B) 保留冻结 TDD 并将受控恢复/恢复版本及确认失效测试纳入 CB-02。未决前本 v0.2 不可冻结/授权。
2. **OPEN — V1 可追溯证明**：当前 `office.document.request` 没有持久化 validator policy/version 与 report ID/readback；负责人审阅 §2.4/§8 的最小兼容保存字段，确认既有无证据记录维持 legacy。
3. **OPEN — 文件白名单**：确认 §9 新旧文件范围。若实际 Odoo 模型或测试加载方式需要额外文件，必须先修订契约；无默许扩展。
4. **OPEN — SRS/数据门禁**：Implementation Plan 的 SRS 变更与外部数据处理门禁仍独立于 CB-02 文档评审。仓库中检索到的冻结 SRS 版本不能单凭本 CC 判定 Candidate B 路线变更已正式完成；Coding Authorization 前需提供相应审批/版本证据。
5. 测试可信边界：认可 test-only Validator stub 仅用于证明 Odoo 版本服务如何受理 proof，不作为 CB-03 实际验证通过证据；CB-03 生产集成另行验收。
6. 审阅后若无阻塞，冻结本契约并另行签发 Coding Authorization；不得仅凭本草案或 CB-01 关闭决定开始编码。

## 14. 修订记录

| 版本 | 日期 | 修订 |
|---|---|---|
| v0.1 | 2026-11-06 | 初稿；依据冻结 TDD V2.0.2 与 Implementation Plan V2.0.1，等待人工评审。 |
| v0.2 | 2026-11-06 | 将 CB-02 与 CB-03 Validator 实际实现解耦；增加服务端 typed validation receipt、防伪造与 Odoo 信任边界、M1 V1 proof 持久性、完整现有模型差异审计、确定文件白名单及独立 DB 并发验收。历史版本恢复延期建议与冻结 TDD §5.4 冲突，明确保留为冻结 BLOCKER；状态 DRAFT — PENDING FINAL REVIEW。 |
