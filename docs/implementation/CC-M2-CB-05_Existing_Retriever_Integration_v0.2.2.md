# CC-M2-CB-05 — Existing Retriever Integration

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 |
| 契约 | CC-M2-CB-05 — Existing Retriever Integration |
| 版本 | v0.2.2 |
| 状态 | **FROZEN — CODING AUTHORIZED** |
| 生效基线 | TDD V2.0.3 FROZEN + FROZEN CB-05 Retriever Change；拟追加的 HVR Amendment 尚为 DRAFT |
| 配套 TDD Change 草案 | `docs/design/TDD_office_engine_m2_v2.0.4.1_CB05_Automated_User_Simulation_HVR_Amendment_DRAFT.md` |
| 配套 Plan Amendment 草案 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.3.1_CB05_Automated_User_Simulation_HVR_Amendment_DRAFT.md` |
| 保留的历史契约 | `CC-M2-CB-05_Data_Tool_JSON_Refresh_v0.1.md` — 不覆盖，待新契约批准后标注 superseded |
| 日期 | 2026-11-10 |

> 负责人于 2026-11-10 批准冻结本 CC 并进入实施。该决定授权按本契约编码；不授权数据库/服务操作、模块升级、真实业务数据外发或生产发布。配套 HVR TDD/Plan successor 文件仍为 DRAFT，不取代冻结上游；本 CC §11 的 Automated User Simulation 是本轮实施与验收的直接契约。

## 1. Contract Goal

在 Office Thread 中，用户要求从 Odoo 取数以补充当前工作簿时，支持 Agent 再次读取当前用户有权访问的数据，并把结果用于后续 Excel 编辑。

唯一公开的 M2 Agent Tool 仍为 `office`。新增 `action="retrieve"` 的唯一实现目的，是通过薄路由复用该 Thread 已绑定的既有 `odoo_record_retriever`。取数只读 Odoo；编辑继续通过现有 Candidate、Validator、Version 和用户决策流程。M1 首轮 Mapping 的 Retriever 调用方式和返回格式不变。

## 2. Authority Baseline and Required Approval Sequence

| 基线 | 当前事实/约束 |
|---|---|
| Frozen TDD V2.0.3 + Frozen CB-05 Retriever Change | v2.0.3 其它条款不变；既有冻结补充将 Snapshot 范围改为 Existing Retriever Integration。HVR successor v2.0.4.1 仍是 DRAFT；本 CC §11 的 HVR 条款依据负责人本次冻结 CC 的明确授权实施。 |
| Frozen Implementation Plan V2.0.2 + Frozen CB-05 Retriever Amendment | 计划其余 CC 条款不变；CB-05 已改为 Existing Retriever Integration。HVR successor v2.0.3.1 仍是 DRAFT；本 CC §11 的 HVR 条款依据负责人本次冻结 CC 的明确授权实施。 |
| CB-01..04 | 已有 Provider、版本、Validator 与 Orchestration 能力按其已接受范围复用；不因本 CC 重开或重构。CC-04 HVR/其它 Open 状态不在本 CC 内修改。 |
| 当前代码证据 | `llm.tool.execute()` 在 `mail_message.py` 中通过 Thread `tool_ids` 查找工具；Retriever 实现在 `llm_tool_record_retriever.py`；M2 `_office_bind_tools` 将 Retriever 绑定到 Thread，而 Accepted Current 路径仅过滤模型可见 Tool 列表，并未从 `thread.tool_ids` 移除它；`office` dispatcher 尚无 retrieve 分支。绑定路径仍需在获授权的运行测试中确认。 |
| 版本门边界 | CB-02/04 是读取结果进入后续 Candidate 编辑/用户决策的依赖；不是只读 `retrieve` 的前置门。本 CC 将 TDD Change §2.3 的 Accepted Current context 解释为后续编辑步骤所需上下文，不用于拒绝只读取数；该解释列为 CC 冻结前的 Owner Decision，必要时以最小 TDD erratum 收口。 |

负责人已批准冻结本 CC 并进入实施；该决定是本 CC 的 Coding Authorization。此前 Retriever 技术路线补充已冻结；本次 HVR 对齐的 TDD/Plan successor 文件仍为 DRAFT，本实施按本 CC 的明确 HVR 验收要求执行，不将其标记为已冻结。本 CC 不扩大其他范围，也不代表环境或 Provider 授权。

## 3. In Scope / Out of Scope

### 3.1 In Scope

- 在既有 `office` Tool schema 中增加 `retrieve` action 及与当前 Retriever 一致的 `query_spec`。
- 在现有 office dispatcher 中解析当前用户、当前 Thread 和当前 tool message。
- 优先复用该 Thread `tool_ids` 中已绑定的 `odoo_record_retriever`；如生命周期检查发现未绑定，提交最小适配选择供负责人裁定。
- 通过该 `llm.tool` 记录的既有 `.with_context(message=tool_message).execute(query_spec)` 调用路径执行；复用现有 schema 验证、ORM、权限及序列化。
- 返回原 Retriever 的记录或分页对象，保持记录 ID、当前值语义与页级状态；不要求额外结果结构。
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
2. `retrieve` 是只读查询，不得要求 Accepted Current，也不得检查 Current/Last Valid/Document Revision 一致性；不能因为无关 Candidate 或 Workbook 版本状态拒绝查询。CB-02/04 版本门只应用于后续文件编辑、接受和交付。
3. 首选从同一 `thread.tool_ids` 查找并复用 `odoo_record_retriever`，但不把“必须在该字段中找到”设成产品硬门禁。编码前先核查 Accepted Current 状态下 Retriever 的实际绑定/可见生命周期；如果未绑定，记录最小兼容接法供负责人裁定，不得仅因缺少该字段就判定功能不可实现，也不得自行扩大权限、改注册或改绑工具。
4. Retriever 可用时，使用其现有 `.with_context(message=tool_message).execute(validated_query_spec)` 路径。禁止直接调用底层 `odoo_record_retriever_execute()`、另建 ORM 查询、使用 `sudo()` 或切换为别的用户。若既有信任路径不够用，先提交最小适配选择，不绕过调用链。
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

具体可选/默认值以及输入类型以已注册 Retriever schema 为准，不在 M2 路由中发明第二份查询语义。Facade 对分页读取请求 `include_pagination=true`，并保留 `count/offset/limit/has_more`；现有 Retriever 的 limit 1–500、非负 offset 及 ORM 行为原样复用。为使分页身份稳定，M2 action 在 order 未提供时使用 `id` 顺序；显式 order 由现有 Retriever 追加 `id` tie-breaker，不改变 M1 默认排序。

查询模型、字段、domain 和 order 都是不可信 Agent 参数；由现有工具验证并由 ORM 再执行访问控制。空 domain 表示当前用户在该模型上的 ORM 可见范围，Agent 不得静默把未限定的用户请求扩大成全模型查询；范围有歧义先澄清。

### 4.3 Output Contract

成功输出沿用 `office` action 必需的外层状态包装，将既有 Retriever 结果放入 `data`；另带两个轻量的当次请求字段：

```json
{
  "status": "completed",
  "operation_status": "odoo_data_retrieved",
  "operation_executed": false,
  "artifact_state": "not_presented",
  "delivery_state": "not_finalized",
  "data": {
    "records": [], "count": 0, "offset": 0,
    "limit": 100, "has_more": false
  },
  "query_scope": {"model": "<model>", "domain": [], "fields": ["id"], "order": "id"},
  "retrieved_at": "<server-generated ISO-8601 UTC time>"
}
```

`data` 必须是现有 Retriever 的原样结果：分页模式为 `{records,count,offset,limit,has_more}`，非分页模式为 records 列表。`query_scope` 仅由规范化后的本次输入参数组成；`retrieved_at` 是服务端生成的一次性读取时间。两者不要求额外 ORM 查询、持久化、指纹或复杂校验，不构成 Snapshot/版本绑定，也不提供点时一致性。分页期间数据可变化；`has_more=false` 不构成跨页原子快照保证。

每条记录的 `(model, id)` 是稳定查询身份。若请求字段投影未包含 `id`，Facade 必须确保该 M2 返回仍保留 `id`，但不得改变 M1 Retriever 原始返回。follow-up 查询必须用返回 ID，而非 Excel 当前行号、名称相似度或排序位置。

JSON 应保留 Retriever 的 `null`、`false`、`0`、`0.0`、空字符串、日期等值序列化行为；Office route 不得以 truthiness 过滤。关系字段遵守 Retriever/Odoo 当前表示，不由 M2 新增递归展开。

工具结果表示“取数调用成功/失败”，不表示文件已编辑、候选已验证、业务意图已覆盖或 Current 已推进。取数不写 Odoo、Session、Workbook、附件或版本数据。

## 5. Agent Call Timing and Workflow

当 Office Thread 中用户要求从 Odoo 取数以补充当前工作簿时，Agent 必须：

1. 确认查询模型、记录范围和所需字段足够明确；不清楚时请求用户澄清。
2. 调用 `office(action="retrieve", query_spec=...)`。仅请求实现用户意图所需的最小字段；用户指定记录集合时沿用其明确筛选条件。
3. 如需跟进读取同一批记录，使用上一次返回的记录 ID 构造精确过滤；如需分页，使用稳定排序、连续 offset，检查每页 `has_more`，对不完整页/错误如实反馈。
4. 收到数据后按用户意图使用现有 `office` plan/edit 流程生成 Candidate；按现有 review/accept/reject 流程处理。不得把 Retriever 结果当作 Candidate，也不得绕过 CB-02/03/04。
5. 每一轮读取均是新的当前用户 ORM 查询；不缓存或重放上轮数据来冒充新读取。Retriever 查询不检查或锁定 Workbook 版本；若后续编辑被现有版本门拒绝，按该结果向用户报告，不构造新的快照状态机。

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
| Thread/用户不可访问 | 使用现有 AccessError/office outcome 机制阻断，不执行 Retriever |
| Current/Last Valid 或 Document Revision 不匹配 | 不阻断只读取数；只有后续修改/接受时才由现有版本流程判定 |
| Retriever 不在 `thread.tool_ids` 或当前绑定路径不可用 | 先记录实际生命周期/信任边界和最小适配选项；不得仅凭此事实认定查询能力不存在，也不得未经裁定新增注册/改绑。若没有可批准的现有执行路径，再报告受限范围 |
| 参数非法或字段/模型不可访问 | 保留现有工具/ORM 错误语义；不得返回成功空列表 |
| 查询无匹配行 | 返回成功的空 records 和有效分页元数据；与错误分开 |
| 有后续页 | 保留 `has_more=true`；Agent 继续按稳定排序分页或说明尚未读取完 |
| 取数成功但 Provider 策略禁止外发 | 继续由现有策略阻断；不得关闭策略、改用权限更高用户或泄漏 Tool result |
| 取数成功、Excel 编辑失败 | 不声称文件已更新；Current/Last Valid 按既有 CB-02 规则保持 |

不在本 CC 新建状态枚举、数据策略引擎、查询框架或 Excel 结果判定规则。

## 8. Integration Boundaries

| 组件 | 本 CC 责任 | 明确不做 |
|---|---|---|
| `office` Facade / dispatcher | 加 `retrieve` 参数 schema/action 路由；首选调用 Thread 已绑定 Retriever，若绑定生命周期不满足则先提交最小适配裁定 | 新增公开 Tool 或改动其它 action 的语义 |
| Odoo-LLM Retriever | 作为已存在的查询、ORM 权限和序列化实现被调用 | 修改其 M1 注册、默认值、查询实现或直接返回结构 |
| Agent instruction | 说明何时 retrieve、何时澄清、以 ID 追读、再走编辑流程 | 模板/业务字段特例或让 Agent 报告未经验证的完成 |
| CB-01/02/03/04 | 后续编辑时复用既有 Provider/版本/验证/决策契约 | 重写或绕过其服务 |
| CB-06/07 | 复用 Preview/Finalize 原接口；CC-05 自行完成自动化用户模拟 HVR；CB-07 负责真实 Provider 与完整浏览器用户体验验收 | 把自动化用户模拟写成真人验证，或把 Mock/服务端结果写成真实 Provider/浏览器 E2E |

## 9. Implementation File Allowlist

### 9.1 允许修改（仅未来单独获得 Coding Authorization 后）

- `mymodules/office_engine_m2/models/office_mapping_tools.py` — `office` Tool schema 与 facade 参数透传。
- `mymodules/office_engine_m2/services/edit_orchestrator.py` — `retrieve` 分支；解析 Thread 绑定的 Retriever，并通过现有 `.execute()` 调用。
- `mymodules/office_engine_m2/models/llm_thread.py` — 仅修改 M2 Agent 指引，说明读取时机和 ID/page 用法；保留 tool visibility。
- `mymodules/office_engine_m2/tests/` — 通用 action routing、Retriever 复用、权限/只读、值/分页、M1 兼容和联系人流程测试。
- `docs/implementation/IHR-M2-CB-05.md`、`ATR-M2-CB-05.md`、`HVR-M2-CB-05_Automated_User_Simulation.md`、`FR-M2-CB-05_Existing_Retriever_Integration.md` 及 `docs/implementation/evidence/CB-M2-CB-05/` — 仅记录授权后的真实事实。

### 9.2 禁止修改

- `mymodules/odoo-llm/llm_tool/models/llm_tool_record_retriever.py`、`llm_tool.py`、`mail_message.py`、Retriever XML/注册、manifest；M1 Retriever 行为必须复用。
- CB-01/02/03/04、M1 `office_core`/`office_verify`、Provider 配置、现有外发安全实现、DB schema/models、其它 CC 和冻结基线文件。
- 任何用于绕过 ORM/ACL/Record Rules、现有 Provider 政策或版本门的文件。

如只读代码审查证明上述白名单不能满足调用链要求，停止相关修改，提交最小差异和证据，等待单独批准；不得自行扩展白名单。

## 10. Automated Test Matrix

| ID | 场景 | 必须断言 | 证据级别 |
|---|---|---|---|
| ERI-01 | `office` Tool schema/dispatch | 唯一公开 M2 Tool 仍是 `office`；`retrieve` 是允许 action；未知参数按封闭 schema 拒绝 | Contract/Mock |
| ERI-02 | 内部 Retriever 解析 | 优先复用 `thread.tool_ids` 中已绑定 Retriever 并通过 `.with_context(message=tool_message).execute(query_spec)` 调用；若 Accepted Current 状态下未绑定，先保留实际代码证据并提交最小适配决定，不预设不可实现 | TransactionCase / Mock call assertion / read-only lifecycle check |
| ERI-03 | 用户/Thread 权限 | 无权访问 Thread 时，在 Retriever 执行前阻断；合法 Thread 的 retrieve 不因缺少 Current 或无关 Candidate/Revision 状态而阻断，且不改 Session/Current | TransactionCase |
| ERI-04 | 查询和分页投影 | `data` 原样返回现有 Retriever records 或分页对象；保留 count/offset/limit/has_more 和 `id`；M2 缺省分页顺序使用 `id`，显式顺序保留 ID tie-breaker；`query_scope` 从输入得出、`retrieved_at` 一次生成；不引入 snapshot/full/incremental 字段 | Contract/TransactionCase |
| ERI-05 | 值语义 | `None`、`False`、整数零、浮点零、空字符串及日期按现有 Retriever JSON 行为保留 | Retriever integration assertions；不新增 serializer |
| ERI-06 | 权限和多公司 | 当前用户 ACL、字段访问、Record Rules、公司边界在调用链生效；无 sudo/切换用户/直接 SQL | 多用户 TransactionCase |
| ERI-07 | 只读 | 查询前后业务记录和值相同；Current、Last Valid、Document Revision、附件、Session 状态不变 | ORM before/after 与事务测试 |
| ERI-08 | M1 兼容 | M1 直接调用 Retriever 的旧参数/返回仍通过既有回归；Agent visibility 和工具绑定规则不退化 | 既有 M1 定向回归 |
| ERI-09 | 异常和空值区分 | 权限/非法字段/工具缺失为可见失败；真正无匹配结果才返回空 records；分页继续读取时不隐瞒 `has_more` | TransactionCase |
| ERI-10 | Retriever 到编辑接缝 | 合成数据下，Agent/Mock Tool loop 将 `office.retrieve` 的记录和值交给现有 Office edit path 并生成 Candidate；不要求接受 Candidate，不修改本地业务规则；按 ID 二次查询 | Mock + existing Orchestrator integration test |

## 11. Contact Excel 两阶段 HVR — Automated User Simulation

CC-05 保留 HVR，必须以 Automated User Simulation 验证联系人两阶段场景；不要求真人逐步操作、真人浏览器、完整浏览器 UI 或真实外部 Provider。此项是 CC-05 的验收门槛，不因 CB-07 尚未执行而延期。CB-07 另行验证真实 Provider 和完整浏览器用户体验。

自动化模拟必须通过现有 Agent/office Tool 调用链和正式 Candidate/接受业务服务。测试自动向同一隔离 Office Thread 提交两轮用户意图，并以受控测试身份模拟用户；接受动作必须走现有正式应用入口，由正式业务服务校验用户、Candidate、来源版本和并发条件。不得用 ORM 直接改 Candidate 状态、Current/Last Valid 指针或 Revision 来伪造接受。ORM 可用于只读前后核验。

### Stage 1 — 名称、电话、邮件

1. 在获准的测试环境准备同一 Thread 的初始 Workbook，A1=名称、B1=电话、C1=邮件。测试记录/附件等准备步骤遵守单独环境授权。
2. 自动模拟用户指令：“请从 Odoo 联系人中选择这 3 个联系人，将名称、电话和邮件填写到当前 Excel。” Agent 在同一 Thread 调用 office(action=retrieve)，按当前用户权限读取 3 条联系人及稳定 res.partner.id。
3. 记录三条不同 ID 及对应值，生成 Candidate 1。自动化用户模拟通过现有正式接受入口接受 Candidate 1；验证 Candidate 1 成为 Current，记录 Current、Last Valid、Document Revision、Parent Version、SHA 和接受结果。
4. 独立读取 Current 附件字节并回读 XLSX：A1:C1 表头正确；A2:C4 与对应三条记录的名称/电话/邮件相符；空源字段保持空；文件可读取。对联系人记录只读核验前后未变化。

### Stage 2 — 按第一阶段 ID 补充地址

1. 在同一 Office Thread 中自动模拟新指令：“请在第四列增加‘地址’表头，并从 Odoo 查询刚才这 3 个联系人的地址，填写到对应行。”
2. Agent 再次独立调用 office(action=retrieve)，使用 Stage 1 同一组三个 res.partner.id 做精确过滤，读取当前用户可访问的地址字段（如 street、street2、city、state_id、zip、country_id）。不得以 Excel 行号、名称相似度或排序位置代替记录身份。
3. 生成 Candidate 2，其 Parent/Input 必须为已接受的 Candidate 1 Current。自动化用户模拟经同一正式接受入口接受 Candidate 2；以只读方式核对 Current/Last Valid/Revision 和版本链正确推进。
4. 独立读取 Candidate 2 的真实附件字节并回读 XLSX：D1=地址；D2:D4 与对应 Odoo 记录的实际非空地址字段一致，空字段跳过、不编造；A–C 的数据/值和身份对应关系与 Candidate 1 完全一致；SHA 与版本记录一致。

### HVR 证据与判定

- 报告名：HVR-M2-CB-05_Automated_User_Simulation.md；明确标注 Automated User Simulation，不得称为真人手工验证。
- 记录两轮模拟用户输入、Thread 标识、两次 Retriever 调用及参数、返回 ID、Candidate 1/2、正式接受调用结果、Parent/Current/Last Valid/Revision/SHA、附件回读断言，以及联系人数据前后未变的只读证据。脱敏凭据和不必要的个人数据。
- HVR 必须实际执行；未运行步骤标记 NOT RUN，失败标记 FAIL/BLOCKED，不以测试源码、Mock 单测、静态检查或 Agent 自述替代 HVR 结果。
- 可使用 Mock Provider、合成 Workbook 及现有测试适配器；这仅证明对应本地/Mock 层。无需真实 Provider 外发或完整浏览器 UI。使用真实联系人记录时须经当前用户 ORM 权限读取，且不得发送至未授权 Provider；测试数据与环境写入遵守单独授权。
- 不创建或修改真实业务记录，不新增持久化 provenance/snapshot，不改变 Retriever 或 Candidate 生产规则。

## 12. Acceptance Criteria

CB-05 Contract/Integration 可以提交独立 Final Acceptance 评审的条件：

1. 经唯一 `office` Tool 的 `retrieve` action 从同一 Thread 内通过现有可信机制成功调用 Retriever；首选 Thread 绑定路径。若需改用经负责人批准的最小内部适配，应记录实际取舍；没有新增公开 Tool 或 ORM 查询实现。
2. 当前用户权限、只读、记录身份、数据类型和值语义及分页状态真实由 Retriever 路径保持。
3. M1 调用方式、默认行为、返回格式和既有功能回归通过。
4. CC-05 自动化用户模拟 HVR 两阶段均实际完成：同一 Thread 两次 office.retrieve，第二次精确复用首轮三个联系人 ID；两次 Candidate 都经现有正式接受服务接受，Current/Revision/SHA/父子版本关系正确；独立 XLSX 回读证明 A–C 未变化且 D 地址正确。不得直接 ORM 写 Candidate/Current。证据按 Contract/Mock/ORM/Automated User Simulation/Browser/Provider 层级区分。
5. IHR、ATR、HVR、FR 与对应证据索引完整；没有通过关闭外发策略或权限门取得测试通过。
6. retrieve 本身不写 Odoo 业务数据或推进版本；HVR 中 Candidate 的接受必须经过现有正式业务服务。两个接受动作后 Current、Last Valid、Document Revision 按既有 CB-02 规则正确推进至 Candidate 2；不得直接 ORM 写状态。

明确不作为本 CC 验收条件：Snapshot/fingerprint/full-incremental、跨页点时一致性、真实外部 Provider、真人浏览器操作、完整浏览器 UI HVR、CB-06 Finalize 或生产发布。CC-05 Automated User Simulation HVR 是必需验收项；CB-07 负责真实 Provider 与完整浏览器用户体验。

## 13. Environment / Runtime Authorization

CC Coding Authorization 与环境操作授权分开。任何后续实施任务必须逐项明确环境和允许的副作用。本 CC 本身不授权：

- 启动/停止/重启 8091、8092、8909 或任何 Odoo/Mock 服务；
- 修改生产/开发 Provider 配置、环境变量、数据策略，或安装依赖；
- 模块升级、数据库 schema 变更、数据库创建/恢复；
- 创建/删除联系人或其他 Odoo 业务记录；
- 读取/处理未获准的真实业务数据，向外部 Provider 发送任何真实业务数据；
- 操作生产附件、Finalize 或部署发布。

运行 CC 自动测试如需数据库写入（包括测试 Thread、附件、版本行和事务测试数据），授权应明确指定开发数据库、可写范围、清理方式和允许的服务操作。本 HVR 通过自动化消息/工具调用模拟同一 Thread 中的用户，不要求浏览器。测试身份及其数据范围由执行授权确定。真实 Provider 外发仍须满足现行授权，不由本 CC 或 Mock 测试推定。

## 14. Required Records: IHR / ATR / HVR / FR

- **IHR**：记录获授权后的代码 HEAD/工作区、冻结基线版本、准确文件白名单、Retriever 与 office 调用链、现存测试状态、外发/数据和环境授权范围；不得重写历史报告。
- **ATR**：记录单元、集成和回归测试的真实命令、数量、PASS/FAIL/BLOCKED/NOT RUN 与 Contract/Mock/ORM 层级；不以测试源码数代替运行结果。
- **HVR**：HVR-M2-CB-05_Automated_User_Simulation.md 记录上述两阶段自动化用户模拟的实际结果、正式接受流程和证据；明确不是真人手工验证。任何未执行项不得标 PASS。
- **FR**：FR-M2-CB-05_Existing_Retriever_Integration.md 汇总契约逐项、ATR、HVR 与证据索引，另列真实 Provider/浏览器/CB-07、下载、Release 未完成项；不得因 FR 完成自动声明 Final Accepted 或 Production Release。
- 证据目录建议：`docs/implementation/evidence/CB-M2-CB-05/`；只在未来获授权执行后追加真实日志、输入/输出 XLSX、SHA、版本和脱敏 Trace。

## 15. Stop Conditions

出现以下情况时停止受影响操作并报告证据，不绕过或扩大范围：

- TDD Change / Plan Amendment 与本 CC/实际冻结接口存在未解决冲突；
- 经代码证据确认不存在可复用的可信 Retriever 执行路径，且负责人尚未裁定任何最小适配；
- 必须使用 `sudo()`、更换用户、绕过 ACL/Record Rules 或写业务记录；
- 现有外发策略阻止真实数据进入 Provider，且没有适用授权；
- E2E 需要未批准的服务启动/重启、模块升级、数据库数据写入或真实数据处理；
- Retriever 返回结果不含可用稳定 ID，且不能在不改变 M1 行为的前提下满足 M2 ID 需求；
- 任何 Candidate/Current 变化不能通过既有 CB-02/03/04 受控流程完成。

## 16. Open Questions / Owner Decisions

1. 已裁定：负责人批准本 CC v0.2.2 冻结并进入编码实施；该决定不授权本节列出的环境操作。
2. 已裁定：只读取数不要求 Accepted Current 或 Workbook 版本门；版本门仅适用于后续 Candidate 编辑、接受和交付。
3. 未决环境授权：运行 TransactionCase/HVR 前须明确开发数据库、测试数据写入/联系人读取范围、清理方式及服务操作权限；本次编码授权不包含这些环境操作。

## 17. Coding Authorization Gate and Stop

当前状态为 `FROZEN — CODING AUTHORIZED`，依据负责人 2026-11-10 的明确指令。编码仅限本 CC §9 白名单。实施授权不等于数据库/服务、模块升级、真实 Provider/外发或生产发布授权；未经单独授权不得执行这些操作。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-10 | DRAFT — NOT AUTHORIZED | 原 Data Tool JSON Snapshot 契约，保留历史 |
| v0.2 | 2026-11-10 | DRAFT — NOT AUTHORIZED | 收敛为复用 Existing Retriever 的最小路由；未编码、未测试、未做环境操作 |
| v0.2.1 | 2026-11-10 | DRAFT — NOT AUTHORIZED | 按评审修改 Retriever 绑定为首选路径、移除读取的 Current 版本门、简化非持久化结果元数据并明确 CC-05/CB-07 验收边界；未编码、未测试 |
| v0.2.2 | 2026-11-10 | FROZEN — CODING AUTHORIZED | 负责人批准冻结并进入实施；保留 Automated User Simulation HVR，正式服务接受、两阶段同 Thread/contact ID/XLSX/版本回读；本次只授权编码，环境/数据库/HVR 执行仍须另行授权 |
