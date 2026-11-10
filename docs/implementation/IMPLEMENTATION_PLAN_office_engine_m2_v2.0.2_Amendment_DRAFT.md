# Office Engine M2 Implementation Plan V2.0.2 — Amendment Proposal

## 文档信息

| 项目 | 内容 |
|---|---|
| 文档 | Office Engine M2 Candidate B Implementation Plan Amendment |
| 修订版本 | V2.0.2 Amendment Proposal |
| 状态 | **DRAFT — NOT AUTHORIZED — NOT EFFECTIVE** |
| 基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` — FROZEN；保留不覆盖 |
| 设计依赖 | `docs/design/TDD_office_engine_m2_v2.0.3_Amendment_DRAFT.md`；须先批准/合并 |
| CC 依赖 | 冻结 CC-M2-CB-04 v0.2；CC-M2-CB-02 Amendment v0.1 待评审 |
| 日期 | 2026-11-08 |

> 本稿只提出版本化实施计划修订。它不是完整替代计划，不修改 v2.0.1，不授权编码、数据库操作、Provider、Browser 或发布。只有批准后并入新的完整 Plan 版本才生效。

## 1. 变更范围

仅对齐 Candidate B 的条件式 Candidate 接受、每轮 Intent Binding、`office` Facade staged migration，以及 CB-04 与 CB-06 的接口边界。保留七轮 CC 分解、CB-01/02/03/04/05/06/07 的总体职责、线性流程、完整 Proposal 重编译/当前文件版本链原则、M1 初始填充、真实多轮 Provider 验收归 CB-07、CB-05 不阻断不使用 Odoo 刷新的编辑交付链。

## 2. 建议替换/补充原计划条款

### 2.1 §7 CB-04 — Intent / Confirmation / Edit Orchestration

在原 CB-04 范围上补充：

- Intent 绑定本轮真实用户 `mail.message`、Thread/Session 和 CB-02 当前父版本；每轮 Candidate 有受信 `intent_message_id`，保留现有 `source_message_id` 首轮上传语义。Intent/Effect digest 不替代 CB-02 hash/revision。
- 明确、低风险请求按当前用户原意图直接执行；如果 Candidate 经 CB-03 独立 `VERIFIED`，实际 Effect 完全匹配服务端绑定授权，且权限/版本/资源 Gate 重验通过，可调用 CB-02 自动接受，不额外重复确认。
- 需业务确认的风险只有在用户实际确认的范围覆盖真实 Candidate Effect 时才能条件式接受。范围不匹配/存在业务裁决/结果无法充分证明时，Candidate 保持已验证非 Current，交 CB-06 Review；安全/权限/验证失败不可由用户确认绕过。
- `VERIFIED`、`ACCEPTED`、`DELIVERED` 分别记录。CB-04 不生成 CB-06 Preview/正式附件，也不声称附件已可下载。
- 多轮编排仍使用 Mock Provider + 实际 CB-02/03 Service 验证 V1→V2→V3；后续轮次的父版本必须为前一轮已接受文件。
- 新增一个对 Agent 的 `office` Facade 承载 Candidate B 调用；Agent 不直接暴露 Validator、Version Service 或为 Candidate B 新建独立工具。保留 M1 旧工具兼容；本 CC 不做全量 M1 Tool Registry 迁移，执行报告不得声称全局已只剩一个 Office Tool。

### 2.2 §9 CB-06 — Preview / Review / Finalize / Delivery

保留 CB-06 负责 Preview、Finalize、附件和 Browser/下载。增加 Review handoff：

1. CB-04 把仅通过 CB-03 验证的 Candidate，以及验证/风险/模型声明/未验证事实传给 CB-06。
2. 对未被已存在授权覆盖的业务决定，CB-06 可向用户呈现私有非当前 Candidate 供 Review，并收集 Accept/Reject/Revise；该 Review 产物不等于 Current、Last Valid 或正式附件。
3. Accept/Reject 必须回到 CB-04/CB-02 的受控服务接口。CB-02 按当前用户、Thread/Session、parent、Candidate bytes/SHA、Document revision、Intent/Effect 和真实决策消息重验。拒绝不推进任何当前指针或 revision。
4. 对用户原始意图/有效确认已覆盖且效果严格匹配的 Candidate，CB-04 可自动接受，CB-06 仅处理后续 Preview/正式交付；不增加重复 Accept 操作。
5. 正式 Finalize 只引用已 `accepted_current` 版本。Preview/Finalize/Attachment/Browser/Delivery 分层报告，不把候选文件存在作为交付事实。

### 2.3 Candidate 生命周期及依赖关系

```text
User Intent → Intent Binding / Context / Confirmation Gate
  → CB-01 Candidate bytes → CB-02 Candidate registration
  → CB-03 ValidationReceipt → CB-04 authorization/effect assessment
      ├─ matching authorization → CB-02 atomic accept
      └─ unresolved business choice → CB-06 private Review → user decision → CB-02 accept/reject
  → CB-06 Preview / Finalize / Delivery
```

CB-02 保持版本与接受的唯一权威服务；CB-03 仅验证 Candidate 并登记 typed Receipt；CB-04 仅确定该验证事实是否被用户授权覆盖及是否发出接受请求；CB-06 管界面/正式附件/交付。任何 Agent/RPC 路径不得直写版本字段。

## 3. `office` Facade 兼容迁移口径

- Candidate B 路由只向 Agent 暴露一个 `office` Tool，动作 schema 有限且版本化，当前仅承载批准的 Candidate B 编排操作。
- 复用 Odoo-LLM 的 `llm.tool` decorator registry 和 Thread `tool_ids` 机制；CB-04 以一个受装饰入口分派内部服务，不公开多个 Candidate 专用 Tool。
- M1 既有 Tool/函数和外部调用暂时保持兼容；M1 全量迁移至 Facade 单独安排，除非后续明确变更范围，不纳入 CB-04/CB-06 验收。
- 过渡期间对外必须如实说明：Candidate B 使用单一 Facade；全局 Tool Registry 仍含 M1 历史工具。不得宣称最终全系统已统一。

## 4. 验收和阶段边界

### 4.1 CB-04 Contract / Integration

按冻结 CC-M2-CB-04 v0.2 的测试矩阵验收：Explicit+effect match 自动接受、不重复确认；授权外 Effect/不充分验证不自动接受；歧义澄清；风险确认及确认范围绑定；ACL 与安全不可绕过；拒绝不推进；旧 Intent/版本/SHA/revision/授权失效；真实每轮消息绑定；失败/indeterminate 不盲重试；多轮使用上一 Accepted 文件；单一 Candidate B `office` Facade；M1 回归。

可使用 Mock Provider、合成 XLSX、CB-02/03 实际服务与经单独授权的非生产 Odoo TransactionCase。Contract/TransactionCase 不等于真实 Provider/Browser/生产验收。

### 4.2 CB-06 M2-BASIC-EDIT

保持用户可观察的“提交明确 Excel 意图 → Adapter 返回真实修改文件 → CB-03 独立验证 → 符合明确授权时 CB-02 自动接受 → CB-06 Preview/Finalize/下载 → 用户独立回读”的验收闭环。若是未授权业务风险或效果不确定，必须走 Review/Accept/Reject 分支；不能用自动接受测试替代 Review 分支。真实 Provider、Browser 和预算须有对应独立授权。

### 4.3 CB-07

继续负责真实 Responses API 多轮 V1→V2→V3→V4、格式/排序或结构操作、Data Tool 集成及故障恢复的全链路验收。不得用 CB-04 Mock PASS 冒充 CB-07 Provider/Browser PASS。

## 5. Coding / Runtime / Release Gate

- 本 Amendment 获批前，Plan V2.0.1 保持唯一有效的冻结计划。
- CB-04 Coding Authorization 前，TDD 生命周期 Amendment、Plan Amendment、CB-02 Intent/Accept/Reject Amendment 必须各自版本化批准和生效；CB-02 Amendment 的组件实现/测试需先于依赖它的 CB-04 集成编码。
- 每个 CC 单独授权；CC 冻结不授权数据库、升级、Provider、服务操作或生产发布。CC-04 TransactionCase 数据库、模块升级、合成数据范围须在对应 Coding Authorization 明确写明。
- SRS Candidate B 真实文件外发与数据留存对齐是独立 Release/Provider Gate；不阻止独立获批的 Mock/合成测试。
- 不改变 Implementation Plan 对现有测试统计差异、历史失败和 APIConnectionError 的证据层级要求。

## 6. 建议更新的计划矩阵/流程图

在新完整 Plan 中，将阶段信息补充为：

| 阶段 | 变更后的完成事实 |
|---|---|
| CB-04 Candidate 编排 | Intent 绑定、授权/Effect 确定、Candidate 注册及验证、条件式接受或 Review handoff；无实际附件交付声明。 |
| CB-06 Review / Delivery | 接收非当前 Verified Candidate 决策或已 Accepted Current；负责 Preview、正式附件、Finalize 和下载。 |
| Candidate 结果 | `candidate_received` → `verified`（仍可非当前）→ `accepted_current`（有服务端授权且 CB-02 原子接受）→ `finalized/delivered`（CB-06 事实）。 |
| 工具边界 | Candidate B 单一外部 `office` Facade；M1 旧工具暂兼容；全局 Registry 收敛单列后续。 |

## 7. 不变项与明确排除

- 保留七轮 CC 总体划分及各自独立接受；CB-05 Data Tool 不阻断不使用刷新数据的编辑交付链。
- 不引入 DAG、事件总线、第二套状态机、Excel DSL 或新的通用授权框架。
- 不改 SRS/TDD 正文、CB-02 Schema、CB-03 验证契约、CB-01 Adapter、M1 Mapping 或 Provider 配置。
- 本稿仅建议版本化修订，不宣布任何组件已通过 Provider/Browser 或生产验收。

