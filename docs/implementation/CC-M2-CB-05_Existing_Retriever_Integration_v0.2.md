# CC-M2-CB-05 — Existing Retriever Integration

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 |
| 契约 | CC-M2-CB-05 — Existing Retriever Integration |
| 版本 | v0.2 |
| 状态 | **DRAFT — NOT AUTHORIZED** |
| 生效基线 | TDD V2.0.3 FROZEN；其 CB-05 条款只有配套 TDD Change 获批并正式生效后才由新版本替代 |
| 本次提出的 TDD Change | `docs/design/TDD_office_engine_m2_v2.0.4_CB05_Existing_Retriever_Integration_DRAFT.md` |
| 本次提出的 Plan Amendment | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.3_CB05_Existing_Retriever_Integration_Amendment_DRAFT.md` |
| 保留的历史契约 | `CC-M2-CB-05_Data_Tool_JSON_Refresh_v0.1.md` — 不覆盖，待新契约批准后标注 superseded |
| 日期 | 2026-11-10 |

> 本文是定稿候选，不授权编码、执行测试、修改数据库、启动/停止服务、模块升级、真实业务数据外发或生产发布。冻结 TDD Change、Plan Amendment 和 CC-05 均须分别获批；本 CC 的批准不自动给予 Runtime/Environment Authorization。

## 1. Contract Goal

在已有 Accepted Current Workbook 的同一 Office Thread 中，支持 Agent 按用户要求再次读取当前用户有权访问的 Odoo 数据，并把结果用于后续当前 Excel 编辑。

唯一公开的 M2 Agent Tool 仍为 `office`。新增 `action="retrieve"` 的唯一实现目的，是通过薄路由复用该 Thread 已绑定的既有 `odoo_record_retriever`。取数只读 Odoo；编辑继续通过现有 Candidate、Validator、Version 和用户决策流程。M1 首轮 Mapping 的 Retriever 调用方式和返回格式不变。

## 2. Authority Baseline and Required Approval Sequence

| 基线 | 当前事实/约束 |
|---|---|
| Frozen TDD V2.0.3 | CB-05 仍写有 Snapshot/full-incremental/fingerprint 等冻结要求；本 v0.2 不得悄然覆盖。 |
| Proposed TDD V2.0.4 Change | 仅拟议把 CB-05 改为 Existing Retriever Integration；当前 DRAFT/NOT EFFECTIVE。 |
| Frozen Implementation Plan V2.0.2 | 当前 CB-05 为 Data Tool JSON Snapshot；须由配套 Amendment 正式替换。 |
| CB-01..04 | 已有 Provider、版本、Validator 与 Orchestration 能力按其已接受范围复用；不因本 CC 重开或重构。CC-04 HVR/其它 Open 状态不在本 CC 内修改。 |
| 当前代码证据 | `llm.tool.execute()` 在 `mail_message.py` 中通过 Thread `tool_ids` 查找工具；Retriever 实现在 `llm_tool_record_retriever.py`；M2 Thread 的 Accepted Current 路径仅把 `office` 暴露给 Agent；`office` dispatcher 尚无 retrieve 分支。 |

实施前必须先有负责人批准并生效的 TDD Change 与 Plan Amendment，再冻结 CC-05 并另行签发 Coding Authorization。未生效之前如与上游冻结条款冲突，以当前冻结基线为准并停止编码，不以本草案自行解除冲突。

## 3. In Scope / Out of Scope

### 3.1 In Scope

- 在既有 `office` Tool schema 中增加 `retrieve` action 及与当前 Retriever 一致的 `query_spec`。
- 在现有 office dispatcher 中解析当前用户、当前 Thread、当前 tool message 和 Accepted Current Workbook 上下文。
- 从该 Thread 的 `thread.tool_ids` 取得已绑定且 active 的 `odoo_record_retriever`。
- 通过该 `llm.tool` 记录的既有 `.with_context(message=tool_message).execute(query_spec)` 调用路径执行；复用现有 schema 验证、ORM、权限及序列化。
- 返回原 Retriever 的记录或分页对象，并附最小的规范化查询范围和服务器读取时间；保持记录 ID、当前值语义与页级状态。
- 更新 M2 Agent 指引：用户要求在 Current Workbook 基础上补充 Odoo 数据时，先调用 `office(action="retrieve")`，之后继续既有 Office 编辑流程。
- 自动化测试、M1 兼容性回归和两阶段联系人 Excel 集成验收标准。

### 3.2 Out of Scope

- 原 Data Tool JSON Snapshot 方案的实现；独立数据服务、快照模型、snapshot ID、query/content fingerprint、full/incremental/CDC。
- 跨页点时一致性保证、查询时强制锁 Workbook 版本、快照与 Candidate 的新持久关联。
- 新的外发数据分类、字段审批、Provider 策略配置、留存/删除管理功能。既有有效外发安全边界继续生效。
- 新公开 Agent Tool、修改 Tool Registry 迁移、Retriever ORM 实现或其 M1 参数/默认行为/返回格式。
- `sudo()`、直接 SQL/cursor、管理员身份回退或复制 search/read 查询。
- 本地 Excel 意图解析、坐标选择、Mapping DSL、业务正确性验证、修改 Odoo 业务数据。
- 修改 CB-01/02/03/04/06 行为或扩充其验收范围。

## 4. Existing Retriever Reuse Contract

### 4.1 Internal Resolution and Call

对由 `office` Tool 触发的调用，服务端必须：

1. 使用现有受信任 Office context 解析当前消息、Thread、用户和公司上下文，并校验该用户拥有/可读该 Thread。
2. 确认 Thread 有 Accepted Current Workbook，且 Current/Last Valid 状态符合现有版本服务要求。取数路径不能因此改变版本。
3. 在同一 `thread.tool_ids` 中按名称查找恰好一个 active `odoo_record_retriever`；未注册、未绑定、停用或歧义时显式失败。
4. 使用该 tool 的现有 `.with_context(message=tool_message).execute(validated_query_spec)`。禁止直接调用 `odoo_record_retriever_execute()`、另建 ORM 查询、使用 `sudo()` 或切换为别的用户。
5. 保留正常 Retriever 权限错误/字段错误/查询错误；错误不得伪装成成功空结果，也不得泄露被拒绝记录的受保护数据。

### 4.2 Retriever Input Compatibility

`query_spec` 与现有 Retriever 输入一一对应：

```json
{
  "model": "<Odoo model>",
  "domain": [["<field>", "=", "<value>"]],
  "fields": ["id", "<field>"],
  "order": "<validated ORM order>",
  "limit": 100,
  "offset": 0,
  "include_pagination": true
}
```

具体可选/默认值以及输入类型以已注册 Retriever schema 为准，不在 M2 路由中发明第二份查询语义。Facade 将分页结果作为默认模式（`include_pagination=true`）；关闭分页元数据不得造成 `has_more` 丢失。现有 Retriever 的 limit 1–500、非负 offset、ORM 行为原样复用。为使分页身份稳定，M2 action 在 order 未提供时使用 `id` 顺序；显式 order 由现有 Retriever 追加 `id` tie-breaker，不改变 M1 默认排序。

查询模型、字段、domain 和 order 都是不可信 Agent 参数；由现有工具验证并由 ORM 再执行访问控制。空 domain 表示当前用户在该模型上的 ORM 可见范围，Agent 不得静默把未限定的用户请求扩大成全模型查询；范围有歧义先澄清。

### 4.3 Output Contract

成功输出沿用当前 office 公共结果信封，并增加 `data`、`query_scope`、`retrieved_at`：

```json
{
  "status": "completed",
  "operation_status": "odoo_data_retrieved",
  "operation_executed": false,
  "artifact_state": "not_presented",
  "delivery_state": "not_finalized",
  "data": {
    "records": [],
    "count": 0,
    "offset": 0,
    "limit": 100,
    "has_more": false
  },
  "query_scope": {
    "model": "<model>",
    "domain": [],
    "fields": ["id", "<field>"],
    "order": "<effective order>"
  },
  "retrieved_at": "<server-generated ISO-8601 UTC time>"
}
```

`data` 必须是现有 Retriever 的原样结果：启用分页时为现有分页对象；非分页时为 records 列表（但本 M2 route 应请求分页元数据）。查询范围和 `retrieved_at` 只用于说明本次调用，不是持久化快照、点时一致性证明或 Workbook 绑定。分页期间数据可变化；`has_more=false` 不能被包装为跨页原子快照保证。

每条记录的 `(model, id)` 是稳定查询身份。若请求字段投影未包含 `id`，Facade 必须确保该 M2 返回仍保留 `id`，但不得改变 M1 Retriever 原始返回。follow-up 查询必须用返回 ID，而非 Excel 当前行号、名称相似度或排序位置。

JSON 应保留 Retriever 的 `null`、`false`、`0`、`0.0`、空字符串、日期等值序列化行为；Office route 不得以 truthiness 过滤。关系字段遵守 Retriever/Odoo 当前表示，不由 M2 新增递归展开。

工具结果表示“取数调用成功/失败”，不表示文件已编辑、候选已验证、业务意图已覆盖或 Current 已推进。取数不写 Odoo、Session、Workbook、附件或版本数据。

## 5. Agent Call Timing and Workflow

当 Thread 已有 Accepted Current Workbook，用户明确要求在当前文件基础上补充 Odoo 数据时，Agent 必须：

1. 确认查询模型、记录范围和所需字段足够明确；不清楚时请求用户澄清。
2. 调用 `office(action="retrieve", query_spec=...)`。仅请求实现用户意图所需的最小字段；用户指定记录集合时沿用其明确筛选条件。
3. 如需跟进读取同一批记录，使用上一次返回的记录 ID 构造精确过滤；如需分页，使用稳定排序、连续 offset，检查每页 `has_more`，对不完整页/错误如实反馈。
4. 收到数据后按用户意图使用现有 `office` plan/edit 流程生成 Candidate；按现有 review/accept/reject 流程处理。不得把 Retriever 结果当作 Candidate，也不得绕过 CB-02/03/04。
5. 每一轮读取均是新的当前用户 ORM 查询；不缓存或重放上轮数据来冒充新读取。若现有版本门拒绝后续编辑，按其结果向用户报告，不构造新的快照状态机。

两阶段联系人验收是集成测试数据，不是业务特例：首次查询 `res.partner` 的 `id/name/phone/email` 后由 Agent 填入工作簿；第二次按首轮三个 ID 读取地址字段，再由 Agent 补充地址列。通用生产逻辑不得包含 `res.partner`、联系人字段、固定工作表或单元格分支。

## 6. Security, Read-only and Compatibility

- 以 Odoo 当前用户 `env` 执行；ACL、字段组、Record Rules、allowed companies 和 Thread 私有访问不得削弱。
- 外发授权仅按当前有效数据策略处理。本 CC 不开发新的策略管理，也不授予把真实业务数据发送给外部 Provider 的权限。Mock 与合成数据只证明对应测试路径，不代表真实数据外发获批。
- Odoo 业务记录读取前后不得变化。`retrieve` 不调用 create/write/unlink，不修改附件，不创建/接受候选。
- M1 `odoo_record_retriever` Tool 注册、调用方式、字段参数及直接返回格式保持不变。M2 Accepted Current 路径中 Agent 仍只看见公开 `office`；Retriever 通过绑定记录内部调用。
- 不新增模型、持久化字段、数据库表、公开 Tool、查询权限清单或独立 service。
- 若现有有效安全门拒绝数据进入 Provider 上下文，保持拒绝；不得为通过 E2E 关闭门禁或把被拒绝数据伪装成空结果。

## 7. Error Handling and Non-Goals

| 情况 | 要求 |
|---|---|
| Thread/用户/Accepted Current 不可访问 | 使用现有 AccessError/office outcome 机制阻断，不执行 Retriever |
| Retriever 未注册/未绑定/停用 | 明确工具配置失败；不建立替代 ORM 查询 |
| 参数非法或字段/模型不可访问 | 保留现有工具/ORM 错误语义；不得返回成功空列表 |
| 查询无匹配行 | 返回成功的空 records 和有效分页元数据；与错误分开 |
| 有后续页 | 保留 `has_more=true`；Agent 继续按稳定排序分页或说明尚未读取完 |
| 取数成功但 Provider 策略禁止外发 | 继续由现有策略阻断；不得关闭策略、改用权限更高用户或泄漏 Tool result |
| 取数成功、Excel 编辑失败 | 不声称文件已更新；Current/Last Valid 按既有 CB-02 规则保持 |

不在本 CC 新建状态枚举、数据策略引擎、查询框架或 Excel 结果判定规则。

## 8. Integration Boundaries

| 组件 | 本 CC 责任 | 明确不做 |
|---|---|---|
| `office` Facade / dispatcher | 加 `retrieve` 参数 schema/action 路由并调用绑定 Retriever | 新增公开 Tool 或改动其它 action 的语义 |
| Odoo-LLM Retriever | 作为已存在的查询、ORM 权限和序列化实现被调用 | 修改其 M1 注册、默认值、查询实现或直接返回结构 |
| Agent instruction | 说明何时 retrieve、何时澄清、以 ID 追读、再走编辑流程 | 模板/业务字段特例或让 Agent 报告未经验证的完成 |
| CB-01/02/03/04 | 后续编辑时复用既有 Provider/版本/验证/决策契约 | 重写或绕过其服务 |
| CB-06/07 | Preview/Finalize 原接口不变；完整联系人用户闭环汇入 CB-07 HVR | 把组件测试写作完整 UI/Provider E2E |

## 9. Implementation File Allowlist

### 9.1 允许修改（仅未来单独获得 Coding Authorization 后）

- `mymodules/office_engine_m2/models/office_mapping_tools.py` — `office` Tool schema 与 facade 参数透传。
- `mymodules/office_engine_m2/services/edit_orchestrator.py` — `retrieve` 分支；解析 Thread 绑定的 Retriever，并通过现有 `.execute()` 调用。
- `mymodules/office_engine_m2/models/llm_thread.py` — 仅修改 M2 Agent 指引，说明读取时机和 ID/page 用法；保留 tool visibility。
- `mymodules/office_engine_m2/tests/` — 通用 action routing、Retriever 复用、权限/只读、值/分页、M1 兼容和联系人流程测试。
- `docs/implementation/IHR-M2-CB-05.md`、`ATR-M2-CB-05.md`、`FR-M2-CB-05_Existing_Retriever_Integration.md` 及 `docs/implementation/evidence/CB-M2-CB-05/` — 仅记录授权后的真实事实。

### 9.2 禁止修改

- `mymodules/odoo-llm/llm_tool/models/llm_tool_record_retriever.py`、`llm_tool.py`、`mail_message.py`、Retriever XML/注册、manifest；M1 Retriever 行为必须复用。
- CB-01/02/03/04、M1 `office_core`/`office_verify`、Provider 配置、现有外发安全实现、DB schema/models、其它 CC 和冻结基线文件。
- 任何用于绕过 ORM/ACL/Record Rules、现有 Provider 政策或版本门的文件。

如只读代码审查证明上述白名单不能满足调用链要求，停止相关修改，提交最小差异和证据，等待单独批准；不得自行扩展白名单。

## 10. Automated Test Matrix

| ID | 场景 | 必须断言 | 证据级别 |
|---|---|---|---|
| ERI-01 | `office` Tool schema/dispatch | 唯一公开 M2 Tool 仍是 `office`；`retrieve` 是允许 action；未知参数按封闭 schema 拒绝 | Contract/Mock |
| ERI-02 | 内部 Retriever 解析 | 从当前 Thread 的 `tool_ids` 找 active、已绑定 Retriever；准确调用 `.with_context(message=tool_message).execute(query_spec)` 一次；不直接调底层查询方法 | TransactionCase / Mock call assertion |
| ERI-03 | 无 Retriever / 无 Accepted Current / 错误 Thread | 在 Retriever 执行前阻断；不改 Session/Current | TransactionCase |
| ERI-04 | 查询和分页投影 | 返回现有 Retriever records 或分页对象；保留 count/offset/limit/has_more 和 `id`；缺省顺序使用 `id`，显式顺序保留 ID tie-breaker；不引入 snapshot/full/incremental 字段 | Contract/TransactionCase |
| ERI-05 | 值语义 | `None`、`False`、整数零、浮点零、空字符串及日期按现有 Retriever JSON 行为保留 | Retriever integration assertions；不新增 serializer |
| ERI-06 | 权限和多公司 | 当前用户 ACL、字段访问、Record Rules、公司边界在调用链生效；无 sudo/切换用户/直接 SQL | 多用户 TransactionCase |
| ERI-07 | 只读 | 查询前后业务记录和值相同；Current、Last Valid、Document Revision、附件、Session 状态不变 | ORM before/after 与事务测试 |
| ERI-08 | M1 兼容 | M1 直接调用 Retriever 的旧参数/返回仍通过既有回归；Agent visibility 和工具绑定规则不退化 | 既有 M1 定向回归 |
| ERI-09 | 异常和空值区分 | 权限/非法字段/工具缺失为可见失败；真正无匹配结果才返回空 records；分页继续读取时不隐瞒 `has_more` | TransactionCase |
| ERI-10 | Agent 指引 | 已接受 Workbook 上用户要补充 Odoo 数据时调用 `office.retrieve`，然后既有编辑流程；按 ID 二次查询；不声称 retrieve 已修改文件 | Prompt/tool-call integration test |

## 11. Contact Excel 两阶段 E2E Acceptance Standard

本节定义必须可复现的集成验收场景。业务模型及地址字段只用于此集成数据，不得进入通用路由或 Retriever 生产分支。真实 UI HVR 按已批准计划纳入 CB-07；CB-05 的组件测试不得冒充该 HVR。

### Stage 1 — 基本联系人字段

1. 在一个获准的隔离测试 Thread 中准备已登记且 Accepted Current 的 XLSX：首行 A1=`名称`、B1=`电话`、C1=`邮件`。
2. 使用当前测试用户可读取的三条不同 `res.partner` 记录；不创建或修改业务联系人。若只能用合成 fixture，必须另有测试数据写入授权。
3. 用户指令：“请从 Odoo 联系人中选择这 3 个联系人，将名称、电话和邮件填写到当前 Excel。”Agent 调用一次或按需分页调用 `office.retrieve`，请求 `id/name/phone/email`。
4. 记录实际返回的三个不同 ID，并以这些结果生成 Candidate 1。由授权的人类在同一 Thread 通过既有流程接受 Candidate 1；禁止直接 ORM 推进。
5. 独立回读接受字节：A1:C1 表头未变；A2:C4 与这三条记录值相符；空字段保持空；文件可读；记录 Candidate/Parent/Current ID、Revision、SHA 和接受结果；业务联系人前后值不变。

### Stage 2 — 按稳定 ID 补充地址

1. 在同一 Thread 和 Current Candidate 1 基础上，用户要求：“请在第四列增加‘地址’表头，并从 Odoo 查询刚才这 3 个联系人的地址，填写到对应行。”
2. Agent 通过第二次独立 `office.retrieve` 调用，以 Stage 1 返回的三个 `id` 构造 domain，并读取可用地址字段（例如 street、street2、city、state_id、zip、country_id）。不得用行号识别记录。
3. 地址只按记录真实非空字段组成；空字段跳过，不添加推断或虚构内容。生成 Candidate 2，来源为 Candidate 1 的 Accepted Current。
4. 人类在同一 Thread 查看并接受 Candidate 2。独立回读：D1=`地址`，D2:D4 对应记录地址；A1:A4 内容及身份关联保持不变，B/C 联系人字段和其它原有内容未因路由而丢失；记录版本链、Revision、SHA、接受结果；业务联系人前后值不变。

### E2E 证据与范围

- 必须能从现有 Thread/tool trace（若当前运行记录可见）或本次运行脱敏证据看到两次 Retriever 调用、参数、返回记录 ID 和结果；第二次查询 ID 集合与第一次相同。本 CC 不新增持久化 provenance 或 snapshot。
- 必须读取真实 Candidate 字节并独立回读；服务端状态与下载/附件内容哈希一致。
- Mock Provider 或 Mock 文件编辑器只证明 Mock 层。若未授权真实 Provider，不发送数据并标记真实 Provider E2E `NOT RUN/BLOCKED`；不得把 Mock 结果称为真实 Provider PASS。
- 合成数据和本地 Mock 可验证路由与编辑机制，但不证明真实联系人数据外发获批。若环境不允许把现有联系人传入测试执行环境，停止该范围，不改联系人、不创建 fixture。
- 按既定计划，完整 UI/HVR 验收在 CB-07 完整业务流程中执行；本标准可在 CB-05 的自动集成层验证，必须按证据层分别标注。

## 12. Acceptance Criteria

CB-05 Contract/Integration 可以提交独立 Final Acceptance 评审的条件：

1. 经唯一 `office` Tool 的 `retrieve` action 从同一 Thread 内成功调用绑定 Retriever；没有新增公开 Tool 或 ORM 查询实现。
2. 当前用户权限、只读、记录身份、数据类型和值语义及分页状态真实由 Retriever 路径保持。
3. M1 调用方式、默认行为、返回格式和既有功能回归通过。
4. E2E 标准已可执行，组件/Mock/ORM/UI/Provider 证据层级如实分开；按 CB-07 计划延期的完整 UI HVR 不得伪报通过。
5. IHR、ATR、FR 与对应证据索引完整；没有通过关闭外发策略或权限门取得测试通过。
6. 未改变 Current/Last Valid/Document Revision，未写入 Odoo 业务数据；后续 Candidate 仅通过既有人工决策和 CB-02 服务推进。

明确不作为本 CC 验收条件：Snapshot/fingerprint/full-incremental、跨页点时一致性、真实外部 Provider 处理、完整 CB-07 HVR、CB-06 Finalize 或生产发布。

## 13. Environment / Runtime Authorization

CC Coding Authorization 与环境操作授权分开。任何后续实施任务必须逐项明确环境和允许的副作用。本 CC 本身不授权：

- 启动/停止/重启 8091、8092、8909 或任何 Odoo/Mock 服务；
- 修改生产/开发 Provider 配置、环境变量、数据策略，或安装依赖；
- 模块升级、数据库 schema 变更、数据库创建/恢复；
- 创建/删除联系人或其他 Odoo 业务记录；
- 读取/处理未获准的真实业务数据，向外部 Provider 发送任何真实业务数据；
- 操作生产附件、Finalize 或部署发布。

运行 CC 自动测试如需数据库写入（包括测试 Thread、附件、版本行和事务测试数据），授权应明确指定开发数据库、可写范围、清理方式和允许的服务操作。真实 UI E2E 另需真实 Thread/用户授权。真实 Provider 外发仍须满足现行授权，不由本 CC 或 Mock 测试推定。

## 14. Required Records: IHR / ATR / FR

- **IHR**：记录获授权后的代码 HEAD/工作区、冻结基线版本、准确文件白名单、Retriever 与 office 调用链、现存测试状态、外发/数据和环境授权范围；不得重写历史报告。
- **ATR**：逐命令记录 schema/路由测试、TransactionCase、M1 回归、联系人自动集成、文件独立回读的实际结果；区分 PASS/FAIL/BLOCKED/NOT RUN 及 Contract/Mock/ORM/Browser/Provider 层，不以测试源码数代替运行结果。
- **FR**：`FR-M2-CB-05_Existing_Retriever_Integration.md` 汇总契约逐项结果及证据索引，列明未完成的 CB-07/HVR、Provider、下载、Release 项；不得因 FR 文档完成而自动声明 Final Accepted 或 Production Release。
- 证据目录建议：`docs/implementation/evidence/CB-M2-CB-05/`；只在未来获授权执行后追加真实日志、输入/输出 XLSX、SHA、版本和脱敏 Trace。

## 15. Stop Conditions

出现以下情况时停止受影响操作并报告证据，不绕过或扩大范围：

- TDD Change / Plan Amendment 尚未生效，或与冻结接口存在未解决冲突；
- 当前 Thread 未绑定可信 Retriever，必须复制 ORM 实现或新增公开 Tool 才可工作；
- 必须使用 `sudo()`、更换用户、绕过 ACL/Record Rules 或写业务记录；
- 现有外发策略阻止真实数据进入 Provider，且没有适用授权；
- E2E 需要未批准的服务启动/重启、模块升级、数据库数据写入或真实数据处理；
- Retriever 返回结果不含可用稳定 ID，且不能在不改变 M1 行为的前提下满足 M2 ID 需求；
- 任何 Candidate/Current 变化不能通过既有 CB-02/03/04 受控流程完成。

## 16. Open Questions / Owner Decisions

1. 是否批准本 TDD V2.0.4 Change 和 Plan V2.0.3 Amendment，并发布对应正式基线？
2. 是否批准本 CC-05 v0.2 冻结并另行授予编码？
3. 后续运行授权需明确具体开发数据库、测试数据/联系人读取范围，以及是否允许 8092/8909 服务操作、模块升级和 Thread/附件/版本写入；本 CC 草案本身不包含这些授权。

## 17. Coding Authorization Gate and Stop

当前状态为 `DRAFT — NOT AUTHORIZED`。在负责人批准 TDD Change、Plan Amendment、冻结 CC 并发出独立 Coding Authorization 前，不得实施或以本草案运行测试。实施授权也不等于环境/Provider/Production 授权。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-10 | DRAFT — NOT AUTHORIZED | 原 Data Tool JSON Snapshot 契约，保留历史 |
| v0.2 | 2026-11-10 | DRAFT — NOT AUTHORIZED | 收敛为复用 Existing Retriever 的最小路由；未编码、未测试、未做环境操作 |
