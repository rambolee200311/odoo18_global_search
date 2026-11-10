# IHR — CC-M2-CB-02 Workbook Version & Artifact Service

## 0. 文档治理

- 类型：Implementation History Record（仅记录已发生事实）
- 状态：**FINAL ACCEPTED — CC-M2-CB-02 scope**（负责人 2026-11-08 明确决定）；生产附件留存/删除仍为独立 `Release Gate OPEN`，browser-backed RPC 仍未验证
- Amendment follow-up：Candidate Acceptance / Intent Binding v0.1 已在获批的 `odoo18ce` 完成模块升级、完整 TransactionCase 与双连接竞争验收；实施事实见 IHR-012。该记录不扩大原 CB-02 Final Accepted 范围或生产 Release Gate。
- Coding Contract：[CC-M2-CB-02 v0.3](CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md)，原文保留；[v0.3.1 并发环境修订](CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md)，负责人批准
- TDD：[Office Engine M2 TDD V2.0.2](../design/TDD_office_engine_m2_v2.0.2.md)，FROZEN
- 实施基线：branch `main`，HEAD `f9801fca76f7c248a9cc823c583138ab0191b978`
- 起始工作区：`main...origin/main [ahead 1]`；存在既有 untracked 文档、证据、coverage 与 odoo-llm 服务/测试目录；均保留，不清理、不暂存、不提交。
- 执行者：Codex
- 日期：2026-11-06
- 环境观察：Python 3.11.9；Odoo 18.0；配置数据库名 `odoo18ce`、HTTP 端口 8091、addons 路径含 `mymodules`。8091 有 Python 进程监听；进程内加载模块身份未由本次检查证明。未重启服务。

## 1. Coding Contract 基线

范围和验收以 CC v0.3 为准；仅并发测试环境按负责人批准的 CC v0.3.1 修订执行，尤其是：

- 版本模型、独立 document revision、父链、current/last-valid、服务端 proof、原子接受、附件访问与不可变性。
- 历史恢复采用新 recovery candidate/version；父版本为当时 current，记录 source version；历史对象不变、旧确认不复用，适用的新确认由后续 CB-04 提供。
- CB-02 使用 tests-only Validator 替身证明服务端 proof 受理，不实现/不声称真实 CB-03 Validator。
- 真实数据库竞争须使用 v0.3.1 允许的负责人批准非生产测试环境、两个独立连接和专用合成记录；顺序 TransactionCase 不作为并发 PASS。
- 不调用 Provider、不向外发送工作簿或真实 Odoo 数据；不进入生产发布。

## 2. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC 修订 | 1 个窄范围并发环境修订（v0.3.1）；v0.3 原文未改 |
| Preservation Impact | Session、M1 request、ir.attachment 与首轮 M1 交付引用；模块升级及 Odoo/M1 回归已通过 |
| Deviation | Approved / documented: 负责人指示本 CC 不等待 SRS 修订；SRS 文件保持未修改 |
| Stop Condition | No（截至本记录） |
| Open Issues | 1：生产附件留存/删除政策仍未裁定，属于独立 Release Gate，不阻止 CB-02 技术验收 |
| 当前状态 | Implementation Complete; Odoo Integration Verified including approved real race; Ready for Final Acceptance |

## 3. 实施历史（仅追加）

### IHR-001 — 执行前基线及冻结裁定

- 时间：2026-11-06
- 阶段：Implementation
- Action：检查 `docs/AGENTS.md`、TDD V2.0.2、Implementation Plan V2.0.1、SRS V1.1.0、CC v0.2、目标模块清单、Git 状态及 Odoo/Python 配置；保留全部既有修改。负责人裁定遵循 TDD §5.4 历史恢复，并要求不因 SRS 阻止 CB-02。
- Reason：明确冻结契约、授权范围与真实代码/环境基线。
- Files / Components：本 IHR、CC v0.3（新增）；尚未修改生产代码。
- Contract Reference：CC §§2、3、5、6、8、9、10、12、13。
- Upstream Reference：TDD V2.0.2 §5.4；Implementation Plan V2.0.1 §0.2；SRS V1.1.0 §0.2、§13。
- Result：Completed（基线检查）；Implementation 继续。
- Deviation：负责人明确要求本 CC 不等待 SRS 修订；不修改 SRS，亦不据此授权 Provider 调用、真实数据外发或生产发布。
- Follow-up：验证命令及结果持续追加至 ATR；生产保留/删除策略保持 OPEN。

## 4. 当前实现摘要

- 新增 `office.workbook.version` 不可变版本记录、Session 内版本号/幂等键唯一约束、验证回执绑定字段、状态迁移、私有附件关系和 Finalize 引用。
- 新增当前用户 ORM 版本服务：M1 V1 登记、真实字节 SHA 读取、候选持久化、typed validation receipt 接收、原子接受、显式历史恢复为新子候选、授权元数据读取/列表、Finalize 交付引用登记。
- `office.mapping.session` 增加独立 Document revision/current/last-valid 指针及仅内部服务使用的行锁后 ORM 更新入口。新增 SQL 仅为 ACL 校验后的 `SELECT ... FOR UPDATE`；没有用 SQL 读取或改写业务字段。
- `office.document.request` 在受控生成事务中持久化 M1 readback 状态、policy、报告摘要、输入/输出 SHA 与 Session/Proposal revision。M1 已生成结果只在证明匹配实际请求和附件字节时才能登记为 V1。
- `render_bridge` 在 M1 输出已交付后，在同一保存点内登记 V1 并记录匹配 SHA 的附件/Thread 消息；版本登记失败时保留既有 M1 结果并明确返回 `legacy` 元数据，不伪称已进入版本谱系。
- 已新增 TransactionCase 覆盖 proof 伪造/绑定、V1-V3、恢复、current 指针、附件安全、Finalize 引用、M1 RenderBridge 接线及原有附件失败恢复。首次运行发现的夹具/签名/状态迁移问题已按 IHR-006 修复；授权后 18 项 CB-02 TransactionCase 和两模块完整回归均已实际运行。双连接竞争现已按负责人批准的 v0.3.1 通过真实 ORM/独立连接执行，结果见 IHR-008 与 ATR-RUN-006。
- 不实现真实 CB-03 Validator；生产候选 receipt 入口仍是同进程内部服务函数。tests-only receipt issuer 不在生产模块 import 路径中。

## 5. 实际变更清单

| 路径 | 状态 | 用途 |
|---|---|---|
| `docs/implementation/CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md` | 新增 | 按负责人决策冻结的实施契约 |
| `docs/implementation/CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md` | 新增 | 负责人批准的窄并发环境修订；v0.3 原文未覆盖 |
| `docs/implementation/IHR-M2-CB-02.md` | 新增 | 实施事实记录 |
| `docs/implementation/ATR-M2-CB-02.md` | 新增 | 自动化测试执行记录 |
| `mymodules/office_engine_m2/models/office_workbook_version.py` | 新增 | 版本元数据、不可变字段、状态和绑定约束 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 修改 | 独立 Document revision/current/last-valid 指针与锁后 ORM 推进 |
| `mymodules/office_engine_m2/models/ir_attachment.py` | 新增 | 版本附件与已关联 Finalize 附件私有/不可变保护 |
| `mymodules/office_engine_m2/services/workbook_version_service.py` | 新增 | M1 V1、候选、证明、接受、恢复、Finalize 引用和只读版本服务 |
| `mymodules/office_engine_m2/services/mapping_service.py` | 修改 | 有权限的版本摘要读取/列表包装 |
| `mymodules/office_engine_m2/services/__init__.py` | 修改 | 仅导出只读版本摘要服务，不导出 proof/accept API |
| `mymodules/office_engine_m2/services/render_bridge.py` | 修改 | M1 V1 登记及原交付附件/Thread 消息引用 |
| `mymodules/office_engine_m2/models/__init__.py` | 修改 | 注册新模型与附件扩展 |
| `mymodules/office_engine_m2/security/office_workbook_version_rules.xml` | 新增 | owner 与 allowed-company 全局 Record Rule |
| `mymodules/office_engine_m2/security/ir.model.access.csv` | 修改 | 新版本模型最小读/写/建 ACL，无删权 |
| `mymodules/office_engine_m2/__manifest__.py` | 修改 | 版本号递增并加载 Record Rule |
| `mymodules/office_engine_odoo/models/office_document_request.py` | 修改 | M1 回读证明、哈希与版本绑定的受控持久化 |
| `mymodules/office_engine_odoo/__manifest__.py` | 修改 | 版本号递增 |
| `mymodules/office_engine_odoo/tests/test_attachment_identity.py` | 修改 | M1 proof RPC 风格伪造拒绝与真实 readback 报告适配 |
| `mymodules/office_engine_m2/tests/__init__.py` | 修改 | 注册新 TransactionCase |
| `mymodules/office_engine_m2/tests/support/__init__.py` | 新增 | 合成 XLSX、Session 与 M1 回读夹具 |
| `mymodules/office_engine_m2/tests/support/validator_stub.py` | 新增 | 仅测试目录内创建 typed receipt/confirmation |
| `mymodules/office_engine_m2/tests/test_workbook_version_contract.py` | 新增 | V1 证明、V1-V3、幂等、伪造回执和旧 request legacy 测试 |
| `mymodules/office_engine_m2/tests/test_workbook_version_access.py` | 新增 | owner、company、Session 隔离及只读摘要测试 |
| `mymodules/office_engine_m2/tests/test_workbook_version_state.py` | 新增 | 原子推进/回滚、恢复、Finalize、附件不变性与失败状态测试 |
| `mymodules/office_engine_m2/tests/test_render_bridge.py` | 修改 | M1 生成后 V1 与正式交付关联回归 |
| `mymodules/office_engine_m2/tests/integration/test_workbook_version_race.py` | 修改 | 两独立连接竞态辅助器；仅接受 stale/SerializationFailure 冲突，其他异常判失败；使用连接 PID 与有限锁等待 |

白名单边界：没有修改 Odoo 官方模块、Provider/CB-01、`office_core`、`office_verify`、真实业务数据、SRS/TDD/Implementation Plan/其他 CC。仅新增已批准的 CB-02 v0.3.1 并发环境修订；新增访问接口仅提供授权后的摘要，不暴露 proof 接收、候选接受或任意附件字节 RPC。

## 6. 偏差、停止与基线变更

- SRS gate：负责人明确指示本 CC 不等待 SRS 修订。本轮不修改冻结 SRS；此实施记录不是 SRS 版本化变更，也不授权外部数据处理或生产发布。
- 历史恢复：按负责人选择遵循冻结 TDD §5.4，以新增 recovery version 实现；不修改 TDD。
- 生产数据附件保留/删除期限：未裁定；仅阻止生产启用，不用本轮合成数据测试代替该决策。

## 7. Open Issues

| ID | 问题 | 当前影响 | 关闭证据 |
|---|---|---|---|
| CB02-OPEN-01 | 最终生产附件保留/删除及版本生命周期政策未批准 | 不处理真实业务文件、不做生产发布；不阻止本 CC 合成数据验收 | 有权负责人批准的政策及 Release Gate 记录 |
| CB02-OPEN-04 | 真实数据库并发验收 | **CLOSED** — v0.3.1 amendment approved; real independent-connection race passed; approved synthetic lineage retained | ATR-RUN-006 and `evidence/CB-M2-CB-02/concurrency-run-20261107_authorized.log` |

## 8. 交接摘要

代码实现、静态检查、Odoo TransactionCase、模块升级、M1 回归和并发测试分别由 ATR 记录。当前两模块升级、全部必需 TransactionCase、M1/附件回归及真实并发均有执行证据。CB-02 已提交 **READY FOR FINAL ACCEPTANCE**；最终接受决定仍由负责人作出。生产附件留存/删除政策继续是独立 Release Gate OPEN。

### IHR-002 — 版本服务实现与静态验证

- 时间：2026-11-06
- 阶段：Implementation
- Action：在 CC v0.3 白名单内完成版本模型、受控 ORM 服务、M1 proof 持久化、M1 V1 登记、版本摘要读取、Finalize 附件/消息引用和附件保护；增加合成数据 TransactionCase。
- Reason：建立 V1→Vn 的私有谱系与服务端 proof/原子接受边界，且不替代 CB-03 Validator。
- Files / Components：见 §5 实际变更清单。
- Contract Reference：CC §§3–10；TDD V2.0.2 §§5.1–5.4、§8.1。
- Result：实现与静态检查完成；Odoo TransactionCase、模块升级及 DB 并发验证 `BLOCKED / NOT RUN`。
- Deviation：实现后代码审查识别出冻结契约中版本摘要读取和 Finalize 引用接线尚未落地。为满足既定接口，补写对应 TransactionCase 后再完成实现；这些增补测试未能在同一轮运行，因此实际行为仍待 Odoo registry 验证。该范围没有扩展到 CB-03/04/05/06 的生产集成。
- Evidence：ATR §5 Run 001；Python `py_compile`、manifest AST、XML 解析、`git diff --check` 均 PASS；数据库 readiness 检查 `127.0.0.1:5555 - no response`。8091 仍有 Python 进程监听，本轮未重启。
- Follow-up：先在安全可用的隔离 Odoo 测试环境运行 TransactionCase 和升级兼容性测试；再在 disposable DB 执行真实并发竞争。此前不得标记 Odoo Integration Verified 或 Final Accepted。

### IHR-003 — PostgreSQL 端点与隔离测试环境只读核查

- 时间：2026-11-07
- 阶段：Integration Readiness
- Action：只读核查 8091 进程启动配置路径、工作目录、Odoo 配置中的数据库目标、PostgreSQL 监听状态、可见服务管理信息及仓库内测试配置文件。
- Evidence：8091 PID 4295 的参数为 `-c odoo.conf`，进程工作目录为本仓库；该配置指定 `db_host=127.0.0.1`、`db_port=5555`、`db_name=odoo18ce`、`db_user=odoo`、`http_port=8091`。配置内存在数据库密码，但本记录未读取或披露其值。`lsof` 未显示 5555 的监听者，只显示 PID 4295 及另一 Python 进程到该端口的既存 TCP 会话；`pg_isready -h 127.0.0.1 -p 5555` 返回 `no response`。8091 仍监听，未重启。`launchctl list` 未找到 PostgreSQL/Postmaster/PgBouncer 匹配项；Docker CLI 不存在；仓库文件清单中只发现 `odoo.conf`，没有隔离测试数据库配置。`pg_ctl status -D /Library/PostgreSQL/16/data` 因数据目录 PID 文件权限被拒绝，无法确认本机 PostgreSQL 16 实例状态。
- Result：根因**未完全确认**。已确认当前端口没有可观察到的监听者且新探测无响应；既存 TCP 会话可能是残留/失效会话，不能证明 PostgreSQL 仍可用。现有证据无法区分服务停止、转发/代理失效或其他端点变更。由于数据库不可探测，无法确认任何可用且获准的隔离数据库；也没有读取数据库目录或列举数据库。
- Safety：没有建立数据库连接、执行 SQL/ORM 查询、创建/修改数据库或业务数据；没有启动/停止 PostgreSQL、没有重启 8091。工作区既有改动保持。
- Follow-up / Gate：需先由负责人/环境管理员确认并授权在隔离环境恢复或提供 PostgreSQL 测试端点；其后只在获准的 disposable DB 上运行模块安装/升级、TransactionCase、M1 回归及独立连接并发测试。若需创建 DB，先由负责人授权创建独立数据库和临时测试服务；不使用 `odoo18ce`，也不从共享业务库复制真实数据。完成上述门禁前，CC-02 保持 `Implementation Complete; Odoo Integration Pending`。

### IHR-004 — 负责人授权后的服务身份复核及集成门禁

- 时间：2026-11-07
- 阶段：Integration Readiness
- Decision：负责人授权在 `odoo.conf` 指定的 `odoo18ce` 上执行 CB-02 集成测试，不要求另建 DB；同时明确不得违反冻结 CC v0.3 的测试边界，并要求服务恢复操作如影响其他会话须先确认。本决策允许在安全条件满足后使用该数据库，不等于已确认其当前可用或已授权重启服务。
- Evidence：`launchctl print system/postgresql-16` 显示 system LaunchDaemon 状态为 `running`、PID 842、程序 `/Library/PostgreSQL/16/bin/postgres -D /Library/PostgreSQL/16/data`、运行用户 `postgres`。`/Library/LaunchDaemons/postgresql-16.plist` 的只读字段确认服务身份、`RunAtLoad=true`、`KeepAlive=false`。但 `pg_isready` 对 TCP `127.0.0.1:5555`、`127.0.0.1:5432`、`::1` 及 `/tmp` socket 5555/5432 均返回 `no response`。当前用户上下文的 `lsof` 未显示 PostgreSQL TCP listener；由于服务属于其他用户，这不是 listener 不存在的确定证据。数据目录权限为 `postgres` 专有；无法读取 `postgresql.conf` 或 `postmaster.pid`，`sudo -n -u postgres` 因需要密码而未执行读取。8091 PID 4295 使用 `odoo.conf`；PID 4295 与 pgAdmin PID 6868 均显示到 5555 的既存 TCP 会话。
- Evidence：`launchctl print system/postgresql-16` 显示 system LaunchDaemon 状态为 `running`、PID 842、程序 `/Library/PostgreSQL/16/bin/postgres -D /Library/PostgreSQL/16/data`、运行用户 `postgres`。`/Library/LaunchDaemons/postgresql-16.plist` 的只读字段确认服务身份、`RunAtLoad=true`、`KeepAlive=false`。但 `pg_isready` 对 TCP `127.0.0.1:5555`、`127.0.0.1:5432`、`::1` 及 `/tmp` socket 5555/5432 均返回 `no response`。当前用户上下文的 `lsof` 未显示 PostgreSQL TCP listener；由于服务属于其他用户，这不是 listener 不存在的确定证据。数据目录权限为 `postgres` 专有；无法读取 `postgresql.conf` 或 `postmaster.pid`，`sudo -n -u postgres` 因需要密码而未执行读取。8091 PID 4295 使用 `odoo.conf`；PID 4295 与 pgAdmin PID 6868 均显示到 5555 的既存 TCP 会话。Odoo 日志中另有多条 `psycopg2.errors.SerializationFailure: could not serialize access due to concurrent update`，但未取得对应事务时间/归属，不作为当前活动事务或本任务根因证据。
- Result：已确认目标 PostgreSQL 服务身份，但**未确认监听配置、服务内部健康状态或 5555 无响应的具体根因**。LaunchDaemon 的 `running` 只证明进程由 launchd 管理，不证明数据库接受连接。`pg_isready` 证明当前检查方式无法通过这些测试端点获得响应；实际 socket 目录尚未知。重启该服务可能中断 8091 Odoo 和 pgAdmin 的既存会话；在负责人确认具体重启动作前不执行。
- CC 并发边界：复核冻结 CC v0.3 §10，明确真实数据库竞争必须在独立 disposable test DB 上执行，并禁止在共享开发/生产库执行。负责人本次授权使用 `odoo18ce` 不修改该验收条款，因此在 `odoo18ce` 上执行此竞争测试状态为 **CONTRACT CHANGE REQUIRED**；未获契约修订批准前不执行，也不以顺序模拟替代并发 PASS。
- Result / Safety：本次未连接 `odoo18ce`、未读取数据库表/事务、未升级模块、未运行 TransactionCase 或并发测试、未启动/停止/重启 PostgreSQL/8091。仅追加 IHR/ATR 文档。
- Follow-up / Gate：需要环境管理员以 PostgreSQL 服务账号提供监听配置及健康状态，或授权并确认一个具体的服务重启动作（包括可能中断 PID 4295 和 6868 会话的影响）。服务可连接后，先只读核验目标 DB、模块版本、模块状态、相关模型/表结构和活动事务，再静态审查升级钩子/迁移影响，方可执行已授权升级与回归。并发测试仍需要符合 CC §10 的 disposable DB，除非负责人正式批准最小 CC 变更。

### IHR-005 — 8091 ORM 可用性与模块升级失败诊断

- 时间：2026-11-07。
- 阶段：Integration Readiness / Upgrade Attempt。
- Action：使用当前已认证的 8091 Odoo Web 会话只读查看 Settings、Technical → Database Structure → Models、Apps 模块信息；随后按负责人授权从 Apps 页面升级 `office_engine_odoo`。
- ORM 可用性证据：Settings 页面成功读取配置界面；Technical → Models 能通过当前 Odoo 请求检索 `office.mapping.session` 元数据及字段；Apps 能读取两个目标模块的安装信息。这证明现有 8091 请求路径中的 ORM 可用，不能推断 PostgreSQL 接受新的独立客户端连接。
- Runtime/registry 证据：当前 `office.mapping.session` 技术模型字段列表未出现工作区新增的 `document_revision`、`current_version_id`、`last_valid_version_id`；模块详情仍显示已安装版本 M2 `18.0.26.0.13`、Odoo Request `18.0.1.4.1`。工作区清单为 M2 `.14` 与 Odoo Request `.2`。
- Upgrade Attempt：从 Odoo Apps 页面调用 `office_engine_odoo` 的 Upgrade。Odoo 返回真实 RPC_ERROR，依赖模块加载在读取 `office_engine_m2/security/ir.model.access.csv` 时失败：`No matching record found for external id 'model_office_workbook_version' in field 'Model'`。工作区 `mymodules/office_engine_m2/models/__init__.py` 已导入 `office_workbook_version`，并且新模型源码存在；当前升级 registry 未提供该模型外部 ID。模块信息随后仍显示旧安装版本，故升级未达到成功状态。错误强烈指向 8091 当前已加载的 Python/registry 未包含工作区新增模型；不得据此声称数据库或 ORM 不可用。
- Safety：未重启 8091/PostgreSQL，未通过 SQL/cursor 查询或修改业务数据，未手工编辑任何模块记录。Upgrade 调用因服务器异常未成功；没有 TransactionCase 断言运行。没有尝试绕过 Odoo 模块加载。
- Concurrency：冻结 CC v0.3 §10 仍要求 disposable/isolated DB；本次负责人对 `odoo18ce` 的授权未改变该条款。并发验收单独保持 `CONTRACT CHANGE REQUIRED`，不阻断非并发测试。
- Follow-up / Gate：要让新模型代码进入 Odoo registry 并执行隔离/回滚 TransactionCase，需要先恢复对配置 PostgreSQL 端点的新连接，再重启 8091 以载入工作区代码；这两项均涉及已说明的服务会话中断风险，未执行。审批后使用同一 `odoo.conf` 的受控测试命令完成升级与测试；若只批准 PostgreSQL 重启，不能据此宣称 M2 新代码已载入或升级通过。

### IHR-006 — 负责人授权后的 Odoo 集成验收

- 时间：2026-11-07。
- 阶段：Odoo Integration / Regression。
- Decision：负责人授权使用当前仓库 `odoo.conf` 的 `odoo18ce` 执行 CB-02 模块升级、TransactionCase、M1 与附件权限回归；随后明确授权重启 8091，并要求停止重复检查 PostgreSQL/5555。本轮依指令未再执行 PostgreSQL 工具或端口探测。
- Action：先在 8091 已停止的测试窗口中由已认证 UI 触发模块升级，再运行 `-u office_engine_m2,office_engine_odoo` 和两模块 Odoo TransactionCase；修复测试发现的 CB-02 状态迁移与夹具问题、更新两个 M1 测试 mock 的 `version_binding` 签名；完成完整重跑后重启 8091。UI 点击的返回本身不作为升级完成证据；以 CLI 模块加载日志和完整 Odoo 测试结果为准。
- Findings / Changes：
  - `candidate_received → partially_verified` 现可登记部分验证结果。`accept_verified_candidate` 仍要求状态及回执均为 `VERIFIED`，因此部分验证不会推进 current/last-valid 指针。
  - 测试夹具不再要求普通内部用户创建 `res.partner`，复用自身可读 partner；跨公司访问测试复用既有公司，不新增公司业务设置记录；错误字节附件绑定测试 Session，使测试能覆盖 finalize mismatch 校验而不绕过附件 ACL。
  - M1 Private Skill 与 RenderBridge 测试替身接收并断言 `version_binding`；生产 M1 接口和权限逻辑未为测试放宽。
- Evidence：完整 Odoo 测试日志报告 `0 failed, 0 error(s) of 203 tests`，并实际记录 203 个 `Starting Test` 事件；18 个 CB-02 TransactionCase 全部运行。目标模块更新命令日志显示 `office_engine_odoo`、`office_engine_m2` 均加载并完成 registry rebuild。M1 Private Skill/RenderBridge 定向回归为 23 项、0 failed、0 error。详细命令、日志路径和统计差异见 ATR-RUN-005 与 `docs/implementation/evidence/CB-M2-CB-02/`。
- Runtime：测试完成后 Odoo 8091 已按授权重新启动，PID 35158 监听端口；已认证浏览器 Thread/Inbox 可加载并显示连接恢复。该检查仅证明 Web 服务可访问，不作为 Provider/Browser E2E。
- Preserved first failure：首次完整 TransactionCase 运行记录为 1 failed、19 errors；日志保留。失败根因及后续定向测试、完整重跑结果均追加在 ATR，不覆盖历史事实。
- Unresolved：`tests.stats` 为 M2 214、Odoo 27 与 203 个 `startTest()` 结果的差异已由 Odoo `OdooSuite` 的 class setup/teardown 统计解释（M2 34 条、Odoo 4 条）；实际 test skip 为 1 项（缺 websocket-client），其余 202 项 0 failed/0 error。冻结 CC §10 并发仍 `NOT RUN`；若在共享库运行，提交后版本历史不可用普通 ORM 清理，因此需要负责人裁定是否允许保留专用合成测试链并批准最小契约修订，或继续要求 disposable DB。生产附件留存策略仍 OPEN。
- Safety：只使用已授权共享 DB、当前 Odoo ORM/TransactionCase 机制及合成测试数据；没有真实业务记录更新、Provider 调用或 Git stage/commit/push/reset/clean。模块升级产生的模型/视图/ACL 元数据更新属于本次明确授权的升级动作。
- Result：Odoo module update、CB-02 TransactionCase、M1/附件权限回归 **PASS（集成测试层，完整结果 203 started / 202 未跳过 / 1 SKIP / 0 failed / 0 errors）**；stats 差异 **RESOLVED**；真实数据库并发 **NOT RUN**。不提交 `READY FOR FINAL ACCEPTANCE`，因为并发条款和共享库不可清理的测试数据风险仍待负责人裁定。

### IHR-007 — ATR-RUN-005 统计口径复核与并发契约修订请求

- 时间：2026-11-07。
- 阶段：Evidence reconciliation / concurrency gate。
- Action：只读核对保留的最终完整 Odoo 日志、Odoo 测试统计源码、冻结 CC §10 和现有竞态 helper；未重新运行测试、未访问数据库或检查 PostgreSQL/5555、未修改冻结 CC。统计分析见 `evidence/CB-M2-CB-02/test-count-analysis-20261107.md`；并发契约与 helper 审查及未批准的最小修订建议见 `evidence/CB-M2-CB-02/concurrency-contract-review-20261107.md`。
- Test count：最终日志记录 M2 180、Odoo Request 23、共 203 个 `Starting Test`；测试 ID 203 个唯一，无重复；1 项 Browser-backed RPC 用例因 `websocket-client module is not installed` 跳过；其余 202 项未跳过，测试结果 0 failed / 0 error。`tests.stats` 的 214/27 多出的 34/4 条分别等于 M2 17 个与 Odoo Request 2 个 TestCase 类的 `setUpClass`/`tearDownClass` 统计。`OdooTestResult.startTest()` 计数与 `OdooSuite` 把类生命周期写入 stats 的实现证据见 `odoo/tests/result.py`、`odoo/tests/suite.py`，详细解析存于 `evidence/CB-M2-CB-02/test-count-analysis-20261107.md`。统计差异结论：**RESOLVED；241 不是实际测试方法数**。
- Concurrency contract：冻结 CC v0.3 §10 明确要求 disposable/isolated Odoo test DB，顺序 TransactionCase 不足以证明竞争。建议仅将“并发测试数据库限制”改为以下窄条款，不改变业务验收：

  > 经负责人书面批准，可在非生产 Odoo 开发/测试数据库使用专用、可识别的合成 Session、Version 与 Attachment 执行并发验收。测试必须通过两个独立 Odoo cursor/transaction 同时竞争相同 parent 与 Document Revision；测试前确认目标 Session/Thread 为测试专用且没有活动业务操作；设置有界等待并在发生意外冲突时中止。验证恰好一个候选接受，另一候选因明确的 stale/revision 冲突被拒；任何其他异常均判为测试失败。核验 current/last-valid/revision 与附件归属一致，且没有测试范围外变更。测试后必须回滚或清理测试记录；若版本/附件不可变约束使清理不可能，只有在负责人另行明确批准保留带唯一标识的合成测试版本链后，才可在该开发/测试 DB 执行，否则仍须使用 disposable DB。不得运行于未授权的生产 DB，不得用顺序调用替代并发证据。

- Cleanup constraint：当前 `office.workbook.version.unlink()` 明确拒绝删除，版本附件也不可变；真实竞争需要 winner commit，因此无法通过随后回滚 winner 事务清理该版本链。负责人需在“批准保留仅含合成数据、带唯一标识的测试版本链并接受上述窄修订”与“维持清理要求、改用 disposable DB”之间作出决定。现有 `odoo18ce` 普通集成测试授权不包含这项数据保留或 CC §10 修订授权。
- Existing race helper review：`tests/integration/test_workbook_version_race.py:12-38` 使用 `threading.Barrier(2)` 与两个 `registry.cursor()`，可提供真实独立连接的并发起点；但 helper 将任意 `Exception` 归类成 `rejected`，没有断言败方必须因 stale/revision 冲突被拒。因此即使运行前，也需在获批范围内将“预期冲突类型与其他异常区分”作为测试判定条件；本轮没有修改或执行 helper。
- Result：统计差异关闭；浏览器 RPC skip 如实保留；并发 **BLOCKED / OWNER DECISION REQUIRED**。本记录不构成契约批准或并发执行授权。

### IHR-008 — 已批准并发修订及真实双连接验收

- 时间：2026-11-07。
- 阶段：Concurrency Integration / Closeout。
- Decision：负责人回复“批准最小修订并允许保留合成版本链”。据此新增 [CC-M2-CB-02 v0.3.1 并发环境修订](CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md)，保留 v0.3 原文，仅允许在明确批准的非生产 `odoo18ce` 使用唯一标记合成链，并在版本/附件不可变导致无法清理时保留该链；其他并发验收要求不变。
- Action：先以 ORM 搜索确认唯一测试 Thread tag 不存在；使用 `base.user_admin` 的普通 Odoo 用户环境创建专用合成 Thread、Session、V1 和两个 `VERIFIED` 候选。提交 fixture 后，通过两个独立 `registry.cursor()` / 独立数据库后端并发接受同一 V1/Document Revision 的不同候选。每连接设置 10 秒 `lock_timeout`、30 秒 `statement_timeout`；未重启 Odoo/PostgreSQL，未运行完整测试，不调用 Provider。
- Runner correction evidence：首次 `odoo-bin shell` 在调用 Registry/ORM 前因 Odoo shell 的 `server.start()` 进程枚举触发 sandbox `PermissionError`，保存在 `concurrency-run-20261107_shell-permission-failure.log`；改用不启动服务的 Registry ORM runner。后续两次启动分别因 evidence 脚本缺少 repo `sys.path`、随后缺少 `mymodules` 导入路径失败，记录于 `concurrency-run-20261107.log` 与 `_retry1.log`，均发生在数据库写入前。未提权直连 ORM 尝试因沙箱 `Operation not permitted` 记录于 `_retry2.log`；按已授权动作使用受控沙箱外 ORM 执行后通过。
- Race result：测试 Thread `13850`、Session `10612`、V1 `101`、候选 `102`/`103`。真实数据库 backend PIDs `37490` 与 `37491` 不同。候选 `103` 唯一 commit 并成为 `accepted_current`；另一候选 `102` 的原并发事务以 PostgreSQL `SerializationFailure: could not serialize access due to concurrent update` 回滚。随后以新事务重试候选 `102`，服务返回 `WORKBOOK_VERSION_STALE`。这一区分记录为“数据库并发冲突 + 后续 stale 重验”，不把 SerializationFailure 伪写成应用层 stale 错误。
- State/readback：最终 current 与 last-valid 均为 `103`，Document Revision `2`，V1 `101` 为 `superseded`；败方 `102` 保持非 current 的 `verified` 状态。只读 ORM 回读确认恰好 3 条版本、3 个版本输出附件，parent/input/attachment binding 一致，无孤立版本附件；3 个附件 SHA-256 均匹配，并通过 ZIP integrity 与 `openpyxl` 独立读取。完整 IDs、SHA 和断言见 `evidence/CB-M2-CB-02/concurrency-lineage-readback-20261107.log`。
- Evidence：实际并发输出见 `evidence/CB-M2-CB-02/concurrency-run-20261107_authorized.log`；只读回读见同目录 `concurrency-lineage-readback-20261107.log`。合成链唯一标识 `CB02-CONCURRENCY-APPROVED-20261107-01`，按批准保留；未修改真实业务记录、未调用 Provider。
- Result：真实双连接并发 **PASS**；统计差异 **RESOLVED**；历史单项 browser RPC skip 继续如实记录。CB-02 其余已授权测试证据见 ATR-RUN-005，完整收口见 ATR-RUN-006。当前可提交 **READY FOR FINAL ACCEPTANCE**，不得由 Codex 自行标为 Final Accepted。生产附件留存/删除政策仍为独立 Release Gate OPEN。

### IHR-009 — 最终验收证据索引与状态核对

- 日期：2026-11-08。
- 核对：复查冻结 CC v0.3 与已批准的 v0.3.1 并发环境修订、ATR-RUN-005/006、模块升级/TransactionCase/M1 日志、真实双连接竞态日志、只读版本与附件回读及测试统计分析。
- 结论：CC §10 的 disposable-only 环境限制已由负责人批准的 v0.3.1 窄修订替代；竞态实际在获准的非生产 `odoo18ce` 上通过独立 Odoo cursor/事务执行。没有未批准的契约偏差。203 个测试方法启动，202 个未跳过，1 个 browser-backed RPC 测试因缺 `websocket-client` 跳过，0 failed / 0 errors；241 是 Odoo 测试统计行数而非测试方法数。
- 交付：逐项验收证据、日志 SHA-256 和残留边界见 [FINAL_EVIDENCE_INDEX_20261107.md](evidence/CB-M2-CB-02/FINAL_EVIDENCE_INDEX_20261107.md)。
- 状态：证据支持 **READY FOR FINAL ACCEPTANCE**；负责人尚需单独记录 `Final Accepted` 决定。生产附件留存/删除仍是独立 `Release Gate OPEN`；browser-backed RPC 路径仍未验证。

### IHR-010 — 负责人正式 Final Acceptance 决定

- 日期：2026-11-08。
- Owner Decision：负责人对“CC-02 是否作出正式 Final Accepted 决定”选择批准（选项 1）。
- Basis：ATR-RUN-005/006、`FINAL_EVIDENCE_INDEX_20261107.md` 及已批准的 v0.3.1 并发环境修订；本次不重跑测试，不修改代码或冻结验收标准。
- Disposition：**CC-M2-CB-02 Final Accepted — 限定于 CB-02 技术范围**。先前的 READY 状态及“待负责人决定”均作为历史事实保留，不删除或改写历史运行记录。
- Open boundary：生产附件留存/删除政策仍为 `Release Gate OPEN`；1 个 browser-backed RPC 测试仍为 SKIP/未验证。该决定不授权生产发布。
- Dependency effect：满足 CC-M2-CB-03 的 CB-02 最终状态前置条件；不替代 CB-03 自身的数据范围与执行授权。

### IHR-011 — Candidate Acceptance / Intent Binding Amendment 实施与集成门禁

- 日期：2026-11-08。
- 授权：负责人批准先使 TDD V2.0.3、Implementation Plan V2.0.2 与 CB-02 Candidate Acceptance / Intent Binding Amendment 生效，并先实施/验收该 Amendment，再继续 CC-04。范围限于合成 Candidate；不调用 Provider、不处理真实附件、不重启 8091、不升级正在服务 8091 的实例、不执行 Git 写操作。
- 本轮涉及的实现：`office.workbook.version` 增加逐轮 `intent_message_id`、接受授权审计字段及 `verified → rejected` 状态迁移；版本服务要求 edit/restore Candidate 绑定经当前 ORM 权限核验的真实用户 Thread 消息；edit Candidate 接受需要与 Candidate、Session、owner、Thread、Intent、parent、Document revision、Output SHA、Effect digest 和用户决策消息绑定的 typed authorization；拒绝只改变被拒 Candidate，不推进 Current/Last Valid/Document Revision。确认回执引用纳入幂等请求比较，防止同一幂等键换回执后复用旧 Candidate。
- 测试准备：扩展 Candidate acceptance/confirmation/rejection、跨 Thread 消息、确认引用幂等及附件 SHA 不变断言；更新双连接竞态 runner，使其用每个 Candidate 的真实用户 Review 消息构造当前 API 所需授权。历史竞态日志未改写。
- 静态证据：定向 `python3 -m py_compile` 覆盖模型、版本服务、TransactionCase/support 和竞态 runner，退出码 0；`git diff --check` 退出码 0；9 个相关 Python 文件行尾空白检查 PASS。完整命令和状态见 ATR-RUN-007 及 `evidence/CB-M2-CB-02/cb02-amendment-static-20261108.log`。
- Odoo 集成状态：**NOT RUN / BLOCKED**。此前批准的 `odoo18ce` 与当前 8091 服务实例关联；本次授权明确禁止升级正在服务 8091 的实例。没有识别或使用其他已授权隔离数据库；未进行数据库探测或连接，未升级模块，也未运行 TransactionCase。
- 状态：CB-02 Amendment 本地实现未取得 Odoo ORM 集成证据；因此不提交该 Amendment 的 Final Acceptance，也不解除依赖它的 CC-04 集成编码门。
- 最小后续环境决策：提供一个已可用且获授权的非生产隔离 Odoo 数据库，或授权创建一个全新、空白、仅含合成数据的专用测试数据库。不能以对 8091 服务数据库做模块升级替代。

### IHR-012 — Amendment ORM 验收、并发复测及 8091 恢复

- 日期：2026-11-08。
- 授权：负责人明确决定不新建数据库、使用 `odoo18ce`，并授权短暂停止 8091、升级目标模块、运行合成数据测试后恢复服务。遵守不访问真实业务记录、不调用 Provider、不检查 PostgreSQL/5555、不执行 Git 写操作的边界。
- 首次完整运行：命令按两模块完整 Odoo 测试入口执行，退出码 1；保留 [`cb02_amendment_transactioncase_20261108.log`](evidence/CB-M2-CB-02/cb02_amendment_transactioncase_20261108.log)。日志实际启动 214 个测试方法，结果为 0 failed / 11 errors。根因已逐项确认：6 个 subTest 将 Odoo TransactionCase 的 `assertRaises` 传入异常元组导致 `TypeError`；4 项 Candidate Review 使用 PostgreSQL 事务时间与 Python `created_at` 跨时钟比较而误判；1 项 FAILED Candidate 测试未携带 typed authorization，提前在授权门失败而未触达被测状态规则。
- 修复：在不可变 `office.workbook.version` 上记录 Candidate 创建时当前 Thread 最后消息水位；服务端只接受水位之后、作者/Thread/用户均有效的 Candidate Review/Reject 消息。该记录由受控 ORM 服务建立，字段只读且校验 Thread 归属。回归测试覆盖 Candidate 创建前已有的旧 Review/Reject 消息不能授权新 Candidate。异常断言改为明确捕获允许的 `AccessError`/`ValidationError` 类型；FAILED 状态测试使用完整 scoped authorization 触发状态拒绝。
- 定向集成：重新升级 `office_engine_m2` 并运行 `TestWorkbookVersionContract`、`TestWorkbookVersionState`；实际 20 个测试方法，0 failed / 0 errors，退出码 0。证据：[`cb02_amendment_targeted_20261108.log`](evidence/CB-M2-CB-02/cb02_amendment_targeted_20261108.log)。
- 完整集成：`-u office_engine_m2,office_engine_odoo --test-enable --test-tags /office_engine_m2,/office_engine_odoo --stop-after-init --no-http` 实际升级并加载两个目标模块。日志记录 215 个 `Starting Test`，`tests.result` 为 0 failed / 0 errors / 215；其中 1 个既有 Browser-backed RPC 测试因缺少 `websocket-client` 为 SKIP，其余 214 项执行且通过。M1 Mapping/RenderBridge/Document Request/附件路径在全套中回归；该被跳过的浏览器/JS 用例仍未验证。证据：[`cb02_amendment_full_20261108_retry1.log`](evidence/CB-M2-CB-02/cb02_amendment_full_20261108_retry1.log)。
- 统计口径：同一日志 `tests.stats` 为 `office_engine_m2: 228`、`office_engine_odoo: 27`，合计 255；`tests.result` 的 215 是 `startTest()` 实际测试方法数。日志中 M2 实际 192 个方法/18 个 TestCase 类，Odoo Request 实际 23 个方法/2 个类；`OdooSuite` 另把各类 `setUpClass` 与 `tearDownClass` 作为 36+4 条 stats 记录计入，故 `255 - 215 = 40` 可由 20 个测试类各 2 条生命周期统计解释。3 个非 installable addon 的 module-graph skip 不计入测试方法。`tests.result` 为测试总数依据。
- 并发复测：通过双独立 Odoo backend PID `52121` 与 `52122` 对同一 parent/revision 竞争；唯一赢家 Candidate `337`，Current=Last Valid=`337`，Document Revision=`2`；败方 Candidate `338` 保持 verified 非 Current，重新接受明确得到 `WORKBOOK_VERSION_STALE`。附件归属及输出 SHA 检查通过。仅使用合成 Thread/Session/版本/附件，不调用 Provider。按既有负责人授权保留唯一标识版本链 `CB02-AMEND-ACCEPT-RACE-20261108-01`。证据：[`cb02_amendment_concurrency_20261108.log`](evidence/CB-M2-CB-02/cb02_amendment_concurrency_20261108.log)。
- 服务恢复：最初以系统 Python 启动时，Odoo 日志显示 `ModuleNotFoundError: No module named 'emoji'`，登录页 HTTP 500；该进程已停止。随后用项目 `venv/bin/python`、相同 `odoo.conf`、`odoo18ce` 和 8091 参数启动；新 PID `52279` 监听，GET `/web/login` 返回 HTTP 200。无 PostgreSQL 探测或配置修改。启动诊断日志见 `/private/tmp/odoo_8091_restored_20261108.log` 与 `debug_logs/odoo_181.log`。
- 结果：CB-02 Amendment 的模块升级、完整 Odoo TransactionCase 与双连接竞争均有真实通过证据；**Amendment Integration Verified / ready for component acceptance**。原 CB-02 技术范围 `Final Accepted` 决定保持不变。该依赖门按负责人授权的顺序满足，CC-04 可继续执行。生产附件留存/删除 `Release Gate OPEN`、browser-backed RPC SKIP 均未被本次测试改变。
