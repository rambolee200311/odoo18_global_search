# IHR — OFFICE-ENGINE-M1-SPAWN-REMEDIATION

## 0. 文档治理

本记录只记载 spawn worker 导入及资源监控修复的实施事实。它不修改或关闭 CC-OFFICE-M1-004 / CC-OFFICE-M1-006，不覆盖既有 FAIL/BLOCKED 证据。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-SPAWN-REMEDIATION` |
| 上游问题 | TV-SPAWN-001/002/004；CC-004 成功链路历史 FAIL |
| 工作类型 | 缺陷修复 |
| 模块 | `mymodules/office_core/`、`mymodules/office_engine_odoo/` |
| 执行人 | Codex |
| 日期 | 2026-10-22 |
| 当前状态 | Implementation Complete；独立复验见 ATR；聊天路由 HVR 未通过/未开放 |
| Git 基线 | `19499b84a9b62b1ee5561fae81c3ff33d4fc64ca` 加本记录列出的工作树变更；未提交 |

## 2. 基线与授权说明

本修复直接针对用户要求完成真实 Office golden path 后暴露的 worker 缺陷。没有新建或冻结专用 CC；CC-004 与 CC-006 的原始状态保持不变。该实施记录不作为重新解释其验收范围或豁免聊天 handoff 门禁的依据。

## 3. 当前实施状态

| 项 | 状态 |
|---|---|
| `spawn` 稳定导入身份 | 已修复并由 Odoo 集成测试及真实 ORM 请求验证 |
| macOS 4 GiB worker 预算 | 改为父进程 RSS 采样监督；无法采样/超限均 fail-closed |
| Core → Verify → 私有输出附件 | `uid=2`, `env.su=False` 的真实 `odoo18ce` 请求通过 |
| 聊天 Office handoff 与下载 UI | 未开放；当前聊天适配仍按已冻结 MVP 策略拒绝 Office 附件 |
| Linux/生产内存硬上限 | 未验证；RSS 采样是带超调风险的监督，不是内核硬限制 |

## 4. 实施历史（仅追加）

### IHR-001 — 统一纯 Python worker 导入身份

`office_engine_odoo` 从 Odoo 已配置的可信 `mymodules` 根加载 `office_core` 与 `office_verify` 普通 Python 包，校验包来源，并在父进程启动 spawn 前加入该根路径。worker target 因而以 `office_core.service` 身份序列化，spawn 子进程可从同一可信根重新导入。用户输入、附件和 Mapping Plan 不参与导入路径解析。

### IHR-002 — 以 RSS 监督替代 `RLIMIT_AS`

删除 Core 对 `RLIMIT_AS` 的内存限制依赖。父进程按有限间隔读取 macOS `libproc` 或 Linux `/proc` 的 worker RSS；无法观测或超过 `ResourceBudget.max_memory_bytes` 时终止、等待回收并拒绝返回候选。保留 wall-clock timeout 和可用平台上的 CPU 限制。RSS 采样存在时间窗口及超调，不被描述为硬上限。

### IHR-003 — 增加修复回归覆盖

Core 增加正常预算成功、RSS 不可观测拒绝、超预算终止三项 worker 行为覆盖；Odoo TransactionCase 增加通过真实 spawn Core 与独立 Verify 的合法 XLSX 黄金路径。

## 5. 实际变更清单

| 文件 | 变更 |
|---|---|
| `mymodules/office_core/service.py` | RSS 监测、失败关闭、worker 终止/回收；移除 `RLIMIT_AS` |
| `mymodules/office_core/tests/test_office_core.py` | RSS 正常、不可观测及超限回归测试 |
| `mymodules/office_engine_odoo/models/office_document_request.py` | 从配置的可信 Addon 根导入普通 Python 包，校验来源 |
| `mymodules/office_engine_odoo/tests/test_office_document_request.py` | Odoo 内 spawn → inspect → render → independent verify 黄金路径 |

## 6. 偏差与停止事项

| 项 | 状态 | 处置 |
|---|---|---|
| 专用修复 CC / 冻结实施计划尚未建立 | 流程偏差 | 代码变更依用户直接要求进行；保留本记录，不回写既有 CC 状态；需在后续基线化中处理 |
| Linux 部署环境及生产 RSS 预算 | 未决 | 不宣称生产部署准入；目标环境确定后补充平台验证 |
| M1 聊天 handoff/Mapping/下载链路 | 未处理 | 不绕过 CC-005/CC-006 的 fail-closed 边界；须另行实现并验收 |

## 7. 问题清单

1. RSS 监督是软性边界，存在采样超调；生产资源预算仍需目标环境验证。
2. 当前聊天层尚无从自然语言生成 Mapping Plan 并调用内部服务的成功路由，因此本次修复不使聊天 UI 生成下载链接。
3. 历史 CC-004/006 状态未因本次新证据自动变更。

## 8. 交接摘要

自动化和当前开发库真实 ORM 证据见同目录 ATR 及 [成功链路 JSON](../../CC-OFFICE-M1-004/evidence/spawn_repair_success.json)。聊天 UI 正常生成 HVR 尚未执行；成功服务侧证据不替代用户界面验收、生产预算验证或 CC 关闭。
