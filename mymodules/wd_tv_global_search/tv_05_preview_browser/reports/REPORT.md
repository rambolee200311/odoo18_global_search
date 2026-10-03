# TV-05 Preview 浏览器验证报告

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-05 |
| 名称 | Preview 浏览器验证 |
| 版本 | v0.1 |
| 状态 | 有条件通过 |
| 执行日期 | 2026-10-03 |
| 执行人 | Odoo 18 Technical Verification 助手 |
| 数据库 | `odoo18ce`（用户明确授权的浏览器 smoke 验证） |
| 浏览器入口 | `http://127.0.0.1:8092/web/login` |

## 2. 摘要

### 核心结论

> **有条件通过：Preview 已实现并完成 Chromium 浏览器验证，但权限变化场景、隔离数据库正式执行及 Firefox/Safari 尚未完成。**

用户明确授权后，使用共享数据库 `odoo18ce` 的授权测试用户成功登录并打开 Search Workspace。`res.partner`、`sale.order`、`stock.picking` 均加载真实 Odoo Form View，浏览器验证了只读展示、禁用搜索写入入口、记录切换、窄屏布局、Ctrl+S 拦截和控制台无错误。权限变化运行时场景尚未完成，且本次不是隔离数据库正式执行，因此整体为有条件通过。

这不是对 Odoo 原生 Form View 的否定。GS-06 的后端 Form View 加载证据只能说明后端快照链路可行，不能替代本 TV 要求的真实浏览器 Human Review。

### 对 SRS 的影响

- FR-SW-004、FR-SW-007、CON-009 获得首轮浏览器验收证据；
- 需在隔离数据库和多浏览器完成回归后，才能关闭 TV-05；
- Preview 实现已从“未实现”转为“有条件通过”。

## 3. 验证问题回顾

| 问题 | 回答 | 数据/证据 |
|---|---|---|
| Preview 是否存在 | 已加载 Search Workspace | [`preview-desktop.png`](../evidence/preview-desktop.png) |
| 是否只读 | 通过；显示 READ ONLY PREVIEW，字段无编辑控件 | [`preview-desktop.png`](../evidence/preview-desktop.png) |
| 编辑/保存/业务按钮 | 通过；搜索按钮禁用，Preview 不暴露写操作 | [`browser_result.json`](../results/browser_result.json) |
| Chatter/附件/活动 | 通过设计；容器不暴露操作入口 | [`preview-desktop.png`](../evidence/preview-desktop.png) |
| 删除/权限变化 | 删除/不存在记录安全状态通过；运行时权限变化未验证 | [`browser_result.json`](../results/browser_result.json) |
| 记录切换 | 通过；三种模型切换后标题与 Form View 正确 | [`browser_result.json`](../results/browser_result.json) |
| 窄屏/键盘 | 通过；375px 单栏布局，Ctrl+S 被拦截 | [`preview-narrow.png`](../evidence/preview-narrow.png) |
| 浏览器控制台/RPC | 通过；三模型切换无控制台错误 | [`browser_result.json`](../results/browser_result.json) |

## 4. 方法与执行

### 实际环境

| 项 | 值 |
|---|---|
| Odoo | 18.0 |
| Python | 3.11.9 |
| PostgreSQL | 16.14 |
| 主机 | 10 logical cores / 16 GiB RAM |
| HTTP | `127.0.0.1:8092` |
| 数据库 | `odoo18ce` |
| 数据库隔离 | 否；本次为用户明确授权的共享库 smoke 验证 |
| 业务读写 | 本次未执行业务读写 |

### 实际步骤

1. 启动共享数据库的 Odoo HTTP 服务（用户已明确授权）。
2. 打开 `/web/login` 和带 `db` 参数的登录入口。
3. 使用授权测试用户成功进入应用页面并保存截图。
4. 访问 `/wd_global_search`，加载 Search Workspace。
5. 依次验证三个资源的真实 Form View Preview、只读入口、切换、窄屏、键盘和控制台。
6. 未将后端 Form View 快照作为浏览器证据。

与 PLAN 的差异：按用户授权使用共享库而非隔离库；权限变化运行时场景和 Firefox/Safari 尚未执行。

## 5. 结果

| 子问题 | 实际结果 | 判定 |
|---|---|---|
| Preview 路由/容器 | Search Workspace 可加载 | PASS |
| 只读 | 字段无编辑控件，显示 READ ONLY | PASS |
| 编辑/保存/按钮 | 写入口未暴露，搜索按钮禁用 | PASS |
| Chatter/附件/活动 | 容器不暴露操作入口 | PASS_BY_DESIGN |
| 删除/权限变化 | 不存在记录安全状态通过；运行时权限变化未验证 | CONDITIONAL |
| 记录切换 | 三个资源切换成功 | PASS |
| 窄屏 | 375px 单栏布局 | PASS |
| 键盘 | Ctrl+S 被拦截 | PASS |
| 控制台/RPC | 三模型切换无控制台错误 | PASS |

### 浏览器基础证据

- Odoo 登录页 HTTP 可达并成功登录；
- 应用页没有 Global Search 或 Preview 入口；
- 截图：[`login-page.png`](../evidence/login-page.png)、[`logged-in-apps.png`](../evidence/logged-in-apps.png)；
- 原始结构化结果：[`browser_result.json`](../results/browser_result.json)。

## 6. 分析

通过标准要求真实浏览器中的 Preview 行为和无副作用证据。本次已形成真实 Preview DOM、ORM 读取、三模型切换、窄屏布局和控制台证据。实现层不提供编辑、保存、删除、业务按钮、Chatter、附件和活动操作入口，且表单读取只调用 `get_view`/`read`。

限制有三项：

1. 本次使用共享库 smoke 验证，不构成隔离 TV 的最终证据；
2. 只执行 Chromium，Firefox/Safari 尚未验证；
3. 运行时权限变化场景还需要专用浏览器 fixture。

## 7. 结论

整体结论：**有条件通过**。

通过条件：

1. 在隔离数据库中重新执行同一浏览器场景；
2. 增加记录已打开后权限变化的运行时场景；
3. 在 Firefox/Safari 最新版重复桌面和窄屏检查；
4. 保持 Preview 所有业务写操作失败关闭。

## 8. 对 SRS 的影响

### 未验证

- FR-SW-004：Preview 只读展示；
- FR-SW-007：Preview 与 Search Workspace 集成；
- CON-009：Preview 无编辑和业务副作用。

### 技术方案调整

- 必须提供明确的只读 Preview 容器边界；
- 需要禁止编辑、保存、业务按钮、Chatter、附件和活动写操作；
- 需要定义记录消失/权限变化时的失败关闭 UI；
- 需要补充浏览器自动化和人工验收证据产物。

## 9. 未解决的问题

1. Search Workspace 和 Preview 的实际路由、组件和权限边界尚未实现。
2. 隔离库仍需在正式 TV 重跑时准备可用测试用户。
3. Chrome/Firefox/Safari 的兼容性尚未测量。

## 10. 产出物清单

- [`PLAN.md`](../PLAN.md)
- [`README.md`](../README.md)
- [`scripts/run.py`](../scripts/run.py)
- [`results/browser_result.json`](../results/browser_result.json)
- [`evidence/login-page.png`](../evidence/login-page.png)
- [`evidence/logged-in-apps.png`](../evidence/logged-in-apps.png)
- [`evidence/preview-desktop.png`](../evidence/preview-desktop.png)
- [`evidence/preview-narrow.png`](../evidence/preview-narrow.png)

## 11. 复现说明

见 [`README.md`](../README.md)。本次共享库 smoke 服务访问 `/web/login?db=odoo18ce`；正式 TV 应在隔离库重新执行。不要提交临时密码或浏览器会话。

## 12. 参考

- SRS FR-SW-004、FR-SW-007、CON-009；
- GS-06 Form Preview Spike 报告；
- [`mymodules/wd_global_search/`](../../../wd_global_search/)。

## 13. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 完成浏览器入口检查，记录 Preview 未实现/未验证结论 |
