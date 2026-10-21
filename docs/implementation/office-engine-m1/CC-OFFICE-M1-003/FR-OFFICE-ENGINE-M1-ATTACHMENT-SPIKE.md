<!-- 使用 Coding/FR 模板；仅依据冻结 CC-003 与 IHR/ATR/HVR/Spike 报告评估关闭。 -->

# FR — CC-OFFICE-M1-003 `ir.attachment` 事务与清理边界 Spike

## 0. 文档治理

本报告依据冻结 CC-OFFICE-M1-003 和对应 IHR、ATR、HVR、Spike 报告评估执行义务。负责人于 2026-10-21 明确批准关闭本 CC。关闭结论不表示两个 filestore 对象已物理删除，不批准应用层同步擦除，也不代表 Phase 4 所有产品策略门禁已关闭。

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-ATTACHMENT-TRANSACTION-SPIKE` |
| FR ID | `FR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE` |
| FR Version | `v1.0` |
| Closure Status | **SATISFIED** |
| CC | [CC-OFFICE-M1-003](../../../context/intent/CC-OFFICE-M1-003.md) `v1.0.0 Frozen` |
| IHR | [IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE](IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md) |
| ATR | [ATR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE](ATR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md) |
| HVR | [HVR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE](HVR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md)（按冻结 CC 为 N/A） |
| 模块 | Odoo 18 `ir.attachment` runtime；未新增产品模块 |
| Current Implementation Baseline | Odoo source/runtime baseline `ab89f54727807a25b16f3ad7e699fd05c782f3d9`；本 CC 未修改产品代码或数据库 schema |
| Prepared By / Assessment Date | Codex Agent / 2026-10-21 |

## 2. 最终基线

| 来源 | 最终版本 | 相关性 |
|---|---|---|
| CC | `v1.0.0 Frozen` | 本次关闭义务的唯一来源 |
| SRS | `V1.0.0 Frozen` | CC 引用的业务约束；本 Spike 不声称完成产品 AC |
| DDD | N/A | 验证既有 Odoo 附件行为，不定义业务领域模型 |
| TDD | `V0.3 Frozen` | 同步生命周期、权限与附件事务边界 |
| Implementation Plan | `V0.2 Frozen` | Phase 3 验证契约；计划中的 Phase 4 状态映射仍需计划维护 |

## 3. Executive Closure Summary

| 字段 | 结果 |
|---|---|
| Closure Status | **SATISFIED** |
| Current Code Baseline | `ab89f54727807a25b16f3ad7e699fd05c782f3d9`（本 CC 无产品代码修改） |
| CC-CHANGE | 6 required / 6 satisfied |
| CC-PRESERVE | N/A；冻结 CC 未定义 `CC-PRESERVE-*` 编号 |
| Applicable CC Guardrails | 5 required / 5 satisfied，按 CC §7 及其验证范围 |
| Automated Verification | SATISFIED — ATR 对 8 项 CC 测试均有当前运行证据；它们是 Odoo shell/ORM 探针和受控观察，不是产品自动化测试套件 |
| Human Verification | N/A — 冻结 CC 的 CC-TEST-001—008 均不要求 UI 人工验证 |
| Unauthorized Deviation | None |
| Open Blocking Issues for CC Closure | 0 |
| Evidence Baseline Consistency | Valid — IHR/ATR 对应执行时 Odoo source/runtime baseline；未发生产品代码变更 |

## 4. Coding Contract Closure Matrix

| Contract Obligation | Source | Evidence | Status | Notes |
|---|---|---|---|---|
| 使用唯一标记建立测试前后盘点 | CC-CHANGE-001；CC-TEST-001 | IHR-001/IHR-004；ATR-RUN-002/006 | SATISFIED | 开始前无冲突；结束后测试附件记录和 fname 数据库引用均为 0 |
| ORM 提交合成附件并验证字节读取 | CC-CHANGE-002；CC-TEST-002 | IHR-002；ATR-RUN-003 | SATISFIED | User A 创建并提交；新 cursor 读取字节 SHA-1 一致 |
| 独立事务回滚并追踪精确存储对象 | CC-CHANGE-003；CC-TEST-003 | IHR-002/003；ATR-RUN-003/004/006 | SATISFIED | 回滚记录在新 shell 不存在；关联对象仍存在并有 GC 标记，事实已明确区分 |
| ORM 删除和精确重复清理 | CC-CHANGE-004；CC-TEST-004 | IHR-003；ATR-RUN-005/006 | SATISFIED | 已提交控制附件经 ORM 删除；重复清理安全 no-op |
| 用户权限、失败输出可访问性与快照边界证据 | CC-CHANGE-005；CC-TEST-005—007 | IHR-002/003；ATR-RUN-003/004；Spike 报告 §5 | SATISFIED | A/B 均 `su=False`；B 被 ACL 拒绝。回滚结果无 ORM 附件记录；未夸大为完整产品下载测试或大文件事务证明 |
| 孤儿对象识别和补偿路径结论 | CC-CHANGE-006；CC-TEST-008 | IHR-004；ATR-RUN-006；Spike 报告 §§4、6 | SATISFIED | 对象与 GC checklist 精确可识别；Odoo 原生延迟 GC 路径由源码确认；全局 GC 未执行且如实标记 NOT RUN |
| 适用的 TDD 防护栏 | CC §7 | IHR/ATR 的用户隔离、事务观察、失败记录和补偿路径证据 | SATISFIED | 仅评估 CC 明确纳入且本 Spike 可验证的边界；不声明长耗时渲染和生产容量已验证 |
| CC 测试合同 | CC-TEST-001—008 | ATR §4—§6；ATR-RUN-002—006 | SATISFIED | 8 项均有实际证据；ATR-RUN-001 是测试开始前的启动阻断，未进入数据库操作，不属于 CC 测试失败 |
| 完成定义 1—7 | CC §10 | IHR/ATR/HVR、Spike 报告、本 FR | SATISFIED | 负责人已批准关闭；Phase 4 的政策与计划映射问题另列为下游门禁，不倒改本 CC 证据 |

## 5. Implementation Closure Assessment

| CC-CHANGE | IHR Evidence | 实际变更清单 | Status |
|---|---|---|---|
| CC-CHANGE-001—006 | IHR-001—004 | 无产品代码、Addon、数据库 schema 或 Odoo 配置修改；新增的 IHR/ATR/HVR、脱敏 Spike 报告和受控验证脚本位于本 CC 的实施证据目录 | SATISFIED |

本 CC 是验证性 Spike，其交付为实测事实和清理路径报告，不要求修改产品代码。证据目录中的合成运行结果不包含业务附件内容；数据库中的合成附件记录已通过 ORM 清理。

## 6. Preservation & Guardrail Assessment

### 6.1 Preservation

冻结 CC 未定义 `CC-PRESERVE-*` 项，故该维度为 N/A，而非测试通过。实际操作遵守 CC 的数据库、用户权限和文件系统边界；相关事实见 IHR §2—§4 与 ATR §6。

### 6.2 Applicable CC Guardrails

| CC §7 项 | TDD 来源 | Evidence | Status |
|---|---|---|---|
| 短事务/附件文件 I/O 边界只作实际观察 | TDD §6.1、`T-TRX-002` | IHR-002/003；ATR CC-TEST-007 | SATISFIED（限小型合成附件观察） |
| 交付前附件所有权/当前用户权限边界 | TDD §6.1、§7.1 | IHR-002；ATR CC-TEST-005 | SATISFIED（权限边界已测；完整产品交付重验未实现） |
| 失败路径不形成可访问附件记录 | TDD §6.1、§7.3 | IHR-003；ATR CC-TEST-006 | SATISFIED（限回滚后 ORM 记录不可见） |
| 不使用 sudo 扩权并记录脱敏证据 | TDD §7.1/§7.3 | IHR §2；ATR §6 | SATISFIED |
| 不在长 Office 处理中持有业务锁；附件 I/O 边界实测 | `T-TRX-002` | Spike 报告 §5；ATR CC-TEST-007 | SATISFIED（已观察附件 I/O；未模拟长时间渲染，不作长任务性能结论） |

## 7. Automated Verification Assessment

ATR 记录 8 项冻结 CC 测试均已执行并按各自观察目标标记 PASS；主要运行证据为 `ATR-RUN-002` 至 `ATR-RUN-006`。`ATR-RUN-001` 是默认 sandbox 启动 Odoo shell 时发生的前置权限阻断，未执行 ORM 操作；同一授权命令在允许的开发环境成功运行。Odoo 全局 GC 被 CC 明确禁止，本次未运行，因此不属于缺失的 CC 测试；物理 GC 清理不被宣称为已验证。

证据只支持 Odoo 18 开发库、短小合成附件、现有两个非系统用户和 file/filestore 模式下的行为结论，不外推为生产并发、容量、大文件、长事务或即时物理擦除保证。

## 8. Human Verification Assessment

```text
Human Verification: N/A
Source: Frozen CC-OFFICE-M1-003 §8（CC-TEST-001—008 均标记“否”）
Reason: 本 Spike 仅通过受控 Odoo shell / ORM 观察，无产品 UI 或人工操作场景。
```

HVR 的 N/A 不等于人工 PASS。负责人的 CC 关闭批准是治理决定，不改写 HVR 状态。

## 9. Deviation & Stop Condition Assessment

| 项 | 评估 |
|---|---|
| 未批准偏离 | None；未建隔离库、未安装依赖/模块、未修改配置/schema、未触碰业务附件 |
| 初次 shell 启动阻断 | ATR-RUN-001 在进入数据库前因 sandbox 下 psutil 进程枚举受限；批准环境重跑成功，失败尝试无 ORM 副作用 |
| 测试对象残留 | 两个唯一合成 filestore 对象和 GC checklist 标记仍存在；无附件记录或数据库 fname 引用；未直接删文件、未运行全局 GC |
| 负责人处置 | 2026-10-21 批准关闭 CC；残留按报告所述留给 Odoo 原生延迟 GC；不代表即时擦除能力通过 |

## 10. Open Issues / Findings / Evidence Gaps

| ID | 来源 | 描述 | Closure Impact（本 CC） | Human Judgment Required | 下游处理 |
|---|---|---|---|---|---|
| ATR-I-001/002 | ATR、Spike 报告 | rollback/unlink 不同步删除 filestore；延迟物理清理依赖 Odoo 原生 GC | Non-Blocking；CC 的观察、报告和补偿路径义务已完成 | Yes — 已由负责人批准本 CC 关闭 | CC-004 冻结前必须明确产品接受延迟 GC；若要求同步擦除，先改 TDD/计划并单独验证 |
| PLAN-IMPACT-003 | Implementation Plan V0.2 §4/§12 | 冻结计划仍记录 Phase 3 未执行、Phase 4 依赖 Spike PASS | Non-Blocking；不否定已完成的 Spike 证据，但计划需维护 | Yes | 在 CC-004 冻结/实施前，评审并基线化计划状态更新，记录 Phase 3 已完成和 Phase 4 精确 GC 处置 |

无缺失证据阻塞本 CC 关闭。以上两项保留为下游设计/计划门禁，不得用本 FR 宣称它们已解决。

## 11. Evidence Baseline Consistency

| Evidence Source | Baseline | Valid for this CC? | Basis |
|---|---|---|---|
| IHR | Odoo source/runtime commit `ab89f54727807a25b16f3ad7e699fd05c782f3d9` | Yes | Spike 未修改产品代码 |
| ATR | 同一 Odoo source/runtime baseline；运行环境快照见 `evidence/environment-snapshot.json` | Yes | ATR-RUN-002—006 属于同一开发实例；CC 期间没有代码变化 |
| HVR | N/A | N/A | Frozen CC 不要求人工验证 |

## 12. Done Criteria Assessment

| CC §10 Done Criterion | Evidence | Status | Gap |
|---|---|---|---|
| #1：CC-TEST-001—008 均有运行状态、命令、版本与当前环境证据 | ATR §§3—5；环境快照；ATR-RUN-002—006 | SATISFIED | — |
| #2：报告覆盖提交、回滚、ORM 删除、幂等、权限、存储副作用与清理 | Spike 报告 §§2—6；IHR-002—004 | SATISFIED | — |
| #3：只操作合成附件，无未授权库/配置变更；残留对象识别且补偿路径经负责人处置 | ATR-RUN-006；Spike 报告 §6；负责人 2026-10-21 关闭批准 | SATISFIED | 物理对象依赖原生延迟 GC；未声称已删除 |
| #4：明确短事务和文件 I/O 可行性及证据限制 | Spike 报告 §5；ATR CC-TEST-007 | SATISFIED | 大文件/生产锁预算未测，已明确为限制 |
| #5：提出 Odoo 支持的补偿路径或受控任务方案 | Spike 报告 §§4、6；ATR CC-TEST-008 | SATISFIED | 源码确认原生 GC 路径和精确标记；GC 实际运行不属于本 CC，未执行 |
| #6：Spike 报告、脱敏日志、环境快照、清理核对并由负责人评审 | IHR/ATR/HVR/报告/证据目录；负责人关闭批准 | SATISFIED | — |
| #7：全部关键门禁及证据完整后建议 Phase 4 CC 起草/实施；Spike PASS 不等于 Phase 4 授权 | 本 FR；负责人仅请求 CC 关闭并起草 CC-004 | SATISFIED | CC-004 仍为 Draft；冻结和实施须通过更新后的计划及 GC 策略门禁 |

## 13. Final Closure Determination

```text
Final Closure Status: SATISFIED
Basis:
- CC-CHANGE-001—006 均按验证性 Spike 的范围完成并有 IHR 证据。
- CC-TEST-001—008 均有当前 Odoo runtime / shell 证据，边界与限制已明确。
- CC §7 所列且适用于本 Spike 的附件权限、事务观察、失败记录和补偿路径要求均有证据。
- HVR 按冻结 CC 为 N/A；未冒充人工 UI 验收。
- 无未经批准偏离，CC §10 Done Criteria 均满足。
- 负责人于 2026-10-21 明确批准关闭 CC。
- CC 关闭不表示 filestore 物理清理已完成，也不授权同步擦除或产品发布。

This determination closes only CC-OFFICE-M1-003.
It does NOT constitute Phase 4 implementation authorization or Merge / Release approval.
```

## 14. Handoff

| 项 | 状态 |
|---|---|
| Closure Assessment Complete | Yes |
| CC Closure | 负责人已批准；本 FR 记录为 SATISFIED |
| Human Review Required | 已完成负责人关闭审批 |
| Phase 4 CC-004 | 仅可保留 Draft；冻结/实施前须更新并基线化实施计划，明确延迟 GC 策略和请求模型/附件失败边界 |
| 同步物理擦除 | 未验证、未批准；如成为要求，须回到 TDD/计划及独立技术验证 |

## 附录 A — Evidence Reference Index

| Evidence Type | Reference | 状态 | 用途 |
|---|---|---|---|
| CC | `docs/context/intent/CC-OFFICE-M1-003.md` | Frozen | 关闭义务权威 |
| IHR | `IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md` | 已更新关闭处置 | 执行历史 |
| ATR | `ATR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md` | 当前运行证据 | Odoo shell/ORM 观察 |
| HVR | `HVR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md` | N/A | 冻结 CC 无人工 UI 场景 |
| Spike report | `OFFICE-ENGINE-M1-ATTACHMENT-SPIKE-REPORT.md` | 执行完成 | 事务副作用、限制和 GC 路径 |
| Runtime logs/scripts | 当前目录 `evidence/` | 留存 | 复核运行步骤与脱敏结果 |

## 附录 B — FR Version History

| Version | Date | Closure Status | Reason |
|---|---|---|---|
| v1.0 | 2026-10-21 | SATISFIED | 依据完整 IHR/ATR/HVR 与 Spike 报告，并记录负责人批准关闭；保留延迟 GC 和下游计划门禁 |
