# CC-009 Global Search 国际化与时区

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-009 |
| 版本 | v0.1 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-I18N-TIMEZONE` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 9 |
| 前置 CC | CC-001~CC-008 已冻结；TD-001 已完成 |
| 模块 | `wd_global_search` |
| 目标 | 实现 Vocabulary、Snapshot、错误提示、日期时间和用户语言/时区的一致行为 |
| 批准冻结 | 2026-10-06 22:42，用户批准冻结并进入实施 |

本 CC 只处理国际化、用户语言和时区展示，不改变搜索条件、权限、错误码、索引或业务数据语义。

## 1. 追溯与范围

### 1.1 SRS / TDD 追溯

| 来源 | 本 CC 落实 |
|---|---|
| SRS FR-SW-001~003 | Workspace 资源、Snapshot 和导航词汇翻译 |
| SRS FR-ER-002~003 | 错误码稳定、错误消息可翻译 |
| SRS FR-RF-001~009 | Refinement 标签和日期条件本地化 |
| SRS NFR-002 | 当前用户语言、时区和数据新鲜度上下文 |
| SRS NFR-004 | 窄屏和浏览器语言展示 |
| SRS BR-009.1 | 语言周起始日 |
| SRS BR-009.2 | 用户时区日期边界 |
| TDD §3.8 | Vocabulary、语言和时区 |
| TDD §3.14 | 国际化和本地化 |
| TDD §6.1、§6.5 | 服务端用户上下文和失败关闭 |
| TDD §7.5 | Preview 字段标签和值的本地化 |
| TDD §12.5 | 浏览器 HVR |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- Vocabulary 资源、Refinement、状态和错误消息翻译；
- Published Snapshot 字段标签按当前用户语言展示；
- Date / DateTime 按当前用户时区转换；
- 数字、货币、Selection 和 Many2one 标签本地化；
- `en_US`、`zh_CN` 语言周起始规则；
- 缺失翻译回退英文；
- 服务端 `request.env.user.lang` 为唯一语言来源；
- 当前用户 `tz` 为唯一时区来源；
- CC-004 Preview、CC-005 Workspace 和 CC-007 错误提示回归。

### 1.3 超出范围

- 新增语言包、修改官方翻译或修改 Odoo 核心；
- 从浏览器语言、请求体或客户端 header 伪造服务端语言/时区；
- 修改业务日期存储、数据库时区或配置快照结构；
- 改变错误码、权限边界、条件合并、分页和索引策略；
- LLM 翻译、外部翻译 API 或运行时远程词典；
- 缺失翻译时阻断搜索。

## 2. 语言与时区契约

### 2.1 User Context

- 语言唯一来源：`request.env.user.lang`；
- 时区唯一来源：`request.env.user.tz`；
- 公司、语言和时区从服务端 `UserContext` 向下传递；
- 请求体中的 `lang`、`tz`、`locale` 和 `timezone` 忽略或拒绝；
- 前端只展示服务端返回的翻译标签和值。

### 2.2 翻译回退

- 首选当前用户语言；
- 缺失翻译回退 `en_US`；
- `en_US` 仍缺失时显示服务端安全默认文本；
- 翻译缺失不得改变错误码、结果、计数或权限；
- 原始业务字段值不作为翻译 key 直接写入日志。

### 2.3 日期与时间

- 数据库 DateTime 继续使用 Odoo UTC 语义；
- 展示层按当前用户时区转换；
- `today`、`this_week`、`this_month` 使用当前用户时区和语言周起始；
- 日期范围使用 `[start, end)`；
- `en_US` 与 `zh_CN` 的周起始日遵守 BR-009.1；
- 跨午夜场景使用服务端固定时钟/当前请求时钟，不使用浏览器本地时钟；
- API 返回 ISO 可解析值和服务端格式化标签，不返回未经说明的本地时间。

## 3. 序列化与提示契约

| 类型 | 规则 |
|---|---|
| char/text | 当前语言标签，空值显示 `—` |
| integer/float | 当前语言数字格式 |
| date/datetime | 当前用户时区和语言格式 |
| boolean | 当前语言 True/False 标签 |
| selection | 当前语言 selection label |
| many2one | 当前用户语言 display_name |
| monetary | 当前语言和货币格式 |
| error message | 错误码稳定，消息按服务端语言翻译 |

错误响应必须保留稳定 `code`，允许 `message` 按语言变化。

## 4. 必需行为变更

| ID | 变更 | 验证 |
|---|---|---|
| CC9-CHANGE-001 | Vocabulary 和资源标签本地化 | CC9-TEST-001 |
| CC9-CHANGE-002 | Snapshot/Preview 字段标签和值本地化 | CC9-TEST-002 |
| CC9-CHANGE-003 | Date/DateTime 按用户时区格式化 | CC9-TEST-003 |
| CC9-CHANGE-004 | 周起始和日期 Refinement 按语言/时区 | CC9-TEST-004 |
| CC9-CHANGE-005 | 错误消息翻译且错误码稳定 | CC9-TEST-005 |
| CC9-CHANGE-006 | 缺失翻译英文回退 | CC9-TEST-006 |

## 5. 既有行为保留与 TDD 防护栏

| ID | 行为 |
|---|---|
| CC9-PRESERVE-001 | CC-002 Search/Cancel 错误码、cursor、计数和分页不变 |
| CC9-PRESERVE-002 | CC-003 当前用户、公司和字段权限不变 |
| CC9-PRESERVE-003 | CC-004 Preview 只读和安全失败不变 |
| CC9-PRESERVE-004 | CC-005 Raw Query、Refinement 和 Preview 联动不变 |
| CC9-PRESERVE-005 | CC-007 错误结构、retryable 和失败关闭不变 |
| CC9-PRESERVE-006 | CC-008 日志字段白名单和 audit_log 语义不变 |

- TDD §3.14：国际化集中在服务端用户上下文；
- TDD §6.1：语言/时区来自当前 request.env；
- TDD §6.5：翻译失败不放宽权限，异常失败关闭；
- TDD §7.5：Preview 序列化遵守当前用户语言/时区；
- TDD §12.5：浏览器完成桌面和窄屏 HVR；
- 不新增业务模型、字段、表或迁移。

## 6. 测试契约

| ID | 内容 | 类型 | 预期 |
|---|---|---|---|
| CC9-TEST-001 | en_US/zh_CN Vocabulary | 单元+浏览器 | 资源、Refinement 和状态标签正确 |
| CC9-TEST-002 | Snapshot/Preview 字段标签 | Odoo+浏览器 | 标签和值按当前用户语言展示 |
| CC9-TEST-003 | DateTime 时区转换 | Odoo 集成 | UTC、上海、洛杉矶边界正确 |
| CC9-TEST-004 | 周起始和日期 Refinement | TV-06+集成 | en_US 周日、zh_CN 周一，范围 `[start,end)` |
| CC9-TEST-005 | 错误消息和错误码 | API+浏览器 | code 稳定，message 可翻译 |
| CC9-TEST-006 | 缺失翻译回退 | 单元+浏览器 | 回退英文，不阻断搜索 |
| CC9-TEST-007 | 当前用户语言/时区边界 | 权限+集成 | 请求体 lang/tz 不改变服务端上下文 |
| CC9-TEST-008 | CC-001~CC-008 回归 | Odoo+浏览器 | 权限、错误、日志和 Preview 不回归 |

## 7. 安全、数据和 API 影响

- 不新增业务表、字段、迁移或外部翻译服务；
- 不使用 `sudo()` 读取业务数据；
- 语言/时区不参与权限授权，只影响展示和时间条件计算；
- 不记录原始字段值、用户输入或翻译后的敏感数据；
- API 错误 `code` 稳定，`message` 可按当前服务端语言变化；
- 配置 Snapshot 不因用户语言改变 checksum 或版本；
- 任何翻译异常不得返回猜测数据。

## 8. 状态机与验收场景

```text
REQUESTED
   -> RESOLVED_USER_CONTEXT
   -> TRANSLATED
   -> FORMATTED
   -> PRESENTED
   -> FALLBACK_ENGLISH
   -> FAILED_CLOSED
```

验收场景：

1. en_US 用户搜索并查看 Preview；
2. zh_CN 用户搜索并查看 Preview；
3. 同一 UTC DateTime 在 UTC、上海、洛杉矶显示不同本地时间；
4. en_US 周起始为周日，zh_CN 周起始为周一；
5. 缺失翻译回退英文并继续搜索；
6. 错误 code 不随语言变化，message 随服务端语言变化；
7. 请求体伪造 lang/tz 不改变结果；
8. 桌面和窄屏显示无截断和控制台错误。

## 9. 性能、日志与 Fixture

- 翻译查找 P95 ≤ 20ms，日期格式化 P95 ≤ 10ms；软闸门；
- 日志只记录 request_id、lang hash、tz、status、latency 和 error_code；
- 不记录原始语言、字段值或用户 Query；
- Fixture 位置：`tests/fixtures/i18n/`；
- Fixture 覆盖 en_US、zh_CN、缺失翻译、UTC、Asia/Shanghai、America/Los_Angeles；
- 每个测试使用唯一标记并清理。

## 10. HVR 与浏览器矩阵

HVR：

1. 人工切换 en_US/zh_CN 用户；
2. 验证资源、状态、错误和 Preview 字段标签；
3. 验证跨时区 DateTime 和日期 Refinement；
4. 验证缺失翻译英文回退；
5. 验证桌面和窄屏布局。

| 浏览器 | 桌面 | 窄屏 |
|---|---|---|
| Chrome 最新 | 待验证 | 待验证 |
| Firefox 最新 | 待验证 | 待验证 |
| Safari 最新 | 待验证 | 待验证 |
| Edge 最新 | 待验证 | 待验证 |

## 11. 实施结构与 CC-DEC

```text
services/i18n.py                 # 翻译、回退和日期格式化
services/preview.py              # Snapshot 字段本地化
services/conditions.py           # 用户时区日期条件
controllers/main.py              # 服务端语言/时区上下文
tests/test_i18n_timezone.py      # 语言、时区和回退测试
docs/context/history/            # IHR、ATR、HVR
```

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC9-DEC-001 | request.env.user.lang 是唯一语言来源 | 浏览器语言优先 | 保持服务端一致 |
| CC9-DEC-002 | request.env.user.tz 是唯一时区来源 | 浏览器本地时区 | 防止边界漂移 |
| CC9-DEC-003 | 缺失翻译回退英文 | 阻断搜索 | 保持可用性 |
| CC9-DEC-004 | code 稳定、message 可翻译 | code 随语言变化 | 保持客户端兼容 |
| CC9-DEC-005 | 复用 Odoo i18n/format 工具 | 自建格式化规则 | 保持 Odoo 18 语义 |

## 12. 冻结与实施结论

- 用户批准冻结：2026-10-07；
- 实施与自动化验证完成；
- TV-06 时间语义回归通过；
- 当前 Chromium 桌面与 `390x844` 窄屏 HVR 通过；
- 多浏览器及独立多用户语言/时区矩阵保留为后续补测，不阻塞本阶段冻结；
- CC-009 状态：FROZEN，实施完成。

未经用户批准冻结，不得实施 CC-009。
