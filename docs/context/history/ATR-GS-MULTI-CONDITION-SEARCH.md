# ATR-GS-MULTI-CONDITION-SEARCH

## 0. 文档治理

| 项 | 内容 |
|---|---|
| ATR 文档 | `ATR-GS-MULTI-CONDITION-SEARCH.md` |
| Intent ID | `CC-015` |
| IHR 文档 | [IHR-GS-MULTI-CONDITION-SEARCH.md](./IHR-GS-MULTI-CONDITION-SEARCH.md) |
| CC 基线 | [CC-015 v0.4 AMENDED / APPROVED](../intent/CC-015_multi_condition_search.md) |
| 模块 | `wd_global_search` |
| 状态 | PARTIAL；用户人工 HVR 已通过，数据库型及其他回归仍待完成 |
| 维护原则 | Current Snapshot 可更新；Test Run History 仅追加 |

ATR 记录自动化、Playwright 证据及人工 HVR 确认；不替代 HVR、FR，也不宣布 CC-015 已关闭。

## 1. 执行元数据（Current Snapshot）

| 字段 | 值 |
|---|---|
| Intent ID | `CC-015` |
| IHR | [IHR-GS-MULTI-CONDITION-SEARCH.md](./IHR-GS-MULTI-CONDITION-SEARCH.md) |
| CC Version | `CC-015 v0.4 AMENDED / APPROVED` |
| Module | `wd_global_search` |
| Environment | macOS，Python 3.11，Odoo 18 CE，数据库 `odoo18ce` |
| Test Framework | 定向 `unittest`、Python `compileall`、`node --check`、`git diff --check`、内置浏览器 Playwright |
| Code Baseline | `main @ 63a2df2` + 未提交的 CC-015 工作区变更 |
| Execution Window | 2026-10-13 10:35–10:37 +08:00 |
| Executed By | Copilot assistant |

Playwright 使用临时 Odoo 实例 `127.0.0.1:8092` 加载当前工作区代码，通过现有认证浏览器会话执行只读搜索。验证结束后临时实例已停止；未发布配置或修改业务数据。

## 2. Test Contract Baseline

| 来源 | ID | 验证范围 |
|---|---|---|
| CC Test Contract | `CC15-TEST-001~043` | 多词语法、Contains 文本字段、授权、Count、Query Understanding、Search API、错误及性能 |
| CC Regression | CC-015 §18 | CC-002/003/005/007/008/009/012/013/014/014-1/014-2 和 TD-001 |

CC-015 §17、§18 是测试范围的唯一依据；本 ATR 不缩减契约要求。

## 3. Current Automated Test Status

| 指标 | 值 |
|---|---:|
| Required CC Test IDs | 43 |
| PASS | 11 |
| FAIL | 0 |
| SKIPPED | 0 |
| BLOCKED | 0 |
| NOT RUN | 32 |
| 最新有效 CC-015 Run | `ATR-RUN-013` |
| 用户人工 HVR | PASS（ATR-RUN-013；2026-10-13 11:20 +08:00） |
| Code Baseline | `main @ 63a2df2` + 当前未提交工作区 |
| Evidence Baseline Match | Yes |
| 定向自动化单元测试 | 53 项，53 PASS |
| Playwright 页面场景 | 5 项新代码场景；另有 1 项 8091 旧运行版数据诊断 |

自动化矩阵中的 `PASS` 只表示表中列明的断言已执行。目标端验证见 RUN-012；用户人工 HVR 已按 RUN-013 确认通过。数据库型 `TransactionCase`、完整 Odoo 模块套件及真实 Contains 跨字段 ORM fixture 仍未完成。

## 4. Core Test Contract Coverage Matrix

| CC15 Test | 自动化 / 浏览器覆盖 | Run | Result | Evidence / Gap |
|---|---|---|---|---|
| 001 | 订单号和明细产品字段分别包含两个 token；提交 `001 chair` | RUN-012 | PASS | 8091 v0.4：Sales Order Count 11，首个结果 S00001 显示 Office Chair |
| 002 | `S00001+S00001` 与 `S00001 + S00001` 的 token、结果 ID 对比 | RUN-007 | PASS | 两者均 `SUCCESS`、Count 1、Result `sale_order:1` |
| 003 | 既有 `conditions[]` 多条结构化条件适配 | — | NOT RUN | 未通过真实 Search API 单独提交结构化条件 |
| 004 | 单 token `001` 走旧 Raw Query | RUN-009、RUN-012 | PASS | 8091 Sales Order Count 1190；v0.4 下摘要仍为 `name=001` |
| 005 | 多词文本与等价结构化 Contains 条件的 Result Identity/Count 对比 | — | NOT RUN | 尚未用 ORM fixture/API 比较两种入口 |
| 006 | 合法/非法 CQO 类型、缺值、combinator 及深度 | — | NOT RUN | 请求边界与域单元测试不覆盖完整 CQO 负例集 |
| 007 | 两种 adapter 共用同一权限字段集合 | — | NOT RUN | 未执行 adapter 间权限集成对比 |
| 008 | executor 消费已验证 CQO、不调用 parser | — | NOT RUN | 运行时调用链未做 parser 隔离集成测试 |
| 009 | 不跨记录拼接命中 A、B | — | NOT RUN | 尚未用包含/不包含两种根记录的 ORM fixture 验证 |
| 010 | JSON 提交完整 Published dotted path | — | NOT RUN | 字段路径解析有单元测试；本次未从公开 Search API 提交该场景 |
| 011 | 两个 token + Exact 结构化条件的 Query Understanding | — | NOT RUN | token 摘要和结构化域分别覆盖，未验证组合摘要 |
| 012 | 多词 `search_count` 与分页结果、page size 一致 | — | NOT RUN | 浏览器断言 Count 1；未比较完整分页及不同 page size |
| 013 | 用户不可读末端字段从多词字段集合排除 | — | NOT RUN | 未执行专门的多词字段授权 fixture |
| 014 | `A++B` 整体拒绝 | RUN-005 | PASS | 请求边界单元测试拒绝；不执行有效前缀 |
| 015 | `A OR B` 不执行自由 OR | RUN-005、RUN-007 | PASS | Playwright 返回 `FAILED/INVALID_REQUEST`，摘要为 `No conditions` |
| 016 | `A NOT B` 整体拒绝 | RUN-005 | PASS | 请求边界单元测试拒绝 |
| 017 | `A (B)` 整体拒绝 | RUN-005 | PASS | 请求边界单元测试拒绝 |
| 018 | `"A B"` 不推断 quoted phrase | RUN-005 | PASS | 请求边界单元测试拒绝 |
| 019 | Result Card 使用现有 Published Card 及授权字段 | RUN-007、RUN-012 | PASS | 8091 v0.4 返回并渲染 Sales Order `S00001` 卡片及含 Office Chair 的明细行 |
| 020 | 结果使用 CC-013 配置的 Form Action 导航 | — | NOT RUN | 本次未打开结果 |
| 021 | Resource Selector、selection scope 和 facet Count | — | NOT RUN | 页面加载了 Resource tabs；未完成契约级多选/count 对比 |
| 022 | 两名权限不同用户的结果/Count 隔离 | — | NOT RUN | 未切换用户 |
| 023 | 多 Resource 部分失败遵循 CC-007 | — | NOT RUN | 未注入 Resource 故障 |
| 024 | Search API 请求/响应、pagination、cursor 兼容 | — | NOT RUN | 搜索 API 可用；未覆盖完整分页/cursor 契约 |
| 025 | Raw Query 与 Refinement 增删保持分离 | — | NOT RUN | 未操作 Refinement |
| 026 | 日志不含 Raw Query/token/条件/SQL/path | — | NOT RUN | 未检查 observability 日志 |
| 027 | 10 token 接受、11 token 拒绝 | RUN-005 | PASS | 请求边界单元测试覆盖上限两侧 |
| 028 | 100 字符 token 接受、101 字符拒绝 | RUN-005 | PASS | 多词请求边界单元测试覆盖上限两侧 |
| 029 | 多公司及 Portal-like 用户 ACL/Record Rules | — | NOT RUN | 未执行多用户/多公司集成测试 |
| 030 | 两 Resource 不跨 Resource 拼接 token | — | NOT RUN | 未执行跨 Resource fixture |
| 031 | Query Understanding 不泄露隐藏字段 | — | NOT RUN | 单元测试验证不展示搜索路径；未执行隐藏字段授权场景 |
| 032 | parser 不可用时直接执行已构造 CQO | — | NOT RUN | 未执行服务级 parser 隔离测试 |
| 033 | 忽略/拒绝客户端 uid、公司、groups 声明 | — | NOT RUN | 未提交伪造权限上下文请求 |
| 034 | 拒绝 client model/action/domain/relation expression | — | NOT RUN | 本次未执行该 API 负例集 |
| 035 | `query` 与 `conditions[]` 共存 | — | NOT RUN | 单元测试分别覆盖 token 和条件域，未用公开 API 验证共存 |
| 036 | 空 query 与空 conditions 兼容基线 | — | NOT RUN | 曾执行空查询展示，但未做变更前后 fixture 比较 |
| 037 | 日期 Refinement 与日期样式 Raw token 不互相改写 | — | NOT RUN | 未执行日期 Refinement 场景 |
| 038 | State Refinement 与状态标签 Raw token 不互相改写 | — | NOT RUN | 未执行 State Refinement 场景 |
| 039 | 无效 Published 配置在发布时拒绝 | — | NOT RUN | 已增加配置测试，但本次未运行数据库型 `TransactionCase` |
| 040 | 未发布/有歧义 dimension 失败关闭 | — | NOT RUN | 未通过 API 执行该场景 |
| 041 | 1/2/5/10 token、Resource、20 并发性能预算 | — | NOT RUN | 未采集性能基线 |
| 042 | Unicode Contains 匹配及禁用 Unicode 控制字符 | — | NOT RUN | 单元测试覆盖解析/拒绝策略；未验证 ORM Unicode Contains 结果 |
| 043 | 非法语法响应及 observability allowlist | — | NOT RUN | Playwright 验证 `INVALID_REQUEST`/不显示条件；未检查日志 allowlist |

## 5. Test Run History（Append-only）

### ATR-RUN-001 — 初始 unittest 导入方式

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Code Baseline | `main @ 63a2df2` + CC-015 工作区 |
| Invocation | `python -m unittest mymodules.wd_global_search.tests...` |
| Scope | 定向服务测试启动检查 |
| Executed | 0 |
| PASS / FAIL / SKIPPED / BLOCKED | 0 / 0 / 0 / 1 |
| Result | BLOCKED |
| Evidence | Odoo ORM model import 拒绝 `mymodules.*` 顶层命名空间，要求 `odoo.addons.*` |
| Follow-up | 改用 Odoo addons namespace 的 unittest harness |

### ATR-RUN-002 — 测试用例结构修正前

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Invocation | Odoo addons namespace unittest harness |
| Scope | RequestBoundary 与 SearchServiceCore |
| Executed | 33 |
| PASS / FAIL / SKIPPED / BLOCKED | 32 / 1 / 0 / 0（该 1 项为 ERROR） |
| Result | FAIL |
| Evidence | 新增测试的缩进使其引用相邻测试局部变量；不是生产代码结果 |
| Follow-up | 恢复测试方法边界并重跑；本失败记录保留 |

### ATR-RUN-003 — 定向回归

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Invocation | Odoo addons namespace unittest harness |
| Scope | Request boundary、SearchServiceCore、field path、permission boundary |
| Executed | 46 |
| PASS / FAIL / SKIPPED / BLOCKED | 46 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | unittest 输出；之后有测试覆盖补充，非 Latest Valid Run |

### ATR-RUN-004 — 扩展定向回归

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Invocation | Odoo addons namespace unittest harness |
| Scope | 上述测试及 index strategy |
| Executed | 50 |
| PASS / FAIL / SKIPPED / BLOCKED | 50 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | unittest 输出；之后增加 `+` 空格等价断言，非 Latest Valid Run |

### ATR-RUN-005 — 当前定向自动化

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 10:36 +08:00 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 工作区 |
| Invocation | Odoo addons namespace harness，执行 `test_request_boundary`、`test_service_core`、`test_field_path`、`test_permission_boundary`、`test_index_strategy` |
| Scope | Request parsing、CQO/domain、cursor identity、Query Understanding、field path、permission 和 index strategy |
| Executed | 51 |
| PASS / FAIL / SKIPPED / BLOCKED | 51 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | 本地 unittest 输出；存在 Odoo 测试环境未设置语言的非致命翻译告警 |
| Follow-up | 数据库型配置发布测试和完整模块套件仍待执行 |

### ATR-RUN-006 — Playwright 并发交互试跑

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 10:37 +08:00 |
| Environment | 内置浏览器，同一页面 `127.0.0.1:8092` |
| Scope | 同一页面并发填入并提交多个 query |
| Executed | 0 项有效场景 |
| PASS / FAIL / SKIPPED / BLOCKED | 0 / 0 / 0 / 1 |
| Result | BLOCKED |
| Evidence | 同一输入框的并发操作互相覆盖，生成混合 query；该次响应不作为产品测试结论 |
| Follow-up | 改为同一页面串行提交并逐项断言 |

### ATR-RUN-007 — Playwright 串行搜索模拟

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 10:37 +08:00 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 工作区 |
| Environment | 内置浏览器；临时 Odoo 18 实例 `127.0.0.1:8092`；已认证用户；`odoo18ce` |
| Scope | 实际 Workspace → Search API → ORM → Result Card，只读串行查询 |
| Executed | 5 个场景 |
| PASS / FAIL / SKIPPED / BLOCKED | 5 / 0 / 0 / 0 |
| Result | PASS for executed scenarios; overall ATR remains PARTIAL |
| Evidence | 单词 `S00001` → `SUCCESS`, Count 1, `name=S00001`；`S00001+S00001` 与 `S00001 + S00001` 均返回 `sale_order:1`；`S00001 Acme` → `EMPTY`, Count 0, 摘要 `keywords: S00001 AND Acme`；`S00001 OR Acme` → `FAILED/INVALID_REQUEST`, 摘要 `No conditions`。重复 token 场景实际渲染 S00001 Sales Order Card。 |
| Follow-up | v0.3 时的跨 Exact 字段限制由 v0.4 修订消除；真实 ORM fixture 和人工 HVR 仍待完成 |

### ATR-RUN-008 — 最终静态检查

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 10:37 +08:00 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 工作区 |
| Invocation | `python -m compileall -q mymodules/wd_global_search`；`node --check mymodules/wd_global_search/static/src/js/preview.js`；`git diff --check` |
| Scope | Python 语法、前端 JavaScript 语法及工作区差异格式 |
| Executed | 3 checks |
| PASS / FAIL / SKIPPED / BLOCKED | 3 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | 本地命令均 exit code 0 |

### ATR-RUN-009 — 8091 数据可用性诊断（非 CC-015 基线）

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 10:48 +08:00 |
| Environment | 用户现有 `http://127.0.0.1:8091/wd_global_search`，已认证浏览器会话 |
| Scope | 在 8091 依次测试单 token `001`、`chair`，及双 token `001 chair`；Sales Order 单独筛选 |
| Result | PASS for data availability; NOT VALID as new-code CC-015 evidence |
| Evidence | `001`：Sales Order Count 1190；`chair`：Sales Order Count 16，`sale_order:1` 卡片显示明细产品 `Office Chair`；`001 chair`：0 records，Query Understanding 显示 `name=001 chair`，而非 token AND。零计数后 Sales Order tab 被隐藏，页面提示 Select at least one Resource。 |
| Runtime Baseline | Workspace 返回 `preview.js?v=cc013-v07`，不是工作区 `cc015-v01`；页面将双词作为单个旧式条件 `name=001 chair` 处理 |
| Diagnosis | 业务记录存在。当前 8091 运行版未包含 CC-015 多词解析，故尝试匹配包含完整短语 `001 chair` 的字段，无法命中 `001` 的订单号与 `Office Chair` 产品明细分属不同字段的订单。 |
| Contract Limitation | 本次浏览器运行时的 `cc013-v07` 旧代码把双词作为完整条件；它不是 v0.4 代码验证。v0.3 Exact-only 限制已由用户批准在 v0.4 修订。 |
| Follow-up | v0.4 已实现跨文本字段 Contains token AND；8091 仍需经用户授权加载新代码后验证。 |

### ATR-RUN-010 — v0.4 定向服务测试

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 v0.4 工作区 |
| Invocation | Odoo addons namespace unittest harness：`test_request_boundary`、`test_service_core`、`test_field_path`、`test_permission_boundary`、`test_index_strategy` |
| Scope | token Contains 域（含 Exact/Prefix/Contains 配置文本字段）、跨订单号与产品字段 AND、LIKE 元字符字面转义、单 token/权限/path/index 回归 |
| Executed | 53 |
| PASS / FAIL / SKIPPED / BLOCKED | 53 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | 本地 unittest 输出；使用配置加载并初始化 `odoo.addons` 命名空间的只读 Python harness |
| Limitation | 未包含数据库型 `TransactionCase`，未执行真实 ORM 查询或目标 8091 Playwright |

### ATR-RUN-011 — v0.4 静态检查

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 v0.4 工作区 |
| Invocation | `python -m compileall -q mymodules/wd_global_search`；`node --check mymodules/wd_global_search/static/src/js/preview.js`；`git diff --check` |
| Scope | Python 语法、前端 JavaScript 语法及工作区差异格式 |
| Executed | 3 checks |
| PASS / FAIL / SKIPPED / BLOCKED | 3 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | 三条本地命令均 exit code 0 |

### ATR-RUN-012 — 8091 v0.4 搜索验证

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 用户授权重启/升级后的 `http://127.0.0.1:8091/wd_global_search`，`odoo18ce` |
| Code Baseline | CC-015 v0.4 工作区；页面加载 `preview.js?v=cc015-v01` |
| Scope | Sales Order 单独选中，串行搜索 `001` 与 `001 chair` |
| Result | PASS for target behavior and single-token compatibility |
| Evidence | `001`：Sales Order Count 1190，摘要 `name=001`；`001 chair`：摘要 `keywords: 001 AND chair`、Sales Order Count 11、页面显示 `1–10 of 11`。首个结果 `sale_order:1`（S00001）卡片明细含 `Office Chair`。 |
| Data / Configuration | 只读搜索；未改业务记录或 Published 配置。Odoo 模块按用户授权升级并重启。 |
| Limitation | 未执行全量 ORM fixture、全模块回归、性能测试或用户人工 HVR |

### ATR-RUN-013 — 用户人工 HVR 确认

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 11:20 +08:00 |
| Environment | 用户人工检查 `http://127.0.0.1:8091/wd_global_search` |
| Scope | 验收 `001 chair` 的跨字段结果、S00001 明细中的 Office Chair，以及单词 `001` 的兼容结果 |
| Result | PASS（用户确认） |
| Evidence | 用户在收到上述验收步骤后回复“通过”；据此记录指定检查项通过。没有独立截图或录屏 |
| Boundary | 此人工确认不构成数据库型 TransactionCase、完整模块套件、性能、多用户或日志测试的证据 |

## 6. Regression Verification（映射 CC-015 §18）

| 回归边界 | 实际证据 | Run | Result |
|---|---|---|---|
| CC-002 SearchRequest、单词 Raw Query 与 API 基础行为 | 单词 `S00001` 实际搜索；请求边界/条件合并/现有 cursor 单元测试 | RUN-005、RUN-007 | NOT RUN（完整 pagination/cursor/API 组合未覆盖） |
| CC-003 当前用户、字段与关系权限 | `test_permission_boundary` 及服务层定向单元测试 | RUN-005 | PASS（单元层；非多用户集成） |
| CC-005 Raw Query/Refinement 分离和 Query Understanding | 单词、多词摘要实际显示；未操作 Refinement | RUN-007 | NOT RUN |
| CC-007 `EMPTY`/失败状态和错误聚合 | 既有 core 状态测试；非法语法返回 INVALID_REQUEST | RUN-005、RUN-007 | PASS（未注入多 Resource 部分故障） |
| CC-008 日志 allowlist/audit | 未检查日志或 audit event | — | NOT RUN |
| CC-009 服务端 label、语言、时区 | 未执行专项测试 | — | NOT RUN |
| CC-012 Resource Selector、多选、count | Workspace tabs/counts 可见；未完成多选和 facets 对比 | RUN-007 | NOT RUN |
| CC-013 Result Card action/native navigation | 渲染了卡片，未打开记录 | RUN-007 | NOT RUN |
| CC-014 / CC-014-1 Card 与 One2many 展示 | 实际 Sales Order 卡片及 order lines 已渲染 | RUN-007 | PASS |
| CC-014-2 Searchable Field path/operator | field path 与按配置授权的多词 Contains 域单元测试通过 | RUN-010 | PASS（单元层；真实 ORM fixture 待执行） |
| TD-001 Raw Query/条件数/深度限制 | 请求边界测试覆盖现有上限及多词限制 | RUN-005 | PASS |

## 7. Issues（Current Snapshot）

| ID | 类型 | 状态 | 说明 | Follow-up |
|---|---|---|---|---|
| ATR-ISSUE-001 | ORM fixture | Open | v0.4 的 `CC15-TEST-001/005/009` 需验证 Contains 跨字段的实际 ORM 结果 | 在隔离测试数据库执行 fixture；不修改 Published 配置或业务记录 |
| ATR-ISSUE-002 | NOT RUN | Open | `TestGlobalSearchConfiguration` 是数据库型 TransactionCase；8091 部署升级未使用 `--test-enable`，不构成该测试通过证据 | 使用安全隔离测试数据库执行 |
| ATR-ISSUE-003 | NOT RUN | Open | 完整 `wd_global_search` 模块测试、性能预算、日志和 multi-user 回归未执行 | 继续 ATR run 并追加历史 |
| ATR-ISSUE-004 | Human HVR | Resolved | 用户于 2026-10-13 11:20 +08:00 回复“通过”，确认 RUN-013 所列 8091 搜索验收项 | 已记录于 RUN-013；不替代未执行的自动化回归 |
| ATR-ISSUE-005 | Runtime mismatch | Resolved | 用户授权升级并重启后，8091 已提供 `cc015-v01`；`001 chair` 返回 11 条 Sales Order | 已由 RUN-012 验证；继续保留性能和完整回归项 |

## 8. Special Verification

### 8.1 Playwright / Integration Transparency

- **实际运行级别：** Playwright 控制内置浏览器，连接临时 Odoo 应用实例；搜索走真实 Search API 和 ORM，不使用 mock/stub。
- **数据：** 现有只读 Sales Order `S00001`（record ID 1）；不创建、修改或删除数据，不发布配置。
- **页面：** `http://127.0.0.1:8092/wd_global_search`；当前工作区 controller 返回 `preview.js?v=cc015-v01`。
- **结论边界：** 该 5 个场景执行于 v0.3 Exact-only 语义；证明单词兼容、重复 token、分隔符等价、Contains 字段排除及非法 OR 拒绝。v0.4 已反转 Contains 字段排除规则，因此这些结果不验证修订后的跨字段 Contains；也不证明多用户权限隔离、全量模块回归或人工验收。
- **进程：** 临时 Odoo 实例已停止；8091 原服务未升级或重启。

8091 数据诊断见 RUN-009：`001` 在 Sales Order 命中 1190 条；`chair` 命中 16 条，其中 `sale_order:1` 明确显示 `Office Chair`；`001 chair` 无结果且理解摘要为 `name=001 chair`。这是 `cc013-v07` 旧运行版将双词当作完整条件的证据。v0.4 已按用户批准改为跨文本字段 Contains AND，但尚未加载到 8091。

### 8.2 性能、安全和迁移

| 项 | 结果 |
|---|---|
| 性能基准 | NOT RUN；未采集 P50/P95/P99 |
| 敏感日志检查 | NOT RUN；未读取日志，也未执行独特 token allowlist 测试 |
| DB migration / module upgrade | 模块升级已作为 RUN-012 部署操作执行；未单独验证数据库迁移，也未执行直接 SQL |
| 人工验收 | PASS；用户于 2026-10-13 11:20 +08:00 确认 RUN-013 所列验收项通过 |

## 9. Evidence Inventory

| Evidence ID | 类型 | 位置 / 引用 | 对应 Run |
|---|---|---|---|
| E-001 | unittest 输出 | 本会话定向测试输出；53 项 v0.4 服务层测试通过 | RUN-010 |
| E-002 | Playwright 输出 | 内置浏览器页面 `127.0.0.1:8092/wd_global_search`，页面 ID `7ecb2dcd-d844-4d28-bd14-da71d3a3c3a2` | RUN-007 |
| E-003 | Static checks | v0.4 本地 `compileall`、`node --check`、`git diff --check` 命令输出 | RUN-011 |
| E-004 | Playwright / live Odoo | 8091 `preview.js?v=cc015-v01`；`001 chair` → `keywords: 001 AND chair`、Sales Order Count 11，S00001 Card 含 Office Chair | RUN-012 |
| E-005 | 用户人工 HVR 确认 | 用户于 2026-10-13 11:20 +08:00 回复“通过”，确认 `001 chair` 的 11 条结果及 S00001 / Office Chair，并确认单词 `001` 仍为 1190 条 | RUN-013 |

未生成额外截图或日志副本；E-005 为用户在会话中的人工确认，不代表独立录屏或截图证据。

## 10. Handoff to HVR / FR

```text
Required CC test IDs: 43
PASS: 11   FAIL: 0   SKIPPED: 0   BLOCKED: 0   NOT RUN: 32
Focused automated tests: 53 PASS (v0.4 service-level; no TransactionCase)
Latest valid run: ATR-RUN-013
Evidence baseline match: Yes
Playwright: `001 chair` returned 11 Sales Orders on 8091 with `cc015-v01`; single-token `001` retained 1190 Sales Orders
Human HVR: PASS (ATR-RUN-013; user-confirmed 2026-10-13 11:20 +08:00)
Outstanding: Contains cross-field ORM fixture; DB TransactionCase/full module suite; multi-user/log/performance regressions; FR

→ ATR is PARTIAL; HVR passed, while listed automated/integration gaps and FR remain pending.
→ Playwright 是支持性自动化证据；人工验收以用户在 RUN-013 的确认单独记录。
→ No Coding Closure / Merge / Release decision is made by this ATR.
```

## Appendix A — Baseline Change History

| 日期 | Code Baseline | Run 影响 | 处理 |
|---|---|---|---|
| 2026-10-13 | `main @ 63a2df2` + 未提交 CC-015 工作区 | RUN-001~RUN-007 绑定 v0.3 Exact-only 切片；RUN-010/011 验证 v0.4 实现；RUN-012 验证 8091 | 旧语义证据保留但不代表 v0.4 Contains 行为 |

## Appendix B — Version History

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-13 | 首次记录 CC-015 定向测试和 Playwright 模拟 | Superseded |
| v0.2 | 2026-10-13 | 记录 v0.4 契约修订、53 项定向测试、静态检查及 8091 Playwright 验证 | PARTIAL |
| v0.3 | 2026-10-13 | 记录用户人工 HVR 通过及剩余自动化/集成缺口 | PARTIAL |

## Appendix C — ATR 自查

- [x] CC-015 冻结版本及 IHR 已引用。
- [x] 43 项 CC 测试均有显式状态；NOT RUN 原因明确。
- [x] 所有 PASS 均来自实际执行；53 项 v0.4 服务层单元测试及 8091 Playwright 输出可复核。
- [x] 初始导入失败、测试用例错误及并发浏览器试跑均保留在 Run History。
- [x] Playwright 的真实应用级别、只读数据范围及证据限制已声明。
- [ ] 数据库型配置发布测试和完整 Odoo 模块回归仍待执行。
- [x] 用户人工 HVR 已记录为 PASS（RUN-013）。
- [ ] FR、数据库型配置发布测试和完整 Odoo 模块回归仍待完成。
