# Office Engine M2 TDD V2.0.4 — CB-05 Minimal Data Retrieval Change

## 文档信息

| 项目 | 内容 |
|---|---|
| 修订目标 | TDD V2.0.4（仅 CB-05 条款） |
| 状态 | **DRAFT — PENDING REVIEW — NOT EFFECTIVE** |
| 基线 | `TDD_office_engine_m2_v2.0.3.md` — FROZEN；原件保留不覆盖 |
| 配套计划变更 | `IMPLEMENTATION_PLAN_office_engine_m2_v2.0.3_CB05_Amendment_DRAFT.md` |
| 配套契约 | `CC-M2-CB-05_Data_Tool_JSON_Refresh_v0.2.md` — DRAFT，未授权编码 |
| 变更范围 | 同一 Thread 中经现有 `office` Facade 多次读取 Odoo 数据，复用 `odoo_record_retriever` |
| 日期 | 2026-11-10 |

> 本文件是针对 Frozen TDD 的版本化最小变更提案，不替换或修改 V2.0.3。只有评审批准并合并到完整的新 TDD 后才生效。本变更不授权编码、测试、Provider 外发、数据库操作或发布。

## 1. 变更依据与目标

负责人批准方案 B：保持唯一公开的 M2 `office` Tool，由现有 Facade 通过薄 action 路由调用既有 `odoo_record_retriever`。CB-05 不重复实现 ORM 查询，不更改 M1 Retriever 的参数或返回格式。

本次产品目标是：在同一 Office Thread 中，用户可按需多次读取当前用户有权访问的 Odoo 数据，由 LLM 根据用户意图决定如何应用到当前 Excel。重复读取是独立的只读查询，不隐含创建同步任务、持久快照或逐次锁定工作簿版本。

## 2. 对 TDD 的最小变更

### 2.1 §2.3「后续 Odoo 数据补充/刷新」替换文本

```text
用户在同一 Thread 请求读取数据
  → office Facade 的只读读取 action
  → 复用现有 odoo_record_retriever，在当前用户 ORM 环境中执行 query_spec
  → 返回带稳定记录身份、必要字段类型、查询范围/时间和分页状态的 JSON
  → LLM 根据用户意图决定是否及如何把数据应用到当前有效 Workbook
  → 后续文件修改仍经既有 Candidate、Validator、Version 和用户决策流程
```

Data Tool 只读取并返回 JSON，不指定 Excel 坐标、行号或写入动作，不写 Odoo 业务数据或 XLSX。查询范围由模型、domain、fields、order 与页参数明确表达；范围只指该次 ORM 查询，不代表整个 Odoo 模型。记录身份使用 `(model, record_id)`；显式提供的业务键是普通数据值，不默认唯一，也不自动合并。

不要求 `snapshot_type`、通用 CDC 或增量变化游标。分页状态描述本次查询页及是否还有后续页；只有消费端实际取得声明范围所需的全部页后，才可声称该范围已枚举完成。任何缺失记录均不得单独解释为业务记录删除。

### 2.2 §5.3「多轮修改与数据刷新」相关段落替换文本

同一 Thread 可进行多次独立 Odoo 数据读取。每次读取在调用时使用当前用户 ORM 权限，返回该次的查询范围、读取时间、记录和值类型以及页状态；现有 Tool call/message trace 是读取出处。读取不修改 Session、Current、Last Valid 或 Document Revision，也不要求锁定当前 Workbook 版本。

分页沿用 Retriever 已有的 `limit`、`offset`、`order`、`count` 和 `has_more` 行为。跨页不承诺点时一致性；若数据在分页期间变化，结果不得声称来自原子数据库快照。消费端可以识别页间重复记录 ID；无法证明完整或存在页间变化时应如实说明并重新读取或澄清。不能将查询时刻等同于数据在整个分页期间保持不变。

后续 Excel 编辑始终基于 CB-02/CB-04 当前有效文件版本及其既有版本校验。数据读取与 Workbook 版本不做强制一一绑定；读取来源可从同一 Thread 的 Tool call/message trace 追溯。数据查询成功不表示 Workbook 已更新、Candidate 已生成或用户已接受。

### 2.3 §8.1 `get_authorized_data(thread/session, query_spec)` 条目替换文本

| 逻辑入口 | 输入 | 输出与边界 |
|---|---|---|
| `office(action=refresh_data, query_spec)` | 模型、domain、fields、order、limit、offset；所有值均作为不可信参数由现有 Tool schema、Retriever 与 ORM 处理 | 现有 `office` Tool 结果信封中的 typed JSON records、`(model, record_id)`、查询范围、查询时间、count/offset/limit/has_more 及明确结果状态；不返回 Excel 坐标、编辑命令、独立 snapshot ID、强制 query/content fingerprint |

Facade 的内部实现复用现有 Retriever 读取路径，不提供第二个公开 M2 Tool，不改变 M1 Retriever 输出。每页都回传规范化后的查询范围与页参数，供 Thread 消息记录和调用方识别；不要求 query fingerprint、内容指纹或跨页持久身份。

### 2.4 §10「数据刷新」测试行替换文本

| 测试层 | 必需覆盖 | 验收证据 |
|---|---|---|
| Data Tool 读取 | 同一 Thread 多次读取；单页及分页；显式 query scope/time；`(model, record_id)`；必要字段类型和值语义；`has_more` 与不完整/失败区分；当前用户 ACL、字段访问、Record Rules、多公司；只读；M1 原 Retriever 调用/返回格式不变 | 合成数据 Odoo TransactionCase/HttpCase、Tool result 回读及业务值前后比较；每页 trace 可追溯；不要求 Snapshot Service、CDC、跨页点时一致快照、真实 Provider 外发或 HVR |

## 3. 外发授权边界

本变更不新增数据分类、字段审批、Provider 策略配置、审批工作流或留存管理功能。所有现有有效的数据外发授权边界继续适用；不得通过删除、关闭或绕过现有安全检查把未授权的真实业务数据交给外部 Provider。

合成数据和 Mock 测试可独立验证 Facade、Retriever、序列化及权限行为，不要求真实业务数据外发。真实业务数据进入外部 Provider 上下文仍须符合当时适用的既有授权；该授权不是本 CC 组件测试的强制前置，也不因本变更而被推定已获得。

## 4. 明确保留与延期

**保留：**当前用户 ORM/ACL/Record Rules/多公司权限；query model/domain/fields/order/pagination；稳定记录身份；必要字段类型和值语义；查询范围和时间；分页完整性及错误状态；Odoo 业务数据只读；后续 Candidate/Validator/Version 流程。

**本轮不要求：**独立 Snapshot Service 或数据库模型、新 `snapshot_id`、强制 `content_fingerprint`、通用 `incremental`/CDC、跨页点时一致性快照、读取时强制 Workbook 版本锁，以及新的外发规则管理系统。

既有 CB-01/02/03/04、M1 Mapping、CB-06 Preview/Finalize/Delivery 及其安全边界不因本变更改变。CB-05 仍不阻断不使用 Odoo 数据刷新的 Excel 编辑/交付链。

## 5. 版本与生效

该提案仅调整 TDD V2.0.3 §2.3、§5.3、§8.1、§10 中与 CB-05 直接相关的条款及其对应解释；其余 Frozen TDD 条款不变。批准后应发布完整 TDD V2.0.4 并保留 V2.0.3 历史文件。本提案本身不标记 Frozen 或生效。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V2.0.4 CB-05 Change | 2026-11-10 | DRAFT — PENDING REVIEW — NOT EFFECTIVE | 按负责人批准的最小功能范围起草；未改原 Frozen TDD，未编码、测试或外发数据 |

