# TV-05：通过反向库存移动实现回滚

## 验证结论

**需调整：标准退货机制不能直接覆盖库存调整移动，项目需要实现受控的反向库存移动。**

## Odoo 原生能力

Odoo 的 `stock.return.picking` 向导要求来源是 `stock.picking`，并通过：

```python
origin_returned_move_id
```

建立退货移动关系。

但是库存清除和库存重建使用的是 `is_inventory = True` 的库存调整移动，这些移动通常没有 `picking_id`。源码和验证数据库均确认：

```text
库存调整移动数量：存在
带 picking_id 的库存调整移动：0
```

因此不能直接调用标准 `stock.return.picking` 向导完成 Step 1/Step 2 回滚。

## 推荐方案

项目处理模型应记录每一步产生的原始库存移动。回滚时由受控业务方法创建反向 move：

```python
reverse_move = env['stock.move'].create({
    'name': 'Rollback of %s' % original_move.display_name,
    'product_id': original_move.product_id.id,
    'product_uom': original_move.product_uom.id,
    'product_uom_qty': original_move.quantity,
    'location_id': original_move.location_dest_id.id,
    'location_dest_id': original_move.location_id.id,
    'company_id': original_move.company_id.id,
    'is_inventory': True,
    'picked': True,
    'move_line_ids': [(0, 0, {
        'product_id': original_move.product_id.id,
        'product_uom_id': original_move.product_uom.id,
        'quantity': original_move.quantity,
        'location_id': original_move.location_dest_id.id,
        'location_dest_id': original_move.location_id.id,
        'lot_id': move_line.lot_id.id,
    }) for move_line in original_move.move_line_ids],
})
reverse_move._action_done()
```

实际实现必须按 move line 逐行保留：

- 产品；
- 数量；
- UoM；
- lot/serial；
- owner；
- package（如果业务允许）；
- 公司；
- 源/目标货位。

## 回滚不变量

```text
原始 move 保留
反向 move 新建
原始 move 不删除
回滚状态记录为 rolled_back
回滚人、时间、原因必填
```

回滚后应验证：

- Step 2 回滚后库存恢复到 Step 1 完成后的状态；
- Step 1 回滚前，Step 2 必须已经回滚；
- 原始库存移动和反向库存移动均可追溯；
- 不允许重复回滚同一步骤。

## 技术风险

1. 自建反向 move 必须正确复制所有 move line 维度；
2. Serial 库存不能按总数量合并；
3. 原移动已被后续业务消耗时，直接反向可能失败；
4. 回滚不能删除 `stock.move` 或 `stock.move.line`；
5. 多次回滚和重执行必须通过步骤状态和 move 关联去重；
6. 回滚必须使用与原始移动相同的公司和 UoM。

## 对 SRS 的影响

SRS 的“反向库存移动”要求仍然可实现，但应在 TDD 中明确：

- 标准 picking return 不是库存调整回滚方案；
- 项目需要封装库存调整移动的反向业务动作；
- 反向 move 必须关联原 move；
- 回滚动作必须记录原因、人和时间；
- 回滚顺序和幂等性由处理单状态强制保证。

