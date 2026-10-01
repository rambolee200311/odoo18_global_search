# TV-17：复核明细与盲盘明细匹配

## 验证结论

**可行。需要双向匹配，不能只找“复核记录对应的盲盘行”。**

## 匹配键

正常匹配键：

```text
product + package_code + lot_name
```

但复核允许产品、托盘和 Serial 异常，因此实现时应保留原始输入，并使用规范化键进行匹配。

## 双向结果

复核输入对应不到盲盘明细时：

```text
not_in_blind
```

盲盘明细没有被任何复核明细覆盖时：

```text
not_covered
```

匹配成功但数量不同：

```text
not_matched
```

产品或 Serial 不合法时：

```text
out_of_scope / not_matched
```

## 实现建议

后端一次加载当前盲盘单的明细并构造字典：

```python
blind_by_key = {
    (line.product_id.id, line.package_code, line.lot_name): line
    for line in blind_lines
}
reviewed_keys = set()
```

完成复核后，对 `blind_by_key.keys() - reviewed_keys` 生成未覆盖状态。数据量较大时应使用批量读取和索引，避免逐行 RPC。

## 对 SRS 的影响

业务需求无需改变；TDD 应冻结匹配键、空值规范化、双向状态和展示文案。

