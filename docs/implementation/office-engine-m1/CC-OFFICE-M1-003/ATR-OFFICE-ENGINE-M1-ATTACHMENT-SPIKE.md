<!-- 使用 Coding/ATR 模板；记录 CC-OFFICE-M1-003 的 Odoo shell 运行证据。 -->

# ATR — CC-OFFICE-M1-003

## 1. Execution Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-ATTACHMENT-TRANSACTION-SPIKE` |
| IHR | [IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE](IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md) |
| CC Version | `v1.0.0 Frozen` |
| Module | Odoo 18 `ir.attachment` runtime；no product addon |
| Environment | macOS 开发环境；项目 `venv`；Odoo 18.0；Python 3.11.9；PostgreSQL 16.14；database `odoo18ce`；storage `file` |
| Test Framework | `odoo-bin shell -c odoo.conf -d odoo18ce` + Odoo ORM |
| Code Baseline | 项目 HEAD `ab89f54727807a25b16f3ad7e699fd05c782f3d9`（未提交的既有工作树变更未纳入） |
| Executed By | Codex Agent |
| Execution Date | 2026-10-21 |
| CC Closure Decision | 负责人批准关闭，2026-10-21；详见 FR |

Filestore 路径不记录；测试数据为唯一合成 bytes。UID 97/98 的附件操作环境均 `su=False`。环境详情见 `evidence/environment-snapshot.json`。

## 2. Test Contract Baseline

仅验证冻结 CC §8 的 CC-TEST-001—008。此 Spike 不实现产品模块，不宣称满足 SRS 产品验收；源码解释与 Odoo shell 实测分开标记。

## 3. Current Test Status

| 指标 | 值 |
|---|---|
| Required CC Tests | 8 |
| PASS | 8（每项均按 CC 的“观察并记录”目标完成） |
| FAIL | 0 |
| BLOCKED | 0 个契约测试；ATR-RUN-001 是沙箱启动阻断，未进入测试 |
| NOT RUN | 0 个 CC-TEST；Odoo 全局 GC 明确不运行，不属于本 CC 必须执行的清理动作 |
| Evidence Set | `ATR-RUN-002`—`ATR-RUN-006`；多次独立 Odoo shell，不是单个自动化套件 |
| Evidence Baseline Match | Yes；当前仓库 HEAD 未在执行中变化 |

**解释边界：** PASS 表示 CC 指定的提交、回滚、权限和清理边界已观察并如实记录。它不代表 filestore 文件在事务回滚时同步消失；实测结果恰为文件保留并进入 Odoo GC checklist。

## 4. Core Test Contract Coverage Matrix

| CC Test | 实际证据 | Run | Result | 说明 |
|---|---|---|---|---|
| CC-TEST-001 | 运行前两条 marker 和 deterministic checksum 路径均不存在；最终两个 name 与 fname 引用均为 0 | 002、006 | PASS | 记录回到 DB 基线；两份磁盘对象是已报告的延迟 GC 残留 |
| CC-TEST-002 | User A 以 ORM 创建并提交附件；新 cursor 读回 raw bytes，SHA-1 一致 | 003 | PASS | 记录 6089；只含合成字节 |
| CC-TEST-003 | 区别于控制 payload 的独立 rollback payload；显式 rollback；新 shell 按精确 name 和 fname 查无记录/引用，检查同一文件与 GC marker | 003、004、006 | PASS | 记录 6090；回滚并未删除 filestore 对象 |
| CC-TEST-004 | User A ORM unlink 提交；新 cursor 查无精确 name；再次 ORM unlink 为 no-op；物理文件与 marker 状态被记录 | 005、006 | PASS | 不手动删除任何文件、不触发全局 GC |
| CC-TEST-005 | User B `su=False` 搜索不可见；对同一 ID 调 `check('read')` 得到 `AccessError` | 003 | PASS | A/B 都为既有非系统内部用户 |
| CC-TEST-006 | 独立 Odoo shell、User A `su=False` 查询回滚附件 name 与 fname 均为零；不把 DB absence 当作文件已清除 | 004、006 | PASS | 与存储对象状态分开记录 |
| CC-TEST-007 | Runtime：create/rollback 期间文件及 checklist 已出现；提交后新事务可以读取字节。源码：`_file_write` 在 `_mark_for_gc` 后直接写文件 | 003、004；源码观察 `ir_attachment.py:133-145` | PASS（范围限定） | 读/写文件系统 I/O 与 ORM 调用处于同一请求事务；事务外纯 Python 可消费已取出的 bytes，但该完整产品生命周期未实现/未测 |
| CC-TEST-008 | 精确对象与 marker 可识别；源码 autovacuum GC 按 DB `store_fname` 引用保留/删除 checklist 文件；未执行 GC | 006；源码观察 `ir_attachment.py:165-220` | PASS（补偿路径已识别，未执行） | 原生 GC 为全局维护操作；不得据本次报告宣称已完成物理清理 |

## 5. Test Run History（Append-only）

| Run | Scope / Invocation | Result | Evidence |
|---|---|---|---|
| ATR-RUN-001 | 默认 sandbox 启动 Odoo shell；Queue Job 的 psutil `sysctl(KERN_PROC_ALL)` 被权限拒绝；未进入数据库 | BLOCKED before test | `evidence/ATR-RUN-001-shell-bootstrap.log` |
| ATR-RUN-002 | 只读预检：运行时、storage、非系统用户、唯一 name/checksum 冲突 | PASS | `evidence/ATR-RUN-002-preflight.log` |
| ATR-RUN-003 | 合成控制附件提交与 SHA-1 回读、跨用户 ACL、独立回滚探针 | PASS | `evidence/ATR-RUN-003-commit-rollback.log` |
| ATR-RUN-004 | 新 Odoo shell 校验回滚后数据库记录/fname 缺失及对象/checklist 状态 | PASS | `evidence/ATR-RUN-004-fresh-shell-postcheck.log` |
| ATR-RUN-005 | User A ORM unlink、精确重复清理 no-op、保留对象状态 | PASS | `evidence/ATR-RUN-005-orm-cleanup.log` |
| ATR-RUN-006 | 最终只读核对两条 marker、两条 fname 引用、文件和 GC marker | PASS | `evidence/ATR-RUN-006-final-audit.log` |

## 6. Regression / Preservation Verification

| CC 条款 | 验证 | 结果 | 证据边界 |
|---|---|---|---|
| 禁止 sudo/su | 每个附件操作前断言 UID 97/98、`su=False`、非 system group | PASS | bootstrap superuser 只做身份初始化及 cursor 启动 |
| 仅合成附件 | 唯一 token name、确定性 synthetic bytes、运行前精确冲突检查 | PASS | 未查询或更改业务附件内容 |
| ORM-only cleanup | 控制附件仅用 `unlink()`；重复搜索/清理 | PASS | 不等于即时 filestore 擦除 |
| 回滚隔离 | 独立 cursor 显式 rollback；新 shell 查 name/fname | PASS | 记录 6090 在 DB 不存在 |
| 文件系统边界 | 两个精确 fname 使用 realpath/commonpath containment 后只读检查 | PASS | 未输出根目录、未扫描其他对象 |
| 禁止全局 GC | 全程未调用 `_gc_file_store`、autovacuum 或手动文件删除 | PASS | 两个对象留待 Odoo 原生延迟 GC |

## 7. Issues / Findings

| ID | 发现 | 级别 | 状态 | 处理 |
|---|---|---|---|---|
| ATR-I-001 | DB 回滚不会回滚已写入的文件；Odoo 通过 checklist 延迟 GC | Major finding | Recorded; CC closure approved; Phase 4 policy gate remains | 结果文件不因无 DB 记录而可经附件路由读取；物理清理依赖 Odoo 原生 GC |
| ATR-I-002 | ORM unlink 也只标记 GC；磁盘文件仍存在 | Major finding | Recorded; CC closure approved; Phase 4 policy gate remains | 本 CC 不要求同步物理擦除；若产品要求即时擦除，另立设计/验证与授权 |
| ATR-I-003 | 全局 GC 代码持 `ir_attachment` SHARE lock 并遍历 checklist | Scope safety | Recorded | 依据 Odoo 源码；本 CC 禁止执行，因此没有宣称运行时 GC 清理通过 |

## 8. Special Verification

- **Runtime:** 真正执行 Odoo ORM、用户 ACL、独立 cursor 的 commit/rollback 和 filestore 只读检查；非性能或生产并发测试。
- **Source review:** `ir_attachment.py` `_file_write` 先写 checklist 再落盘；`_file_delete` 仅标记；autovacuum `_gc_file_store` 通过 DB fname whitelist 清理。源码解释不是 Runtime GC 执行证据。
- **Database / migration:** 未修改 schema；未执行模块安装/升级。
- **Browser / HVR:** N/A；冻结 CC 的全部测试标记人工验证 No。
- **Global cleanup:** NOT RUN by design; CC prohibits global GC and direct file deletion.

## 9. Evidence Inventory

| Evidence | 位置 | 内容 |
|---|---|---|
| CC | `docs/context/intent/CC-OFFICE-M1-003.md` | 验证边界权威 |
| IHR | 当前目录 `IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md` | 执行历史 |
| HVR | 当前目录 `HVR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md` | 人工验证 N/A |
| Spike report | 当前目录 `OFFICE-ENGINE-M1-ATTACHMENT-SPIKE-REPORT.md` | 结论、事务边界和补偿策略 |
| Runtime snapshot | `evidence/environment-snapshot.json` | 脱敏环境基线 |
| Run logs | `evidence/ATR-RUN-001` 至 `006` | 每次 Odoo shell 的命令摘要和 JSON 观察 |
| Executable probes | `evidence/*.py` | 可审阅的 Odoo shell 验证逻辑 |

## 10. Handoff

实施验证已执行；关闭权留给负责人。Spike 发现的两个 filestore 对象仍存在但无附件记录/fname DB 引用，且各有 GC marker。没有运行 GC，因此不能写成“磁盘清理完成”。
