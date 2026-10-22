# ATR — CC-OFFICE-M1-005 Provider 前路由 Spike

## 0. 文档治理

本 ATR 仅记录运行时测试事实，不改变 CC。Mock/Stub 证据只证明本地隔离路径，不代表真实外部 Provider 集成通过。

## 1. Execution Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-PROVIDER-PRE-ROUTE-SPIKE` |
| IHR | [IHR](IHR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) |
| CC Version | `v1.0.0 Frozen`（TDD V0.4） |
| Environment | `odoo18ce`、`odoo.conf`、Odoo 18.0、Python 3.11.9、PostgreSQL 16.14 |
| Test Framework | `odoo-bin shell` 运行时探针；本地 stub/mock，无真实 HTTP |
| Code Baseline | 根仓库 `e91bf5a502b8970bfa9c795335e5ee2dce0e57b7` + Odoo-LLM `609ec6dda3645165f6a4a843d7af5d286081a29d`（clean） |
| Execution Date | 2026-10-21 |
| Executed By | Codex Agent |
| Latest Valid Run | `ATR-RUN-001` |
| Evidence Baseline Match | Yes for Odoo-LLM pinned source; root repo has unrelated pre-existing dirty files |

## 2. Test Contract Baseline

| 来源 | ID | 验证点 |
|---|---|---|
| CC | CC-TEST-001 | 运行时/源码基线一致 |
| CC | CC-TEST-002 | 附件识别先于 Provider dispatch |
| CC | CC-TEST-003 | 已识别 Office 内容不进入 Provider payload |
| CC | CC-TEST-004 | 当前实际启用 Provider、普通聊天、工具请求路径覆盖 |
| CC | CC-TEST-005 | 当前用户与跨用户附件/线程权限 |
| CC | CC-TEST-006 | MIME 不确定/错误及异常安全失败 |
| CC | CC-TEST-007 | 普通文本附件回归 |
| CC | CC-TEST-008 | 独立 Addon 扩展点/受控服务 handoff 可行性 |
| CC | CC-TEST-009 | 证据脱敏与可复现性 |
| CC | CC-TEST-010 | 临时 hook 物理清理及证明 |

## 3. Current Automated Test Status

| 指标 | 值 |
|---|---|
| Required tests | 10 |
| PASS | 7 |
| FAIL | 1 |
| BLOCKED | 2 |
| MISSING | 0 |
| Latest Valid Run | `ATR-RUN-001` (`c23b629f521a`) |
| Current Code Baseline | Odoo-LLM `609ec6dda3645165f6a4a843d7af5d286081a29d` |
| Evidence Baseline Match | Yes |

> 原生状态汇总：7 PASS、1 FAIL、2 BLOCKED、0 MISSING，共 10 项。CC-TEST-008 的原生状态为 BLOCKED；其可行性评估结论另记为 INCONCLUSIVE。

## 4. Core Test Contract Coverage Matrix

| CC Test | Native Result | Workflow Evidence Status | Evidence / 限定 |
|---|---|---|---|
| CC-TEST-001 | PASS | Passed | 目标 DB `odoo18ce`；Odoo 18.0、Python 3.11.9、PostgreSQL 16.14；`llm`、`llm_thread`、`llm_assistant`、`llm_openai` installed；Odoo-LLM clean HEAD `609ec6d…`；运行实例由检查后新进程启动。 |
| CC-TEST-002 | PASS | Passed | 对 `.xlsx/.xls/.docx/.doc` 标准 MIME，instrumented `_check_unsupported_attachments` 在 Provider dispatch 前被调用，拒绝数为 1，Provider mock 调用数为 0。 |
| CC-TEST-003 | PASS（限定） | Passed | 已识别的四类 Office MIME 未进入 Provider mock；独立调用 OpenAI message formatter 生成的结构不含 synthetic Office marker。不是外部网络捕获。 |
| CC-TEST-004 | PASS（当前运行配置） | Passed | 当前仅有一个 active provider service：OpenAI。覆盖 chat、multimodal、tools-enabled mock cycle；tool executor 为 stub。未外推到未安装 Provider。 |
| CC-TEST-005 | BLOCKED | Blocked | 用户 uid 6（owner）与 uid 103（attacker）均 `su=False`；攻击方按 ID 搜索线程/附件均为 0，调用产生 `UserError`，Provider 调用增量为 0。跨用户拒绝通过；向 `office_engine_odoo` 服务交付授权引用不可测试，因为当前没有路由服务。 |
| CC-TEST-006 | FAIL | Failed | `.xlsx` 文件名配纯文本 synthetic 内容，在 Odoo message attachment 链接后 MIME 为 `text/plain`；附件预检拒绝数 0，Provider mock 被调用 1 次，format payload 含合成文本 sentinel。未请求外部网络。命中 CC “身份不一致必须 fail closed” 门禁。 |
| CC-TEST-007 | PASS | Passed | 普通 `text/plain` 附件正确进入 mock payload；无 Office sentinel；普通文本未被错误拦截。 |
| CC-TEST-008 | BLOCKED（可行性结论 INCONCLUSIVE） | Blocked | 当前标准拒绝扩展点可观察，但本 CC 禁止新 Addon/模块安装及产品代码；未验证独立 Addon handoff 到受控 Office 服务，也未证明全部扩展路径。 |
| CC-TEST-009 | PASS | Passed | 最终证据仅含状态、计数、MIME、uid、运行基线；无 API key、Office 原文、Base64 或原始 payload。Mock/Stub 明确标识。 |
| CC-TEST-010 | PASS | Passed | shell 退出后 patch 不持久；临时探针/日志已删除；嵌套 Odoo-LLM `git status --porcelain --untracked-files=all` 为空；hook 标记扫描无命中；见 cleanup-proof。 |

## 5. Test Run History（Append-only）

### ATR-RUN-001

| 字段 | 值 |
|---|---|
| Timestamp | 2026-10-21 |
| Run ID | `c23b629f521a` |
| Code Baseline | Odoo-LLM `609ec6dda3645165f6a4a843d7af5d286081a29d`，clean |
| Environment | Odoo 18.0 / Python 3.11.9 / PostgreSQL 16.14 / `odoo18ce` |
| Invocation | `venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce --no-http < /tmp/cc005_runtime_probe.py` |
| Scope | Integration-style in-process probe; synthetic attachments, OpenAI provider stub, tool executor stub |
| Executed | 10 contract items |
| Result | **FAIL**；原生状态为 7 PASS、1 FAIL、2 BLOCKED、0 MISSING；CC-TEST-008 可行性评估为 INCONCLUSIVE |
| Evidence | `evidence/ATR-RUN-001-provider-route.json`、`evidence/environment-snapshot.json` |
| Follow-up | CC-TEST-006 失败阻塞 CC-006；CC-004 FR 仍 NOT SATISFIED。 |

前置 harness 曾因所选用户没有 sender email 而在 `message_post` 前停止；未执行目标断言。本正式 Run 改用已有普通用户 uid 6（未修改用户资料），并完整 ORM 清理。该前置失败不计入最终 Run 测试数。

## 6. Regression Verification

| CC-PRESERVE / 行为 | 结果 | Evidence |
|---|---|---|
| 普通文本附件的现有 OpenAI chat 处理 | PASS | CC-TEST-007：合成 `text/plain` sentinel 进入 mock 文本 payload |
| 工具调用框架路径 | PASS（mock） | CC-TEST-004：mock Provider 返回 tool call；stub executor 产生 synthetic tool result；第二次 Provider mock 收到继续消息 |
| Office 标准 MIME 安全拒绝 | PASS（限已识别 MIME） | CC-TEST-002/003：四种 MIME 均拒绝且 Provider mock 零调用 |
| MIME/扩展名不一致失败关闭 | FAIL | CC-TEST-006；当前行为继续 mock dispatch |

## 7. Issues

| ID | Test | 类型 | 原因 | Status | Follow-up |
|---|---|---|---|---|---|
| ISSUE-005-01 | CC-TEST-006 | FAIL / security boundary | Office-looking extension + text/plain detected MIME 未拒绝，文本被 mock Provider 接收 | Open | 需单独设计/授权修复；不得在本 Spike 修改上游/产品代码 |
| ISSUE-005-02 | CC-TEST-005/008 | BLOCKED / INCONCLUSIVE | 尚无内部路由服务或独立聊天 Addon handoff | Open | CC-004 gap 与独立路由契约解决后再建立后续 CC |

## 8. Special Verification

### 8.1 Security

测试执行环境内 Provider 是 monkey-patched OpenAI method；未创建任何真实 HTTP client 请求。发现的文本 sentinel 只被本地 mock 捕获。无真实外部 Provider 调用或业务数据访问。

### 8.2 Integration / Mock Transparency

| 层级 | 使用方式 | 证据含义 |
|---|---|---|
| Odoo Runtime | 真实 Odoo 18 ORM、真实 `llm.thread.generate`、真实 ACL/Record Rules | 证明本机当前运行代码路径 |
| Provider | 进程内 OpenAI `openai_chat` stub | 观察 Provider dispatch / formatter；不代表外部 API |
| Tool executor | 进程内 stub，不运行真实工具 | 证明消息循环，不证明任何业务工具行为 |
| Browser / external API | 未执行 | N/A / 不作结论 |

## 9. Evidence Inventory

| Evidence | 内容 |
|---|---|
| `evidence/ATR-RUN-001-provider-route.json` | 脱敏最终测试结果 |
| `evidence/environment-snapshot.json` | Odoo/DB/Addon/Provider 基线 |
| `evidence/cleanup-proof.txt` | 临时文件删除、嵌套 repo clean、产品目录扫描 |
| Odoo service log | `/tmp/office_m1_cc005_odoo.log`，仅作为本机运行日志，保留用于运行实例；不含测试 payload |

## 10. Handoff to HVR / FR

- Human Verification Required = No（来源：CC-005）；HVR N/A，不代表 PASS。
- FR 应按实际 evidence 判定 NOT SATISFIED；本 ATR 有一个明确 FAIL 和两个未闭环项。
- 本次没有产品代码变化，自动化证据绑定 Odoo-LLM commit `609ec6d…` 与根仓库 HEAD `e91bf5a…` 的运行时。
