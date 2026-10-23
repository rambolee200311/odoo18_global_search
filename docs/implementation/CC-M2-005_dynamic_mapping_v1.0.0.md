<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# CC-M2-005 修订草案：AI 智能编排与动态列表映射

## 0. 文档治理

| 项目 | 内容 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-005` |
| Coding Contract | `CC-M2-005` 动态列表映射 V1.0.0 |
| 状态 | **CONDITIONALLY CLOSED — 冻结基线 V1.0.0；负责人于 2026-10-23 批准条件关闭** |
| 既有基线 | `CC-M2-005` FROZEN V1.0.0；本文件不覆盖或改写其历史状态 |
| SRS | `SRS_office_engine_m2_ai_mapping.md` V1.0.0 Frozen |
| TDD | `TDD_office_engine_m2.md` V1.0.0 Frozen；动态列表语义由 `TDD_office_engine_m2_dynamic_rows_addendum_v1.1.0.md` 补充 |
| Implementation Plan | V1.0.0 Frozen；阶段范围由 `IMPLEMENTATION_PLAN_office_engine_m2_dynamic_rows_v1.1.0.md` 补充 |
| 前序 CC | CC-M2-001 至 CC-M2-004；既有 ATR/HVR 状态均保持原记录 |
| 目标 | 将智能映射扩展为可呈现多目标行和列表循环建议的受控流程，并把 Proposal 经完整性校验、用户修订确认后安全编译为 M1 可执行计划。 |

### 0.1 基线与冻结裁定

既有 CC-M2-005 V1.0.0 已冻结且曾进入实施。本文件将负责人批准的动态列表映射扩展记录为独立 V1.0.0 CC；不得把它追溯解释为原冻结范围的一部分。负责人于 2026-10-23 批准冻结本 CC 并进入实施。

冻结的 M2 TDD 定义标量 `mappings[]` 与 M1 `writes[]`。本 CC 不增加模型可生成的坐标/行数 schema：AI 必须对服务端有限目标目录中的每个单元格给出显式标量 mapping；服务端分组元数据只标识授权集合、行索引和目标 ID。TDD 补充已将列表语义限定为“按当前用户可读集合的稳定顺序，将每个已批准行槽位映射到具体 M1 `set_value` writes”，不新增 M1 API。该边界已获本次冻结批准。

本 CC 冻结并授权其白名单范围实施。内置浏览器中的多行卡片展示仅证明 UI 数据绑定；AI 语义映射、列表数据展开和 M1 生成仍须各自通过本 CC 的自动与人工验收。

## 1. 背景与目标

当前映射卡片以服务端目标目录生成下拉行，但真实运行页面只收到单一目标，因此无法审查多项映射。M2 需要让模型把自然语言、模板结构和经授权的 Odoo 字段目录转换为 Proposal；用户可逐行修正；完整性不足时重试一次，仍不足则明确标红并要求澄清，不能确认或渲染。

本修订建立单值目标映射及列表循环映射的**建议与确认契约**。模型输出是不可信数据；字段、目标、集合关系、重复次数和最终坐标均由服务端白名单校验或从服务端元数据重建。

## 2. 上游追溯

### 2.1 SRS

| ID | 相关行为 |
|---|---|
| `FR-M2-001/002/003` | 收集自然语言、模板上下文和当前用户可访问的数据字段。 |
| `FR-M2-004/005` | 生成并校验 Proposal；缺项重试/澄清，不猜值。 |
| `FR-M2-006/007` | 卡片展示和人工修订。 |
| `FR-M2-008` | 用户确认后重新授权取数并交付生成文件。 |
| `BR-M2-001/002/003` | 当前权限、事实来源和完整性优先。 |
| `NFR-M2-001/002/003/004/008` | 数据保密、隔离、可信、安全与受控错误。 |

### 2.2 TDD 适用性与差异

DDD：N/A（沿用批准结论）。

| 冻结设计 | 本 CC 的处理 |
|---|---|
| `Mapping Proposal v1` 只有逐目标标量 `mappings[]` | 保持 V1；AI 对服务端下发的有限目标逐项映射。循环关系是分组上下文，不新增 AI 可生成的 `list_mappings` schema。 |
| `office_mapping_verify` 校验字段、目标、类型和必填完整性 | 保持纯 Python V1 校验；列表行映射成为带命名空间的已授权字段 ID 和显式 element IDs。 |
| M1 `Mapping Plan V1` 是具体 `writes[]` | 服务端将集合每行展开到有限、唯一、可写的具体元素；行数或权限不匹配即拒绝。 |
| Owl 卡片的 CC-M2-004 编辑接口 | 保留 RPC 用户、公司、状态、revision 和白名单校验；一次提交所有逐行 edits 并原子验证。 |

## 3. 范围

### 3.1 范围内

- 服务端在 Provider 请求中明确指示模型可建议单一字段映射，或针对授权集合字段提出列表循环映射（例如 `order_line`）。
- 在 `ai_orchestrator.py` 收集用户意图、模板目标目录、Retriever 授权字段目录；调用当前批准的 Provider；严格解析和校验 Proposal。
- Prompt 必须明确包含以下指令：“你可以为目标生成单一字段映射，也可以生成列表循环映射（如 `order_line`）；只能使用本次提供的目标目录和授权字段目录。”这只是输出格式能力，不授权模型自行增加坐标、行数或 Odoo 字段。
- 对必填目标不完整、未知目标/字段、类型冲突或非法 JSON，最多执行一次包含机器可读错误类别和缺失目标 ID 的修复请求。
- 第二次结果完整且合法时生成待确认映射卡片；仍不完整时进入 `needs_clarification`，逐项标红缺失目标/问题，并禁止确认和 M1 调用。
- 卡片由服务器下发 `mapping_rows[]` 逐行渲染，且以稳定 `row_id` 独立维护选择；可展示只读 `mapping_groups[]` 循环摘要，例如“遍历订单明细，循环填充 10 行”。
- 用户保存/确认后由服务器再次校验整份 Proposal、字段与目标权限、集合字段、revision、状态和循环上限。
- `render_bridge.py` 依据动态列表补充定义，在能力门禁通过后将列表建议展开为具体、已授权的 M1 `writes[]` 并调用现有 M1 同步接口；失败时 fail-closed。
- 每次 Provider 调用使用 CC-M2-002 的 `record_usage()` 记录最少 Usage 元数据，不持久化 Prompt、响应正文或业务样例。

### 3.2 范围外

- 修改冻结 SRS/TDD 的既有文件内容或修改 Odoo 官方源码、其他 Provider、M1 `office_core` / `office_verify` / `office_engine_odoo`。
- 声称当前 M1 原生支持循环渲染；循环必须先展开成已准入的具体目标，或升级 M1 设计并单独审批。
- 任意 Python、公式、domain、动态模型/字段访问；模型不得生成 Odoo 记录 ID、文件路径或执行代码。
- 未经策略批准把真实业务数据发送到模型；不启用其他 Provider/模型。
- `.xls` / `.doc`、PDF、图片、宏及未验证高级 Office 结构。
- 私有 Skill 实现（阶段 6 / CC-M2-006）。

## 4. 变更边界

### 4.1 本次冻结的允许文件白名单

| 路径 | 允许内容 |
|---|---|
| `mymodules/office_engine_m2/services/ai_orchestrator.py` | Prompt 组装、Provider 调用、Proposal 解析/校验、一次修复及状态处理。 |
| `mymodules/office_engine_m2/services/mapping_service.py` | `mapping_rows`/列表摘要服务响应、服务端编辑校验与 Session 状态衔接。 |
| `mymodules/office_engine_m2/services/__init__.py` | 导出 AI 编排及渲染桥接服务，保持现有包入口。 |
| `mymodules/office_engine_m2/services/render_bridge.py` | 经确认映射的权限重验、实时取数、有限目标展开及 M1 调用。 |
| `mymodules/office_engine_m2/controllers/mapping_controller.py` | 既有认证路由的受控输入/输出扩展；不接收客户端 UID 或权限声明。 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 仅扩展既有 `context_json` 的服务端 schema 允许键 `mapping_groups`；不新增字段、权限或状态。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.js` | 多行独立编辑、缺项/澄清状态、循环摘要和按钮状态。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.xml` | `t-foreach` 多行表格、行级错误/摘要展示。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.scss` | 必要的缺项/列表摘要样式。 |
| `mymodules/office_engine_m2/tests/test_ai_orchestrator.py` | Proposal/重试/Usage 测试。 |
| `mymodules/office_engine_m2/tests/test_mapping_rpc.py` | 多行、独立编辑、revision、错误和确认门禁测试。 |
| `mymodules/office_engine_m2/tests/test_render_bridge.py` | 标量与已批准列表展开到 M1 writes 的集成测试。 |
| `mymodules/office_engine_m2/tests/test_office_core_integration.py` | 实际 M1 引擎生成和独立回读。 |
| `mymodules/office_engine_m2/tests/__init__.py` | 注册本 CC 新增的 Odoo 测试模块。 |
| `mymodules/office_engine_m2/__manifest__.py` | 自有 Addon 资产/版本声明。 |
| `mymodules/office_mapping_verify/` | 本次不修改；保持纯 Python Validator V1 契约，不导入 Odoo/网络/数据库。 |
| `docs/implementation/CC-M2-005_dynamic_mapping_v0.2_Draft.md` 及本修订的 IHR/ATR/HVR/FR | 变更契约和证据记录。 |

其他路径均不在本次拟议白名单中。若 M1 API 需要变化，停止本 CC 并单独升级 M1 TDD/实施计划/CC。

### 4.2 保留行为

- CC-M2-001 严格解析、未知键/字段/目标拒绝和完整性校验；新列表 schema 不得削弱旧标量 schema。
- CC-M2-002 Usage ACL 和 `content/tool_calls` 向后兼容。
- CC-M2-003/004 所有者/公司隔离、八状态、revision 和指定消息类型隔离。
- M1 当前用户权限、格式/资源限制、文件回读、私有附件交付及幂等行为。
- 普通聊天消息和非 Office 附件流转不受影响。

## 5. 数据契约提案

### 5.1 服务端卡片上下文

```json
{
  "session_id": 552,
  "revision": 4,
  "state": "waiting_confirm",
  "mapping_rows": [
    {
      "row_id": "xlsx:Sheet1!A1",
      "element_id": "xlsx:Sheet1!A1",
      "label": "xlsx:Sheet1!A1",
      "required": true,
      "source_field": "partner_id.name",
      "clarification": ""
    }
  ],
  "mapping_groups": [
    {
      "group_id": "order_lines",
      "collection_field": "order_line",
      "row_count": 10,
      "summary": "将遍历 order_line 明细，循环填充 10 行"
    }
  ],
  "fields": [
    {"field_id": "partner_id.name", "label": "Customer", "value_type": "string", "sample": null}
  ],
  "missing_targets": [],
  "clarifications": []
}
```

`mapping_rows` 和 `mapping_groups` 必须由服务端从已校验 Proposal、服务端 TargetManifest/授权字段目录构造。`summary` 是纯文本，按文本转义展示。业务值样例只允许来自当前用户授权 Retriever，且遵循批准的数据政策；不得由模型自报。

### 5.2 列表映射契约

列表循环不作为新的 Proposal schema，而由服务端分组上下文、稳定行槽位和显式 `mappings[]` 表达。`source_field` 可使用服务端目录中的命名空间字段 ID，例如 `order_lines::name`；每个映射仍须列出具体目标 ID。模型不得提交 `list_mappings`、集合字段、目标偏移或行数。

```json
{
  "schema_version": "m2.mapping-proposal.v1",
  "mappings": [
    {"element_id": "xlsx:Sheet1!A8", "source_field": "order_lines::name", "value_type": "string"},
    {"element_id": "xlsx:Sheet1!A9", "source_field": "order_lines::name", "value_type": "string"}
  ],
  "clarifications": [],
  "skipped_targets": []
}
```

组关系、目标行槽位、授权字段和 50 行上限均由服务端管理并按 TDD 补充重验。模型不能指定任意行数、坐标偏移公式或创建目标；服务端按关系 recordset 顺序生成具体写入。若数量不匹配必须澄清或拒绝，不截断、不静默覆盖。

## 6. 必需行为

| 当前行为 | 目标行为 |
|---|---|
| 卡片实际上下文仅包含单目标，服务端没有列表分组摘要。 | 服务端返回多项 `mapping_rows[]` 和只读 `mapping_groups[]`；前端逐行渲染并以 `row_id` 保存各自选择。 |
| Prompt/Proposal 仅按单值映射描述。 | Prompt 明确允许单目标字段映射或列表循环建议，并严格限定到提供的授权字段和 TargetManifest。 |
| 5/20 提案缺项时重试和卡片澄清尚未完整贯通。 | Validator 报出所有缺失必填目标；仅修复一次；二次完整则显示待确认卡片，仍缺失则红色逐项提示、确认禁用、M1 调用数为零。 |
| 卡片确认后只有服务端确定目标才允许交给 M1。 | 经批准的列表建议先被服务端展开成目标目录中的具体 writes，再由 M1 自身校验/回读；不能表达时拒绝。 |

## 7. 安全与权限要求

- 只调用当前批准的 OpenAI `gpt-5.6-luna` 路径；所有自动测试使用 Provider Mock，不访问外网。
- Prompt 将模板文字放入明确的数据区，并声明其为不可信内容；任何模型输出均不获得指令优先级。
- `source_field` 必须存在于服务端当前 Retriever 返回并经数据政策筛选的字段目录；列表 `collection_field` 也必须是服务端明确批准的关系字段。
- 每次保存、确认和渲染使用当前用户 `env` 重新校验 session owner/company、状态、revision、目标/字段权限；不使用 `sudo()` 或身份切换读取业务数据。
- 用户修改一个行的下拉框不得改变其他行；客户端提交整体 edits，服务端原子校验整份计划，旧 revision 全部拒绝。
- 错误/澄清文本按纯文本渲染；不得暴露 Prompt、模型原始内容、受限字段、系统路径、内部 traceback 或他人记录存在性。
- 失败、缺项、权限撤销、列表上限超限或 M1 verify 失败均不得生成成功状态或可下载附件。

## 8. 测试契约

| 测试 | 验收条件 |
|---|---|
| 多行上下文 | 服务端返回至少六条不同 `row_id/element_id` 的 `mapping_rows`，浏览器渲染至少六个 `<select>`；修改任一行只改变该行。 |
| 列表摘要 | 服务端下发 10 行集合摘要，卡片准确展示遍历集合字段和行数；摘要纯文本转义。 |
| 多目标 Proposal | Mock 返回至少五个不同目标（`A1`、`B2`、`C3`、`D4`、`E5`）；后端保留五个目标 ID，聊天卡片渲染为五个独立下拉框。 |
| 重试成功 | Mock 第一次返回 5/20、第二次返回完整合法 Proposal（至少包含 `A1`、`B2`、`C3`、`D4`、`E5` 五个不同目标）；两次调用后卡片呈现完整映射，Usage 记录两次，不调用 M1 直到用户确认。 |
| 重试失败 | 两次仍为 5/20；缺失必填项全部标红并可辨认；Confirm 禁用；Session 为 `needs_clarification`；M1 调用数 0、无输出附件。 |
| 恶意/未知字段 | Prompt injection、未知字段、未知目标、重复目标、非法集合/行数均被 Validator 拒绝，不调用 M1。 |
| 服务端并发 | 过期 revision 或不属于当前用户/公司的 Session 被拒绝，状态和映射不变。 |
| M1 标量闭环 | 合成 `.xlsx` 经实际 `office_core.render_candidate` 与 `office_verify.verify_output`；再经 Odoo M1 同步请求成功交付私有附件。 |
| M1 列表展开 | 列表项被确定性映射至 manifest 中有限单元格，实际 M1 生成/回读验证每一项；超出范围 fail-closed。 |
| UI 回归 | 普通聊天消息仍正常；卡片在专用消息类型渲染；保存/确认输入框可继续使用，无 JS 错误。 |

人工验证必须使用 Codex 内置浏览器；截图应同时看见至少六个独立下拉框和循环行数摘要。此截图只作为 UI 证据，不可替代 Provider、Validator、M1 引擎或人工业务验收。

## 9. API / 事务 / 兼容性

- 延续 `/office_engine_m2/mapping/context`、`/update`、`/confirm` 的 authenticated JSON-RPC；服务端响应增加 `mapping_rows`、`mapping_groups`、`missing_targets`。如保留 `targets` 仅作为短期兼容别名，不作为新契约字段。
- `/update` 接收完整编辑集合及 `expected_revision`；所有校验成功后一次性递增 revision，禁止逐行部分写入。
- `/confirm` 对必填缺项、澄清未关闭、过期 revision、未通过服务端列表目录校验的映射一律拒绝。
- Provider 首调/修复与 M1 渲染仍为有界同步调用，遵循 TDD 资源限制；本 CC 不新增队列。

## 10. 数据与迁移

| 项目 | 处理 |
|---|---|
| Session 持久字段 | 复用既有模型；本 CC 不新增 ORM 字段。 |
| Proposal/context JSON | 版本化 JSON；只保存模板结构标识、目标 ID、来源字段 ID、状态/错误类别等最小元数据，不保存 Prompt、Completion 或业务样例明文。 |
| 回滚 | Addon 升级失败恢复既有部署版本；旧 scalar Proposal 必须继续可读。 |

## 11. 验收和关闭门禁

- TDD 动态列表补充及 Implementation Plan 动态列表补充作为本 CC 的适用设计基线；循环映射与 M1 固定 writes 的转换方案明确。
- 自动测试覆盖至少六行渲染与行间独立性、循环摘要、5/20 重试成功/失败、安全拒绝和 revision/ACL。
- 真实 M1 Python 引擎生成、独立回读通过；列表展开仅按已批准的有限目标逐项验收。
- Playwright 自动化通过 UI/RPC；Codex 内置浏览器 HVR 截图通过。
- IHR/ATR/HVR/FR 按证据记录；任何未运行/失败项不得写为 PASS。
- 代码只触及 §4.1 白名单；`office_mapping_verify` 静态依赖扫描无 Odoo/网络/数据库；不改官方或 M1 代码。

## 12. 停止条件

- 服务端未提供有限集合目录、显式目标行槽位及授权字段时，停止列表映射；不得推导坐标或进入 M1。
- `office_mapping_verify` 无法不破坏 V1 Proposal 地扩展版本化 schema 时，先提交 Validator/TDD 兼容方案。
- Retriever 无法在当前用户权限下提供关系字段及列表项字段时，禁止通过任意 ORM/domain 或 `sudo()` 绕过。
- M1 manifest 无法为循环项提供有限唯一目标，禁止根据模型指定行号进行扩展。
- Provider policy 未批准真实业务数据时，只运行合成数据与 Mock。

## 13. 决策记录

| ID | 提案 | 状态 |
|---|---|---|
| CC-DEC-001 | `mapping_rows` 由服务端 TargetManifest 构建；客户端只提交字段选择。 | FROZEN |
| CC-DEC-002 | `mapping_groups` 由服务器计算摘要和有限行槽位，不含可执行代码/坐标偏移。 | FROZEN |
| CC-DEC-003 | 列表映射使用显式目标，最终编译为具体 M1 V1 writes；不修改 M1 核心/API。 | FROZEN；TDD 动态列表补充 V1.1.0 |
| CC-DEC-004 | 首调加一次修复；第二次仍缺项就澄清，禁止确认和 M1 调用。 | FROZEN，追溯 SRS FR-M2-004/005 |

## 14. 追溯矩阵

| 变更 | SRS/TDD | 测试 |
|---|---|---|
| 多目标卡片/独立行 | `FR-M2-006/007`、TDD 动态列表补充 §3 | 多行上下文、浏览器逐行选择 |
| 标量/列表 Proposal | `FR-M2-001/004`、TDD 动态列表补充 §2 | Proposal parser/validator 单测及列表分组验证 |
| 5/20 有限修复与澄清 | `FR-M2-004/005`、`T-M2-MAP-002/003` | 重试成功/失败 |
| 实时取数及 M1 渲染 | `FR-M2-008`、TDD §9 | 实际 M1 引擎与 Odoo 私有交付 |
| 注入、权限和数据最小化 | `NFR-M2-001/002/003/004/008`、`T-M2-SEC-001–004` | 未知值拒绝、跨用户/revision、无泄露 |

## 附录：版本历史

| 版本 | 状态 | 说明 |
|---|---|---|
| V0.2 | Draft | 初始多行/列表映射修订草案。 |
| V1.0.0 | FROZEN | 负责人于 2026-10-23 批准。冻结兼容式逐元素 Proposal、服务端有限列表分组、Retriever 逐记录授权读取、M1 显式 writes 展开与验收门禁。 |

## 条件关闭记录

负责人于 2026-10-23 批准本动态映射 CC 条件关闭。动态行功能的定向测试与内置浏览器 HVR、真实 `office_core` / `office_verify` 回读均按 ATR 记录。共享开发库中的全表 Session 数断言仍为 **FAIL**，不改写为通过；负责人裁定它不阻塞本 CC 关闭，并登记为测试基建债务 `EXEMPTION-CC-M2-005-001`。本状态不证明全 Addon 全绿，也不补足主 CC 中仍未完成的上传入口和完整 UI E2E 场景。

| 处置版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| 执行处置 | 2026-10-23 | CONDITIONALLY CLOSED | 负责人批准；保留所有原始测试状态和未完成范围，详见 ATR。 |
