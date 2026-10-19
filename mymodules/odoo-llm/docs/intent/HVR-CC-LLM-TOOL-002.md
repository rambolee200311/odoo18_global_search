# 人工验证记录 — CC-LLM-TOOL-002

## 1. 当前状态

| 字段 | 值 |
|---|---|
| Intent ID | `CC-LLM-TOOL-002` |
| CC 版本 | v1.0.0 Frozen |
| IHR | `IHR-CC-LLM-TOOL-002.md` |
| ATR | `ATR-CC-LLM-TOOL-002.md` |
| 模块 | `llm_tool`、`llm_openai` |
| 环境 | Odoo 18；`odoo18ce`；端口 8091；Codex 内置浏览器 |
| Human Verification Required | Yes — 用户已明确确认人工验收通过 |
| Required Scenarios | 1 |
| PASS / FAIL / BLOCKED / NOT RUN | 1 / 0 / 0 / 0 |
| Current Code Baseline | `67baad4a1d3c49b11618d380b8b5bc54ae9abe57`；自动化运行源码指纹详见 ATR-RUN-003；人工确认记录于 HVR-RUN-001 |
| Evidence Baseline Status | User-confirmed; detailed interaction transcript not supplied |

## 2. 验证契约基线

| 来源 | ID | 相关性 |
|---|---|---|
| CC | `CC-TEST-010` | 通过 Odoo 聊天读取少量当前用户可访问记录，验证自然语言到 Provider tool call、Odoo 执行和结果返回 |
| CC | `CC-PRESERVE-001`、`CC-PRESERVE-002` | 当前用户权限及只读边界 |

## 3. 场景

| 字段 | 值 |
|---|---|
| Scenario ID | `HVR-SCN-001` |
| Title | Odoo 聊天中的受限记录读取 |
| Purpose | 确认业务用户可以从自然语言发起工具调用，并只看到当前用户可读记录的结果 |
| Preconditions | Odoo 18 已运行；OpenAI provider、`odoo_record_retriever` 工具已配置；用户已有聊天访问权限 |
| Role | 当前 Odoo 登录用户 |
| Steps | 在聊天框输入一条针对当前公司客户的销售订单查询；确认助手调用 retriever、工具完成并给出订单号和状态 |
| Expected | Provider 调用参数符合 schema；Odoo 以当前用户环境执行；工具返回授权数据；不验证链接渲染 |
| Evidence Required | 人类验证者执行 / 观察并确认；敏感业务参数不写入该记录 |

## 4. 验证覆盖

| Verification Requirement | Scenario | 当前有效证据 | 结果 | 基线有效性 |
|---|---|---|---|---|
| CC-TEST-010 人工观察项 | HVR-SCN-001 | 用户在 2026-10-19 明确确认“人工验收通过”；此前 Agent Playwright E2E PASS 见 ATR §8 | PASS（用户确认；不将 Agent 运行冒充人工执行） | CC-002 实施代码基线 |

## 5. Run 历史

### HVR-RUN-001 — 用户确认人工验收

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-19（用户确认日期） |
| 验证者 | lijianqiang（本项目用户；通过当前对话明确确认） |
| 执行方式 | 用户报告人工验收已通过；本记录不声称由 Codex 执行人工步骤 |
| 场景 | HVR-SCN-001：Odoo 聊天中的受限记录读取 |
| 结果 | PASS（基于用户的明确确认“人工验收通过”） |
| 观察细节 | 用户未在本次确认中复述具体输入、页面观察或记录值；不补造业务细节。已有 Agent Playwright 技术观察仍单独记录于 ATR §8。 |
| 证据 | 当前对话中用户的验收确认；无截图或业务数据复制到仓库 |

Codex 此前使用内置浏览器 Playwright 两次执行同一目标旅程，工具调用成功，见 [ATR-CC-LLM-TOOL-002.md](ATR-CC-LLM-TOOL-002.md) §8。该 Agent 证据与本次用户确认分开记录。

## 6. 回归与发现

没有额外人工回归 Run。自动化 ACL 回归见 ATR-RUN-003。技术范围问题 ATR-ISSUE-001 记录在 ATR；其未修复状态保留，不由 HVR 改写。

## 7. 交接

HVR-SCN-001 按用户明确确认记录为 PASS；该确认没有提供可复述的具体交互细节。Agent Playwright E2E 仍只作为 ATR 证据。用户确认足以记录其验收结论，但本记录不声称拥有额外截图、输入文本或业务数据。
