# Office Engine M2 Implementation Plan V2.0.2 — CB-07 Consolidation Amendment

| 项目 | 内容 |
|---|---|
| 基线 | `IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md`（Frozen） |
| 修订 | V2.0.2 Amendment — CC-M2-CB-07 Consolidation |
| 适用 CC | `CC-M2-CB-07 — Route B End-to-End Integration & Cross-layer Regression` |
| 状态 | **APPROVED IMPLEMENTATION AMENDMENT** |
| 决策依据 | 负责人明确要求将本次 Route B 集成并入原 CB-07，并批准冻结 CC-M2-CB-07、进入实施。 |

本 amendment 以版本化增补方式修订 V2.0.1 §10，不覆盖冻结原文。其他 CC 的范围、依赖、验收和状态不变。

## 1. CB-07 合并后的目标与范围

原 `CB-07 Cross-layer Regression & Release Readiness` 与 Route B E2E 集成为唯一 `CC-M2-CB-07`，不另立 `CC-07` 或第二份 CB-07 契约。

合并后的范围：

1. 保留 CB-01 至 CB-06 已验收能力，进行跨层兼容回归，不重复开发既有 Adapter、Version Service、Validator、Orchestrator、Retriever、Finalize 或附件服务。
2. 验证 Route B 首次文件 Candidate、用户 Accept 后登记 V1，以及以 Accepted Current 实际字节为输入的多轮编辑、Accept/Reject、Finalize 和交付。
3. 验证真实 Responses API 的 V1→V2→V3→V4 连续编辑，包含值修改、格式修改及一项 TDD 支持矩阵允许的排序/结构操作；每轮以上一已接受文件为输入。
4. 在同一真实 Odoo Thread 中执行至少两轮用户数据补充流程，验证两个独立工具：`odoo_record_retriever` 只读取数，`office` 编辑与版本交付；M1 Retriever 和既有首轮 Mapping 流程作为兼容回归，不作为 Route B 内容生成前置。
5. 回归 CB-06 单轮交付、M1 Skills/Mappings/RenderBridge/Document Request/附件权限/Chat Completions，以及超时、损坏候选、验证失败、权限撤销、附件发布失败时的 last-valid 保护。
6. 分层报告 Unit/Mock、Odoo TransactionCase/HttpCase、真实 Provider、Browser/UI 和下载独立回读证据；历史失败保留原记录并按对当前验收影响评估。

## 2. 顺序与授权门禁

依赖仍为 CB-01 至 CB-06 各自完成并满足其授权门禁后进入本合并批次。真实 Provider dispatch 默认关闭；只有收到真实集成测试的单独授权后，受信任操作人员才可通过受控服务端配置在获批测试环境临时启用。真实业务数据外发、生产启用和 Release 另行授权。

## 3. 编号与证据

- 唯一合同编号：`CC-M2-CB-07`。
- 唯一实施记录：`IHR-M2-CB-07.md`、`ATR-M2-CB-07.md`、`HVR-M2-CB-07.md`、`FR-M2-CB-07.md` 及 `evidence/CB-M2-CB-07/`。
- 本 amendment 不产生第二个 CC，不改变 CB-01 至 CB-06 的完成状态，也不批准生产发布。

