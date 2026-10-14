# ATR-GS-P0-RELATION-DEPTH

## 0. 执行元数据

| 项 | 内容 |
|---|---|
| 修复 | P0-04 runtime `max_relation_depth` enforcement |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 环境 | macOS；Odoo 18 CE |
| 日期 | 2026-10-14 |
| 执行者 | Copilot assistant |

## 1. 自动化验证

| 验证项 | 结果 | 覆盖 |
|---|---|---|
| Field-path、permission-boundary、service-core | **55/55 PASS** | 旧 snapshot 默认深度；深度 2 路径在 Resource 上限 1 时拒绝；上限经过 Resource 授权、条件校验和 executor；无越界 ORM 查询 |
| CC-015 contract + request boundary | **34/34 PASS** | 搜索、授权字段、关键词、条件和日期请求回归 |
| Python 编译 | **PASS** | 所有改动的服务及测试模块 |
| `git diff --check` | **PASS** | 补丁格式无 whitespace errors |

## 2. 行为证据

- 默认 snapshot 的 `max_relation_depth` 为 2。
- Resource 配置深度 1 时，`partner_id.country_id.name`（深度 2）经授权边界拒绝，错误码为 `CONFIGURATION_ERROR`。
- 运行时 `max_relation_depth` 为 `0`、`4`、`True` 或字符串 `"2"` 时配置拒绝；不以默认值静默放宽。
- executor 单测确认它收到 SearchService 对该 Resource 传入的深度预算。

## 3. 当前结论

**P0-04 的运行期深度预算在授权筛选、条件校验和 ORM executor 入口统一应用。** 定向自动化及 CC-015/request-boundary 回归通过；未对数据库或配置记录执行写操作。
