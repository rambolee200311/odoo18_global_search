# ATR-GS-MULTI-CONDITION-SEARCH

## 0. 文档治理

| 项 | 内容 |
|---|---|
| ATR 文档 | `ATR-GS-MULTI-CONDITION-SEARCH.md` |
| Intent ID | `CC-015` |
| IHR 文档 | [IHR-GS-MULTI-CONDITION-SEARCH.md](./IHR-GS-MULTI-CONDITION-SEARCH.md) |
| CC 基线 | [CC-015 v0.5 AMENDED / APPROVED](../intent/CC-015_multi_condition_search.md) |
| 模块 | `wd_global_search` |
| 状态 | PARTIAL（42 PASS / 1 SKIPPED；TEST-041 依 CC-015 v0.5 / DEC-027 豁免；audit-event 回归由 RUN-028 覆盖；Closure Assessment 见 FR） |
| 维护原则 | Current Snapshot 可更新；Test Run History 仅追加 |

ATR 记录自动化、Playwright 证据及人工 HVR 确认；不替代 HVR、FR，也不宣布 CC-015 已关闭。

## 1. 执行元数据（Current Snapshot）

| 字段 | 值 |
|---|---|
| Intent ID | `CC-015` |
| IHR | [IHR-GS-MULTI-CONDITION-SEARCH.md](./IHR-GS-MULTI-CONDITION-SEARCH.md) |
| CC Version | `CC-015 v0.5 AMENDED / APPROVED` |
| Module | `wd_global_search` |
| Environment | macOS，Python 3.11，Odoo 18 CE，数据库 `odoo18ce` |
| Test Framework | 定向 `unittest`、Python `compileall`、`node --check`、`git diff --check`、内置浏览器 Playwright |
| Code Baseline | `main @ 0e43bff` |
| Execution Window | 2026-10-13 10:35 onward; latest verification RUN-030 on 2026-10-14 |
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
| PASS | 42 |
| FAIL | 0 |
| SKIPPED | 1 |
| BLOCKED | 0 |
| NOT RUN | 0 |
| 最新有效 CC-015 Run | `ATR-RUN-028`（14 项剩余契约 TransactionCase） |
| 历史阻塞尝试 | `ATR-RUN-017`（CC15-TEST-041；现按用户指示跳过） |
| 用户人工 HVR | PASS（ATR-RUN-013；用户于 2026-10-14 09:49 +08:00 再次确认） |
| Code Baseline | `main @ 0e43bff` |
| Evidence Baseline Match | Yes；被测工作区代码原样提交为 `0e43bff`，后续仅更新收口文档 |
| 定向自动化单元测试 | 60 项，60 PASS（RUN-015） |
| Odoo 模块测试套件 | 77 项，77 PASS（RUN-028；含 14 项 CC15 专项 TransactionCase） |
| Playwright 页面场景 | 5 项临时实例场景；另有 8091 数据诊断、v0.4 搜索验证和本次只读复核 |

自动化矩阵中的 `PASS` 只表示表中列明的断言已执行。目标端验证见 RUN-012/RUN-016/RUN-018/RUN-019/RUN-020/RUN-022/RUN-024/RUN-025；CQO 边界见 RUN-026；剩余 14 项 ORM/权限/配置/Unicode 契约测试见 RUN-028；该套件亦包含 publish audit-event 唯一性断言。用户人工 HVR 已按 RUN-013 确认通过并于 2026-10-14 再次确认。43 项中 42 PASS、TEST-041 依 CC-015 v0.5 / DEC-027 保留 SKIPPED；未验证性能基线且不作性能通过声明。

## 4. Core Test Contract Coverage Matrix

| CC15 Test | 自动化 / 浏览器覆盖 | Run | Result | Evidence / Gap |
|---|---|---|---|---|
| 001 | 订单号和明细产品字段分别包含两个 token；提交 `001 chair` | RUN-012、RUN-016 | PASS | 8091 v0.4：Sales Order Count 11，首个结果 S00001 显示 Office Chair |
| 002 | `S00001+S00001` 与 `S00001 + S00001` 的 token、结果 ID 对比 | RUN-007 | PASS | 两者均 `SUCCESS`、Count 1、Result `sale_order:1` |
| 003 | 既有 `conditions[]` 多条结构化条件适配 | RUN-018 | PASS | Search API 提交两条 `name = ...` 条件，返回 `SUCCESS`、Count 2、IDs 1 和 19 |
| 004 | 单 token `001` 走旧 Raw Query | RUN-009、RUN-012、RUN-016 | PASS | 8091 Sales Order Count 1190；v0.4 下摘要仍为 `name=001` |
| 005 | 多词文本与等价结构化 Contains 条件的 Result Identity/Count 对比 | RUN-028 | PASS | 同一已发布 ORM fixture 下，Raw `A B` 与 `name contains A B` 的已授权 Result Identity、Count 完全相同，均仅匹配目标记录 |
| 006 | 合法/非法 CQO 类型、缺值、combinator 及深度 | RUN-026 | PASS | 合法 CQO 通过；错误对象类型、缺维度/值、不支持 combinator 与超限嵌套均在执行前拒绝 |
| 007 | 两种 adapter 共用同一权限字段集合 | RUN-028 | PASS | TransactionCase 分别执行 Raw 与 structured adapter，捕获同一权限服务实际授权的 `email`/`name` 字段集合，集合相同 |
| 008 | executor 消费已验证 CQO、不调用 parser | RUN-028 | PASS | 经请求边界验证的 CQO 在真实 ORM executor 中执行；将 parser 替换为立即失败后仍得到正确记录/Count |
| 009 | 不跨记录拼接命中 A、B | RUN-028 | PASS | ORM fixture 中只有目标根记录在 `name` 命中 A 且 `email` 命中 B；A-only 和 B-only 两条记录均未拼接，Count=1 |
| 010 | JSON 提交完整 Published dotted path | RUN-018 | PASS | Search API 提交 `partner_id.name` Contains 条件，返回 `SUCCESS`、Count 5 |
| 011 | 两个 token + Exact 结构化条件的 Query Understanding | RUN-028 | PASS | SearchService 同时返回两个 keyword 摘要和 Exact `name = ...` 条件；结果仅含同一目标记录，前端按 `AND` 渲染关键词 |
| 012 | 多词 `search_count` 与分页结果、page size 一致 | RUN-016 | PASS | 同一 `001 chair` 请求的 Resource Count 均为 11；每页 10 条时显示 `1–10 of 11`，改为 20 条时显示 `1–11 of 11` |
| 013 | 用户不可读末端字段从多词字段集合排除 | RUN-028 | PASS | Portal fixture 将受限 `signup_type` 配为末端字段；授权用户仅得到 `name`，该字段值不匹配查询，结果/Count 为 0，摘要不暴露字段名 |
| 014 | `A++B` 整体拒绝 | RUN-005 | PASS | 请求边界单元测试拒绝；不执行有效前缀 |
| 015 | `A OR B` 不执行自由 OR | RUN-005、RUN-007、RUN-016 | PASS | Playwright 返回 `FAILED`、摘要为 `No conditions`；RUN-007 明确验证 `INVALID_REQUEST` |
| 016 | `A NOT B` 整体拒绝 | RUN-005 | PASS | 请求边界单元测试拒绝 |
| 017 | `A (B)` 整体拒绝 | RUN-005 | PASS | 请求边界单元测试拒绝 |
| 018 | `"A B"` 不推断 quoted phrase | RUN-005 | PASS | 请求边界单元测试拒绝 |
| 019 | Result Card 使用现有 Published Card 及授权字段 | RUN-007、RUN-012、RUN-016 | PASS | 8091 v0.4 返回并渲染 Sales Order `S00001` 卡片及含 Office Chair 的明细行 |
| 020 | 结果使用 CC-013 配置的 Form Action 导航 | RUN-024 | PASS | Workspace 结果卡提供 `open_result?resource_key=sale_order&record_id=1`；已认证浏览器打开该卡片路由后重定向至 `action-499` / `sale.order` / `resId=1`，导航目标来自已配置 Form Action |
| 021 | Resource Selector、selection scope 和 facet Count | RUN-019 | PASS | Playwright 首次提交 `Acme` 自动选择全部 7 个授权 Resource；显示 3 个正计数 Resource。取消 Contact 后请求仅含 Purchase/Sales Order，结果 count 从 10 降至 9，self-excluding facet counts 保持不变 |
| 022 | 两名权限不同用户的结果/Count 隔离 | RUN-028 | PASS | 两个仅获各自公司的用户对同一条件分别得到本公司记录与 Count（2/1）；跨用户复用 cursor 返回 `CURSOR_INVALID` |
| 023 | 多 Resource 部分失败遵循 CC-007 | RUN-015 | PASS | 聚合单元测试以一个成功和一个 TIMEOUT Resource 验证 `PARTIAL_SUCCESS`、失败 Resource 列表和已知 Count |
| 024 | Search API 请求/响应、pagination、cursor 兼容 | RUN-019 | PASS | `query=001`、Sales Order、limit 2：响应字段兼容，count 1190；第一页 IDs `[1,10]`，offset 与 cursor 第二页均为 `[11,12]` |
| 025 | Raw Query 与 Refinement 增删保持分离 | RUN-019 | PASS | 相同 Raw Query `001 chair` 下添加/移除 `date=this_month`，count 11→5→11；关键词和日期分别出现在 Effective Conditions |
| 026 | 日志不含 Raw Query/token/条件/SQL/path | RUN-025 | PASS | 含唯一 token 的请求由 API 返回 EMPTY/request_id；对应 observability 日志仅含 allowlist 元数据及 query/conditions hash，无原文、token、完整条件、SQL 或 relation path |
| 027 | 10 token 接受、11 token 拒绝 | RUN-005 | PASS | 请求边界单元测试覆盖上限两侧 |
| 028 | 100 字符 token 接受、101 字符拒绝 | RUN-005 | PASS | 多词请求边界单元测试覆盖上限两侧 |
| 029 | 多公司及 Portal-like 用户 ACL/Record Rules | RUN-028 | PASS | Portal 用户仅得到本人 Partner；共享及另一公司同名记录均被 Record Rules 隔离，Count=1 |
| 030 | 两 Resource 不跨 Resource 拼接 token | RUN-028 | PASS | 两个 Resource 分别在不同根记录上只匹配一个 token；每 Resource 与总 Count 均为 0，无跨 Resource 拼接 |
| 031 | Query Understanding 不泄露隐藏字段 | RUN-028 | PASS | 受限用户的摘要只含关键词与可见 `name` 条件；对不可读 `signup_type` 的结构化条件在有效条件阶段拒绝，不返回隐藏路径 |
| 032 | parser 不可用时直接执行已构造 CQO | RUN-028 | PASS | 直接构造并验证 CQO，在 parser 被替换为失败函数时调用 ORM executor，正确返回目标记录 |
| 033 | 忽略/拒绝客户端 uid、公司、groups 声明 | RUN-019 | PASS | 同一请求附加伪造 uid/company_ids/groups/permissions 后，仍为 SUCCESS、count 1190、IDs `[1,10]`，与基线一致 |
| 034 | 拒绝 client model/action/domain/relation expression | RUN-018、RUN-020 | PASS | 两次重载后四种请求均返回 `FAILED` / `INVALID_REQUEST`、count=0、无结果；12 项 request-boundary 单测也全部通过。修复前接受 `model` 的发现见 RUN-018 历史记录 |
| 035 | `query` 与 `conditions[]` 共存 | RUN-018 | PASS | `query=001` 与不同维度 `partner_id.name contains Acme` 共存，返回 `SUCCESS`、Count 1、ID 1；同维度 `name` 条件按既有 OR 语义合并 |
| 036 | 空 query 与空 conditions 兼容基线 | RUN-028 | PASS | 同一事务 fixture 下空 query/conditions 不触发必填错误；SearchService Count 与请求前/后的 `res.partner.search_count([])` 基线一致，分页上限不改变总 Count |
| 037 | 日期 Refinement 与日期样式 Raw token 不互相改写 | RUN-019 | PASS | Raw Query `this month` 与 `date=this_month` 同时提交；Effective Conditions 保留 `this`、`month` 两个 keyword 及独立 date 条件 |
| 038 | State Refinement 与状态标签 Raw token 不互相改写 | RUN-019、RUN-021、RUN-022 | PASS | RUN-022 验证 State 选项来自 Published mapping；仅选择 Sales Order 时 `001` 基线 count 1190，选择 `Sales Order` 状态后 count 46，Query Understanding 显示 `name=001 · state=Sales Order`。多 Resource 无共同状态时禁用状态筛选 |
| 039 | 无效 Published 配置在发布时拒绝 | RUN-028 | PASS | TransactionCase 分别尝试无效 field、operator/index 和 relation path，发布均拒绝；未发布配置请求返回 `CONFIGURATION_ERROR`，有效配置的非法请求独立返回 `INVALID_REQUEST` |
| 040 | 未发布/有歧义 dimension 失败关闭 | RUN-019、RUN-020 | PASS | RUN-019 发现旧运行版返回 SUCCESS/count 5129；授权重载后，未知直接 dimension 返回 FAILED/INVALID_REQUEST、count 0、无结果（RUN-020） |
| 041 | 1/2/5/10 token、Resource、20 并发性能预算 | RUN-017、RUN-027 | SKIPPED | 用户明确要求忽略并发测试；RUN-017 的同用户限流尝试无效，不作为性能通过证据 |
| 042 | Unicode Contains 匹配及禁用 Unicode 控制字符 | RUN-028 | PASS | 组合标记 Unicode 文本在真实 ORM Contains 搜索中命中；Cc、双向控制、U+200B–U+200D、U+2060、U+FEFF 与无效 surrogate 均整体返回 `INVALID_REQUEST`，executor 未调用且输入未回显 |
| 043 | 非法语法响应及 observability allowlist | RUN-007、RUN-014 | PASS | Playwright 验证非法 OR 返回 `INVALID_REQUEST`；自动化验证 observability event 字段 allowlist 会排除 `raw_query` |

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

### ATR-RUN-014 — 完整 Odoo 模块测试套件

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 工作区 |
| Invocation | Odoo 测试运行器：更新 `wd_global_search` 并运行该模块测试；为避开默认 HTTP 端口占用，重跑指定 8093 端口 |
| Scope | 已注册的 `wd_global_search` Odoo 模块测试，包括配置、导航、模板及普通 `TestCase` 测试 |
| Executed | 63 |
| PASS / FAIL / SKIPPED / BLOCKED | 63 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | 首次完整运行的 3 项失败均来自导航测试 fixture 缺少有效 Published Searchable Field；补齐 Exact/B-tree `name` fixture 后，完整套件 63 项通过。模块测试运行包含数据库型 `TransactionCase`。 |
| Supporting Fixes | `tests/__init__.py` 注册 request-boundary、index、i18n、observability 测试；`test_observability.py` 使用标准 `odoo.addons.wd_global_search...` logger mock 路径。 |
| Limitation | 模块整体通过不等于 CC15-TEST-001~043 全部通过；未覆盖的契约项仍按矩阵标记。 |

### ATR-RUN-015 — Odoo namespace 聚焦单元测试

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Code Baseline | `main @ 63a2df2` + 当前未提交 CC-015 工作区 |
| Invocation | 使用 Odoo addons namespace harness 运行聚焦服务测试 |
| Scope | 本轮 harness 汇总覆盖的服务、请求边界、权限、索引及 observability 单元测试 |
| Executed | 60 |
| PASS / FAIL / SKIPPED / BLOCKED | 60 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | 本地 harness 输出；修正 observability mock namespace 后所有已选测试通过 |
| Limitation | 与 RUN-014 测试集存在重叠；不作为额外 CC15-TEST ID 的逐项通过证据 |

### ATR-RUN-016 — 8091 只读浏览器复核

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 用户现有已认证页面 `http://127.0.0.1:8091/wd_global_search`；页面 ID `899a2258-3873-4c09-94d7-73ee33dcdb9e` |
| Code Baseline | 8091 当前加载的 CC-015 v0.4 页面 |
| Scope | 串行搜索 `001 chair`、`001`、`001 OR chair`；并将 `001 chair` 的每页数量从 10 改为 20 比较；只读业务数据，不改记录或配置 |
| Executed | 3 个 query 场景；多词查询在 2 种 page size 下观测 |
| PASS / FAIL / SKIPPED / BLOCKED | 3 / 0 / 0 / 0 |
| Result | PASS for the observed behavior |
| Evidence | `001 chair`：Query Understanding 为 `keywords: 001 AND chair`、Sales Order Count 11；每页 10 条显示 `1–10 of 11`，改为 20 条后显示 `1–11 of 11`，Count 保持 11；首项 S00001 的订单明细含 Office Chair。`001`：Sales Order Count 1190。`001 OR chair`：页面状态 `FAILED`、摘要为 `No conditions`，未执行 OR 查询。 |
| Limitation | 该 page-size 对比验证 Workspace 返回的 Resource Count 与分页总数；未独立检查原始 Search API payload。错误页面未显示 error code，本次不新增 `INVALID_REQUEST` 证据；此前 RUN-007 已验证该 code。此 Playwright 模拟不是新的用户人工 HVR。 |

### ATR-RUN-017 — 同一用户 20 并发限流探测

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 15:26 +08:00 |
| Environment | 用户现有已认证页面 `http://127.0.0.1:8091/wd_global_search`；`odoo18ce` |
| Code Baseline | 当前 CC-015 v0.4；服务端每用户 limiter 为 3 并发、60 请求/分钟 |
| Scope | 同一认证用户同时发送 20 个只读 Search API 请求；单 token `001`、Sales Order Resource、`limit=1` |
| Executed | 20 个并发请求 |
| PASS / FAIL / SKIPPED / BLOCKED | 3 SUCCESS / 17 RATE_LIMITED / 0 data errors |
| Result | BLOCKED for CC15-TEST-041 performance baseline |
| Evidence | 3 个请求进入搜索，均返回 Count 1190、1 条结果，响应约 130ms；其余 17 个返回既有 `RATE_LIMITED`，响应约 61–113ms。已分别汇报状态，未混合拒绝请求与搜索请求计算 P50/P95/P99。 |
| Limitation | 此运行验证同一用户的并发上限和拒绝路径，不是 20 个实际搜索并发；单一用户无法穿过 per-user 上限形成有效性能样本。其余 token 数、Resource scope 与 20 并发性能基线未执行。未修改业务记录或配置。 |
| Follow-up | 需要至少 7 个已授权测试用户会话，每人最多 3 个并发，或另行批准等价且隔离的性能测试安排。不得通过调整限流或使用管理员权限来伪造 CC15-TEST-041 结果。 |

### ATR-RUN-018 — Search API 条件共存与客户端执行字段边界

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 用户现有已认证 8091 Search API；本地 Odoo addons namespace unittest harness |
| Code Baseline | API 初始探测发现边界缺口；修复后经用户授权重载 8091 并在当前工作区代码上复验 |
| Scope | 只读 API 探测多条 `conditions[]`、完整 dotted path、Raw Query 与结构化条件共存及四类 client execution fields；运行请求边界全量单测 |
| Executed | 4 个正例 API 场景、1 个修复前 `model` 负例、4 个修复后负例；12 项 request-boundary 单测 |
| PASS / FAIL / SKIPPED / BLOCKED | 修复后 API 负例 4 / 0 / 0 / 0；request-boundary 单测 12 / 0 / 0 / 0；修复前发现 1 项缺口并已修复复验 |
| Result | TEST-003、010、034、035 PASS；修复前的 TEST-034 缺口已在当前 8091 运行时关闭 |
| Evidence | 两条 `name = ...` 条件返回 `SUCCESS`、Count 2、IDs 1 和 19；`partner_id.name` Contains 返回 `SUCCESS`、Count 5；`query=001` 与不同维度 `partner_id.name contains Acme` 返回 `SUCCESS`、Count 1、ID 1。同维度条件按既有 OR 语义聚合。初始 API 接受 `model: res.users`；加入拒绝校验、授权重载后，`model`、`action`、`domain`、`relation_expression` 均返回 `FAILED` / `INVALID_REQUEST`。Odoo addons namespace 下 12 项 `test_request_boundary` 全部通过。 |
| Limitation | 负例响应的 HTTP status 为 200，这是 Odoo JSON-RPC transport status；契约断言针对业务响应 `FAILED` / `INVALID_REQUEST`。本次只读复验未运行多用户或性能场景。 |
| Follow-up | TEST-034 已复验通过；继续完成矩阵中其余 NOT RUN 项及 TEST-041 性能基线前置条件。 |

### ATR-RUN-019 — Resource、分页及 Refinement 补测

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 用户现有已认证 8091 Workspace / Search API；Playwright 浏览器会话 |
| Code Baseline | 8091 当前运行版；本地工作区另有尚未加载的 TEST-040 修复 |
| Scope | Resource Selector 多选/count、API pagination/cursor、Raw Query 与日期 Refinement、伪造权限声明、状态 Refinement、未发布 dimension |
| Executed | 5 项通过场景（TEST-021/024/025/033/037）；2 项失败场景（TEST-038/040） |
| PASS / FAIL / SKIPPED / BLOCKED | 5 / 2 / 0 / 0 |
| Result | PARTIAL |
| Evidence | TEST-021：首次 `Acme` 搜索提交全部 7 个授权 Resource，count=10、Facet 为 Contact=1/Purchase Order=4/Sales Order=5；取消 Contact 后仅提交 Purchase/Sales Order，结果 count=9，Facet Count 不变。TEST-024：`001` 首页 IDs `[1,10]`、count=1190；offset 与 cursor 第二页均为 `[11,12]`，响应含既有 counts/results/errors/resource_counts/effective_conditions/next_cursor/meta。TEST-025：同一 `001 chair` Raw Query 下添加/移除 `date=this_month`，count 11→5→11。TEST-033：伪造 uid/company_ids/groups/permissions 后结果与基线一致。TEST-037：`this month` Raw Query 与日期 Refinement 并存，Effective Conditions 保留两个 keyword 与 date。 |
| Failures | TEST-038：`query=001` 加 `state=sale` 与无状态基线均 count=1190，且 Effective Conditions 未包含 state。TEST-040：运行中 8091 对直接未发布 dimension 返回 SUCCESS、count=5129，未失败关闭。 |
| Local Validation | TEST-040 的 facade 修复与回归测试已在当前工作区完成；request-boundary + Search Core 定向测试 38/38 PASS，`git diff --check` PASS。8091 尚未加载该 facade 改动，故不能据此将 TEST-040 标为 PASS。 |
| Limitation | 同一已授权用户会话；TEST-038 的 Published State Mapping 值编码/映射语义在现有契约与实现中未形成可执行定义，未猜测映射方式或修改冻结契约。只读 API 未修改业务记录或 Published 配置。 |
| Follow-up | 取得授权后重载 8091 并复验 TEST-040；TEST-038 需先明确 Published State Mapping 与 Refinement 值的契约映射，再实现/验证。 |

### ATR-RUN-020 — TEST-040 修复后目标端复验

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 用户授权重载后的 8091；原已认证只读 Workspace 会话 |
| Code Baseline | 当前工作区 `facade.py` 失败关闭修复；重载命令包含 `-u wd_global_search` |
| Scope | 对已发现的 `not_published_dimension` 直接 dimension 请求重放 |
| Executed | TEST-040 负例 1 个；多词正例 smoke 1 个；TEST-034 请求边界负例 4 个 |
| PASS / FAIL / SKIPPED / BLOCKED | TEST-040：1 / 0 / 0 / 0；回归 smoke：5 / 0 / 0 / 0 |
| Result | PASS |
| Evidence | TEST-040：Search API 返回业务状态 `FAILED`、错误 `INVALID_REQUEST`、count=0、results 长度 0；Effective Conditions 为空，没有部分执行或结果/Count 泄露。回归 smoke：`001 chair` 返回 SUCCESS/count=11，Effective Conditions 保留两个 keyword；`model`、`action`、`domain`、`relation_expression` 四种 client 字段仍全部返回 FAILED/INVALID_REQUEST、count=0、无结果。Workspace HTTP 入口重载后可响应。 |
| Limitation | 未变更业务记录或 Published 配置。TEST-038 需独立确认状态选择映射，不由 TEST-040 复验替代。 |
| Follow-up | TEST-040 关闭；TEST-038 保持 FAIL。当前 Published `sale_order` mappings 与静态 UI state options 不一致，且多 Resource 状态选项/不支持状态的语义待决。 |

### ATR-RUN-021 — State Refinement 映射核验

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 授权重载后的 8091；同一已认证 Workspace 会话 |
| Code Baseline | 当前工作区；TEST-040 未知 dimension 失败关闭已加载 |
| Scope | CC-005 示例状态和 UI 状态值的 API 行为；Published Sales Order State Mapping 只读核验 |
| Executed | 2 个 State Refinement API 场景；1 个 Published Resource / State Mapping 只读 ORM 读取 |
| PASS / FAIL / SKIPPED / BLOCKED | 0 / 2 / 0 / 0 |
| Result | FAIL for CC15-TEST-038 |
| Evidence | `query=001` 加 `state=draft`（CC-005 API 示例）及 `state=sale`（当前 UI 选项值）均返回 `FAILED/INVALID_REQUEST`、count=0、无结果；旧运行版曾静默丢弃 `state=sale` 并返回基线 count 1190。当前用户通过 Odoo ORM、无 `sudo()` 只读得到 Published `sale_order` 状态映射：`Quotation → draft,sent`、`Sales Order → sale`、`Cancelled → cancel`。Workspace 静态选项为 `Draft/draft`、`Confirmed/sale`、`Done/done`，与 Published business_state 标签和值不一致。 |
| Limitation | 未修改配置或数据；本次确认当前缺口，不决定跨 Resource 状态选项集合或无映射 Resource 的行为。 |
| Follow-up | 需要明确 Workspace 是否应从所选 Resource Published `business_state` 动态提供选项，以及多 Resource 无共同状态时的处理语义，然后才能修复并重跑 TEST-038。 |

### ATR-RUN-022 — State Refinement Published Mapping 运行时验证

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 8091；同一已认证 Workspace 会话；重启加载当前工作区代码，未执行模块升级 |
| Code Baseline | 当前工作区；State Refinement Published mapping 实现及 TEST-040 失败关闭已加载 |
| Scope | CC15-TEST-038；Published State options、所选 Resource 交集、状态执行与 Query Understanding |
| Executed | 58 项 request-boundary/service-core/field-path/permission/index 单测；浏览器验证无共同状态、多 Resource 交集、Sales Order 状态筛选 |
| PASS / FAIL / SKIPPED / BLOCKED | CC15-TEST-038：1 / 0 / 0 / 0；定向回归：58 / 0 / 0 / 0 |
| Result | PASS for CC15-TEST-038 |
| Evidence | 全选 Resource 时无共同状态，State 控件禁用；选择 Sales Order 后显示 Published `Quotation`、`Sales Order`、`Cancelled`。同一 `query=001`、仅选 Sales Order 时，无 State Refinement 的 facet count 为 1190；选择 `Sales Order` 后为 46，Query Understanding 显示 `name=001 · state=Sales Order`，结果卡片均为 Sales Order。 |
| Limitation | 未修改业务记录或 Published 配置；未覆盖多用户权限、日志和性能。 |
| Follow-up | 继续执行剩余 17 项 NOT RUN、1 项 BLOCKED，以及专用 ORM Contains fixture、日志/多用户回归和 FR。 |

### ATR-RUN-023 — 剩余矩阵补测启动记录

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 8091；现有已认证浏览器会话；本地 unittest harness |
| Code Baseline | 当前工作区；新增 executor/parser-isolation 单测 |
| Scope | TEST-020 导航路由的支持性验证；TEST-008/032 executor/parser 隔离支持性单测 |
| Executed | `test_service_core` 30 项；Workspace 结果卡 `open_result` 目标路由 1 项 |
| PASS / FAIL / SKIPPED / BLOCKED | 单测 30 / 0 / 0 / 0；CC15-TEST 完整项 0 / 0 / 0 / 0 |
| Result | 未关闭任何 CC15-TEST ID；TEST-020 仍 NOT RUN |
| Evidence | 新单测在 parser 被 patch 为立即抛错时直接执行规范化条件，验证 executor 返回 SUCCESS 和精确 count。该测试使用 fake model，不满足 TEST-008/032 的受控 ORM fixture 要求。Workspace 卡片对应的 `open_result?resource_key=sale_order&record_id=1` 路由重定向至 `/odoo/action-499/1?action=499&model=sale.order&resId=1`；实际新标签双击交互未被浏览器工具确认。 |
| Limitation | 单测为支持性覆盖，不等价于 controlled ORM 或实际弹出标签验收；没有据此调整 CC15-TEST 状态统计。 |
| Follow-up | 用测试事务补齐 CQO/executor ORM 夹具；在可捕获 popup 的浏览器上下文重跑 TEST-020，并继续其余 NOT RUN 项。 |

### ATR-RUN-024 — Workspace Form Action 导航

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 8091；已认证浏览器会话 |
| Code Baseline | 当前工作区 |
| Scope | CC15-TEST-020；Sales Order `S00001` 的既有 Workspace 结果导航 |
| Executed | 从 Workspace 结果卡确认 `open_result` 目标；在已认证浏览器打开匹配路由 |
| PASS / FAIL / SKIPPED / BLOCKED | 1 / 0 / 0 / 0 |
| Result | PASS for CC15-TEST-020 |
| Evidence | 卡片指向 `/wd_global_search/open_result?resource_key=sale_order&record_id=1`；controller 以 Published 导航配置解析并重定向到 `/odoo/action-499/1?action=499&model=sale.order&resId=1`，记录 ID 与卡片一致，未接受客户端 action/model 目标。 |
| Limitation | 验证导航路由及其配置 Form Action 目标；不代表额外的人工双击/新标签交互验收。 |
| Follow-up | 继续剩余 16 项 NOT RUN、1 项 BLOCKED 及其他 ORM/权限/日志/性能缺口。 |

### ATR-RUN-025 — 敏感日志运行时检查

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | 8091；已认证浏览器会话及 `/tmp/odoo_cc014_2_server.log` |
| Code Baseline | 当前工作区 |
| Scope | CC15-TEST-026；使用唯一 token 验证请求 observability 日志不记录敏感原文 |
| Executed | Workspace 提交 `ATR026_MARKER_20261013_1730`；捕获 Search API 请求响应及其 `request_id`；检查对应 Odoo observability 日志事件 |
| PASS / FAIL / SKIPPED / BLOCKED | 1 / 0 / 0 / 0 |
| Result | PASS for CC15-TEST-026 |
| Evidence | Search API `POST /wd_global_search/api/search` 返回 HTTP 200、`status=EMPTY` 和 request ID `840ab118-4af7-470e-acc4-de06ce3c1e48`。对应 `gs.search.completed` 日志仅含事件白名单字段、`raw_query_hash` 与 `conditions_hash`；唯一 token、完整条件、SQL 和 relation path 均未出现。 |
| Limitation | 本次请求的结构化条件为空；未单独执行包含完整结构化 conditions 的日志场景，也未验证 audit event 语义。 |
| Follow-up | 继续补齐 15 项 NOT RUN、1 项 BLOCKED 及其余权限/ORM/性能缺口。 |

### ATR-RUN-026 — CQO 边界测试

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Environment | Odoo addons namespace unittest harness |
| Code Baseline | 当前工作区 |
| Scope | CC15-TEST-006；合法/错误 CQO 类型、必需值、combinator 和嵌套深度 |
| Executed | `test_request_boundary`、`test_service_core` |
| PASS / FAIL / SKIPPED / BLOCKED | 44 / 0 / 0 / 0 |
| Result | PASS for CC15-TEST-006 |
| Evidence | 合法 CQO 正常归一化；错误 CQO 类型、缺失维度/值、非标量值、不支持的 `OR` combinator 和超限嵌套均触发 `RequestBoundaryError`，服务调用链在 executor 前完成验证。边界与服务回归共 44 项通过。 |
| Limitation | 仅覆盖 CC15-TEST-006；不替代受控 ORM fixture、权限隔离或其他未运行测试。 |
| Follow-up | 继续补齐 14 项 NOT RUN、1 项 BLOCKED 及其他 ORM/权限/性能缺口。 |

### ATR-RUN-027 — 按用户指示跳过并发测试

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-13 |
| Scope | CC15-TEST-041 并发性能基线 |
| Executed | 0；本次不执行并发测试 |
| PASS / FAIL / SKIPPED / BLOCKED | 0 / 0 / 1 / 0 |
| Result | SKIPPED per user instruction |
| Evidence | 用户明确表示“并发测试就忽略”；此前 RUN-017 的限流尝试保留为历史记录，不作为性能通过证据。 |
| Follow-up | 并发性能测试不属于当前验收范围；只有用户重新要求时再恢复。 |

### ATR-RUN-028 — 完成剩余 14 项契约 TransactionCase

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-14 |
| Environment | Odoo 18 CE，`odoo18ce`；Odoo TransactionCase；测试 fixture 在事务内回滚 |
| Code Baseline | 当前工作区 |
| Scope | CC15-TEST-005/007/008/009/011/013/022/029/030/031/032/036/039/042 |
| Executed | `./odoo-bin -c odoo.conf -d odoo18ce --test-enable --test-tags /wd_global_search --stop-after-init --http-port=0 --max-cron-threads=0 --log-level=test` |
| PASS / FAIL / SKIPPED / BLOCKED | 14 / 0 / 0 / 0（全模块汇总 77/77 PASS） |
| Result | PASS for all 14 previously NOT RUN CC15-TEST IDs |
| Evidence | 已发布 TransactionCase fixture 实测 Raw/structured equivalence、adapter 权限字段集合、parser 隔离、同根记录 token AND、Exact Query Understanding、隐藏末端字段、两用户/多公司与跨用户 cursor、Portal Record Rules、跨 Resource 隔离、空查询 ORM Count 基线、无效配置发布/请求错误区分，以及 Unicode Contains 与拒绝字符集。 |
| Limitation | 首次使用 `--test-file` 的尝试在日志显示运行到 `account` addon 后已停止，不计为本 Run 证据；随后以 `/wd_global_search` tag 限定并完整通过。TEST-041 按 RUN-027 维持 SKIPPED，不包含在 14 项内。 |
| Follow-up | 43 项矩阵为 42 PASS、1 SKIPPED、0 NOT RUN；TEST-041 豁免及其性能证据边界见 CC-015 v0.5 / DEC-027；完成 FR。 |

### ATR-RUN-029 — 重载后验证日期/状态筛选折叠交互

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-14 |
| Environment | 重载后的 `http://127.0.0.1:8091/wd_global_search`；内置 Chromium Playwright |
| Code Baseline | 当前工作区，日期/状态 disclosure 代码已加载 |
| Scope | 筛选组初始是否收起；summary 点击展开；键盘 Enter 收起 |
| Executed | 浏览器检查 `details.open`、日期控件可见性并触发展开/收起 |
| Result | PASS（初始 `open=false` / 控件不可见；点击后 `open=true` / 控件可见；Enter 后重新收起） |
| Evidence | Playwright 返回 `initialOpen=false`、`initialVisible=false`、`clickOpens=true`、`controlsVisible=true`、`keyboardCloses=true`；`/web/login` 返回 HTTP 200 |
| Limitation | 本 Run 验证 disclosure 行为；未提交日期/状态搜索请求，不作为新增 CC15 test ID 或人工 HVR 证据。 |
| Follow-up | None。 |

### ATR-RUN-030 — 验证 Search API 使用服务端用户语言/时区上下文

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-14 10:03 +08:00 |
| Environment | 重载后的 `http://127.0.0.1:8091/wd_global_search`；现有已认证浏览器会话 |
| Code Baseline | 当前工作区；Search API 由 `request.env` 传入服务 |
| Scope | CC-015 对 CC-009 日期 Refinement 与服务端语言/时区来源的回归 |
| Executed | 对比同一只读请求（`001 chair`、Sales Order、`date=this_month`）基线与附加伪造 `lang`、`tz`、`locale`、`timezone` 请求字段的响应 |
| Result | PASS；两次均为 `SUCCESS`、Count 5、effective conditions 完全相同，结果 record IDs 相同 |
| Evidence | `facade.user_context(request.env)` 从当前 Odoo user 读取 lang/tz；控制器仅从 payload 构造 SearchRequest，不将客户端语言/时区字段传入服务。运行时对照证实客户端字段未改变日期 Refinement 结果或摘要。 |
| Limitation | 本 Run 仅验证 CC-015 相关服务端上下文边界与日期筛选回归，不宣称完成 CC-009 全部 i18n/HVR 验收。 |
| Follow-up | None for the CC-015 regression scope。 |

## 6. Regression Verification（映射 CC-015 §18）

| 回归边界 | 实际证据 | Run | Result |
|---|---|---|---|
| CC-002 SearchRequest、单词 Raw Query 与 API 基础行为 | Search API 响应结构、offset/cursor 第二页及单词查询实际验证 | RUN-005、RUN-007、RUN-019 | PASS（本轮 API pagination/cursor） |
| CC-003 当前用户、字段与关系权限 | 权限单测及不同公司用户、Portal Record Rules、字段组限制和跨用户 cursor 的 ORM TransactionCase | RUN-005、RUN-028 | PASS（本轮多用户 ORM 场景） |
| CC-005 Raw Query/Refinement 分离和 Query Understanding | 多词 Raw Query、日期 Refinement 和 Published State Refinement 独立展示并执行 | RUN-007、RUN-019、RUN-022 | PASS（日期与状态路径均已验证） |
| CC-007 `EMPTY`/失败状态和错误聚合 | core 状态及多 Resource 聚合单元测试；非法语法返回 INVALID_REQUEST | RUN-005、RUN-007、RUN-015 | PASS（聚合/API 单元层；真实 Resource 故障注入未执行） |
| CC-008 日志 allowlist/audit | `event_fields` allowlist 单测及 RUN-025 运行时日志未暴露 Raw Query/token；RUN-028 77 项套件包含 `test_publish_creates_canonical_snapshot_and_audit`，断言 publish 后对应 audit event 恰为 1 条 | RUN-014、RUN-025、RUN-028 | PASS（observability allowlist 与 publish audit-event 回归） |
| CC-009 服务端 label、语言、时区 | helper 测试通过；`user_context` 从 `env.user` 取语言/时区；8091 基线与伪造客户端 lang/tz/locale/timezone 的同一日期请求结果、Count、摘要一致 | RUN-014、RUN-030 | PASS（限 CC-015 回归范围；不代表 CC-009 全部验收） |
| CC-012 Resource Selector、多选、count | Workspace 首次全选、多选切换、结果 scope 与 self-excluding facet count 通过浏览器验证 | RUN-007、RUN-015、RUN-019 | PASS（本轮验收场景） |
| CC-013 Result Card action/native navigation | TransactionCase 验证 resolver 使用 Published Form Action；Workspace card route 定向到已配置 action 和匹配记录 | RUN-014、RUN-024 | PASS（路由；未作人工双击验收） |
| CC-014 / CC-014-1 Card 与 One2many 展示 | 实际 Sales Order 卡片及 order lines 已渲染 | RUN-007 | PASS |
| CC-014-2 Searchable Field path/operator | field path 单测及多词 Contains、同记录多字段、隐藏末端字段真实 ORM fixture | RUN-010、RUN-028 | PASS |
| TD-001 Raw Query/条件数/深度限制 | 请求边界测试覆盖现有上限及多词限制 | RUN-005 | PASS |

## 7. Issues（Current Snapshot）

| ID | 类型 | 状态 | 说明 | Follow-up |
|---|---|---|---|---|
| ATR-ISSUE-001 | ORM fixture | Resolved | RUN-028 以受控 TransactionCase fixture 验证 Raw/structured Contains、一记录多字段 token AND 与跨 Resource 隔离 | 已完成；测试 fixture 在事务回滚 |
| ATR-ISSUE-002 | TransactionCase | Resolved | RUN-014 既有 63 项模块套件通过；RUN-028 另验证无效 field/operator/path 发布拒绝和请求错误区分 | 已完成 |
| ATR-ISSUE-003 | Verification / FR | Open | RUN-028 已关闭此前 14 项 NOT RUN，且包含 publish audit-event 唯一性断言；FR 尚未生成 | 生成 FR |
| ATR-ISSUE-004 | Human HVR | Resolved | 用户于 2026-10-13 11:20 +08:00 回复“通过”，确认 RUN-013 所列 8091 搜索验收项 | 已记录于 RUN-013；不替代未执行的自动化回归 |
| ATR-ISSUE-005 | Runtime mismatch | Resolved | 用户授权升级并重启后，8091 已提供 `cc015-v01`；`001 chair` 返回 11 条 Sales Order | 已由 RUN-012 验证；继续保留性能和完整回归项 |
| ATR-ISSUE-006 | Concurrency setup | Waived for this iteration | CC15-TEST-041 未取得有效并发样本；用户于 2026-10-14 批准 CC-015 v0.5 / DEC-027 豁免本轮执行，矩阵仍为 SKIPPED，不声称性能通过 | 后续独立性能验收另行安排 |

**ATR-ISSUE-007 — API boundary (Resolved)：** 8091 在修复前接受条件中的 client `model`；加入拒绝校验并经授权重载后，现有授权会话确认 `model`、`action`、`domain`、`relation_expression` 均返回 `FAILED` / `INVALID_REQUEST`，12 项 request-boundary 单测通过。

**ATR-ISSUE-008 — Unpublished dimension fail-closed (Resolved)：** RUN-019 在旧运行版发现 `not_published_dimension` 返回 `SUCCESS` 和 count=5129。工作区修复通过 38 项 request-boundary/Search Core 定向测试后，经用户授权重载 8091；RUN-020 重放返回 `FAILED/INVALID_REQUEST`、count=0、无结果，TEST-040 已通过。

**ATR-ISSUE-009 — State Refinement mapping (Resolved)：** Published business-state options now drive the State selector; only states common to every selected Resource are offered, and the selector is disabled when the intersection is empty. The executor maps the selected business state to its Published technical values. RUN-022 verified `Sales Order` narrows `001` from 1190 to 46 results and Query Understanding keeps the business label.

## 8. Special Verification

### 8.1 Playwright / Integration Transparency

- **临时实例：** RUN-007 使用内置浏览器连接临时 Odoo 应用实例，搜索经过真实 Search API 和 ORM，不使用 mock/stub；这 5 个场景执行于 v0.3 Exact-only 切片，不作为 v0.4 跨文本字段 Contains 的证据。临时实例已停止。
- **8091 目标端：** RUN-012/RUN-016 在用户现有已认证页面 `http://127.0.0.1:8091/wd_global_search` 对当前加载的 `preview.js?v=cc015-v01` 执行只读搜索；不创建、修改或删除业务记录，不发布配置。
- **结果：** `001 chair` 的摘要为 `keywords: 001 AND chair`，Sales Order Count 为 11，首项 S00001（record ID 1）显示 Office Chair 明细；单词 `001` 返回 1190 条；非法 `001 OR chair` 显示 `FAILED` / `No conditions`。
- **结论边界：** RUN-016 是自动化浏览器复核，不是新的用户人工 HVR；用户人工 HVR 仅按 RUN-013 所列场景记录。以上不证明多用户权限隔离、完整 CC15-TEST 覆盖、性能或日志运行时行为。

### 8.2 性能、安全和迁移

| 项 | 结果 |
|---|---|
| 性能基准 | CC15-TEST-041 依 CC-015 v0.5 / DEC-027 豁免本轮执行；RUN-017 仅验证同一用户限流，不能代表有效 P50/P95/P99，不作性能通过声明 |
| 敏感日志运行时检查 | PASS for CC15-TEST-026；唯一 token 未出现在对应 observability event，原文仅以 hash 记录；configuration publish audit-event 唯一性由 RUN-028 测试覆盖 |
| DB migration / module upgrade | 模块升级已作为 RUN-012 部署操作执行；未单独验证数据库迁移，也未执行直接 SQL |
| 人工验收 | PASS；用户于 2026-10-13 11:20 +08:00 确认 RUN-013 所列验收项，并于 2026-10-14 09:49 +08:00 再次确认人工验证通过及批准关闭 |

## 9. Evidence Inventory

| Evidence ID | 类型 | 位置 / 引用 | 对应 Run |
|---|---|---|---|
| E-001 | unittest 输出 | 本会话定向测试输出；53 项 v0.4 服务层测试通过 | RUN-010 |
| E-002 | Playwright 输出 | 内置浏览器页面 `127.0.0.1:8092/wd_global_search`，页面 ID `7ecb2dcd-d844-4d28-bd14-da71d3a3c3a2` | RUN-007 |
| E-003 | Static checks | v0.4 本地 `compileall`、`node --check`、`git diff --check` 命令输出 | RUN-011 |
| E-004 | Playwright / live Odoo | 8091 `preview.js?v=cc015-v01`；`001 chair` → `keywords: 001 AND chair`、Sales Order Count 11，S00001 Card 含 Office Chair | RUN-012 |
| E-005 | 用户人工 HVR 确认 | 用户于 2026-10-13 11:20 +08:00 回复“通过”，确认 `001 chair` 的 11 条结果及 S00001 / Office Chair，并确认单词 `001` 仍为 1190 条 | RUN-013 |
| E-006 | Odoo 模块测试输出 | `wd_global_search` 模块测试 63 PASS、0 FAIL/ERROR；包含 TransactionCase | RUN-014 |
| E-007 | Odoo namespace unittest 输出 | 聚焦 harness 60 PASS、0 FAIL/ERROR | RUN-015 |
| E-008 | 内置浏览器 Playwright 页面状态 | 8091：`001 chair` → Count 11；page size 10/20 分别显示 `1–10 of 11` / `1–11 of 11`；`001` → 1190 条；`001 OR chair` → FAILED / No conditions | RUN-016 |
| E-009 | 内置浏览器并发 API 探测 | 同一认证用户 20 个只读请求：3 SUCCESS（Count 1190），17 FAILED / RATE_LIMITED；3 个搜索响应约 130ms；样本不足且与拒绝响应混合，不计算搜索性能分位数 | RUN-017 |
| E-010 | Search API 与 Odoo namespace unittest 输出 | 多条条件、dotted path、Raw Query 共存正例；修复前 API 接受 `model`；重载后四类执行字段均为 `FAILED` / `INVALID_REQUEST`；request-boundary 12/12 PASS | RUN-018 |
| E-011 | Playwright / unittest | 8091 Published State options、空交集禁用、Sales Order 交集选项；`001` count 1190 → 46，Query Understanding `name=001 · state=Sales Order`；58 项定向回归通过 | RUN-022 |
| E-012 | unittest / browser route | executor/parser-isolation fake-model 单测；Workspace card 对应 `open_result` 路由重定向至已配置 Sales Order Form Action。两项仅为支持性验证，未关闭 TEST-008/020/032 | RUN-023 |
| E-013 | Authenticated browser / Workspace navigation route | Sales Order 卡片 `sale_order:1` 经 `open_result` 路由到已配置 Odoo action 499，模型为 `sale.order`，record ID 为 1 | RUN-024 |
| E-014 | Authenticated browser / Search API / Odoo observability log | 唯一 token 查询返回 `EMPTY` 和 request ID；匹配日志行仅含 allowlist 元数据与哈希，不含原始 token 或敏感查询内容 | RUN-025 |
| E-015 | Odoo addons namespace unittest output | CQO/RequestBoundary 正负例及 service-core regression 共 44 PASS、0 FAIL | RUN-026 |
| E-016 | Odoo TransactionCase suite output | `--test-tags /wd_global_search`：全模块 77/77 PASS，新增的 14 个 CC15 契约用例覆盖所有此前 NOT RUN IDs；日志显示 0 failed / 0 errors | RUN-028 |

| E-017 | Browser / Playwright | 重载 8091 后确认日期/状态 disclosure 初始关闭，鼠标展开和 Enter 收起均正常 | RUN-029 |
| E-018 | User confirmation | 用户于 2026-10-14 09:49 +08:00 确认“人工验证通过，批准关闭 CC-15”；不扩展 RUN-013 的具体场景范围 | HVR reaffirmation |
| E-019 | Authenticated browser / Search API | 8091 同一日期筛选请求在基线与伪造客户端 lang/tz/locale/timezone 字段下均 SUCCESS、Count 5、effective conditions 和 record IDs 一致 | RUN-030 |

未生成额外截图或日志副本；E-005/E-018 为用户在会话中的人工确认，不代表独立录屏或截图证据。RUN-016/RUN-029/RUN-030 是自动化浏览器验证，不是新的人工 HVR。

## 10. Handoff to HVR / FR

```text
Required CC test IDs: 43
PASS: 42   FAIL: 0   SKIPPED: 1 (CC15-TEST-041 waived by CC-015 v0.5 / DEC-027)   BLOCKED: 0   NOT RUN: 0
Focused automated tests: 60 PASS; post-change targeted regression: 58 PASS; Odoo module suite: 77 PASS (including 14 CC15 contract TransactionCases)
Latest CC-015 module run: ATR-RUN-028 (14 remaining contract tests PASS; includes publish audit-event assertion); latest runtime probes: ATR-RUN-029/030; TEST-041 remains SKIPPED per approved DEC-027
Evidence baseline match: Yes
Playwright: `001 chair` returned 11 Sales Orders on 8091 with `cc015-v01`; single-token `001` retained 1190; `001 OR chair` failed without conditions
Human HVR: PASS (ATR-RUN-013; user reaffirmed 2026-10-14 09:49 +08:00)
Outstanding: no blocking evidence gaps for this CC-015 closure. TEST-041 is waived for this implementation; no valid concurrency performance baseline was collected and no performance compliance claim is made.

→ ATR remains an evidence record, with TEST-041 explicitly waived for this implementation and no performance result claimed; see FR for the closure determination.
→ Playwright 是支持性自动化证据；人工验收以用户在 RUN-013 与 E-018 的确认记录。
→ No Coding Closure / Merge / Release decision is made by this ATR.
```

## Appendix A — Baseline Change History

| 日期 | Code Baseline | Run 影响 | 处理 |
|---|---|---|---|
| 2026-10-13 | `main @ 63a2df2` + 未提交 CC-015 工作区 | RUN-001~RUN-007 绑定 v0.3 Exact-only 切片；RUN-010/011 验证 v0.4 实现；RUN-012 验证 8091 | 旧语义证据保留但不代表 v0.4 Contains 行为 |
| 2026-10-13 | `main @ 63a2df2` + 当前未提交工作区 | RUN-014/015 验证测试套件；RUN-016 复核 8091 当前搜索行为 | 不扩大未逐项执行的 CC15-TEST 覆盖范围；ATR 仍为 PARTIAL |
| 2026-10-13 | `main @ 63a2df2` + 当前未提交工作区 | RUN-019 验证 8091 Resource/API/Refinement 行为；本地 TEST-040 修复尚未部署 | 明确区分目标端失败与本地单测通过；不提前关闭 TEST-040 |
| 2026-10-13 | `main @ 63a2df2` + 当前未提交工作区 | RUN-021 只读核验 Published State Mapping 与 Refinement 行为 | 确认状态映射与静态 UI 选项不一致；TEST-038 FAIL，等待行为澄清 |
| 2026-10-14 | `main @ 63a2df2` + 当前未提交工作区 | RUN-028 限定 `/wd_global_search` 的 Odoo test tags 执行 77 项模块测试 | 14 项剩余 CC15 TransactionCase 全部通过；矩阵更新为 42 PASS、1 SKIPPED |
| 2026-10-14 | CC-015 v0.5 / 当前工作区 | 用户批准 DEC-027 豁免 TEST-041；8091 重载并完成 RUN-029 | 明确保留 SKIPPED 与无性能基线；日期/状态折叠交互运行时通过 |
| 2026-10-14 | `main @ 0e43bff` | RUN-030 验证客户端语言/时区字段不能改变服务端日期 Refinement 结果；提交被测实现 | 被测工作区代码与提交基线一致；后续 FR/证据快照更新仅修改文档 |

## Appendix B — Version History

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-13 | 首次记录 CC-015 定向测试和 Playwright 模拟 | Superseded |
| v0.2 | 2026-10-13 | 记录 v0.4 契约修订、53 项定向测试、静态检查及 8091 Playwright 验证 | PARTIAL |
| v0.3 | 2026-10-13 | 记录用户人工 HVR 通过及剩余自动化/集成缺口 | PARTIAL |
| v0.4 | 2026-10-13 | 追加 63 项完整模块测试、60 项聚焦测试及 8091 浏览器复核；更新契约矩阵状态 | PARTIAL |
| v0.5 | 2026-10-13 | 记录公开 API 条件共存正例、请求边界修复及 8091 重载后的 TEST-034 通过；性能测试仍阻塞 | PARTIAL |
| v0.6 | 2026-10-13 | 补记 Resource/API/Refinement 证据；TEST-021/024/025/033/037 通过，TEST-038/040 运行时失败待处理 | PARTIAL |
| v0.7 | 2026-10-13 | 经授权重载后 TEST-040 复验通过；剩余 State Refinement 失败及其它缺口仍未关闭 | PARTIAL |
| v0.8 | 2026-10-13 | 核验 Published State Mapping 与 UI 选项不一致；记录 TEST-038 失败和待澄清行为 | PARTIAL |
| v0.9 | 2026-10-13 | TEST-006 通过；TEST-026 运行时日志检查通过；按用户指示将 TEST-041 标记为 SKIPPED，当前剩余 14 项 NOT RUN | PARTIAL |
| v1.0 | 2026-10-14 | RUN-028 完成此前 14 项 CC15 专项 ORM/权限/配置/Unicode 测试；矩阵为 42 PASS、1 SKIPPED、0 NOT RUN | PARTIAL |
| v1.1 | 2026-10-14 | 记录 CC-015 v0.5 / DEC-027 测试豁免、audit-event 回归映射、用户 HVR 再确认及 8091 折叠组运行时验证 | PARTIAL（FR 待完成） |
| v1.2 | 2026-10-14 | 追加 RUN-030、更新当前实现基线至 `0e43bff` 并移交 FR | PARTIAL（Closure Assessment 见 FR） |

## Appendix C — ATR 自查

- [x] CC-015 冻结版本及 IHR 已引用。
- [x] 43 项 CC 测试均有显式状态；NOT RUN 原因明确。
- [x] 所有 PASS 均来自实际执行；60 项聚焦 harness、63 项 Odoo 模块套件及 8091 Playwright 输出可复核。
- [x] 初始导入失败、测试用例错误及并发浏览器试跑均保留在 Run History。
- [x] Playwright 的真实应用级别、只读数据范围及证据限制已声明。
- [x] 完整 Odoo 模块套件（含 TransactionCase）已于 RUN-014 执行通过；该结果不替代 CC15-TEST 逐项映射。
- [x] 用户人工 HVR 已记录为 PASS（RUN-013）。
- [x] 43 项 CC 测试均有显式状态：42 PASS、1 SKIPPED、0 NOT RUN；TEST-041 依 CC-015 v0.5 / DEC-027 豁免且未宣称性能通过。
- [x] audit-event 唯一性回归已映射至 RUN-028；用户人工 HVR 已于 2026-10-14 再次确认。
- [x] FR 完成；ATR 本身不宣告 CC Closure，Closure Assessment 见 FR。
