# CC-003 Global Search 权限边界

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-003 |
| 版本 | v0.2 DRAFT |
| 状态 | v0.2 FROZEN，实施阶段冻结 |
| Intent ID | `GS-SEARCH-PERMISSION-BOUNDARY` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 3 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 将当前用户、模型访问、字段访问、Record Rule、Relation Path 和失败关闭固化为 Search Service 不可绕过的权限边界 |
| 冻结批准 | 2026-10-04 22:32，用户批准冻结并进入实施 |
| 阶段关闭批准 | 2026-10-05 19:24，用户批准冻结 CC-003 并进入后续阶段 |

本 CC 只冻结 Phase 3 权限边界的执行契约，不替代 SRS、TDD 或 Implementation Plan。它不包含 Preview 容器、Search Workspace UI、索引性能补测或新的业务权限语义。

## 1. 变更概述

| 字段 | 值 |
|---|---|
| 工作类型 | 安全边界强化 |
| 变更类型 | Search Service 权限上下文、过滤与失败关闭 |
| 目标 | 确保搜索结果、计数、字段和关系路径均受当前 Odoo 用户权限约束；任何权限边界无法确定时不返回猜测数据 |
| 前置条件 | CC-001 Published 配置可消费；CC-002 Facade、UserContext、Provider、Executor 和 Aggregator 可注入权限边界 |
| 不变更 | 不新增普通用户配置模型权限；不修改官方代码；不使用 `sudo()` 读取业务数据 |

## 2. 上游基线与追溯

### 2.1 SRS

| SRS ID | 标题 | 相关性 |
|---|---|---|
| FR-PM-001~008 | 当前用户、模型、字段、关系和失败关闭权限 | 在范围内 |
| FR-ER-002~003 | 结果状态、错误分类和安全失败 | 在范围内 |
| FR-L1-001~003 | Identifier 搜索 | 必须经过权限过滤 |
| FR-L2-001~004 | Entity、关系和歧义搜索 | 关系路径权限在范围内 |
| FR-RF-001~009 | Refinement、日期、状态和计数 | 计数必须与授权结果一致 |
| BR-010~013 | 条件、快照、计数、排序和分页 | 权限过滤先于计数和分页 |
| NFR-001 | 搜索性能 | 权限过滤不能绕过 Odoo ORM 规则 |
| NFR-002 | 数据新鲜度 | 权限变化后的新请求使用新的当前用户上下文 |
| CON-008 | 安全失败关闭 | 在范围内 |
| CON-010 | 配置变更立即生效 | Published 配置引用和权限判断使用当前有效版本 |
| CON-011 | 无权限字段不参与搜索 | 在范围内 |

### 2.2 DDD

N/A。本项目没有冻结 DDD；不得虚构聚合、实体、值对象或不变式编号。

### 2.3 TDD

| TDD 章节 | 主题 | 本 CC 落实 |
|---|---|---|
| §6.1 | 当前用户环境 | Facade 创建并向下传递，不接受请求体权限声明 |
| §6.2 | Record Rule 与模型权限 | ORM 当前用户环境执行，拒绝权限旁路 |
| §6.3 | 字段权限 | 字段白名单和访问检查后才可搜索/返回 |
| §6.4 | Relation Path | 每一段关系路径都必须可验证 |
| §6.5 | 失败关闭 | 权限异常、字段未知、关系不安全时拒绝该资源 |
| §9.1~§9.3 | Search 结果、计数和错误协议 | 不泄露无权记录、数量或字段值 |
| §12.4 | 权限测试 | 多用户、多公司、Portal、字段权限和规则 fixture |

## 3. 范围冻结

### 3.1 在范围内

- 当前用户 `env` / `UserContext` 的不可伪造传递；
- 模型 `check_access_rights`、Record Rule 和 ORM 查询边界；
- Searchable Field 的字段读取权限和返回字段过滤；
- Relation Path 每一段模型、字段和访问权限校验；
- 多公司环境下的公司域和当前用户规则；
- 无权记录不出现在结果、计数、分页或 cursor 中；
- 权限变更后新请求使用新的当前用户环境；
- 权限异常的资源级失败关闭和整体错误聚合；
- Permission Boundary 接口、fixture、单元/集成/浏览器验证；
- 不使用 `sudo()`、管理员环境或请求体声明绕过业务权限。

### 3.2 超出范围

- Search Workspace、搜索输入框、Refinement UI 和导航；
- Form View Preview 容器及按钮/Chatter/附件阻断；
- PostgreSQL 索引创建、迁移、回滚和百万级性能结论；
- 新增业务角色、修改官方模型 ACL 或改变既有业务权限；
- 业务数据迁移、批量修权或 `sudo()` 修复历史数据；
- LLM、向量检索、外部搜索引擎；
- CC-002 尚未完成的真实 request timeout 和 active cancel 实现。

### 3.3 非目标

- 不把“管理员可读”作为普通用户权限；
- 不把配置管理员组权限传递给业务搜索；
- 不在请求体接受 `uid`、groups、company_ids 或权限声明；
- 不返回无权记录的存在性、总数、record ID、字段值或错误细节；
- 不宣称 Phase 4 Preview 或 Phase 5 前端完成。

## 4. 变更边界

### 4.1 允许

- `services/` 权限边界、字段过滤、关系路径校验和错误聚合；
- CC-002 Resource Executor 的权限注入点；
- 测试 fixture、测试数据和测试专用慢执行适配器；
- 必要的模块 Python/XML/ACL 接线，但不修改官方代码；
- IHR、ATR、HVR 文档记录。

### 4.2 禁止

- 在业务读取中使用 `sudo()`、`with_user(SUPERUSER_ID)` 或管理员环境；
- 从请求体读取或信任权限、用户、公司和字段授权信息；
- 先读取全部记录再在 Python 中模拟 Record Rule；
- 在权限异常时返回成功形状、猜测计数或部分敏感结果；
- 修改 `odoo/` 或官方 addons；
- 将 Preview、Workspace、索引或新业务语义混入本 CC。

## 5. 必需的行为变更

| ID | 当前行为/缺口 | 期望行为 | 验证 |
|---|---|---|---|
| CC3-CHANGE-001 | Service 已有 UserContext，但权限边界尚未硬化 | 所有资源执行只使用 Facade 创建的当前用户上下文 | CC3-TEST-001 |
| CC3-CHANGE-002 | 模型、Record Rule 和公司域缺少统一边界证据 | ORM 查询遵守当前用户模型和记录规则 | CC3-TEST-002 |
| CC3-CHANGE-003 | Searchable Field 结果字段未完成字段权限过滤 | 无权字段不参与查询、不出现在结果或计数上下文 | CC3-TEST-003 |
| CC3-CHANGE-004 | Relation Path 尚未逐段验证 | 任一关系段不可访问或不安全时拒绝该路径 | CC3-TEST-004 |
| CC3-CHANGE-005 | 权限异常的资源失败关闭缺少集成证据 | 返回明确权限错误，不泄露记录、数量或字段值 | CC3-TEST-005 |
| CC3-CHANGE-006 | 多公司、多角色、Portal 边界未完成覆盖 | 每个用户只能看到其当前 Odoo 环境允许的结果 | CC3-TEST-006 |
| CC3-CHANGE-007 | 权限变化后的新请求缺少证据 | 新请求重新建立当前用户环境，不复用跨用户授权缓存 | CC3-TEST-007 |

### 5.1 权限边界与配置版本交互

- Permission Boundary 消费 CC-001 Published 配置中的模型、Searchable Field 和 Relation Path 引用；
- Published 配置引用用户无权访问的字段时，该字段从搜索字段集合中排除，不参与查询或结果输出；
- Published 配置引用用户无权访问的模型时，该资源从本次搜索范围中排除，并按权限协议记录；
- Published 配置引用无效模型、字段或关系路径时，返回 `CONFIGURATION_ERROR`，不得以空结果静默替代；
- CC-003 不读取 Draft/Rejected 配置，也不修改 CC-001 的 Published 快照。

## 6. 既有行为保留

| ID | 必须保留的行为 | 原因 |
|---|---|---|
| CC3-PRESERVE-001 | CC-001 Published 配置和快照不可被业务搜索修改 | 配置与业务读取职责分离 |
| CC3-PRESERVE-002 | CC-002 Search/Cancel 协议结构保持兼容 | 权限边界是服务内部约束，不重定义协议 |
| CC3-PRESERVE-003 | 已完成的资源搜索、去重、排序、分页和 cursor 语义不回退 | 权限过滤应发生在结果聚合前 |
| CC3-PRESERVE-004 | 既有 Preview 继续只读且使用当前用户权限 | Phase 4 之前不扩大 Preview 范围 |
| CC3-PRESERVE-005 | 普通用户不能读取配置模型或看到配置管理员菜单 | 权限边界不授予配置权限 |

## 7. TDD 防护栏

| TDD 防护栏 | 适用性 | 落实位置 | 验证 |
|---|---|---|---|
| §6.1 当前用户原则 | 适用 | UserContext/Facade | CC3-TEST-001 |
| §6.2 Record Rule | 适用 | ORM Resource Executor | CC3-TEST-002 |
| §6.3 字段权限 | 适用 | Field Permission Boundary | CC3-TEST-003 |
| §6.4 Relation Path | 适用 | Relation Path Guard | CC3-TEST-004 |
| §6.5 失败关闭 | 适用 | Error Aggregator | CC3-TEST-005 |
| §9.3 错误协议 | 适用 | Permission error mapping | CC3-TEST-005 |
| §12.4 权限测试 | 适用 | Isolated fixtures and browser evidence | CC3-TEST-006~007 |
| §3.10 分页 cursor | 适用 | 用户上下文、配置版本和条件绑定 | CC3-TEST-002、009 |
| §3.11 配置快照 | 适用 | 只消费 Published snapshot 中的权限相关引用 | CC3-TEST-002、010 |

## 8. 数据 / 迁移影响

- 不迁移业务数据；
- 不修改官方模型字段或 ACL；
- 测试 fixture 仅在隔离测试数据库创建；
- 不建立跨用户共享搜索结果缓存；
- 不缓存授权结果跨越用户、公司、权限上下文或请求；
- 配置快照不保存用户业务字段值或权限规则内容。

## 9. API / 集成影响

| 接口 | 影响 |
|---|---|
| `/wd_global_search/api/search` | 请求体不得声明权限；响应只包含当前用户授权结果 |
| `/wd_global_search/api/cancel` | 仅当前用户可取消自己的活动 request_id |
| `SearchService` | 接收 Facade 创建的 UserContext 和 Permission Boundary，不读取 HTTP 全局上下文 |
| `ResourceExecutor` | 通过当前用户 ORM 环境查询，并在返回前执行字段过滤 |
| `ConfigurationProvider` | 只读取 Published snapshot，不读取 Draft/Rejected |

## 10. 安全 / 权限影响

- 当前用户、公司和语言环境来自服务端 `request.env`；
- 请求体中的 `uid`、groups、company_ids 和权限声明一律忽略或拒绝；
- 业务数据不使用 `sudo()`、超级用户或管理员环境；
- Search Service 读取 CC-001 Published 配置和 `database.secret` 时可使用隔离的控制面只读环境；该例外不得用于任何业务模型、业务记录或业务字段；
- 权限错误、未知字段、不可验证关系和规则异常默认失败关闭；
- 计数在权限过滤和去重后计算；
- 日志只记录 request_id、resource、错误码和延迟，不记录字段值、SQL、Record Rule 内容或令牌；
- cursor 必须绑定用户上下文和 Published 配置版本；
- 任一跨用户缓存或共享授权结果属于停止条件。

## 11. 测试契约

| ID | 测试内容 | 类型 | 预期结果 | 人工验证 |
|---|---|---|---|---|
| CC3-TEST-001 | UserContext 不可由请求体伪造 | 单元+集成 | 请求体用户/公司字段不改变服务端上下文 | 否 |
| CC3-TEST-002 | 模型访问和 Record Rule | ORM 集成 | 无权记录不出现在结果、计数、分页和 cursor | 否 |
| CC3-TEST-003 | 字段权限 | ORM 集成 | 无权字段不搜索、不返回、不泄露存在性 | 否 |
| CC3-TEST-004 | Relation Path 逐段权限 | 单元+集成 | 不安全路径被拒绝并失败关闭 | 否 |
| CC3-TEST-005 | 权限异常错误协议 | 集成 | 返回 `PERMISSION_DENIED` 或安全失败状态，无敏感结果 | 否 |
| CC3-TEST-006 | 多公司、多角色、Portal | ORM 集成 | 每类用户只得到其当前环境授权结果 | 否 |
| CC3-TEST-007 | 权限变化后新请求 | 集成+浏览器 | 新请求反映权限变化，不复用旧授权结果 | 是 |
| CC3-TEST-008 | 配置/Preview 回归 | 模块+浏览器 | CC-001 配置管理员隔离、既有 Preview 只读不回归 | 是 |
| CC3-TEST-009 | 跨用户缓存隔离 | 集成 | 用户 A 的结果不会被用户 B 复用；权限变化后缓存失效 | 否 |
| CC3-TEST-010 | Published 配置权限引用 | 集成 | 无权模型/字段/路径按规则排除或配置失败关闭 | 否 |

## 12. 停止条件 / 升级闸门

1. 需要改变 SRS 权限语义：停止，回到 SRS 评审；
2. TDD §6 无法表达实现边界：停止，修订 TDD；
3. 需要 `sudo()`、超级用户或管理员环境读取业务数据：立即停止并进行安全评审；
4. 需要修改官方 Odoo 代码或官方 addons：停止并升级架构评审；
5. 需要新增角色、改变既有业务 ACL 或迁移业务权限：新建独立 CC；
6. 需要 Preview 写入、Workspace UI 或索引迁移：进入对应后续 Phase/CC；
7. 无法证明计数、cursor 和结果都经过权限过滤：不得完成；
8. 发现跨用户、跨公司共享缓存：立即停止并清除该设计；
9. 权限边界与 CC-002 timeout/cancel 交互影响结果：回到相应 CC 修订；本 CC 不实现 timeout/cancel；
10. 需要改变 CC-002 Search/Cancel 协议：停止并提交接口变更评审。

## 13. 完成定义 / 关闭标准

1. CC3-CHANGE-001~007 均实现并有 IHR 记录；
2. CC3-TEST-001~008 均执行并有 ATR 证据；
3. 多用户、多公司、Portal、字段权限和关系路径 fixture 通过；
4. 至少一个浏览器 HVR 验证权限变化和失败关闭；
5. 无 `sudo()`、超级用户旁路、官方代码修改或请求体权限信任；
6. 结果、计数、分页和 cursor 均无越权泄露；
7. CC-001 配置管理员隔离和 CC-002 已验证 Search/Preview 行为不回归；
8. 未宣称 Preview、Workspace、索引和整体项目完成；
9. 权限边界性能基线已记录：单资源、多资源、Relation Path 校验和 20 并发 P50/P95/P99；该项为软闸门，作为 TV-01 输入。

## 14. 追溯矩阵

| 上游 | CC-003 |
|---|---|
| SRS FR-PM-001~008 | CC3-CHANGE-001~007、CC3-TEST-001~007 |
| SRS FR-ER-002~003 | CC3-CHANGE-005、CC3-TEST-005 |
| TDD §6.1~§6.5 | CC3-CHANGE-001~005 |
| TDD §9、§12.4 | CC3-TEST-002~008 |
| Implementation Plan Phase 3 | 全部章节 |

## 15. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC3-DEC-001 | 权限过滤在 ORM 当前用户环境和结果聚合前完成 | 先查全量再 Python 过滤 | 防止记录、计数和字段存在性泄露 |
| CC3-DEC-002 | UserContext 只由 Facade 创建 | 从请求体读取用户/公司 | 请求体不可作为权限边界 |
| CC3-DEC-003 | 关系路径逐段验证 | 只验证起始模型 | 关系中间段同样可能泄露数据 |
| CC3-DEC-004 | 权限异常默认失败关闭 | 返回部分猜测结果 | 安全优先，避免成功形状泄露 |
| CC3-DEC-005 | 不改变既有业务 ACL | 在 CC 中新增业务角色 | 本 CC 固化 Search 边界，不重定义业务权限 |
| CC3-DEC-006 | Permission Boundary 在 CC-002 Executor 查询前和字段返回前被调用 | 由各资源自行决定权限 | 统一入口可证明不绕过权限 |

## 16. 实施结构与接口约束

```text
services/
  permission_boundary.py   # 当前用户、模型/字段/关系权限检查
  executor.py              # 只读 ORM 执行与权限过滤
  conditions.py            # Effective Conditions
  errors.py                # 权限错误和失败关闭
  facade.py                # UserContext 唯一创建点
  types.py                 # PermissionContext / AuthorizedField / PathCheck
tests/
  test_permission_boundary.py
  fixtures/permissions/
```

建议接口：

```python
class PermissionBoundary:
    def authorize_resource(self, env, resource, context): ...
    def authorize_field(self, model, field_name, context): ...
    def authorize_relation_path(self, env, resource, path, context): ...
    def filter_readable_fields(self, recordset, fields, context): ...
```

所有接口必须返回明确的授权结果或错误，不得以空列表、宽松默认或静默异常代替失败关闭。

### 16.1 CC-002 → CC-003 接口契约

- CC-002 Resource Executor 在查询前调用 `authorize_resource(env, resource, context)`；
- CC-002 在返回字段前调用 `filter_readable_fields(recordset, fields, context)`；
- CC-002 在执行关系路径前调用 `authorize_relation_path(env, resource, path, context)`；
- CC-003 消费 CC-001 Published snapshot 的模型、字段和路径引用；
- CC-003 返回明确授权结果或错误；CC-002 不得把权限错误静默转换为空成功；
- CC-002 聚合器只能聚合已完成权限过滤的结果，计数、分页和 cursor 不得绕过该边界。

### 16.2 权限边界错误码

| 错误码 | 含义 | 响应规则 |
|---|---|---|
| `PERMISSION_DENIED` | 当前用户无权访问资源或字段 | 失败关闭，不返回业务细节 |
| `RESOURCE_NOT_ACCESSIBLE` | 资源模型对当前用户不可访问 | 资源级排除或失败，按协议聚合 |
| `FIELD_NOT_READABLE` | 字段不可读或不可搜索 | 字段排除，不返回字段值 |
| `RELATION_PATH_BLOCKED` | 关系路径某段被权限阻断 | 路径拒绝，不返回关系结果 |
| `CONFIGURATION_ERROR` | Published 配置引用无效权限对象 | 整体失败关闭 |
| `INTERNAL_ERROR` | 无法分类的内部异常 | 整体失败关闭，不暴露堆栈 |

### 16.3 类型定义

```python
PermissionContext:
  user_id: int
  company_id: int
  company_ids: list[int]
  lang: str
  tz: str
  groups: list[int]  # 只读服务端上下文
  allowed_models: list[str]
  allowed_fields: dict[str, list[str]]
  allowed_relation_paths: list[dict]

AuthorizedField:
  model: str
  field_name: str
  field_type: str
  readable: bool
  searchable: bool
  reason: str | None

PathCheck:
  resource: str
  path: list[dict]
  authorized: bool
  blocked_at: int | None
  reason: str | None
```

### 16.4 日志规范

- 位置：`services/permission_boundary.py`、`services/errors.py`；
- 级别：INFO（授权成功）、WARNING（授权拒绝）、ERROR（权限异常）；
- 字段：`request_id`、`user_id`、`resource`、`field_name`（适用时）、`path`（适用时）、`error_code`、`latency`；
- 禁止记录：原始 query、条件值、字段值、SQL、Record Rule 内容、令牌；
- 日志不作为权限判断输入，也不允许记录跨用户缓存键。

### 16.5 测试 fixture 规范

- 位置：`tests/fixtures/permissions/`；
- 格式：Python/ORM fixture；
- 内容：公司 A/B、多公司用户、普通用户、Portal 用户、管理员、字段权限、可访问/不可访问/中间段阻断的关系路径、权限变化场景；
- 隔离：每个测试套件使用唯一标记；
- 清理：测试结束检查 fixture 数量和跨测试残留；
- 不使用超级用户环境制造“普通用户已授权”的假证据。

### 16.6 性能预算与失败模式

默认预算（软闸门）：

- 单资源权限过滤：≤ 100 ms；
- 单字段权限检查：≤ 10 ms；
- 单关系路径校验：≤ 50 ms；
- 总权限过滤：≤ 500 ms。

失败模式：

| 场景 | 错误/行为 |
|---|---|
| 模型不可访问 | `RESOURCE_NOT_ACCESSIBLE`，不返回记录或计数 |
| Record Rule 阻断 | 记录不进入结果 |
| 字段不可读 | `FIELD_NOT_READABLE` 或字段排除，不返回字段值 |
| 关系路径不可访问 | `RELATION_PATH_BLOCKED`，路径拒绝 |
| 权限判断异常 | `PERMISSION_DENIED`，失败关闭 |
| 配置无效 | `CONFIGURATION_ERROR`，整体失败关闭 |
| 内部错误 | `INTERNAL_ERROR`，不暴露堆栈 |

### 16.7 验收场景

1. 用户 A 只能看到公司 A 授权记录；
2. 用户 B 只能看到公司 B 授权记录；
3. 多公司用户遵守当前公司上下文；
4. Portal 用户只看到 Portal 规则允许的记录；
5. 无权字段不参与搜索、不出现在结果；
6. Relation Path 中间段无权时路径被拒绝；
7. 权限变化后新请求反映新权限；
8. 权限异常不返回猜测数据；
9. 用户 A 结果不会被用户 B 复用；
10. Published 配置引用无权模型/字段时按本 CC 规则排除或失败关闭。

### 16.8 浏览器 HVR 场景

1. 用户 A 登录搜索，仅观察公司 A 结果；
2. 用户 B 登录搜索，仅观察公司 B 结果；
3. 移除用户 A 公司权限后重新搜索，结果变化；
4. 移除用户 A 字段权限后重新搜索，字段不出现；
5. Portal 用户登录，结果受 Portal 规则限制；
6. 权限异常时显示安全错误，不显示业务细节。
