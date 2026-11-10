# Office Engine M2 — TDD V2.0.4.1 CB-05 Automated User Simulation HVR Amendment

## 文档信息

| 项目 | 内容 |
|---|---|
| 提案 | TDD V2.0.4.1 — CB-05 Automated User Simulation HVR Amendment |
| 状态 | **DRAFT — NOT AUTHORIZED — NOT EFFECTIVE** |
| 基线 | [`TDD_office_engine_m2_v2.0.3.md`](TDD_office_engine_m2_v2.0.3.md) — FROZEN；原件不覆盖 |
| 既有冻结 CB-05 补充 | TDD_office_engine_m2_v2.0.4_CB05_Existing_Retriever_Integration_Change.md — FROZEN；本稿仅提议修订其 HVR 条款 |
| 保留的早期未生效草案 | `TDD_office_engine_m2_v2.0.4_CB05_Change_DRAFT.md` — 保留历史，不与本稿合并视为生效 |
| 配套计划修订草案 | docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.3.1_CB05_Automated_User_Simulation_HVR_Amendment_DRAFT.md — DRAFT |
| CC-05 契约评审稿 | `docs/implementation/CC-M2-CB-05_Existing_Retriever_Integration_v0.2.2.md` — DRAFT，未授权 |
| 日期 | 2026-11-10 |

> 本文件是对既有冻结 TDD v2.0.3 与 CB-05 Retriever Integration 冻结补充的 HVR 定稿提案。此前冻结文件保留不变；本稿在负责人批准前不生效，也不授权编码、测试副作用、Provider 外发、服务操作、模块升级或发布。

## 1. 决定与变更范围

负责人确定：不实施独立 Data Tool JSON Snapshot。CB-05 收敛为 Existing Retriever Integration：Agent 通过唯一公开 office Tool 的 retrieve action 复用当前 Thread 已绑定的 Retriever，按当前用户 ORM 权限再次读取数据，再由 LLM 使用现有 Office 编辑流程处理工作簿。负责人另决定 CC-05 保留 HVR，但采用不要求真人浏览器操作的 Automated User Simulation；本提案只修订 HVR 执行和验收层级，不改变 Retriever、版本或其他 CC 的职责。

本提案只修订此前冻结 CB-05 Retriever Integration 补充中与联系人 HVR 执行层级及证据边界有关的条款，不改变冻结 TDD v2.0.3 或先前冻结 Retriever 路线的其他内容。Candidate/Validator/Version/确认/交付职责及其余 CC 范围保持不变。如本提案获批，应与 TDD v2.0.3 及此前冻结的 Retriever Integration 补充合并阅读；本稿不单独替代或覆盖任一冻结文件。

## 2. 变更前后

| 条款 | 冻结 v2.0.3 中 CB-05 相关要求 | 本提案替换后的要求 |
|---|---|---|
| §1.1、§1.2、§2.1 | 将后续取数称作独立 Data Tool，并要求快照/来源完整性契约 | 通过现有 `office` Facade 的 `retrieve` action 薄路由复用注册 Retriever；不新增公开 Tool 或查询服务 |
| §2.3 | typed snapshot、`full`/`incremental`、完整集合同步语义 | 同一 Thread 按需进行独立只读查询；返回既有 Retriever 结果及最小查询范围、页信息和读取时间 |
| §5.3 | 查询与 Workbook 版本强绑定、快照重验及快照用于刷新 | 读取不改变或锁定 Workbook 版本；后续编辑仍使用当时的 Accepted Current 和现有版本门 |
| §8.1 | `get_authorized_data` 与强制快照/指纹 | `office(action="retrieve", query_spec)`，返回既有 Retriever 结果 |
| §10、§11.1 | `full`/`incremental`、snapshot、fingerprint 测试 | 路由、权限、只读、身份、类型、分页、M1 兼容及两轮联系人场景 |

## 3. 拟替换的 TDD 条款

### 3.1 §1.1 / §1.2 中 CB-05 的描述

将“独立 Data Tool / typed snapshot”相关描述替换为：

> **保留**现有 Odoo Record Retriever，继续服务 M1 首轮 Mapping。对已有 Accepted Current Workbook 的 M2 Thread，唯一公开的 `office` Tool 提供只读 `retrieve` action；内部通过该 Thread 的 `tool_ids` 找到已注册、已绑定的 `odoo_record_retriever`，使用 `llm.tool.execute()` 既有验证和执行路径。不得增加第二个公开 Tool、重复实现 ORM 查询或改变 M1 Retriever 默认调用与返回格式。

### 3.2 §2.1 组件职责表中的 Odoo Data Tool 行

将原“返回带记录身份、业务键、类型、快照范围、分页/完整性和来源信息的 JSON”替换为：

> 通过唯一 `office` Tool 的 `retrieve` action 复用当前 Thread 已绑定的 Odoo Record Retriever，按当前用户 ORM 权限只读查询；返回 Retriever 记录/分页结果及最小查询范围与读取时间。不得定位工作表/单元格、产生编辑指令、写 XLSX、以行号识别记录或新增独立 Snapshot 协议。

### 3.3 §2.3「后续 Odoo 数据补充/刷新」替换文本

```text
用户在同一 Thread 请求补充 Odoo 数据
  → Agent 调用 office(action="retrieve", query_spec)
  → office Facade 确认当前 Thread/用户及 Accepted Current 上下文
  → 通过 thread.tool_ids 找到已绑定的 odoo_record_retriever
  → 用既有 llm.tool.execute() 在当前用户 ORM 环境执行
  → 返回该 Retriever 的原始 records 或分页对象，并附最小查询范围/读取时间
  → LLM 按用户意图决定如何应用数据
  → 后续工作簿修改继续走现有 Candidate、Validator、版本和用户决策流程
```

查询输入沿用现有 Retriever 的模型、domain、fields、order、limit、offset 和 `include_pagination` 语义。为支持稳定后续读取，结果必须保留 Retriever 返回的 `id`；Agent 依据它再次查询同一记录，不得使用 Excel 行号替代身份。`office.retrieve` 应取得并保留分页信息（`count`、`offset`、`limit`、`has_more`）；分页调用若未指定排序，M2 路由以 `id` 作为默认顺序；显式排序由既有 Retriever 追加 `id` tie-breaker。Agent 只在按稳定顺序继续读取后续页时，才可说明已取完其查询范围。各页是独立 ORM 查询，不构成点时一致快照；不得从缺失记录推断业务记录删除。

结果可附服务端生成的 `retrieved_at`，仅说明该次读取时间，不是快照 ID、数据版本或跨页一致性保证。查询范围由模型、domain、fields、order 和分页参数确定；不得将其描述为整个 Odoo 模型的全量。`null`、`false`、`0`、`0.0`、空字符串及日期等值沿用 Retriever/JSON 当前序列化的类型和值语义；不得由 Office 路由统一按真假值过滤。

此 action 只读 Odoo，不改 Odoo 业务记录，不写 XLSX，不接受 Candidate，不推进 Current、Last Valid 或 Document Revision。取数成功不代表工作簿已更新或用户任务已完成。Workbook 内容仍以 CB-02 Accepted Current 字节为准；编辑与接受继续使用现有 Candidate/Validator/Version/用户决策链。取数不绑定或锁定 Workbook 版本；若后续编辑遇到现有版本冲突，按现有版本门处理。

所有现有用户权限、ACL、字段访问、Record Rules、多公司边界及已生效的数据外发授权继续适用。本提案不新增外发分类、审批、配置、留存或删除管理功能，也不放宽现有授权。

### 3.4 §5.3「多轮修改与数据刷新」CB-05 段落替换文本

同一 Office Thread 可以多次调用 `office(action="retrieve")`。每次调用均通过同 Thread 绑定的既有 Retriever，在当前用户 ORM 上下文中独立读取；结果通过现有 Tool 结果返回 Agent。可追溯性限于现有 Tool call/message 能力，不承诺额外的持久化 provenance。该行为不创建 Snapshot，不锁定读取时 Workbook 版本，不修改 Session 或文件版本状态。后续写入始终基于当时的 Accepted Current 字节，并通过既有版本冲突和用户决策流程。

Agent 在用户要求“将 Odoo 数据补充到当前工作簿”时先调用 `retrieve`，只请求用户目标所需的模型、字段和记录范围。后续对已识别记录取数时使用 Retriever 返回的 `id` 过滤；需更多结果时按稳定 order 和 offset 读取并检查 `has_more`。对跨页期间的数据变化不作原子快照保证；若所需数据范围不明，应向用户澄清，不得静默扩大查询。取数输出仅作为 LLM 输入，不能凭工具成功声称 Excel 已更新。

### 3.5 §8.1 逻辑接口表中的取数条目替换文本

| 入口 | 输入 | 输出与边界 |
|---|---|---|
| `office(action="retrieve", query_spec)` | 沿用现有 `odoo_record_retriever` 的 `model`、`domain`、`fields`、`order`、`limit`、`offset`、`include_pagination` 参数；服务端从当前消息解析用户与 Thread，模型参数均是不可信输入 | 既有 `office` 结果信封，`data` 保留 Retriever 返回的 records 列表或分页对象；另提供规范化查询范围及 `retrieved_at`。保留记录 `id`、值类型和页字段；无 Excel 坐标/动作、Snapshot、Fingerprint 或删除语义 |

路由只调用绑定在当前 Thread 的已启用 Retriever：`thread.tool_ids` 查找 `odoo_record_retriever`，随后以当前 `tool_message` 作为上下文调用其既有 `.execute(query_spec)`。不存在、未绑定或不可执行时明确返回失败/阻断；不得回退管理员身份、另行 ORM 查询或直接调用底层方法。

### 3.6 §10「数据刷新」测试行替换文本

| 测试层 | 必需覆盖 | 验收证据 |
|---|---|---|
| 同 Thread Odoo 数据读取 | 单一 `office` Tool 的 `retrieve` 路由；同一 Thread 多次读取；复用绑定 Retriever 的 `llm.tool.execute()`；查询范围、稳定 `id`、类型和值语义、分页字段；当前用户权限及只读；M1 调用和返回格式不变 | Tool schema/dispatcher 测试、Retriever 执行调用断言、Odoo ORM 权限/只读测试、M1 定向回归；不得以 Snapshot、CDC、Fingerprint、跨页点时一致快照或 Workbook 版本锁作验收项 |
| 联系人补充 HVR | 同一 Thread 中自动模拟两轮用户指令：首次通过 office.retrieve 读取 3 条联系人并填名称/电话/邮件，生成 Candidate 1；经现有正式接受服务模拟用户接受后成为 Current。第二轮再次调用 office.retrieve，按首轮 res.partner.id 精确读取地址，生成 Candidate 2 并经同一正式接受服务接受 | 必须使用 Automated User Simulation；经现有 Agent/Tool 与业务接受链，不直接 ORM 写 Candidate/Current。独立回读验证 A–C 未变化、D 地址正确，以及 Current、Revision、SHA、父子版本链一致。不得称为真人手工验证；不要求真实 Provider 或完整浏览器 UI，后两者归 CB-07 |

### 3.7 HVR 层级与交付记录（补充）

CC-05 必须保留联系人两阶段 HVR，执行方式为 Automated User Simulation：自动化向同一 Thread 提交两轮用户意图，经过 Agent、office.retrieve 与现有 Candidate/正式接受服务；接受由已认证测试用户上下文发起，并由正式业务服务校验和推进。不得直接 ORM 写 Candidate、Current、Last Valid 或 Revision 状态。HVR 报告记录两次查询、联系人 ID、Candidate、接受结果、Current/Revision/SHA/版本链及独立 XLSX 回读；未执行步骤标记 NOT RUN，不得标 PASS。此 HVR 不要求真人浏览器操作、真实外部 Provider 或完整浏览器 UI；真实 Provider 与完整 UI 留给 CB-07。

CC-05 的 IHR、ATR、HVR、FR 分别记录实施、自动化测试、上述自动化用户模拟业务场景和最终评审。单元、集成、回归测试结果写入 ATR；不得用 ATR 组件测试冒充 HVR。

### 3.8 §11.1 中 Data Tool 对照行替换文本

| 主题 | V1.x 冻结设计 | V2.0.3 基线 | 本提案处置 |
|---|---|---|---|
| Odoo 后续读取 | Retriever 为 M1 Mapping 提供当前用户授权字段数据 | 后续数据刷新经 Data Tool 返回带完整快照语义 JSON | 保留 Retriever 及 M1 行为；增加 `office.retrieve` 薄路由复用现有 Retriever；取消独立快照与同步协议，不改变后续 Excel Candidate/版本流程 |

## 4. 明确取消或延期的设计

本轮不实现且不作为 CB-05 隐含验收条件：

- 独立 Snapshot Service、Snapshot 模型或持久快照；
- `snapshot_id`、强制 query/content fingerprint；
- `full`/`incremental`、通用 CDC 或删除检测语义；
- 跨页点时一致性快照；
- 读取时强制绑定/锁定 Workbook 版本；
- 新的数据分类、外发审批、Provider 策略配置、留存或删除管理功能。

这不是删除已存在权限或数据策略。当前用户 ACL/Record Rules/多公司限制、已生效的 Provider 外发授权、M1 Retriever、安全及版本门继续有效。

## 5. 保持不变

- M1 Mapping、Retriever 现有调用方式、Tool 注册和返回结构；
- 唯一公开 M2 `office` Tool；
- Odoo 业务数据只读；
- 当前用户 ORM、ACL、字段访问权、Record Rules 和多公司边界；
- Retriever 的查询、排序、分页、身份和值序列化能力；
- CB-01 Provider Adapter，CB-02 Version/Current 权威，CB-03 ValidationReceipt，CB-04 用户决策/候选编排，以及 CB-06 Preview/Finalize/Delivery；
- 人类对业务结果和 Candidate 的最终决定权。

## 6. 生效及配套变更

原 TDD v2.0.3 与 V2.0.4 CB-05 Retriever Integration 补充继续保留其既有冻结状态。本 v2.0.4.1 HVR 修订及对应 Plan Amendment、CC-05 v0.2.2 均须经负责人评审冻结后，才替换各自 CB-05 HVR 条款。冻结不自动授权编码、环境操作、真实业务数据处理、外部 Provider 调用或生产发布；这些门禁仍分别适用。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V2.0.4 | 2026-11-10 | FROZEN — CB-05 CHANGE — EFFECTIVE | 原 Retriever Integration 补充基线；保留，不覆盖 |
| V2.0.4.1 | 2026-11-10 | DRAFT — NOT AUTHORIZED — NOT EFFECTIVE | 仅将 CC-05 联系人 HVR 定义为 Automated User Simulation，并明确 CB-07 浏览器/Provider 边界；未编码、未测试、未操作环境 |
