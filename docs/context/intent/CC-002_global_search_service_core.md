# CC-002 Global Search Search Service 核心

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-002 |
| 版本 | v0.1 |
| 状态 | v0.2 FROZEN |
| Intent ID | `GS-SEARCH-SERVICE-CORE` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 2 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN |
| 模块 | `wd_global_search` |
| 冻结批准 | 2026-10-04 19:12，用户批准进入实施；2026-10-04 22:04，用户批准按当前阶段冻结 |

本 CC 只冻结 Phase 2 Search Service 核心执行边界。它不替代 SRS、TDD 或实施计划，不包含完整权限边界、Preview 容器或 Search Workspace UI。

本次阶段冻结只冻结 CC-002 的契约和已形成的实施证据，不宣称 CC-002 全部完成；真实 request 级 timeout、执行中的 active cancel 和完整集成测试继续作为后续实施项，并不得被 CC-003 隐式吸收。

## 1. 变更概述

| 字段 | 值 |
|---|---|
| 工作类型 | 新功能 |
| 变更类型 | 服务层与只读查询接口新增 |
| 目标 | 消费 CC-001 的 Published 配置，在当前 Odoo 用户环境中完成请求解析、条件合并、资源执行、结果去重、计数、分页、错误聚合、超时、取消、并发和限流。 |
| 背景 | 当前模块只有 Preview/配置基础，没有可复用的 Search Service。Phase 2 必须先建立稳定的服务契约，后续 Phase 3 权限边界、Phase 4 Preview 和 Phase 5 前端才能接入。 |

## 2. 上游基线与追溯

### 2.1 SRS

| SRS ID | 标题 | 相关性 |
|---|---|---|
| FR-L1-001~003 | Identifier 搜索 | 在范围内 |
| FR-L2-001~004 | Entity、歧义和关系搜索 | 本 CC 只实现服务编排接口；完整权限关系过滤由 Phase 3 |
| FR-RF-001~009 | Refinement、日期、状态和计数 | 条件结构与结果聚合在范围内 |
| FR-ER-002~003 | 结果状态、错误分类和部分成功 | 在范围内 |
| BR-006~008 | Parsed/Refinement、Effective Conditions、两条路径等价 | 在范围内 |
| BR-010~013 | 条件组合、Snapshot、计数、排序和分页 | 在范围内 |
| NFR-001 | 搜索性能 | 预算、超时和并发边界在范围内 |
| NFR-002 | 数据新鲜度 | 仅作为 Published 配置版本校验上下文 |
| CON-008 | 安全失败关闭 | 在范围内 |
| CON-010 | 配置变更立即生效 | 仅作为配置版本校验上下文 |
| CON-011 | 无权限字段不参与搜索 | 仅作为 Permission Boundary 接口输入 |
| FR-PM-001~008 | 权限 | 仅保留 Permission Boundary 接口；完整权限实现属于 Phase 3 |

### 2.2 DDD

N/A。本项目没有冻结 DDD，不得虚构聚合、实体、值对象或不变式编号。

### 2.3 TDD

| TDD 章节 | 主题 | 相关性 |
|---|---|---|
| §3.2~§3.14 | 请求、条件、超时、并发、分页、快照、可观测性和限流 | 在范围内 |
| §5.3 | Published 配置快照 | Configuration Provider 消费边界 |
| §6.1~§6.5 | 当前用户和失败关闭 | 服务接口必须保留边界；完整权限逻辑由 Phase 3 |
| §9.1~§9.3 | Search Service、结果和错误协议 | 在范围内 |
| §10.1~§10.2 | Search/Cancel 接口 | 在范围内 |
| §12.3~§12.5 | 服务、权限和错误测试 | 在范围内 |

## 3. 范围冻结

### 3.1 在范围内

- HTTP/RPC Facade 与服务端 `request_id`；
- Facade-only `UserContext` 创建；
- Published Configuration Provider；
- Parsed Conditions / Refinement Conditions 合并；
- Resource Executor 的只读 ORM 查询编排；
- Result Identity 去重、稳定排序、分页和签名 cursor；
- Counter Aggregator；
- Partial Success / Error Aggregator；
- 单资源超时、总超时、取消、每用户并发和有界队列；
- 请求速率、结果数、字段数限制；
- 消费当前 Published 版本并读取其 version/checksum；配置版本兼容性由 CC-001 负责，本 CC 只消费兼容的 Published 快照；
- Search 与 Cancel 的服务端协议；
- 单元、集成和服务协议测试。

### 3.2 超出范围

- Phase 3 完整 Record Rule、字段 ACL、关系路径权限硬边界；
- Search Workspace 菜单、前端输入框、Refinement UI 和导航；
- Form View Preview、只读容器和 Preview API；
- PostgreSQL 业务索引创建或迁移；
- Natural Language Parser、LLM、向量检索、Elasticsearch/OpenSearch；
- 业务数据写入、配置 UI 改造和 `sudo()` 权限旁路；
- 性能压测结论和百万级性能达标声明。

### 3.3 非目标

- 不发布或修改 CC-001 已建立的配置版本；
- 不把 Draft/Rejected 配置作为运行时配置；
- 不重新定义 SRS 查询语义；
- 不将 Phase 2 的 Permission Boundary 接口描述为已完成的权限安全审计。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| 新增服务 | `mymodules/wd_global_search/services/` 下的 facade、provider、conditions、executor、aggregator、limiter |
| 控制器 | `mymodules/wd_global_search/controllers/main.py` 中新增只读 Search/Cancel 路由，保留既有 Preview 路由 |
| 测试 | `mymodules/wd_global_search/tests/` 下 Search Service 单元/集成测试与 fixture |
| 模块接线 | `__init__.py`、manifest 中接入新服务；不新增普通用户 Workspace 菜单 |
| 审计/观测 | 使用 TDD 已冻结的 request metadata，不记录原始业务字段值 |

### 4.2 禁止

- 修改 `odoo/` 或官方 addons；
- 在业务查询、计数、快照或 Preview 中使用 `sudo()`；
- 从请求体接受 `uid`、company、groups 或可读字段作为可信权限输入；
- Search Service 直接读取 HTTP 全局上下文；
- 返回无权限资源的记录 ID、数量、字段值或 Record Rule 内容；
- 使用共享缓存保存未按用户隔离的业务结果；
- 实现前端菜单、Search Workspace 或 Preview 容器；
- 引入外部搜索引擎、LLM、向量数据库或任意新技术栈。

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE |
|---|---|---|---|
| 1 | 没有可复用 Search Service | Facade 从当前 `request.env` 创建 UserContext，并传入服务层 | CC-CHANGE-001 |
| 2 | 没有 Published 配置消费路径 | Provider 每次请求读取当前 Published version/checksum；无 Published、快照解析失败、checksum 不匹配或版本不可消费均返回 `CONFIGURATION_ERROR` | CC-CHANGE-002 |
| 3 | 没有条件合并和资源执行 | Parsed/Refinement 条件按 TDD 规则合并，按 Resource 执行只读 ORM 查询 | CC-CHANGE-003 |
| 4 | 没有统一结果身份和计数 | 去重、稳定排序后分页；计数独立于分页 | CC-CHANGE-004 |
| 5 | 没有超时、取消和并发边界 | 实现 request_id、单资源/总超时、当前用户取消、并发和有界队列 | CC-CHANGE-005 |
| 6 | 没有统一错误协议 | 返回 SUCCESS、PARTIAL_SUCCESS、TIMEOUT、RATE_LIMITED 或 FAILED 结构，不泄露业务细节 | CC-CHANGE-006 |

## 6. 既有行为保留

| ID | 行为 / 契约 | CC-PRESERVE |
|---|---|---|
| 1 | Search Service 只读取当前 Published 的最后一次成功发布/应用快照；快照在单次请求内不可变 | CC-PRESERVE-001 |
| 2 | 既有 `/wd_global_search` Preview 路由和只读策略不变 | CC-PRESERVE-002 |
| 3 | 业务查询只通过当前用户 Odoo ORM 环境，不使用 `sudo()` | CC-PRESERVE-003 |
| 4 | 现有错误状态和 `PERMISSION_OR_DELETED` Preview 响应不被 Search Service 改写 | CC-PRESERVE-004 |
| 5 | 普通用户不因本 CC 获得配置模型直接访问或配置管理员菜单 | CC-PRESERVE-005 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| 当前用户环境与 UserContext 来源 | 适用 | Facade 单一入口 | CC-TEST-001、CC-TEST-002 |
| Published snapshot/version/checksum | 适用 | Configuration Provider | CC-TEST-003 |
| Effective Conditions AND/OR 规则 | 适用 | Condition Merger | CC-TEST-004 |
| Result Identity 去重和稳定排序 | 适用 | Aggregator | CC-TEST-005 |
| 超时、取消、并发和限流 | 适用 | Orchestrator/Limiter | CC-TEST-006、CC-TEST-007 |
| 失败关闭和错误协议 | 适用 | Error Aggregator | CC-TEST-008 |
| 完整权限硬边界 | 部分适用 | 仅定义接口，不宣称完成 | Phase 3 CC |
| §3.10 分页 cursor | 适用 | `cursor.py` 签名、绑定和失效校验 | CC-TEST-005、CC-TEST-010 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否 |
| 业务数据写入 | 否 |
| 运行时缓存 | 进程内短生命周期缓存，按用户/配置版本隔离 |
| 恢复 / 回滚 | 删除新增服务接线并恢复既有 Preview 路由 |
| 验证 | Odoo 模块升级、服务测试和既有 Preview smoke |

## 9. API / 集成影响

| 接口 | 方法 | 规则 |
|---|---|---|
| `/wd_global_search/api/search` | POST | 只接受 query、conditions、resources、offset/limit 或 signed cursor；不接受权限声明 |
| `/wd_global_search/api/cancel` | POST | 只接受服务端返回的 request_id；仅当前用户可取消自己的请求 |

响应必须包含 `status`、`request_id`、`results`、`counts`、`errors`、`meta`。不新增写 API，不改变既有 Preview API。

### 9.1 Search Request Boundary（TD-001）

- Raw Query 最大长度为 500 字符；
- Parsed Conditions 与 Refinement Conditions 合计最多 20 个；
- 条件嵌套深度最多 3 层；
- Relation Path 最多 2 层；
- 控制字符、非文本 Query、超限数量和超深结构返回 `INVALID_REQUEST`；
- Request Timeout 上限为 5 秒，Resource Timeout 上限为 3 秒；
- Result limit、pagination limit、rate limit 和 concurrency limit 沿用本 CC 既有契约；
- 请求不得携带可执行 domain、动态代码或客户端权限声明；
- 错误消息和日志不得包含 Raw Query、完整 conditions 或业务字段值。

## 10. 安全 / 权限影响

- Facade 是唯一允许读取 `request.env` 的层；
- UserContext 的 `uid`、公司、语言和时区来自当前请求环境，只能向下传递；
- Phase 2 不以 `sudo()` 替代业务权限；
- Permission Boundary 作为显式接口传递给 Resource Executor，完整 Record Rule/字段 ACL 验证进入 Phase 3；
- cursor 使用服务端 HMAC-SHA256 签名，绑定配置版本、条件摘要、用户上下文摘要、排序版本和过期时间；
- 日志仅记录 request_id、配置版本、resource、延迟和错误码，不记录原始 query、字段值或 SQL。

## 11. 测试契约

| 测试 ID | 对应变更 | 测试类型 | 预期结果 | 人工验证 |
|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-001 | Facade 集成 | UserContext 全部来自当前 env；请求体 uid/company/groups 被拒绝或忽略 | 否 |
| CC-TEST-002 | CC-CHANGE-001 | 单元 | Search Service 不读取 HTTP 全局上下文，可注入测试 UserContext | 否 |
| CC-TEST-003 | CC-CHANGE-002 | 集成 | 只消费 Published；无 Published、版本/checksum 异常或快照解析失败均返回 `CONFIGURATION_ERROR` | 否 |
| CC-TEST-004 | CC-CHANGE-003 | 单元 | 同维度 OR、不同维度 AND；无效条件不进入 Effective Conditions | 否 |
| CC-TEST-005 | CC-CHANGE-004 | 集成 | 以 Result Identity 去重，分页在去重/排序后执行，计数不受分页影响 | 否 |
| CC-TEST-006 | CC-CHANGE-005 | 单元 | 单资源超时不丢弃已完成资源；总超时返回 TIMEOUT 和已完成结果 | 否 |
| CC-TEST-007 | CC-CHANGE-005 | 集成 | 取消仅允许当前用户取消自己的 request_id；并发/队列/速率超限返回 RATE_LIMITED | 否 |
| CC-TEST-008 | CC-CHANGE-006 | 协议回归 | 权限异常、配置异常和内部协议异常失败关闭，不返回猜测数量或记录信息 | 否 |
| CC-TEST-009 | CC-PRESERVE-002 | 回归 | 既有 Preview 路由、只读行为和模块安装 smoke 不回归 | 是 |
| CC-TEST-010 | CC-CHANGE-004 | 单元 + 集成 | cursor 签名验证通过；跨用户、跨版本、条件变化、排序变化和过期 cursor 均被拒绝 | 否 |

## 12. 停止条件 / 升级闸门

- 需要完整实现 Record Rule、字段 ACL、Relation Path 权限硬边界：停止，进入 Phase 3 CC；
- 需要新增或修改 Search Workspace、菜单或 Preview 容器：停止，进入 Phase 4/5 CC；
- SRS/TDD 未定义的查询语义、排序、评分或计数规则：停止，回到 TDD；
- 需要 `sudo()`、管理员环境或客户端权限声明：立即停止并进行安全评审；
- 需要业务数据迁移、数据库索引迁移或外部技术：停止，建立独立 CC；
- 无法保证失败关闭、用户隔离 cursor 或当前用户取消边界：不得进入实现完成状态。
- 需要回滚 Published 配置版本：业务回滚进入 CC-001 修订；技术回滚进入 TDD 修订；本 CC 只消费 Published，不实现回滚。

## 13. 完成定义 / 关闭标准

1. CC-CHANGE-001~006 均已实现并有 IHR；
2. CC-TEST-001~010 均已执行并有 ATR；
3. Search/Cancel 协议、cursor、超时、并发和限流有可复现证据；
4. 当前用户环境和 Published 配置消费有 ORM/集成证据；
5. 既有 Preview 和模块安装 smoke 通过；
6. 无官方代码修改、无 `sudo()` 业务读取、无普通用户菜单越权；
7. 无 Search Workspace、完整权限 Phase 3 或 Preview Phase 4/5 的完成宣称；
8. 若需浏览器人工验证，单独建立 HVR-002，不得把自动化测试冒充人工验证；
9. Search Service 性能基线已记录单资源、多资源和 20 并发的 P50/P95/P99 及超时边界，作为软闸门和后续 TV-01 输入；
10. CC-002 已于 2026-10-04 19:12 获批准冻结并进入实施。

## 14. 追溯矩阵

| 上游 | CC-002 落点 |
|---|---|
| FR-L1、FR-L2 | CC-CHANGE-003、CC-TEST-004 |
| FR-RF、BR-006~008、BR-010~013 | CC-CHANGE-003/004、CC-TEST-004/005 |
| FR-ER-002~003 | CC-CHANGE-006、CC-TEST-008 |
| NFR-001~002 | CC-CHANGE-002/005、CC-TEST-003/006/007 |
| CON-008、CON-010、CON-011 | §7、§10、CC-TEST-003/008/010 |
| TDD §3、§9、§10 | CC-CHANGE-001~006 |
| TDD §6 | §10、CC-TEST-008；完整实现由 Phase 3 承接 |
| Phase 2 Implementation Plan | 全文 |

## 15. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | Phase 2 先实现服务正确性，再实现完整权限硬边界 | 将 Phase 2/3 合并 | 实施计划已拆分依赖；避免把权限风险隐藏在服务编排中 |
| CC-DEC-002 | Facade 创建 UserContext，Service 不直接读取 request.env | Service 内部直接读取 HTTP 上下文 | 便于测试并防止调用方伪造 |
| CC-DEC-003 | 只消费 Published 配置，Draft/Rejected 不可运行 | 自动选择最新 Draft | 防止未批准配置影响搜索 |
| CC-DEC-004 | cursor 使用签名 JSON 并绑定用户/配置/条件/排序 | 使用裸 offset 或客户端可改 cursor | 防止跨用户、跨版本复用和结果篡改 |
| CC-DEC-005 | 本 CC 不接入普通用户 Global Search 菜单 | 顺便修改根菜单 | 菜单与 Workspace 属于后续 Phase 5，避免扩大 CC-002 |

### 15.1 CC-001 → CC-002 接口契约

| 契约 | 约束 |
|---|---|
| Provider 输入 | `domain_key` 和当前请求的 `UserContext` |
| Provider 输出 | `ConfigSnapshot`，包含 `domain_key`、`version_id`、`checksum`、Published Resource、字段、日期、状态、Snapshot、评分和性能配置 |
| 读取边界 | CC-002 只读取 `ConfigSnapshot`，不直接读取配置模型的业务关系 |
| 不可变性 | Published snapshot 在一次请求内不可变；版本或 checksum 变化使缓存失效 |
| 异常 | 无 Published、解析失败、checksum 不匹配或不兼容配置均返回 `CONFIGURATION_ERROR` |
| 责任归属 | CC-001 负责配置模型和版本兼容；CC-002 负责消费、校验和运行时失败关闭 |

## 16. 实施结构与接口约束

### 16.1 服务模块结构

```text
mymodules/wd_global_search/services/
  __init__.py
  facade.py           # HTTP/RPC 入口，创建 UserContext
  provider.py         # Published Configuration Provider
  conditions.py       # Condition Merger
  executor.py         # Resource Executor
  aggregator.py       # Result/Count/Error Aggregator
  limiter.py          # 并发、队列和速率限制
  cursor.py           # HMAC cursor 编码和验证
  errors.py           # 错误码和错误聚合
  types.py            # UserContext、Request、Response 类型
```

### 16.2 服务接口签名

```python
# facade.py
def search(request: SearchRequest, env) -> SearchResponse: ...
def cancel(request_id: str, env) -> CancelResponse: ...

# provider.py
def published_snapshot(domain_key: str, user_context: UserContext) -> ConfigSnapshot: ...

# conditions.py
def merge(parsed: list[dict], refinement: list[dict], deleted: list[dict]) -> EffectiveConditions: ...

# executor.py
def execute(
    resource: dict,
    conditions: EffectiveConditions,
    context: UserContext,
) -> ResourceOutcome: ...

# aggregator.py
def merge(outcomes: list[ResourceOutcome], request: SearchRequest) -> SearchResponse: ...

# cursor.py
def encode(cursor_data: dict) -> str: ...
def decode(cursor: str, user_context: UserContext) -> dict: ...

# limiter.py
def check_rate(user_id: int, limit: int) -> bool: ...
def check_concurrency(user_id: int, limit: int) -> bool: ...
```

### 16.3 类型定义

```text
UserContext:
  uid: int
  company_id: int
  company_ids: list[int]
  lang: str
  tz: str
  groups: list[int]  # 只读派生值，不接受请求体覆盖

SearchRequest:
  raw_query: str
  parsed_conditions: list[dict]
  refinement_conditions: list[dict]
  resource_scope: list[str]
  offset: int
  limit: int
  cursor: str | None

SearchResponse:
  status: str
  request_id: str
  results: list[dict]
  counts: dict
  errors: list[dict]
  meta: dict

ResourceOutcome:
  resource: str
  status: str
  results: list[dict]
  count: int
  error: dict | None
  latency: float
```

### 16.4 错误码清单

| 错误码 | 语义 | 默认可重试 |
|---|---|---|
| `SUCCESS` | 所有请求资源成功 | 否 |
| `PARTIAL_SUCCESS` | 至少一个资源成功，至少一个资源失败 | 按错误项 |
| `FAILED` | 请求未产生可安全返回的结果 | 否 |
| `TIMEOUT` | 单资源或总请求预算耗尽 | 是 |
| `RATE_LIMITED` | 速率、并发或队列限制 | 是 |
| `PERMISSION_DENIED` | 权限边界异常 | 否 |
| `CONFIGURATION_ERROR` | Published 配置不可消费 | 否 |
| `CONFIGURATION_TOO_LARGE` | 配置快照超过限制 | 否 |
| `CONCURRENCY_LIMIT` | 当前用户并发超过限制 | 是 |
| `CURSOR_INVALID` | cursor 签名、绑定或内容无效 | 否 |
| `CURSOR_EXPIRED` | cursor 超过有效期 | 否 |
| `INTERNAL_ERROR` | 未分类的服务内部错误 | 否 |

### 16.5 性能预算

以下为本 CC 的默认运行时预算，均可由 Published Performance Config 限制，但不得由客户端扩大：

| 项目 | 默认值 |
|---|---:|
| 单资源超时 | 3 秒 |
| 总请求超时 | 5 秒 |
| 单资源最大返回 | 50 条 |
| 总最大返回 | 200 条 |
| 最大字段数 | 50 |
| 最大 Relation Path depth | 2 |
| 每用户并发 | 3 |
| 用户队列上限 | 10 |
| 每用户速率 | 60 次/分钟 |

性能基线（单资源、多资源、20 并发的 P50/P95/P99）为软闸门：必须记录为后续 TV-01 输入，但不以未完成压测阻塞本 CC 的功能关闭。

### 16.6 日志规范

- 位置：`services/` 各模块的服务日志与既有 observability metadata；
- `INFO`：成功请求、配置版本、资源延迟；
- `WARNING`：部分成功、超时、限流；
- `ERROR`：配置错误、权限边界异常、协议或内部错误；
- 字段：`request_id`、`user_id`、`config_version`、`resource`、`latency`、`status`、`error_code`；
- 禁止记录：原始 query、条件值、业务字段值、SQL、Record Rule 内容、令牌和路径。

### 16.7 测试 fixture 规范

- 位置：`mymodules/wd_global_search/tests/fixtures/search_service/`；
- 格式：Python fixture；
- 内容：多公司/多角色用户、Published 配置、多资源业务数据、有效/过期/跨用户 cursor；
- 隔离：每个测试套件使用唯一标记；
- 清理：测试结束不得残留由 fixture 创建的业务记录；
- 权限 fixture 的完整十类场景由 Phase 3 CC 独立维护，本 CC 只提供 Service 可注入的 Boundary stub。
