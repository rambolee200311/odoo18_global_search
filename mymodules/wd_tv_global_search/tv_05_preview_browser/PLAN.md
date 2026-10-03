# TV-05 Preview 浏览器验证

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-05 |
| 名称 | Preview 浏览器验证 |
| 版本 | v0.1 |
| 状态 | 已执行 |
| 负责人 | Odoo 18 Technical Verification 助手 |
| 日期 | 2026-10-03 |

## 2. 背景与动机

验证 SRS FR-SW-004、FR-SW-007、CON-009，以及 GS-06 关于真实 Odoo Form View 可加载但尚未完成人工浏览器验证的结论。目标是确认 Search Workspace 的 Preview 在真实浏览器中只读、无副作用并能安全降级。

## 3. 验证问题

1. Preview 是否存在并能加载三种模型（`res.partner`、`sale.order`、`stock.picking`）。
2. Preview 是否只读，不能编辑、保存或执行按钮。
3. 是否阻止 Chatter、附件和活动操作。
4. 记录删除或权限变化时是否安全处理。
5. 切换记录、窄屏和键盘操作是否安全。
6. 浏览器控制台和 RPC 是否无未预期错误。

Preview 不存在或无法进入时，相关子问题判定为 `NOT_VERIFIED`，不得以后端 Form View 结果替代浏览器证据。

## 4. 假设

- 使用隔离数据库 `wd_tv_gs01_20261002_100k`，不访问共享数据库。
- 浏览器为 Playwright 驱动的 Chromium；浏览器基础登录页可访问。
- 当前 `wd_global_search` 目录为空时，预期结果是 Preview 未实现，而非通过。

## 5. 范围

### In Scope

- Odoo HTTP 登录入口；
- Search Workspace/Preview 路由、菜单和容器存在性；
- 三种业务模型的只读 Preview；
- 浏览器控制台、网络/RPC、窄屏和键盘行为。

### Out of Scope

- 修改 `odoo/` 或官方 addons；
- 直接数据库读写；
- `sudo()`；
- 用后端快照冒充浏览器验证；
- Elasticsearch、OpenSearch、LLM 或向量检索。

## 6. 方法

1. 启动隔离数据库 HTTP 服务 `127.0.0.1:8091`。
2. 打开 `/web/login`，记录页面、控制台和截图。
3. 尝试以隔离库用户登录。
4. 登录成功后检查 Search Workspace、三种模型 Preview、编辑/按钮/Chatter/附件/活动、删除权限变化、记录切换、窄屏和键盘。
5. 登录失败或路由不存在时，记录阻断原因并将 Preview 子问题标记为 `NOT_VERIFIED`。
6. 保存 JSON 结果、截图和复现说明。

## 7. 通过标准

- Preview 能在真实浏览器加载；
- 任何输入、保存、业务按钮、Chatter、附件和活动操作均不能产生业务副作用；
- 删除/权限变化安全失败；
- 记录切换状态正确；
- 窄屏安全降级；
- 无未预期控制台错误；
- 每个结论都有浏览器证据。

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| Preview 模块尚未实现 | 明确记录 `NOT_VERIFIED`，不宣称通过 |
| 测试污染业务记录 | 仅使用隔离数据库和固定测试标记 |
| 登录失败 | 保存登录页面和错误信息，区分基础入口与 Preview |
| 浏览器工具不可复现 | README 提供 URL、命令和人工步骤 |

## 9. 产出物

- `PLAN.md`、`README.md`
- `scripts/run.py`
- `results/browser_result.json`
- `evidence/login-page.png`
- `reports/REPORT.md`

## 10. 参考

- SRS FR-SW-004、FR-SW-007、CON-009；
- GS-06 报告；
- `mymodules/wd_global_search/` 当前实现目录。

## 11. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 完成浏览器入口检查和 Preview 未实现证据记录 |
