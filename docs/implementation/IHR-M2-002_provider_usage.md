# IHR-M2-002：Provider Usage 实施历史记录

| 项目 | 值 |
|---|---|
| CC | `CC-M2-002` — FROZEN V1.0.0 |
| 状态 | CLOSED — 负责人于 2026-10-23 批准关闭 CC-M2-002 |
| 上游基线 | 本地提交 `9e0d32be7b166ef7710d7a6a8fd7174ebdb5f943` (`chore: stable baseline before M2-002`) |
| 分支 | `main` |
| Odoo / Python | Odoo 18.0；Python 3.11.9 |
| 数据库 / 配置 | `odoo18ce` / `odoo.conf`；沿用既有开发环境 |
| Provider 基线 | 仅 OpenAI `gpt-5.6-luna` 的 SDK Mock；不调用外网 |

## 基线裁定

负责人明确要求以 `git add .` 创建本地稳定基线。上述 commit 收录了该时点整个工作区（380 个文件，45,145 insertions、3,355 deletions）；因此它也固化了当时的 Odoo-LLM 源码与文档/模块迁移状态。CC-M2-002 实施补丁以该 commit 为父基线。该基线提交尚未推送。

基线创建后开始实施的文件变更仅按 `CC-M2-002` §4 白名单进行；Provider 方法级差异与工作树文件清单见 ATR 差异范围图。

## 实施阶段记录

| 日期 | 记录 | 结果 |
|---|---|---|
| 2026-10-23 | 将 CC-M2-002 状态更新为负责人批准的 FROZEN V1.0.0；附录 B 四项审批裁定已落实，OIP-M2-003 基线 hash 固定。 | 完成 |
| 2026-10-23 | 按负责人指令执行 `git add . && git commit -m "chore: stable baseline before M2-002"`，建立本地上游基线。 | commit `9e0d32be7b166ef7710d7a6a8fd7174ebdb5f943`；尚未推送 |
| 2026-10-23 | Provider 非流式响应标准化：只在 `_openai_process_non_streaming_response()` 增加 allowlist Usage 与可选 response ID；保留 content/tool_calls，streaming 路径不变。 | 完成；CC-TEST-001–004、008 PASS |
| 2026-10-23 | 新建 `office_engine_m2` Usage Addon：元数据 ORM、受限 `record_usage()`、管理员/运维只读 ACL；仅 Usage create 使用 sudo，业务/thread/message 不提权。 | 完成；CC-TEST-005–007 PASS |
| 2026-10-23 | 对 `odoo18ce` 执行模块升级和 Odoo TransactionCase。 | `office_engine_m2: 19 tests 0.63s 578 queries`；`0 failed, 0 error(s) of 13 tests`；日志 `/private/tmp/cc_m2_002_odoo_test_pass.log` |
| 2026-10-23 | Python 编译、XML 解析、`git diff --check` 与 Provider 方法范围复核。 | 全部通过；详见 [`ATR-M2-002.md`](ATR-M2-002.md) |
| 2026-10-23 | 负责人批准关闭 CC-M2-002。 | 已关闭；FR 根据 IHR/ATR 证据单独判定 |

## 变更范围核对

生产代码：

- `mymodules/odoo-llm/llm_openai/models/openai_provider.py`：仅 `_openai_process_non_streaming_response()` 方法体。
- `mymodules/office_engine_m2/`：M2 Usage Addon、模型、服务、组/ACL 和 TransactionCase。

未修改 Odoo 官方源码、其他 Provider、`llm_assistant` 或 `llm_thread` 生产代码。自上游基线以来的状态清单仅含上述 Provider 文件、`mymodules/office_engine_m2/`、本 CC 的 ATR/IHR 和差异证据图；`git diff --check HEAD` 通过。Provider 文件差异为 69 insertions、1 deletion，修改范围限于规定方法体。负责人已批准提交推送，提交标识将在完成后补入本记录。

## 关闭前证据

- 自动化测试与升级结果：见 [`ATR-M2-002.md`](ATR-M2-002.md)；本次通过 `odoo-bin -u office_engine_m2 --test-enable` 完成，而非 XML-RPC。
- Provider 方法差异范围：已复核，仅 `_openai_process_non_streaming_response()` 方法体有修改。
- 数据库清理：TransactionCase 在测试事务中运行并回滚；测试结束未留下持久 Usage 测试记录。
- 环境备注：测试日志另有三个原有不可安装模块提示，具体名称及与本 CC 无关的说明见 ATR；本 CC 最终测试结果无失败/错误。
