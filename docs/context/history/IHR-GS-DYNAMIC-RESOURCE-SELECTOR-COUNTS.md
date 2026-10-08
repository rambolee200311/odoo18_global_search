# IHR-GS-DYNAMIC-RESOURCE-SELECTOR-COUNTS

## 状态

CC-012 已批准冻结并进入实施。

## 实施范围

CC-012 已接入 Published Configuration 驱动的 Resource Descriptor、多选
Resource Selector、权限安全的 Resource Count，以及未知 Resource key 的拒绝。

## 关键实现

- Workspace 从当前 Published Snapshot 读取 Resource，而不是使用静态模型列表；
- Workspace 先经过 `authorize_resource`，无读权限的 Resource 不显示；
- 前端使用 `Set` 维护多选 Resource，空集合表示全部授权 Resource；
- Search 请求使用同一 Published Resource key；
- Facade 拒绝不属于当前 Published Snapshot 的未知 key；
- Executor 在 Permission Boundary 后使用 `search_count()` 计算匹配总数；
- Aggregator 将成功 Resource count 写入 `counts.by_resource`，失败 Resource 不伪造 count；
- Workspace 显示 `label + count`，并在 Query、Resource 或 Refinement 变化后刷新；
- JS cache version 更新为 `cc012`，避免浏览器继续使用旧 Selector 代码。

## 验证

通过：

```bash
./venv/bin/python -m compileall -q mymodules/wd_global_search
node --check mymodules/wd_global_search/static/src/js/preview.js
git diff --check
```

浏览器验证通过：

- Published Configuration 自动显示 Warehouse、Storage Location、Product、
  Contact、Stock Transfer、Sales Order、Purchase Order；
- `GS-CUSTOMER-001` 返回 Contact `1`、Stock Transfer `20`、Sales Order `20`；
- Contact 与 Sales Order 可同时选中；
- 多选后结果按 Resource scope 过滤；
- Count 从 `—` 更新为真实匹配数量。

## 当前限制

- 当前仅完成 Chromium 浏览器验证；
- Firefox、Safari、Edge 及窄屏矩阵尚未执行；
- Odoo 原生 unittest 直接导入方式受 Odoo addon import 约束，未作为独立
  `unittest` 命令执行；compileall、JavaScript syntax check 和浏览器 API/UI
  验证已完成；
- Odoo cron 线程仍有环境相关异常，未发现影响本 CC Search Workspace 的证据。
