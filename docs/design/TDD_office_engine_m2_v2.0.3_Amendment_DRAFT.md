# Office Engine M2 TDD V2.0.3 — Amendment Proposal

## 文档信息

| 项目 | 内容 |
|---|---|
| 文档 | TDD Office Engine M2 — 条件式 Candidate 接受与用户授权 |
| 修订版本 | V2.0.3 Amendment Proposal |
| 状态 | **DRAFT — NOT AUTHORIZED — NOT EFFECTIVE** |
| 基线 | `docs/design/TDD_office_engine_m2_v2.0.2.md` — FROZEN；保留不覆盖 |
| 关联契约 | 冻结 CC-M2-CB-04 v0.2；待批准的 CC-M2-CB-02 接受/Intent Amendment |
| 日期 | 2026-11-08 |

> 本文件仅提出对冻结 TDD V2.0.2 的最小版本化修订。只有负责人批准并将其并入新的完整 TDD 版本后才生效。它不授权编码、测试、Provider 外发或发布。

## 1. 目的与范围

落实人类最终业务决策权及 CC-M2-CB-04 D-01/D-07：已验证 Candidate 仅在服务端能证明原始明确授权或有效确认覆盖实际 Effect 时才自动接受；需要业务选择的 Candidate 保持非 Current，交由 CB-06 展示并收集 Accept/Reject/Revise。保持 CB-03 Validator 的既有验证深度、`VERIFIED` 定义和文件安全约束不变。

本 Amendment 不修改首轮 M1 Mapping、Provider Adapter、Validator 规则/Expected Effect、Odoo 权限、版本哈希、父链、并发锁、Data Tool、CB-06 UI 实现或 SRS。真实 Provider/真实业务数据外发仍受 SRS 和数据政策独立门禁约束。

## 2. 核心不变量

1. `VERIFIED` 只表示冻结 CB-03/TDD §6.3 定义的文件与结构化 Effect 验证结果；它既不是用户授权，也不等于 `ACCEPTED`。
2. `ACCEPTED` 是 CB-02 依据有效授权及实际 Candidate 绑定，通过原子服务调用推进到 `accepted_current` 的版本事实。
3. `DELIVERED` 是 CB-06 对正式附件/消息/下载的独立事实；`ACCEPTED` 不等于 `DELIVERED`。
4. 明确低风险用户请求可授权自动接受，但仅在 CB-03 为 `VERIFIED`、实际 Effect 与服务端绑定的授权范围完全相符、父版本和 revision 仍有效且没有待处理业务裁决时。
5. 需要确认的风险只有在实际 Effect 完全被确认范围覆盖时才可使用同一确认接受；确认提示应说明其是否允许“效果匹配后成为当前版本”，避免重复询问。
6. 未被原始/确认授权覆盖、Effect 存在实质歧义、需要人类判断或无法证明匹配时，Candidate 保持非 Current，CB-06 交由人类决策。
7. `PARTIALLY_VERIFIED`、`FAILED`、权限/安全失败和不支持结构不能通过确认、用户 Accept、模型声明或 `force_override` 变成可接受 Candidate。
8. 拒绝 Candidate 不改变 Current、Last Valid 或 Document Revision；旧确认不复用。

## 3. 拟替换/澄清条款

### 3.1 §5.2 状态语义（替换关于 `verified` 自动成为 current 的歧义）

保留 TDD 已列状态集合。补充如下解释：

- `verified` 表示 Candidate 已满足验证策略，可处于非 Current 状态等待授权评估或业务决定。
- `accepted_current` 只由 CB-02 服务端接受操作产生。
- `verified` Candidate 可按已绑定的授权条件式接受；若授权不覆盖实际 Effect，则保持 `verified` 且非 Current，交由 CB-06 Review。
- `rejected` 由受控拒绝操作登记；拒绝不得修改 current/last-valid/document revision。
- 不要求新增 `pending_review` 状态。若后续真实实现证明 `verified + 非 current + 当前父版本仍有效` 无法可靠表示待决 Candidate，才提交独立版本化修订，不由实现者自行增加状态。

推荐生命周期：

```text
candidate_received → verifying → verified
verified + matching explicit/confirmed authorization → accepted_current
verified + unresolved business decision → remain verified/non-current → CB-06 review
verified/non-current + user rejection → rejected
partially_verified / failed / stale → never accepted_current
accepted_current → CB-06 finalize/delivery lifecycle
```

### 3.2 §6.3 验证等级与接受判据（替换 `VERIFIED` 的自动提交规则）

保持原 §6.3 的 `VERIFIED`、`PARTIALLY_VERIFIED`、`FAILED` 验证含义及能力矩阵。将版本/交付列修订为：

| 验证等级 | 判定（不变） | 修订后的接受/交付规则 |
|---|---|---|
| `VERIFIED` | 文件安全/完整性、绑定、声明的结构化 Effect、实际范围及支持策略均通过独立验证；不表示完整自然语言意图已被证明 | **具备接受资格，不自动接受。** CB-02 只有收到受信任的条件式接受依据，且重验授权/用户/Thread/Session/Candidate/parent/bytes SHA/revision/实际 Effect 后才可原子设为 `accepted_current`。没有匹配授权或仍需业务裁决时保留为非 Current 候选，并交 CB-06。接受后方可按 CB-06 规则预览正式流程。 |
| `PARTIALLY_VERIFIED` | 原定义不变 | 不得接受为 Current、不得 Finalize/正常交付；是否有隔离诊断视图仍由产品另行决定。 |
| `FAILED` | 原定义不变 | 拒绝候选；不接受、不交付；Current/Last Valid 不变。 |

条件式接受是 CB-02 原子接受 API 的授权前置，并不是 CB-03 新的 Validator 结果等级，也不允许 `VERIFIED` 覆盖任何安全失败。

### 3.3 §6.4 Outcome、Candidate、Current 与交付（补充）

操作结果、验证等级、版本状态、artifact 状态和 delivery 状态是独立维度。补充：

- `candidate_received`：Provider 已返回并由 CB-02 登记真实字节；不是验证或接受。
- `verified`：验证通过；仍可能不是 Current。
- `accepted_current`：CB-02 条件式接受已完成。
- Preview/Review 可以引用私有非当前 Candidate；此类 Review artifact 不表示 Accepted、last-valid 或可正式 Finalize。
- 对外 `completed` 必须限定为实际已完成的阶段；只有 Accepted 才可声明版本已成为 Current，只有 CB-06 有正式交付证据才能声明已交付/可下载。
- Review/Accept/Reject/Revise 属于 CB-06 用户交互；条件判定和服务端接受请求由 CB-04 编排、CB-02 持久化。

### 3.4 §8.1 逻辑接口（拆分验证和接受）

将逻辑 `verify_and_accept(candidate, parent_version, expected_effect)` 分成两个有独立结果的逻辑动作：

| 逻辑动作 | 输入 | 返回与边界 |
|---|---|---|
| `validate_candidate(candidate, parent_version, expected_effect)` | 候选、父版本、只读 Expected Effect、实际附件/版本绑定 | CB-03 返回 Validator Result、Risk Facts、typed Receipt。该操作不推进 Current、不表示授权或完成。 |
| `accept_candidate(candidate, authorization)` | `VERIFIED` Candidate、CB-03 Receipt、当前父版本/revision、由 CB-04 内部产生且绑定用户决策/Intent/Effect 的 typed authorization | CB-02 重验实际附件字节/哈希、Receipt、current parent、revision、ACL 和授权绑定后原子推进；拒绝/失效时不改变 current/last-valid。任何 Odoo RPC/LLM 客户端不能直接提交可信授权对象。 |
| `reject_candidate(candidate, decision)` | 当前用户对明确 Candidate 的拒绝事实及现有版本绑定 | CB-02 受控拒绝；不推进指针，不重写历史附件。 |
| `finalize(accepted_current, delivery_authorization)` | 已接受 Candidate 及当前用户/业务流程要求 | CB-06 创建/关联正式附件并记录独立 delivery 结果；失败不撤销版本接受或伪报交付。 |

`expected_effect` 继续按 v2.0.2 §8.1 定义为只读的结构化目标、条件及允许影响范围，不演化为 Excel 编辑 DSL。

### 3.5 §4.2 Confirmation 与 Accept 不重复

补充条件式接受授权规则：

- 对用户明确、低风险且可验证的操作，原始请求可作为该精确操作的授权；实际 Effect 完全匹配后不再请求重复确认/Accept。
- 对需预先确认的业务风险，确认范围与确认提示需明确说明若实际 Effect 完全匹配，是否允许 Candidate 成为 Current。确认只覆盖该范围，实际 Effect 超范围或无法验证时不得自动接受。
- 若确认只授权尝试编辑而未授权接受，或 Candidate 结果需要人类审查，CB-04 保留候选并由 CB-06 请求一次基于实际 Candidate 的决策。
- 用户确认、用户 Accept 均不能绕过 ACL、Record Rules、公司隔离、附件/文件安全、资源限制、版本绑定和 Validator 失败。

## 4. 兼容与迁移

- M1 首轮填充和既有 Mapping/Proposal/Finalize 行为不变。
- CB-01 Adapter、CB-03 Validator/Receipt 和 CB-02 附件/SHA/父链/并发不变量继续由原组件负责。
- CB-02 的最小接受/拒绝及 Intent 绑定协议由独立 CC-02 Amendment 冻结并实施；TDD 本 Amendment 不替代该组件契约。
- CB-06 对 Accepted 文件的 Preview/Finalize/Delivery 继续存在，并新增对 Verified 非当前 Candidate 的私有 Review handoff；不把 Review artifact 当正式输出。
- M2-BASIC-EDIT 仍以真实候选内容验证、接受、预览和下载验收；如果授权/Effect 不匹配，则不自动接受，并如实进入 Review/澄清路径。
- 迁移期间旧状态/附件不通过模型声明补标为 Verified/Accepted；按原有兼容政策处理。

## 5. 必要验证

后续 CC 测试至少证明：匹配的明确授权自动接受且不重复询问；已确认 Effect 匹配时按确认规则接受；越界/不明 Effect 保持非当前；`PARTIALLY_VERIFIED`/`FAILED` 不接受；用户拒绝不改变 Current/Last Valid/Document Revision；旧授权在 parent/SHA/revision/Intent/Effect 变化后失效；CB-02 并发/幂等/权限不变量保持；`VERIFIED`、`ACCEPTED`、`DELIVERED` 对外状态不混淆。

Mock/合成数据和 Odoo TransactionCase 的结果不代表真实 Provider、Browser、生产外发或 Release Gate 通过。

## 6. 生效和限制

本稿批准前，冻结 TDD V2.0.2 仍为权威基线。批准后应并入保留历史的完整 TDD V2.0.3 或正式发布的后续版本，记录逐条变更；不能仅凭本 Amendment 文件名或 CC-04 冻结状态推定已生效。无需改动 SRS 冻结文件；真实 Provider 外发仍需 SRS/数据处理路线正式对齐。

本稿不授权编码、TransactionCase、模块升级、Provider 请求、真实文件外发、服务重启或生产发布。

