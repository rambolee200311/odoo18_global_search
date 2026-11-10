# Office Engine M2 — Implementation Plan V2.0.3.1 CB-05 Automated User Simulation HVR Amendment

## 文档信息

| 项目 | 内容 |
|---|---|
| 修订目标 | 冻结 Implementation Plan V2.0.2 的 CB-05 条款 |
| 状态 | **DRAFT — NOT AUTHORIZED — NOT EFFECTIVE** |
| 计划基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.2.md` — FROZEN；原件不覆盖 |
| 配套设计修订草案 | docs/design/TDD_office_engine_m2_v2.0.4.1_CB05_Automated_User_Simulation_HVR_Amendment_DRAFT.md — DRAFT，不生效 |
| CC-05 契约评审稿 | `docs/implementation/CC-M2-CB-05_Existing_Retriever_Integration_v0.2.2.md` — DRAFT，未授权 |
| 日期 | 2026-11-10 |

> 本稿仅提议对既有冻结 CB-05 Amendment 的 HVR 条款作最小版本化修订。此前冻结计划与 Amendment 保留不变；本稿获负责人批准前不生效。其他 CC 的分工、依赖、测试和实施顺序保持原样；本文不授权编码、测试副作用、Provider 外发、模块升级、服务操作或生产发布。

## 1. 修订目的

按负责人确定的最小路线，把 CB-05 从 **Read-only Data Tool JSON Refresh / Snapshot** 收敛为 **Existing Retriever Integration**：保留现有 Retriever 查询能力和 M1 行为，在唯一公开的 `office` Tool 增加 `retrieve` action，优先从 Thread 已绑定的 `odoo_record_retriever` 调用。用户可在 Office Thread 中按需再次读取 Odoo 数据，再由 LLM 使用现有工作簿编辑/候选流程。

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

**测试与验收**：验证 Facade 只暴露 office，action 正确路由到当前 Thread 绑定的 Retriever；数据、错误、分页和类型语义来自现有 Retriever；当前用户权限与只读行为有效；M1 现有 Retriever 流程不变。CC-05 必须完成联系人两阶段 Automated User Simulation HVR：同一 Thread 两次 retrieve、第二次按首轮 ID、两次 Candidate 经现有正式接受服务推进，并独立回读文件与版本证据。不得直接 ORM 写 Candidate/Current，不得将未执行项标 PASS。HVR 不要求真人或完整浏览器 UI，也不要求真实外部 Provider；CB-07 继续负责真实 Provider 和完整浏览器验收。

**交付**：CC-05 授权契约、IHR、ATR、HVR、单轮 FR。ATR 记录单元/集成/回归测试；HVR 标注 Automated User Simulation 并记录两阶段实际结果和证据。证据按 Contract/ORM/Mock/Automated User Simulation/Browser/Provider 层级区分。HVR 未实际执行时不得报告 PASS。CC-05 完成不代表 CB-07 的真实 Provider、完整浏览器流程、CB-06 交付或生产发布通过。

**PASS**：M2 route 通过既有 Retriever 读取并保留查询结果、页状态、ID、值语义；权限和只读约束通过；M1 回归未见由改动引起的回归；联系人两阶段 Automated User Simulation HVR 通过现有正式业务服务完成接受，并经独立回读证明文件和版本链。**FAIL**：出现新增 Tool/重复 ORM 查询、越权/写入、绕过正式接受服务、错误吞掉失败或破坏 M1 行为。**BLOCKED**：运行需要未批准的环境操作/数据外发，或现有正式接受入口不能由受控自动化用户模拟调用。真实 Provider 与完整浏览器用户流程留给 CB-07。

### 2.4 §11 测试矩阵中的 CB-05 行

将“Data Tool JSON 完整性及 ORM 权限 / schema、full/incremental、fingerprint”替换为：

| 关注项 | 主要 CC | Contract / Mock | Odoo TransactionCase / HttpCase | Thread / 文件回读 | 通过边界 |
|---|---|---|---|---|---|
| Existing Retriever Integration + HVR | CB-05 | office.retrieve 路由/结果、既有 llm.tool.execute、M1 兼容；联系人两阶段 Automated User Simulation：同一 Thread 两次读取，第二次按首轮 ID，两次 Candidate 经正式接受服务推进 | 当前用户 ORM、ACL/Record Rules/公司边界、只读、稳定 ID、类型/分页；HVR 经正式应用服务，不直接 ORM 写 Candidate/Current | 两阶段 XLSX 独立回读：A–C 不变、D 地址匹配、Candidate/Current/Revision/SHA/父子版本链正确；不要求真人浏览器或真实 Provider | 不要求 Snapshot/full-incremental/fingerprint/CDC/Workbook 读取锁/跨页一致快照；CB-07 负责真实 Provider 与完整浏览器验收；未执行 HVR 不得标 PASS |

## 3. 其余基线保持不变

- CB-05 仍不作为 CB-06 普通编辑/交付的前置依赖；原计划阶段顺序和七轮 CC 分解不变。
- CB-01 Provider Adapter、CB-02 版本服务、CB-03 Validator、CB-04 编排、CB-06 Preview/Finalize/Delivery、CB-07 整体回归范围不变。
- SRS/TDD/数据外发授权的现有有效安全边界继续适用；本修订不产生新的数据外发许可。
- Thread Tool 可见性和 M1 现有 `odoo_record_retriever` 用法保持原样。M2 Current 状态下仍只向 Agent 暴露 `office`，Retriever 仅由 Facade 内部调用。

## 4. 版本与生效

本 Amendment 已获负责人批准并冻结，是 Plan V2.0.2 的 CB-05 有效补充条款；其它条款继续按 Plan V2.0.2 执行。它不等于 CC Coding Authorization、服务/数据库操作授权、Provider 外发授权或 Production Release。可在后续整合版中合并，但无需等待整合版才按本修订理解 CB-05。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V2.0.3 | 2026-11-10 | FROZEN — CB-05 AMENDMENT — EFFECTIVE | 原 Retriever Integration Amendment；保留，不覆盖 |
| V2.0.3.1 | 2026-11-10 | DRAFT — NOT AUTHORIZED — NOT EFFECTIVE | 仅将 CB-05 HVR 改为 Automated User Simulation，并保留 CB-07 真实 Provider/浏览器验收；未编码或执行测试 |
