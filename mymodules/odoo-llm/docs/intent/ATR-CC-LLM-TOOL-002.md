# 自动化测试记录 — CC-LLM-TOOL-002

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `CC-LLM-TOOL-002` |
| IHR | `IHR-CC-LLM-TOOL-002.md` |
| CC 版本 | v1.0.0 Frozen |
| 模块 | `llm_tool`、`llm_openai` |
| 环境 | Odoo 18；现有开发库 `odoo18ce`；端口 8091 |
| 测试框架 | Odoo `--test-enable` / TransactionCase；Codex 内置浏览器 Playwright |
| Odoo / Python / PostgreSQL | `18.0` / `3.11.9` / `16.14` |
| 依赖 | `mcp 2.3.0`、Pydantic `2.13.4`、OpenAI SDK `2.54.0` |
| 代码基线 | 嵌套仓库 HEAD `609ec6dda3645165f6a4a843d7af5d286081a29d` + 未提交工作树；CC-002 源码指纹见 ATR-RUN-003 |
| 执行时间 | 2026-10-16 UTC；最新定向运行结束于 09:05:09 UTC |
| 执行者 | Codex |
| 当前关闭代码基线 | `67baad4a1d3c49b11618d380b8b5bc54ae9abe57`；ATR-RUN-003 源码指纹与该提交中的实现一致，之后未再修改产品代码 |

## 2. 测试契约基线

按冻结 CC §7 执行 `CC-TEST-001`–`CC-TEST-011`；本记录不重定义预期行为。

## 3. 当前自动化测试状态

| 指标 | 值 |
|---|---:|
| Required automated tests | 10（CC-TEST-001–009、011） |
| PASS | 10 |
| FAIL | 0 |
| SKIPPED | 0 |
| BLOCKED | 0 |
| NOT RUN | 0 |
| Latest valid automated run | `ATR-RUN-003` |
| 当前代码基线 | HEAD `609ec6d` + CC 工作树；CC-002 源码指纹 `b4a51b9f6efd3d684fa7b1da2151ddd1fb186626e05630bb1d7bf74fd4c051d8` |
| Evidence baseline match | Yes；运行后源码未再修改 |

## 4. 核心测试覆盖矩阵

| CC 测试 | 当前结果 | 证据 |
|---|---|---|
| CC-TEST-001 | PASS | ATR-RUN-003：动态 Schema 精确匹配 callable，`model` 必填、union 保留 |
| CC-TEST-002 | PASS | ATR-RUN-003：存储 Schema 优先 |
| CC-TEST-003 | PASS | ATR-RUN-003：非法 JSON / 非 object 受控失败；Provider HTTP mock 为零 |
| CC-TEST-004 | PASS | ATR-RUN-003：OpenAI formatter 保留数组、`anyOf` 与源对象 |
| CC-TEST-005 | PASS | ATR-RUN-003：Schema 生成失败时 Provider HTTP mock 为零且错误脱敏 |
| CC-TEST-006 | PASS | ATR-RUN-003：缺少 `model` 在 callable 前被拒绝 |
| CC-TEST-007 | PASS | ATR-RUN-003：可选参数默认值；无销售读取 ACL 用户执行 `sale.order` 被拒绝 |
| CC-TEST-008 | PASS | ATR-RUN-003：无关工具 formatter 回归；实施前后 6 个活动工具名称及存储 Schema 快照相同 |
| CC-TEST-009 | PASS | ATR-RUN-003：stub Provider 参数到达 `execute()` 并通过验证 |
| CC-TEST-011 | PASS | ATR-RUN-003：聊天错误路径仅呈现受控错误，不泄露注入标记 |

`CC-TEST-010` 的真实浏览器 E2E 记于 §8 和 `HVR-CC-LLM-TOOL-002.md`；不计入自动化单元测试数量。

## 5. 测试运行历史（仅追加）

### ATR-RUN-001 — 模块级探索性回归

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-16 08:51 UTC |
| 基线 | HEAD `609ec6d` + CC-OPENAI-001 / CC-002 工作树；当时新测试桩尚未修正 |
| 环境 | `venv`、`odoo.conf`、`odoo18ce` |
| 执行 | `odoo-bin --test-enable --test-tags /llm_tool,/llm_openai --stop-after-init -u llm_tool,llm_openai` |
| 范围 | 两个模块的广泛测试；日志统计 56 项 |
| 结果 | FAIL：0；ERROR：14；整体 FAILED |
| 证据 | `/private/tmp/ATR-CC-LLM-TOOL-002-RUN-001.log` |
| 说明 | 其中 3 项是本 CC 新测试的 MagicMock 签名桩问题，随后修正并在 ATR-RUN-002 / 003 重测通过；其余错误位于既有并发同步测试和既有 MCP 工具定义断言（含 `readOnlyHint` / `inputSchema` API 差异），不在本 CC 修改范围。该失败运行保留，不以定向通过覆盖。 |

### ATR-RUN-002 — CC 定向测试

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-16 08:52 UTC |
| 基线 | HEAD `609ec6d` + CC-002 工作树（MagicMock 测试桩已修正） |
| 执行 | Odoo 定向 `--test-tags`，`-u llm_tool,llm_openai --stop-after-init` |
| 范围 | 13 个指定测试方法，对应 CC-TEST-001–006、008–009、011 的自动化断言 |
| 结果 | PASS：13；FAIL：0；ERROR：0；0.32 秒 |
| 证据 | `/private/tmp/ATR-CC-LLM-TOOL-002-RUN-002.log`；日志结论 `0 failed, 0 error(s) of 13 tests` |
| 后续 | 为显式验证 CC-TEST-007 的当前用户 ACL，新增受限用户拒绝断言；见 ATR-RUN-003。 |

### ATR-RUN-003 — CC 定向测试与 ACL 断言

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-16 09:05:08–09:05:09 UTC |
| 基线 | HEAD `609ec6d` + CC-002 工作树；源码指纹 `b4a51b9f6efd3d684fa7b1da2151ddd1fb186626e05630bb1d7bf74fd4c051d8` |
| 执行 | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --test-enable --test-tags <14 个 CC 定向选择器> --stop-after-init --http-port=0 --gevent-port=0 -u llm_tool,llm_openai --log-level=test --log-handler=odoo.tests:INFO --log-handler=odoo.modules.loading:INFO --logfile=/private/tmp/ATR-CC-LLM-TOOL-002-RUN-003.log` |
| 范围 | 14 个定向测试方法；覆盖 CC-TEST-001–009、011 |
| 结果 | PASS：14；FAIL：0；ERROR：0；0.24 秒；449 queries |
| 证据 | `/private/tmp/ATR-CC-LLM-TOOL-002-RUN-003.log`；日志结论 `0 failed, 0 error(s) of 14 tests` |
| 后续 | 无代码修改；随后以 Odoo UI 升级两个模块并保留现有服务。 |

## 6. 回归验证

| CC-PRESERVE | 验证 | 结果 | 证据 |
|---|---|---|---|
| CC-PRESERVE-001 | 受限内部用户无 `sale.order` 读取 ACL 时，执行 retriever 被 Odoo `AccessError` 拒绝；线上聊天执行使用当前登录用户环境 | PASS | `test_retriever_keeps_current_user_model_access`、内置浏览器 E2E；执行链无新增 `sudo()` |
| CC-PRESERVE-002 | retriever 仍执行只读 `search_read` / `search` + `read`，E2E 未写业务记录 | PASS | 源码复核 + HVR/ATR E2E 观察 |
| CC-PRESERVE-003 | 实施前后 6 个活动工具 ID / 名称 / 存储 Schema 结构比较；OpenAI formatter 回归 | PASS | `evidence/ATR-CC-LLM-TOOL-002-PRE-TOOLS.json`、`...-POST-TOOLS.json`、ATR-RUN-003；比较前按 ID 排序，结果相同 |
| CC-PRESERVE-004 | 缺少必填 `model` 时 callable 未执行 | PASS | `test_execute_missing_required_model_stops_before_callable` |

## 7. 问题与风险

| ID | 类型 | 状态 | 记录 |
|---|---|---|---|
| ATR-ISSUE-001 | TDD 可观测性边界 | Open；对 CC-002 closure 非阻塞 | `llm_tool_record_retriever.py` 的既有实现含 INFO 级参数日志语句。当前 `odoo.conf` 为 error 级，本轮服务器日志未捕获这些 INFO 参数；代码文件 / callable 被冻结 CC §3.2 / §4 明确排除，因此未越界修改。若运行配置启用 INFO，该语句可能记录业务查询参数，与 TDD §15 的日志约束不一致。本 CC 未新增或放宽该日志行为；该遗留风险仍需单独治理，CC-002 关闭不表示其已修复。 |
| ATR-ISSUE-002 | 广泛模块测试 | Open / 非本 CC 定向失败 | ATR-RUN-001 的 56 项模块级运行有 14 errors；定向 CC 测试均在后续 Run 通过。既有并发 / MCP 断言差异仍未修复。 |

运行日志还报告实例已有的若干 `wd_*` 模块缺失 / 模型告警；定向测试日志未出现 CC-002 的失败或异常。旧 Odoo 日志含本次之前的 MCP schema 导入错误，作为历史基线，不视为本次运行错误。

## 8. 专项核验

### CC-OPENAI-001 前置

PASS；`ATR-CC-OPENAI-001.md` ATR-RUN-004：Provider HTTP 200，响应包含目标工具调用，停止于 Odoo 工具分派之前。历史记录保持不变。

### CC-TEST-008 ORM 快照

- 实施前后均通过 `venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce` 只读采集。
- 两次均为 UID 1、6 个活动工具；各记录存储 `input_schema` 都为空。
- 比较相同 ID 的名称、长度、摘要后完全一致；证据分别见 `evidence/ATR-CC-LLM-TOOL-002-PRE-TOOLS.json` 与 `...-POST-TOOLS.json`。
- retriever 的运行时动态 Schema 与 OpenAI formatter 结构摘要一致：object 根、`model` 必填、domain union 保留、`fields` 字符串数组、`limit` 整数且默认值保留；源对象未被修改。
- 模块 `llm_tool` / `llm_openai` 均保持 installed；经 Odoo UI 分别执行 Upgrade 后返回正常应用界面。

### CC-TEST-010 内置浏览器 E2E

PASS。以当前 Odoo 登录用户在 Codex 内置浏览器聊天界面发送中文自然语言销售订单查询；OpenAI 返回 `odoo_record_retriever` 调用，参数含 schema 所需键且类型正确，必填模型与目标模型匹配；Odoo 工具状态显示成功，聊天返回当前用户可读的一条真实订单摘要。没有验证链接渲染；未将完整参数、客户名或订单号复制到证据文件。UI 升级两个模块后再次成功执行。

## 9. 证据清单

| ID | 类型 | 位置 | 用途 |
|---|---|---|---|
| E-001 | 脱敏 ORM 快照 | `evidence/ATR-CC-LLM-TOOL-002-PRE-TOOLS.json` | CC-TEST-008 实施前基线 |
| E-002 | 脱敏 ORM 快照 | `evidence/ATR-CC-LLM-TOOL-002-POST-TOOLS.json` | CC-TEST-008 实施后比较 |
| E-003 | Odoo 自动化测试日志 | `/private/tmp/ATR-CC-LLM-TOOL-002-RUN-001.log` | 保留的模块级失败运行 |
| E-004 | Odoo 自动化测试日志 | `/private/tmp/ATR-CC-LLM-TOOL-002-RUN-002.log` | 首次 CC 定向通过 |
| E-005 | Odoo 自动化测试日志 | `/private/tmp/ATR-CC-LLM-TOOL-002-RUN-003.log` | 含 ACL 断言的最终定向通过 |
| E-006 | 浏览器 E2E 状态交接 | `HVR-CC-LLM-TOOL-002.md` §5 | 说明 Agent Playwright 运行由 ATR 记录，不冒充人工 PASS |

## 10. 交接摘要

CC-TEST-001–009、011 自动化测试均通过；CC-TEST-010 的内置浏览器 E2E 通过，用户随后明确确认人工验收通过；实施前后工具存储 Schema 快照一致。ATR-RUN-001 的广泛模块运行仍保留 14 个既有错误，定向 CC 测试不覆盖这些外部失败。ATR-ISSUE-001 的 INFO 参数日志风险仍未修复，但对应 callable 在冻结 CC 修改白名单之外，本 CC 未新增该行为。CC 关闭判定见 [FR-CC-LLM-TOOL-002.md](FR-CC-LLM-TOOL-002.md)；该 FR 不代表日志风险或广泛模块回归已修复。
