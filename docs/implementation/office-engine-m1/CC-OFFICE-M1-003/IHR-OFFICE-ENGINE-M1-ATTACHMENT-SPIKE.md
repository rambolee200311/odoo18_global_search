<!-- 使用 Coding/IHR 模板；仅记录冻结 CC-OFFICE-M1-003 的验证执行，不代表产品实现。 -->

# IHR — CC-OFFICE-M1-003

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-ATTACHMENT-TRANSACTION-SPIKE` |
| CC 引用 | [CC-OFFICE-M1-003](../../../context/intent/CC-OFFICE-M1-003.md)，`v1.0.0 Frozen` |
| 模块 | Odoo 18 `ir.attachment` 运行时行为；未新增模块 |
| 工作类型 | 技术验证 / Spike |
| 实施负责人 | Codex Agent；批准人见冻结 CC |
| 开始 / 最后更新 | 2026-10-21 |
| 当前执行状态 | **CC 已由负责人批准关闭（2026-10-21）；Spike 执行完成** |
| SRS / TDD / Plan | SRS V1.0.0 Frozen；TDD V0.3 Frozen；Implementation Plan V0.2 Frozen |
| Git 基线 | `ab89f54727807a25b16f3ad7e699fd05c782f3d9`；本次仅新增验证记录，未提交 |
| 数据库 / Python | `odoo18ce` / 项目 `venv` Python 3.11.9 |

## 2. CC 执行边界

仅按冻结 CC 使用现有 `odoo18ce`、Odoo shell 和两个既有非系统内部用户执行合成附件检查。未建隔离数据库，未安装/升级依赖或模块，未修改配置、schema、官方代码或业务附件。Shell bootstrap 的 superuser 环境只用于识别用户和创建 cursor；所有附件操作都使用 `api.Environment(..., uid, ..., su=False)`，User A=97、User B=98。没有调用 `sudo()`、`env(su=True)`、直接删除 filestore 文件或运行全局 GC。

## 3. 实施历史（仅追加）

### IHR-001 — 只读预检与执行身份

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Preflight |
| Action | 通过项目 `venv` 的 Odoo shell 检查运行时、数据库、存储模式、用户组、唯一标记和两个确定性 payload 的 checksum 路径 |
| Reason | 确认 CC 批准的环境与无冲突前置条件，避免覆盖任何现存对象 |
| Files / Components | `evidence/preflight.py`、`evidence/environment-snapshot.json` |
| Contract Reference | CC-TEST-001；CC §4、§9 |
| Result | PASS：Odoo 18.0、Python 3.11.9、PostgreSQL 16.14、`odoo18ce`、storage=`file`；UID 97/98 均 active/internal、非 system、`su=False`；测试标记和候选 checksum 路径均不存在 |
| Deviation | 首次 sandbox shell 在数据库访问前被 Queue Job 的 psutil 进程枚举权限拒绝；同一命令在已批准开发环境重跑成功。无 ORM 操作发生在失败尝试中 |
| Follow-up | 保留首次启动失败于 ATR-RUN-001；成功预检见 ATR-RUN-002 |

### IHR-002 — 提交、回读、权限与回滚探针

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Runtime verification |
| Action | User A 创建唯一合成控制附件并提交；新 cursor 读取并核对 SHA-1；User B 搜索与直接读检查；另一个唯一 payload 在独立 cursor 创建后显式回滚 |
| Reason | 验证提交、字节一致性、跨用户隔离和 Odoo 文件系统副作用 |
| Files / Components | `evidence/commit_and_rollback_probe.py`、ATR-RUN-003 |
| Contract Reference | CC-CHANGE-002/003/005；CC-TEST-002/003/005/006 |
| Result | 控制附件 6089 哈希一致；B 搜索不可见且 `check('read')` 被 `AccessError` 拒绝；回滚附件 6090 在回滚前生成精确 `store_fname` 对象与 checklist 标记 |
| Deviation | None |
| Follow-up | 按 CC 要求另开 shell 核对回滚后的 DB 可见性 |

### IHR-003 — 新 shell 观察与 ORM 清理

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Cleanup verification |
| Action | 新 shell 确认回滚记录和 fname 引用不存在；只读检查该 fname 文件与 GC marker；User A 对控制附件执行 ORM unlink，再以新事务重复精确清理并核对 |
| Reason | 区分数据库回滚/ORM 删除与 filestore 物理清理，验证清理幂等性 |
| Files / Components | `evidence/fresh_shell_postcheck.py`、`evidence/orm_cleanup_control.py`、ATR-RUN-004/005 |
| Contract Reference | CC-CHANGE-003/004/005；CC-TEST-003/004/006 |
| Result | 回滚和控制记录均不可见；控制附件重复 ORM 清理为安全 no-op。两个对象都仍在 filestore，且 checklist 标记存在 |
| Deviation | None；按 CC 明令不调用全局 GC |
| Follow-up | 对两条精确 fname 做最终只读核验，结果见 IHR-004 |

### IHR-004 — 最终隔离与 GC 路径评估

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-21 |
| 阶段 | Final audit / report |
| Action | 用 User A 的 `su=False` 环境核对两条唯一测试名、两条精确 `store_fname` 引用、对应对象与 checklist；阅读 Odoo 18 `ir_attachment.py` 的写入、unlink 与 autovacuum GC 实现 |
| Reason | 验证记录清理回到基线，并报告延迟物理清理的精确补偿路径 |
| Files / Components | `evidence/final_cleanup_audit.py`、`OFFICE-ENGINE-M1-ATTACHMENT-SPIKE-REPORT.md`、ATR-RUN-006 |
| Contract Reference | CC-CHANGE-006；CC-TEST-001/007/008；CC §10 |
| Result | 两个 marker 和两个 DB fname 引用都为 0；只剩本 Spike 创建的两份合成对象和对应 GC checklist 标记。源码显示 Odoo autovacuum GC 会在锁定附件表后删除无 DB 引用的 checklist 文件；该全局 GC 未执行 |
| Deviation | None；没有直接文件删除或全局 GC |
| Follow-up | 负责人评审接受 Odoo 原生延迟 GC 作为补偿路径；如业务要求同步物理擦除，需另立授权设计/验证 |

## 4. 变更清单

本 CC 没有产品代码、Addon、数据库 schema 或配置变更。新增记录仅限本目录中的 Spike 脚本、脱敏证据、IHR、ATR、HVR 与报告。所有唯一标记数据库记录均已通过 ORM 清除；两个本地 filestore 对象按 CC 保留给 Odoo 原生 GC，不手工删除。

## 5. 当前结论与限制

附件提交/回滚和 ORM unlink 不会同步撤销已写入的 filestore 对象。失败输出在数据库中不存在、没有 fname 引用，也不能经 `ir.attachment` 下载；物理对象由 checklist 与 Odoo 延迟 GC 管理。Odoo 的 GC 是遍历 checklist 的全局维护过程，本次禁止执行；报告不宣称物理擦除已完成，也不声明生产并发、容量或即时清理通过。

本 IHR 只记录事实。负责人于 2026-10-21 批准关闭本 CC；关闭仅接受本 Spike 已完成并如实记录的验证义务，不表示两个磁盘对象已物理擦除，也不等于批准应用层同步擦除。Phase 4 必须按 Odoo 原生延迟 GC 语义设计失败清理；若产品要求同步物理擦除，须先升级 TDD/计划并另行授权验证。
