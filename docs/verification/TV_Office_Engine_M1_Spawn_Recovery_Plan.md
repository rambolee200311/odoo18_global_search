# Office Engine M1 Spawn Worker 恢复技术验证计划

| 项 | 值 |
|---|---|
| 文档状态 | **V1.0.0 Frozen — 负责人于 2026-10-22 批准执行技术验证；不授权产品修复** |
| 版本 | V1.0.0 |
| 日期 | 2026-10-22 |
| 验证对象 | CC-OFFICE-M1-004 的 worker 导入和内存边界阻塞 |
| 已知调查 | [Spawn 导入与内存边界调查](TV_Office_Engine_M1_Spawn_Import_Investigation.md) |
| 运行环境约束 | 项目 `venv`、`odoo.conf`、现有 `odoo18ce`；不建立隔离数据库 |
| 批准记录 | 负责人于 2026-10-22 批准冻结并执行本 TV Plan；范围限于 §1，不修改产品代码/依赖 |

## 1. 目标与边界

本 TV 只验证以下技术问题，为 TDD 补充提供事实：

1. 如何让 `office_core` 与 `office_verify` 的受限 worker 在 Python `spawn` 新解释器中稳定导入，且父子进程使用一致的数据契约。
2. 如何在目标开发环境中对 worker 实施可观察、有效、失败关闭的内存和超时限制；修复 import 后不能退化为无界处理。
3. 上述路径能否在 Odoo 18 运行环境中调用真实 `inspect → render candidate → verify` 关键路径，并由 Odoo 持久层按既有事务/权限契约完成合成附件成功交付。

本 TV 不实现正式产品功能、不修改冻结 SRS/TDD、不改写 CC-004/005 历史状态、不安装或升级依赖、不调用真实 LLM Provider、不改官方 Odoo/Odoo-LLM 代码。Odoo 集成只使用授权的 `odoo18ce` 和合成附件；不使用 `sudo()` 作为权限验证替代。

## 2. 当前已知事实

- CC-004 ATR-RUN-004：真实 ORM 成功路径在 spawn 反序列化 `odoo.addons.office_core` 时失败；CC-004 FR `NOT SATISFIED`。
- 当前 Odoo shell 中 addons 根目录在 Odoo 的动态 `odoo.addons.__path__`，但不在 `sys.path`；模块身份是 `odoo.addons.office_core.*` / `odoo.addons.office_verify.*`，顶层 Python `find_spec` 无结果。
- 把 `mymodules` 显式加入普通 Python `sys.path` 后，顶层 `office_core.service` target 可在 spawn 子进程导入；本机探针随后在 `RLIMIT_AS` 阶段失败，因此未证明文件处理成功。
- 当前 macOS Python 虚拟地址空间约 475 GB；8 GiB `RLIMIT_AS` 无法应用。`office_verify` 中有 RSS 观测代码，但尚未证明可直接满足 `office_core` 当前预算契约。
- CC-005 handoff 仍 `BLOCKED/INCONCLUSIVE`。本 TV 不实现或宣称 handoff 通过。

## 3. 验证环境与固定输入

| 项 | 执行约束 |
|---|---|
| Python/Odoo | 执行时记录 `venv` Python、Odoo 版本、macOS 版本、PostgreSQL 版本 |
| Odoo 配置/DB | `odoo.conf`、既有 `odoo18ce`；运行前后核对服务和数据库状态 |
| 模块基线 | 记录根仓库与所有相关 Addon 的 commit、工作树状态；不得把 dirty 状态称为可复现基线 |
| 样本 | 仓库内获准的 `xlsx` / `docx` 样本及合成最小文件；记录 SHA-256、Mapping Plan 与预期输出 |
| 外部调用 | Provider 全部 mock 或不调用；真实外部 HTTP 请求数必须为 0 |
| 数据清理 | 唯一标记的合成 request/attachment 使用 ORM 清理并在新 shell 核对；不得手工删除 filestore 文件 |

依赖版本保持当前库存，不安装/升级库。若环境或样本与计划不符，记录 `INCONCLUSIVE`，不调整基线掩盖差异。

## 4. 验证矩阵

| ID | 问题 | 方法 | 通过标准 | 失败处置 |
|---|---|---|---|---|
| TV-SPAWN-001 | 普通 Python 包身份是否可被 spawn 重导入？ | 以显式、可信的 Addon 根路径引导普通 Python 包名；在新 spawn 进程中核验 target、数据模型、序列化请求/响应均来自同一模块身份；分别覆盖 core 与 verify | 新进程不依赖 Odoo addon 动态导入器；无重复类身份/反序列化错误；父子路径确定且不接受用户输入路径 | 不把 `sys.path` 全局污染或不稳定别名作为产品方案；转入其他独立 worker entry 设计并追加 TV |
| TV-SPAWN-002 | 内存预算能否在 macOS 实施？ | 对 `RLIMIT_AS`、进程 RSS 采样及其他仅限进程的候选方案做最小实验；模拟持续内存增长；量化采样间隔、超限峰值、停止延迟；观测/限制不可用时检查是否拒绝 | 目标预算有效；超限后在声明界限内停止；观测失败、杀进程失败或策略不支持时拒绝处理；报告实际 RSS 峰值及限制误差 | 不能证实有界时，不开放 worker；不得取消限制或把极大限值写成 PASS |
| TV-SPAWN-003 | 有界内存策略是否仍可完成合成 Office 操作？ | 使用获准合成 `.xlsx` / `.docx` 运行 inspect、candidate render、独立 verify；输入/输出哈希和预期 Mapping 目标明确；非法输入与预算超限做失败注入 | 合成合法路径完成；verify PASS 后才生成候选摘要；非法/超预算路径有稳定失败且无残留/伪成功 | 任一能力未证实即记录失败/不确定，不能从单一格式外推 |
| TV-SPAWN-004 | Odoo ORM 关键成功链路是否可在真实运行时完成？ | 在 `odoo18ce` 用当前用户和唯一标记合成附件调用既有 `office.document.request` 同步接口；核验输入授权、状态、core→verify、输出附件关联、当前用户可读、非 owner 拒绝；新 shell复核成功结果；清理合成数据 | 当前用户成功生成且回读 PASS；只产生一个有效输出附件；失败注入没有输出；权限/事务/清理符合冻结 TDD | 不满足则 CC-004 保持 `NOT SATISFIED`；保留日志和状态，先修正技术设计/实现契约 |
| TV-SPAWN-005 | 是否可对 macOS 结果外推到目标 Linux？ | 若部署目标已确定，在对应 Odoo/Python/Linux runtime 重复 TV-SPAWN-001/002/003 的必要子集 | 逐平台给出独立结果、版本和预算数据 | 未测平台保持 `INCONCLUSIVE`；不作跨平台承诺 |

## 5. 候选策略比较约束

TV 可以比较下列候选，但不得在测试前视为已批准设计：

1. 将纯 Python worker 作为普通可导入包使用，并从 Odoo 可信 Addon 路径解析模块位置；验证 module identity、路径污染、升级和安装布局。
2. 提供独立的 Odoo 无关 worker entry package；验证它只接收有界序列化数据，不导入 ORM、Provider 或用户数据。
3. 比较地址空间硬限制与父进程 RSS 监控/终止策略；监控策略必须测量超限峰值与检测延迟，不能仅因 `office_verify` 已使用就直接复用。
4. 更换 `spawn` 启动方式（例如 `fork`）属于架构改变候选；必须先评估 Odoo 线程/数据库连接/锁状态、macOS 与 Linux 的安全风险。没有实验证据和冻结 TDD 批准时不得实施。

## 6. 证据与产出

批准执行后，在 `docs/verification/evidence/TV_Office_Engine_M1_Spawn_Recovery/` 保存脱敏证据：环境快照、每个候选的命令/退出码、worker import identities、资源监控数据、合成样本哈希、Odoo 成功/失败结果及清理核验。报告写入 `docs/verification/TV_Office_Engine_M1_Spawn_Recovery_Report.md`，按每个 TV ID 标为 `VERIFIED`、`NOT VERIFIED` 或 `INCONCLUSIVE`。

报告必须把“导入成功”“内存边界有效”“Office 操作成功”“Odoo 输出附件交付成功”分开判定；任何一项不能由另一项替代。不得重写原 TV 报告、CC-004 ATR/FR 或 CC-005 ATR/FR。

## 7. 完成门禁与后续顺序

1. TV 计划经负责人批准冻结后，才执行完整计划范围。
2. TV 报告明确 worker import 和跨平台内存策略的可行性及限制后，修订独立 TDD 补充；评审冻结后再更新并冻结 Implementation Plan 新版本，登记 remediation CC 和 Phase 5 Resume CC。
3. 针对 CC-004 成功链路的 remediation CC 必须单独评审、冻结和授权；完成后按原合同可适用的 CC-TEST 重测并评估 FR，不覆盖历史 FAIL。
4. 只有 CC-004 成功链路有合格证据后，才实施/运行 Phase 5 Resume 的独立 handoff 和 Provider payload 验证。
5. Phase 5 完整 Gate PASS、计划影响复核通过后，方可冻结并实施 CC-006。

任何 TV 结果不支持当前设计时，停止并修订 TDD；不得以用户希望进入 Phase 6 为由更改 TV 结果或绕过安全/资源门禁。

## 附录 A — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-22 | Draft | 根据 CC-004 spawn/import 与本机 RLIMIT_AS 调查起草；不授权执行完整验证。 |
| V1.0.0 | 2026-10-22 | Frozen | 负责人批准冻结并执行；范围仅限 worker 导入、资源限制及合成 Odoo 成功路径验证，不授权产品修复。 |
