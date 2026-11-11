# ATR-M2-CB-07 — 自动化测试记录

**状态：PARTIAL — TARGETED VALIDATOR PASS; ROUTE B HVR BLOCKED BEFORE CANDIDATE CREATION**
**契约：** `CC-M2-CB-07_Route_B_End-to-End_Integration_v0.2.md`
**记录日期：** 2026-11-10

## 本轮实际执行

| 层级 | 命令 / 项目 | 结果 |
|---|---|---|
| Python 语法 | `venv/bin/python -m py_compile`，覆盖本 CC 涉及的 M2 models/services/tests | PASS，退出码 0 |
| Office Core + Verifier | `PYTHONPATH=mymodules venv/bin/python -m pytest -q mymodules/office_core/tests mymodules/office_verify/tests` | PASS，97 passed，1 warning，退出码 0 |
| 工作区差异格式 | `git diff --check` | PASS，退出码 0 |

逐条命令及原始摘要见 [`evidence/CB-M2-CB-07/LOCAL-VALIDATION.md`](evidence/CB-M2-CB-07/LOCAL-VALIDATION.md)。

## 未运行

| 层级 | 结果 | 说明 |
|---|---|---|
| 新增/修改的 Odoo TransactionCase | NOT RUN | 测试源码存在不等于测试执行；使用 Odoo 数据库运行受 CC 独立 Runtime/数据库门禁约束。 |
| M1 Odoo Mapping / RenderBridge / Document Request / 附件回归 | NOT RUN | 需要 Odoo TransactionCase/Runtime。纯 Office Core 测试不能替代这些回归。 |
| 模块升级 | NOT RUN | 需要独立模块升级/服务操作授权。 |
| 真实 OpenAI Responses + Hosted Code Interpreter | NOT RUN | Provider 外发授权未在本轮取得，真实 dispatch 仍默认关闭。 |
| 真实 UI / Browser HVR、附件下载 | NOT RUN | 不能以 TransactionCase、Mock 或源码检查替代。 |

## 环境修正记录

首次使用系统 `python3` 运行混合 Office Core/Verifier 测试时，收集阶段因缺少 `python-docx` 失败；单独运行 Office Core worker 测试时，子进程在该不完整环境下报通用 `OFFICE_ENGINE_FAILED`。未安装依赖或修改代码以绕过该问题。改用项目 `venv` 后，较窄测试组合 57 项通过，完整 Office Core + Verifier 套件 97 项通过。系统 Python 失败不计为项目 venv 的测试结果，也未删除其工作区痕迹。

## 结论

目前只能报告本地静态检查及共享 Core/Verifier 测试通过。CC-M2-CB-07 的 Odoo 集成、M1 Odoo 回归、真实 Provider 与 UI HVR 尚无执行证据，不能报告 Contract/Integration 全部通过或 Final Accepted。

## 2026-11-11 — Validator 修复验证追加

### 修复范围

`mymodules/office_verify/verify.py` 对 `docProps/core.xml` 实施严格语义比较，仅允许格式有效的 `dcterms:modified` 时间变化；保留 OOXML 安全解析、未知字段/部件、结构及非目标内容检查。失败报告增加首个失败的错误码、阶段、目标/部件、规则和实际变化摘要。没有修改 M1 Mapping 验证路径或放宽 Expected Effect。

### 自动化结果

| 层级 | 实际执行 | 结果 |
|---|---|---|
| Candidate Validator 定向测试 | `PYTHONPATH=mymodules venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py` | PASS：29 passed，1 warning |
| M1 Verifier 冒烟 | `PYTHONPATH=mymodules venv/bin/python -m pytest -q mymodules/office_verify/tests/test_office_verify.py` | PASS：24 passed |
| Python 语法 | `venv/bin/python -m py_compile mymodules/office_verify/verify.py mymodules/office_verify/tests/test_candidate_verify.py` | PASS |
| 差异格式 | `git diff --check` | PASS |
| CB-03 Validator/Expected Effect 历史候选重放 | `ATR-RUN-025-historical-candidate-replay.json` | 2353 保持 FAILED（A2 为空）；2354 现为 VERIFIED（9 个预期单元格效果），无错误 |
| Odoo 初始候选接受单测 | `ATR-RUN-028-odoo-candidate-acceptance.log` | PASS：1 test，0 failures，0 errors；使用 `odoo18ce`，模块测试运行时加载 `office_engine_m2` |
| Odoo `TestEditOrchestration` 类级运行 | `ATR-RUN-024-provider-preservation-instruction.log` 后续追加记录 | FAIL：24 tests，0 failures，1 error；测试辅助器索引不存在的 ZIP 目录项 `docProps/` 时 `KeyError`。保留原始日志，未将该运行记为通过 |

上述最后一次定向运行的原始命令与输出摘要另存于 [`evidence/CB-M2-CB-07/ATR-RUN-029-validator-fix-final.log`](evidence/CB-M2-CB-07/ATR-RUN-029-validator-fix-final.log)。

### 真实 UI HVR 复验

在 `odoo18ce` 的 8092 测试服务、Thread `llm.thread_18271`、OpenAI `gpt-5.6-luna` 上，只提交一次普通用户请求并使用合成 XLSX/合成联系人。Agent 真实调用 Retriever（Tool call `call_wZJ76wkNCxo44yLiQnBnCD6T`）后调用 `office`（Tool call `call_xD5ROm0hh13iGApJDqMycjFA`）。office 返回 `clarification_required` / `expected_effect_invalid`：Expected Effect 提交 `workbook_structure` 范围及 `<uploaded workbook>`、`<contact name cell>` 等占位地址。`operation_executed=false`，没有 Candidate，因此 Responses + Hosted Code Interpreter 编辑、Accept、下载和文件回读均未发生。未追加 Provider 重试。详见 `HVR-RUN-002-ui-failure.json`。

### 验收口径

确认的 `docProps/core.xml` 误拦截已修复并有定向自动化证据；真实 UI 端到端 HVR 因前置 Intent/Expected Effect 不合法而未能到达 Validator/候选生成。不得据此报告 Candidate 2354 在 UI 中被接受，也不得报告 CC-07 HVR、Finalize 或下载 PASS。
