# TV-06 多值条件、时间语义、部分失败报告

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-06 |
| 名称 | 多值条件、时间语义、部分失败 |
| 版本 | v0.1 |
| 状态 | 有条件通过 |
| 执行日期 | 2026-10-03 |
| 执行人 | Odoo 18 Technical Verification 助手 |
| 数据库 | `wd_tv_gs01_20261002_100k` |
| 数据访问 | Odoo ORM |

## 2. 摘要

### 核心结论

> **语义 reference harness 有条件通过；最终 Global Search 服务尚未接入。**

在隔离数据库中通过 ORM 创建 5 条固定 `TV06-` Sale Order fixture，固定 UTC 时间为 `2026-10-03 23:30:00`，完成十个子问题验证。十项语义检查全部通过：

- 同维度状态多值 OR 与两个单值结果集合的并集完全相同；
- 日期范围使用 `[start, end)`，起点包含、终点排除；
- UTC、上海、洛杉矶用户时区产生正确的本地日期；
- `en_US` 周日开始、`zh_CN` 周一开始；
- 跨午夜表达在固定时间点稳定；
- 部分失败保留成功模型结果，计数只统计成功结果并提供模型级提示；
- 超时保留已返回结果并提供 `TIMEOUT`；
- 配置错误返回 0 结果并失败关闭。

但是当前仓库没有最终 Global Search Search Service，因此本报告验证的是可复现的 ORM 语义 harness 和错误协议，不等同于生产搜索链路已通过。整体判定为**有条件通过**。

## 3. SRS 影响

- BR-009.1：获得 `en_US` / `zh_CN` 周起始日证据；
- BR-009.2：获得三种用户时区和跨日边界证据；
- BR-010：获得同维度 OR 证据；
- FR-ER-003：获得部分成功、超时、配置错误的状态/计数/提示证据；
- 生产实现必须把这些规则接入真实 Search Service，并补充服务层回归测试。

## 4. 验证问题回顾

| # | 问题 | 结果 | 证据 |
|---:|---|---|---|
| 1 | 同维度 OR | 通过；多值结果 IDs 与 draft ∪ sent 相同 | [`tv06_result.json`](../results/tv06_result.json) |
| 2 | 多值日期范围 | 通过；`2026-10-01` 包含，`2026-11-01` 排除 | [`tv06_result.json`](../results/tv06_result.json) |
| 3 | 用户时区今天 | 通过；UTC=10-03、上海=10-04、洛杉矶=10-03 | [`tv06_result.json`](../results/tv06_result.json) |
| 4 | 周起始日 | 通过；en_US 周日、zh_CN 周一 | [`tv06_result.json`](../results/tv06_result.json) |
| 5 | 动态跨日 | 通过；固定时间和边界结果稳定 | [`tv06_result.json`](../results/tv06_result.json) |
| 6 | 部分失败行为 | 通过；成功结果保留，错误模型单独列出 | [`tv06_result.json`](../results/tv06_result.json) |
| 7 | 部分失败计数 | 通过；3 条成功结果计数为 3 | [`tv06_result.json`](../results/tv06_result.json) |
| 8 | 部分失败提示 | 通过；`PERMISSION_DENIED` 含模型和消息 | [`tv06_result.json`](../results/tv06_result.json) |
| 9 | 超时行为 | 通过；状态 `PARTIAL_SUCCESS`，保留已完成结果 | [`tv06_result.json`](../results/tv06_result.json) |
| 10 | 配置错误 | 通过；`CONFIGURATION_ERROR`、0 结果、失败关闭 | [`tv06_result.json`](../results/tv06_result.json) |

## 5. 方法与执行

### 5.1 测试数据

通过 `sale.order.create()` 创建 5 条记录：

| 标记 | 状态 | `date_order` |
|---|---|---|
| `TV06-DRAFT` | draft | 2026-10-01 12:00 |
| `TV06-SENT` | sent | 2026-10-02 12:00 |
| `TV06-SALE` | sale | 2026-10-03 12:00 |
| `TV06-CANCEL` | cancel | 2026-10-04 12:00 |
| `TV06-BOUNDARY` | draft | 2026-11-01 00:00 |

执行结束后通过 ORM 删除 fixture；清理验证：

```text
tv06_orders = 0
zh_CN_week_start = 7
```

测试期间临时将已有 `zh_CN` 的 `week_start` 设置为周一，完成后恢复原值；未留下配置变更。

### 5.2 时间语义

固定 UTC 时间：

```text
2026-10-03 23:30:00
```

结果：

| 时区 | 本地日期 |
|---|---|
| UTC | 2026-10-03 |
| Asia/Shanghai | 2026-10-04 |
| America/Los_Angeles | 2026-10-03 |

语言周起始：

| 语言 | `week_start` | 本周起点 |
|---|---:|---|
| en_US | 6（Python weekday，周日） | 2026-09-27 |
| zh_CN | 0（Python weekday，周一） | 2026-09-28 |

### 5.3 部分失败协议

成功模型返回 3 个结果；模拟模型 `broken.resource` 抛出 `AccessError`：

```json
{
  "status": "PARTIAL_SUCCESS",
  "count": 3,
  "errors": [
    {
      "model": "broken.resource",
      "code": "PERMISSION_DENIED"
    }
  ]
}
```

超时保留 3 个已完成结果并返回 `TIMEOUT`。配置错误不返回结果，状态为 `FAILED`，错误码为 `CONFIGURATION_ERROR`。

## 6. 结果与通过标准

| 检查 | 结果 |
|---|---|
| `same_dimension_or` | `true` |
| `date_range` | `true` |
| `timezone_today` | `true` |
| `week_start` | `true` |
| `dynamic_boundary` | `true` |
| `partial_results` | `true` |
| `partial_count` | `true` |
| `partial_prompt` | `true` |
| `timeout_behavior` | `true` |
| `configuration_fail_closed` | `true` |
| `all_semantic_checks_pass` | `true` |

原始结果：[`tv06_result.json`](../results/tv06_result.json)。

## 7. 分析

### 7.1 已验证事实

Odoo ORM 的日期字段、用户时区上下文、语言周起始配置和 recordset 过滤可以稳定表达 SRS 要求。多值 OR 与日期范围的边界均可通过可复现的集合结果判断。错误协议可以区分：

- 部分成功：保留成功结果；
- 超时：保留已完成结果并提示；
- 配置错误：无结果、显式错误、失败关闭。

### 7.2 限制

当前 `mymodules/wd_global_search` 没有生产 Search Service，`production_service_available=false`。因此本 TV 没有证明真实 Global Search 请求会调用这些规则，也没有证明真实 UI 会展示这些提示。

## 8. 结论

| 层级 | 结论 |
|---|---|
| ORM 时间/条件语义 | 通过 |
| 部分失败/超时/配置错误协议 | 通过 |
| 真实 Global Search 服务 | 未验证 |
| TV-06 整体 | 有条件通过 |

条件：

1. 生产 Search Service 必须复用本 TV 的时区、周起始、OR 和 `[start,end)` 规则；
2. 真实模型级错误必须映射为 FR-ER-003 的错误码和提示；
3. 接入服务后必须在真实浏览器补充提示和计数验收。

## 9. 对技术方案的影响

- 时间表达式解析必须以当前用户 `tz` 计算，不得使用服务器时区；
- 语言对象的 `week_start` 必须作为周范围计算输入；
- 多值同维度条件应转换为 OR domain，跨维度继续 AND；
- 结果聚合器需要返回 `PARTIAL_SUCCESS`、成功结果、失败模型列表和可展示消息；
- 配置错误不得使用默认字段静默替代，必须失败关闭。

## 10. 未解决的问题

1. 真实 Search Service 尚未实现；
2. 真实 UI 的部分失败、超时和配置错误提示尚未验证；
3. 高并发下动态时间边界尚未在服务层测量；
4. 更多语言和用户个性化时区尚未覆盖。

## 11. 产出物清单

- [`PLAN.md`](../PLAN.md)
- [`README.md`](../README.md)
- [`data/generate.py`](../data/generate.py)
- [`scripts/run.py`](../scripts/run.py)
- [`results/tv06_result.json`](../results/tv06_result.json)

## 12. 复现说明

见 [`README.md`](../README.md)。执行命令必须指向隔离数据库 `wd_tv_gs01_20261002_100k`；脚本结束时会清理 `TV06-` 记录并恢复语言配置。

## 13. 参考

- SRS BR-009.1、BR-009.2、BR-010、FR-ER-003；
- SPIKE-GS-03、SPIKE-GS-04；
- [`SRS_global_search.md`](../../../../docs/requirement/SRS_global_search.md)。

## 14. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 完成 ORM 语义、时区/语言、部分失败和失败关闭验证 |
