# TV-01：Odoo 18 CE 按产品大类与货位清除库存

## 1. 验证元数据

| 项目 | 内容 |
|---|---|
| TV 编号 | TV-01 |
| 优先级 | P0 |
| 验证范围 | 按产品大类与货位查询并清除账面库存 |
| Odoo 版本 | 18.0 Community Edition |
| 验证方式 | Odoo Shell、Odoo ORM、Odoo 官方库存模型源码 |
| 生产代码变更 | 无 |
| 最终结论 | 可行，但需要按 Odoo 原生库存调整方式实现 |

## 2. 验证目标

验证以下问题：

1. 如何按产品大类与货位查询现有库存；
2. 是否应直接修改 `stock.quant`；
3. 如何执行库存清除并保留审计记录；
4. 清除后原有 `stock.lot` 是否保留；
5. 清除是否产生库存移动；
6. 清除失败时如何处理事务。

## 3. 按产品大类与货位查询库存

库存余额由 `stock.quant` 表示。推荐使用以下 ORM 域：

```python
domain = [
    ('product_id.categ_id', 'child_of', product_category.id),
    ('location_id', 'child_of', location.id),
    ('quantity', '!=', 0),
]

quants = env['stock.quant'].search(domain)
```

其中：

- `product_id.categ_id` 使用产品模板的产品大类；
- `child_of` 包含指定产品大类的所有子分类；
- `location_id` 使用库存货位；
- `child_of` 包含指定货位下的子货位；
- `quantity != 0` 同时覆盖正库存和负库存；
- 多公司场景必须使用正确的公司上下文和权限范围。

库存汇总可以使用：

```python
groups = env['stock.quant'].read_group(
    domain,
    ['quantity:sum', 'reserved_quantity:sum'],
    ['product_id', 'location_id'],
    lazy=False,
)
```

验证环境结果：

```text
Odoo 版本：18.0
stock.quant 查询：可用
产品大类 + 货位域查询：可用
验证数据库中的非零内部库存：17 条
```

## 4. 库存清除方式

### 4.1 禁止直接写入 `stock.quant.quantity`

以下方式不可采用：

```python
quant.write({'quantity': 0})
```

直接写入会：

- 不产生库存移动；
- 丢失库存变化审计链；
- 可能破坏 `reserved_quantity` 一致性；
- 绕过 Odoo 库存业务逻辑；
- 可能影响批次、序列号和后续库存操作。

### 4.2 使用 Odoo 原生库存调整

推荐使用：

```python
quant.with_context(inventory_mode=True).inventory_quantity = 0
quant.with_context(inventory_mode=True).action_apply_inventory()
```

Odoo 18 的执行路径为：

```text
inventory_quantity
    ↓
inventory_diff_quantity
    ↓
stock.quant._apply_inventory()
    ↓
创建 stock.move / stock.move.line
    ↓
move._action_done()
    ↓
更新库存 quant
```

因此，库存清除应通过库存调整动作完成，而不是直接修改库存余额字段。

## 5. 可运行的 ORM 验证代码

以下脚本用于技术验证。它通过主动抛出异常回滚 savepoint，不保留验证期间的库存变化：

```python
from odoo.tools.float_utils import float_compare

Quant = env['stock.quant']
Move = env['stock.move']

category = env['product.category'].search([], limit=1)
location = env['stock.location'].search(
    [('usage', '=', 'internal')],
    limit=1,
)

domain = [
    ('product_id.categ_id', 'child_of', category.id),
    ('location_id', 'child_of', location.id),
    ('quantity', '!=', 0),
]

quants = Quant.search(domain)

print('CATEGORY:', category.display_name)
print('LOCATION:', location.complete_name)
print('QUANTS:', len(quants))

if quants:
    quant = quants[0]
    before_quantity = quant.quantity
    before_move_count = Move.search_count([])

    try:
        with env.cr.savepoint():
            test_quant = quant.with_context(inventory_mode=True)
            test_quant.inventory_quantity = 0
            test_quant.action_apply_inventory()

            print('QUANTITY_IN_SAVEPOINT:', test_quant.quantity)
            print(
                'MOVES_IN_SAVEPOINT:',
                Move.search_count([]) - before_move_count,
            )

            raise RuntimeError('Rollback technical verification')

    except RuntimeError as error:
        if str(error) != 'Rollback technical verification':
            raise

    env.invalidate_all()
    quant = Quant.browse(quant.id)

    print('QUANTITY_AFTER_ROLLBACK:', quant.quantity)
    print(
        'RESTORED:',
        float_compare(
            quant.quantity,
            before_quantity,
            precision_rounding=quant.product_uom_id.rounding,
        ) == 0,
    )
    print(
        'MOVE_COUNT_AFTER_ROLLBACK:',
        Move.search_count([]) - before_move_count,
    )
```

## 6. 验证结果

验证期间使用一条非零库存记录执行原生库存调整：

```text
清除前数量：16
savepoint 内清除后数量：0
savepoint 内产生库存移动：1
回滚后数量：16
回滚后库存移动数量变化：0
```

结论：

- `stock.quant` 可以按产品大类和货位查询；
- Odoo 原生库存调整可以将范围内库存清除为零；
- 清除会产生可追溯的库存移动；
- 直接写 `stock.quant.quantity` 不符合要求；
- 通过异常回滚的 savepoint 可以撤销验证操作。

注意：savepoint 正常退出时不会自动回滚。测试代码必须显式抛出异常或使用其他明确的回滚方式。

## 7. `stock.lot` 行为

库存清除不会自动删除原有 `stock.lot`：

```text
库存清除 ≠ 删除 stock.lot
```

符合盲盘需求：

- Step 1 只改变库存数量；
- 原批次/序列号主数据保留；
- 不应在清除阶段删除批次或序列号；
- Step 2 再按 `(product_id, lot_name)` 匹配或创建主数据；
- 回滚也不应删除原始批次/序列号记录。

## 8. 库存移动与审计

原生库存调整会创建并完成：

- `stock.move`；
- `stock.move.line`。

库存清除通常表现为：

```text
实际库存货位 → Virtual Locations/Inventory adjustment
```

后续重新入库则相反：

```text
Virtual Locations/Inventory adjustment → 实际库存货位
```

原始库存移动必须保留，回滚应通过反向库存移动完成，不应删除原始记录。

## 9. 事务边界

单次清除和工作包级清除均应在 Odoo 单个事务内执行：

```python
quants.with_context(inventory_mode=True).write({
    'inventory_quantity': 0,
})
quants.with_context(inventory_mode=True).action_apply_inventory()
```

业务方法中不应主动 `commit()`。如果中途失败，应整体回滚：

- 已创建的 `stock.move`；
- 已创建的 `stock.move.line`；
- quant 数量；
- 库存调整状态。

如果将清除拆成多个独立提交，可能出现部分清除、部分失败的不可审计状态。

## 10. 技术风险

| 风险 | 说明 | 建议 |
|---|---|---|
| 直接写 quant | 绕过库存移动和审计 | 禁止直接修改 `quantity` |
| 货位范围遗漏 | 只查询指定货位，不含子货位 | 使用 `location_id child_of` |
| 产品分类范围遗漏 | 只查询精确分类 | 使用 `product_id.categ_id child_of` |
| 预留数量冲突 | 范围内可能存在预留库存 | 清除前检查 `reserved_quantity` |
| 批次/序列号库存 | tracked quant 可能需要逐 quant 调整 | 使用原生库存调整 |
| 负库存遗漏 | 只查询 `quantity > 0` 会漏掉负库存 | 使用 `quantity != 0` |
| 公司隔离 | 多公司可能串数据 | 限定公司和 company context |
| savepoint 误用 | 正常退出不会自动回滚 | 测试必须显式触发回滚 |
| 中途提交 | 可能产生部分清除 | 业务操作中禁止主动提交 |
| 并发变化 | 查询后库存可能被其他操作修改 | 执行前重新校验或加锁 |
| 预留仍存在 | 可能造成库存状态不一致 | 在 TDD 中明确预留处理策略 |

## 11. 对 SRS 的影响

现有 SRS 的业务要求不需要改变。建议在 TDD 或 SRS 的技术约束中明确：

1. 库存清除必须通过 Odoo 原生库存调整或等价的 `stock.move` 完成；
2. 禁止直接写入 `stock.quant.quantity`；
3. 产品大类范围必须包含子分类；
4. 货位范围必须包含子货位；
5. 清除必须覆盖正库存、负库存和批次/序列号库存；
6. 清除前必须定义预留库存处理策略；
7. 清除操作不得主动提交部分事务；
8. 清除失败时必须整体回滚；
9. 生成的 `stock.move` 和 `stock.move.line` 必须保留用于审计。

## 12. 最终结论

```text
TV-01：可行，但需补充技术约束。
```

推荐实施路径：

```text
按产品大类 + 货位查询 stock.quant
    ↓
校验公司、预留、正负库存和 tracked 状态
    ↓
设置 inventory_quantity = 0
    ↓
调用 action_apply_inventory()
    ↓
由 Odoo 创建并完成 stock.move / stock.move.line
    ↓
记录清除操作与库存移动
```
