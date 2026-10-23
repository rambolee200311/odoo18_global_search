# HVR-M2-005：AI 映射到 M1 文件交付端到端链路

## 1. 验证元数据

| 字段 | 值 |
|---|---|
| CC | `CC-M2-005` FROZEN V1.0.0 |
| 日期 | 2026-10-23 |
| HVR 状态 | **PARTIAL** |
| 浏览器 | Codex 内置浏览器，Odoo localhost |
| 线程 | `llm.thread_552`，合成测试线程 |
| 页面 | `http://127.0.0.1:8091/odoo/action-631?active_id=llm.thread_552` |
| 当前服务 | 项目 `venv`，`odoo-bin -c odoo.conf`，既有 `odoo18ce` |
| Provider | 未调用真实 Provider；自动化使用 Mock |
| 测试数据 | 合成伙伴、合成工作簿、合成映射值 |
| 最新自动化回归 | `/private/tmp/atr_m2_005_final_all_except_legacy.log`：47 项、0 failed / 0 error；其中 1 个 HttpCase 跳过；最新完整全量 `/private/tmp/atr_m2_005_full_final_current.log` 为 48 项、1 个前序共享库断言失败 |

本次 HVR 覆盖“已预置服务端 Session 的卡片确认、M1 生成、下载及刷新恢复”。它不覆盖聊天 UI 上传后自动建 Session、自然语言触发 Retriever/AI 映射，因此不能判定完整 CC-TEST-012 通过。

## 2. 场景执行记录

### HVR-SCN-001：成功渲染与下载（部分通过）

1. 在 `odoo18ce` 用 ORM 预置合成线程、有效 `.xlsx` 附件、Mapping Session、TargetManifest 和已确认的映射。模板由测试脚本挂到上传消息；没有声称通过浏览器上传模板或由自然语言自动建立 Session。
2. 在内置浏览器打开 `llm.thread_552`，确认卡片显示目标 `xlsx:Sheet1!B1` 和字段 `name`，点击 Confirm。
3. 浏览器卡片显示 `Document generated and verified.`，并出现下载链接；点击链接下载。
4. 后端 M1 请求 `116` 状态为 `generated`，稳定 UUID 为 `d7e56b71-4193-572f-a533-44f60fc6784d`，仅查到一条匹配请求，输出附件 `7392` 为私有附件。
5. 使用 `odoo-bin shell -c odoo.conf -d odoo18ce` 只读 ORM 读取输出附件，再用 `openpyxl` 回读：`Sheet1!B1 == CC-M2-005-SYNTHETIC-d7f39dd8af`。
6. 重启服务以加载最新 Python 与前端资源后，在浏览器刷新同一线程。卡片恢复 `Document generated and verified.`、显示下载链接，Save/Confirm/Cancel 均禁用。再次点击下载链接后页面没有错误提示。

**结论：预置 Session 的确认→M1 持久渲染→私有附件→下载及刷新恢复通过。UI 上传→AI 启动没有通过本场景验证。**

### HVR-SCN-002：5/20 澄清卡片（未执行 UI）

- Odoo TransactionCase 使用 Mock Provider 验证首轮和修复轮均返回 5/20 后进入 `needs_clarification`，没有 M1 请求或输出附件。
- 本轮未在浏览器中触发或展示 5/20 澄清卡片，因此 HVR 状态为 `NOT RUN`。

### HVR-SCN-003：渲染/权限失败 UI（未执行 UI）

- 自动化验证 M1 返回失败时不提供 `output_attachment_id` / 下载链接；Provider 错误和 Usage 写入失败会在进入 M1 前停止。
- 本轮未在浏览器执行权限撤销、回读失败或交付失败场景，因此 HVR 状态为 `NOT RUN`。

## 3. 自动化测试关联

| 验证项 | 状态 | 证据 |
|---|---|---|
| AI 编排、5/20、非法 JSON、未知字段、Provider/Usage 失败 | PASS | `/private/tmp/atr_m2_005_targeted_final2.log`，定向 11 项整体 0 failed / 0 error |
| `office_core` 真实生成与 `office_verify` 回读 | PASS | `TestOfficeCoreM2Integration.test_cc_test_007_real_engine_generates_and_independently_verifies_xlsx` |
| M1 Odoo 持久请求与私有附件 | PASS（合成） | Request 116 / attachment 7392；稳定 UUID 仅 1 条匹配请求 |
| 全量 Addon | FAIL（环境历史数据） | `/private/tmp/atr_m2_005_full_final2.log`：47 项中 1 failure；前序 Session 测试假设全表计数为 0，但共享库存在 3 条历史 Session |
| 选择性 M2 组件回归 | PASS（带 1 项跳过） | `/private/tmp/atr_m2_005_regression_final.log`：39 项，0 failed / 0 error；HttpCase Playwright 场景因缺少 `websocket-client` 跳过 |
| 负向路径专项回归 | PASS | `/private/tmp/atr_m2_005_negative_paths_final.log`：15 项，0 failed / 0 error；包含 Retriever 超时/无记录、未知目标/字段类型、M1 handoff 异常无下载 |
| AI/Usage 新增隐私与错误边界 | PASS（自动化） | `/private/tmp/atr_m2_005_provider_error_usage_final.log`：Provider 异常受控进入 `failed`，Usage 行持久保存并保持最小字段；M1 请求数不增加 |
| 完整 Addon 回归 | FAIL（既有共享库假设） | `/private/tmp/atr_m2_005_full_final_current.log`：48 项中 1 项前序 Session 全表计数断言失败；`/private/tmp/atr_m2_005_final_all_except_legacy.log` 排除该单项后其余 47 项 0 failure，HttpCase 仍跳过 |
| HttpCase 浏览器自动化 | SKIPPED | 当前环境未安装 `websocket-client`；没有安装依赖。内置浏览器已复核预置 Session 的完成状态和下载链接 |

## 4. 服务配置和数据安全

- 渲染验证使用唯一合成伙伴值 `CC-M2-005-SYNTHETIC-d7f39dd8af`，未使用真实客户/订单数据。
- 渲染所用短暂服务进程仅允许合成字段 `res.partner.name`，没有调用 Provider；验证后停止。
- 随后停止旧系统 Python Odoo 进程，使用项目 `venv` 和 `odoo.conf` 恢复 8091。刷新恢复验证发生在该服务上；不带临时 Provider 数据策略配置。
- 没有真实外网请求。输出附件保持私有，未直接访问或修改 filestore。

## 5. 尚未完成的 HVR

1. 需要安全的产品入口把聊天附件、自然语言请求、服务端 TargetManifest 和 Mapping Session 关联，再从浏览器上传文件并触发 AI 编排。当前不能通过客户端传入任意 `target_model/record_id/manifest` 来绕过这个缺口。
2. 在 UI 中执行 5/20 澄清和 M1/权限失败的可见状态验证。
3. 若需截图文件归档，应在后续验证中将浏览器截图导出到批准的证据目录；本次截图仅出现在 Codex 内置浏览器工具记录中，没有保存为仓库图片。
4. 本轮重跑的内置浏览器仍显示 `Document generated and verified.` 与私有下载链接；没有在 UI 中触发 5/20 澄清卡片或 Provider/M1 失败状态，因此这两项 HVR 仍是 `NOT RUN`。

**HVR 最终结论：PARTIAL。** 预置映射确认后的真实 M1 文件生成与下载已验证；不能据此宣称 M2 完整聊天上传→AI→确认→下载链路通过，也不代替负责人关闭 CC。
