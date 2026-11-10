# CC-M2-CB-02 — Workbook Version & Artifact Service

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-02 — Workbook Version & Artifact Service |
| 版本 | v0.1 |
| 状态 | **DRAFT — NOT AUTHORIZED FOR EXECUTION** |
| 上游设计 | `docs/design/TDD_office_engine_m2_v2.0.2.md` — FROZEN |
| 上游计划 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` — FROZEN |
| 前置 CC | `CC-M2-CB-01` — Final Accepted by project owner on 2026-11-06 |
| 起草日期 | 2026-11-06 |

> 本文件是 CB-02 契约草案，不冻结、不授权编码、模块升级、数据库迁移或部署。冻结本契约与获得独立 Coding Authorization 是两个不同门禁。不得因 CB-01 已关闭而自动开始 CB-02。

## 1. 目标与验收边界

建立 Odoo 侧工作簿版本与文件制品的权威谱系，使首轮 M1 验证通过的文件可作为 V1，后续每个文件候选都能明确记录父版本、真实字节哈希、状态、验证引用和附件来源，并仅在服务端版本条件满足时原子推进当前有效版本。

本服务管理文件身份、来源和生命周期元数据；**不编辑工作簿内容，不调用 Provider，不替代 Validator，也不自行批准业务风险。** Session/Proposal revision、Provider Response ID 和 Workbook Version ID 是不同身份，不得互相代用。

本 CC 的完成只表示版本服务契约及其 Odoo 持久化行为通过。它不表示真实 Provider 编辑、多轮 LLM 行为、Preview/Finalize UI 或生产发布通过。

## 2. 权威依据、前置条件与冻结原则

### 2.1 架构依据

- TDD V2.0.2 §5.1–§5.4：父子版本链、版本状态、current/last-valid、不依赖聊天历史恢复文件、Finalize 引用已接受版本、失败候选不推进、历史恢复必须重验。
- TDD V2.0.2 §6：只有 `VERIFIED` 候选可被接受为 `accepted_current`；`PARTIALLY_VERIFIED`、`FAILED` 或未验证候选不得覆盖 last-valid 或进入 Finalize。
- TDD V2.0.2 §8.1：逻辑 `verify_and_accept` 由 Validator 与版本提交协作；CB-02 只提供版本服务能力，不实现该验证逻辑。
- Implementation Plan V2.0.1 §5、§11–§13：本 CC 负责版本/哈希/父链/current/last-valid、乐观并发、旧 Session/附件兼容及不破坏性迁移；CB-03 验证候选，CB-06 负责 Preview/Finalize/Delivery。
- CB-01 已真实验证 Adapter 能返回并下载合成 XLSX 候选，且独立回读通过；该证据只供候选输入接口参考，不将候选自动视为版本或已验证文件。

### 2.2 编码前置 Gate

编码授权签发前必须满足：

1. 项目负责人已批准适用于 Candidate B 后续文件编辑的版本化 SRS 变更。TDD 和 Implementation Plan 不替代该变更。
2. 负责人单独冻结 CB-02 契约并签发 Coding Authorization；本 v0.1 草案本身不具备该效力。
3. 开工时只读审计当前 `office_mapping_session`、`office.document.request`、`ir.attachment`、访问规则、消息关联和已有 SHA/状态字段的真实调用链；形成复用/新增字段/新模型的差异表。若要改变本契约语义，先提交契约修订，不由编码者自行决定。
4. 记录 branch、HEAD、工作区状态、Odoo/Addons/Python 依赖和相关测试基线。不得清理、覆盖、暂存或提交既有用户修改。
5. 确认本次迁移涉及的模块及其数据安全、附件留存、恢复和维护窗口；不得读取或写入超出已批准范围的数据。

### 2.3 当前实现的只读对照证据

- `mymodules/office_engine_m2/models/office_mapping_session.py` 已有 `source_attachment_id`、`preview_attachment_id`、Session `revision`、`proposal_revision` 及模板/数据指纹等首轮 Mapping 状态；这些字段表达 Session/Proposal/Preview 生命周期，当前未见贯穿 V1→Vn 的独立 Workbook Version 父链与 current/last-valid 指针。
- `mymodules/office_engine_odoo/models/office_document_request.py` 的 `office.document.request` 已记录一次文档请求、输入/输出附件、状态及 input/output SHA，并以 `request_uuid` 保证 request 身份；它不能仅凭现有定义代表多轮 Session 内的父子版本、候选与有效指针。
- `mymodules/office_engine_m2/services/mapping_service.py` 读取 Session/Preview 与既有文档请求附件；该路径是复用审计对象，不代表已存在本 CC 的版本服务。

以上只读检查足以确认需要补充版本谱系的设计缺口，但不足以决定应复用哪些具体字段、是否新建模型、附件记录规则如何调整，或升级清单有哪些。实现前必须完成该差异审计；本草案不预先冻结数据库模型方案。

## 3. 职责边界

### 3.1 范围内

- 为已经通过适用初始文件验证的 M1 输出登记 V1；不根据“存在预览附件”推定验证通过。
- 登记 Responses Adapter 下载后的真实候选附件及其父版本、输入/输出 SHA-256、调用关联和不可信 Provider 元数据。
- 维护 Session 内的版本编号/父链、候选及接受状态、current/last-valid 指针、乐观并发 revision、私有附件绑定和只读历史查询。
- 仅接受来自权威 Validator 的 `VERIFIED` 结果引用，并在事务及父版本仍为 current 的条件下原子接受候选。
- 记录 Finalize 对已接受版本的引用及交付关联元数据；正式文件发布和消息交付由 CB-06 执行。
- 通过当前用户 ORM 环境执行版本/附件读取授权；维护 owner、Thread、Session 和 company 边界。
- 以加法方式保存新版本谱系；旧 Session、Proposal、Preview、request 和 attachment 保持原读写语义。

### 3.2 范围外

- XLSX/DOCX 编辑、格式转换、公式计算、Provider API/Code Interpreter 调用。
- 用户自然语言意图、风险分类、确认授权或 Confirmation Gate；属于 CB-04。
- 文件内容、Effect、结构或支持矩阵验证；属于 CB-03。CB-02 不提供可绕过 CB-03 的 `accept` 入口。
- Data Tool JSON Refresh；属于 CB-05。
- Preview UI、Finalize 执行、Thread 消息发布、浏览器附件展示和下载；属于 CB-06。
- 删除或重写旧 Session/Proposal/附件历史；破坏性迁移。
- 将 Proposal revision、Session revision、`office.document.request` UUID 或 Provider Response ID 冒充版本号。
- 生产发布、旧记录全量自动回填、隐式恢复历史版本、Candidate C 或新的全局状态框架。

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
- CB-02 首期只提供历史版本的授权读取；恢复/切换版本必须是明确操作并使旧确认失效。若 TDD §5.4 的具体恢复写法需要改变父链，必须在冻结前由负责人裁定，不得在实现时静默选择。

### 5.3 并发与幂等

- 新候选必须声明它实际读取的 parent version 与 document revision。若服务端当前值已经变化，拒绝提交为 current；保留诊断信息，不覆盖较新版本。
- 接受操作以单一事务完成：验证调用前置事实、写入受控状态迁移、标记旧 current superseded、更新 current/last-valid/revision。事务失败时指针保持原值。
- 相同候选登记请求的安全重放不得产生第二份有效版本或重复推进；同一请求标识若关联不同输入/输出哈希必须拒绝。具体幂等键优先复用现有 request/correlation 标识；若现有标识不满足，必须在只读审计差异表提出最小字段，经契约冻结后实施。
- 并发的两个候选即使父版本相同，也最多一个能在 parent/revision 条件满足时成为 current；另一个保留为非当前的 stale/failed 候选，不得自动重基或重放。

## 6. 服务接口语义

以下为职责级契约，不要求照搬函数名；具体方法由实现前调用链审计和 CC 冻结确定。

| 逻辑操作 | 输入与前置条件 | 成功结果 | 拒绝/失败保证 |
|---|---|---|---|
| `register_initial_v1` | 已授权 Session；实际 M1 输出附件；权威初始验证通过引用；真实附件字节及 digest | 建立无父版本 V1，并在首次有效登记后设为 current/last-valid | 无验证证明、附件不属于会话、哈希不符或无权限时不登记 current |
| `register_candidate` | Session/current parent/revision、输入附件/hash、实际 Adapter 候选字节、请求关联和最小必要 metadata | 新候选状态记录，独立私有附件和 output hash；不推进指针 | 重复/不同哈希冲突、父版本陈旧、附件访问不符时安全拒绝 |
| `record_validation` | 候选 ID、预期 parent/revision、CB-03 权威验证报告引用与结果等级 | 记录验证状态及报告摘要 | CB-02 不自行将未提供的验证结果推断为通过 |
| `accept_verified_candidate` | 状态为 `verified` 的候选、权威验证通过引用、parent/current/revision 和附件哈希均匹配 | 原子推进 current/last-valid 并 supersede 旧 current | `PARTIALLY_VERIFIED`/`FAILED`、并发冲突、哈希错链或越权时不推进 |
| `record_finalize_reference` | CB-06 调用；目标必须是 current 且已接受版本；最终 attachment/hash 与接受版本相符 | 记录正式化版本及交付引用，不自行发布消息 | 版本过期、附件越权或字节/hash 不一致时拒绝登记正式化 |
| `get/list_version` | 当前用户有权读取该 Session 与相关版本/附件 | 返回允许消费的版本 metadata/受控附件引用 | 跨 owner/company/thread/session 的读取按不可读处理，不泄露是否存在或详情 |

版本服务结果区分 `created/candidate_recorded/accepted/blocked/failed/stale` 等服务端事实；不返回 Agent 的自然语言 `completed`，不把 `candidate_received` 当作 `verified`。

## 7. 权限、附件与数据完整性

1. 所有业务与附件读取/写入通过当前用户的 Odoo ORM 环境和现有 ACL/Record Rules 执行；不得 `sudo()`、SQL/cursor、数据库驱动或其他旁路绕过权限。若当前模型/附件规则无法安全表达本契约，先阻断并提出差异，不开放公共 URL。
2. 每次请求校验当前用户、Session owner、Thread 关系、company、消息/附件来源和目标版本；不能因为可读源 Session 就推定所有版本附件都可读。
3. 输入和候选附件保持 `public=False`，附件 `res_model/res_id` 或等效关系必须绑定正确的私有版本/Session；严禁用公开链接代替访问授权。
4. 附件 create/read/write/unlink ACL 与记录规则需单独测试。用户可读取的元数据范围不得比其对所属 Session/attachment 的现有权限更宽。
5. SHA-256 对实际字节计算；空字节、大小超限、附件字节无法读取、digest 不匹配或附件版本被替换时，不接受版本。
6. Provider 元数据作为不可信输入，不用其 ID 决定 Odoo 访问权、current 指针、验证等级或用户确认状态。
7. 文件存储与元数据持久化失败时，不得留下 current 指针指向缺失/损坏附件；事务回滚或候选标为失败，旧有效版本保持可用。

## 8. 旧 Session 与迁移兼容

- 迁移采用加法策略：新表/字段/索引/访问规则必须可升级；不重写 Proposal JSON、Proposal history、旧 request、旧附件或 Session 状态历史。
- 未创建 Workbook Version 的旧 Session 继续按现有 M1/M2 初始 Mapping 流程读取/操作。不得只因旧 session 已有 `preview_attachment_id` 就自动标为 V1/`VERIFIED`。
- 只有能证明文件字节、归属、SHA 及原有独立验证事实的旧产物，才能在显式且经授权的兼容路径中登记版本。无法证明的记录维持 legacy 状态，标记不具备版本谱系，不猜测补齐。
- 新入口关闭或升级回退时，不删除新版本/附件或审计记录，不把新工作簿误认为旧 Proposal 文件，不覆盖既有 M1 路径。回退须关闭调用入口并保持历史只读；数据迁移真正回滚必须单独验证不会丢失或断开附件。
- 模块升级的可逆性、索引/字段降级及旧记录可读性在执行计划明确之前，不执行破坏性降级。

## 9. 候选文件与实施边界

以下为只读核查后的候选影响面，不是编码白名单的最终冻结版；签发 Coding Authorization 前，必须根据代码调用方、manifest、安全 CSV/XML、Addon 依赖和实际升级路径把文件清单收敛到确切集合。

| 候选动作 | 路径 | 限制 |
|---|---|---|
| 新增（首选，待审计） | `mymodules/office_engine_m2/models/office_workbook_version.py` | 仅版本/制品元数据模型；无 Provider、XLSX 编辑或业务模型特例 |
| 新增（首选，待审计） | `mymodules/office_engine_m2/services/workbook_version_service.py` | 版本服务；当前用户 ORM、哈希/父链、状态、并发和权限门 |
| 修改（如新模型） | `mymodules/office_engine_m2/models/__init__.py`、Addon manifest、security ACL/record rules | 仅注册该服务和最小私有权限；须有权限测试和审计证据 |
| 修改（经审计必需时） | `mymodules/office_engine_m2/models/office_mapping_session.py`、`services/mapping_service.py` | 最小绑定/接口协作；不得合并 Proposal revision 与 Workbook version |
| 修改（经依赖证明必需时） | `mymodules/office_engine_odoo/models/office_document_request.py` | 仅为请求/附件谱系引用，不重写既有 M1 请求/保存行为；须先修订最终白名单 |
| 新增测试 | `mymodules/office_engine_m2/tests/test_workbook_version_contract.py`、`test_workbook_version_access.py` | 纯 Python contract 与 Odoo TransactionCase 分开；必要时命名按仓库惯例调整 |
| 执行后文档/证据 | `docs/implementation/IHR-M2-CB-02.md`、`ATR-M2-CB-02.md`、专用 evidence 目录 | 保留原始日志/历史失败；不记录 secret 或不必要业务数据 |

明确禁止修改：Odoo 官方模块、CB-01 Adapter、一般 Chat Completions 实现、office_core 编辑器、Canonical Operations、Provider/模型设置、无关 M2 工具/业务规则或冻结上游文档。

## 10. 测试与验收矩阵

| 层级 | 必测范围 | 可得结论 |
|---|---|---|
| 静态/Schema/纯 Python Contract | 文件 SHA、唯一版本标识、父链/无环、会话内序号、不可变字节身份、状态迁移纯函数、重复候选幂等；中性合成字节，不使用固定业务模型/模板/坐标 | `Contract Verified`；不证明 ORM ACL/Record Rules |
| Odoo TransactionCase | 当前用户、跨用户/公司/Thread/session 访问拒绝；源/候选 attachment 归属与 private；无权限的附件不能通过 Version Service 泄露；无 `sudo()` 依赖 | 仅证明实际执行到的 ORM 权限边界，不外推成 Browser |
| Session/Version Integration | 首轮 M1 已验证文件登记 V1；V1→V2 父链与实际 SHA；失败/部分验证不推进；`VERIFIED` 接受原子推进；父 revision 冲突拒绝；重复 request 不重复有效版本；Finalize 只引用 current 已接受版本 | `Integration Passed` 仅限执行的 Odoo 模块/迁移/模型行为 |
| 升级兼容 | 升级前后旧 Session、Proposal、request、附件仍可由原权限路径读取；不自动伪造 V1；数据迁移失败时旧功能保持可用 | 版本数据迁移与兼容层 PASS，不等同生产发布 |
| 文件回读 | 由 CB-01/合成夹具产生的 bytes 保存至附件后再读回；计算 SHA 与原始输入/候选相同；验证附件文件大小与二进制一致 | 只证明储存/版本身份一致，不证明内容正确（由 CB-03） |
| Provider/Browser | CB-02 不执行 Provider 或 UI 流程；复用 CB-01 已接受的真实 Provider 证据；CB-06/CB-07 承担其各自验收 | `NOT APPLICABLE` 于 CB-02；不得将 CB-01 证据误标为 Version Service E2E |

必须保留所有测试发现数、失败、skip 和日志。不要减少既有测试或降低断言。DB/ORM 集成使用 Odoo TransactionCase 回滚并在报告中记录数据库环境；不得操作生产/共享业务数据来构造通过证据。

## 11. 状态、交付与关闭标准

- **`Contract Verified`**：本契约声明的纯 Python/静态契约与允许的版本服务测试通过。
- **`Integration Pending`**：Odoo 当前用户访问、附件权限、迁移/旧记录兼容或版本状态的实际集成测试尚未完成。
- **`Integration Blocked`**：权限、数据库/模块升级授权、SRS/数据策略或安全条件阻断；准确列出执行过的无副作用检查。
- **`Integration Failed`**：版本链错接、当前指针被失败候选推进、越权读写、附件/hash 不一致或兼容断言真实失败；保留证据。
- **`Final Accepted`**：合同测试、TransactionCase、迁移/旧记录兼容和适用附件回读证据均真实通过，IHR/ATR 完成并经负责人接受。只关闭 CB-02，不批准生产发布或其他 CC。

CB-02 不要求人工 HVR，因为本 CC 不交付用户可见界面；若实施期间引入任何版本选择/恢复 UI，须先变更契约并定义单独人工验收。

## 12. 失败、隔离与安全回退

1. 创建版本元数据/附件失败：事务回滚或标记候选失败；current/last-valid 保持不变。
2. Validator 缺失、非 `VERIFIED`、父版本或 revision 失配：不允许接受；不自动重跑编辑、不切换 parent、不清理历史有效版本。
3. 并发 revision 冲突：保留候选为非 current 的 stale/failed 诊断状态；必须由后续调用方重新向当前有效文件发起明确编辑，不静默重基。
4. 迁移或升级出错：停止后续升级/新版本流量，保留现有模型与附件；不使用 destructive downgrade 或删除版本数据作为回退。
5. 新入口关闭与数据回退分开处理：关闭新版本服务调用不意味着可以删除附件或回滚历史版本；若要回滚 schema，必须先有单独、验证过的数据保全/可逆迁移计划。
6. 任何路径都不得让失败/未验证候选进入 Preview/Finalize，也不得使服务端成功结果早于实际附件字节与状态事务完成。

## 13. 人工评审与冻结项

1. 确认 SRS Candidate B 路线变更已正式生效，且 CB-01 `Final Accepted` 不代表生产激活。
2. 审阅只读代码差异表：复用 `office_mapping_session` / `office.document.request` 现有字段还是新增 `office.workbook.version` 模型；需覆盖的 Addon 及文件白名单。
3. 裁定 TDD §5.4 历史版本恢复的首期语义，以及恢复后父链、current/last-valid 与确认失效如何保持一致；若本 CC 暂不实现恢复，应在冻结版明确延期归属。
4. 确认 CB-02 是否只建立 `VERIFIED` 结果的可接受接口，由 CB-03 负责发送权威结果；不得让 CB-02 自己验证文档。
5. 确认迁移中旧有 preview/request/attachment 哪些能够证明为 M1 验证通过的 V1；不可证明项保持 legacy，不自动回填。
6. 批准后冻结本契约并另行签发 Coding Authorization；不得仅凭此草案或 CB-01 关闭决定开始编码。

## 14. 修订记录

| 版本 | 日期 | 修订 |
|---|---|---|
| v0.1 | 2026-11-06 | 初稿；依据冻结 TDD V2.0.2 与 Implementation Plan V2.0.1，等待人工评审。 |
