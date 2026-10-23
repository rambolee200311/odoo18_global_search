# IHR — CC-M2-004 Owl 映射卡片与 RPC 服务端校验

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-004` |
| CC | `CC-M2-004_owl_mapping_card.md`，V1.0.0 Frozen |
| 基线提交 | `24d6d4c7a7b28172c156c0b58b46fa1ef78b869d`（CC-M2-004 实现提交） |
| 分支 | `main` |
| 当前代码状态 | Implementation Complete；已提交 |
| 模块 | `office_engine_m2`，18.0.3.0.0 |
| 环境 | Odoo 18、项目 `venv`、`odoo.conf`、既有 `odoo18ce`、macOS |
| 日期 | 2026-10-23 |

## 2. 当前实施摘要

- 已实现 CC-CHANGE-001–006 的后端会话字段、映射服务、四个 JSON-RPC 路由和 Owl 聊天卡片。
- 服务端从当前 `request.env` 校验 Session owner/company；更新经过 `validate_user_revision()`，并由数据库锁和 `expected_revision` 拒绝陈旧写入。
- 新增交易与 HTTP 集成测试；Odoo 自动化结果见 [ATR-M2-004.md](ATR-M2-004.md)。
- 使用 Codex 内置浏览器验证卡片显示、字段选择、保存、确认、刷新保持，以及竞争更新后的陈旧 revision 反馈。该工具辅助观察不等同于人类验收签字；见 [HVR-M2-004_owl_mapping_card.md](HVR-M2-004_owl_mapping_card.md)。
- 未接入 LLM、Retriever 或 M1 渲染；未修改 `odoo-llm`、其他 Addon、Odoo 官方代码，未安装依赖。

## 3. 实施历史条目（仅追加）

### IHR-001 — Mapping Session 扩展

| 字段 | 记录 |
|---|---|
| 阶段 | Implementation |
| Action | 增加 `mapping_rules_json`、`confirmed_revision`、`context_json`，由服务端私有方法管理；`write()` 仍拒绝直接写入。 |
| Files / Components | `models/office_mapping_session.py` |
| Contract Reference | CC-CHANGE-003/005；TDD §§8–10 |
| Result | Completed |
| Deviation | None |

### IHR-002 — 服务层及 Controller

| 字段 | 记录 |
|---|---|
| 阶段 | Implementation |
| Action | 新增卡片上下文、保存、确认与取消服务；新增四个认证 JSON-RPC 路由。各 handler 首先读取 `request.env`，随后校验 session 存在、owner 和当前公司。 |
| Files / Components | `services/mapping_service.py`、`services/__init__.py`、`controllers/__init__.py`、`controllers/mapping_controller.py`、Addon `__init__.py` |
| Contract Reference | CC-CHANGE-003–005；T-M2-SEC-003/004 |
| Result | Completed |
| Deviation | None |

### IHR-003 — Owl 卡片与资产

| 字段 | 记录 |
|---|---|
| 阶段 | Implementation / Fix |
| Action | 使用 `@web/core/network/rpc`，通过 `Message.components` 注册专用类型卡片；提供目标只读行、后端字段选项、保存/确认/取消及状态反馈。为 mapping 消息隐藏上游 Markdown 正文的呈现，避免将 `<p>` 源文本显示给用户。 |
| Files / Components | Addon manifest、`static/src/components/office_mapping_card/` |
| Contract Reference | CC-CHANGE-001/002/006；CC-PRESERVE-001 |
| Result | Completed |
| Deviation | None |

### IHR-004 — 自动化测试

| 字段 | 记录 |
|---|---|
| 阶段 | Implementation / Fix |
| Action | 增加 TransactionCase / HttpCase，覆盖字段只读、合法更新、未知字段、旧 revision、owner 隔离、未完成映射禁止确认、确认/取消和持久化最小化。 |
| Files / Components | `tests/test_mapping_rpc.py`、`tests/__init__.py` |
| Contract Reference | CC-TEST-003–008 |
| Result | Completed |
| Deviation | `HttpCase.browser_js` 因环境缺少 `websocket-client` 被跳过；未安装依赖。后续用 Codex 内置浏览器完成了实际 UI RPC 操作。 |

### IHR-005 — 开发服务基线纠正

| 字段 | 记录 |
|---|---|
| 阶段 | Environment remediation |
| Action | 内置浏览器首次显示 context 不可用。检查确认 8091 由前一日系统 Python 启动的进程提供，未加载当前 Controller。按既有授权停止旧进程，使用项目 `venv` 和 `odoo.conf` 重启；后续浏览器 RPC 正常。 |
| Files / Components | 本地 8091 Odoo 进程；无仓库外配置改动 |
| Contract Reference | CC-TEST-010；TDD §10 |
| Result | Completed |
| Deviation | None；没有建新数据库或安装依赖 |

### IHR-006 — 内置浏览器验证与清理

| 字段 | 记录 |
|---|---|
| 阶段 | Verification |
| Action | 在已登录用户自己的合成测试线程中加载卡片，选择 `name`，保存并确认；刷新后验证选择保持。随后以服务端竞争更新增加 revision，再从旧卡片提交，观察到受控冲突提示；聊天输入框仍可输入。最后使用 Odoo ORM 按唯一测试标记清理 Session、线程和附件。 |
| Files / Components | 既有 `odoo18ce` 中的临时 HVR 数据；证据见 HVR |
| Contract Reference | CC-TEST-001/002/005/007/009/010 |
| Result | Completed — browser interaction observed and human HVR approved on 2026-10-23 |
| Deviation | None |

## 4. 实际文件清单

| 文件 | 动作 | 内容 | CC |
|---|---|---|---|
| `mymodules/office_engine_m2/__init__.py` | 修改 | 注册 controllers | CC-CHANGE-004 |
| `mymodules/office_engine_m2/__manifest__.py` | 修改 | 版本升至 18.0.3.0.0，注册 Owl 资产 | CC-CHANGE-001 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 修改 | 映射字段和服务端受控写入 | CC-CHANGE-003/005 |
| `mymodules/office_engine_m2/services/__init__.py` | 修改 | 暴露内部服务函数 | CC-CHANGE-003–005 |
| `mymodules/office_engine_m2/services/mapping_service.py` | 修改 | context、保存、确认、取消服务 | CC-CHANGE-002–006 |
| `mymodules/office_engine_m2/controllers/__init__.py` | 新增 | Controller 注册 | CC-CHANGE-004 |
| `mymodules/office_engine_m2/controllers/mapping_controller.py` | 新增 | 四个认证 RPC 路由 | CC-CHANGE-004/005 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/*` | 新增 | Owl、QWeb、样式 | CC-CHANGE-001/002/006 |
| `mymodules/office_engine_m2/tests/__init__.py` | 修改 | 注册测试模块 | CC-TEST-001–008 |
| `mymodules/office_engine_m2/tests/test_mapping_rpc.py` | 新增 | TransactionCase / HttpCase | CC-TEST-003–008 |

本次实现变更均位于冻结 CC §4 白名单。实现代码已提交为 `24d6d4c7a7b28172c156c0b58b46fa1ef78b869d`；关闭处置和追溯文件在后续文档提交中追加。

## 5. 偏离、停止条件与未决事项

| 事项 | 状态 | 处置 |
|---|---|---|
| Implementation Plan 阶段 3 XML-RPC 证据缺口 | Open（沿用 CC 附录 B OPEN-001） | 负责人已批准本 CC 实施，但未将该上游 Gate 缺口改写为 PASS。 |
| HttpCase 浏览器自动化 | Skipped | `websocket-client` 未安装；内置浏览器人工验收已通过，自动化 browser case 缺项仍保留。 |
| M2 AI、Retriever、M1 渲染链路 | Out of scope | 留待 CC-M2-005。 |
| 未授权范围变更 | None | 无。 |

## 6. 交接

实现阶段结束；自动化证据见 ATR，内置浏览器记录见 HVR。负责人已批准 CC 带保留事项关闭；原始自动化/HVR 状态及阶段 Gate 缺口不变。

### IHR-007 — 提交与关闭处置基线

| 字段 | 记录 |
|---|---|
| 阶段 | 关闭 / 基线 |
| Action | 按负责人明确批准将 CC-M2-004 以 `FROZEN WITH OPEN ITEMS` 行政关闭；实现代码提交为 `24d6d4c7a7b28172c156c0b58b46fa1ef78b869d`。将原测试工作树映射到此提交；关闭处置、授权登记和 FR 证据评估另行提交，不改写 ATR/HVR/Plan 原生状态。 |
| Files / Components | CC-M2-004 实现、ATR、HVR、FR、授权登记册 |
| Contract Reference | 负责人 2026-10-23 关闭授权 |
| Result | Committed; push pending |
| Deviation | `HttpCase.browser_js`、HVR 未完成场景和 Plan 阶段 3 Gate 仍分别保持 SKIPPED / NOT RUN / OPEN。 |
