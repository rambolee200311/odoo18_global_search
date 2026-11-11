# ATR-M2-CB-08 — 自动化测试记录

**状态：PASS — CC-08 定向自动化范围**
**契约：** [CC-M2-CB-08 v0.1](CC-M2-CB-08_Integrated_Regression_Release_Readiness_v0.1.md)
**记录日期：** 2026-11-11

## 最终执行结果

| 场景 | 层级 | 实际执行 | 结果 |
|---|---|---|---|
| T1 Provider 文件编辑 | 真实 Provider + Hosted Code Interpreter | 一次真实 Responses API 请求，经现有 Office Edit 路径；返回 Candidate 3107，`PARTIALLY_VERIFIED`；输入/输出 SHA 与 Usage 记录见 Provider JSON | Provider 生成/下载 PASS |
| T1 格式/文件回读 | 独立 openpyxl + ZIP 检查 | USD 两位小数格式生效；非目标样式 ID、工作表名、单元格值、公式保持；输出 SHA 与 Provider 返回字节一致 | PASS |
| T1 Accept | Odoo Candidate/Validator/正式 Accept 服务 | 对真实 Provider 输出字节作零请求回放；Candidate 3109 保留 `PARTIALLY_VERIFIED`；Accept 后 Current=Last Valid=3109、Revision=1、SHA 相同 | PASS（回放层；非真实 UI，Provider 请求数为 0） |
| T2 数据 freshness | Odoo TransactionCase + 测试 Adapter | 更新同一合成联系人后再次 Retriever 查询；新值到达 Office Edit adapter 接缝 | PASS |
| T3 撤权后重读 | Odoo TransactionCase / Record Rule | 二次查询返回空记录；无旧结果、Provider/Candidate/版本指针副作用 | PASS |
| T4 证据基线 | Git/文件 SHA 记录 | HEAD、dirty 状态、关键源码及测试 SHA、DB 名和受信 Provider 开关状态已记录 | PASS |

## 定向 Odoo 测试

测试文件：`mymodules/office_engine_m2/tests/test_cb08_integrated_readiness.py`。

运行方式：项目 Odoo 18 CE 环境对 `odoo18ce` 使用 `--test-file=mymodules/office_engine_m2/tests/test_cb08_integrated_readiness.py`，HTTP 端口设为 0，不接触 8091 服务。原始日志：[`ATR-CC08-T2-T3-focused-final.log`](evidence/CB-M2-CB-08/ATR-CC08-T2-T3-focused-final.log)。

- `Starting Test`：2 项。
- 进程退出码：0。
- 两个测试方法均有实际执行日志；没有测试方法 `FAIL` / `ERROR` 记录。
- `--test-file` 运行未输出最终 `tests.result` 汇总，故只报告“2 项启动、退出码 0”，不补造统计行。
- 测试事务使用合成数据并回滚。

结构化断言与合成记录 ID 见 [`T2-T3-result.json`](evidence/CB-M2-CB-08/T2-T3-result.json)。

本次执行没有做完整模块回归或模块升级：无产品代码改动；CC-07 已有 236/0/0 完整回归及 M1 覆盖按 CC-08 复用。没有重启 8091。

## Provider 与文件证据

- 真实 Provider 结果及原始元数据：[`T1-real-provider-result-attempt-01.json`](evidence/CB-M2-CB-08/T1-real-provider-result-attempt-01.json)
- 原始首轮回读脚本结果（含被修正的过严对象相等断言）：[`T1-real-provider-result.json`](evidence/CB-M2-CB-08/T1-real-provider-result.json)
- 独立校正回读：[`T1-corrected-readback.json`](evidence/CB-M2-CB-08/T1-corrected-readback.json)
- Candidate/接受回放：[`T1-replay-accept-result.json`](evidence/CB-M2-CB-08/T1-replay-accept-result.json)
- 输入、真实 Provider 输出及接受回放输出：`T1-input.xlsx`、`T1-candidate.xlsx`、`T1-accepted-v1.xlsx`
- T1 Provider Usage：11,937 tokens，耗时 45,856 ms。实际账单金额不可核实。

## 失败尝试保留

早期调试日志均保留，未改写：

- `ATR-CC08-T2-T3.log`、`ATR-CC08-T2-T3-rerun.log`、`ATR-CC08-T2-T3-rerun-2.log`：测试最初放在旧 Retriever 测试类时，依次暴露返回形状、测试调用方式和合成上下文准备问题；对应测试随后移至独立文件并修正 fixture/调用方法。
- `ATR-CC08-T2-T3-final.log`：升级式运行与常驻 Odoo 对 `ir_module_module` 的并发更新发生 PostgreSQL 序列化失败；该次不是最终定向测试，未宣称升级成功。
- `ATR-CC08-retriever-module.log`：旧 Retriever 集成模块运行包含既有 CB-05 模拟路径，其模拟首次编辑因缺少 Accepted Current 报错；CC-08 两项也处在当时尚未修正的 harness 形态。最终验收只以独立文件的两项最终执行为准。
- `T1-real-provider-shell.log` / `T1-real-provider-shell-rerun.log` 及 Replay shell 日志：保留 Provider 配置探查、真实 Provider 首轮回读断言以及离线回放调试过程。真实 Provider 总请求数为 1；后续被自动审查拒绝的第二次请求未执行。

当前运行日志还报告三个可选 `wd_*` 模块未安装/不可用；目标模块 Registry 已加载，定向测试启动并退出码为 0。这些可选模块未纳入 CC-08 范围。

最终 Odoo TransactionCase 清理日志记录 `filestore gc 6 checked, 6 removed`。Odoo 18 `TransactionCase._gc_filestore()` 使用测试期间附件操作产生的 filestore checklist，并只删除数据库中没有引用的 checklist 文件；这是本轮合成附件的测试清理。日志还记录测试框架发现并终止一个子进程，服务退出码为 0，但进程清理仍作为环境观察项保留。

额外执行的仓库级 `git diff --check` 被既有修改文件 `evidence/CB-M2-CB-07/HVR-RUN-001-provider-ui-server.log` 中的原始日志尾随空格触发；该历史证据未修改。CC-08 新增/更新文档、测试和脚本已单独检查，无尾随空格。

## Python 语法

T1 Provider runner、输出回放 runner 和 `test_cb08_integrated_readiness.py` 均以项目 Python 3.11.9 `py_compile` 检查。结果 PASS。没有增加生产依赖。
