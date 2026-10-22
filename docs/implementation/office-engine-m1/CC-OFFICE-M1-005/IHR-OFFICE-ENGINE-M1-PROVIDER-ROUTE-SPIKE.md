# IHR — CC-OFFICE-M1-005 Provider 前路由 Spike

## 0. 文档治理

本记录只登记实际执行与证据，不改变 SRS、TDD、Implementation Plan 或冻结 CC。历史条目仅追加；当前状态摘要可更新。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-PROVIDER-PRE-ROUTE-SPIKE` |
| CC | [CC-OFFICE-M1-005](../../../context/intent/CC-OFFICE-M1-005.md) `v1.0.0 Frozen` |
| 模块 | `mymodules/odoo-llm`（仅运行时探针，未修改模块） |
| 工作类型 | Provider 前路由验证性 Spike |
| 执行人 | Codex Agent；批准人 `lijianqiang` |
| 执行日期 | 2026-10-21 |
| 当前实施状态 | **负责人于 2026-10-22 批准行政关闭；Spike 结论 FAIL；FR 仍 NOT SATISFIED** |
| Odoo / DB | Odoo 18.0 / `odoo18ce`，使用 `odoo.conf` |
| Python / PostgreSQL | Python 3.11.9 / PostgreSQL 16.14 |
| Odoo-LLM 基线 | `609ec6dda3645165f6a4a843d7af5d286081a29d`，嵌套工作树干净 |
| 根仓库基线 | `e91bf5a502b8970bfa9c795335e5ee2dce0e57b7`；根工作树原有大量无关变更，未纳入本任务 |
| 运行实例 | 端口 8091，进程 PID 41995；由上述源码清洁检查后启动 |

### 1.1 当前状态摘要

| 项 | 状态 |
|---|---|
| 产品代码变更 | 无 |
| CC-CHANGE / 验证契约 | 完成执行并有证据 |
| 未批准偏离 | 无；遵守 CC 对 Phase 5 的一次性窄范围例外 |
| 自动化/运行时验证 | 有 PASS、FAIL、BLOCKED、INCONCLUSIVE；见 ATR |
| 人工 UI 验证 | N/A；本 CC 不要求用户 UI，也未触发浏览器 Provider 交互 |
| 未关闭问题 | CC-TEST-005/008 的内部路由 handoff 未验证；CC-004 FR 仍 NOT SATISFIED。CC-TEST-006 历史 FAIL 已由独立 pre-route-fix CC 修复，但未在本 CC 下重跑完整契约 |
| 当前状态 | CC-005 行政关闭；原始 Spike 结果和未通过项保留；Phase 5 / CC-006 Gate 仍阻塞 |

## 2. Coding Contract 基线

| 项 | 引用 |
|---|---|
| 范围 | CC-005 §3—§7；仅合成附件、mock/stub Provider 和安全拒绝/路由验证 |
| 上游设计 | SRS V1.0.0 Frozen、TDD V0.4 Frozen、Implementation Plan V0.3 Frozen |
| Odoo-LLM | CC-005 §2 锁定的干净 HEAD `609ec6d…` |
| 测试契约 | CC-TEST-001—010 |
| 已知遗留 | CC-004 FR `NOT SATISFIED`；spawn 子进程无法导入 `odoo.addons.office_core`。未修复、未改写状态 |

## 3. 当前实施状态

本 CC 是验证性 Spike，无产品代码实施。已执行 Odoo-LLM 运行时路由观察、payload 格式化捕获、普通用户/跨用户权限观察、mock 工具循环和 ORM 清理。详细结果见 [ATR](ATR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) 与 [Spike 报告](OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE-REPORT.md)。

## 4. 实施历史条目（仅追加）

### IHR-001 — 冻结与基线启动

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Implementation |
| Action | 负责人批准冻结 CC-005 并授权按窄范围运行 Spike；确认 Odoo-LLM HEAD 和工作树干净后停止旧 PID 并按 `venv/bin/python odoo-bin -c odoo.conf` 启动实例。 |
| Reason | 满足 CC-TEST-001 运行时与源码基线要求。 |
| Files / Components | CC-005；Odoo runtime；`mymodules/odoo-llm` |
| Contract Reference | CC-TEST-001；CC §0.1/§2 |
| Result | Completed |
| Deviation | None |
| Follow-up | 运行实例保留在 8091，供开发环境继续使用。 |

### IHR-002 — Mock Provider 运行时探针

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Implementation |
| Action | 使用临时 `odoo-bin shell -c odoo.conf -d odoo18ce --no-http` 探针，对现有普通用户创建唯一标记的合成附件/线程；临时 patch 仅存在于 shell 进程，OpenAI Provider 与工具执行均由本地 stub 替代。 |
| Reason | 观察服务端附件预检相对 Provider dispatch 的顺序、payload 和用户隔离；避免真实 Provider 网络请求。 |
| Files / Components | Odoo-LLM `llm.thread.generate`、`_check_unsupported_attachments`、OpenAI message formatter / provider dispatch；本地临时探针 |
| Contract Reference | CC-TEST-002—009 |
| Result | Completed；发现 CC-TEST-006 FAIL、CC-TEST-005 BLOCKED 子项、CC-TEST-008 INCONCLUSIVE |
| Deviation | None |
| Follow-up | 不修产品代码；任何 fail-closed 修复需单独 TDD/CC。 |

### IHR-003 — 合成记录清理与 hook 移除

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Implementation |
| Action | 通过现有非超级用户 LLM Manager（uid 2，`su=False`）调用 ORM 删除本次唯一标记线程、消息和附件；验证记录数为 0；删除所有临时探针/输出日志；扫描 Odoo-LLM 产品目录无临时 hook 标记。 |
| Reason | 满足 CC-TEST-009/010 的清理与脱敏证据要求。 |
| Files / Components | Odoo ORM；`/tmp/cc005_*` 临时文件；`mymodules/odoo-llm` |
| Contract Reference | CC-TEST-009、CC-TEST-010；CC §5.1/§6 |
| Result | Completed；清理方法与证据见 `evidence/cleanup-proof.txt` |
| Deviation | None |
| Follow-up | filestore 物理对象遵循 Odoo 延迟 GC；未直接删除文件。 |

## 5. 实际变更清单

| 文件/组件 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `docs/context/intent/CC-OFFICE-M1-005.md` | 修改 | 冻结记录及一处时态勘误；不改变范围/测试契约 | Freeze governance |
| `docs/implementation/office-engine-m1/CC-OFFICE-M1-005/` | 新增 | IHR、ATR、HVR N/A、FR、Spike 报告及脱敏证据 | CC-TEST-001—010 |
| `mymodules/odoo-llm` 产品文件 | 未修改 | 仅锁定、检查干净源码基线 | CC §2 / CC-TEST-001 |
| 临时 shell 探针 | 已删除 | 不留在仓库或 `/tmp` | CC-TEST-010 |

## 6. 偏离与停止条件

| 事项 | 结果 |
|---|---|
| CC-004 spawn/import 缺陷 | 保持开放，FR 仍 `NOT SATISFIED`；负责人接受仅限本 Spike 的风险降低，不构成功能通过 |
| Phase 5 Part I 前置条件 | 按 CC-005 §0.1 的一次性窄范围例外执行，仅验证 Provider 前安全拒绝/隔离；未修改冻结计划 |
| CC-TEST-006 MIME 不一致 | 触发失败关闭门禁：`.xlsx` 文件名配纯文本内容经 Odoo 变为 `text/plain`，预检拒绝数为 0，mock Provider 收到合成文本标记。未发外部网络请求；未实施修复 |
| CC-TEST-008 独立 Addon 路由 | 未创建/安装独立 Addon（CC 禁止模块安装/产品实现）；handoff 能力结论 INCONCLUSIVE |
| 聊天适配 | 依 CC §7 停止；CC-006 与用户文件生成保持阻塞 |

## 7. 遗留问题与后续

| 问题 | 状态 | 影响 / 后续 |
|---|---|---|
| 文件名/内容 MIME 不一致时未 fail closed | Open / Blocking | 用户上传 `.xlsx` 名称而内容被识别为文本时，现有路径可把文本送入 Provider；需另行批准设计与实现契约后修复并回归 |
| 独立 Addon 向受控 Office 服务 handoff | Inconclusive | 本 Spike 只证明当前可识别 MIME 的拒绝路径；未证明服务路由、授权上下文传递或独立 Addon 集成 |
| CC-004 spawn 导入问题 | Open / Blocking | 成功渲染/附件交付仍不可用；不得进入完整聊天生成 |
| Provider 范围 | Limited | 目标实例只安装/启用一个 OpenAI service；结论不外推到其他 provider addon 或外部 API |

## 8. 移交摘要

- ATR 已记录最终运行 `ATR-RUN-001`；原生状态为 7 PASS、1 FAIL、2 BLOCKED、0 MISSING。CC-TEST-008 的可行性评估结论为 INCONCLUSIVE，该结论不另计为原生测试状态。
- HVR 为 N/A，原因是 CC-005 无浏览器 UI / 用户交互验收要求。
- FR 为 `NOT SATISFIED`。负责人于 2026-10-22 指示关闭 CC-005；这是行政关闭，不构成测试豁免，不把 FR 改为满足，也不解除 Phase 5 / CC-006 Gate。
- 所有产品扩展 hook 已在临时 shell 退出时恢复，临时文件已物理删除；清理证明见 `evidence/cleanup-proof.txt`。

### IHR-004 — 负责人批准行政关闭

| 字段 | 内容 |
|---|---|
| 日期 | 2026-10-22 |
| 依据 | 负责人本轮明确指示“关闭 cc-05，提交和推送 git，起草 cc-06” |
| 处置 | 关闭 CC-005 的执行记录；FR 保持 `NOT SATISFIED`，ATR 原生状态保持 7 PASS、1 FAIL、2 BLOCKED；不登记测试豁免，不记为 `FROZEN WITH OPEN ITEMS` |
| 后续证据 | 独立 `CC-OFFICE-M1-PRE-ROUTE-FIX` 已修复其范围内的伪装附件拦截问题；该 FR/ATR 不重写本 CC 的历史运行结果，也未验证 handoff |
| Gate | CC-004 FR `NOT SATISFIED`、CC-TEST-005/008 handoff 未闭环；本次关闭不授权 Phase 6 实施 |

## 附录 — 基线变更历史

无运行中 SRS/TDD/Implementation Plan 基线变化。CC-005 冻结版本在执行前仅更正时态描述，未改变义务或范围。

## 附录 — 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-10-21 | 建立执行记录；后续仅更新当前快照，历史条目保留。 |
| v1.1 | 2026-10-22 | 追加负责人行政关闭决策；保留 Spike FAIL、FR NOT SATISFIED 及 handoff 未决事实；单独记录 pre-route-fix 后续证据，不改写 ATR。 |
