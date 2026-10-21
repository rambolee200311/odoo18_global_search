# Office Engine M1 — `ir.attachment` 事务与清理 Spike 报告

**CC:** `CC-OFFICE-M1-003 v1.0.0 Frozen` | **执行日期:** 2026-10-21
**状态:** Spike 执行完成；负责人已批准关闭 CC（2026-10-21）；Phase 4 仍须明确接受 Odoo 原生延迟 GC 语义

## 1. 结论摘要

在获准开发库 `odoo18ce` 上，使用两个既有非系统内部用户（UID 97/98，均 `su=False`）完成了提交、字节回读、跨用户 ACL、显式回滚、独立 shell 查询、ORM 删除和幂等清理验证。**附件数据库记录受 Odoo 用户权限和事务控制，但 filestore 文件 I/O 是 ORM 请求中的外部副作用：回滚和 `unlink()` 都不会同步删除磁盘文件，而是留下 GC checklist 标记。**

最终只读审计确认：两个合成测试附件的名称记录和 `store_fname` 数据库引用均为 0；对应的两份唯一合成文件及 Odoo GC checklist 标记仍存在。未直接删除磁盘对象，也未调用全局 GC。测试数据没有可访问的 `ir.attachment` 记录，因此回滚输出不可经附件记录访问；物理文件的最终清理依赖 Odoo 原生延迟 GC。

**执行结论：** CC 指定的观察与记录动作均完成，建议将本 Spike 的执行标记为完成。是否关闭 CC / 是否允许 Phase 4 依赖 Odoo 原生延迟 GC，等待负责人评审；若业务要求事务回滚或失败时同步物理擦除，则当前证据不满足该要求，需新设计与授权验证。

## 2. 环境与范围

| 项 | 实测 |
|---|---|
| Odoo | 18.0；仓库基线 `ab89f54727807a25b16f3ad7e699fd05c782f3d9` |
| Python | 项目 `venv` / 3.11.9 |
| PostgreSQL | 16.14 |
| DB | 现有 `odoo18ce`；未创建隔离库 |
| 附件存储 | `file` / filestore |
| 操作用户 | A=97、B=98；都 active/internal、非 system、`su=False` |
| 唯一标记 | `ff5508dd8be3`；仅用于两份短小合成 payload |
| 操作方式 | `./venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce` |

无依赖/模块安装、配置或 schema 修改；无业务附件访问；无 `sudo()` / `su=True` 附件操作；无直接文件删除；无全局 GC。

## 3. 实测结果

| 场景 | 观察 | 结果 |
|---|---|---|
| 预检 | 两个精确测试名和两条 checksum 路径不存在；storage=`file` | PASS |
| 控制附件提交 | User A 创建附件 6089 并提交；新 cursor 读回 bytes 的 SHA-1 匹配；文件与 checklist 均存在 | PASS |
| 跨用户访问 | User B 搜索不到附件；直接 `check('read')` 抛 `AccessError` | PASS |
| 回滚附件 | User A 在独立 cursor 创建附件 6090，捕获 `store_fname=34/34de6936a35011a07ecc06bc0521f9961ccb51f7`，同事务观测到对象和 checklist 后显式 rollback | PASS（回滚行为已执行） |
| 回滚后独立查询 | 全新 `odoo-bin shell` 中精确 name 记录数=0、fname 引用数=0；该唯一对象和 GC 标记仍存在 | PASS（结果明确区分 DB 与文件） |
| ORM 清理与重复清理 | User A unlink 已提交控制附件；新事务精确 name 记录数=0；第二次 unlink 为 `PASS_NOOP` | PASS |
| 最终审计 | 两个 name 和两个 fname DB 引用均为 0；两个对象和两个 checklist marker 均存在 | PASS（待 Odoo 原生 GC） |

完整脱敏输出见 ATR-RUN-002—006；详细环境见 `evidence/environment-snapshot.json`。

## 4. Odoo 源码观察（与运行时证据分开）

仓库 Odoo 18 源码 `odoo/addons/base/models/ir_attachment.py` 显示：

- `_file_write`（约 133—145 行）先 `_mark_for_gc(fname)`，再通过 Python `open(..., 'wb')` 写文件。运行时在同一 ORM 创建流程中观察到了文件和 checklist。
- `_file_delete`（约 147—150 行）只加入 GC checklist，不即时删除对象。运行时 ORM unlink 后对象仍存在，与此一致。
- `_gc_file_store` 是 `@api.autovacuum` 过程；它会打开独立事务、对 `ir_attachment` 加 SHARE 锁，再检查 checklist 和 DB `store_fname` 引用，删除无引用文件并清理 checklist（约 165—220 行）。

该实现是 Odoo 原生的延迟文件回收路径。它是全局维护流程，本次没有执行，所以这里只能说“补偿路径已在源码识别，且对象已被精确标记”，不能说已经通过实际 GC 删除验证。

## 5. 对 M1 同步事务设计的影响

1. **输入快照：** 在短事务中以当前用户权限验证附件并读取 `raw` bytes，随后可关闭 cursor，把 bytes 交给不持有 Odoo 环境的纯 Python 处理阶段。此次实测证明授权读取和内容回读可工作；“关闭事务后完整渲染”并非本 Spike 的产品端到端测试。
2. **输出提交：** 附件创建会在 ORM 事务调用中同步执行 filestore 写入；输出文件写入耗时会落在创建/提交阶段，不能假设该 I/O 随 DB rollback 自动撤销。必须保持输出大小/写入工作有界，并把失败记录不可访问与物理延迟回收区分开。
3. **失败安全：** 回滚后数据库无附件行、无 `store_fname` 引用；用户不能通过 `ir.attachment` 权限访问该文件。后台 Odoo GC 在后续运行时物理回收。不得把“ORM 记录不存在”报告为“文件已擦除”。
4. **锁与耗时：** 此 Spike 使用小型合成文件，没有测量大文件 I/O 延迟、数据库锁等待或生产并发预算；不据此给出容量和时间承诺。

因此，M1 可采用“短事务读取/验证并提取 bytes → 事务外受限处理 → 短事务创建/关联输出”的分层，但输出文件落盘本身仍发生在 ORM 写入路径。Phase 4 需约束候选/输出体积与同步预算，并接受 Odoo 的延迟 GC 语义；不要在失败处理中执行全局 GC。

## 6. 风险与补偿路径

| 风险 | 当前证据 | 建议处置 |
|---|---|---|
| rollback/unlink 后磁盘上暂留无引用对象 | 两个唯一合成对象实测存在且有 checklist；DB 引用均为零 | 依赖 Odoo 原生 autovacuum GC 延迟回收；应用层只用 ORM unlink，禁止直接删除 |
| 要求立即物理擦除 | 本次按 CC 不运行全局 GC；没有同步擦除能力证据 | 若业务安全/合规要求即时擦除，应独立设计“按精确 fname、在确认 DB 无引用后”的安全 API/任务并另行 CC 验证；当前不能承诺 |
| 全局 GC 的广泛影响 | 源码确认它遍历整个 checklist，并对附件表加锁 | 本 Spike 不运行；不可把 GC 当作请求失败路径中的单对象同步清理函数 |
| 生产锁/性能预算 | 未测大文件、并发或目标生产限额 | 按 TDD/实施计划在容量验证阶段单独测量，不阻塞对事务副作用的事实结论 |

当前合成文件仍留在本地 filestore 给原生 GC；它们不含业务数据。执行清理工作没有扫描目录或移除其他文件。

## 7. Gate 建议

- **CC Spike 执行：** 已完成，全部 CC-TEST-001—008 有证据；HVR 按冻结 CC 为 N/A。
- **CC 关闭：** 负责人已于 2026-10-21 批准关闭；两份对象仍待 Odoo 原生 GC，不能改写成“磁盘已清理”。该关闭不构成同步物理擦除的产品承诺。
- **Phase 4：** 可在明确接受 Odoo 原生延迟 GC、失败输出无附件行/不可下载、附件体积和同步写入有界的前提下继续设计。若产品定义要求同步物理删除，则 Phase 4 对该要求仍 BLOCKED，需独立设计/授权验证。
- **不在本报告授权：** 不创建请求模型、不改 TDD、不实现补偿任务、不执行 GC、不直接删文件。

## 8. 附件证据

- `IHR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md`
- `ATR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md`
- `HVR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md`
- `evidence/environment-snapshot.json`
- `evidence/ATR-RUN-001-shell-bootstrap.log` 至 `ATR-RUN-006-final-audit.log`
- `evidence/preflight.py`、`commit_and_rollback_probe.py`、`fresh_shell_postcheck.py`、`orm_cleanup_control.py`、`final_cleanup_audit.py`
