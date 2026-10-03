# TV-04 复杂权限场景

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-04 |
| 名称 | 复杂权限场景 |
| 版本 | v0.1 |
| 状态 | Executed |
| 负责人 | Odoo 18 Technical Verification 助手 |
| 日期 | 2026-10-03 |

## 2. 背景与动机

验证 SRS FR-PM-004、FR-PM-008、BR-012 在复杂多公司、Record Rule、字段权限和 Relation Path 场景下是否仍无泄露。

GS-05 只覆盖两个公司和两个用户。本 TV 在隔离数据库中通过 Odoo ORM 建立共享记录、空公司记录、多公司用户、门户用户、字段值/时间 Record Rule、深度 2 关系和运行时权限变化。

## 3. 验证问题

1. 共享记录是否只对允许用户可见。
2. `company_id=False` 记录是否泄露。
3. 多公司用户是否只看到授权公司。
4. 门户用户是否失败关闭。
5. 字段值 Record Rule 是否生效。
6. 时间条件 Record Rule 是否生效。
7. 深度 2 Relation Path 是否每跳应用权限。
8. 关联记录部分无权时是否跳过。
9. 字段权限与记录权限组合是否无泄露。
10. 权限变化后新请求是否立即使用新权限。

## 4. 假设

### 技术

- 所有业务数据、用户、公司、规则和权限 fixture 通过 Odoo ORM 建立；
- 每个场景使用 `with_user()` 和新的 ORM Environment；
- 任何权限异常返回空结果、0 计数和显式错误状态；
- 不使用 `sudo()`。

### 数据

- 使用独立数据库 `wd_tv_gs01_20261002_100k`；
- 测试数据使用 `TV04-` 标记；
- 两个新公司、公司用户、多公司用户、门户用户和受限字段用户均通过 ORM 建立。

### 环境

- Odoo 18、Python 3.11、PostgreSQL 16；
- 当前用户为 fixture 管理员，仅用于创建测试配置；
- 测试查询使用受限用户身份。

## 5. 范围

### In Scope

- Partner 和 Sale Order 的多公司/共享数据；
- 基于字段值和业务日期的 Record Rule；
- 深度 2 `sale.order -> partner`；
- Portal ACL；
- `credit_limit` 字段权限；
- 权限变化后的新 Environment；
- 异常失败关闭。

### Out of Scope

- 修改 `odoo/` 或官方 addons；
- Elasticsearch/OpenSearch/LLM/向量检索；
- 直接数据库读写；
- `sudo()` 绕过权限；
- 浏览器端 Preview（由 TV-05 验证）。

## 6. 方法

1. 创建公司、用户、组、Record Rule 和 `TV04-` fixture。
2. 用公司用户、多公司用户、门户用户分别执行 Partner/Order 搜索和计数。
3. 检查共享、空公司、阻断字段值、未来日期和关联路径。
4. 使用 `fields_get()` 检查 `credit_limit` 字段权限。
5. 修改测试用户公司权限后，用新 Environment 重复查询。
6. 捕获权限异常，验证失败关闭结构。
7. ORM 清理所有 TV04 记录、用户专用规则和测试公司。

## 7. 通过标准

| 子问题 | 通过标准 |
|---|---|
| 共享/空公司 | 无未授权记录或计数泄露 |
| 多公司 | 只返回用户当前允许公司 |
| 门户 | 无权限时空结果并显式失败状态 |
| Record Rule | 字段值和时间规则均生效 |
| Relation Path | 每一跳应用 Record Rule |
| 字段权限 | 不可读字段不参与搜索或返回 |
| 权限变化 | 新请求无需重启即可反映权限变化 |
| 异常 | 失败关闭，结果为空、计数为 0 |

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 标准规则影响 fixture | 使用独立测试组和新用户，并记录实际规则结果 |
| Portal 用户 ACL 不足 | 记录真实异常，不提升权限 |
| 规则缓存 | 权限变化后新建 Environment 并验证 |
| 测试数据污染 | 只清理 TV04 标记数据和专用对象 |

## 9. 产出物

- `PLAN.md`
- `README.md`
- `scripts/run.py`
- `results/permission_result.json`
- `reports/REPORT.md`

## 10. 参考

- SRS FR-PM-004、FR-PM-008、BR-012、CON-008、CON-011；
- GS-05 报告；
- Odoo ORM `with_user()`、Record Rule 和字段 groups。

## 11. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 创建 TV-04 计划 |
| v0.2 | 2026-10-03 | 完成复杂权限 fixture、Record Rule、字段权限和运行时切换验证 |
