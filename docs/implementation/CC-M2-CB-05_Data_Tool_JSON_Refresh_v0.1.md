# CC-M2-CB-05 — Data Tool JSON Refresh

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-05 — Data Tool JSON Refresh |
| 版本 | v0.1 |
| 状态 | **DRAFT — NOT AUTHORIZED** |
| 权威技术设计 | `docs/design/TDD_office_engine_m2_v2.0.3.md` — FROZEN |
| 实施计划 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.2.md` — FROZEN |
| 上游需求 | `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` — FROZEN |
| DDD | TDD 记录为 N/A；未发现独立冻结的 Office Engine DDD |
| 依赖 | CB-02 Workbook Version/Current identity；CB-04 Intent/authorized query boundary；CB-01/CB-03 仅参与后续文件编辑链，不是 Data Tool 查询实现的直接依赖 |
| 起草日期 | 2026-11-10 |

> 本文件是实施契约草案，不授权编码、数据库变更、模块升级、真实业务数据读取、Provider 外发或生产发布。CC-04 按负责人当前决定保持 `Implementation Complete / HVR Pending`；CC-04 人工验证在本任务中暂停。本契约不重新启动或关闭 CC-04。

## 1. Contract Goal

用户明确要求补充或刷新 Odoo 数据时，系统通过当前登录用户的 ORM 权限查询所请求的数据，返回范围明确、类型保真、完整性可判定的 JSON 快照，供 LLM 理解并应用到当前有效工作簿。

Data Tool 只读取 Odoo 并返回数据。它不选择工作表、行或单元格，不生成 Excel 编辑指令，不写入或替换 XLSX，不推进 Current/Last Valid，也不决定业务数据应如何落入工作簿。后续候选编辑、验证、用户审阅与接受仍由既有 CB-04、CB-03、CB-02 链路负责。

## 2. Authority Baseline and Existing Evidence

| 来源 | 状态与约束 |
|---|---|
| TDD V2.0.3 §2.3、§5.3、§8 | 定义当前用户 ORM → typed JSON snapshot → LLM 应用于当前 Workbook → 既有候选验证/确认/版本链；要求 `full`/`incremental`、查询范围、时间、分页/完整性、记录身份/业务键、类型和空值语义。JSON 不包含 Excel 坐标、行号或写入动作。 |
| Implementation Plan V2.0.2 §8 CB-05 | 定义只读 JSON Data Tool、依赖 CB-02/CB-04、独立验收；CB-05 不阻断不使用数据刷新的 CB-06 链路，结果在 CB-07 汇合。 |
| SRS V1.1.0 | 保留当前用户 ORM/Record Rules、字段授权、数据最小化和 Provider 数据政策。CFG-M2-001/002 默认不批准的 Provider 数据暴露不得发生；OPEN-M2-002/003 所列字段/数据类别/处理政策仍须按实际范围处理。 |
| CB-01 v0.2 | Responses Adapter 负责 Provider 请求和真实文件返回；不负责业务 ORM 查询。CB-05 不修改 Adapter。 |
| CB-02 v0.3 + 已批准并发修订 | 版本、附件 SHA、父链、Current/Last Valid 和原子推进权威。Data Tool 不复刻这些服务。 |
| CB-03 v0.2 | 验证候选文件及生成可信 Receipt；不负责查询 Odoo 或判断业务数据映射。 |
| CC-04 v0.2 / 实现记录 | 现有 `office` 编排服务处理 Intent、版本和候选编辑；按负责人当前决定，CC-04 HVR 保持 Pending 且暂停。本草案只定义其与 Data Tool 的接缝。 |
| `llm_thread.py:LLMTool.odoo_record_retriever_execute()` | 已委派给现有通用 Retriever，并在当前 Odoo `env` 下执行。 |
| `llm_record_retriever.py:odoo_record_retriever_execute()` | 已使用 ORM `search_read`/`search`/`read`，支持 `limit` 1–500、offset、稳定 ID 排序追加，以及可选 `count/offset/limit/has_more`。当前将结果经 `json.dumps(..., default=str)` 转换。 |
| `office_mapping_tools.py:office()` / `edit_orchestrator.py:dispatch_office_action()` | 存在单一 Candidate B `office` Facade，当前动作为 status/plan/edit/accept/reject；尚无 `refresh_data` action。 |
| `llm_thread.py` 的 M1 工具绑定 | 仍有历史 `odoo_record_retriever` 注册，用于首轮 M1 Mapping 数据读取。CB-05 不删除或改造该旧路径；refresh 能力不另注册新的公开 Agent Tool。 |

**已证实的能力差距：**现有 Retriever 有 ORM 读取和页级分页元数据，但没有快照类型、查询时点/规范化范围指纹、typed field envelope、数据内容指纹、full/incremental 语义或完整/失败/截断快照的统一结果。现有 `office` dispatcher 没有数据刷新动作。当前通用 Retriever 的存在不等于 CB-05 已实现。

## 3. Scope

### 3.1 In Scope

- 在现有 `office` Agent Tool Facade 下增加只读 `refresh_data` action；不增加独立公开 Data Tool。
- 对模型、domain、fields、排序、分页和 snapshot 参数做结构化输入验证。
- 在当前用户及其当前公司上下文中，用 Odoo ORM 执行读操作并遵守 ACL、字段访问权限和 Record Rules。
- 形成通用 typed JSON snapshot：来源、查询范围、查询时间、稳定记录身份、可选业务键、分页与完整性、字段类型和值、来源/内容指纹及错误信号。
- 定义 `full` 与 `incremental` 的严格语义；不从未返回推断删除。
- 将快照与当前 Thread/Session、发起用户、Current Version ID/SHA 和 Document Revision 关联；在查询期间基线变化时不得把旧快照作为当前 Workbook 的刷新数据返回。
- 在把结果交回会进入 Provider 上下文的 Agent Tool 循环前，检查既有外发数据策略；策略不允许时不得把数据值放入 Tool result。
- 只读测试、权限测试、快照契约测试、失败分类测试和 Candidate/Current 状态不变测试。

### 3.2 Out of Scope

- 对任何特定 Odoo 业务模型、业务字段、Excel 模板、工作表、列、单元格或业务键编码特殊规则。
- 选择 Excel 坐标、把记录映射到行列、生成 Mapping DSL/单元格操作，或在 Odoo 本地修改/重建 XLSX。
- Data Tool 写 Odoo 业务记录、创建库存/销售/采购动作或变更预留。
- 替代 M1 初始 Mapping、现有 `office` 编排、CB-01 Provider Adapter、CB-02 版本服务、CB-03 Validator 或 CB-04 用户决策流程。
- 新增公开 Agent Tool、通用规则引擎、Excel 意图解析器、DAG、事件总线或快照数据库框架。
- 自动将未返回记录解释为删除；自动合并重复业务键；自动决定发生冲突时应保留哪一个业务值。
- 改变 CC-04 HVR 状态、修复其下载/Validator/Provider 门禁，或以本 CC 测试代替 CC-04 HVR。
- 真实数据外发、生产发布或附件留存政策的审批。

## 4. Data Flow

```text
用户在现有 Thread 中明确请求补充/刷新
  → Agent 调用现有 office(action="refresh_data")
  → 绑定当前用户、Thread、Session、Current Version、SHA、Document Revision
  → 验证 query spec、ORM 权限、字段策略及当前 Provider 数据外发政策
  → 当前用户 ORM 读取并形成 typed JSON snapshot
  → Agent 收到范围、完整性、类型和来源均可见的 JSON
  → LLM 决定如何应用数据；需要歧义澄清/业务确认时回到 CB-04
  → 用户授权后，后续文件编辑仍通过 CB-01/CB-04 形成 Candidate
  → CB-03 验证，CB-02 受控记录/接受；按现有审阅和交付流程继续
```

1. **解析请求。** 用户的明确请求、Thread 与当前版本构成查询上下文。Agent 提交的 `query_spec` 是不可信输入，不能扩大用户要求或数据政策授权。
2. **绑定基线。** 服务端从当前 ORM session 解析 Thread 所有权、Session、当前已接受版本及 SHA、Document Revision。不得使用聊天历史重建文件状态。
3. **权限与外发检查。** 服务端在读取/返回前检查模型和字段许可、用户/公司权限及适用的数据外发策略。Tool result 将被送回 Agent/Provider 上下文；若当前 Provider 不获准接收这些数据，不得返回记录值。
4. **查询与序列化。** 使用当前 `env` 的 ORM。不可用 `sudo()`、管理员回退、SQL/cursor 或绕过 Record Rules。按稳定顺序查询，保留页边界、值类型与错误。
5. **返回 JSON。** JSON 只含数据与来源/完整性语义，不含 workbook 结构、位置或编辑动作。空结果与查询失败必须区分。
6. **检查并发陈旧。** 返回前重新核对绑定的 Current Version、SHA 和 Document Revision；任一已改变时，结果标记 `blocked/stale_snapshot`，不得被 Agent 当成当前版本刷新数据继续使用。
7. **后续文件编辑。** 由 LLM 根据 JSON 和用户意图应用到当前有效 XLSX。Data Tool 不执行写入。生成候选后继续既有 CB-04 → CB-03 → CB-02 流程；工具读取成功本身不表示 Workbook 已刷新或用户任务完成。

## 5. Interface Contract

### 5.1 Public Tool Call

唯一公开入口仍为既有 `office` Tool；在其现有 schema 中增加 `action="refresh_data"`，不注册第二个 M2 Data Tool。

```json
{
  "action": "refresh_data",
  "query_spec": {
    "model": "<permitted Odoo model>",
    "domain": [["<permitted field>", "=", "<explicit value>"]],
    "fields": ["<permitted field>"],
    "order": "<validated order>",
    "snapshot_type": "full",
    "page": {"limit": 100, "offset": 0},
    "incremental": null
  }
}
```

字段语义：

- `model`、domain 字段、读取字段和 order 均为服务端验证的 Odoo 名称/结构；不得通过字符串执行、动态 Python、SQL 或不受限表达式。
- `snapshot_type` 必须为 `full` 或 `incremental`。若用户未说明刷新语义且选择会导致不同数据效果，Agent 应先澄清。
- `full` 的 domain/查询范围必须可明确说明；空 domain 代表该模型当前用户可见的全量范围，不能隐式替用户选取。
- `incremental` 必须提供经服务端验证且对该模型有效的 cursor/watermark 起点和终点/查询时点语义。模型没有可用变化游标时，不得假装支持增量；可以返回 `blocked/unsupported_incremental` 并说明限制。
- `page.limit` 复用现有 Retriever 已实施的每页 `1..500` 边界。总页数、总记录数和 Tool 输出大小不得自行发明新阈值；按已有配置/运行边界执行。超出可执行完整范围时返回不完整标记，不能声称 full 完成。

### 5.2 Snapshot Response

工具返回沿用现有 `office` 结果信封（`status`、`operation_status`、`artifact_state`、`delivery_state` 等），在成功数据读取结果中增加 `data_snapshot`。不创建平行的 Agent 工具结果协议。

```json
{
  "status": "completed",
  "operation_status": "data_snapshot_returned",
  "operation_executed": true,
  "artifact_state": "not_presented",
  "delivery_state": "not_finalized",
  "data_snapshot": {
    "schema_version": "office.data_snapshot.v1",
    "snapshot_id": "<server-generated opaque id>",
    "snapshot_type": "full",
    "scope": {
      "model": "<model name>",
      "query_fingerprint": "<sha256>",
      "field_names": ["<permitted field>"],
      "scope_description": "<bounded user-readable description>"
    },
    "source": {
      "queried_at": "<UTC ISO-8601>",
      "authorized_subject_ref": "<server-side audit reference>",
      "company_scope_ref": "<server-side authorized scope reference>"
    },
    "page": {
      "offset": 0,
      "limit": 100,
      "returned": 1,
      "total_count": 1,
      "has_more": false,
      "complete": true
    },
    "consistency": "<consistent|best_effort|unknown>",
    "content_fingerprint": "<sha256>",
    "records": [
      {
        "identity": {"record_id": 42, "business_key": {"<optional key>": "<value>"}},
        "values": {
          "<field>": {"type": "boolean", "value": false}
        }
      }
    ],
    "warnings": [],
    "errors": []
  }
}
```

Schema rules:

1. `snapshot_id` 是服务端为此次读取生成的 opaque reference。`query_fingerprint` 对规范化查询范围、字段、顺序、快照类型及页范围计算；`content_fingerprint` 对规范化 schema、身份、字段类型和值和顺序计算。不能把这些摘要当作 Odoo 业务记录 ID 或工作簿版本。
2. Odoo `(model, record_id)` 是来源库内的稳定记录身份；可选 `business_key` 是数据值，不默认唯一。重复业务键应明确列出或标注，不能自动合并、覆盖或用 Excel 行号代替身份。
3. 字段值使用 `{type, value}`。`null`、Boolean `false`、整数 `0`、浮点/金额 `0.0`、空文本 `""` 必须区分。日期与 datetime 使用 ISO 8601 和明确时区；不能支持安全、无损序列化的字段类型不得静默转成含糊字符串。
4. 默认查询标量字段。关系值只有在用户显式请求、字段与目标记录都通过 ORM 权限检查并有稳定身份表示时才可返回；不递归扩展关系图。Binary、密码、Secret、计算/非存储或其他未获授权/不可安全表达的字段须拒绝或明确报告不支持。
5. `authorized_subject_ref` 与 `company_scope_ref` 可用不泄漏数据的审计引用；不为模型暴露不必要的用户、公司或数据库内部信息。必要审计值在服务端记录。
6. Response 不得含 sheet、cell、row number、Excel coordinate、Mapping、formula edit、write command 或用户确认令牌。

### 5.3 Snapshot Semantics

- **Full:** 表示对返回元数据中明确的模型、当前用户可见查询范围和字段集合完成枚举。它不表示整个 Odoo 模型或数据库的所有记录。只有所有页连续、同一 `query_fingerprint`、无失败/截断且最终 `has_more=false` 时，才可 `complete=true`。分页未完成时不得用于依赖完整集合的同步。
- **Full absence:** 某记录不在此次 full 结果中，只能说明它不在此次完整且受限的查询结果里；不能单独证明 Odoo 业务记录已删除。不得自动从工作簿删除对应行。
- **Incremental:** 表示在明确 cursor/watermark 范围内查得的新增/变化记录。未返回不代表未变化，更不表示删除。只有数据源显式提供且权限允许的删除标记才可声明删除；通用 Odoo `search_read` 不得伪造 tombstone。
- **Consistency:** `complete` 与点时一致性是分开的属性。若多页读取不能证明来自同一一致读视图，必须标记 `best_effort` 或 `unknown`，不可称为原子点时快照。依赖强一致集合的使用方不得把该状态提升为完整可信结果。
- **Empty:** 成功执行且确实无匹配记录可返回 `status=completed`、`records=[]`、适用的 `complete=true`。权限错误、查询失败、超时、未访问到的页或截断必须使用错误/不完整信号，不得伪装成空结果。

## 6. State and Provenance Contract

1. Data Tool 查询是只读操作。它不改变 Session 的 `current_version_id`、`last_valid_version_id`、`document_revision`，不接受 Candidate，不生成或替换文件附件。
2. Snapshot 绑定发起用户、Thread/Session、查询规范、Current Version ID、输入 SHA、Document Revision 和查询时间。若读取结束时版本绑定已过期，返回 stale 状态且不把记录值交给下一轮 Provider 上下文。
3. Tool execution/message trace 保留 snapshot ID、query/content fingerprint、分页/完整性和安全错误元数据；默认不额外创建 Workbook 附件或完整业务数据快照模型。
4. 若 LLM 使用快照创建后续 Candidate，Candidate 的可审计来源必须能关联该 snapshot ID/fingerprint 与既有 user Intent、CB-04 调用和 CB-02 版本。当前 `office.workbook.version` 有输入/输出 SHA 与 Intent/Effect 绑定，但没有明确的 Data Snapshot 关联字段；代码评审未证明现有 tool trace 到 Candidate 的持久引用已经充分。编码前必须裁定第 13 节的最小来源关联方案，不得将快照 digest 错放到无关字段或仅依赖模型声称。
5. 新的一次读取产生新的 `snapshot_id` 和 query time。对同一只读请求重试时不得把旧快照冒充新值；后续 edit 的输入仍是 CB-02 当前接受版本的真实 XLSX 字节。

## 7. Error Handling and Outcome Semantics

| 状态 / operation_status | 使用条件 | 数据结果与副作用 |
|---|---|---|
| `completed / data_snapshot_returned` | 查询成功；即使零记录，也必须在 JSON 中明确范围和完整性 | 返回记录与 snapshot metadata；不改变 Workbook/业务数据 |
| `completed / snapshot_incomplete` | 已返回一个或多个有效页，但还有页、分页缺失或完整性无法证明 | 必须 `complete=false` 并说明原因；不能称作完整刷新。对于请求要求 full 的使用方式，不得继续执行依赖完整集合的文件同步 |
| `clarification_required / query_scope_ambiguous` | 模型、范围、字段、full/incremental 或业务键解释不明确 | 不查询不确定的数据范围；请求用户补充 |
| `blocked / access_denied` | ACL、字段访问、Record Rules、公司范围、Session/Thread 权限不允许 | 不返回被拒数据或其敏感存在性；不支持用户确认/模型参数绕过 |
| `blocked / data_policy_denied` | 当前 Provider 不允许接收本次数据类别/字段/上下文，或数据策略未配置 | 不把记录值返回到会进入 Provider 上下文的 Tool result；不把该状态表述成“没有记录” |
| `blocked / unsupported_query` | 模型/字段类型/增量 cursor/查询操作不在通用安全支持范围 | 返回最小、脱敏的能力限制；不自动改成更宽查询 |
| `blocked / stale_snapshot` | 查询期间 Current/SHA/Document Revision 变化，或 snapshot token 与原查询绑定不匹配 | 不将旧快照交给后续文件编辑；Current 不变 |
| `failed / retrieval_error` | ORM/数据库/序列化/基础设施错误或执行无法确认 | `errors` 提供稳定脱敏码；不得返回虚假的 `records=[]` 成功结果 |

Data Tool 不产生 `confirmation_required` 来代替 CB-04 对后续文件编辑的确认判断。查询范围不清先澄清；ACL、安全、数据政策和资源限制不可由用户确认绕过；对 JSON 的业务取舍及可能覆盖由 LLM/CB-04 解释并依现有确认契约交给用户决定。

## 8. Integration Boundaries

| 组件 | CB-05 复用/扩展 | 保持不变 |
|---|---|---|
| Single `office` Tool | 在既有 `office` schema/dispatcher 下加 `refresh_data` action；不注册独立 Data Tool。当前 M1 `odoo_record_retriever` 注册保持原样，内部可复用其 ORM 查询能力。 | 不在本 CC 迁移/删除 M1 Tool Registry 或改变首轮 Mapping 调用行为。 |
| Current-user ORM Retriever | 复用当前 `env` 的 ORM 查询、稳定排序和现有限流；增加 Data Snapshot 语义与序列化，不复制权限实现。 | 不用 sudo、管理员回退或直接 SQL；不修改 Odoo 官方代码。 |
| CB-04 Intent/Orchestration | Agent 解释用户请求；绑定 `refresh_data` 与当前 Thread/Session/版本；对后续写文件及用户决策调用现有 CB-04 流程。 | 不在 Data Tool 内实现 Confirmation Gate、编辑/接受/拒绝或候选状态机。 |
| CB-01 Adapter | 只在后续编辑阶段由 CB-04 使用；数据外发检查需在 Tool result 放入 Provider context 前生效。 | 不改 Provider transport、API 或 Adapter。 |
| CB-02 Version Service | 读取 Current identity/SHA/revision；后续 Candidate 仍由其登记、接受、拒绝。 | 查询不推进版本；不复制版本/附件/哈希服务。 |
| CB-03 Validator | 后续 Candidate 按现有 Receipt 与验证链处理。 | 不校验或重写 Data Tool JSON；不新增验证等级/效果规则。 |
| CB-06/CB-07 | CB-07 用合成及获批数据验证 JSON→后续编辑链；交付仍由 CB-06。 | CB-05 不是 CB-06 单纯 XLSX 编辑/交付的前置条件。 |

## 9. Preservation Constraints

- 完全通用，不得按模型、字段、模板、工作表、坐标或某个业务案例特殊处理。
- 用户请求和 ORM 权限共同限定查询。Agent 传入的模型、字段、domain、order、分页和 business key 全部是不可信参数。
- 所有 Odoo 数据通过当前用户 ORM；Record Rules、多公司和字段访问规则必须有效执行。无权不等于空值或零记录。
- Provider 外发政策适用于 Data Tool 返回给 Agent 的 JSON。若工具结果将进入外部 Provider 上下文，须先符合适用数据类别、字段、处理目的和留存政策；用户的业务确认不能替代组织级数据政策授权。
- Data Tool 对 Odoo 业务记录只读；必须证明没有 `.create/.write/.unlink` 或其它业务副作用。Tool execution trace/Snapshot metadata 不得含超出审计需要的原始业务值副本。
- 保留 `null`、`false`、`0`、`0.0`、`""` 及日期/datetime 类型语义；不通过 `if not value` 统一判空。
- `full`/`incremental`、空结果、分页、重复 business key、记录身份和 complete 信号必须可由 JSON 消费端确定解释。
- 不因生成成功的 JSON 宣称 Excel 已刷新；不因 JSON 中缺少记录声称业务记录删除。
- 仍由用户决定业务值如何应用、是否接受覆盖及是否继续；数据读取成功不代表修改获得业务授权。

## 10. Test Matrix

所有 CB-05 测试使用通用合成模型/夹具，不以销售、联系人、库存或特定工作簿定义通用规则。

| ID | 验收行为 | 证据类型 |
|---|---|---|
| DT-01 | `office(action=refresh_data)` 被既有 `office` Facade 路由；没有新增独立公开 Agent Tool | Odoo Tool schema/dispatcher test |
| DT-02 | 合法模型、字段、domain、order、page 输入经当前用户 ORM 查询；非法/未知字段和不安全参数拒绝 | Odoo TransactionCase |
| DT-03 | model ACL、field access、Record Rules、allowed companies、多用户和跨公司隔离均生效；不得 sudo/管理员回退 | 多用户 TransactionCase |
| DT-04 | 输出含稳定 `(model, record_id)` 身份、可选非唯一 business key、query scope/time、页序和指纹；不含 Excel 坐标/行号/写入命令 | JSON schema/assertion tests |
| DT-05 | `full` 仅对明确查询范围完整；全页连续和结束条件正确时 complete；缺页、截断、查询错误或过期页不能 complete | 分页及故障注入测试 |
| DT-06 | `incremental` cursor 起止范围明确；未返回记录不成为删除标记；没有可靠 cursor 的模型不假装支持 | 通用合成字段测试 |
| DT-07 | business key 重复被显式保留/标记；记录不被错误合并，不以行序冒充身份 | 合成重复键测试 |
| DT-08 | `None`、`False`、`0`、`0.0`、`""`、日期和 datetime 序列化、类型标签和 round-trip 均区分 | JSON type tests |
| DT-09 | 无权限、数据策略阻止、未知模型/字段、超时、序列化错误和真正空结果使用不同结果，不泄露受保护值 | 安全及结果契约测试 |
| DT-10 | Tool result 的数据 egress 未获准时无业务值进入 Provider 上下文；合成/隔离测试不伪作真实数据授权 | Mock egress Gate test |
| DT-11 | 读取前后业务记录和值完全一致；无创建、更新、删除；current/last-valid/document revision 和附件集合不变 | ORM before/after + transaction/audit test |
| DT-12 | 查询期间 Current/SHA/Document Revision 变化，或 Thread/Session 不匹配时结果 stale/blocked，不可被后续 edit 使用 | CB-02/CB-04 integration test |
| DT-13 | snapshot ID/content fingerprint 绑定查询和当前版本；内容、范围、页序变化会产生不同指纹；Candidate provenance 可回溯对应 snapshot | 集成测试；所需最小状态扩展先获批准 |
| DT-14 | M1 初始 Mapping/retriever 行为未变化；首轮功能与 refresh action 互不串线 | 现有 M1 定向回归 |

Contract tests 和合成 TransactionCase 不代表获准真实业务数据/Provider E2E。真实 Provider 对 JSON 的外发、文件编辑和浏览器交付应在 CB-07/对应运行授权中单独记录。

## 11. Acceptance Criteria

1. 仅通过既有 `office` Tool Facade 暴露 refresh action；不新增公开 Agent Tool。
2. 读取严格遵守当前用户 ORM 权限、字段策略、Record Rules 和公司边界，无 sudo、直接 SQL 或管理员回退。
3. JSON schema 可表达 query scope、snapshot type/time、身份、类型和值、分页、完整性、错误与指纹；不包含 Excel 位置或写入操作。
4. `full` 只对声明的当前用户可见查询范围表示完整；`incremental` 未返回不代表删除；缺页/截断/失败不冒充完整或零条记录。
5. 空值、Boolean、数值、字符串和日期类型按契约保真；非唯一业务键不被擅自合并。
6. Provider 数据政策未授权时，数据记录值不得出现在会传给 Provider 的 Tool result；错误响应不泄漏受保护字段/记录存在性。
7. 查询前后 Odoo 业务数据不变；Data Tool 不修改附件、不产生文件 Candidate、不推进 Session/Workbook Current 或 Revision。
8. Snapshot 绑定查询基线并可审计；查询期间版本变化时不能继续作为当前版本的 refresh 输入。
9. 新 JSON 被 LLM 应用时，写文件/候选/用户接受仍走现有 CB-04/CB-03/CB-02 路径，不由 Data Tool 直接执行。
10. M1 Mapping 和现有初始 Retriever 行为保持兼容；不得以 CB-05 测试结果宣称 CC-04 HVR、CB-06 浏览器交付或 CB-07 Provider 集成已通过。

## 12. File Scope Proposal

### 12.1 Candidate Implementation Allowlist

- `mymodules/office_engine_m2/models/office_mapping_tools.py` — 扩展现有 `office` action schema/dispatch，不新增公开 Tool。
- `mymodules/office_engine_m2/models/llm_thread.py` — 最小提示/上下文衔接及复用当前用户 Retriever；不得改变 M1 initial mapping 语义。
- `mymodules/office_engine_m2/services/edit_orchestrator.py` — 若实现需要，在既有 dispatcher 下路由 read-only refresh action；不得承担 Excel 写入。
- `mymodules/office_engine_m2/services/` — 只有当现有 Retriever/Orchestrator 无合适位置时，允许新增一个业务无关的 snapshot serialization service；不新增 framework。
- `mymodules/office_engine_m2/tests/` — 通用 JSON、ORM 权限、分页、值类型、只读性、stale binding 和 M1 回归测试。
- `docs/implementation/IHR-M2-CB-05.md`、`ATR-M2-CB-05.md` 与对应 evidence — 仅获编码授权后记录实际事实。

### 12.2 Explicitly Out of Allowlist

- Odoo 官方代码、Provider Adapter/配置、CB-02/CB-03 服务与数据模型、M1 `office_core`/`office_verify` 行为、数据库既有数据和独立公开 Tool Registry 迁移。
- 如实现前证明必须新增版本模型字段/改动上游 CC，停止该子项并先取得对应的最小 Amendment/Coding Authorization；不得把上游版本/状态字段滥用于 Snapshot provenance。

## 13. Dependencies, Risks and Owner Decisions

### 13.1 Concrete Baseline Differences

| 差异 | 证据 | 最小处置建议 |
|---|---|---|
| Frozen SRS V1.1 规范主要覆盖首轮 Mapping/M1，并未定义“当前 Workbook 后续 Odoo JSON refresh”的完整产品流；Frozen TDD V2.0.3 与 Plan V2.0.2 已定义该技术/功能路线 | SRS V1.1 `FR-M2-003`、`CFG-M2-001/002`、`OPEN-M2-002/003`；TDD §0.4/§2.3；Plan §8 CB-05 | 本 CC 草案按明确的 CB-05 功能目标定义本地只读 JSON 契约，不据 SRS 缺项拒绝起草。进入真实数据运行前，负责人应以最小版本化 SRS 澄清记录 refresh 的读权限/字段策略与 Provider egress 边界；不得把 TDD 草案当成已批准的 SRS 修订。 |
| 当前 `office` Facade 没有 `refresh_data`，而现有 Agent 仍有初始 Mapping 用的 `odoo_record_retriever` | `office_mapping_tools.py:office()`、`edit_orchestrator.py:dispatch_office_action()`、`llm_thread.py` tool binding | 在 `office` 下增加一个 action；保留 M1 Retriever 注册和行为。本 CC 不做全局 Tool Registry 迁移。 |
| Current `office.workbook.version` 没有显式 Data Snapshot ID/fingerprint 字段；当前 Intent digest 也未声明 snapshot reference | `office_workbook_version.py` fields、`intent_contract.py:bind_intent()` | 必须在编码前确认最小可持久关联方式：复用并验证不可变 Tool-result/message trace 的稳定引用，或单独批准 CB-02/CB-04 的只读 provenance 字段/Intent 扩展。未裁定前不得声称候选完整来源追溯已实现。 |
| Retriever 每页上限为 500，但没有由本次代码审计证实的累计页数/响应字节预算或跨页点时一致性保证 | `llm_record_retriever.py` 当前实现 | 复用既有界限；超出已配置总预算时标记 incomplete。对多页 full 的完整度与一致性分别报告，不凭查询时间宣称事务级点时快照。 |

### 13.2 Owner Decisions Before Coding Authorization

1. **数据外发政策：**哪些 Odoo 数据类别、字段、用途可进入当前聊天模型/Provider 上下文；处理区域、留存/删除要求是什么？未批准部分保持阻断。合成数据 Contract tests 不需要本项真实数据授权。
2. **Snapshot lineage persistence：**接受复用现有 Tool-result/message trace 的候选关联，还是批准最小 CB-02/CB-04 provenance contract amendment？优先复用现有不可变关联；若不能证明可检索且与 Candidate 一一绑定，则需要窄范围 amendment。
3. **多页 full 一致性：**是否接受 `complete=true` 表示在声明查询范围内所有页被读取、另以 `consistency=best_effort/unknown` 报告跨页期间变更；或要求 point-in-time 一致快照？未经技术证明不得假定后者已具备。
4. **累计资源上限：**若当前部署没有可引用的最大累计结果量/Tool output size 配置，负责人需确认是将超出单页边界的一律作为 incomplete，还是批准一个有测量依据的累计上限。CC-05 实施者不得猜阈值。

### 13.3 Risks

- ORM ACL 通过不等于组织已批准把字段数据送入外部 Provider。Tool output 是模型上下文的一部分，必须在数据值被序列化返回前执行策略门。
- 多页期间数据变化、非唯一 business key 或无 reliable incremental cursor 会降低可用于自动同步的程度；应诚实返回状态并交由用户澄清，不通过行号/名称猜测。
- 原始 JSON 若保存在 Thread Tool message 中，可能延长数据留存。不得另复制整份业务快照；真实留存仍按已批准数据政策执行。
- CC-04 当前 HVR Pending；本草案仅复用其设计/实现接口，不宣称 HVR 通过。CB-06 交付和 CB-07 全链路仍独立验收。

## 14. Stop Conditions and Coding Authorization Gate

本草案不授权实施。未来独立 Coding Authorization 至少须明确允许的模块/测试数据库/数据类别及是否允许 Provider egress。

编码/测试中遇到以下任一情况，应停止受影响部分，不扩大权限或改变上游合同：

- 只能通过 `sudo()`、管理员身份、SQL/直接 cursor、绕开 Record Rules 或新建公开 Tool 才能完成查询。
- 无法证明模型/字段权限或外部数据策略，但返回 JSON 会让 Provider 收到数据值。
- 输入参数含糊、范围更大于用户授权或模型/业务键关系无法可靠表达。
- full/incremental 完整性、分页一致性或值类型无法如实表达。
- Current/Revision 变化后仍试图把旧 Snapshot 用于新版本。
- 必须直接写 Workbook、推进 Current 或绕过 CB-04/03/02 才能交付。
- 必须修改 CB-02/CB-04 上游契约而未获明确 Amendment 与编码授权。
- 测试要求涉及真实业务数据或真实 Provider egress，但当前授权未覆盖。

## 15. Coding Handoff and Stop Condition

CC-05 进入编码前，应完成：

1. 负责人评审并冻结本契约；
2. 明确第 13.2 节会影响实现的数据策略、快照一致性、provenance 和资源预算决策；
3. 单独给出 Coding Authorization、合成 Odoo 测试库/模块升级/TransactionCase 范围；
4. 如需调整 CB-02/CB-04，先批准最小 Amendment，不在 CB-05 中隐式改写其权威语义。

本轮停止于 `DRAFT — NOT AUTHORIZED`。没有执行测试、模块升级、数据库读写、Provider 调用或 CC-04 HVR。
