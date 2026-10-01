# TV-07：跨工作包、货位和托盘的 Serial 唯一性查询

## 验证结论

**可行，但当前仓库尚未实现盲盘模型，实际业务查询和性能尚未最终验证。**

当前 Odoo 数据库没有 `blind.count.line` 模型，因此本轮只能验证查询设计、索引需求和 Odoo ORM 能力，不能宣称真实盲盘数据性能已通过。

## 规则定义

Serial 重复判定键：

```text
product_id + lot_name
```

查询范围：

- 跨工作包；
- 跨盲盘单；
- 跨货位；
- 跨托盘。

排除：

- 盲盘单已处理完成；
- 盲盘单 `cancel`；
- 被 Recount 替代的盲盘单。

建议将“是否参与唯一性判定”作为盲盘单状态和替代标记的明确业务谓词，而不是仅根据明细创建时间判断。

## ORM 查询设计

推荐在后端业务方法中使用 ORM：

```python
domain = [
    ('product_id', '=', product.id),
    ('lot_name', '=', serial),
    ('blind_count_id.state', 'not in', ('cancel', 'done')),
    ('blind_count_id.is_replaced', '=', False),
]

duplicate = self.env['blind.count.line'].search_count(domain)
if duplicate:
    raise UserError('该序列号已被盘点，请勿重复扫描')
```

实际项目模型应根据最终字段名调整 `blind_count_id`、`state` 和 `is_replaced`。

唯一性查询不能读取 `stock.lot` 或库存 quant，因为盲盘阶段必须与库存主数据和库存余额隔离。

## 索引建议

盲盘明细至少需要：

```text
(product_id, lot_name)
```

同时应为父单状态和替代标记提供可用索引或稳定的存储字段，避免每次扫描都对大量父单做复杂连接过滤。

推荐设计：

```text
blind.count.line:
    product_id
    lot_name
    serial_uniqueness_active
    blind_count_id
```

并对有效记录建立唯一性策略。`serial_uniqueness_active` 必须由服务端状态动作维护，不能只依赖前端。

## ORM 与 SQL

项目业务入口必须使用 Odoo ORM，不能用裸 SQL 绕过权限和业务约束。

数据库级索引可以作为模块架构的一部分，但不能把原始 SQL 查询作为业务接口。最终 TDD 需要明确索引创建方式和升级路径。

## 性能结论

本仓库尚无盲盘明细表和测试数据，无法给出 1 万条数据的真实响应时间。因此本 TV 的性能状态为：

```text
查询设计：可行
真实性能阈值：未验证
```

## 对 SRS 的影响

业务规则无需改变。应在 TDD 中补充：

1. 唯一性只查询盲盘明细；
2. 已处理、取消、被替代的盲盘单不参与判定；
3. Serial 唯一性不得依赖 `stock.lot`；
4. 必须提供有效记录查询索引；
5. 真实性能需使用 1 万、10 万和更大数据集单独验证。

