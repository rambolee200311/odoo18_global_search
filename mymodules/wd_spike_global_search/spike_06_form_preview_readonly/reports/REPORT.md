# SPIKE-GS-06 Form Preview 只读嵌入报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-06 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 数据库 | `odoo18ce` |
| Preview 用户 | GS-05 Company 1 用户 |
| 读取方式 | Odoo ORM |

## 2. 摘要

本 Spike 使用三个真实 Odoo 模型和真实 `ir.ui.view` Form View，在受限用户上下文中加载 Preview：

- `res.partner`
- `sale.order`
- `stock.picking`

三个 Form View 均成功加载。Preview 读取未执行 ORM 写入，未触发 onchange；只读策略明确禁止编辑、保存、删除、业务按钮、Chatter、附件和活动操作。

记录删除或权限变化统一进入安全状态，不返回记录。切换记录只改变 selected record，保留 Raw Query 和 Refinement。窄屏从左右分栏安全降级为单栏 Preview。

整体结论：**有条件可行**。真实 Form View 嵌入所需的读取链路可行，但只读操作拦截和窄屏布局必须由后续前端实现强制执行。

## 3. SRS 追溯

- FR-SW-004：桌面端左右分栏 Search Workspace；
- FR-SW-007：Preview 只读、禁止编辑/保存/按钮/Chatter/附件/活动；
- CON-009：Preview 只读；
- AC-013：加载真实 Form View；
- AC-014：禁止编辑、保存和业务按钮。

## 4. 测试模型与真实 View

| 模型 | 记录 | Form View | 加载状态 | 记录可读 |
|---|---:|---|---|---|
| `res.partner` | 6143 | `res.partner.form`（126） | LOADED | 是 |
| `sale.order` | 5050 | `sale.order.form`（1305） | LOADED | 是 |
| `stock.picking` | 31 | `stock.picking.form`（700） | LOADED | 是 |

View 通过 `model.with_user(preview_user).get_view(view_id=..., view_type="form")` 加载，而不是复制或重写官方 Form View。

## 5. 结果

### 5.1 Form View 可行性

三个模型的真实表单架构均非空并成功加载：

```text
all_forms_loaded = true
```

原始 Form View 中存在按钮节点：

- `res.partner`：7
- `sale.order`：17
- `stock.picking`：17

这说明 Preview 不能只依赖原始 View 的自然状态；必须在 Preview 容器和客户端动作层强制只读策略。

### 5.2 只读和副作用

每个 Preview 均使用以下策略：

| 能力 | Preview |
|---|---|
| Create | 禁止 |
| Edit | 禁止 |
| Delete | 禁止 |
| Save | 禁止 |
| Business Buttons | 禁止 |
| Chatter Post | 禁止 |
| Attachment Upload | 禁止 |
| Activity Actions | 禁止 |

验证结果：

- `onchange_invoked=false`
- `orm_write_count=0`
- `readonly_policies=true`

本 Spike 只执行读取和 View 加载，不调用 write、create、unlink、按钮方法或 Chatter 方法，因此未产生业务副作用。

### 5.3 删除或权限变化

两种不可用状态均统一为：

```text
PERMISSION_OR_DELETED
```

验证场景：

- 不存在的记录 ID：安全状态；
- 另一公司的无权记录：安全状态；
- 安全提示：`Record unavailable or permission changed`。

这避免向用户泄露记录是“已删除”还是“权限变化”的具体原因。

### 5.4 切换记录

切换前后状态：

| 状态项 | 切换前后 |
|---|---|
| Raw Query | 保持 |
| Refinement | 保持 |
| Selected Record | 从 `res.partner` 切换到 `sale.order` |
| 完整搜索重跑 | 不需要 |

结果为：

```text
switch_preserves_query_state = true
```

### 5.5 窄屏降级

| 屏幕 | 布局 |
|---|---|
| Desktop | `split_results_and_preview` |
| Narrow | `single_pane_selected_preview` |

窄屏仅改变布局，不恢复编辑能力；完整记录操作通过新浏览器 Tab 打开标准 Form View。

## 6. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 嵌入真实 Form View | 通过 | 三个真实 View 均 LOADED |
| 不触发 onchange | 通过（只读读取路径） | `onchange_invoked=false` |
| 不可编辑/保存/按钮 | 通过（策略验证） | 全部策略为 false |
| 不触发 Chatter 操作 | 通过 | 未调用写入或 Chatter 方法 |
| 删除/权限变化安全处理 | 通过 | 统一 `PERMISSION_OR_DELETED` |
| 切换状态正确 | 通过 | Query/Refinement 保持 |
| 窄屏安全降级 | 通过（布局策略） | 单栏 Preview 且保持只读 |

## 7. 限制与后续工作

1. 本 Spike 验证 ORM View 加载和只读策略，不实现 Web Client 前端容器；
2. 原始 Form View 仍包含按钮节点，TDD 必须定义按钮屏蔽、字段 readonly 和动作拦截的客户端机制；
3. Chatter 节点是否由具体继承 View 注入，需要在最终 Web Client 组合 View 中再做 Human Review；
4. 需要通过浏览器测试验证鼠标、键盘、快捷键和 RPC 层均无法触发写操作；
5. 需要验证 Preview 记录权限在已打开后发生变化时的实时刷新行为。

## 8. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_06_form_preview_readonly/data/generate_orm.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_06_form_preview_readonly/scripts/run.py
```

## 9. 产出物

- `PLAN.md`
- `README.md`
- `data/generate_orm.py`
- `scripts/run.py`
- `results/view_snapshot.json`
- `results/spike_result.json`
- `reports/REPORT.md`

