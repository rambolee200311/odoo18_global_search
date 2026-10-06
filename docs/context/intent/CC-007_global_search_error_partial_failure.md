# CC-007 Global Search 错误与部分失败

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-007 |
| 版本 | v0.2 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-ERROR-PARTIAL-FAILURE` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 7 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN；[CC-004](./CC-004_global_search_preview_container.md) v0.2 FROZEN；[CC-005](./CC-005_global_search_workspace_query_refinement.md) v0.1 FROZEN；[CC-006](./CC-006_global_search_index_performance.md) v0.1 FROZEN（可选） |
| 模块 | `wd_global_search` |
| 目标 | 将 Search Service、Workspace 和 Preview 的错误、部分成功、重试语义和安全提示统一为可验证协议 |
| 批准冻结 | 2026-10-05 22:56，用户确认 HVR 后批准冻结并提交 |

本 CC 只处理错误协议、部分失败和用户提示，不改变搜索条件、权限语义、索引策略或业务数据。

## 1. 追溯与范围

### 1.1 SRS / TDD 追溯

| 来源 | 本 CC 落实 |
|---|---|
| SRS FR-ER-001~003 | 错误分类、状态和用户可理解提示 |
| SRS FR-PM-001~008 | 权限错误失败关闭，不泄露记录存在性 |
| SRS NFR-002 | 错误响应遵守当前请求的数据新鲜度和用户上下文 |
| SRS NFR-003 | 错误可观测性和稳定协议 |
| SRS CON-008 | 安全失败关闭 |
| TDD §6.5 | 所有未分类异常失败关闭 |
| TDD §9.1~§9.3 | 错误分类、retryable、部分成功和计数 |
| TDD §10.1~§10.3 | Search/Cancel/Preview API 错误边界 |
| TDD §12.5 | 浏览器状态和提示验证 |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- `SUCCESS`、`PARTIAL_SUCCESS`、`FAILED`、`TIMEOUT`、`RATE_LIMITED`、`CANCELLED`、`EMPTY`；
- `PERMISSION_DENIED`、`CONFIGURATION_ERROR`、`CONFIGURATION_TOO_LARGE`、`INVALID_REQUEST`、`CURSOR_INVALID`、`CURSOR_EXPIRED`、`INTERNAL_ERROR`；
- retryable 规则、request_id 和错误元数据；
- 已完成资源结果保留；
- 部分失败计数和资源状态；
- Search API、Cancel API、Workspace 和 Preview 的统一错误显示；
- TV-06 真实服务层回归。

### 1.3 超出范围

- 修改错误语义之外的 SRS/TDD；
- 新增业务角色、ACL、Record Rule 或权限旁路；
- 改变 Search Service 的条件合并、分页排序或索引策略；
- 将权限错误包装为成功或空结果；
- 静默吞掉异常、记录原始业务字段或返回 SQL/规则内容。

## 2. 错误协议

### 2.1 状态与 retryable

| 状态/错误 | retryable | 行为 |
|---|---:|---|
| `SUCCESS` | 否 | 显示全部结果和计数 |
| `PARTIAL_SUCCESS` | 依错误而定 | 保留成功资源，明确提示失败资源 |
| `EMPTY` | 否 | 显示无结果，不伪造错误 |
| `TIMEOUT` | 是 | 保留已完成结果，允许重试 |
| `RATE_LIMITED` | 是 | 显示限流提示和重试建议 |
| `CANCELLED` | 否 | 显示取消状态，不显示成功形状 |
| `PERMISSION_DENIED` | 否 | 失败关闭，不泄露记录存在性 |
| `CONFIGURATION_ERROR` | 否 | 0 结果失败关闭 |
| `CONFIGURATION_TOO_LARGE` | 否 | 拒绝请求并提示配置错误 |
| `INVALID_REQUEST` | 否 | 拒绝请求，不执行 ORM |
| `CURSOR_INVALID/EXPIRED` | 否 | 拒绝分页请求，要求重新搜索 |
| `INTERNAL_ERROR` | 否 | 通用错误提示，日志关联 request_id |

`PARTIAL_SUCCESS` 的 retryable 规则：

- 失败资源全部为 `TIMEOUT`：`retryable=true`；
- 失败资源全部为 `PERMISSION_DENIED` 或 `CONFIGURATION_ERROR`：`retryable=false`；
- 失败资源错误码混合：`retryable=false`，采用保守策略。

### 2.2 部分成功

- `PARTIAL_SUCCESS` 只在至少一个资源成功且至少一个资源失败时返回；
- `results` 和 `counts` 只包含成功资源；
- `counts.all` 等于成功资源计数之和；
- `counts.by_resource` 只包含成功资源；
- 失败资源计数不出现在任何用户可见字段中；
- `meta.completed_resources` 与 `meta.failed_resources` 必须明确；
- 失败资源的错误码不得泄露其业务数据、Record Rule 或记录存在性；
- 全部资源失败时返回 `FAILED`，不得返回 `PARTIAL_SUCCESS`。

### 2.3 错误响应

```json
{
  "status": "PARTIAL_SUCCESS",
  "request_id": "...",
  "results": [],
  "counts": {"all": 0, "by_resource": {}},
  "errors": [
    {"code": "TIMEOUT", "resource": "sale_order", "retryable": true}
  ],
  "meta": {
    "completed_resources": ["contact"],
    "failed_resources": ["sale_order"]
  }
}
```

错误响应不得包含原始 Query、条件值、字段值、SQL、Record Rule 内容或令牌。

错误响应规则：

- 每个资源最多一个错误；
- `errors` 按资源名稳定排序；
- 同一响应中的错误码唯一；
- `request_id` 每次请求唯一，不跨请求复用。

错误码完整清单：

`SUCCESS`、`PARTIAL_SUCCESS`、`EMPTY`、`TIMEOUT`、`RATE_LIMITED`、
`CANCELLED`、`PERMISSION_DENIED`、`CONFIGURATION_ERROR`、
`CONFIGURATION_TOO_LARGE`、`INVALID_REQUEST`、`CURSOR_INVALID`、
`CURSOR_EXPIRED`、`INTERNAL_ERROR`、`RESOURCE_NOT_ACCESSIBLE`、
`FIELD_NOT_READABLE`、`RELATION_PATH_BLOCKED`、`VIEW_NOT_FOUND`、
`MODEL_NOT_FOUND`、`PERMISSION_OR_DELETED`。

## 3. 必需变更

| ID | 变更 | 验证 |
|---|---|---|
| CC7-CHANGE-001 | 统一状态和错误码映射 | CC7-TEST-001 |
| CC7-CHANGE-002 | 明确 retryable 和 request_id | CC7-TEST-002 |
| CC7-CHANGE-003 | 正确保留部分成功结果和计数 | CC7-TEST-003 |
| CC7-CHANGE-004 | 配置/权限/协议错误失败关闭 | CC7-TEST-004 |
| CC7-CHANGE-005 | Workspace/Preview 显示一致提示 | CC7-TEST-005 |

## 4. 测试契约

| ID | 内容 | 类型 | 预期 |
|---|---|---|---|
| CC7-TEST-001 | 全部状态和错误码映射 | 单元+集成 | 每个错误进入唯一、明确状态 |
| CC7-TEST-002 | retryable、request_id 和错误元数据 | 单元+API | TIMEOUT/RATE_LIMITED 可重试，其余按契约不可重试 |
| CC7-TEST-003 | 单资源失败、多资源部分成功 | 集成 | 成功资源结果/计数保留，失败资源明确 |
| CC7-TEST-004 | 权限、配置、协议和内部错误 | 集成 | 失败关闭，不泄露业务细节 |
| CC7-TEST-005 | Workspace/Preview 浏览器提示 | 浏览器 | 状态、提示和计数一致 |
| CC7-TEST-006 | TV-06 真实 Search Service 回归 | Odoo 集成 | 错误语义与真实服务一致 |
| CC7-TEST-007 | CC-001~CC-006 回归 | Odoo+浏览器 | 既有行为不回归 |
| CC7-TEST-008 | 错误码唯一性 | 单元 | 同一响应中错误码唯一，每个资源最多一个错误 |
| CC7-TEST-009 | 跨用户错误隔离 | 集成 | 用户 A 的错误不被用户 B 复用 |

## 5. 安全与可观测性

- 日志记录 `request_id`、错误码、资源、状态、retryable 和延迟；
- 不记录原始 Query、条件值、字段值、SQL、Record Rule、令牌或完整响应；
- 权限和配置错误默认失败关闭；
- 错误响应必须绑定当前用户请求上下文，不允许跨用户复用；
- Preview 的 `PERMISSION_OR_DELETED` 不得被 Workspace 改写为成功或详细权限错误。
- 同一错误码在相同条件下响应结构稳定，错误码不随时间变化。

日志规范：

- 位置：`services/errors.py`、`services/aggregator.py`；
- `INFO`：`SUCCESS`；
- `WARNING`：`PARTIAL_SUCCESS`、`EMPTY`；
- `ERROR`：`FAILED`、`TIMEOUT`、`RATE_LIMITED`；
- 字段：`request_id`、`user_id`、`error_code`、`resource`、`retryable`、`latency`；
- 不记录原始 Query、条件值、字段值、SQL、Record Rule、令牌或完整响应。

## 6. 停止条件与完成定义

### 6.1 停止条件

1. 权限错误泄露记录、计数、字段或 Record Rule；
2. 未分类异常被包装为 `SUCCESS` 或静默丢失；
3. 部分成功计数包含失败资源；
4. 需要修改官方代码、使用 `sudo()` 读取业务数据或改变 ACL；
5. retryable 语义与 CC-002/TDD 冲突。

### 6.2 完成定义

1. CC7-CHANGE-001~005 实现并有 IHR；
2. CC7-TEST-001~007 执行并有 ATR；
3. TV-06 真实服务层回归通过；
4. Workspace 和 Preview 浏览器显示状态、提示、计数一致；
5. 权限、配置、协议和内部错误全部失败关闭；
6. CC-001~CC-006 既有行为不回归；
7. 错误响应 P95 ≤ 500ms、部分成功响应额外开销 P95 ≤ 100ms；此项为软闸门。

## 7. 既有行为保留与 TDD 防护栏

| ID | 行为 |
|---|---|
| CC7-PRESERVE-001 | CC-002 Search/Cancel API 的错误码、request_id 和 cursor 协议不被覆盖 |
| CC7-PRESERVE-002 | CC-003 权限失败关闭和当前用户边界继续生效 |
| CC7-PRESERVE-003 | CC-004 Preview 的 `PERMISSION_OR_DELETED` 和只读边界继续生效 |
| CC7-PRESERVE-004 | CC-005 Raw Query、Refinement、计数和 Preview 联动不回归 |
| CC7-PRESERVE-005 | CC-006 可选索引策略不改变错误协议 |

- TDD §6.5：未分类异常统一失败关闭；
- TDD §9：错误码、retryable、部分成功和计数由服务端统一决定；
- TDD §10：前端只消费 API 错误协议，不推断 ORM/SQL 错误；
- TDD §12.5：状态、提示和计数必须通过浏览器 HVR 验证；
- 不新增业务模型、ACL、Record Rule、数据库迁移或错误持久化表。

## 8. 错误状态机与用户提示

```text
IDLE -> SEARCHING -> SUCCESS
                 -> PARTIAL_SUCCESS
                 -> TIMEOUT
                 -> RATE_LIMITED
                 -> CANCELLED
                 -> FAILED
                 -> EMPTY
```

Workspace 提示：

- `PARTIAL_SUCCESS`：部分资源搜索失败，显示失败资源；
- `EMPTY`：No results found；
- `TIMEOUT`：搜索超时，已显示部分结果，提供重试；
- `RATE_LIMITED`：请求过于频繁，请稍后重试；
- `CANCELLED`：搜索已取消；
- `FAILED`：搜索失败，请重试；
- `PERMISSION_DENIED`：部分数据不可访问；
- `CONFIGURATION_ERROR`：配置错误，请联系管理员；
- `INTERNAL_ERROR`：内部错误，请稍后重试。

Preview 提示：

- `SUCCESS`：显示记录；
- `PERMISSION_OR_DELETED`：记录不可用或权限已变更；
- `VIEW_NOT_FOUND` / `MODEL_NOT_FOUND`：视图或模型不存在；
- `INTERNAL_ERROR`：内部错误。

## 9. 测试 Fixture、验收与浏览器

Fixture 位置：`tests/fixtures/errors/`，使用 Python，覆盖：

- 成功、失败和混合资源；
- `TIMEOUT`、`PERMISSION_DENIED`、`CONFIGURATION_ERROR`；
- 普通用户、Portal、多公司用户；
- `SUCCESS`、`PARTIAL_SUCCESS`、`FAILED`、`TIMEOUT`。

验收场景：

1. 全部资源成功返回 `SUCCESS`；
2. 部分资源成功返回 `PARTIAL_SUCCESS`；
3. 无结果返回 `EMPTY`；
4. 超时、限流和取消提示正确；
5. 权限、配置、无效请求和内部错误失败关闭；
6. cursor 失效提示重新搜索；
7. 部分成功计数只包含成功资源；
8. 错误响应和日志不泄露业务细节；
9. Workspace 和 Preview 状态一致。

首轮浏览器矩阵：Chrome、Firefox、Safari、Edge 最新版；桌面和窄屏均记录结果。

## 10. 实施结构

```text
services/errors.py               # 错误码、状态和 retryable
services/aggregator.py           # 部分成功、计数和资源状态
controllers/main.py              # API 错误协议
static/src/js/workspace.js       # Workspace 错误提示与重试
static/src/js/preview.js         # Preview 安全错误状态
tests/test_errors.py             # 协议和回归测试
```

前端错误处理接口：

```javascript
handleError(response): void
showPartialSuccess(response): void
showTimeout(response): void
showRateLimited(response): void
showCancelled(): void
showFailed(response): void
showPermissionDenied(): void
showConfigurationError(): void
showInternalError(): void
retry(): Promise<SearchResponse>
```

## 11. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC7-DEC-001 | 所有资源 outcome 显式归类 | 未分类异常静默忽略 | 防止错误伪装成功 |
| CC7-DEC-002 | 权限错误失败关闭 | 返回空成功结果 | 防止存在性泄露 |
| CC7-DEC-003 | 部分成功只保留成功资源 | 返回全部或全部失败 | 保持计数和结果可信 |
| CC7-DEC-004 | retryable 由错误码决定 | 前端按 HTTP 状态猜测 | 保持服务端协议唯一 |
| CC7-DEC-005 | 错误日志只记录错误码和 request_id | 记录完整错误详情 | 防止业务细节泄露 |
| CC7-DEC-006 | 错误响应不跨用户复用 | 共享错误响应缓存 | 防止跨用户泄露 |
| CC7-DEC-007 | 错误响应结构可复现 | 响应随条件和时间变化 | 便于调试和测试 |
| CC7-DEC-008 | 错误码保持稳定 | 随版本随意变更错误码 | 保证前端兼容 |

## 12. Implementation TODO

- 将错误码完整清单整理为带类别和 retryable 的表格；
- 区分审计日志、性能日志和错误日志的保留周期；
- 验证组合 Query 与逐步 Refinement 在错误场景下的结构等价；
- 完成超时、限流、权限拒绝和配置错误的浏览器 HVR；
- 实现 retryable 的退避策略：TIMEOUT 为 1s/2s/4s，RATE_LIMITED 为 5s/10s/30s；
- 接入错误上报，仅上报 request_id、error_code、resource、retryable 和 latency。

## 13. 本轮验证记录

- TV-06 真实 ORM 错误注入：十项检查全部通过；
- 内置浏览器 HVR：`EMPTY`、`RATE_LIMITED`、`PARTIAL_SUCCESS` 和
  `PERMISSION_OR_DELETED` 均显示预期安全状态；
- 详细记录见 [IHR-GS-ERROR-PARTIAL-FAILURE](../history/IHR-GS-ERROR-PARTIAL-FAILURE.md)
  和 [ATR-GS-ERROR-PARTIAL-FAILURE](../history/ATR-GS-ERROR-PARTIAL-FAILURE.md)。

## 14. TD-001 Error / Log Boundary

- 服务端错误消息使用固定模板，不插入用户 Query 或条件值；
- 错误日志只记录 request_id、错误码、资源、retryable 和延迟；
- 不记录 Raw Query、完整 conditions、业务字段值、SQL、Record Rule 或令牌；
- 前端错误消息使用文本节点或 `textContent`，不把用户输入拼接到 HTML；
- 需要输入摘要时只允许记录 `hash(query)`。
