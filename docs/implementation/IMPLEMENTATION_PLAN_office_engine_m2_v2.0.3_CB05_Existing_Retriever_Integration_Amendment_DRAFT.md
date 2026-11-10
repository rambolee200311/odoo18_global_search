# Office Engine M2 — Implementation Plan V2.0.3 CB-05 Existing Retriever Integration Amendment

## 文档信息

| 项目 | 内容 |
|---|---|
| 修订目标 | 冻结 Implementation Plan V2.0.2 的 CB-05 条款 |
| 状态 | **DRAFT — NOT AUTHORIZED — NOT EFFECTIVE** |
| 计划基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.2.md` — FROZEN；原件不覆盖 |
| 配套设计 | `docs/design/TDD_office_engine_m2_v2.0.4_CB05_Existing_Retriever_Integration_DRAFT.md` — DRAFT |
| 配套契约 | `docs/implementation/CC-M2-CB-05_Existing_Retriever_Integration_v0.2.md` — DRAFT |
| 日期 | 2026-11-10 |

> 本 Amendment 只调整 CB-05 的范围、依赖描述和验收条款。其他 CC 的分工、依赖、测试和实施顺序不变；本文不授权编码、测试副作用、Provider 外发、模块升级、服务操作或生产发布。

## 1. 修订目的

按负责人确定的最小路线，把 CB-05 从 **Read-only Data Tool JSON Refresh / Snapshot** 收敛为 **Existing Retriever Integration**：保留现有 Retriever 查询能力和 M1 行为，在唯一公开的 `office` Tool 增加 `retrieve` action，内部调用 Thread 已绑定的 `odoo_record_retriever`。用户可以在已有 Accepted Current Workbook 的同一 Thread 中按需再次读取 Odoo 数据，再由 LLM 使用现有工作簿编辑/候选流程。

本修订不更改 CB-01、CB-02、CB-03、CB-04、CB-06、CB-07 的目标、范围或阶段验收，也不改变“CB-05 不阻塞不使用 Odoo 数据刷新的 CB-06 编辑和交付链”。

## 2. Plan V2.0.2 的最小替换项

### 2.1 §1.2 能力差异表中的 Retriever 行

将“Data Tool JSON refresh / Snapshot 协议尚未实现，因此新增快照能力”替换为：

| 现有能力 | 可复用 | 最小缺口/计划处置 |
|---|---|---|
| `odoo_record_retriever` 通过当前用户 ORM 读取，支持模型/domain/fields/order/limit/offset 及可选分页结果 | 完整复用其既有 `llm.tool.execute()`、ORM、校验、序列化及权限路径；保留 M1 注册、输入和返回格式 | M2 已有 Accepted Current Workbook 的 Thread 中，Agent 不能经唯一公开 `office` action 在同一条调用链上再次取数。仅增加 `office.retrieve` 路由与 Agent 指引；不复制查询实现 |

### 2.2 §3.2 依赖图和说明

仅将 §3.2 原依赖图中的节点标签 `CB-05 Read-only Data Tool JSON` 改为 `CB-05 Existing Retriever Integration`；保留图内其它所有节点、边和阶段顺序。

CB-05 仍只依赖 CB-02 已接受的 Current Workbook 上下文及 CB-04/office Thread 编排接缝；它不更改其接口权威，不重复其版本或候选服务。CB-05 在 CB-07 汇入完整用户流程验收；CB-06 不依赖 CB-05，其他 CC 的既定依赖不变。

### 2.3 §8「CC-M2-CB-05」整节替换文本

#### CC-M2-CB-05 — Existing Retriever Integration

**目标**：在已有 Accepted Current Workbook 的同一 Office Thread 中，让 Agent 通过 `office(action="retrieve")` 再次读取当前用户可访问的 Odoo 数据；之后由 LLM 使用现有 Candidate/Validator/Version/用户决策流程补充当前工作簿。

**实现边界**：唯一公开 Tool 仍为 `office`。Facade 从当前 Thread 的 `tool_ids` 取得已绑定且启用的 `odoo_record_retriever`，经既有 `llm.tool.execute()` 路径调用；不直接调用底层方法、不新增查询服务、不复制 ORM 查询。既有 Retriever 保持 M1 默认调用、注册、参数含义及返回结构。

**保留**：当前用户 ORM、ACL、字段访问、Record Rules、多公司权限；model/domain/fields/order/limit/offset；记录 `id`；类型和值语义；读取时间与查询范围；现有页级 `count/offset/limit/has_more`；业务数据只读。M2 分页调用未提供 order 时使用 `id` 顺序，显式排序沿用 Retriever 的 ID tie-breaker。若 Agent 需要后续读取同一批记录，必须使用 Retriever 返回的 ID。外发安全以现有生效授权为准。

**明确不做**：独立 Data Tool 或第二个公开 Tool；ORM 查询框架；Snapshot Service/model/ID；query/content fingerprint；`full`/`incremental`/CDC；跨页点时一致性快照；读取时 Workbook 版本锁；新的 Provider 数据分类、审批、配置、留存/删除管理；模板/模型/字段专用规则；Workbook 写入或 Candidate/Version 接受。

**Agent 时机**：用户在当前 Accepted Workbook 基础上要求补充 Odoo 数据时，先用 `office(action="retrieve")`，仅查询用户所需的字段和范围；以返回 ID 进行后续按记录查询，以稳定 order/offset/`has_more` 继续分页。范围不清时澄清，不能把分页读取描述为数据库点时快照，不能从未返回推断删除。取数完成后按现有 `office` 编辑和用户决策流程继续。

**测试与验收**：验证 Facade 只暴露 `office`，action 正确路由到当前 Thread 绑定的 Retriever；数据、错误、分页和类型语义来自现有 Retriever；当前用户权限与只读行为有效；M1 现有 Retriever 流程不变；联系人两阶段场景规范见 CC-05。自动化组件测试在 CB-05；完整真实 Thread/UI 的联系人 E2E/HVR 汇入既定 CB-07 验收，不能以 Mock、TransactionCase 或服务端调用冒充真实 UI。

**交付**：CC-05 授权契约、IHR、ATR、单轮 FR；测试证据需分别标注 Contract/ORM Integration/Mock/UI/Provider 层级及未执行项。CC-05 组件关闭不代表 HVR、真实 Provider、CB-06 交付或生产发布通过。

**PASS**：M2 route 通过既有 Retriever 读取并保留查询结果/页状态/ID/值语义；权限和只读约束通过；M1 回归未见由改动引起的回归。**FAIL**：出现新增 Tool/重复 ORM 查询、越权/写入、错误吞掉失败或破坏 M1 行为。**BLOCKED**：代码依赖冻结 TDD Change 尚未批准，或执行需要未批准的环境操作/数据外发。**延期**：联系人完整 UI HVR 由 CB-07 执行。

### 2.4 §11 测试矩阵中的 CB-05 行

将“Data Tool JSON 完整性及 ORM 权限 / schema、full/incremental、fingerprint”替换为：

| 关注项 | 主要 CC | Contract / Mock | Odoo TransactionCase / HttpCase | Thread / 文件回读 | 通过边界 |
|---|---|---|---|---|---|
| Existing Retriever Integration | CB-05 | `office.retrieve` 参数/结果适配；既有 `llm.tool.execute()` 路由；M1 默认调用和返回兼容 | 当前用户 ORM、ACL/字段权限/Record Rules/多公司、只读、稳定 ID、值类型和分页；无 Workbook/业务记录副作用 | 两阶段联系人 Excel 场景在同一 Thread：两次 Retriever 查询、第二次按首轮 ID、两次 Candidate/接受、内容/版本/SHA 回读；完整 UI HVR 归 CB-07 | 不要求 snapshot、full/incremental、fingerprint、CDC、Workbook 读取锁或跨页一致快照；不得把 Contract/Mock/ORM 测试写成真实 UI/Provider E2E |

## 3. 其余基线保持不变

- CB-05 仍不作为 CB-06 普通编辑/交付的前置依赖；原计划阶段顺序和七轮 CC 分解不变。
- CB-01 Provider Adapter、CB-02 版本服务、CB-03 Validator、CB-04 编排、CB-06 Preview/Finalize/Delivery、CB-07 整体回归范围不变。
- SRS/TDD/数据外发授权的现有有效安全边界继续适用；本修订不产生新的数据外发许可。
- Thread Tool 可见性和 M1 现有 `odoo_record_retriever` 用法保持原样。M2 Current 状态下仍只向 Agent 暴露 `office`，Retriever 仅由 Facade 内部调用。

## 4. 版本与生效

负责人批准后，应将本 Amendment 与 TDD Change 一并纳入相应正式版本；批准本计划修订不等于 CC Coding Authorization、服务/数据库操作授权、Provider 外发授权或 Production Release。批准前冻结 Plan V2.0.2 不变。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V2.0.3 CB-05 Amendment | 2026-11-10 | DRAFT — NOT AUTHORIZED — NOT EFFECTIVE | 将 CB-05 Snapshot 范围改为复用 Retriever 的薄路由；其他 CC 不变；未编码或执行测试 |
