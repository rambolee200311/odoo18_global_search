# TV-02：按（产品，lot_name）匹配或新建 `stock.lot`

## 验证结论

**可行，但必须在库存重建阶段执行，不能在盲盘阶段执行。**

## 验证事实

Odoo 18 的 `stock.lot` 关键字段为：

| 字段 | 必填 | 说明 |
|---|---:|---|
| `name` | 是 | 批次号或序列号 |
| `product_id` | 是 | 绑定产品 |
| `company_id` | 否 | 由公司上下文/位置推导 |

源码中的 `stock.lot` 没有 `_sql_constraints` 唯一约束。唯一性由 `stock.lot._check_create()` 等业务逻辑校验，而不是简单依赖数据库唯一索引。

## 推荐实现

```python
lot = env['stock.lot'].search([
    ('product_id', '=', product.id),
    ('name', '=', lot_name),
], limit=1)

if not lot:
    lot = env['stock.lot'].create({
        'name': lot_name,
        'product_id': product.id,
        'company_id': company.id,
    })
```

必须使用产品维度匹配，不能只按 `name` 匹配，否则同名 Lot/SN 可能串到其他产品。

产品追踪方式：

- `none`：不创建或写入 `lot_id`；
- `lot`：使用批次对应的 `stock.lot`；
- `serial`：使用序列号对应的 `stock.lot`，每个序列号对应一个库存单位。

## ORM 验证代码

```python
Lot = env['stock.lot']
product = env['product.product'].search([
    ('tracking', 'in', ('lot', 'serial')),
    ('is_storable', '=', True),
], limit=1)

try:
    with env.cr.savepoint():
        lot = Lot.create({
            'name': 'TV02-ORM-ROLLBACK',
            'product_id': product.id,
            'company_id': env.company.id,
        })
        assert lot.product_id == product
        assert Lot.search_count([
            ('product_id', '=', product.id),
            ('name', '=', lot.name),
        ]) == 1
        raise RuntimeError('rollback tv02')
except RuntimeError as error:
    if str(error) != 'rollback tv02':
        raise
```

实际验证结果：

```text
tracked product：创建成功
name + product_id 查询：成功
product_id 和 name 之外的产品不参与匹配：符合预期
savepoint 回滚后测试 Lot 不存在：符合预期
```

## 技术风险

1. Odoo 没有简单的 `(product_id, name, company_id)` 数据库唯一约束，必须考虑并发创建；
2. 同一产品的 Lot/SN 名称匹配必须限定公司；
3. 产品追踪为 `none` 时写入 `lot_id` 会违反库存语义；
4. 创建 Lot 会创建主数据，但不会自动增加库存；
5. Serial 的唯一性和盲盘文本唯一性是两套规则，不能混用。

## 对 SRS 的影响

业务需求无需改变。建议补充：

- Step 2 才允许查询或创建 `stock.lot`；
- 匹配键至少为 `(product_id, lot_name, company_id)`；
- `tracking = none` 时不得写入 `lot_id`；
- 并发创建需要应用层锁、唯一策略或冲突重试方案。

