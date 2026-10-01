# TV-03：按货位重新入库

## 验证结论

**可行，必须通过 `stock.move` / `stock.move.line` 完成，不能直接写 `stock.quant.quantity`。**

## 核心规则

库存重建 Step 2 应创建从库存调整位置到目标货位的库存移动：

```text
Virtual Locations/Inventory adjustment
    →
指定内部货位
```

移动明细应包含：

- `product_id`；
- `product_uom_id`；
- `quantity`；
- `location_id`；
- `location_dest_id`；
- tracked 产品对应的 `lot_id`；
- 不设置 `package_id`，保证托盘不进入库存维度。

Odoo 原生库存调整使用 `_get_inventory_move_values()` 生成 move 和 move line；源码验证确认 move line 会携带 `lot_id`。

## 汇总键

实现前应先按盲盘业务规则汇总：

| 产品追踪 | 汇总键 |
|---|---|
| `none` | 产品 + 货位 |
| `lot` | 产品 + `lot_name` + 货位 |
| `serial` | 产品 + `lot_name` + 货位，每个 SN 数量为 1 |

托盘码只属于盲盘事实，不进入 Odoo 库存 quant 的维度。

## 验证代码片段

```python
quant = env['stock.quant'].search([
    ('quantity', '>', 0),
    ('product_id.tracking', 'in', ('lot', 'serial')),
    ('location_id.usage', '=', 'internal'),
], limit=1)

inventory_location = (
    quant.product_id
    .with_company(quant.company_id)
    .property_stock_inventory
)

move_values = quant._get_inventory_move_values(
    quant.quantity,
    inventory_location,
    quant.location_id,
)

assert move_values['product_id'] == quant.product_id.id
assert move_values['move_line_ids']
assert move_values['move_line_ids'][0][2]['lot_id'] == quant.lot_id.id
```

验证结果：

```text
库存调整 move values：可生成
tracked lot_id 传递到 move line：成功
目标货位：成功
stock.move / stock.move.line 路径：可用
```

## 失败与事务

Step 2 应在一个 Odoo 事务内完成。创建或完成任一移动失败时，应整体回滚该次入库操作，不能保存部分明细。

Step 2 必须满足：

```text
清除状态 = done
处理单已审核
处理明细已冻结
入库状态 = pending
```

## 技术风险

1. Serial 产品必须逐 SN 建立 move line，不能把多个 SN 合并成一条无 lot 的数量；
2. Lot/SN 主数据必须先按 TV-02 匹配或创建；
3. 不应把托盘码写入 `package_id`；
4. 不应使用 `_update_available_quantity()` 作为业务入口，它是库存底层更新方法，不提供完整审计业务；
5. 目标货位、公司和产品 UoM 必须一致；
6. 重复执行必须由处理单状态阻断。

## 对 SRS 的影响

无需改变业务语义。建议在 TDD 中明确：

- Step 2 统一通过库存移动完成；
- 托盘不映射为 `stock.quant.package`；
- Serial 每个 SN 一个 move line；
- Step 2 失败整体回滚；
- 入库成功后保存原始 move/move line 关联。

