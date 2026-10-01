# TV-09：Serial 唯一性查询索引与性能

## 验证结论

**索引方案可设计，但真实性能尚未验证。**

当前仓库尚未实现盲盘明细模型，也没有 1 万、10 万或 100 万条盲盘测试数据，因此不能宣称任何具体响应时间已经达标。

## 推荐索引

盲盘明细的主要查询是：

```text
product_id + lot_name + 有效状态
```

推荐索引方向：

```text
(product_id, lot_name, serial_uniqueness_active)
```

如果大量查询只针对有效 Serial，应使用仅覆盖有效记录的部分索引。索引设计必须与最终数据库迁移机制一并进入 TDD。

其他辅助索引：

```text
blind_count_id
blind_count_id + state
work_package_id
```

不建议只对 `lot_name` 单独建索引，因为相同 Serial 文本可以属于不同产品。

## 查询性能验证方案

需要准备隔离测试数据集：

| 数据规模 | 目标 |
|---:|---|
| 10,000 | 基线查询 |
| 100,000 | 常规压力 |
| 1,000,000 | 上限风险评估 |

每个数据集应执行：

```python
start = time.perf_counter()
env['blind.count.line'].search_count([
    ('product_id', '=', product.id),
    ('lot_name', '=', serial),
    ('serial_uniqueness_active', '=', True),
])
elapsed_ms = (time.perf_counter() - start) * 1000
```

应同时验证：

- 冷缓存和热缓存；
- 不同产品的同名 Serial；
- 有效、取消、已处理和被替代记录；
- 并发扫描；
- 索引升级后的查询计划。

## 缓存结论

前端缓存只能减少重复的产品条码查询，不能缓存 Serial 唯一性结论。Serial 唯一性必须以服务端数据库结果为准。

如果使用服务端缓存，必须处理：

- 新明细创建；
- 明细撤销；
- 盲盘单取消；
- Recount 替代；
- 处理完成；
- 多进程和多 worker 一致性。

在没有真实性能数据前，不建议增加缓存层。

## 对 SRS 的影响

业务规则无需改变。建议补充：

1. Serial 查询必须有产品+Serial+有效状态索引；
2. 性能阈值必须通过真实规模数据测量；
3. 不用缓存替代服务端唯一性判断；
4. 并发测试和查询性能测试必须分开记录；
5. 性能不达标时优先优化索引和查询域，不引入额外缓存基础设施。

