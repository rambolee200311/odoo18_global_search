# TV-04 复杂权限场景报告

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-04 |
| 名称 | 复杂权限场景 |
| 版本 | v0.2 |
| 状态 | 有条件通过 |
| 执行日期 | 2026-10-03 |
| 执行人 | Odoo 18 Technical Verification 助手 |
| 数据库 | `wd_tv_gs01_20261002_100k` |
| 数据标记 | `TV04-` |

## 2. 摘要

### 核心结论

> **有条件通过。**

最终验证在隔离数据库中覆盖了两个公司、共享记录、公司为空、多公司用户、门户用户、字段值/时间 Record Rule、深度 2 关系、字段权限组合和运行时权限切换。最终结果：

- 未发现最终测试路径的泄露；
- 公司 A 用户不可见公司 B Partner/Order；
- 共享记录对授权用户可见；
- Portal 用户无测试记录可见；
- 阻断字段值订单和未来日期订单均不可见；
- 深度 2 `sale.order -> partner` 关联每跳受限；
- `credit_limit` 无权限字段被排除；
- 权限切换后无需重启，新 Environment 立即反映公司范围；
- 失败关闭返回 `PERMISSION_DENIED`、空 ID、0 计数。

本结论是对当前 fixture 和 Odoo ORM/Record Rule 组合的验证，不等同于完整 Global Search 实现已通过；复杂多跳路径、真实搜索服务错误传播和浏览器层由后续 TV 覆盖。

### 对 SRS V1.4 的影响

- FR-PM-004、FR-PM-008、BR-012 获得复杂权限场景的技术证据；
- CON-008/CON-011 的失败关闭和字段排除路径通过；
- 发现同一用户组中的多个组规则可能按 OR 组合，不能把互相依赖的硬限制拆成同组独立规则；
- V1 范围不调整。

## 3. 验证问题回顾

| 问题 | 回答 | 实际行为 | 证据 |
|---|---|---|---|
| 共享记录 | 通过 | 公司 A 和多公司用户均可见共享 Partner | [permission_result.json](../results/permission_result.json) |
| 公司为空 | 通过 | `company_id=False` 共享记录可见且不泄露公司 B 数据 | [permission_result.json](../results/permission_result.json) |
| 多公司用户 | 通过 | 可见 A/B 记录及共享记录 | [permission_result.json](../results/permission_result.json) |
| 门户用户 | 通过 | TV04 Partner/Order 结果均为空 | [permission_result.json](../results/permission_result.json) |
| 字段值 Record Rule | 通过 | `TV04-ORDER-BLOCKED` 不可见 | [permission_result.json](../results/permission_result.json) |
| 时间 Record Rule | 通过 | 当前订单可见，2099 未来订单不可见 | [permission_result.json](../results/permission_result.json) |
| 深度 2 Relation Path | 通过 | A 用户按 A Partner 可见，按 B Partner 为 0 | [permission_result.json](../results/permission_result.json) |
| 关联记录部分无权 | 通过 | B Partner 关联订单被跳过，返回 0 | [permission_result.json](../results/permission_result.json) |
| 字段/记录权限组合 | 通过 | `credit_limit` 不可读且被排除，name 可读 | [permission_result.json](../results/permission_result.json) |
| 运行时权限变化 | 通过 | A 用户切换到 B 后 A 隐藏、B 可见，无重启 | [permission_result.json](../results/permission_result.json) |

## 4. 方法与执行

### 4.1 实际环境

| 项 | 值 |
|---|---|
| Odoo | 18.0 |
| Python | 3.11.9 |
| PostgreSQL | 16.14 |
| 数据库 | `wd_tv_gs01_20261002_100k` |
| 业务写入 | Odoo ORM |
| 权限读取 | `with_user()` + 新 Environment |
| `sudo()` | 未使用 |
| 直接数据库业务读写 | 未使用 |

### 4.2 Fixture

- 公司 A、公司 B；
- 公司 A 用户、公司 B 用户；
- 同时属于 A/B 的多公司用户；
- Portal 用户；
- 测试专用权限组；
- `res.partner`：A、B、共享、阻断四类记录；
- `sale.order`：A、B、共享、阻断、未来日期五类记录；
- Partner 公司规则；
- Sale Order 测试全局规则：公司范围、阻断值和日期条件；
- `credit_limit` 字段权限检查。

### 4.3 执行过程

1. ORM 创建所有 fixture；
2. 通过各用户 `with_user()` 查询 Partner/Order；
3. 对查询、计数和关联路径记录 ID 与状态；
4. 修改 A 用户的 `company_id/company_ids` 到 B；
5. 使用新用户 Environment 查询；
6. 验证失败关闭；
7. ORM 删除订单、Partner、用户、规则、测试公司。

## 5. 结果

### 5.1 用户可见性

| 用户 | Partner 结果 | Order 结果 | 结论 |
|---|---:|---:|---|
| 公司 A | A + shared | A + shared | 无 B 泄露 |
| 公司 B | B + shared | B | 无 A 泄露 |
| 多公司 A/B | A + B + shared | A + B + shared | 符合授权范围 |
| Portal | 0 | 0 | 失败关闭/无泄露 |

### 5.2 共享和空公司

| 场景 | 结果 |
|---|---|
| A 用户读取共享 Partner | 1 条 |
| A 用户读取 A Partner | 1 条 |
| A 用户读取 B Partner | 0 条 |
| 多公司用户读取共享 Partner | 1 条 |

### 5.3 Record Rule

| 规则 | 结果 |
|---|---|
| 字段值 `TV04-ORDER-BLOCKED` | 0 条 |
| 当前/过去日期订单 | 1 条可见 |
| 2099-01-01 未来订单 | 0 条 |

### 5.4 Relation Path

| 查询 | 结果 |
|---|---:|
| A 用户通过 `partner_id=A` 搜订单 | 1 条 |
| A 用户通过 `partner_id=B` 搜订单 | 0 条 |
| B 关联订单计数 | 0 |

### 5.5 字段权限

| 字段 | 结果 |
|---|---|
| `name` | 可读 |
| `credit_limit` | 不可读 |
| `credit_limit` 参与搜索 | 排除 |

### 5.6 运行时权限变化

| 项 | 结果 |
|---|---|
| A 用户切换到公司 B | 成功 |
| 切换后 A Partner 可见 | false |
| 切换后 B Partner 可见 | true |
| 是否重启 | 否 |

### 5.7 失败关闭

| 项 | 结果 |
|---|---|
| 状态 | `PERMISSION_DENIED` |
| 结果 ID | `[]` |
| 计数 | `0` |
| 异常类型 | `AccessError` |

## 6. 分析

### 6.1 与通过标准对比

- 最终测试所有十个子问题均有实际行为；
- 最终 `no_leakage=true`；
- 最终 `failure_closed=true`；
- 关联路径按用户 Record Rule 返回 0，不泄露关联数量；
- 字段权限通过 `fields_get()` 排除；
- 权限切换用新 Environment 后立即生效。

### 6.2 重要发现：组规则 OR 组合

首次运行使用同一测试组的独立字段值规则和时间规则时，Odoo 标准 Sales Manager 组规则与测试组规则组合导致阻断订单仍可见。该路径被识别为真实的权限配置风险。

随后将仅作用于 `TV04-*` fixture 的公司、字段和时间硬约束合并为全局测试规则，并重新执行。最终结果阻断订单和未来订单均不可见。

这说明：

- 互相依赖的安全条件不能假设同一组中的多个 Group Rule 自动 AND；
- Global Search 配置生成 Record Rule 时必须明确 global/group 组合语义；
- 规则生成器应有“阻断记录必须不可见”的回归测试。

### 6.3 与 GS-05 对比

GS-05 验证了两公司两用户的基础隔离。本 TV 增加了共享记录、多公司用户、门户用户、字段值/时间规则、深度 2 关联和权限运行时变化，并发现/修复了组规则组合导致的潜在泄露路径。

## 7. 结论

| 子问题 | 结论 |
|---|---|
| 共享记录 | 通过 |
| 公司为空 | 通过 |
| 多公司用户 | 通过 |
| 门户用户 | 通过 |
| 字段值规则 | 通过 |
| 时间规则 | 通过 |
| 深度 2 Relation Path | 通过 |
| 关联记录部分无权 | 通过 |
| 字段与记录权限组合 | 通过 |
| 权限运行时变化 | 通过 |

### 整体结论

**有条件通过。**

条件：

1. Global Search 必须在每个 Business Resource 和 Relation Path 上下文使用当前用户；
2. 规则合并不能依赖未经验证的 Group Rule AND 假设；
3. 所有权限异常必须失败关闭；
4. 真实 Global Search 服务实现后需把这些 fixture 转为自动化回归测试。

## 8. 对 SRS 的影响

### 已验证

- FR-PM-004：多公司、共享和关联权限路径；
- FR-PM-008：复杂 Record Rule 和运行时权限；
- BR-012：跨资源结果必须遵守当前用户权限；
- CON-008：权限异常失败关闭；
- CON-011：无权限字段不参与搜索。

### 需要技术方案调整

- 配置生成器需显式区分 Global Rule 与 Group Rule；
- 同一安全边界的字段/时间/公司条件应生成单一 AND 硬边界，或有明确的组合证明；
- Relation Path 每跳都要执行 `check_access_rule`/等价 ORM 权限过滤；
- 计数和 Query Understanding 必须使用过滤后的结果集。

### 不修改事项

- 不修改 SRS V1.4 业务范围；
- 不引入外部搜索引擎、LLM 或向量检索；
- 不使用 `sudo()` 作为搜索权限实现。

## 9. 对技术方案的影响

| 领域 | 影响 |
|---|---|
| 权限边界 | 结果、计数、Preview、关联扩展统一使用当前用户 |
| Record Rule | 规则组合语义必须显式建模和测试 |
| 字段权限 | Searchable Field 生成前调用当前用户 `fields_get()` |
| Relation Path | 每跳单独查询并应用 Record Rule |
| 缓存 | 权限变化后必须失效用户/公司相关缓存 |
| 错误处理 | AccessError 和规则评估异常均失败关闭 |

## 10. 未解决的问题

1. 真实 Global Search 服务实现后的端到端权限回归；
2. 深度大于 2 的多跳路径；
3. 门户用户拥有部分业务 ACL 时的细粒度结果；
4. 复杂 Record Rule 共享记录和多公司规则的更多组合；
5. 多 worker 权限/配置缓存失效；
6. Preview、Query Understanding 和分类计数在真实前端链路的权限行为。

## 11. 产出物清单

- [PLAN.md](../PLAN.md)
- [README.md](../README.md)
- [run.py](../scripts/run.py)
- [permission_result.json](../results/permission_result.json)
- 本报告

执行结束后已通过 ORM 清理 TV04 测试公司、用户、规则、Partner 和 Sale Order。

## 12. 复现说明

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
TV_DB=wd_tv_gs01_20261002_100k \
  ./venv/bin/python odoo-bin shell -c odoo.conf \
  -d wd_tv_gs01_20261002_100k --no-http \
  < mymodules/wd_tv_global_search/tv_04_complex_permissions/scripts/run.py
```

脚本只处理 `TV04-` 标记的数据，并且不使用 `sudo()`。

## 13. 参考

- `docs/requirement/SRS_global_search.md`：FR-PM-004、FR-PM-008、BR-012、CON-008、CON-011；
- `mymodules/wd_spike_global_search/spike_05_permission_integrity/reports/REPORT.md`；
- `docs/verification/SPIKE_global_search_report.md`：GS-05。

## 14. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 创建 TV-04 报告结构 |
| v0.2 | 2026-10-03 | 完成最终复杂权限验证，并记录组规则 OR 组合发现 |
