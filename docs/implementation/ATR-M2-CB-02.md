# ATR — CC-M2-CB-02 Workbook Version & Artifact Service

## 0. 文档治理

- 状态：**FINAL ACCEPTED — CC-M2-CB-02 技术范围**（负责人 2026-11-08 明确决定）；生产附件留存/删除 `Release Gate OPEN`，browser-backed RPC 仍为 SKIP/未验证。
- CC：[CC-M2-CB-02 v0.3](CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md)，原文保留；[v0.3.1 并发修订](CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md)，负责人批准。
- IHR：[IHR-M2-CB-02](IHR-M2-CB-02.md)
- 上游：TDD V2.0.2、Implementation Plan V2.0.1。
- 数据范围：仅合成测试数据；不调用 Provider、不处理真实业务附件。
- 起始代码基线：`f9801fca76f7c248a9cc823c583138ab0191b978`，branch `main`。

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| 模块 | `office_engine_m2`, `office_engine_odoo` |
| 环境 | Python 3.11.9；Odoo 18.0；配置 DB `odoo18ce`；HTTP 8091 |
| 测试框架 | Odoo `TransactionCase`；Odoo Registry/ORM 双独立连接并发 runner（真实运行） |
| Latest Code Baseline | `f9801fca76f7c248a9cc823c583138ab0191b978`（实施前基线；工作区未提交） |
| 执行状态 | Odoo 模块升级、两模块完整 TransactionCase、M1/附件回归及获批环境下真实双连接并发均已运行 |

## 2. 测试契约基线

| 来源 | 验证点 |
|---|---|
| CC §4–§5 | 版本字段、typed validation receipt、proof 绑定、版本状态/current/last-valid |
| CC §6–§8 | Odoo 服务入口、ACL/Record Rules、旧 Session 与 M1 兼容 |
| CC §9–§10 | 白名单内实现与逐项测试 |
| CC §10 并发（v0.3.1 修订） | 获批的非生产 `odoo18ce`、独立连接实际竞争；顺序模拟不算并发安全 PASS |
| TDD V2.0.2 §5.4 | 显式历史恢复生成新版本，旧确认失效 |

## 3. 当前测试摘要

| 指标 | 数值 |
|---|---:|
| 新增 CB-02 TransactionCase 测试方法（源码计数） | 18 |
| Python compilation | PASS |
| Manifest AST / XML parse | PASS |
| `git diff --check` | PASS |
| CB-02 TransactionCase（目标类） | PASS — 18 项测试方法运行，0 failed / 0 error |
| M1 Private Skill / RenderBridge 定向回归 | PASS — 23 项测试方法运行，0 failed / 0 error |
| 完整 Odoo TransactionCase（两模块） | PASS — 203 个方法启动，202 个未跳过完成，1 个 SKIP，0 failed / 0 error |

## 8. Owner Decision — Final Acceptance

- 日期：2026-11-08。
- 决定：负责人对 CC-M2-CB-02 正式 `Final Accepted` 决定回答批准（选项 1）。
- 范围：仅本 ATR 所列 CB-02 技术验收范围；历史 READY 阶段记录保留，未重跑测试。
- 遗留边界：生产附件留存/删除仍为独立 `Release Gate OPEN`；1 个 browser-backed RPC 用例仍为 SKIP/未验证；二者均不被写作已通过，也不由本决定授权生产发布。
| 模块升级 | PASS — 命令 `-u office_engine_m2,office_engine_odoo`；两模块均加载并完成测试 registry 构建 |
| 模块统计差异 | RESOLVED — `tests.stats` 将 19 个 test class 的 `setUpClass`/`tearDownClass` 统计项计入数字；不代表额外用例 |
| Database race | PASS — 两个独立 backend 竞争；唯一赢家提交、败方数据库并发冲突回滚且新事务 stale 重验拒绝；唯一标记合成链按批准保留 |
| Odoo test result | 203 项汇总，0 failed / 0 error；详见 ATR-RUN-005 |
| Test-level SKIP | 1 项：`test_real_backend_browser_renders_select_and_saves_over_rpc`，因缺少 `websocket-client` 跳过；另有 3 个无关、not-installable addon 被模块图跳过 |
| Latest Odoo Test Run | ATR-RUN-005；并发验收 ATR-RUN-006；共享 DB `odoo18ce` |

## 4. Coverage Matrix（初始）

| CC 范围 | 自动化验证 | 状态 | 证据 |
|---|---|---|---|
| V1 proof 与 registration | 持久化 M1 report/policy/input/output SHA、Session/Proposal revision | PASS | `test_workbook_version_contract.py` / ATR-RUN-005 |
| Candidate chain | V1→V2→V3、父链、状态、幂等与 current/last-valid | PASS | `test_workbook_version_contract.py` / ATR-RUN-005 |
| Proof forgery | direct ORM 字段、JSON/错误 typed receipt、跨 candidate、SHA/revision mismatch | PASS | contract + attachment tests / ATR-RUN-005 |
| Access boundary | owner/company/Session/thread、版本与附件权限、摘要读取 | PASS | `test_workbook_version_access.py` / ATR-RUN-005 |
| Restore | 新 recovery child、源历史不变、current parent、fresh confirmation/proof、stale 拒绝 | PASS | `test_workbook_version_state.py` / ATR-RUN-005 |
| Idempotency | 同键同载荷重放；异 SHA/source/parent 拒绝 | PASS | `test_workbook_version_contract.py` / ATR-RUN-005 |
| Atomicity | candidate 附件创建失败、接受回滚、失败等级不推进 | PASS | `test_workbook_version_state.py` / ATR-RUN-005 |
| Finalize reference | 已接受 current 的实际字节、assistant Thread 消息、附件绑定和不可变性 | PASS | `test_workbook_version_state.py`, `test_render_bridge.py` / ATR-RUN-005 |
| Attachment integrity | private binding、真实 bytes/hash、write/unlink protection | PASS | access/state tests / ATR-RUN-005 |
| Odoo module compatibility | manifest upgrade、旧 Session/Proposal/request 读写 | PASS | `-u office_engine_m2,office_engine_odoo` + full tests / ATR-RUN-005 |
| Database race | 两独立 Odoo cursor/backend 竞争同一 current parent + Document Revision | PASS | ATR-RUN-006; concurrency run + read-only ORM/XLSX readback logs |
| Provider/Browser/CB-03 validator | Out of scope for CB-02 | NOT RUN / OUT OF SCOPE | 本 CC 明确不覆盖 |

## 5. Test Run History（仅追加）

### ATR-RUN-000 — 执行前基线（历史记录）

- 状态：NOT RUN。
- 含义：编写实现和测试前的计划快照；不代表后续没有运行。

### ATR-RUN-001 — 静态检查及 Odoo 环境可用性

- 日期：2026-11-06。
- 数据：未访问业务记录；未调用 Provider；没有创建持久化测试数据。
- `./venv/bin/python -m py_compile`，覆盖本 CC 的模型、服务、RenderBridge、测试夹具/用例、Odoo Request 及附件身份测试：**PASS / exit 0**。
- Manifest 检查：使用 `ast.literal_eval` 读取 `office_engine_m2/__manifest__.py` 与 `office_engine_odoo/__manifest__.py`：**PASS / 2 个**。
- XML 检查：`office_workbook_version_rules.xml` 使用 `xml.etree.ElementTree.parse`：**PASS / 1 个**。
- `git diff --check`：**PASS / exit 0**。
- 信任边界静态核对：新增生产 models/services 没有导入 `tests.support.validator_stub`；`record_validation_receipt` / `accept_verified_candidate` 仅为普通 Python service 函数，没有加入 ORM Model/RPC/tool schema；受保护关系字段的 ORM `create/write` 需要进程局部 ContextVar。结果：**STATIC CHECK PASS；不是行为安全测试**。
- SQL 核对：本次 Session 新增 SQL 只有 ORM ACL 校验后的 `SELECT id ... FOR UPDATE`；没有新增业务数据 SQL `INSERT/UPDATE/DELETE`。Model 的 `init()` 中已有旧状态映射 SQL 属于基线代码，未改动。
- 环境检查：`pg_isready -h 127.0.0.1 -p 5555` 返回 `127.0.0.1:5555 - no response`；Odoo 配置 `db_name=odoo18ce`，该数据库服务端点不可达。8091 仍有 Python 进程 PID 4295 监听；不重启服务，且不能由监听进程推断其内存模块版本。
- Odoo TransactionCase：**BLOCKED / NOT RUN**。无法建立 Odoo registry/test cursor；没有运行测试断言，也没有更新共享 DB schema。
- Isolated DB concurrency：**BLOCKED / NOT RUN**。没有可用 PostgreSQL endpoint 或 disposable test DB。race helper 不是并发验证证据。
- Module upgrade/旧 Session 兼容：**NOT RUN**。不在仍运行 8091 的共享环境对数据库执行升级。
- Provider/Browser/真实数据：**OUT OF SCOPE / NOT RUN**。
- 费用/请求：0 Provider requests。

实际静态命令（退出码 0）：

```sh
./venv/bin/python -m py_compile \
  mymodules/office_engine_m2/models/office_workbook_version.py \
  mymodules/office_engine_m2/models/office_mapping_session.py \
  mymodules/office_engine_m2/models/ir_attachment.py \
  mymodules/office_engine_m2/services/workbook_version_service.py \
  mymodules/office_engine_m2/services/mapping_service.py \
  mymodules/office_engine_m2/services/__init__.py \
  mymodules/office_engine_m2/services/render_bridge.py \
  mymodules/office_engine_m2/tests/support/__init__.py \
  mymodules/office_engine_m2/tests/support/validator_stub.py \
  mymodules/office_engine_m2/tests/test_workbook_version_contract.py \
  mymodules/office_engine_m2/tests/test_workbook_version_access.py \
  mymodules/office_engine_m2/tests/test_workbook_version_state.py \
  mymodules/office_engine_m2/tests/test_render_bridge.py \
  mymodules/office_engine_m2/tests/integration/test_workbook_version_race.py \
  mymodules/office_engine_odoo/models/office_document_request.py \
  mymodules/office_engine_odoo/tests/test_attachment_identity.py
git diff --check
```

本次未发生 pytest collection 错误；没有执行 pytest/Odoo test runner。若后续执行发现测试收集或断言失败，必须在后续 ATR 运行中保留原始失败日志，不覆盖此记录。

## 6. Regression Verification

ATR-RUN-005 的 Odoo runtime 回归覆盖 M1 Mapping/RenderBridge、`office.document.request` proof 写入、附件交付关联及附件失败恢复；另有 1 项 Browser-backed RPC 测试因缺 `websocket-client` 跳过，故该具体浏览器/JS 路径仍未验证。Chat Completions 业务实现未修改。

## 7. Issues

- CC02-OPEN-01：生产附件留存/删除政策未批准，阻止真实业务数据启用和生产发布，不替代本轮合成数据测试。
- CC02-OPEN-04：**CLOSED** — v0.3.1 并发环境修订及合成链留存已获负责人批准；真实双连接验收 PASS，证据见 ATR-RUN-006。
- ATR-RUN-005 测试计数差异已解释，证据见 `evidence/CB-M2-CB-02/test-count-analysis-20261107.md`。

## 8. Special Verification

| 验证 | 结果 |
|---|---|
| Python compilation | PASS / command exit 0 |
| XML parse | PASS / 1 file |
| Manifest AST | PASS / 2 manifests |
| Module version bump / update | PASS — `-u office_engine_m2,office_engine_odoo`; both target modules loaded and registry rebuilt in the test run |
| Odoo TransactionCase | PASS — 203 started, 202 not skipped, 1 skipped, 0 failed / 0 errors |
| Real two-connection concurrency | PASS — approved v0.3.1; exactly one winner, one SerializationFailure rollback, fresh stale retry rejected; readback verified |
| 8091 restart / browser availability | PASS — restarted under user authorization; service listening and authenticated page reconnected |
| `tests.stats` count reconciliation | RESOLVED — class lifecycle metrics explain extra 38 entries |
| Provider API | OUT OF SCOPE / NOT RUN |
| Browser E2E | OUT OF SCOPE / NOT RUN |

## 9. Evidence Inventory

本轮包含首次失败与修复日志、CB-02 定向和完整 Odoo 测试日志、M1 回归日志、真实并发与只读 lineage/XLSX 回读日志，均位于 `docs/implementation/evidence/CB-M2-CB-02/`；ATR-RUN-005/006 记录命令、真实计数、版本 ID、结果与退出状态。没有 Provider 请求或真实业务文件；证据中不存放密钥、Cookie 或业务附件。模块升级和并发测试使用获批 `odoo18ce`，仅写入合成测试记录；唯一标记的不可变 synthetic lineage 按 v0.3.1 批准保留。

## 10. Handoff Summary

（历史运行摘要：当时状态为 Odoo Integration Pending；后续状态以 ATR-RUN-002/003 为准。）当时新增 Odoo 行为测试与 schema upgrade 尚未运行；静态结果不得表述为 Odoo Integration Verified。生产附件留存政策仍 OPEN；CB-03 Validator、Provider/Browser 与生产 Release Gate 独立。

## 11. Test Run History — ATR-RUN-002（只读集成环境核查）

- 日期：2026-11-07。
- 本次范围：只读环境核查；未运行 Odoo 测试、模块升级或数据库并发测试。
- 8091 进程配置：PID 4295 使用相对配置参数 `-c odoo.conf`，工作目录为仓库根目录。实际配置目标为 `127.0.0.1:5555 / odoo18ce`，HTTP 端口 8091。数据库密码仅检查“是否配置”，不读取或记录其值。
- 端点结果：`pg_isready -h 127.0.0.1 -p 5555` 返回 `127.0.0.1:5555 - no response`；主机 `lsof` 未显示 TCP 5555 listener。`lsof` 显示 PID 4295 和另一 Python 进程仍有到 5555 的已建立 TCP 会话。它们可能为失效/残留连接，不能作为数据库可用证据。`127.0.0.1:5432` 同样无响应。
- 进程/服务发现：只读 `launchctl list` 未找到包含 PostgreSQL、Postmaster 或 PgBouncer 的服务项；Docker CLI 不存在。`/Library/PostgreSQL/16/data` 的 `pg_ctl status` 因读取 `postmaster.pid` 权限不足而失败，即使在本次批准的只读权限提升调用后也无法读取；PostgreSQL 进程及其实际 data directory 因而未确认。Homebrew 服务清单因本机 Homebrew 元数据缓存权限错误未取得，不能作为服务状态证据。
- 隔离 DB：仓库配置清单未发现额外 Odoo 测试配置；唯一已核实配置指向 `odoo18ce`。由于 PostgreSQL 无响应，无法列举其数据库，也无法确认是否存在其他授权隔离 DB。结论为 **NO AUTHORIZED ISOLATED DB CONFIRMED / ENVIRONMENT BLOCKED**，不推断其他 DB 不存在。
- 执行结果：TransactionCase **0 项断言运行**；模块升级 **NOT RUN**；M1 Mapping/RenderBridge/`office.document.request`/附件权限行为回归 **NOT RUN**；独立连接数据库竞争 **NOT RUN**。测试数仍为源码计数 18，不是运行通过数。
- 数据安全：没有建立数据库会话、执行 SQL/ORM、创建数据库、修改共享/业务数据、启动/停止 PostgreSQL 或重启 8091；没有 Provider 请求。
- Git：仅追加本次环境审计事实到 IHR/ATR；未 stage、commit、push、reset、clean。

### 当前最小环境修复/测试库方案（等待授权）

1. 由环境管理员确认 `127.0.0.1:5555` 原本对应的 PostgreSQL 实例/转发服务及其启动方式，并授权恢复该端点或提供替代的隔离测试端点；不触碰 8091。
2. 先以 `pg_isready` 与只读连接验证端点，再确认测试数据库名称和所有者。若没有已授权隔离库，负责人需明确授权创建一个专用 disposable DB/临时 Odoo 测试服务；不使用 `odoo18ce`，不复制真实业务数据。
3. 在获准的 disposable DB 中，以合成数据准备可升级基线（必要时从实施前代码版本初始化），再对当前 `office_engine_m2` 与 `office_engine_odoo` 执行升级及全部 CB-02 TransactionCase 和既有 M1/附件回归。
4. 使用 disposable DB 上的两个独立连接/游标执行同 parent/revision 竞争测试；至少一个接受成功，竞争者因过期 parent/revision 被拒绝。按真实日志更新 ATR，不以顺序测试代替。

**门禁结论：**当前只读核查已完成，但测试运行被环境可用性阻塞。须获得隔离 PostgreSQL 服务/DB 的启动或创建授权后再继续；在此之前状态保持 `Implementation Complete; Odoo Integration Pending`，不可提交 `READY FOR FINAL ACCEPTANCE`。

## 12. Test Run History — ATR-RUN-003（负责人数据库授权后的只读复核）

- 日期：2026-11-07。
- 负责人决策：允许使用 `odoo.conf` 指定的 `odoo18ce` 完成 CB-02 集成测试；不要求另建 DB。负责人同时要求不改冻结 CC 验收标准，且若服务恢复会影响其他服务/会话，先报告具体动作并等待确认。
- PostgreSQL 身份：`launchctl print system/postgresql-16` 返回 system LaunchDaemon `running`、PID 842、运行用户 `postgres`、程序路径 `/Library/PostgreSQL/16/bin/postgres`、数据目录 `/Library/PostgreSQL/16/data`。服务 plist 只读字段与之吻合，`RunAtLoad=true`、`KeepAlive=false`。
- 监听状态：TCP 5555、5432，IPv6 loopback 5555/5432，以及 `/tmp` socket 目录对应端口的 `pg_isready` 均返回 `no response`；当前用户权限下的 `lsof` 未显示 PostgreSQL TCP listener，但服务进程属于其他用户，该观察不能证明系统中没有 listener。实际 Unix socket 目录未知。当前无法读取 PostgreSQL 专有数据目录配置：`pg_ctl status` 不能读取 `postmaster.pid`，`postgresql.conf` 读取受权限限制；`sudo -n -u postgres` 报告需要密码。故 PostgreSQL 实际 `port`/`listen_addresses`、PG 内部健康及无响应原因仍 `UNVERIFIED`。未猜测是配置错端口或服务损坏。
- 影响范围：PID 4295（Odoo 8091）及 PID 6868（pgAdmin）有指向 `127.0.0.1:5555` 的已建立 TCP 会话。会话是否仍有效不确定；重启 PostgreSQL 会有中断这些会话的风险。未执行重启，等待负责人对具体动作确认。
- 日志线索：对 `debug_logs/odoo_181.log` 的只读定向搜索发现多条 `psycopg2.errors.SerializationFailure: could not serialize access due to concurrent update`（日志行号约 92232–97793）。没有解析这些条目的事务时间、用户或业务记录，不据此声称当前存在活动事务，也不将其归因于 CB-02；这只是共享库并发状态的历史风险线索。当前活动事务无法通过 PostgreSQL 查询确认。
- DB 状态：未连接数据库，无法确认 `odoo18ce` 存在性/可用性、当前模块版本、安装状态、目标表结构或活动事务。未确认其他授权隔离 DB。
- CC 并发条款复核：CC v0.3 §10 要求并发竞争仅在独立 disposable test DB 执行，并禁止共享开发/生产 DB。负责人授权使用 `odoo18ce` 不等同修改 CC。故共享 DB 并发测试为 **CONTRACT CHANGE REQUIRED**，等待正式修订批准；不得执行或用顺序测试冒充。
- 测试结果：本次只读检查；TransactionCase、M1/RenderBridge/Document Request/附件回归、模块升级均 **NOT RUN**；真实并发为 **NOT RUN / CONTRACT CHANGE REQUIRED**。已执行断言数仍为 0。
- 安全边界：未执行 SQL/ORM 查询、未升级 schema、未写入数据库、未启动/停止/重启 PostgreSQL 或 8091、未处理业务附件/调用 Provider。
- 文档完整性：只追加此记录；不修改冻结 CC、TDD 或实施计划。
- 日志权限补充：尝试从 macOS unified log 只读筛选 PostgreSQL 监听/启动消息，但系统返回 `Cannot run while sandboxed`；未得到服务启动错误日志。该证据缺口保留为 `UNVERIFIED`。

### 当前下一步门禁

1. 环境管理员需提供 PG16 的非敏感配置值（`port`、`listen_addresses`、socket directory）及健康/启动错误检查结果，或负责人需明确批准的具体服务操作。当前服务虽在 launchd 显示 `running`，但目标 5555 不接受新连接；不能安全地自行重启。
2. 恢复连接后，在升级前只读核验 `odoo18ce`、已安装模块、版本、目标表结构和活动事务；再审查本次模块升级的具体 schema/data 影响。只有没有破坏性迁移且不违反负责人边界时才升级。
3. 为并发验收另需符合 CC v0.3 的 disposable test DB；若负责人希望在 `odoo18ce` 上进行，须先批准针对 CC §10 的最小契约修订。现有数据库授权本身不解除此条款。

**当前状态仍为 `Integration Blocked`。**没有足够证据进入测试执行阶段，不提交 `READY FOR FINAL ACCEPTANCE`。

## 13. Test Run History — ATR-RUN-004（认证 Odoo ORM 核验与模块升级尝试）

- 日期：2026-11-07。
- 用户问题/修正：用户指出 Odoo ORM 是否可用。本轮通过当前已认证的 8091 页面实际读取 Settings、Technical Model 元数据和 Apps 模块信息。结论：**现有 8091 ORM 请求可用**；此前 `pg_isready` 无响应只证明该独立探测未取得响应，不足以证明现有 Odoo 数据访问不可用。
- 已安装版本（Apps 页面）：`office_engine_m2` 为 `18.0.26.0.13`，`office_engine_odoo` 为 `18.0.1.4.1`。工作区 manifest 分别为 `.14` 与 `.2`。
- Registry 元数据：Technical → Models 页面成功读取 `office.mapping.session` 字段目录，但工作区新增的 `document_revision`、`current_version_id`、`last_valid_version_id` 未出现在该当前 ORM 字段列表中；现有页面/registry 尚不能证明本轮工作区 Python 模型已加载。
- 模块升级尝试：通过 Odoo Apps 页面调用 `office_engine_odoo` Upgrade（目标数据库来自当前 Odoo 会话，依此前负责人授权）。真实服务器响应为 `RPC_ERROR`。调用链为 `ir.module.module.button_immediate_upgrade` → `Registry.new(update_module=True)` → 加载 `office_engine_m2/security/ir.model.access.csv`，失败详情：`No matching record found for external id 'model_office_workbook_version' in field 'Model'`，随后提示 `office_engine_m2` 模块加载失败。工作区 `models/__init__.py` 已导入新模型；但当前 registry 加载阶段没有相应 `ir.model` 外部 ID。Apps 页面重读仍显示两个旧版本。未手工修复该错误，因为现有证据指向运行进程未载入新增模型代码；在不重启 8091 的限制下，不能安全地从当前旧 registry 完成这项升级。
- 运行结果：此操作不是测试。CB-02 TransactionCase **0 方法运行 / 0 断言**；M1 Mapping、RenderBridge、`office.document.request`、附件 ACL 回归 **NOT RUN**；真实并发 **NOT RUN / CONTRACT CHANGE REQUIRED**。不将 ORM 页面读取或模块升级尝试视为测试 PASS。
- 对数据库服务问题的定位：可以并且已经通过现有 Odoo ORM 读元数据；不能通过当前服务进程之外的新 PostgreSQL 连接运行独立 Odoo test runner，因为历史 `127.0.0.1:5555` 探测仍为 `no response`。因此，“ORM 可用”与“独立测试 runner 可连接”是不同状态。
- 安全与副作用：未重启 Odoo 或 PostgreSQL，未连接数据库驱动、执行原始 SQL、创建测试记录或调用 Provider。模块升级未成功；未确认模块升级对数据库有部分持久改变，因此保持其结果为 `FAILED/NOT COMPLETED`，不作成功或已完全回滚的推断。
- 后续门禁（一次性明确请求）：完成正式 TransactionCase 需批准恢复 PostgreSQL 16 服务的具体操作，并批准在目标端点恢复后重启 8091 以加载工作区 Python 代码；PostgreSQL 当前服务由 `launchctl system/postgresql-16` 管理（前次观测 PID 842）；8091 进程 PID 4295，另有 pgAdmin PID 6868 使用该端点。重启 PostgreSQL 会断开现存 Odoo/pgAdmin 会话并可能回滚当时未提交事务；重启 8091 会使当前网页/会话短暂不可用。未得到这两项具体操作确认前，不执行。
- 并发门禁：CC v0.3 §10 要求真实竞态在独立 disposable test DB；`odoo18ce` 负责人授权不更改该条款。该项单独等待正式契约修订，不阻断其余已授权测试。
- 真实服务与浏览器证据：通过当前 8091 已认证页面导航读取 Odoo Settings、Technical Models、Apps 记录。没有把该 UI 观察描述为 Browser E2E 或业务流程验收。

## 14. Test Run History — ATR-RUN-005（负责人授权后的模块升级、TransactionCase 与 M1 回归）

- 日期：2026-11-07。
- 授权/边界：按负责人指令停止独立 PostgreSQL/5555 探测；使用 `odoo.conf` 配置和现有认证 ORM 流程。负责人授权在共享开发库 `odoo18ce` 执行模块升级及测试，并单独指出若 CC §10 限制并发则列为待裁定项，不得因此阻断其他测试。本轮不访问或改动真实业务记录，不调用 Provider，不执行 Git 写操作。
- 8091 生命周期：依授权终止原 8091 Odoo PID，先通过已认证 UI 提交两个目标模块 Upgrade；之后使用 `-u` 测试 runner 执行升级与完整 TransactionCase。测试完成后按用户最新授权重新启动 Odoo，当前 PID `35158` 监听 8091；浏览器已认证 Inbox 页面显示服务连接恢复。未执行独立 PostgreSQL 检查。
- 初次完整运行失败证据（保留）：`/private/tmp/cc02_transactioncase_20261107.log`，初次完整结果为 **1 failed、19 error(s) / 203**。根因定位：18 个 CB-02 fixture 错误源于普通内部测试用户没有联系人创建 ACL；1 个 M1 RenderBridge mock 不接受新增的 `version_binding` 调用参数；另 1 个 Private Skill M1 mock 同样因参数签名过旧导致预期失败。没有降低生产 ACL 或删除测试。
- CB-02 定向修复复测：第一次修复后，`/private/tmp/cc02_targeted_20261107.log` 报告 **0 failed、3 errors / 18**。剩余原因分别为测试数据库 `res.company` 的必填扩展字段、测试附件未绑定可访问 Session、以及合法 `PARTIALLY_VERIFIED` receipt 被状态迁移表拒绝。修复后重跑同 18 项，`/private/tmp/cc02_targeted_20261107_retry1.log` 最终报告 **0 failed、0 error(s) / 18**。当前 `candidate_received → partially_verified` 只记录验证结果；`accept_verified_candidate` 仍只接受 `VERIFIED`，失败/部分/拒绝不会推进 current 或 Document revision。
- M1 定向回归：`/private/tmp/cc02_m1_regression_20261107_retry1.log`，Private Skill 与 RenderBridge 两类共 **23 项 / 0 failed / 0 error**。两个 mock 现在接收并断言 `version_binding` 的 Session、Session revision、Proposal revision；没有绕开真实生产调用链断言。
- 完整升级及回归命令：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce \
  -u office_engine_m2,office_engine_odoo \
  --test-enable --test-tags /office_engine_m2,/office_engine_odoo \
  --stop-after-init --no-http --log-level=test \
  --logfile=/private/tmp/cc02_transactioncase_20261107_retry1.log
```

- 完整结果：`odoo.tests.result` 报告 **0 failed、0 error(s) / 203 testsRun**；日志有 **203** 条 `Starting Test`，其中 M2 180、Odoo Request 23；203 个测试 ID 唯一、重复数 0。实际有 **1 个 test skip**（`TestOfficeMappingRpcHttp.test_real_backend_browser_renders_select_and_saves_over_rpc`，原因 `websocket-client module is not installed`），故 202 项未跳过运行，0 failed / 0 errors。两个目标模块均在本次 `-u` 下进入 `Module ... loaded` / registry rebuild：`office_engine_odoo` 加载 22.99s（含 22.51s 测试），`office_engine_m2` 加载 539.45s（含 539.17s 测试）。全部 18 项 CB-02 TransactionCase 在完整集内运行。
- **计数差异已解释**：`tests.stats` 报 M2 214、Odoo 27（合计 241）。Odoo `OdooSuite` 将 `setUpClass` 和 `tearDownClass` 单独放入统计表；`log_stats()` 将这些生命周期统计 ID 也计为 stats 的 `tests`。本次 M2 17 个类对应 34 条额外统计，Odoo Request 2 个类对应 4 条，合计正好 38。`tests.result` 的 203 是 `startTest()` 计数，包含被 skip 的测试方法。源码引用、日志计数与解析结果见 [test-count-analysis-20261107.md](evidence/CB-M2-CB-02/test-count-analysis-20261107.md)。不将 241 报为执行通过数。
- 模块图还跳过 3 个无关的 `not installable` addons（`wd_qooling_app`、`wd_advanced_m2o_record_panel`、`wd_evidence_album`）；它们不是 3 个目标测试用例，也不等于前述单个 test skip。
- CLI session 在测试汇总后未自行结束；shutdown 阶段记录遗留测试子进程和 `bus_presence` serialization conflict / websocket `BrokenPipe`，测试进程随后终止。该诊断发生在 `0 failed/0 error(s)` 汇总行之后，单独作为运行收尾现象记录。
- 并发：**NOT RUN / APPROVAL REQUIRED**。冻结 CC v0.3 §10 明文要求 disposable/isolated DB；现有授权不修改契约。只读代码审查确认版本/附件 history 通过服务不变量保持不可删除，因此在共享 `odoo18ce` 上提交竞争结果后无法通过普通 ORM 清理全部合成版本链。IHR-007 与 [`concurrency-contract-review-20261107.md`](evidence/CB-M2-CB-02/concurrency-contract-review-20261107.md) 提出窄修订及两种选择：允许在非生产开发/测试 DB 使用合成记录，并在无法清理时明确批准保留带唯一标识的合成版本链；或维持清理要求并使用 disposable DB。现有 race helper 使用两个独立 cursor 和 barrier，但把任意异常都归为 rejected；获批后的验收需确认败方确由 stale/revision 冲突拒绝，其他异常均判失败。负责人批准前不执行、不修改冻结 CC。
- 回归/安全观察：直接 ORM/RPC 伪造状态、验证回执和跨候选证明等用例均在 203 项完整测试中通过；owner/company/Session/Thread 与私有附件访问用例通过。TransactionCase 使用回滚机制和合成数据；未将业务写入作为测试对象。真实 CB-03 Validator、Provider、Finalize 浏览器端到端和生产附件政策仍在 CC-02 范围外/未授权。
- 证据文件：首次完整失败、定向未通过、定向通过、M1 定向通过及最终完整通过日志已复制到 [`evidence/CB-M2-CB-02`](evidence/CB-M2-CB-02/)，原 `/private/tmp` 文件保留。日志不含凭据。
- 当时结论（ATR-RUN-005）：**Odoo module update + 203 个测试方法（202 未跳过、1 SKIP）+ M1/附件回归：PASS（测试层）；241 stats 已解释而非测试数；真实并发：NOT RUN / approval pending；当时尚不提交 READY FOR FINAL ACCEPTANCE。** 并发后续状态见 ATR-RUN-006。

## 15. Test Run History — ATR-RUN-006（负责人批准后的并发契约修订与真实双连接验收）

- 日期：2026-11-07。
- Owner Decision：负责人批准 CC §10 最小并发环境修订并允许保留带唯一标识的合成版本链。新增 `CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md`；原冻结 v0.3 未覆盖。只调整测试数据库资格及不可变合成数据留存边界，不改 one-winner、stale/revision、权限、附件和事务验收标准。
- Test precondition：通过 Odoo ORM 按唯一 tag `CB02-CONCURRENCY-APPROVED-20261107-01` 确认不存在既有 Thread/测试链；创建全新 synthetic Thread/Session/V1/两个候选。测试使用非 superuser `base.user_admin` 的 ORM 环境执行业务服务；没有读取或修改真实业务记录。远端 Provider 请求数为 0。
- Test implementation：最初 helper 会把任意异常都作为 `rejected`。在批准范围内仅修改 `mymodules/office_engine_m2/tests/integration/test_workbook_version_race.py`：记录独立 backend PID，连接设置 10 秒 lock timeout/30 秒 statement timeout；仅接受带 `WORKBOOK_VERSION_STALE` 的应用异常或 PostgreSQL `SerializationFailure` 为并发败方，其他异常作为测试失败。回滚败方事务。
- Exact command：

```sh
./venv/bin/python docs/implementation/evidence/CB-M2-CB-02/run-concurrency-acceptance-shell.py
```

- Harness startup failures preserved：使用 `odoo-bin shell` 的首次尝试在 server process-list shutdown hook 触发 `PermissionError`，未创建 Registry cursor；后两次独立 runner 分别因 repo/mymodules 导入路径问题失败；sandbox 内 ORM 连接返回 `Operation not permitted`。原始输出文件为 `concurrency-run-20261107_shell-permission-failure.log`、`concurrency-run-20261107.log`、`concurrency-run-20261107_retry1.log`、`concurrency-run-20261107_retry2.log`。失败都发生在测试 fixture 写入前。修正导入路径后，根据用户已批准操作，通过受控沙箱外命令执行成功；未重启 Odoo/PostgreSQL，也未检查 PostgreSQL 端口。
- Actual race result：fixture Thread `13850`、Session `10612`、V1 `101`、competing candidates `102`/`103`，Document Revision `1`。Barrier 两侧真实数据库 backend PID 分别为 `37490`、`37491`。候选 `103` 唯一提交，state=`accepted_current`；另一事务候选 `102` 收到 `SerializationFailure: could not serialize access due to concurrent update` 并 rollback。之后使用新事务重试 `102`，服务明确返回 `WORKBOOK_VERSION_STALE`。helper 与竞态证据文件 `concurrency-run-20261107_authorized.log`。
- Final state and attachment audit：current=last-valid=`103`，Document Revision=`2`；V1 `101` 为 `superseded`；败方 `102` 保持 `verified` 但不是 current。独立只读 ORM 检查确认 Session 下恰好 3 个版本、恰好 3 个版本输出附件；parent/input/owner/company/thread bindings 一致，没有孤立输出附件。三个实际附件均以 SHA-256 对比版本字段，并经 ZIP integrity 和 `openpyxl.load_workbook(data_only=False)` 成功读取。详情与散列见 `concurrency-lineage-readback-20261107.log`。
- Data/cleanup：没有业务记录被修改。版本行及关联附件被设计为不可变，不能通过 ORM 清除；按负责人批准保留唯一标记的纯 synthetic lineage。测试 Thread/Session、源与输出附件及关联版本均保留，未调用 Provider。
- Other results retained：完整模块升级/203 started（202 未跳过、1 skip、0 failed/errors）、CB-02 定向 18 PASS、M1 定向 23 PASS、首次失败日志和 241-vs-203 统计解释均以 ATR-RUN-005 记录，不重跑。
- Current status：并发验收 **PASS**；测试统计差异 **RESOLVED**；其余必需 CB-02 技术验收有实际 PASS 证据。**CC-M2-CB-02 — READY FOR FINAL ACCEPTANCE**，由负责人作最终决定；不标记 Final Accepted。生产附件留存/删除政策仍为独立 `Release Gate OPEN`，不阻断本次合成数据技术验收。

## 16. Final Evidence Index — compiled 2026-11-08

- 逐项 CC 验收证据、数据库环境、并发结果、版本/附件回读、测试统计口径、保留限制与证据 SHA-256 已汇总于 [FINAL_EVIDENCE_INDEX_20261107.md](evidence/CB-M2-CB-02/FINAL_EVIDENCE_INDEX_20261107.md)。
- 冻结 CC v0.3 原文未修改；并发环境按负责人批准的 v0.3.1 修订执行。证据核对未发现未批准的契约偏差。
- 最终状态：**READY FOR FINAL ACCEPTANCE**。负责人应另行作出 `Final Accepted` 决定；本 ATR 不代签。生产附件留存/删除政策保持 `Release Gate OPEN`，单项 browser-backed RPC 用例仍为 SKIP/未验证。

## 17. Amendment v0.1 Implementation Record — Static Checks / Odoo Integration Not Run

- 日期：2026-11-08。
- 权威决定：负责人批准 TDD V2.0.3、Implementation Plan V2.0.2 和 CB-02 Candidate Acceptance / Intent Binding Amendment v0.1 生效，并要求先实施及验收该 Amendment，再继续依赖它的 CC-04。该 Amendment 不改变原 CB-02 技术范围 Final Accepted 记录；本节单独跟踪 Amendment 验收。
- 范围：合成数据下逐轮用户 Intent 绑定、Candidate 条件式接受与拒绝；保持 `source_message_id` 首轮来源语义、CB-03 Receipt、M1 Mapping、CB-02 版本/附件权限和 Current/Last Valid 原子服务边界。
- 实际代码调整：`models/office_workbook_version.py` 增加 `intent_message_id`、接受/拒绝审计字段以及 `verified → rejected`；`services/workbook_version_service.py` 增加真实 Thread 用户消息校验、typed acceptance/rejection、Candidate 绑定重验、拒绝不推进指针，并在幂等比较中加入 Intent 和 confirmation reference。测试支持和用例新增确认授权绑定、Effect/Receipt/SHA/parent/revision/message 不匹配拒绝、同 Candidate 重复接受/拒绝幂等、确认回执不能跨幂等请求复用、拒绝不改变 Current/Last Valid/Document Revision 或附件 SHA。双连接 runner 已更新为传递带真实 Candidate Review 消息的 typed authorization；历史运行日志保持原样。
- 静态命令及结果：

```sh
python3 -m py_compile \
  mymodules/office_engine_m2/models/office_workbook_version.py \
  mymodules/office_engine_m2/services/workbook_version_service.py \
  mymodules/office_engine_m2/tests/support/__init__.py \
  mymodules/office_engine_m2/tests/support/validator_stub.py \
  mymodules/office_engine_m2/tests/test_workbook_version_contract.py \
  mymodules/office_engine_m2/tests/test_workbook_version_state.py \
  mymodules/office_engine_m2/tests/test_candidate_validator.py \
  mymodules/office_engine_m2/tests/integration/test_workbook_version_race.py \
  docs/implementation/evidence/CB-M2-CB-02/run-concurrency-acceptance-shell.py
```

结果：退出码 0。`git diff --check` 退出码 0；9 个相关 Python 文件的行尾空白检查 PASS。记录见 `evidence/CB-M2-CB-02/cb02-amendment-static-20261108.log`。这些是静态检查，不是 TransactionCase。
- Odoo TransactionCase / module upgrade / M1 regression：**NOT RUN**。原因：唯一先前明确授权的数据库 `odoo18ce` 与正在运行的 8091 实例关联，而本次授权明令禁止升级该运行实例；尚无另一个已确认、已授权的隔离测试数据库。未连接/探测数据库，未重启服务，未将历史 CB-02 v0.3 通过日志冒充本 Amendment 的测试结果。
- Concurrent race：**NOT RUN for Amendment API**。既有 2026-11-07 双连接证据证明原 v0.3/v0.3.1 API 的竞态不变量；由于接受接口本轮新增 typed authorization，竞态 runner 现已更新但需要在授权隔离数据库重新验证。顺序 TransactionCase 不替代此测试。
- Final status：**AMENDMENT IMPLEMENTATION — INTEGRATION BLOCKED / NOT ACCEPTED**。CB-02 原技术范围的 Final Accepted 状态不被撤销；本 Amendment 尚未达到组件验收，故依赖它的 CC-04 集成实施仍停在前置门。
- Environment request: 指定一个可用、已授权的隔离非生产 Odoo 数据库，或批准创建全新空白合成测试数据库并仅在该库安装/升级目标模块和运行 TransactionCase。不得升级服务 8091 使用的数据库作为替代。

## 18. Amendment v0.1 Integration Acceptance — Owner-Authorized `odoo18ce`

- 日期：2026-11-08。
- 授权：负责人明确要求不新建数据库、使用 `odoo18ce`，并批准短暂停止 8091、升级目标模块、运行合成数据测试后恢复服务。该授权覆盖本次 CB-02 Amendment 集成验收；没有访问真实业务记录、调用 Provider 或检查 PostgreSQL/5555。
- 首次完整运行（保留，不覆盖）：`evidence/CB-M2-CB-02/cb02_amendment_transactioncase_20261108.log`，退出码 1；214 个测试方法启动，0 failed / 11 errors。错误根因已查明并修复：6 个测试把异常元组传给 Odoo TransactionCase 的 `assertRaises`；4 个 Candidate Review 判定依赖数据库与 Python 时钟比较；1 个 FAILED Candidate 用例未提供 typed authorization，未到达预期状态断言。
- 修复边界：为 Candidate 记录创建时的 Thread message watermark，并在服务端要求 Review/Reject 用户消息晚于 watermark；水位字段由服务端建立、只读、绑定 Candidate Thread。补充“Candidate 前旧消息不可授权”的回归。将异常断言改为明确类型捕获；FAILED 状态测试提供完整、绑定范围的授权以实际验证失败状态禁止接受。未放宽权限或验证级别。
- 定向 TransactionCase：

  ```sh
  ./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2 \
    --test-enable --test-tags /office_engine_m2:TestWorkbookVersionContract,/office_engine_m2:TestWorkbookVersionState \
    --stop-after-init --no-http --log-level=test \
    --logfile=docs/implementation/evidence/CB-M2-CB-02/cb02_amendment_targeted_20261108.log
  ```

  结果：20 个测试方法，0 failed / 0 errors，退出码 0。
- 完整升级与回归：

  ```sh
  ./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u office_engine_m2,office_engine_odoo \
    --test-enable --test-tags /office_engine_m2,/office_engine_odoo \
    --stop-after-init --no-http --log-level=test \
    --logfile=docs/implementation/evidence/CB-M2-CB-02/cb02_amendment_full_20261108_retry1.log
  ```

  两个模块升级并加载成功；215 个测试方法启动，`tests.result` 为 0 failed / 0 errors。1 个既有 browser-backed RPC 测试因缺少 `websocket-client` SKIP，214 个其余方法运行通过；完整套件包含 M1 Mapping、RenderBridge、Document Request 与附件权限回归。模块图另有 3 个不可安装 addon 被跳过，不计为测试方法。
- 统计口径：同一完整日志的 `tests.stats` 分别报告 M2 228、Odoo Request 27，合计 255；日志有 215 个 `Starting Test`，最终 `tests.result` 215。M2 的 192 个方法/18 个类与 Odoo 的 23 个方法/2 个类，共 20 类；`OdooSuite` 将每类 `setUpClass`、`tearDownClass` 各作为统计记录，因此 `255 - 215 = 40` 是生命周期统计，不是额外测试方法。以 `Starting Test` 与 `tests.result` 作为实际测试方法数证据，统计分析详见 IHR-012。
- 真实并发复测：runner 使用两个独立 Odoo backend（PID 52121、52122）竞争同一 parent/revision。恰有候选 337 成为 current；候选 338 保持 verified、非 current，重试明确返回 `WORKBOOK_VERSION_STALE`。Current=Last Valid=337，Document Revision=2；附件绑定与 SHA 检查通过。唯一标记的合成链 `CB02-AMEND-ACCEPT-RACE-20261108-01` 按负责人授权保留。证据：`evidence/CB-M2-CB-02/cb02_amendment_concurrency_20261108.log`。
- 8091 恢复：系统 Python 启动缺少 `emoji` 依赖，首次恢复尝试 HTTP 500；该进程已停止。改用项目 `venv/bin/python`、原 `odoo.conf`、原 `odoo18ce` 与 8091 参数成功启动，PID 52279，`/web/login` 返回 HTTP 200。没有修改配置或探测 PostgreSQL。失败诊断保存在 `/private/tmp/odoo_8091_restored_20261108.log` 与 `debug_logs/odoo_181.log`。
- SHA-256：首次失败日志 `d00c6c70ca5e0561b4eacae03696c1726804e142017c41e1113485bfb6bb1bb9`；定向通过 `34e4534b280036b06b8e62a2cfd54b5a18d51dc072d9cb21f51dcb64debcd9ae`；全量通过 `21eaf8402b2e0f20392b609211adce5fbadeeee86fed9a1612e039afc2691aa9`；双连接并发 `45c25a7b28dc52fc903e00ebfc074f2dce4818c71c3cd6280fd530728530ca75`。
- Amendment disposition：**Integration Verified / ready for component acceptance**；原 CB-02 技术范围的 `Final Accepted` 决定保持不变。CC-04 可继续其下游实现。Production attachment retention/deletion 仍为独立 `Release Gate OPEN`；1 个 browser-backed RPC 测试仍为 SKIP/未验证，不宣称浏览器 E2E 通过。
