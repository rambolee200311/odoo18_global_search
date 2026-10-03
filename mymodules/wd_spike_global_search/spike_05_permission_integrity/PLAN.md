# SPIKE-GS-05 权限过滤完整性

## 1. Spike 标识

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-05 |
| 名称 | 权限过滤完整性 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 日期 | 2026-10-02 |

## 2. 验证问题

验证 Global Search 在结果、计数、字段搜索、Preview、Query Understanding 和关联扩展各环节是否遵守 Odoo 权限：

1. 无权记录不出现在结果；
2. 无权记录不进入分类计数；
3. 无权 Searchable Field 不参与搜索；
4. 不因无权字段命中而返回记录；
5. 无权记录不进入 Preview；
6. 无权记录不进入 Query Understanding；
7. 关联扩展每跳应用 Record Rule；
8. 无权关联记录跳过且不泄露数量；
9. 权限异常失败关闭。

## 3. SRS 追溯

- FR-PM-001 ~ FR-PM-008
- FR-ER-003
- CON-008
- CON-011
- AC-016 ~ AC-019
- AC-024

## 4. 测试矩阵

- 公司 A：可见用户 A；
- 公司 B：可见用户 B；
- 两个公司各有一个带 `GS05-` 标记的客户和销售订单；
- 使用 Odoo 标准公司 Record Rule；
- 使用无账户权限用户验证 `res.partner.credit_limit` 字段不可读；
- 通过 `with_user()` 执行所有受限读取。

## 5. 成功标准

| 项目 | 成功标准 |
|---|---|
| 记录访问 | 用户只能看到当前公司记录 |
| 分类计数 | 只统计当前用户可访问的 Result Identity |
| 字段权限 | `credit_limit` 不在可读字段中，不参与搜索 |
| Preview | Preview 二次权限检查失败时不返回数据 |
| Query Understanding | 不为无权记录生成实体/命中提示 |
| 关联扩展 | 关联目标无权时跳过且数量为 0 |
| 失败关闭 | 权限判断异常返回空结果，不返回部分未经确认数据 |

