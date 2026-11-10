# CC-M2-CB-02 — Candidate Acceptance & Intent Binding Amendment

## 文档信息

| 项目 | 内容 |
|---|---|
| 修订对象 | `CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md` 及已接受的 v0.3.1 并发 Amendment |
| Amendment | Candidate 条件式接受、拒绝与每轮 Intent Binding |
| 版本 | v0.1 |
| 状态 | **DRAFT — NOT AUTHORIZED — NOT EFFECTIVE** |
| 关联契约 | TDD V2.0.3 Amendment Draft；Implementation Plan V2.0.2 Amendment Draft；CC-M2-CB-04 v0.2 FROZEN（implementation gates open） |
| 前置代码基线 | CB-02 Final Accepted — 技术范围；本 Amendment 不改写原接受记录 |
| 日期 | 2026-11-08 |

> 本稿是对 CB-02 v0.3/v0.3.1 的窄范围、版本化修订建议。只要未获负责人冻结并单独授权实施，它就不能改变当前已接受接口或运行行为。不得将本 Amendment 的草案内容视为已实现能力。

## 1. 目标

以最小扩展使 CB-02 支持 CC-04 的两个不变量：

1. 每个 Candidate 可追溯到本轮真实用户 Intent 消息，同时保留既有 `source_message_id` 的首始上传来源语义。
2. `VERIFIED` Candidate 只有在受信服务端给出的、与实际 Candidate Effect 相符的用户授权条件成立时才可成为 `accepted_current`；存在待业务决定时可保持非 Current；拒绝时不改变 Current、Last Valid 或 Document Revision。

本 Amendment 不重做版本服务、附件安全、Validator、确认解释、Tool Facade、UI、Provider 或 Finalize，不建立独立 Intent ORM 子系统或第二套 Current/Last Valid 指针。

## 2. 保留的 CB-02 v0.3 权威范围

以下均保持不变：

- `office.workbook.version` 是 Candidate/父子/附件/SHA/状态的权威模型；`office.mapping.session` 的 Current、Last Valid、Document Revision 仍由现有服务管理。
- 所有读写使用当前 Odoo ORM 环境，执行现有 ACL、Record Rules、company、Thread、Session 和 attachment 权限检查；不得 `sudo()`、SQL 数据写入或用客户端 context 绕过。
- CB-03 仍是唯一候选 Validator；typed `ValidationReceipt` 的实际 Candidate ID、输出 SHA、policy/report、Session/Proposal/Document revision、parent/input SHA、Effect digest 绑定维持不变。
- CB-02 仍负责原子接受、Current/Last Valid 与并发检查；拒绝不可移动指针；Candidate 附件私有且不可变；历史记录保留。
- `source_message_id` 继续表示 Session 原始上传来源，不重解释、不回填为逐轮编辑消息。

## 3. 最小模型修订

### 3.1 每轮 Intent Binding

在 `office.workbook.version` 增加：

| 字段 | 建议类型 | 语义 |
|---|---|---|
| `intent_message_id` | `Many2one('mail.message')`, readonly/copy=False/ondelete restrict | 此 Candidate 所属本轮用户 Intent 消息；由 Candidate 注册服务校验并绑定。每个 Candidate 一条；多个 Candidate 可引用同一 Intent 消息。 |

由服务层验证该消息存在、可由当前用户读取、位于版本所属 `llm.thread`、作者与 `env.uid` 对应当前用户匹配、Thread/Session/company 关联有效且消息在此次请求流程中。外部客户端提交的任意 message/user/thread/session ID 不可信。

在 `register_candidate` 的受控签名中增加 `intent_message_id` 或等价受限参数，由服务从当前用户环境核验。不能改变 `source_message_id=session.source_message_id`。Intent message id 不是 idempotency key：一个意图可以产生多个不同请求 Candidate；每次 Candidate 使用独立幂等键并以规范化 request/effect digest 防重。

### 3.2 接受授权事实

Acceptance 需要一次性、服务端内部使用的 typed authorization，不接受客户端 JSON、LLM 参数或任意 boolean。建议在现有版本服务内增加非 RPC 的不可变类型 `CandidateAcceptanceAuthorization`，字段至少绑定：

- `candidate_version_id`, `session_id`, `owner_id`, `thread_id`；
- `parent_version_id`, `document_revision`, Candidate 实际 output SHA-256；
- `intent_message_id`, 已规范化的 Intent/effect digest；
- 授权来源类型：`explicit_intent`、`confirmed_intent` 或 `candidate_review`；
- 作为授权依据的真实 `mail.message` 引用（明确请求、风险确认或候选 Accept 消息）；
- 实际验证 Receipt/Effect digest 与服务端授权范围 digest；
- 服务端生成的 decision/authorization idempotency reference。

该对象仅可在 Odoo Python 受控编排内部构造，不得通过 Agent Tool、XML-RPC/JSON-RPC、public model method、模型传入 `user_id`、`confirmed=True`、`force_override=True` 或 `env.context` 布尔标志输入。CB-02 接受服务仍须重新从 ORM 读取用户、Thread/Session、决策消息、Candidate/Receipt/实际附件字节及 revision，验证全部绑定与 ACL；typed 对象只提供受限接口类型，不替代实际权限/版本重验。

为保留可审计的授权来源，最小持久化优先复用版本行现有 `confirmation_receipt_id` 和 digest 字段；如复用后无法区分明确意图/已确认/候选 Accept，才增加以下只读字段：`acceptance_authorization_kind`、`acceptance_authorization_message_id`、`acceptance_authorization_digest`。不新增授权模型或全局 token framework。最终采用现有字段还是三个最小字段，应在编码前以代码审计确认并记录；不得把必要授权事实只存在易失内存中。

### 3.3 接受接口

将现有逻辑接口：

```python
accept_verified_candidate(env, candidate_id)
```

改为仅供内部服务调用的：

```python
accept_verified_candidate(env, candidate_id, authorization: CandidateAcceptanceAuthorization)
```

事务内必须重新验证：

1. Candidate 是当前 Session 中的编辑 Candidate，状态为 `verified`，并有当前有效且绑定准确的 CB-03 typed Receipt。
2. 实际 Candidate 附件字节、附件关联、SHA、文件大小和 MIME 与版本行、Receipt 一致。
3. Candidate parent 仍为 Session current，Session owner/thread/company/current user、Session/Proposal/Document revision 与授权记录一致。
4. 授权决策消息存在且当前用户可读；消息 Thread、作者、会话顺序与授权类型一致；服务端调用方已基于 CB-03 actual effect facts 判定其完全落在 Intent/Confirmation/Review 授权范围内。
5. Candidate effect/Intent digest 与授权 digest 相符；否则 stale/拒绝，当前指针不变。
6. 接受由现有锁和单一事务原子完成：状态/指针/revision 同步；并发败方 stale；同一 Candidate+同一授权幂等返回已接受版本，不重复推进 revision；Candidate/授权变化不得复用成功结果。

`VERIFIED` 本身不充分。CB-02 不负责自然语言解释或风险决策；它信任边界内的 CC-04 typed 决策服务，但仍独立校验数据库事实与字节/授权绑定。

### 3.4 拒绝接口与迁移

新增内部受控逻辑接口：

```python
reject_verified_candidate(env, candidate_id, decision: CandidateRejection)
```

要求：

- 只允许拒绝当前用户可读的同 Session `verified`、尚未 Current 的 Candidate；验证 Thread、owner、company、消息作者和 Candidate 实际绑定。
- 拒绝决定引用真实用户决策消息及 candidate/version/revision；重复同一拒绝幂等。
- `office.workbook.version` 最小状态转移增加 `verified → rejected`。不新增 `pending_review`；`verified && 非 current` 表示已验证且未接受，是否尚待 Review 由服务层返回，不另设全局状态。
- 拒绝仅修改 Candidate 的 terminal state/拒绝审计字段，不更新 Session current/last-valid/document revision，不改附件或 Receipt。
- 若 Candidate 已 stale（Current 已变），拒绝可在权限允许时作只影响候选的终结记录；绝不可回写/阻塞新的 Current。由服务端返回 stale/rejected 的准确事实。
- `candidate_received` 等未验证状态按既有失败处理；禁止将验证失败 Candidate 转成已拒绝后误报为用户业务拒绝。

## 4. 回退与兼容

- `source_message_id`、M1 `register_initial_v1`、现有版本 SHA/父链/并发、CB-03 Receipt schema 和 `record_finalize_reference` 不变。
- 旧 Session/旧 Candidate 不伪造 `intent_message_id` 或授权事实；它们按原兼容策略保持 legacy，不可借空字段自动进入新接受门。
- 部署回退须关闭新调用入口但保留已生成版本、Decision 绑定与附件审计，不删除/覆盖；DB schema rollback 必须先证明不丢失链接和已接受版本，不在本 Amendment 内执行破坏性迁移。
- M1 既有 Session 和 Finalize 行为继续由原流程处理；新 Candidate B 接受逻辑不得改变 M1 的确认/预览语义。

## 5. 组件验收要求

| ID | 场景 | 必要结果 |
|---|---|---|
| CB02-A01 | 合法本轮用户消息注册 Candidate | `intent_message_id` 对应真实当前 Thread/用户消息；source upload message 保持原字段语义。 |
| CB02-A02 | 伪造/跨用户/跨 Thread/跨 Session/公司消息引用 | Candidate 注册拒绝；不得泄露无权消息内容。 |
| CB02-A03 | 一个 Intent 创建多个 Candidate | 允许不同幂等键/请求；同键同 payload 幂等；同键不同 digest 拒绝。 |
| CB02-A04 | 低风险明确意图且实际 Effect digest 匹配的内部条件接受 | 只有可信 typed authorization 且所有 ORM/bytes/receipt/revision 检查通过时接受；客户端/Agent不能直接传该对象。 |
| CB02-A05 | 无授权、`VERIFIED` 单独传入、伪造 JSON/boolean/force/context | 接受拒绝；Current/Last Valid/Document Revision 不变。 |
| CB02-A06 | authorization message、Candidate SHA、parent、effect、revision 任一变化 | 拒绝/STALE；不推进。 |
| CB02-A07 | 有效风险确认覆盖 Candidate Effect | exact same authorized scope 可接受；确认失效或 Effect 越界拒绝。 |
| CB02-A08 | 已验证非当前 Candidate 用户拒绝 | 状态拒绝；当前指针、last-valid、document revision、附件 SHA 不变；拒绝 Candidate 不可作下轮 parent。 |
| CB02-A09 | 同 Candidate 重复接受/拒绝 | 返回既有相同决策；不重复递增 revision 或生成额外 Current。 |
| CB02-A10 | 两个 Candidate 竞争同 parent/revision | 复用已接受的双连接 race invariant；最多一个接受；另一个 stale；不出现双重 current。 |
| CB02-A11 | ACL/Record Rule/attachment/company 权限 | 当前用户环境被拒绝；不以 sudo/SQL 旁路。 |
| CB02-A12 | M1/旧 Session/现有附件兼容 | M1 Mapping/Proposal/Finalize 不回归；无 intent binding 的历史行保持 legacy，不被伪补为已授权 Candidate。 |

需要 Odoo TransactionCase/真实 ORM 环境验证权限、消息关系、事务与字段保护；纯 Python/Mock 不能作为 CB-02 Amendment Integration PASS。并发专项仅在执行授权中允许的开发数据库/环境运行，不能用顺序测试替代。

## 6. 建议最小文件白名单

以下只用于后续 CC-02 Amendment Coding Contract；本稿不授权修改：

- `mymodules/office_engine_m2/models/office_workbook_version.py`：增加 `intent_message_id`、必要授权审计字段和 verified→rejected 迁移；保持受控字段保护。
- `mymodules/office_engine_m2/services/workbook_version_service.py`：`register_candidate` 逐轮消息核验；带 typed authorization 的条件接受；只影响候选的拒绝接口；重验与幂等。
- `mymodules/office_engine_m2/tests/test_workbook_version_contract.py`、`test_workbook_version_access.py`、`test_workbook_version_state.py` 及必要的支持文件：增加上述合成 TransactionCase，不降低既有断言。
- 若权限/消息字段审计证明还需变更 `models/office_mapping_session.py`、ACL/Record Rule/XML、manifest 或 `models/__init__.py`，先提最小白名单修订；不改 `office_verify`/CB-03、不改 Provider、Thread Tool 或 M1 Mapping。
- 新建/更新 CC02 Amendment IHR/ATR/evidence 只在其后续授权实施阶段处理。

## 7. 关闭与授权门

本 Amendment 的冻结/生效须由负责人明确批准，保留 CC-02 v0.3/v0.3.1 历史。CB-02 amendment 编码、非生产数据库名、模块升级及 TransactionCase 范围必须获得单独的 Coding/Runtime Authorization；只批准 CC-04 不自动授权修改 CB-02 或数据库。

组件实现和 TransactionCase 满足 §5 后，才能给 CC-04 Coding Authorization 解除 CB-02 依赖门。本 Amendment 不授权真实 Provider、业务文件、Browser/UI、Finalize/Delivery、生产部署、服务重启或 Git 写操作。

