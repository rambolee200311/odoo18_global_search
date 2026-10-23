# M2 项目授权登记册

本文件仅记录负责人明确批准的未通过项处置，不改变原始测试、HVR 或上游阶段 Gate 状态。

## EXEMPTION-CC-M2-004-001

| 字段 | 记录 |
|---|---|
| 豁免项 | Odoo `HttpCase.browser_js` 自动浏览器测试（ATR-ISSUE-001；CC-TEST-002/010 的自动化浏览器子项） |
| 状态 | `Skipped` |
| 原因 | 本机缺少 `websocket-client`，未安装额外依赖；负责人已通过内置浏览器确认卡片显示、合法字段选择、保存及确认，并明确批准关闭 CC-M2-004。 |
| 影响 | 人工核心路径有证据，但没有自动浏览器回归；普通消息隔离、控制台错误等仍依靠非浏览器自动化证据或未验证。原 ATR 状态保持 `SKIPPED/PARTIAL`。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-10-23 明确指示“cc-004允许关闭，提交推送git”；并于 2026-10-23 确认“人工验证通过”。 |

## EXEMPTION-CC-M2-004-002

| 字段 | 记录 |
|---|---|
| 豁免项 | HVR-SCN-003 未由人类完整验证的取消/不完整映射子场景；HVR-SCN-004 普通聊天发送与浏览器 console 检查 |
| 状态 | `Missing` |
| 原因 | 负责人确认了卡片展示、字段选择、保存和确认；其余子场景未在内置浏览器中完整执行。负责人随后明确批准关闭 CC-M2-004。 |
| 影响 | 不声称取消、澄清补项及错误后普通聊天发送均通过；残余交互回归风险被接受。HVR 保持 PARTIAL，场景状态保持 NOT RUN。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-10-23 明确指示“cc-004允许关闭，提交推送git”。 |

## EXEMPTION-CC-M2-004-003

| 字段 | 记录 |
|---|---|
| 豁免项 | Implementation Plan 阶段 3 XML-RPC 安装/升级 Gate 的证据缺口（CC-M2-004-OPEN-001） |
| 状态 | `Missing` |
| 原因 | CC-M2-003 ATR 有 CLI 升级与 TransactionCase 证据，但没有 Plan 明定的 XML-RPC 安装/升级记录；负责人已批准 CC-M2-004 带该缺口关闭。 |
| 影响 | 仅接受本次 CC 的行政关闭处置；阶段 3 Gate 仍为 OPEN，计划阶段不标记 PASS，M2 阶段与后续阶段 Gate 仍需独立评估。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人于 2026-10-23 明确指示“cc-004允许关闭，提交推送git”。 |

## EXEMPTION-CC-M2-005-001

| 字段 | 记录 |
|---|---|
| 豁免项 | 全 Addon 回归：`TestOfficeMappingSession.test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message` 的共享数据库全表 Session 数断言 |
| 状态 | `Failed`（原始失败保持不变） |
| 原因 | 测试断言开发数据库中全表 Session 数必须为 0；既有历史记录导致断言失败。负责人认定这是测试基建缺陷，不作为 CC-M2-005 条件关闭的阻塞。 |
| 影响 | 不证明该测试通过，不证明全 Addon 全绿。只接受该失败不阻断 CC-M2-005 的条件关闭；脆弱断言的修复作为独立测试基建债务跟踪。其他需求缺口和 PARTIAL 证据继续按各自状态保留。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确裁定：“测试代码写了‘全表 Session 必须为 0’这种脆弱的断言，遭遇了开发库的历史残留数据。这属于测试基建缺陷，不作为阻塞本 CC 关闭的理由”，并批准将 CC-M2-005 状态更新为 `CONDITIONALLY CLOSED`。 |

## EXEMPTION-CC-M2-005-001

| 字段 | 记录 |
|---|---|
| 豁免项 | 全 Addon 回归：`TestOfficeMappingSession.test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message` 的共享数据库全表 Session 数断言 |
| 状态 | `Failed`（原始失败保持不变） |
| 原因 | 该测试断言开发数据库中全表 Session 数必须为 0；既有历史记录导致断言失败。负责人认定这是测试基建缺陷，不作为 CC-M2-005 条件关闭的阻塞。 |
| 影响 | 不证明该测试通过，也不证明全 Addon 全绿。只接受该失败不阻断 CC-M2-005 条件关闭；脆弱断言修复作为独立测试基建债务跟踪。其他需求缺口和 PARTIAL 证据继续按各自状态保留。 |
| 授权人 | Li Jianqiang（项目工作区账号 `lijianqiang`；Git 身份 `rambolee200311 <rambolee200311@hotmail.com>`） |
| 授权证据 | 当前任务中负责人明确裁定：“测试代码写了‘全表 Session 必须为 0’这种脆弱的断言，遭遇了开发库的历史残留数据。这属于测试基建缺陷，不作为阻塞本 CC 关闭的理由”，并批准将 CC-M2-005 状态更新为 `CONDITIONALLY CLOSED`。 |

## 处置约束

- 上述授权只接受列明的未通过项；不把任何原生 `SKIPPED`、`NOT RUN`、`PARTIAL` 或 `OPEN` 改写为 PASS/RESOLVED。
- CC-M2-004 的处置为 `FROZEN WITH OPEN ITEMS`。对应 FR 的 Closure Status 仍按证据判断；豁免不自动使 Closure Status 成为 SATISFIED。
- CC-M2-005 的单项授权只接受列明的测试失败不阻塞其条件关闭；测试原生 FAIL 和 FR NOT SATISFIED 状态不变，其他未完成路径不在此授权范围内。
- CC-M2-005 的单项授权只接受列明的测试失败不阻塞其条件关闭；测试原生 FAIL 和 FR NOT SATISFIED 状态不变，其他未完成路径不在此授权范围内。
- 本登记不批准合并、发布、M2 阶段完成或变更 Implementation Plan 基线。
