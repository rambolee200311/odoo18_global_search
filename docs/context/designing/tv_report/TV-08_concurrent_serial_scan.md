# TV-08：并发扫描 Serial 的唯一性保证

## 验证结论

**应用层搜索不足以保证并发唯一性，需采用数据库约束或数据库锁方案。**

典型竞态：

```text
PDA A：查询 Serial，不存在
PDA B：查询 Serial，不存在
PDA A：创建明细
PDA B：创建明细
```

如果只使用 ORM `search_count()` 再 `create()`，两个事务都可能成功。

## 推荐设计

将参与唯一性判断的状态物化到明细行，例如：

```text
serial_uniqueness_active = True / False
```

对有效 Serial 建立数据库唯一策略：

```text
(product_id, lot_name, serial_uniqueness_active)
```

实际工程中更适合使用“仅 active=true 生效”的部分唯一索引。因为 Odoo `_sql_constraints` 的普通唯一约束无法表达“只对有效记录唯一”的条件，最终 TDD 必须明确模块升级时的索引创建方式。

## 冲突处理

后端仍应先做 ORM 查询以返回友好错误，但必须捕获数据库唯一冲突并转换为标准用户错误：

```python
try:
    line = self.env['blind.count.line'].create(vals)
except IntegrityError:
    raise UserError('该序列号已被盘点，请勿重复扫描')
```

不能宽泛捕获所有异常，也不能把冲突吞掉后返回成功。

## 锁方案

对“尚未存在的 Serial”无法锁定一条不存在的明细行，因此只使用行锁不能解决首次并发创建。

可选方案：

1. 数据库唯一索引，优先；
2. 按产品和 Serial 使用数据库 advisory lock；
3. 为 Serial 建立独立的业务锁记录。

应用层 Python 锁或前端缓存不能作为并发一致性保证。

## 并发验证代码结构

最终模型完成后，应使用两个独立 Odoo 游标/事务执行：

```python
# transaction A and transaction B both call the same business action
line_a = blind_count_line.create_from_scan(product, serial)
line_b = blind_count_line.create_from_scan(product, serial)

# Exactly one transaction must commit.
```

验证重点：

- 一个事务成功；
- 另一个事务收到唯一冲突；
- 冲突事务不产生部分明细；
- 用户看到明确的重复 Serial 错误。

## 技术风险

1. ORM 搜索加创建存在 TOCTOU 竞态；
2. 相关字段的存储状态变化必须与父单状态同步；
3. Recount、cancel 和处理完成时要正确释放唯一性占用；
4. 批量二维码必须在同一事务内整体校验和写入；
5. 唯一冲突必须转换为业务错误，不能返回成功。

## 对 SRS 的影响

现有 Serial 唯一性规则无需改变。建议增加技术约束：

- 唯一性必须在数据库并发层面保证；
- 应用层查询只负责提前提示；
- 并发冲突必须整体失败；
- 释放唯一性占用必须由受控状态动作完成；
- 必须有两个独立事务的并发测试。

