# SPIKE-GS-06 Form Preview 只读嵌入

## 1. Spike 标识

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-06 |
| 名称 | Form Preview 只读嵌入 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 日期 | 2026-10-02 |

## 2. 验证问题

1. 是否能加载真实 Odoo Form View；
2. 只读加载是否触发 onchange；
3. 是否阻止编辑、保存和业务按钮；
4. 是否阻止 Chatter、附件和活动操作；
5. 记录删除或权限变化时是否安全处理；
6. 切换记录时是否保留搜索状态；
7. 窄屏时是否安全降级。

## 3. SRS 追溯

- FR-SW-004
- FR-SW-007
- CON-009
- AC-013
- AC-014

## 4. 测试模型

- `res.partner`
- `sale.order`
- `stock.picking`

使用真实 `ir.ui.view` Form View 和受限用户 ORM 上下文读取。

## 5. 成功标准

| 项目 | 成功标准 |
|---|---|
| Form View | 三个模型均能加载真实表单架构 |
| 只读 | 禁止 create/edit/delete/write 和业务按钮 |
| 无副作用 | Preview 读取不触发 onchange、写入或 Chatter 操作 |
| 安全状态 | 删除/权限变化显示安全状态，不返回数据 |
| 切换 | 只替换 selected record，Raw Query/Refinement 不变 |
| 窄屏 | 从双栏降级为单栏，不出现越权操作 |

