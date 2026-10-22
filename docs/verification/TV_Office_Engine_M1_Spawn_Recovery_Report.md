# Office Engine M1 Spawn Worker 恢复技术验证报告

| 项 | 记录 |
|---|---|
| 报告状态 | **执行完成；总体结论 Partial / Gate 未通过** |
| 计划基线 | [TV Plan V1.0.0 Frozen](TV_Office_Engine_M1_Spawn_Recovery_Plan.md)；负责人于 2026-10-22 批准执行 |
| 执行日期 | 2026-10-22 |
| 验证环境 | 项目 `venv`、`odoo.conf`、现有 `odoo18ce`；macOS ARM64 |
| 目标 | 定位并验证 CC-OFFICE-M1-004 的 spawn 导入、内存边界和 Odoo 合成文件成功交付链路 |
| 代码/依赖变更 | 无；没有安装或升级依赖，没有修改产品代码 |
| 外部 Provider 请求 | 0 |
| CC 状态影响 | 不改写 CC-004/005 历史；CC-004 FR 仍 `NOT SATISFIED`，CC-005 handoff 仍 `BLOCKED/INCONCLUSIVE` |

## 1. 执行摘要

本轮验证**没有关闭 CC-004 成功链路门禁**。直接通过 Odoo 的 `office.document.request._render_request_sync` 执行时，spawn 子进程仍无法反序列化 `odoo.addons.office_core`，请求被 fail-closed 地持久化为 `failed`，没有输出附件。

另用不改产品代码的独立 Python 探针验证了一个候选方向：把 `mymodules` 作为受信任的普通 Python 导入根后，spawn 子进程能以统一的 `office_core.*` / `office_verify.*` 模块身份导入；受父进程 RSS 采样和终止监督的临时 worker 可处理本次合成的基础 `.xlsx`、`.docx` 并通过独立回读。这个结果是**候选策略的技术可行性证据**，不是当前产品服务的 PASS，也没有证明生产级 RSS 硬上限。

`RLIMIT_AS` 在当前 macOS Python 运行时不能用于 4 GiB 核心预算：进程地址空间约 475 GiB，官方服务调用按预期拒绝运行。最新 RSS 试验显示监控器三次均终止超限子进程，但检测时 RSS 超出 96 MiB 阈值约 5.9–7.1 MiB；因此只能证明失败关闭和终止链路可工作，不能宣称严格硬上限或生产安全边界已满足。

## 2. 环境与基线

| 项 | 实测值 |
|---|---|
| Git HEAD | `19499b84a9b62b1ee5561fae81c3ff33d4fc64ca` |
| Office 源码工作树 | `mymodules/office_core`、`mymodules/office_verify`、`mymodules/office_engine_odoo` 在执行快照时无本地变更；全仓库存在其他既有脏/未跟踪文件，未暂存、未提交 |
| Odoo | `18.0`；Addon `office_engine_odoo` 已安装，版本 `18.0.1.1.0` |
| Python | `3.11.9`，项目 `venv` |
| 操作系统 | `macOS-27.0.1-arm64-arm-64bit` |
| 解析器依赖 | `openpyxl 3.1.5`、`python-docx 1.1.2`、`lxml 4.9.3`；仅记录现有版本，未安装/升级 |
| PostgreSQL | `16.14`，本机 `x86_64-apple-darwin24.6.0` 服务端构建 |
| 数据库 | `odoo18ce` |
| Odoo shell 身份 | `uid=1`, `env.su=True`；因此本次不是普通业务用户 ACL/Record Rule 的成功路径验证 |
| `RLIMIT_AS` | soft/hard 均为 `9223372036854775807`；受测 Python 进程 VMS 约 `475,345,338,368` bytes，RSS 约 17 MiB（既有调查快照） |
| Odoo 核心内存预算 | `_MAX_MEMORY_BYTES = 4,294,967,296` bytes（4 GiB） |
| 依赖 | 不变；既有环境快照见 [探针证据](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-001-004-python-probe.json) |

详细环境快照：[TV-SPAWN-environment-snapshot.json](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-environment-snapshot.json)。

## 3. 验证矩阵与结果

### TV-SPAWN-001 — spawn 导入身份

**结果：部分候选已验证；Odoo 集成导入仍失败。**

- 在新 spawn 解释器中预置受信任的 `mymodules` 根目录后，`office_core.service`、`office_core.models`、`office_verify.service` 和 `office_verify.models` 均按普通 Python 包成功导入；探针退出码为 0，身份一致。
- 这与 Odoo 进程中 `odoo.addons.office_core.*` 的动态模块身份不同。既有 Odoo 子进程不能从父进程继承 Odoo 动态 addon 导入器；本次 ORM 探针再次复现 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`。
- 将受信任 addon 根映射为普通 Python 包是可继续设计的候选，不代表可以直接把全局 `sys.path` 改动当成产品方案；TDD 仍需定义固定、可信、父子一致的入口与包身份。

证据：`spawn_identity` 节、`existing_core_public_inspect` 节及 Odoo traceback，见 [Python 探针 JSON](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-001-004-python-probe.json) 和 [Odoo 探针结果](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-004-odoo-result.json)。

### TV-SPAWN-002 — macOS 内存边界与 RSS 监督

**结果：`RLIMIT_AS` 方案未通过；RSS 候选可观察并能终止，但不能宣称硬上限已满足。**

- 通过现有 `office_core.service.inspect_document` 使用 4 GiB 预算时，worker 返回 `OFFICE_RESOURCE_LIMIT / worker_limits`，消息为“当前运行环境无法落实调用方声明的内存上限，已拒绝处理”。
- 对 RSS 监督原型以 96 MiB 阈值进行 3 次受控内存增长测试，三次都检测超限并终止子进程，子进程退出码 `-15`，结束后均不存活。
- 最新证据采样到的超限值为约 103.0、103.1、101.9 MiB，超过 96 MiB 阈值约 7.0、7.1、5.9 MiB；从启动到终止约 226–258 ms。该时间包含 spawn 启动、内存分配和监控，不是纯检测延迟。采样/kill 存在竞态与峰值超调，RSS 不是内核硬限制。
- 现有 `office_verify.verify_output` 在人为设置 1 byte RSS 上限时返回 `OFFICE_RESOURCE_LIMIT / worker_limits`，证明低预算下拒绝路径生效；在 512 MiB 预算下，本次小型合成文件回读通过。
- 不能将 Verify 的监控实现直接视为 Core 已有同等保护；核心现行公共 API 仍使用 `RLIMIT_AS`，也没有经过本次修改。

### TV-SPAWN-003 — 合成文件处理候选

**结果：当前公共 Core API 未通过；RSS 监督候选下的基础 `.xlsx` / `.docx` 读写和独立回读通过。**

| 样本 | 操作 | 结果 | 实测 worker RSS 峰值 | 说明 |
|---|---|---|---:|---|
| 合成 `.xlsx` | inspect → 1 个白名单字符串写入 → `office_verify.verify_output` | 候选 PASS | inspect 约 49.4 MiB；render 约 49.2 MiB | 无公式、单工作表、两个简单单元格；独立回读 1 个目标，公式数 0 |
| 合成 `.docx` | inspect → 1 个普通段落写入 → `office_verify.verify_output` | 候选 PASS | inspect 约 57.9 MiB；render 约 68.4 MiB | 由既有基础段落/表格测试辅助函数生成；不覆盖复杂文本框、图片或版式 |

两种候选路径均在脚本外部的 RSS 监督 spawn worker 中调用 `office_core.engine` inline 解析/渲染，然后调用独立 Verify 服务；不是调用当前 Core 的 `_run_worker`。因此它证明的是方案候选可以工作，不证明当前产品 Worker 可运行。样本 SHA-256、候选 SHA-256、耗时和进程数据记录在 [Python 探针 JSON](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-001-004-python-probe.json)。

### TV-SPAWN-004 — Odoo ORM 成功交付链路

**结果：FAIL（核心成功门禁仍未满足）；失败输出正确关闭并清理。**

- 在现有 `odoo18ce`、当前 Odoo shell 环境中，用唯一标记创建一个合成 `.xlsx` `ir.attachment`，构造明确的 Mapping Plan，并调用 `office.document.request._render_request_sync`。
- 真实 spawn bootstrap 在反序列化 target 时抛出 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`。
- ORM 包装层将请求持久化为 `failed / OFFICE_ENGINE_FAILED / inspect`；`output_attachment_id=False`，未创建可下载输出。该结果验证失败关闭路径，不证明成功交付。
- 初次清理脚本因误用 `env.cr.invalidate_all()` 而未完成清理。随后用唯一 marker 找到且只清理该测试的 1 个 request 和 1 个附件，使用 ORM 提交删除；未直接操作 filestore。另开全新 Odoo shell 确认该 request UUID 与附件名均为 0 条。修正后的重跑也在 `finally` 中完成 ORM 清理。
- 测试身份 `uid=1, env.su=True`，普通业务用户的 ACL、Record Rule、其他用户拒绝和成功下载仍未验证。
- 无 Provider/外部 HTTP 调用；没有 Odoo schema 迁移或代码修改。

证据：[TV-SPAWN-004 Odoo 结果](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-004-odoo-result.json)、[Odoo 探针脚本](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-004-odoo-shell-probe.py)、[新 shell 环境及清理快照](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-environment-snapshot.json)。

### TV-SPAWN-005 — Linux 目标环境

**结果：INCONCLUSIVE / 未执行。**

当前没有已确认的 Linux 部署目标及其 Python/Odoo/内存预算，不能在 macOS 结果上推定 Linux 的 `RLIMIT_AS`、RSS 监控或 worker 行为。目标环境确认后仍须按计划重复相应子集。

## 4. 汇总状态

| 验证项 | 状态 | 对当前产品的结论 |
|---|---|---|
| TV-SPAWN-001 导入 | 候选入口可导入；现有 Odoo 动态身份失败 | 未解决当前 ORM worker 导入错误 |
| TV-SPAWN-002 内存 | `RLIMIT_AS` 失败；RSS 监督原型可杀进程但有超调 | 需要 TDD 选择并定义有界策略；不能称生产可用 |
| TV-SPAWN-003 Office 核心路径 | 独立监督原型下基础样本通过 | 当前核心公开服务没有成功证据；真实复杂模板也未覆盖 |
| TV-SPAWN-004 ORM 成功交付 | FAIL；持久失败状态、无输出，清理 PASS | CC-004 成功交付仍未满足 |
| TV-SPAWN-005 Linux | INCONCLUSIVE | 不作跨平台结论 |

**整体判定：Partial，且 CC-004 关键成功链路 FAIL。** 本报告不覆盖原始 CC-004 ATR/FR，也不将候选探针结果回填为原 CC 的 PASS。

## 5. 对 TDD 的影响与必须处理的设计问题

1. Worker 必须在独立解释器中使用确定且一致的普通 Python 模块身份。TDD 补充需比较可信包根引导/独立 worker entry 等方案，并规定禁止来自用户输入的导入路径、禁止把 Odoo `env` 或 ORM 对象传入 worker。
2. macOS 上不得继续把 `RLIMIT_AS=4 GiB` 写成有效限制。若采用 RSS 监督，TDD 必须定义采样周期、超限安全余量、超限时终止与等待流程、无法采样时 fail-closed、父子进程清理以及“RSS 有超调，不是内核硬上限”的风险处置。
3. RSS 原型的 96 MiB 测试显示最高观测约 105 MiB。应用策略需要以阈值留出经过负载测试的 overshoot/headroom；本次 3 个小探针不足以确定生产预算。
4. 基础 `.xlsx/.docx` 的候选操作可在隔离进程模型下完成，但 `.xlsx` 公式、真实 CMR/销售模板、复杂 Word 对象、最大体积与并发尚未由本次探针证明。
5. Odoo ORM 请求状态和失败路径可工作，但成功附件创建/关联、附件可读、非 owner 拒绝、幂等重复请求以及普通业务用户权限必须在成功 worker 实现后重测。
6. 必须明确目标 Linux 部署环境；macOS 本地数据不能替代目标运行时证据。

## 6. Gate 与后续顺序

1. 保持 CC-004 FR `NOT SATISFIED`；CC-005 handoff 继续 `BLOCKED/INCONCLUSIVE`；CC-006 不得冻结或实施。
2. 基于本报告起草 TDD 补充，冻结前明确模块导入身份、跨平台内存策略、失败关闭和终止清理契约。不得把 RSS 原型描述成生产硬限制。
3. 在 TDD 补充冻结后，起草新的 Implementation Plan 基线，明确先修复 CC-004 成功路径、再单独恢复 Phase 5 handoff 的顺序和门禁。
4. 创建独立 remediation CC 修复 worker import 与内存限制，并验证 Core→Verify→Odoo output attachment 全成功链路。该 CC 冻结并实施后，按契约重跑失败用例；历史 FAIL 保留。
5. CC-004 成功链路闭环后，再由独立 CC 验证 Phase 5 handoff 和 Provider 隔离；Phase 5 完整 PASS 后才能进入 CC-006。
6. Linux 目标未确认前，报告限定为当前开发环境技术证据，不声明生产部署准入。

## 附录 A — 证据文件

- [受限 Python spawn 探针脚本](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-001-004-python-probe.py)
- [受限 Python spawn 探针 JSON 结果](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-001-004-python-probe.json)
- [Odoo ORM 合成请求探针脚本](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-004-odoo-shell-probe.py)
- [Odoo ORM 探针结果与清理记录](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-004-odoo-result.json)
- [环境与新 shell 清理核验快照](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-environment-snapshot.json)
- [两次 ORM 探针的最终新 shell 清理核验](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-final-cleanup-check.json)
- [ORM 清理探针脚本](evidence/TV_Office_Engine_M1_Spawn_Recovery/TV-SPAWN-cleanup-orm.py)

所有数据库探针均使用当前 Odoo shell 环境，不使用 `sudo()`、隔离数据库、真实业务附件或真实 Provider。全仓库原有脏状态未暂存、未提交。
