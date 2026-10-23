# Odoo 通用 Office 文档自动化引擎 M1 TDD 补充：Spawn 导入与内存边界

<!-- TDD 结构参考：docs/skill/odoo-project-workflow/references/templates/Designing/TDD模板.md；模板同步检查 PASS（2026-10-22） -->

| 字段 | 内容 |
|---|---|
| 补充编号 | `TDD-OFFICE-ENGINE-M1-SPAWN-RECOVERY` |
| 文档版本 | V0.1 |
| 状态 | **Draft — 待评审；不授权实施** |
| 适用基线 | SRS V1.0.0 Frozen；TDD V0.4 Frozen；M1 TV Plan V1.0.0 Frozen |
| 证据输入 | TV Office Engine M1 Spawn Recovery Report，2026-10-22，Partial |
| 关联实现/问题 | CC-OFFICE-M1-004 `CC-TEST-007 FAIL`；`CC-TEST-006 BLOCKED`；Odoo `spawn` 模块导入与 4 GiB 内存限制 |
| 计划基线 | Implementation Plan V0.4 Frozen；本补充获批冻结后须作影响评审并建立新计划基线 |

> 本文件补充而不覆盖 [TDD V0.4](TDD_office_engine_m1_v0.4.md)。它保留 TV 实测的成功、失败与不确定状态，不修改 SRS 验收含义、CC-004/005 历史记录或产品代码。本文仍为 Draft，未经评审批准不得作为 CC 或实现依据。

## 1. 目的与范围

解决当前 M1 同步服务的两个运行时阻断：

1. Odoo addon 在父进程中以 `odoo.addons.office_core.*` 动态模块名加载，而 `multiprocessing` 使用 `spawn` 创建全新解释器时无法按该名称重新导入，导致 `ModuleNotFoundError`。
2. 当前 Core worker 用 `RLIMIT_AS` 应用 4 GiB 限制；在本机 macOS Python 已占用约 475 GB 虚拟地址空间时，4 GiB 限制不能设置，服务 fail-closed。

本补充只定义受信任的 worker 导入契约、内存监控策略候选、超时/清理行为、测试与启用门禁。它不增加 Office 功能、不开放新文件结构、不改变 Mapping Plan、不改变 SRS 或产品权限语义，也不引入 Queue Job、Redis、Celery 或外部服务。

## 2. 技术验证基线与事实

详见 [TV Spawn Recovery Report](../verification/TV_Office_Engine_M1_Spawn_Recovery_Report.md) 与关联证据。关键事实如下：

| 观察 | 状态 / 证据边界 |
|---|---|
| 将可信 `mymodules` 根目录加入普通 Python 导入路径后，`office_core.service` / `office_verify.service` 在 spawn 子进程中以一致顶层模块身份导入 | 候选导入方式已验证；不是当前 Odoo 动态模块身份 |
| 顶层 `office_core.service.inspect_document` 的 spawn 已越过模块导入并到达内存预算检查 | 该次 4 GiB `RLIMIT_AS` 在 macOS 失败；未证明通过现有 Core API 完成 Office 处理 |
| 通过外部 RSS 采样并终止的临时 spawn harness 处理最小无公式 XLSX 和基础 DOCX，独立 Verify 均 PASS | 候选策略可行性证据；不代表当前 Core 公共 API、Odoo ORM 或复杂模板通过 |
| 96 MiB 受控内存增长测试三次均被终止，峰值超过阈值约 2.2–5.3 MiB | RSS 监控有超调，属于软性停止阈值，不是内核硬限制；试验规模不足以推导生产余量 |
| `office.document.request._render_request_sync` 在 `odoo18ce` 仍失败，状态 `failed / OFFICE_ENGINE_FAILED / inspect`，无输出附件 | CC-004 成功交付仍 FAIL；shell 身份为 `uid=1, env.su=True`，普通用户权限未验证 |
| Linux 部署目标未确认 | 不得将本机 macOS 结果外推到 Linux |

上述状态是补充设计输入，不是对 CC-004 / CC-005 的回填或豁免。

## 3. Spawn 导入与消息契约

### 3.1 目标约束

- Worker target 必须定义在 spawn 子进程可通过**固定、普通 Python 模块名**导入的模块中。不得把 `odoo.addons.*` 动态模块名作为 spawn target 或 pickle 数据类的唯一导入地址。
- 父、子进程必须对 Worker target 与跨进程类型使用同一模块身份；禁止同一消息在父进程使用顶层包、子进程使用 `odoo.addons.*` 的混合身份。
- Worker 只接收有界 `bytes`、字符串、有限数字、布尔、列表和 JSON 对象等普通序列化值。禁止传递 Odoo `env`、ORM recordset、cursor、attachment/request 模型实例、Provider 对象或回调。
- 进程返回值采用普通序列化值或由同一固定模块名导入的数据契约；错误只回传稳定错误码、阶段和脱敏文案，不回传 traceback、文件路径或业务内容。
- worker import 根必须来自 Odoo 已配置的可信 Addon 部署路径。不得接受请求、附件、Mapping Plan 或用户上下文提供的导入路径；发现路径解析歧义、非预期包来源或模块名冲突时 fail closed。
- 不改用 `fork`，不依赖父进程的 `sys.modules` 状态，不用 Monkey Patch 修正 pickle，不把 `sys.path` 中用户可写目录作为受信任路径。

### 3.2 建议的最小实现边界（待评审）

优先评估将 Worker API 作为 `office_core` 下的普通 Python 模块入口，由受控 Odoo 适配器在调用前解析并核验固定 Addon 根路径；父子使用相同的顶层包名。为避免 Odoo 动态包和顶层包同时被使用造成类身份分裂：

1. `office_engine_odoo` 适配器不得把 `odoo.addons.office_core` / `odoo.addons.office_verify` 中加载的 Python 对象传入 Worker。
2. 若服务父进程使用普通顶层导入，则同一纯 Python 服务路径、数据类和错误类型也必须使用该普通身份，不得混合导入。
3. 模块初始化不得执行 Odoo ORM、创建全局运行状态、读取业务数据或启动进程。
4. 实际模块加载来源与 `sys.modules` identity 必须在真实 Odoo shell 及 spawn 子进程中验证；单独 Python 探针不替代 ORM 成功路径。

本节描述 TV 支持的优先候选，不将模块布局细节视为已冻结。若真实 Odoo addon 加载导致双身份、重复副作用或升级风险，应先修订本补充，不得以隐式 alias 或 monkey patch 绕过。

### 3.3 禁止路径

- 不使用 `fork`/`forkserver` 替代 `spawn`，除非新的 TV 评估 Odoo 线程、数据库连接、锁和目标平台并获批 TDD 修订。
- 不在 provider/chat 路径中传入任意可导入模块名、目录或 callable。
- 不直接把 Odoo 动态 addon module object、异常类或 ORM 对象 pickle 给子进程。
- 不以“本地顶层导入通过”作为 Odoo 成功交付证据。

## 4. 内存、超时与进程清理

### 4.1 当前限制

`RLIMIT_AS` 不得被写为当前跨平台可用的 4 GiB 硬限制。macOS 的 Python VMS 明显高于该值，实际设置会使正常工作进程在解析前被拒绝。`RLIMIT_RSS` 不能未经目标平台实测就视为有效替代。

### 4.2 RSS 监督候选

候选方案为父进程对单个 `spawn` worker 进行 RSS 采样；超过批准阈值时立即 `terminate`，宽限期后仍存活则 `kill`，随后 `join` 并确认子进程退出。内存不可观察、pid 无效、监控异常或清理失败时按资源限制错误拒绝，不允许返回部分候选。

RSS 采样有观察间隔和终止竞态，不是内核硬上限。实际内存峰值可能超过阈值。不得把 96 MiB 探针结果直接当成生产余量，也不得从小文件中推导最大输入规模。实现若采用 RSS 监督，必须：

1. 在 TDD/Implementation Plan 中明确采样间隔、阈值、留给采样/终止超调的安全余量及该余量的实测依据。
2. 使用代表性最大输入与内存增长样本测峰值、检测延迟、终止延迟、退出确认和父/子进程总 RSS；覆盖 Odoo Worker 本身的预算影响。
3. 通过真实目标 Odoo/Python/OS 运行时验证 Core 与 Verify 两条 worker 路径；分别证明正常负载不误拒绝、超预算可终止、监控不可用时拒绝。
4. 若部署环境要求严格 OS 级硬内存上限而 RSS 采样无法满足，不得开放同步文件处理；应提出平台隔离策略并单独评估，不得静默取消限制。

TV 的临时原型显示 `office_verify` 内置 RSS 采样路径在本机可运行；这不意味着 Core 已实现或自动满足本节。

### 4.3 墙钟超时和临时资源

- 每次 inspect/render/verify 均有有限墙钟时限；超时后终止 worker、关闭 Pipe/FD、回收进程，并清理该请求专属临时资源。
- 进程异常退出、无消息、pickle 错误、回读失败或清理失败均映射为稳定失败状态，不可交付候选文件。
- 不允许为观察异常而无期限等待、无限重试或在 Odoo 请求事务中保留业务记录锁。
- 异步调度不是本补充的补救方案；首期仍按同步 TDD 处理，超出批准预算的请求明确拒绝。

## 5. Odoo 调用与事务边界保持不变

1. `office.document.request` 继续在短事务校验当前用户、输入附件及请求上下文，并提交请求状态。
2. 无状态 worker 只接收已经授权的有界内容快照及 Mapping Plan，不接收 `env`、uid、附件 ID、路径或业务记录访问能力。
3. 文件处理阶段不持有业务锁。输出附件只能在核心候选生成且独立 Verify PASS 后创建；提交前重验请求、输入摘要、授权和状态。
4. worker spawn/import/资源限制错误必须进入失败路径；请求最终状态不能留下有效输出附件；下载权限不扩张。
5. 失败/回滚时数据库授权立即失效、物理文件依 Odoo 原生 GC 延迟回收的既有已批准语义保持不变。

本次 TV 仅观察了失败闭环，未验证新的导入/内存实现下附件创建、提交、跨用户下载拒绝、幂等并发和事务耗时；这些仍需新的 remediation CC 证据。

## 6. 实施与验证要求

实施前必须有新的冻结 Implementation Plan 与独立修复 CC。最小验证矩阵：

| 编号 | 必须覆盖的验证 | 通过条件 |
|---|---|---|
| `TEST-SPAWN-001` | 静态与子进程导入路径核验 | `office_core`/`office_verify` worker target 在 spawn 中从固定可信来源以一致身份导入；不依赖 Odoo 动态 loader 或用户可写路径 |
| `TEST-SPAWN-002` | 父子序列化契约 | 只传输白名单基础类型；无 Odoo recordset/env/cursor；正常返回及稳定错误均可往返 |
| `TEST-SPAWN-003` | 资源监控正常路径 | `.xlsx`/`.docx` 合成样本在目标批准的 RSS/时限预算内完成 inspect、candidate render 与独立 Verify |
| `TEST-SPAWN-004` | 超内存、超时、采样不可用、进程异常 | 在资源阈值/时限内外产生确定、可观测的拒绝；被终止子进程全部回收；无部分可交付文件 |
| `TEST-SPAWN-005` | 真实 Odoo ORM 成功路径 | `odoo-bin shell -c odoo.conf -d odoo18ce` 使用获准合成附件完整完成 Core→Verify→附件交付；正确状态、哈希和唯一结果；新 shell 验证附件授权与清理 |
| `TEST-SPAWN-006` | 权限/幂等回归 | 普通非 superuser owner 可按规则读取；非 owner 被拒；同 UUID 并发仅一个有效输出；失败无下载 |
| `TEST-SPAWN-007` | 目标平台兼容 | 对明确目标 OS/Python/Odoo/PostgreSQL 重跑导入、RSS、timeout 与 ORM 路径；报告不能跨平台外推 |

所有测试绑定代码 commit、Odoo/Python/PostgreSQL/OS、配置和样本 SHA-256。开发库只用当前批准的 `odoo18ce`，不新建隔离库；不使用 `sudo()` 代替普通用户权限测试。自动测试、权限测试、人工 UI 验证状态分别记录，不把源代码级/临时探针 PASS 替代真实 Odoo 成功路径。

## 7. 错误语义

| 条件 | 错误码 | 要求 |
|---|---|---|
| Worker target / 契约模块不可导入或身份冲突 | `OFFICE_ENGINE_FAILED` | 失败关闭；无输出附件；日志记录阶段和脱敏模块 identity 摘要 |
| RSS 不可观测、超过预算或强制终止失败 | `OFFICE_RESOURCE_LIMIT` | 不返回候选；记录阈值、采样/终止数据；标注资源风险 |
| 超出时限 | `OFFICE_RESOURCE_LIMIT` | 终止、join、清理；不返回部分结果 |
| Odoo 附件授权/输入变化/事务交付失败 | 既有 `OFFICE_DELIVERY_FAILED` / 授权处理 | 无链接，不改变既有权限边界 |

任何面向普通用户的错误不得暴露 traceback、绝对路径、pid、其他用户标识、附件数据或内部部署路径。

## 8. TDD 决策与待决事项

| ID | 决策/事项 | 当前提出方案 | 证据与剩余工作 | 状态 |
|---|---|---|---|---|
| `TD-SPAWN-001` | spawn import identity | 固定可信 Addon 根导入普通 Python worker API；父子同一模块名；拒绝动态 Odoo addon 名作为 pickle 契约 | 本机顶层导入候选通过；仍需真实 Odoo 适配器的 module identity/升级验证 | Draft proposal |
| `TD-SPAWN-002` | IPC 数据模型 | 仅用有界 bytes 和基础 JSON 数据；错误序列化为稳定字段 | 本轮探针通过基础对象 pickle；请求/结果生产契约需实现测试 | Draft proposal |
| `TD-SPAWN-003` | macOS RSS 策略 | 评估父进程 RSS 监控 + 实测 headroom + 超限终止；不宣称硬上限 | 三次小型 kill probe 通过但存在超调；缺目标负载与预算 | Open; TDD freeze review required |
| `TD-SPAWN-004` | Linux 生产预算 | 必须在目标环境按独立 OS 证据决定资源策略 | 目标 Linux 未提供，当前 INCONCLUSIVE | Open; production enablement blocked |
| `TD-SPAWN-005` | CC-004 成功交付 | 必须重新完成 Odoo Core→Verify→Attachment 输出成功路径 | 本轮失败并无输出；需 remediation CC | Open; CC-004 FR NOT SATISFIED |

## 9. 冻结门禁及范围说明

本补充可在 TV 总体 Partial 的情况下评审，但冻结前必须：

1. 评审通过 `TD-SPAWN-001` 的固定导入机制、模块 identity 与包初始化风险，不得仅靠一次普通 Python 导入推断 Odoo 运行时可行。
2. 确定当前开发环境的资源限制方案及失败关闭口径；如果选择 RSS 监督，记录其软限制属性和超调风险，不得称硬内存限制。
3. 明确 Linux 目标未确认的生产门禁范围；不因此阻塞本机受控开发修复，但不得宣称生产准入。
4. 保持 CC-004 FR `NOT SATISFIED`、CC-005 handoff `BLOCKED/INCONCLUSIVE`、CC-006 `BLOCKED`，无豁免时不允许修改状态。
5. 本补充冻结之后，对 Implementation Plan V0.4 执行影响分析并形成新 Draft 计划；新计划经批准冻结前不得创建 remediation CC 或实施。

TDD 补充冻结只确立设计，不授权改代码。修复 CC 必须单独评审、冻结并由负责人明确授权后实施。

## 附录 A. 变更记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-22 | Draft | 基于 TV Spawn Recovery Report 起草；提出普通 Python spawn identity 与 RSS 监督策略；不修改 TDD V0.4、不授权实施 |
