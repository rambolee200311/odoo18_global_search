# IHR-M2-005：AI 映射到 M1 文件交付端到端链路

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-005` |
| CC | `CC-M2-005`，FROZEN V1.0.0 |
| Git 基线 | `25a1a9e6d42692f512c90c559fd2d9b3e17dff09`；实现为未提交工作树 |
| Addon | `office_engine_m2`，版本 `18.0.4.0.0` |
| Odoo / Python | Odoo 18.0 / Python 3.11.9 |
| 数据库 | `odoo.conf` 指向既有 `odoo18ce`；未创建隔离库 |
| 外部 Provider | 未调用；自动化响应均为 Mock |
| 日期 | 2026-10-23 |

## 2. 实施记录

### IHR-001 — Provider 编排与确定性校验

- 新增 `services/ai_orchestrator.py`：固定检查 OpenAI `gpt-5.6-luna`，以当前用户 `env` 调用现有 `odoo_record_retriever`，使用服务端 TargetManifest/字段白名单构建受限上下文，再调用 `office_mapping_verify` 验证 Proposal。
- 业务数据 Provider 外发默认拒绝；需同时满足部署数据政策批准和模型字段基线。测试仅在合成夹具中临时允许 `res.partner.name`，未使用真实客户/订单数据或外部 API。
- 对 JSON 解析和 Proposal 完整性失败最多重试一次；每次 Provider 尝试调用 `record_usage()`。5/20 修复仍不完整时转为澄清，不调用 M1。
- 补充自动化：非法 JSON 重试后澄清、未知字段丢弃且不进 M1、Provider 错误/Usage 写入失败停止在 M1 前。

### IHR-002 — M1 确认渲染桥接

- 新增 `services/render_bridge.py`：校验 Session owner/company、消息/附件绑定、确认 revision 和字段授权；确认时实时经现有 Retriever 取数，编译受限 M1 Mapping Plan。
- 使用稳定的 Session + confirmed revision UUID 调用既有 `office.document.request._render_request_sync`；只返回 M1 已校验并创建的私有附件，不自行创建交付文件。
- 修复跨事务快照问题：M1 在独立游标提交输出后，父 HTTP 事务的旧快照不能重查新附件。桥接层使用 M1 返回的正向 attachment ID，避免把成功渲染误报为失败。
- 修复 M1 handoff 抛异常后的失败语义：持久化 Session `failed` 并返回受控失败对象，不把异常抛回 RPC 导致状态回滚；结果不包含输出附件 ID 或下载 URL。
- 补齐 Provider 异常计量持久化：Provider 异常在 `record_usage()` 成功后返回受控失败结果，写入 Session `failed` 状态和服务端错误卡片，避免向 RPC 抛异常回滚 Usage 行；Usage 写入失败仍停止后续流程。自动化验证 Usage `outcome=provider_error`、缺失 Usage 的 `error_code=usage_missing`、attempt/耗时元数据、无 M1 请求。
- 对同一已完成 revision 重试时复用同一请求 UUID 和输出。实际 ORM 复核确认稳定 UUID 仅有一条 generated 请求；并发事务竞态未验证。

### IHR-003 — 映射卡片联动

- 扩展 `mapping_service.py`、认证 Controller 和 Owl 卡片：增加已有 Session 的 `/mapping/start` 编排入口、澄清显示、成功下载链接和失败状态。
- 发现完成后刷新只显示 revision 提示、未恢复结果链接的问题。context 服务现在按当前用户 ACL 查找已完成 Session 对应的 M1 请求/私有附件，Owl 在刷新后恢复完成状态/下载链接，并禁用终态按钮。
- QWeb `&&` 已 XML 转义；Python、JS、XML 静态检查通过。

### IHR-004 — 自动化与内置浏览器验证

- 定向 Odoo 测试：11 项，`0 failed, 0 error(s)`，日志 `/private/tmp/atr_m2_005_targeted_final2.log`。
- 负向路径专项：15 项，`0 failed, 0 error(s)`，日志 `/private/tmp/atr_m2_005_negative_paths_final.log`。
- 最新 M2 组件回归：39 项，`0 failed, 0 error(s)`；其中 1 个 HttpCase Playwright 场景因环境缺少 `websocket-client` 跳过。日志 `/private/tmp/atr_m2_005_regression_final.log`。
- 最新 M2 组件回归：40 项，`0 failed, 0 error(s)`；1 个 HttpCase Playwright 场景因环境缺少 `websocket-client` 跳过。日志 `/private/tmp/atr_m2_005_regression_final4.log`。
- 最新 AI/Usage 定向：9 个测试方法，`0 failed, 0 error(s)`。日志 `/private/tmp/atr_m2_005_provider_error_usage_final.log`；覆盖正常 Proposal、Usage 缺失、Prompt 哨兵不落消息/Usage、Provider 错误计量持久化及 Usage 写入失败阻断。
- 最新完整 Addon 测试：48 项，`1 failed, 0 error(s)`。失败是前序 Session 测试断言共享库全表 Session 数为 0，但 `odoo18ce` 中有 3 条历史 Session；此测试文件不在 CC-M2-005 允许修改范围内，未修改或删除历史数据。一个 HttpCase 因环境缺少 `websocket-client` 被跳过；未安装依赖。最终日志 `/private/tmp/atr_m2_005_full_final_current.log`。
- 完整 Addon 排除上述单个历史数据敏感测试后：47 项，`0 failed, 0 error(s)`，同一个 HttpCase 仍跳过。最终日志 `/private/tmp/atr_m2_005_final_all_except_legacy.log`。
- 内置浏览器在预置合成 Session 中确认后真实调用 M1，生成私有 XLSX 并下载；Odoo shell ORM 复核稳定 UUID 对应唯一请求，`Sheet1!B1` 为合成标记值。服务重启后刷新线程，卡片恢复完成状态和下载链接。
- 没有完成 UI 上传后自动创建 Session/TargetManifest 并触发 AI 的链路；没有调用真实 Provider。

## 3. 实施缺口与偏离

1. 当前入口仍从已有服务端 Session 开始。系统尚无“聊天新上传附件 + 自然语言目标 → 安全解析目标 → M1 Inspection/TargetManifest → 创建 Session”的完整入口；不能声称用户上传后自动开始 AI 映射。
2. 部署 Provider 数据政策和安全字段白名单尚未批准；真实业务数据仍按默认拒绝外发。
3. 人工浏览器只覆盖预置 Session 的确认、M1 生成、下载和刷新恢复。5/20 澄清及权限/渲染失败 UI 未执行。
4. 同一稳定 UUID 的真实重复请求验证通过；独立并发事务竞态和 Retriever/verify/附件交付完整失败矩阵未验证。
5. 全量 Addon 存在一项共享数据库历史 Session 计数失败和一个缺依赖 HttpCase skip；不把选择性 M2 组件回归通过外推为全量全绿。

## 4. 实际变更路径

- `mymodules/office_engine_m2/services/ai_orchestrator.py`
- `mymodules/office_engine_m2/services/render_bridge.py`
- `mymodules/office_engine_m2/services/mapping_service.py`
- `mymodules/office_engine_m2/controllers/mapping_controller.py`
- `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.js`
- `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.xml`
- `mymodules/office_engine_m2/tests/test_ai_orchestrator.py`
- `mymodules/office_engine_m2/tests/test_render_bridge.py`
- `mymodules/office_engine_m2/tests/test_office_core_integration.py`
- `mymodules/office_engine_m2/tests/__init__.py`
- `mymodules/office_engine_m2/__manifest__.py`

未修改 `odoo-llm`、`office_core`、`office_verify`、`office_engine_odoo`、Odoo 官方代码或其他 Addon；未新增依赖、ORM 模型或字段。
