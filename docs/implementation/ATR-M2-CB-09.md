# ATR-M2-CB-09 — Fileless Office Generation

## 状态

**AUTOMATED TESTS PASS — REAL PROVIDER/UI HVR PASS — FINAL ACCEPTED / CLOSED BY OWNER (2026-11-11)**

代码基线：当前 dirty worktree，分支 `main`，HEAD `de82bb9`。未暂存、提交、推送、重置或清理工作区。

## 自动化测试结果

| 测试层 | 命令/范围 | 结果 | 证据 |
|---|---|---|---|
| Pure XLSX verifier | `PYTHONPATH=mymodules venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py` | **12 passed** | 本地原始日志 `ATR-office-verify.log` |
| Responses Adapter SDK Mock | 将 Adapter、测试、Chat Provider 与依赖复制至隔离临时包后运行 `venv/bin/python -m pytest -q .../llm_openai/tests/test_responses_adapter.py` | **30 passed** | 本地原始日志 `ATR-responses-adapter.log` |
| Python syntax | `py_compile` 覆盖本轮改动的 Python 模块 | **PASS** | [ATR-python-syntax.log](evidence/CB-M2-CB-09/ATR-python-syntax.log) |
| Scoped whitespace check | `git diff --check`，限于 Route B/office_verify 实现文件 | **PASS** | 本轮命令退出码 0；未检查或修改其他历史改动 |
| Post-run integrity | Python syntax for final changed files, JSON evidence parse, scoped `git diff --check` | **PASS** | [ATR-post-run-integrity.log](evidence/CB-M2-CB-09/ATR-post-run-integrity.log) |

SDK Mock 测试证明请求结构与下载适配契约，不代表真实 Provider、Odoo ORM 或 UI 通过。

## 测试入口说明

- Adapter 测试必须在隔离包中加载，以避免直接导入 Odoo addon 的环境问题。初次隔离运行未复制 Chat Provider 测试依赖，导致 3 项兼容性用例为 harness `FileNotFoundError`；补齐同一源码包依赖后复测为上表的 30 passed。
- verifier 首次运行有 1 项断言期待了错误的中文说明文本；断言改为实际报告中的“无来源工作簿可供比较”后，最终结果为 12 passed。该调整没有放宽验证器行为。

## 未运行项目

| 验收层 | 状态 | 说明 |
|---|---|---|
| 生产部署/生产数据测试 | **OUT OF SCOPE** | 未访问生产环境或真实 Odoo 业务数据。 |
| Provider 账单金额 | **UNVERIFIED** | Responses usage 已记录；本次实际费用未从账单/账户侧核实。 |

## 证据文件

- 本地原始测试日志（保留在执行工作区，不随 Git 推送发布，因为日志可能包含测试联系信息）：`ATR-office-verify.log`、`ATR-responses-adapter.log`、`ATR-python-syntax.log`、`ATR-fileless-current-fix-focused.log`、`ATR-fileless-current-fix-full-regression.log`。
- 本地 Odoo trace `HVR-odoo-8091.log` 也不随 Git 推送；HVR 报告保留脱敏后的调用、版本、状态和 SHA 结果。
- 真实 Provider 摘要：`evidence/CB-M2-CB-09/HVR-provider-calls.json`
- HVR 记录见 [HVR-M2-CB-09.md](HVR-M2-CB-09.md)。

## Odoo 18 CE 集成测试补充（2026-11-11）

| 测试层 | 执行 | 结果 | 证据 |
|---|---|---|---|
| CC-09 focused TransactionCase | `TestEditOrchestration.test_fileless_current_is_used_as_parent_for_next_edit`，并升级 `office_engine_m2` | **1 test, 0 failed, 0 errors** | [ATR-fileless-current-fix-focused.log](evidence/CB-M2-CB-09/ATR-fileless-current-fix-focused.log) |
| Odoo 完整回归及模块升级 | `-u office_engine_m2,office_engine_odoo --test-enable --test-tags /office_engine_m2,/office_engine_odoo --stop-after-init` | **240 tests, 0 failed, 0 errors**；模块升级完成 | 本地原始日志 `ATR-fileless-current-fix-full-regression.log` |
| M1 / Odoo 功能兼容范围 | 同一完整回归包含 `office_engine_m2` 与 `office_engine_odoo`，其中包含既有 Mapping、动态行、附件/RPC 等回归 | **上述 240 项全通过** | 同上 |
| 真实 Responses + Hosted Code Interpreter | 同 Thread 两个真实 Provider 请求：fileless `create`、Current 上的 `edit` | **PASS**；Provider 清理状态均为 `completed` | [HVR-provider-calls.json](evidence/CB-M2-CB-09/HVR-provider-calls.json) |
| Odoo UI/Agent/office/Accept/Finalize | Thread 19720；Candidate 3282 由 Agent 受控 Accept；Finalize 经 `office` 完成 | **PASS** | [HVR-M2-CB-09.md](HVR-M2-CB-09.md)；服务 trace 本地保留 |
| 附件下载和 XLSX 独立回读 | UI 下载控件对应的 `/web/content/49337?...download=true` 返回 HTTP 200；同一附件原始字节回读 | **PASS**；ZIP、openpyxl 内容及 SHA 断言通过 | `CC09_Synthetic_Final_V2.xlsx`；服务 trace 本地保留 |

### 本轮异常/统计说明

- 完整回归日志包含一条 `duplicate key ... office_document_request_request_uuid_unique`，属于唯一约束负向用例路径；Odoo 最终汇总为 0 failed、0 errors，测试执行清单 240 条。
- `tests.stats` 报 `office_engine_m2: 258`、`office_engine_odoo: 28`，合计 286，与 240 条 `Starting Test` 及最终 `tests.result` 不一致。统计差异原因未证实，作为未解释的计数口径观察项保留；验收数以实际启动条目和最终结果共同记录，不虚构 286 tests passed。
- Odoo 测试进程在完整汇总后记录子进程清理警告；日志显示测试汇总已经完成，之后该测试命令会话通过 Ctrl-C 收尾。该运行环境警告没有造成测试失败。
- 初始 UI 新 Thread 未选中 `office` Tool，Agent 首次回复无文件工具。通过 Thread 现有 Tool 选择器启用已有 `office` 后，在同一 Thread 重发请求并完成实际调用；未新增工具或改代码处理 Tool 可见性。

## 无源工作簿工具激活回归及产品 HVR（2026-11-11）

| 层级 | 执行 | 结果 | 证据 |
|---|---|---|---|
| Odoo TransactionCase | `TestNativeOfficeChatIntegration.test_fileless_xlsx_request_binds_route_b_tools_for_create_and_followup_turns` 与 `TestEditOrchestration.test_fileless_current_is_used_as_parent_for_next_edit`，数据库 `odoo18ce` | **2 tests, 0 failed, 0 errors** | `evidence/CB-M2-CB-09/ATR-fileless-tool-binding-and-current-20261111-rerun.log` |
| 真实 Odoo UI / Agent Tool Loop | Thread 19915；Retriever 查询 5 条 `product.template`，再调用现有 `office(action="create")` | **PASS** | `HVR-M2-CB-09.md` 补充段及 `evidence/CB-M2-CB-09/HVR-products-discuss-20261111.md` |
| 真实 Responses + Hosted Code Interpreter | Response `resp_058f906fb0cb7b64016af46c7278bc87d2a362ec2acd13174c`；创建请求 12,448 tokens，42.778s；清理完成 | **PASS** | `evidence/CB-M2-CB-09/HVR-products-readback-20261111.json` |
| Discuss 附件下载 / XLSX 独立回读 | 附件 49900 经 UI 下载到本地；ZIP 和 openpyxl 读取通过，5 行逐字段匹配 Retriever | **PASS** | 同上；下载文件保留在本地，不随 Git 推送发布 |

首次无提权的本地测试命令被 sandbox 拒绝连接 PostgreSQL，尚未开始测试；在已授权环境中重跑后得到上表结果。重跑未做模块升级，也未启动第二个持久 Odoo 服务。该运行的 `tests.stats` 报 6、最终 `tests.result` 报 2 项；验收数采用实际启动的两个指定 TransactionCase 和最终结果，不把模块计数 6 当作 6 项通过测试。
