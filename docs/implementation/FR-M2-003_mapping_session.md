<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/FR模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# FR-M2-003：Odoo 编排层基础与 Mapping Session

## 0. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-003` |
| FR ID | `FR-M2-003_mapping_session.md` |
| FR Version | `V1.0` |
| CC Version | `CC-M2-003 FROZEN V1.0.0` |
| IHR Reference | [`IHR-M2-003_mapping_session.md`](IHR-M2-003_mapping_session.md) |
| ATR Reference | [`ATR-M2-003.md`](ATR-M2-003.md) |
| HVR Reference | N/A — 本 CC 不交付用户可见 UI；适用性由 CC §13 确定 |
| Module | `office_engine_m2` |
| Implementation baseline | `1e33a25` — `feat: add M2 mapping session orchestration` |
| Prepared By | Codex，基于 IHR/ATR 证据评估 |
| Assessment Date | 2026-10-23 |

## 1. 最终 CC 基线

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC | `CC-M2-003 FROZEN V1.0.0` | 本 FR 唯一义务来源 |
| SRS | `SRS_office_engine_m2_ai_mapping.md V1.0.0 Frozen` | 业务权限、隔离与数据最小化 |
| DDD | N/A | 依据冻结 M2 TDD |
| TDD | `TDD_office_engine_m2.md V1.0.0 Frozen` | Session、状态、权限与 revision 约束 |
| Implementation Plan | `IMPLEMENTATION_PLAN_office_engine_m2.md V1.0.0 Frozen` | M2 阶段 3 计划门禁；阶段级 XML-RPC 证据另行注明 |

## 2. 执行摘要

| 字段 | 结果 |
|---|---|
| Closure Status | `SATISFIED` — Frozen CC-M2-003 的义务均有实现/自动化证据并满足 |
| Current Code Baseline | `1e33a25` |
| CC-CHANGE | `6/6 SATISFIED` |
| CC-PRESERVE | `5/5 SATISFIED`，据 ATR 范围检查及既有 Usage 回归 |
| Applicable TDD Guardrails | `SATISFIED`，证据见 IHR/ATR |
| Automated Verification | `SATISFIED` — CC-TEST-001–008 PASS |
| Human Verification | `N/A` — 无用户可见 UI |
| Unauthorized Deviation | `None identified` |
| Open Blocking Issues | `0` for this CC |
| Evidence Baseline Consistency | `Valid` for implementation commit `1e33a25` |

## 3. CC Closure Matrix

| Contract Obligation | Source | Evidence | Status | Notes |
|---|---|---|---|---|
| 增加最小 Mapping Session 模型 | CC-CHANGE-001 | IHR 实施记录；ATR CC-TEST-001/005/007 | SATISFIED | owner/company、绑定关系、状态和 revision 均受服务端管理 |
| 校验 thread/message/attachment/target 关系与当前用户权限 | CC-CHANGE-002 | ATR CC-TEST-002/003 | SATISFIED | 跨用户、非关联附件及无权目标被拒绝，无残留 Session |
| 提供当前用户可见的最小 Session 上下文 | CC-CHANGE-003 | ATR CC-TEST-001/006 | SATISFIED | 跨用户/跨公司读取受 ACL 和 Record Rule 限制 |
| 服务端状态转换与乐观 revision | CC-CHANGE-004 | ATR CC-TEST-004/005 | SATISFIED | 非法跳转、旧 revision、直接写受保护字段拒绝 |
| ACL 与 owner/company Record Rule | CC-CHANGE-005 | ATR CC-TEST-006/007 | SATISFIED | 无 unlink；Usage ACL 保持原样 |
| Session 数据最小化 | CC-CHANGE-006 | ATR CC-TEST-006/008 | SATISFIED | 禁止字段和额外输入拒绝；无 Prompt/模板全文/样例持久化 |
| Usage、当前用户环境、数据最小化、阶段边界保持不变 | CC-PRESERVE-001–005 | ATR CC-TEST-006–008；IHR 变更范围 | SATISFIED | 未修改 Provider、Usage 实现、M1 或 UI |
| TDD 权限、数据与 revision 防护栏 | CC §7 / TDD IDs | ATR CC-TEST-002–006/008 | SATISFIED | 未发现 `sudo()`、su 环境或用户切换路径 |
| 自动化与模块升级义务 | CC-TEST-001–008 / CC §13 | ATR 最终 Odoo 日志及静态检查 | SATISFIED | 最终结果 0 failed / 0 error(s) of 21 tests |
| HVR 义务 | CC §13 | CC §13、ATR 人工验证节 | N/A | 后端-only CC，无 UI 验收场景 |

## 4. 实施与验证评估

实现范围限于 `mymodules/office_engine_m2/`，对应模型、内部服务、ACL/Record Rule 和 `TransactionCase`。实际文件与提交记录见 IHR；运行命令、环境、逐项测试结果、数据库复核及清理记录见 ATR。最终日志在既有 `odoo18ce` 上完成 `-u office_engine_m2` 和模块测试，报告 21 项 Odoo tests 全部通过；Addon stats 为 29 tests、1.22 秒、1919 queries。测试没有调用真实 LLM/外网，也没有创建隔离数据库。

HVR 为 N/A，而非 PASS。ATR 记录的三个既有不可安装 Addon 环境摘要不属于本 CC；它们不改变本次 `office_engine_m2` 的测试结果，亦不被本 FR 解释为整个 Odoo 实例启动无错误。

## 5. 偏移与停止条件

IHR/ATR 未记录未授权偏移或本 CC 触发后仍未解决的停止条件。状态机、关系验证和 `error_code` 均按冻结 CC/TDD 基线实施。

## 6. 计划阶段门禁注记

Implementation Plan 阶段 3 的验收 Gate 明确列出在既有环境通过 XML-RPC 安装/升级。当前 ATR 提供的是 `odoo-bin -u office_engine_m2` 的升级和 TransactionCase 证据，没有 XML-RPC 安装/升级记录。此项不属于 Frozen CC-M2-003 的独立 CC 完成义务，因此不改变本 FR 对 CC 的 `SATISFIED` 判定；但 M2 阶段 3 的计划 Gate 不得标记为全部通过，进入阶段 4 实施前应按 Implementation Plan 补齐或通过正式计划变更处置该证据缺口。

## 7. 最终关闭判定

**Final Closure Status: SATISFIED**

依据：CC-CHANGE-001–006、CC-PRESERVE-001–005、适用 TDD 防护栏及 CC-TEST-001–008 均有当前提交基线上的实现或自动化证据并满足；HVR 按 CC 明确为 N/A；未发现未授权偏移。负责人于 2026-10-23 明确批准关闭 CC-M2-003。

本判定关闭 CC-M2-003，不代表 M2 阶段 3 计划 Gate 已全部通过，也不代表 M2 项目结项、合并或发布获批。

## 8. 人工评审移交

| 字段 | 值 |
|---|---|
| Closure Assessment Complete | Yes |
| Human Review Required | 已由负责人完成关闭批准 |
| Merge / Release Decision | 不在本 FR 范围 |
| 阶段 Gate 提醒 | 阶段 3 XML-RPC 安装/升级证据未记录；进入阶段 4 实施前需处置 |

## 附录 A — 证据索引

| 证据 | 引用 | 用途 |
|---|---|---|
| Frozen CC | [`CC-M2-003_mapping_session.md`](CC-M2-003_mapping_session.md) | 关闭义务权威 |
| IHR | [`IHR-M2-003_mapping_session.md`](IHR-M2-003_mapping_session.md) | 实际变更与提交基线 |
| ATR | [`ATR-M2-003.md`](ATR-M2-003.md) | 测试/环境/清理证据；原始 Odoo 日志 `/private/tmp/cc_m2_003_odoo_test_pass.log` |

## 附录 B — 版本历史

| 版本 | 日期 | Closure Status | 说明 |
|---|---|---|---|
| V1.0 | 2026-10-23 | SATISFIED | 依据 CC-M2-003 IHR/ATR 及负责人关闭批准生成；阶段 3 XML-RPC Gate 证据缺口单独保留 |
