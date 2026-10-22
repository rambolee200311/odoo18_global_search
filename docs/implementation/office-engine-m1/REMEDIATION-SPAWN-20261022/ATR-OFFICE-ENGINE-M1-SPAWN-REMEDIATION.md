# ATR — OFFICE-ENGINE-M1-SPAWN-REMEDIATION

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-SPAWN-REMEDIATION` |
| CC | 未创建专用修复 CC；不改变 CC-004/006 历史状态 |
| 环境 | Odoo 18；项目 `venv`；`odoo.conf`；现有 `odoo18ce`；macOS ARM64 |
| Python | 3.11.9 |
| 数据库身份 | Odoo addon 测试及 shell 黄金链路分别按各自测试环境执行；ORM 黄金链路为 `uid=2`, `env.su=False` |
| 代码基线 | Git HEAD `19499b84a9b62b1ee5561fae81c3ff33d4fc64ca` + 未提交工作树修改 |
| 日期 | 2026-10-22 |

## 2. 测试结果摘要

| 验证 | 结果 | 证据含义 |
|---|---|---|
| `office_core` unittest | PASS；19 项 | spawn worker 正常预算、RSS 不可观测拒绝、RSS 超限终止及既有格式/映射测试通过 |
| `office_verify` unittest | PASS；15 项 | 独立回读包既有测试通过 |
| `office_engine_odoo` 升级及测试 | PASS；命令 exit 0，18 项 | 当前适配器可加载；Odoo TransactionCase 的 Core→Verify 正常文件路径通过 |
| Odoo shell 黄金链路 | PASS | `uid=2`, `env.su=False`；A1 读取；B1 写入“测试客户”；`office_verify` PASS；私有输出附件 6461 可读 |
| 语法编译 | PASS | `python -m compileall -q mymodules/office_core mymodules/office_engine_odoo` exit 0 |
| 聊天 UI 成功生成 | NOT RUN / 仍不可用 | 当前 `llm_thread` 适配器继续拒绝 Office 文件；该行为保持 fail-closed，本 ATR 不表示聊天 handoff 通过 |
| Linux / 生产 RSS 硬上限 | NOT RUN | 目标 Linux 环境未确认；macOS RSS 监督只属采样软边界 |

## 3. 实际执行记录

### ATR-RUN-001 — Core 与 Verify 自动化

- `PYTHONPATH=mymodules ./venv/bin/python -m unittest discover -s mymodules/office_core/tests -v`：19 项通过，exit 0。
- `PYTHONPATH=mymodules ./venv/bin/python -m unittest discover -s mymodules/office_verify/tests -v`：15 项通过，exit 0。

### ATR-RUN-002 — Odoo addon 集成测试

- 命令：`./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u office_engine_odoo --stop-after-init --test-enable --test-tags /office_engine_odoo --log-level=warn`
- 结果：exit 0；18 项 addon 测试，无失败/错误。覆盖新增的 spawn Core inspect/render 与独立 Verify PASS 的合法 XLSX 用例。
- 首次集成测试曾因夹具把目标单元格 B1 留空而失败；修正为有内容的可映射单元格后重新执行通过。历史失败未从运行日志中抹除。

### ATR-RUN-003 — 当前用户 ORM Golden Path

- 入口：`./venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce`。
- 用户：`uid=2`, `env.su=False`；无 `sudo()`。
- 结果：`office.document.request` 为 `generated`；源附件 `6460`；输出附件 `6461`，`public=False`；A1=`客户名称`；B1=`测试客户`；独立 Verify 状态 `PASS`、目标数 1；输出 SHA-256 与请求记录一致。
- 证据：[spawn_repair_success.json](../../CC-OFFICE-M1-004/evidence/spawn_repair_success.json)。该输出记录留在开发库供核验；未宣称聊天链接已交付。

## 4. 结果边界

- Core 和 Odoo 请求服务在本机当前用户上下文已取得成功生成与私有附件证据，修复了历史 spawn 导入及 macOS `RLIMIT_AS` 阻断。
- Core RSS 通过父进程采样实现，可能发生超调；不是内核级硬内存限制。
- 当前聊天扩展仍有意拒绝 Office 附件，未做 Provider handoff，也未提供 Mapping UI 或聊天下载链接。
- CC-004 及 CC-006 历史 FAIL/REJECTED 状态不自动改写；需独立复审其覆盖项后才可关闭。
- 本 ATR 不包含人工验收结论；UI HVR 状态保持待执行/不满足。
