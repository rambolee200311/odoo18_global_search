# CC-008 Global Search 可观测性与配置审计

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-008 |
| 版本 | v0.2 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-OBSERVABILITY-AUDIT` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 8 |
| 前置 CC | CC-001~CC-007 已冻结；TD-001 已完成 |
| 模块 | `wd_global_search` |
| 目标 | 使用 Odoo 原生日志和现有 `wd.gs.audit.event`（audit_log）建立不泄露业务数据的请求、错误、性能和配置审计 |
| 批准冻结 | 2026-10-06 22:17，用户确认验证范围后批准冻结并提交 |

本 CC 不引入外部日志、指标、追踪或告警平台，不创建第二套审计模型，不改变业务权限边界。

## 1. 追溯与范围

### 1.1 SRS / TDD 追溯

| 来源 | 本 CC 落实 |
|---|---|
| SRS NFR-003 | 结构化错误、性能和行为观测 |
| SRS NFR-002 | request/config 快照和新鲜度上下文 |
| SRS FR-PM-001~008 | 观测不绕过当前用户权限 |
| SRS CON-008 | 观测失败不改变安全失败关闭 |
| SRS CON-011 | 观测不记录无权限字段，不参与业务数据读取 |
| SRS FR-ER-002~003 | 错误码、失败关闭和错误率 |
| SRS CFG-007、CFG-008 | 发布、拒绝、停用和版本审计 |
| TDD §3.12 | request metadata、hash 和可观测性 |
| TDD §5.4 | 配置版本、checksum 和审计 |
| TDD §6.5 | 观测异常不得改变失败关闭 |
| TDD §12.3 | 性能、错误率和验收环境采集 |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- Odoo Python logger（`odoo.tools` / `logging.getLogger`）结构化记录；
- `request_id`、`config_version`、resource、latency、result_count；
- status、error_code、retryable 和错误率聚合；
- `raw_query_hash`、`conditions_hash`；
- 服务端 salt 生成和 hash 版本；
- 使用现有 `wd.gs.audit.event` 记录配置发布、拒绝、停用和缓存失效；
- 指标/日志字段白名单、采集说明和告警阈值；
- 单元、集成和验收环境采集测试。

### 1.3 超出范围

- Elasticsearch、OpenSearch、Sentry、Prometheus、Grafana 或其他外部观测平台；
- 原始 Query、完整 conditions、字段值、业务数据、SQL、Record Rule 或 token；
- 新增平行 audit_log 模型或绕过现有 `wd.gs.audit.event`；
- 将日志/审计读取权限扩大给普通业务用户；
- 用日志代替权限校验、错误协议或业务数据审计。

## 2. 观测契约

### 2.1 Odoo 原生日志

统一使用模块 logger：

```python
_logger = logging.getLogger(__name__)
```

日志事件使用固定事件名和白名单字段：

| 事件 | 级别 | 必填字段 |
|---|---|---|
| `gs.search.completed` | INFO | request_id、config_version、status、latency_ms、result_count |
| `gs.search.partial` | WARNING | request_id、config_version、failed_resources、latency_ms |
| `gs.search.failed` | ERROR | request_id、error_code、retryable、latency_ms |
| `gs.search.cancelled` | INFO | request_id、config_version、latency_ms |
| `gs.search.rate_limited` | WARNING | request_id、user_context_hash、latency_ms |
| `gs.preview.failed` | WARNING | request_id、model、status、error_code |
| `gs.boundary.rejected` | WARNING | request_id、error_code、boundary |

日志不得包含原始用户输入。字段值仅允许经过服务端 salt 的 hash。

### 2.2 Hash 契约

- `raw_query_hash = HMAC-SHA256(server_secret, raw_query)`；
- `conditions_hash = HMAC-SHA256(server_secret, canonical_conditions)`；
- `hash_version = "v1"`，版本变更时旧 hash 不失效；
- 不使用客户端 salt、用户可控 salt 或明文 fallback；
- 日志只记录 hash、hash 版本和长度，不记录原文；
- server secret 不写入日志、audit_log 或 API 响应；
- 缺少 server secret 时观测事件失败关闭，不退回明文记录。

### 2.3 指标和聚合维度

允许按以下维度聚合：

- resource；
- config_version；
- status；
- error_code；
- retryable；
- user_context_hash（仅用于识别同一用户请求，必须为服务端 HMAC）；
- 时间窗口。

不得按 raw query、字段值、record_id 或用户输入建立标签，避免高基数和数据泄露。

### 2.4 观测字段白名单和格式

允许字段：

`request_id`、`config_version`、`resource`、`latency_ms`、`result_count`、
`status`、`error_code`、`retryable`、`failed_resources`、`boundary`、
`model`、`raw_query_hash`、`conditions_hash`、`hash_version`、
`user_context_hash`。

禁止字段：

`raw_query`、`conditions`、`field_values`、`sql`、`record_rule`、
`token`、直接 `user_id`、直接 `record_id`。

观测事件使用 Odoo 结构化字段传递，不使用字符串拼接：

```json
{
  "event": "gs.search.completed",
  "request_id": "...",
  "config_version": "...",
  "status": "SUCCESS",
  "latency_ms": 245,
  "result_count": 56
}
```

## 3. audit_log 契约

配置审计必须复用现有 `wd.gs.audit.event`：

| 事件 | 触发条件 | 必填内容 |
|---|---|---|
| `config.publish` | Published 版本成功发布 | domain、version、checksum、request/user context |
| `config.reject` | 发布校验失败 | domain、version、error_code、request_id |
| `config.retire` | Published 版本停用 | domain、version、request_id |
| `config.cache_invalidate` | 配置快照缓存失效 | domain、old_version、new_version、request_id |

- audit_log 不记录原始 Query、业务字段值、SQL 或权限规则；
- audit_log 继续使用现有模型 ACL，普通业务用户不可读取配置审计；
- 配置审计写入失败不得把成功发布伪装成成功；按 CC-001 生命周期协议失败关闭；
- Search 请求错误不写入配置 audit_log，避免混淆配置审计与运行日志。
- audit_log 默认保留 180 天，可配置，并由 Odoo 标准清理机制处理。

## 4. 必需行为变更

| ID | 变更 | 验证 |
|---|---|---|
| CC8-CHANGE-001 | Search/Preview/Boundary 使用固定结构化 Odoo 日志 | CC8-TEST-001 |
| CC8-CHANGE-002 | request/config/resource/latency/result/error metadata 可聚合 | CC8-TEST-002 |
| CC8-CHANGE-003 | Query 和 conditions 只以服务端 HMAC hash 观测 | CC8-TEST-003 |
| CC8-CHANGE-004 | 配置生命周期复用 `wd.gs.audit.event` | CC8-TEST-004 |
| CC8-CHANGE-005 | 观测失败不改变权限和失败关闭 | CC8-TEST-005 |

## 5. 测试契约

| ID | 内容 | 类型 | 预期 |
|---|---|---|---|
| CC8-TEST-001 | Odoo logger 字段白名单 | 单元+日志捕获 | 无原始 Query、字段值或 SQL |
| CC8-TEST-002 | request/resource/status/error 聚合 | 集成 | 可按允许维度聚合，不卡入用户输入高基数标签 |
| CC8-TEST-003 | HMAC hash | 单元 | 同输入稳定、不同输入不同、无 secret 不明文 fallback |
| CC8-TEST-004 | config audit_log | Odoo 集成 | 发布、拒绝、停用、缓存失效均写入 `wd.gs.audit.event` |
| CC8-TEST-005 | 观测异常隔离 | 集成 | 日志失败不绕过权限、不改变失败关闭 |
| CC8-TEST-006 | CC-001~CC-007 回归 | Odoo+浏览器 | 搜索、Preview、错误和权限行为不回归 |
| CC8-TEST-007 | 验收环境采集 | HVR/验证 | 可采集 latency、error rate、版本和 resource |
| CC8-TEST-008 | hash 版本 | 单元 | `hash_version` 写入日志，变更时旧 hash 不失效 |
| CC8-TEST-009 | audit_log 保留周期 | Odoo 集成 | 超过保留周期的记录由 Odoo 标准机制清理 |

## 6. 安全、数据和迁移影响

- 不新增业务数据表和外部服务；
- `wd.gs.audit.event` 为既有审计模型，继续使用现有 ACL；
- 日志和 hash 只在服务端生成；
- 观测代码不得使用 `sudo()` 读取业务数据；
- 任何日志字段扩展必须先通过敏感数据白名单评审；
- 观测异常不能让权限错误变成成功结果；
- 发现原始 Query、条件值或字段值进入日志时立即停止采集并清理日志。

### 6.1 Server Secret 管理

- 存储于 Odoo `ir.config_parameter`；
- 只有系统管理员可读写；
- 不写入日志、audit_log 或 API 响应；
- 建议每 90 天轮换；
- 轮换通过 `hash_version` 保持旧 hash 可解释，不回退到明文。

### 6.2 告警、追踪和性能软闸门

建议告警阈值：

- `gs.search.failed` > 5% / 5 分钟；
- `gs.search.partial` > 20% / 5 分钟；
- `gs.search.rate_limited` > 10% / 5 分钟；
- `gs.preview.failed` > 5% / 5 分钟；
- `gs.boundary.rejected` > 1% / 5 分钟。

告警渠道由部署决定，不在本 CC 引入外部平台。每个观测事件关联唯一
`request_id`；request_id 不跨请求复用，也不写入配置 audit_log。

软闸门：

- 日志写入 P95 ≤ 10ms；
- HMAC hash P95 ≤ 5ms；
- audit_log 写入 P95 ≤ 50ms。

## 7. 停止条件与完成定义

### 7.1 停止条件

1. 日志或 audit_log 包含原始 Query、完整 conditions、字段值、SQL 或 token；
2. 为采集业务数据需要 `sudo()`、管理员环境或修改官方代码；
3. 指标标签使用 record_id、raw query 或其他高基数用户输入；
4. audit_log 权限被扩大给普通用户；
5. 观测失败改变 Search、Preview 或 Permission Boundary 的结果。

### 7.2 完成定义

1. CC8-CHANGE-001~005 实现并有 IHR；
2. CC8-TEST-001~007 执行并有 ATR；
3. Odoo logger 字段白名单和 HMAC hash 通过；
4. `wd.gs.audit.event` 覆盖配置发布、拒绝、停用、缓存失效；
5. 验收环境可采集性能和错误率；
6. CC-001~CC-007 既有行为不回归。

## 8. 既有行为保留、TDD 防护栏和 API 影响

| ID | 行为 |
|---|---|
| CC8-PRESERVE-001 | CC-002 request_id、错误码、分页和限流协议不变 |
| CC8-PRESERVE-002 | CC-003 权限边界和字段过滤不被观测逻辑绕过 |
| CC8-PRESERVE-003 | CC-004 Preview 只读和失败关闭不变 |
| CC8-PRESERVE-004 | CC-005 Workspace 状态和 CC-007 错误提示不变 |
| CC8-PRESERVE-005 | CC-006 可选索引策略不因观测接线改变 |

- TDD §3.12：只采集白名单 request metadata；
- TDD §5.4：配置版本、checksum 和审计复用既有模型；
- TDD §6.5：观测失败继续失败关闭；
- TDD §12.3：性能和错误率可在验收环境采集；
- 不新增业务 API、业务表或迁移。

API 影响仅限于内部 metadata，不向普通用户暴露日志、hash、secret 或 audit_log。

## 9. 状态机、Fixture、验收与 HVR

```text
REQUESTED -> OBSERVING -> COMPLETED
                      -> PARTIAL
                      -> FAILED
                      -> CANCELLED
                      -> REJECTED
```

Fixture 位置：`tests/fixtures/observability/`，覆盖多资源、多状态、多错误码、
Published/Rejected/Retired 版本和普通用户、Portal、多公司用户；每个套件使用唯一标记并清理。

验收场景：

1. 搜索成功记录 `gs.search.completed`；
2. 部分成功记录 `gs.search.partial`；
3. 失败记录 `gs.search.failed`；
4. 取消和限流记录对应事件；
5. Preview 和 Boundary 失败记录对应事件；
6. 配置发布、拒绝、停用、缓存失效写入 `wd.gs.audit.event`；
7. 日志不含原始 Query、字段值和 SQL；
8. 同输入 hash 稳定，secret 缺失时不明文 fallback；
9. 指标可按允许维度聚合。

HVR 场景：

1. 人工触发成功、部分成功和失败搜索并检查日志；
2. 人工触发配置发布并检查 audit_log；
3. 检查日志无原始 Query、字段值和 SQL；
4. 检查 hash 稳定；
5. 检查窄屏和桌面浏览器无观测相关前端错误。

浏览器矩阵：Chrome、Firefox、Safari、Edge 最新版，桌面和窄屏。

前端接口：

```javascript
reportClientError(error): void
reportClientPerformance(metric): void
```

前端上报只允许 request_id、error_code、resource、retryable 和 latency，
不得上传原始 Query、条件值、字段值、SQL 或 token。

## 10. 实施结构

```text
services/observability.py        # Odoo logger、字段白名单和 HMAC hash
models/configuration.py          # 复用 wd.gs.audit.event
controllers/main.py              # request metadata 接线
tests/test_observability.py      # 日志、hash、audit_log 和隔离测试
docs/context/history/            # IHR、ATR、HVR
```

## 11. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC8-DEC-001 | 使用 Odoo 原生日志 | 引入外部日志平台 | 保持模块边界和部署简单 |
| CC8-DEC-002 | 复用 `wd.gs.audit.event` | 新建第二套 audit_log | 避免审计分裂 |
| CC8-DEC-003 | HMAC hash 代替原文 | 记录明文 Query | 防止日志泄露 |
| CC8-DEC-004 | 允许维度固定白名单 | 任意动态标签 | 防止高基数和用户输入泄露 |
| CC8-DEC-005 | 观测与权限结果隔离 | 观测失败时放宽访问 | 保持失败关闭 |
| CC8-DEC-006 | server secret 支持轮换 | 固定 secret | 满足安全合规要求 |

未经用户批准冻结，不得实施 CC-008。
