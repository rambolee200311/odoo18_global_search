<!-- 使用 Coding/FR 模板；评估依据为 CC-OFFICE-M1-001 v1.0.0 Frozen。 -->

# FR — CC-OFFICE-M1-001 Office Core 纯 Python 同步底座

## 0. 文档治理

本报告按冻结 CC 的义务和 IHR/ATR/HVR 证据评估 CC-001。项目负责人已于 2026-10-20 批准关闭 CC。该关闭评估不代表 `office_verify`、Odoo 附件交付、聊天 Office 流程或产品发布完成。

## 1. Closure Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-CORE-FOUNDATION` |
| FR ID | `FR-OFFICE-ENGINE-M1-CORE-FOUNDATION` |
| FR Version | `v1.1` |
| Closure Status | **SATISFIED** |
| CC | [CC-OFFICE-M1-001](../../../context/intent/CC-OFFICE-M1-001.md) `v1.0.0 Frozen` |
| IHR | [IHR-OFFICE-ENGINE-M1-CORE-FOUNDATION](IHR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) |
| ATR | [ATR-OFFICE-ENGINE-M1-CORE-FOUNDATION](ATR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) |
| HVR | [HVR-OFFICE-ENGINE-M1-CORE-FOUNDATION](HVR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md)（按 CC 为 N/A） |
| 模块 | `mymodules/office_core` |
| Current Implementation Baseline | `WT-office_core:5430736474b92ddb2d0dc928e478621db877b4a8aedeeb546887d55e398eaf78` |
| Prepared By / Assessment Date | Codex Agent / 2026-10-20 |

## 2. 最终基线

| 来源 | 最终版本 | 相关性 |
|---|---|---|
| CC | `v1.0.0 Frozen` | 本次所有关闭义务的唯一来源 |
| SRS | V1.0.0 Frozen | CC 的业务追溯基线 |
| DDD | N/A | M1 无状态核心无需独立领域模型 |
| TDD | V0.3 Frozen | 纯 Python 同步核心、格式和安全边界 |
| Implementation Plan | V0.2 Frozen | Phase 1 实施计划 |

## 3. Executive Closure Summary

| 字段 | 结果 |
|---|---|
| Closure Status | **SATISFIED** |
| Current Code Baseline | 工作树包内容指纹 `5430736474b92ddb2d0dc928e478621db877b4a8aedeeb546887d55e398eaf78` |
| CC-CHANGE | 7 required / 7 satisfied |
| CC-PRESERVE | 6 required / 6 satisfied |
| Applicable CC Guardrails | 6 required / 6 satisfied |
| Automated Verification | SATISFIED — `ATR-RUN-011` 17/17 通过 |
| Human Verification | N/A — 冻结 CC 声明不需要人工 UI 验收 |
| Unauthorized Deviation | None |
| Open Blocking Issues | 0 |
| Evidence Baseline Consistency | Valid — ATR 哈希与当前 `office_core` 源文件指纹一致 |

## 4. Coding Contract Closure Matrix

| Contract Obligation | Source | Evidence | Status | Notes |
|---|---|---|---|---|
| 纯 Python 无状态服务及稳定接口 | CC-CHANGE-001 | IHR-002；ATR-TEST-009 | SATISFIED | 不导入 Odoo/Provider/HTTP/Queue |
| 容器、格式、异常输入 fail-closed | CC-CHANGE-002 | IHR-002/003；ATR-TEST-002 | SATISFIED | 合成输入覆盖；真实加密文件的范围限制见 §10 |
| 受限结构读取与能力白名单 | CC-CHANGE-003 | IHR-002/004；ATR-TEST-003/006 | SATISFIED | `.xls/.doc` 及未验证部件关闭 |
| Mapping Plan V1 校验 | CC-CHANGE-004 | IHR-002/003；ATR-TEST-004 | SATISFIED | 包括 null、空串、零值和不可写目标边界 |
| 输入不变的隔离候选渲染 | CC-CHANGE-005 | IHR-002；ATR-TEST-005 | SATISFIED | 候选不是已回读/可交付文件 |
| 告警、资源界限、稳定错误和清理 | CC-CHANGE-006 | IHR-003/004；ATR-TEST-002/007/008/009 | SATISFIED | 当前 macOS 小内存预算不满足时稳定拒绝 |
| 锁定依赖、目标 venv 与许可证证据 | CC-CHANGE-007 | IHR-001；ATR-TEST-001 | SATISFIED | Python 3.11.9；`pip check` 与合成读写 smoke 通过 |
| 保留 CC-PRESERVE-001—006 | CC §6 | ATR §6，`ATR-RUN-011` | SATISFIED | 无路径/动态代码；输入不变；公式目标只读；未准入能力拒绝；无业务集成；失败不交付 |
| CC 测试合同 | CC-TEST-001—009 | ATR §3—§5；`ATR-RUN-011` | SATISFIED | 当前代码基线 17 项 PASS；历史失败保留并有修复记录 |
| HVR 要求 | CC §11、附录 B | HVR §2—§4 | N/A | CC 明确所有测试均不要求人工验证；浏览器观察没有被记作 PASS |

## 5. Implementation Closure Assessment

| CC-CHANGE | IHR Evidence | Actual Change Inventory | Status |
|---|---|---|---|
| CC-CHANGE-001 | IHR-002 | `mymodules/office_core/__init__.py`、`models.py`、`service.py`、`errors.py` | SATISFIED |
| CC-CHANGE-002 | IHR-002/003 | `security.py` 与异常输入测试 | SATISFIED |
| CC-CHANGE-003 | IHR-002/004 | `engine.py` 结构读取、格式拒绝及真实样本拒绝 | SATISFIED |
| CC-CHANGE-004 | IHR-002/003 | `engine.py` Mapping 校验与边界测试 | SATISFIED |
| CC-CHANGE-005 | IHR-002 | 隔离候选写入和原件未变断言 | SATISFIED |
| CC-CHANGE-006 | IHR-002/003 | 资源策略、工作进程超时/清理、warning 和错误处理 | SATISFIED |
| CC-CHANGE-007 | IHR-001 | 专用依赖清单及目标 `venv` 依赖安装证据 | SATISFIED |

## 6. Preservation & Guardrail Assessment

### 6.1 Preservation

| CC-PRESERVE | Implementation Impact | ATR Evidence | HVR Evidence | Status |
|---|---|---|---|---|
| CC-PRESERVE-001 | Potential Impact | `ATR-RUN-011` 静态包边界检查 | N/A | SATISFIED |
| CC-PRESERVE-002 | Impacted | 输入哈希不变和候选独立测试 | N/A | SATISFIED |
| CC-PRESERVE-003 | Impacted | 公式目标拒绝及含公式工作簿渲染关闭 | N/A | SATISFIED |
| CC-PRESERVE-004 | Impacted | 未验证格式/结构 fail-closed 测试 | N/A | SATISFIED |
| CC-PRESERVE-005 | Potential Impact | 无 Odoo/业务/Provider/HTTP/Queue 导入检查 | N/A | SATISFIED |
| CC-PRESERVE-006 | Impacted | 错误、超时、Mapping 失败无候选泄漏测试 | N/A | SATISFIED |

### 6.2 Applicable CC Guardrails

| CC 来源 | TDD 来源 | Evidence | Status |
|---|---|---|---|
| CC §7：服务契约与 Mapping Plan | TDD §§3.2—3.3 | ATR-TEST-003—005 | SATISFIED |
| CC §7：格式与公式约束 | TD-003—006 | ATR-TEST-003/005/006 | SATISFIED |
| CC §7：显式 Mapping Plan | TD-007 | ATR-TEST-004 | SATISFIED |
| CC §7：同步有限执行 | TD-008 | ATR-TEST-007 | SATISFIED |
| CC §7：文件安全、临时清理和错误处理 | TDD §7.1—7.3 | ATR-TEST-002/007/008 | SATISFIED |
| CC §7：解析器告警不得静默吞掉 | TDD §7.1 | ATR-TEST-009 | SATISFIED |

## 7. Automated Verification Assessment

`ATR-RUN-011` 在项目 `venv` / Python 3.11.9 上执行，共 **17 PASS、0 FAIL、0 ERROR**。CC-TEST-001—009 在 ATR 覆盖矩阵中均有当前代码基线证据；`compileall`、`pip check` 和模板同步检查通过。历史失败运行保留并关联到已修复问题，不作为当前基线失败。测试只证明列出的合成结构、格式关闭策略和边界行为，不外推到任意 Office 模板或生产容量。

## 8. Human Verification Assessment

```text
Human Verification: N/A
Source: Frozen CC-OFFICE-M1-001 §11 and Appendix B
Reason: CC 是纯 Python 核心；所有 CC-TEST 均标记人工验证为否。
```

Codex 内置浏览器只观察了现有 Odoo 聊天页没有 Office Engine UI；该观察在 HVR 中单独记录，不作为人工场景 PASS。用户已批准关闭 CC，但没有改变 HVR 的 N/A 结论。

## 9. Deviation & Stop Condition Assessment

| 项 | 评估 |
|---|---|
| Deviation | None；无未经批准的基线或范围变化 |
| Stop condition | macOS 4 GB `RLIMIT_AS` 预算不能落实；服务按 CC 约定返回 `OFFICE_RESOURCE_LIMIT` 并安全拒绝 |
| Resolution | 当前实施符合超预算 fail-closed 要求；目标部署平台的资源预算仍是后续生产开放事项，不是本 CC 的生产容量承诺 |

## 10. Open Issues / Findings / Evidence Gaps

| ID | 来源 | 描述 | Closure Impact | Human Judgment Required | 依据 |
|---|---|---|---|---|---|
| OI-001 | IHR/ATR | macOS 低内存限制及目标生产资源预算未验证 | Non-Blocking | No | CC-TEST-007 要求无法落实时拒绝；实现和测试均安全拒绝，不声称生产容量通过 |
| OI-002 | IHR/ATR | 指定真实 XLSX/DOCX 含未准入结构，当前被拒绝 | Non-Blocking | No | CC §13 #6 要求未通过能力保持关闭；当前未开放这些样本 |
| OI-003 | HVR | 本 CC 无 Odoo Office UI 或完整聊天文件流程 | Non-Blocking / N/A by CC | No | CC 明确人工 UI 验收不适用；浏览器观察已记录且未记 PASS |
| ATR 限定 | ATR §9 | 未提供真实口令保护 Office 文件；仅验证 CFB/OLE 签名拒绝 | Non-Blocking | No | 本包对 CFB/OLE 签名一律拒绝；此限制已在 ATR 明确披露，不宣称已验证加密解密 |

以上事项均不违反 CC 的强制义务：生产资源未声明通过；未支持格式/结构保持关闭；无人工 HVR 要求；未声称解密或通用 Office 兼容。当前无 Blocking 或 Undetermined 项。

## 11. Evidence Baseline Consistency

| Evidence Source | Baseline | Valid for Current Code? | Basis |
|---|---|---|---|
| IHR | Base commit `ae9e42e7e46394ed3d5c212b7779ee05c3882db9` + 本次限定工作树包 | Yes | IHR 变更清单与当前工作区包一致 |
| ATR-RUN-011 | `WT-office_core:5430736474b92ddb2d0dc928e478621db877b4a8aedeeb546887d55e398eaf78` | Yes | 按 `.py/.txt` 相对路径和字节计算的源码指纹一致；后续仅修改记录文档 |
| HVR | 同一工作树包基线 | Yes | HVR 记录人工验证 N/A 和浏览器环境观察；无代码变更 |

## 12. Done Criteria Assessment

| Done Criterion | Evidence | Status | Gap |
|---|---|---|---|
| CC §13 #1：变更和边界 | IHR §5；CC 允许文件范围 | SATISFIED | — |
| CC §13 #2：适用测试、缺口、能力关闭 | ATR §§3—7、10 | SATISFIED | 限定与关闭能力已明确 |
| CC §13 #3：依赖、venv、pip check、smoke、许可证 | ATR §§4、9 及 CC-TEST-001 evidence | SATISFIED | — |
| CC §13 #4：纯 Python 边界 | ATR-TEST-009 | SATISFIED | — |
| CC §13 #5：输入不变、失败无候选、限制/错误/warning/清理 | ATR-TEST-002/005/007/008/009 | SATISFIED | — |
| CC §13 #6：只开放有证据的能力 | IHR-004；ATR-TEST-006 | SATISFIED | 真实复杂样本继续拒绝 |
| CC §13 #7：不宣称回读、交付或 UI 完成 | IHR §8；HVR §4 | SATISFIED | `office_verify` 留待 CC-002 |
| CC §13 #8：证据绑定 CC/基线/上游 | IHR、ATR、HVR 与本 FR | SATISFIED | — |

## 13. Final Closure Determination

**Final Closure Status: SATISFIED**

CC-001 的强制变更、保留边界、适用技术防护栏、9 项测试义务和 8 项完成标准均有当前基线证据并满足。HVR 按 CC 为 N/A。未决生产资源预算和不开放的真实模板能力不会改变本 CC 规定的 fail-closed 行为，因此为非阻塞事项。

该结论表示 CC-OFFICE-M1-001 有足够证据关闭；不批准合并后的发布，不表示 M1 全部完成，也不表示 Office 文件已接入 Odoo 聊天。用户已批准本 CC 关闭。

## 14. Handoff to Human Review

```text
Closure Assessment Complete: Yes
Human Review Required: Yes
CC Closure Approval: Granted by user on 2026-10-20
Merge / Release Decision: Not part of this FR
```

后续工作按 Implementation Plan Phase 2 进行；`CC-OFFICE-M1-002` 另行评审、冻结后才获得实施授权。

## 附录 A — Evidence Reference Index

| Evidence Type | Reference | Current / Valid | Purpose |
|---|---|---|---|
| CC | [CC-OFFICE-M1-001](../../../context/intent/CC-OFFICE-M1-001.md) | Frozen | 关闭义务来源 |
| IHR | [IHR](IHR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) | Yes | 实施事实 |
| ATR | [ATR](ATR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) | Yes | 自动化运行证据 |
| HVR | [HVR](HVR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) | Yes; N/A by CC | 人工验证要求和浏览器观察边界 |
| Latest test log | [ATR-RUN-011](evidence/ATR-RUN-011-unittest.log) | Yes | 17 项 unittest |
| Browser observation | [BROWSER-OBSERVATION-001](evidence/BROWSER-OBSERVATION-001.md) | Yes | 脱敏页面环境观察 |

## 附录 B — FR Version History

| Version | Date | Closure Status | Reason |
|---|---|---|---|
| v1.0 | 2026-10-20 | SATISFIED | 基于 CC、IHR、ATR-RUN-010、HVR N/A 和工作树源码基线评估 |
| v1.1 | 2026-10-20 | SATISFIED | 绑定 ATR-RUN-011 当前测试基线；真实样本留在本机、不随 Git 提交，自动化改用合成扩展结构 |
