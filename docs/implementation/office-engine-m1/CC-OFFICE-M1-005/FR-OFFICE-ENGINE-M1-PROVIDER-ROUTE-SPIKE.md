# FR — CC-OFFICE-M1-005 Provider 前路由与 payload 隔离 Spike

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-PROVIDER-PRE-ROUTE-SPIKE` |
| FR ID | `FR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE` |
| FR Version | `v1.0` |
| CC Version | `v1.0.0 Frozen` |
| IHR / ATR / HVR | [IHR](IHR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) / [ATR](ATR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) / [HVR](HVR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) |
| Module | `mymodules/odoo-llm` 运行时扩展验证；无产品代码变更 |
| Current Baseline | 根仓库 `e91bf5a502b8970bfa9c795335e5ee2dce0e57b7`；Odoo-LLM `609ec6dda3645165f6a4a843d7af5d286081a29d` |
| Prepared By / Date | Codex Agent / 2026-10-21 |

## 2. Final Coding Contract Baseline

| 来源 | 版本 | 相关性 |
|---|---|---|
| CC | CC-OFFICE-M1-005 v1.0.0 Frozen | Closure 权威；只含验证性 Spike |
| SRS | V1.0.0 Frozen | 不改变业务含义 |
| DDD | N/A | 按已批准 M1 决策 |
| TDD | V0.4 Frozen | 不实现聊天、Provider 文件访问或 Office 生成 |

## 3. Executive Closure Summary

| 字段 | 值 |
|---|---|
| Closure Status | **NOT SATISFIED — CC 行政关闭；验证结果未满足** |
| CC-CHANGE | 验证义务已执行；安全判定未全部满足 |
| Automated Verification | NOT SATISFIED（CC-TEST-006 FAIL；CC-TEST-005 BLOCKED；CC-TEST-008 INCONCLUSIVE） |
| Human Verification | N/A（来源 CC） |
| Unauthorized Deviation | None |
| Open Blocking Issues | 2 |
| Evidence Baseline Consistency | Valid for pinned Odoo-LLM source; root workspace had unrelated dirty files |

## 4. Coding Contract Closure Matrix

| Contract Obligation | Evidence | Status | Notes |
|---|---|---|---|
| CC-TEST-001/002/003：真实运行时基线与已识别 Office MIME 前置拒绝 | ATR-RUN-001、脱敏 JSON | SATISFIED（有限范围） | `.xlsx/.xls/.docx/.doc` MIME 被拒绝且 provider mock 零调用；不外推到 MIME 不一致文件 |
| CC-TEST-004：当前 Provider 与工具路径覆盖 | ATR-RUN-001 | SATISFIED（当前配置） | 只有 OpenAI service；tools-enabled cycle 使用工具执行 stub；不证明其他 Provider 或外部 API |
| CC-TEST-005：用户隔离/授权 handoff | ATR-RUN-001 | NOT SATISFIED | 低权限用户跨线程/附件拒绝通过；内部路由授权引用 handoff 缺实现而 BLOCKED |
| CC-TEST-006：异常与不确定身份 fail closed | ATR-RUN-001 | NOT SATISFIED（历史运行结果） | 文件名 `.xlsx` 配文本内容/MIME 被识别为 `text/plain` 并进入 mock Provider payload。独立 `CC-OFFICE-M1-PRE-ROUTE-FIX` 后续修复了其限定场景，但未重跑本 CC 全部契约；不得改写本项历史 FAIL |
| CC-TEST-007：普通附件回归 | ATR-RUN-001 | SATISFIED | `text/plain` 按既有路径进入本地 mock |
| CC-TEST-008：独立 Addon 扩展点/服务路由 | ATR-RUN-001 | BLOCKED / INCONCLUSIVE | 本 Spike 未安装/实现独立聊天 Addon 或受控服务；没有运行时 handoff 证据 |
| CC-TEST-009/010：脱敏、基线复现、hook 清理 | IHR-003、cleanup-proof | SATISFIED | 无真实外发；探针物理删除，源码仓库 clean |
| CC-004 成功生成/附件交付 | CC-004 FR | NOT SATISFIED | spawn 导入缺陷未改、未掩盖；本 FR 不重新评估 CC-004 |

## 5. Implementation Closure Assessment

本 CC 不交付产品实现。仅冻结文档勘误和 Spike 证据文档有变更；Odoo-LLM 产品代码、数据库 schema、模块安装状态和全局配置未变。临时 runtime patch 在隔离 shell 中恢复并随进程退出，不进入持久服务器进程或仓库。

## 6. Preservation & Guardrail Assessment

- 已识别标准 Office MIME 的拒绝顺序、非 Office 文本回归和跨用户 record rule 拒绝有有限运行证据。
- MIME/扩展名不一致未按 fail-closed 规则拒绝，构成未满足安全约束。
- 没有实际独立路由实现，不能宣称当前用户环境已传递到 `office_engine_odoo` 服务。

## 7. Automated Verification Assessment

ATR-RUN-001 对全部十项 CC 测试给出显式状态。存在 `CC-TEST-006 = FAIL`、`CC-TEST-005 = BLOCKED`、`CC-TEST-008 = INCONCLUSIVE`。唯一实际 Provider 服务为 OpenAI，全部 Provider/工具调用均为本地 stub，未向外网发送请求。故自动化验证未满足。

## 8. Human Verification Assessment

Human Verification Required = No，来源 CC-005。HVR 为 N/A；没有人工/浏览器 PASS 声明。

## 9. Deviation & Stop Condition Assessment

- 用户批准了 CC-004 技术债的有限风险接受及一次性 Phase 5 Spike 例外；本次严格限于 CC 范围。
- CC-TEST-006 触发停止条件；后续独立修复仅处理伪装附件拦截，不解除 CC-005 handoff Gate，也不授权 Office 聊天生成。
- 没有未经授权的源码或数据库偏离。

## 10. Open Issues / Evidence Gaps

| Issue | Status | 影响 |
|---|---|---|
| 文件名与实测 MIME 不一致 | 历史 FAIL；限定场景已由独立 CC 缓解 | CC-005 原始运行中 `.xlsx` 文件名 + 纯文本被识别为 `text/plain` 并到达本地 mock。独立 pre-route-fix CC 对该限定场景通过验证；CC-005 的原始 FAIL 保留且没有全量重跑 |
| `office_engine_odoo` 路由 handoff | Blocking / Missing evidence | 独立 Addon 授权服务路由未验证 |
| CC-004 spawn/import | Open / Blocking | 成功渲染及附件交付仍未通过 |
| 非 OpenAI Provider | N/A in environment | 目标实例未安装/启用其他 Provider，结论不能外推 |

## 11. Evidence Baseline Consistency

Odoo-LLM 仓库 HEAD 与冻结值一致且工作树干净；运行实例在干净基线确认后重启。根仓库存在与本 CC 无关的既有修改，但 `odoo/`、官方 `addons/` 目录无工作树修改；本 CC 未修改产品代码。

## 12. Done Criteria Assessment

| CC §7 标准 | 结果 |
|---|---|
| 基线/数据库/模块状态与当前 Provider 覆盖记录完整 | SATISFIED |
| 已识别 Office MIME 在 Provider 前被阻断 | SATISFIED（四种合成标准 MIME） |
| 任意不确定/不一致 Office 附件 fail closed | NOT SATISFIED（CC-TEST-006 FAIL） |
| 当前用户授权 handoff 或拒绝 | PARTIAL；拒绝可验证，handoff 缺失 |
| 全路径/独立 Addon 扩展可行性 | NOT SATISFIED / INCONCLUSIVE |
| IHR/ATR/HVR/FR 与 hook 清理证据完整 | SATISFIED（HVR N/A） |
| 可得出整体 PASS 并进入 Phase 6 | NOT SATISFIED |

## 13. Final Closure Determination

```text
Final FR Closure Status: NOT SATISFIED
Administrative CC closure: approved by project owner on 2026-10-22
Spike outcome: FAIL (with additional BLOCKED / INCONCLUSIVE items)
Original ATR: 7 PASS, 1 FAIL, 2 BLOCKED; unchanged
CC-TEST-006: historical FAIL; its spoofed-file scenario was subsequently mitigated by the separate PRE-ROUTE-FIX CC, without a full CC-005 rerun
CC-TEST-005/008: handoff remains BLOCKED / INCONCLUSIVE
Real external provider calls: 0
Product code changes within CC-005: 0
CC-004 FR: remains NOT SATISFIED
Waiver: none; no FROZEN WITH OPEN ITEMS disposition
```

负责人于 2026-10-22 明确要求行政关闭 CC-005。本次关闭只结束该 Spike 的执行记录；不接受、豁免或重写未通过项，不把 FR 判为 `SATISFIED`。CC-005 的冻结契约、ATR 与原始运行证据仍保持原样。独立 pre-route-fix 关闭了伪装附件问题的限定修复范围，但 handoff 和 CC-004 缺口依旧存在；Implementation Plan Phase 5 完整 Gate 未通过，用户可用 Office 聊天生成与 Phase 6 实施仍未获授权。

## 附录 — Evidence Reference Index

- [ATR](ATR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- [IHR](IHR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- [HVR](HVR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- `evidence/ATR-RUN-001-provider-route.json`
- `evidence/environment-snapshot.json`
- `evidence/cleanup-proof.txt`
