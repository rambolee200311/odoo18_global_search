# SPIKE-GS-05 权限过滤完整性报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-05 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 数据库 | `odoo18ce` |
| 数据标记 | `GS05-` |
| 读取/写入入口 | Odoo ORM |

## 2. 摘要

本 Spike 在两家公司中创建了两个最小内部用户、客户和销售订单，并在受限用户上下文中验证 Odoo Model Access、公司 Record Rule、字段权限和关联扩展。

验证结果：

- 公司 A 用户只看到公司 A 的客户和订单；
- 公司 B 用户只看到公司 B 的客户和订单；
- 外部记录不进入结果和分类计数；
- 外部记录不进入 Preview；
- 外部记录不进入 Query Understanding；
- 关联销售订单每一跳应用 Record Rule，无权关联记录数量为 0；
- `res.partner.credit_limit` 对测试用户不可读，已被排除出 Searchable Field；
- 模拟权限判断异常时返回空结果和 0 计数，执行失败关闭。

整体结论：**有条件可行**。已验证路径未发现权限泄露；字段权限、关联扩展和权限异常策略符合 SRS。仍需在真实 Global Search 配置运行时补充更多模型和权限组合。

## 3. SRS 追溯

- FR-PM-001：继承 Model Access、Record Rule 和 Multi-company；
- FR-PM-002：权限不扩大；
- FR-PM-003：无权记录不泄露；
- FR-PM-004：关联扩展每跳应用权限；
- FR-PM-005：字段权限；
- FR-PM-007：Refinement 与权限交互；
- FR-PM-008：多公司；
- FR-ER-003：权限错误分类与失败策略；
- CON-008：安全失败关闭；
- CON-011：无权限字段不参与搜索；
- AC-016 ~ AC-019、AC-024。

## 4. 测试数据与权限矩阵

| 公司 | 用户 | 客户 | 销售订单 |
|---|---|---|---|
| Company 1 | `gs05_user_1@example.test` | `GS05-PARTNER-1` | `GS05-ORDER-1` |
| Company 2 | `gs05_user_2@example.test` | `GS05-PARTNER-2` | `GS05-ORDER-2` |

用户使用标准 `base.group_user` 和 Sales Manager 业务读取组，不使用 `sudo()`。公司上下文通过每个用户的 `company_id` 和 `company_ids` 设置。

## 5. 结果

### 5.1 记录结果与计数

| 用户公司 | 可见客户数 | 可见订单数 | 外部客户可见 | 外部订单可见 |
|---|---:|---:|---|---|
| Company 1 | 1 | 1 | 否 | 否 |
| Company 2 | 1 | 1 | 否 | 否 |

`search()` 与 `search_count()` 均在受限用户上下文执行。外部公司的记录既不返回，也不进入分类计数。

### 5.2 Preview

Preview 使用受限用户再次通过 `search([("id", "=", record_id)])` 校验，而不是信任已有 Recordset：

| 用户公司 | 自有记录 Preview | 外部记录 Preview |
|---|---|---|
| Company 1 | 可访问 | 不可访问 |
| Company 2 | 可访问 | 不可访问 |

这证明无权记录在 Preview 阶段不会因已知 ID 而被返回。

### 5.3 Query Understanding

实体命中查询在用户公司上下文执行：

| 用户公司 | 自有实体命中 | 外部实体命中 |
|---|---:|---:|
| Company 1 | 1 | 0 |
| Company 2 | 1 | 0 |

因此无权记录不会出现在实体解析、匹配提示或 Query Understanding。

### 5.4 字段权限

测试用户没有账户权限组，`res.partner.credit_limit` 不出现在其 `fields_get()` 可读字段集合中：

| 检查项 | 结果 |
|---|---|
| `credit_limit` 可读 | 否 |
| 从 Searchable Field 排除 | 是 |
| 因禁止字段命中返回记录 | 否 |

运行时不得把配置管理员可见字段直接作为普通用户的搜索字段；本结果证明了按当前用户重新检查字段权限的必要性。

### 5.5 关联扩展

通过 `sale.order.partner_id` 从客户扩展到订单：

| 用户公司 | 自有关联订单 | 外部关联订单 | 外部关联计数 |
|---|---:|---:|---:|
| Company 1 | 1 | 0 | 0 |
| Company 2 | 1 | 0 | 0 |

关联记录无权时被跳过，且没有通过关联数量泄露外部记录存在性。

### 5.6 权限异常失败关闭

模拟主记录权限判断异常：

```json
{
  "status": "PERMISSION_DENIED",
  "records": [],
  "count": 0
}
```

没有返回未经权限确认的部分结果，符合 CON-008 和 FR-ER-003。

## 6. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 无权记录不出现在结果 | 通过 | `no_foreign_visibility=true` |
| 无权记录不出现在计数 | 通过 | `no_foreign_count=true` |
| 无权字段不参与搜索 | 通过 | `credit_limit` 不可读且已排除 |
| 不因无权字段命中返回 | 通过 | `search_result_from_forbidden_field=false` |
| 无权记录不出现在 Preview | 通过 | `no_foreign_preview=true` |
| 无权记录不出现在 Query Understanding | 通过 | `no_foreign_understanding=true` |
| 关联每跳应用 Record Rule | 通过 | `relation_rule_applied=true` |
| 关联无权不泄露数量 | 通过 | 外部关联计数为 0 |
| 权限异常失败关闭 | 通过 | 空结果、0 计数、`PERMISSION_DENIED` |

## 7. 限制与后续工作

1. 本 Spike 使用标准公司 Record Rule 和最小测试用户，尚未覆盖自定义复杂 Record Rule；
2. 字段权限使用标准账户字段 `credit_limit`，后续需覆盖多个 Searchable Field 配置；
3. 尚未覆盖多跳 Relation Path（深度 2）和跨模型混合部分失败；
4. Preview 和 Query Understanding 的验证使用 ORM 等价测试路径，生产 UI 尚需 Human Review；
5. 需要补充门户用户、无模型 ACL、无权限判断字段读取异常和多公司共享记录场景。

## 8. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_05_permission_integrity/data/generate_orm.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_05_permission_integrity/scripts/run.py
```

## 9. 产出物

- `PLAN.md`
- `README.md`
- `data/generate_orm.py`
- `scripts/run.py`
- `results/simulation_result.json`
- `results/spike_result.json`
- `reports/REPORT.md`

