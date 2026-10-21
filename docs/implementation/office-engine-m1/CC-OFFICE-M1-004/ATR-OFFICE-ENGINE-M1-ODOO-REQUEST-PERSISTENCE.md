<!-- 使用 Coding/ATR 模板；无执行不得标 PASS，运行历史只追加。 -->

# ATR — OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE

## 0. 文档治理

只记录 CC-OFFICE-M1-004 实际运行的自动化验证；不替代人工验收或 CC 关闭评估。

负责人于 2026-10-21 批准行政关闭 CC。该决定不改变下方任何测试的原生状态；成功输出链路仍为 FAIL，缺失或受阻的测试仍保持原状态，详见 FR。

## 1. Execution Metadata

| 字段 | 值 |
|---|---|
| Intent ID / IHR | `OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE` / [IHR](IHR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) |
| CC / Module | `v0.3 Frozen` / `mymodules/office_engine_odoo/` |
| Environment | 项目 `venv`；Odoo 18；现有 `odoo18ce`；`odoo.conf` |
| Test Framework | Odoo `TransactionCase`、Odoo shell runtime probes、纯 Python checks |
| Initial Code Baseline | `ea45974f8f38444d5aff250833b8dcae7ff0f92f` + 未提交工作树 |
| Execution Start / By | 2026-10-21 / Codex Agent |

## 2. Test Contract Baseline

引用冻结 CC-TEST-001—016、CC-PRESERVE-001—007，及 TDD V0.4 §§5—7；需求追溯见 CC §14。

## 3. Current Automated Test Status

| 指标 | 值 |
|---|---|
| Required Tests | 16 CC Tests |
| PASS / FAIL / PARTIAL / BLOCKED / NOT RUN | 5 / 1 / 5 / 2 / 3 |
| Latest Valid Run | 2026-10-21；Odoo `-u office_engine_odoo --stop-after-init --test-enable --test-tags /office_engine_odoo` exit 0；6 TransactionCase tests |
| Current Code Baseline | 工作树未提交；测试与当前 addon 文件一致，未提交指纹未冻结 |
| Evidence Baseline Match | Partial — ORM, static scan, unsupported-format failure path run; successful core output path failed at spawn import |

## 4. Core Test Contract Coverage Matrix

| CC 来源 | 自动化验证 | Run | 原生结果 | Workflow Evidence Status | Evidence |
|---|---|---|---|---|---|
| CC-TEST-001 | 字段/最小模型形状 TransactionCase | 2026-10-21 | PASS | Pass | 六项 Odoo 测试运行，exit 0 |
| CC-TEST-002 | 部分状态机/非法跳转 TransactionCase | 2026-10-21 | PARTIAL | Partial | accepted→validating 及非法跳转覆盖；完整成功/失败状态链未覆盖 |
| CC-TEST-003 | owner 搜索、读取、写入 Record Rule | 2026-10-21 | PASS | Pass | B 搜索无记录、直接读取/修改被拒；未使用 sudo 代替验证 |
| CC-TEST-004 | SQL UNIQUE + 重复 ORM 创建 | 2026-10-21 | PARTIAL | Partial | 数据库唯一约束拒绝重复键；尚未做独立 cursor 并发竞态 |
| CC-TEST-005 | 两独立 cursor 并发幂等 | — | NOT RUN | Missing | 成功服务路径被 spawn 导入阻塞 |
| CC-TEST-006 | Mapping Plan 经 Odoo 包装进入真实核心 | 2026-10-21 | BLOCKED | Blocked | 当前 spawn 子进程无法导入 `odoo.addons.office_core` |
| CC-TEST-007 | core→verify→交付成功准入 | 2026-10-21 | FAIL | Fail | 成功路径探针失败：`ModuleNotFoundError: No module named 'odoo.addons.office_core'`；不把错误返回伪装为 PASS |
| CC-TEST-008 | 附件私有/owner ACL/不可变 | 2026-10-21 | PARTIAL | Partial | TransactionCase 验证 owner 可读、非 owner `check('read')` 和 ORM `read(['raw'])` 被拒、普通 owner 写/删被拒；成功交付路径未跑通 |
| CC-TEST-009 | 失败无输出附件 | 2026-10-21 | PARTIAL | Partial | 真实 ORM `.xls` 拒绝：请求 failed 且无输出；verify/attachment commit 失败注入未执行 |
| CC-TEST-010 | 文件/结构预算边界 | — | NOT RUN | Missing | 未实测资源阈值拒绝 |
| CC-TEST-011 | 解析隔离及 attachment create-to-commit 计时 | 2026-10-21 | BLOCKED | Blocked | create-to-commit 代码存在；成功交付未达，尚无真实耗时数据 |
| CC-TEST-012 | ORM rollback / delayed GC | — | NOT RUN | Missing | 未在本 CC 重测；不运行全局 GC、不直接删 filestore |
| CC-TEST-013 | Addon 安装/升级 | 2026-10-21 | PASS | Pass | `odoo18ce` 安装并两次升级，测试命令 exit 0 |
| CC-TEST-014 | 纯 Python 边界/无 Queue Job | 2026-10-21 | PASS | Pass | 两核心目录无改动；manifest 无 queue 依赖、请求模型无队列字段 |
| CC-TEST-015 | 安全行为回归 | 2026-10-21 | PARTIAL | Partial | owner 隔离、附件私有和稳定拒绝已有证据；成功输出及事务错误路径未验证 |
| CC-TEST-016 | 固定 `rg` 纯 Python 隔离扫描 | 2026-10-21 | PASS | Pass | 精确命令 exit 1，零匹配；符合 CC 定义 |

## 5. Test Run History（Append-only）

### ATR-RUN-001 — 初次 ORM 安装测试

| 字段 | 值 |
|---|---|
| 命令 | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -i office_engine_odoo --stop-after-init --test-enable --test-tags /office_engine_odoo` |
| 结果 | FAIL：1/6。测试错误地用通用 `check_access` 断言附件关联权限；发现 Odoo 18 的 `ir.attachment` 需要专用 `check('read')`。 |
| 后续 | 修正源/输出附件授权检查与测试断言；未掩盖本次失败。 |

### ATR-RUN-002 — 模块升级与 ORM 回归

| 字段 | 值 |
|---|---|
| 日期 | 2026-10-21 |
| 命令 | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u office_engine_odoo --stop-after-init --test-enable --test-tags /office_engine_odoo --log-level=warn` |
| 结果 | PASS；exit 0，6 TransactionCase tests。后续同命令复跑亦 exit 0。 |
| 备注 | Odoo 日志中重复 UUID 的唯一键 ERROR 是 `assertRaises(IntegrityError)` 预期场景；另有环境中已存在的缺失/不可安装模块告警，与本 addon 无关。 |

### ATR-RUN-003 — 静态隔离扫描

| 字段 | 值 |
|---|---|
| 日期 | 2026-10-21 |
| 命令 | `rg -n --glob '*.py' '^[[:space:]]*(from[[:space:]]+odoo([.]|[[:space:]]|$)|import[[:space:]]+odoo([.]|,|[[:space:]]|$))' mymodules/office_core mymodules/office_verify` |
| 结果 | PASS；exit 1，零匹配。 |

### ATR-RUN-004 — 真实成功路径集成探针

| 字段 | 值 |
|---|---|
| 环境 | 项目 `venv`；现有 `odoo18ce`；真实 ORM + `office_core`/`office_verify` API；仅本探针临时将内存/超时预算调大，以越过本机 macOS `RLIMIT_AS` 差异，不作生产预算证据。 |
| 结果 | FAIL；直接调用 `_render_request_sync` 后，spawn 子进程反序列化出现 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`，请求正确持久为 `failed / OFFICE_ENGINE_FAILED / inspect`，`output_attachment_id=False`。验证了核心启动失败的 fail-closed 行为，但没有生成成功文件。 |
| 清理 | 唯一标记的合成输入附件和失败请求通过 Odoo ORM 删除并提交；没有直接操作 filestore。 |
| 处置 | 冻结核心包未修改；需独立技术变更处理 spawn 可导入性。 |

### ATR-RUN-005 — 不支持格式的真实 ORM 失败路径

| 字段 | 值 |
|---|---|
| 日期 | 2026-10-21 |
| 结果 | PASS；`.xls` 返回 `failed / OFFICE_UNSUPPORTED_FEATURE / format`，请求无 `output_attachment_id`。 |
| 清理 | 唯一标记请求和源附件均通过 ORM 删除并提交；不运行全局 GC。 |

## 6. Regression Verification

| CC-PRESERVE | 验证 | Run | 结果 | Workflow Evidence Status |
|---|---|---|---|---|
| 001/002 | 两个纯 Python 包边界、未修改 | — | NOT RUN | Missing |
| 003/004 | 附件权限、回读准入 | — | NOT RUN | Missing |
| 005/006/007 | 事务/同步/Queue/错误脱敏 | — | NOT RUN | Missing |

## 7. Issues

发现并修正通用 `check_access` 不执行 `ir.attachment` 关联记录检查的问题。当前已知关键阻塞为 spawn child 无法导入动态注册的 Odoo addon namespace。模块安装、ORM/失败路径验证不等于文件成功渲染已可用。

## 8. Special Verification

本 CC 成功关键路径必须调用真实 Odoo ORM、`office_core` 与 `office_verify`；mock 仅允许用于 CC 明确的失败注入，不能代替成功路径。

| 验证 | 原生状态 | Workflow Evidence Status | 证据 |
|---|---|---|---|
| ACL / owner rule / 私有附件 | PARTIAL | Partial | TransactionCase 6 项通过；见 ATR-RUN-002 |
| 并发 UUID / create-to-commit 耗时 | BLOCKED | Blocked | 成功服务链路不能启动核心子进程；未记录虚构耗时 |
| 失败回滚 / 延迟 GC | PARTIAL | Partial | 不支持格式失败无输出已实测；附件事务回滚与 GC 留待后续 |

## 9. Evidence Inventory

| Evidence | 状态 |
|---|---|
| Addon install/upgrade 与 Odoo tests | PASS；升级命令 exit 0，6 tests；首次错误断言失败保留在 RUN-001 |
| CC-TEST-016 扫描输出/退出码 | PASS；exit 1，零匹配 |
| 失败格式生命周期探针 | PASS；失败状态无输出且 ORM 清理 |
| 成功路径/并发/提交计时 | FAIL/BLOCKED；spawn 包导入阻塞 |

## 10. Handoff to HVR / FR

HVR：冻结 CC 所有测试的人工验证列均为“否”，按 HVR N/A 记录；不把浏览器观察算作 PASS。FR 待实际证据完成后编写。

## 附录 B — Version History

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1 | 2026-10-21 | 建立初始 NOT RUN 测试基线。 |
| 0.2 | 2026-10-21 | 追加安装/升级、6 项 ORM、静态扫描、失败路径及成功路径失败证据；更新分项状态。 |
| 0.3 | 2026-10-21 | 追加负责人批准行政关闭记录；不更改测试矩阵和历史运行结果，成功生成路径仍未验证。 |
