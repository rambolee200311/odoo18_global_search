# Global Search Technical Design Document

## 1. 文档信息

| 项 | 内容 |
|---|---|
| 文档 | TDD_global_search |
| 版本 | v0.1 |
| 状态 | Draft for Freeze Review（v0.3 评审问题已处理，待正式 Freeze） |
| 模块 | `wd_global_search` |
| 上游需求 | [SRS_global_search.md](../requirement/SRS_global_search.md) V1.4 FROZEN |
| 上游分析 | [RAR_global_search.md](../requirement/RAR_global_search.md) V0.2 |
| Spike 输入 | [SPIKE_global_search_report.md](../verification/SPIKE_global_search_report.md) |
| TV 输入 | [TV_global_search_report.md](../verification/TV_global_search_report.md) |
| 目标 | 定义进入 Implementation 前必须冻结的技术边界，不定义具体代码实现 |
| 评审状态 | 待评审、待 TDD Freeze |

### 1.1 评审输入

- TV-01：100k 性能基线通过，百万级待补测；
- TV-02：Exact/Prefix/Contains 索引策略已确定；
- TV-03：业务记录新鲜度通过，配置发布/停用未验证；
- TV-04：复杂权限 fixture 通过，Group Rule 组合风险需固化；
- TV-05：Chromium Preview 有条件通过；
- TV-06：语义 reference harness 通过，真实服务层待接入。

### 1.2 设计边界

- 业务数据读写只通过 Odoo ORM；
- 所有查询使用当前用户环境，不使用 `sudo()` 绕过权限；
- 不引入 Elasticsearch、OpenSearch、LLM 或向量检索；
- 本文不定义 DDD 聚合、实体和值对象；
- 本文不替代前端 TDD、具体测试用例或具体代码设计。

## 2. 架构概览

### 2.1 逻辑组件

```text
Browser / Search Workspace
          |
          v
Search HTTP/RPC Facade
          |
          v
Search Service
  ├─ Query Condition Resolver
  ├─ Configuration Snapshot Reader
  ├─ Permission Boundary
  ├─ Resource Executor
  ├─ Result Identity Deduplicator
  ├─ Counter Aggregator
  └─ Error/Partial Success Aggregator
          |
          +── Odoo ORM, current user Environment
          |
          +── PostgreSQL indexes selected by field usage

Configuration Models
  ├─ Draft Version
  ├─ Published Version
  ├─ Vocabulary / Resource / Field mappings
  └─ Audit events

Preview Container
  └─ current-user Form View/read path, read-only action boundary
```

### 2.2 请求生命周期

1. 接收 Raw Query、Parsed Conditions、Refinement Conditions 和分页参数；
2. 读取当前用户可见的已发布配置快照；
3. 合并条件，生成 Effective Conditions；
4. 对每个 Business Resource 建立当前用户 ORM 环境；
5. 对每个 Relation Path 和字段执行权限检查；
6. 运行资源查询，返回候选结果或模型级错误；
7. 以 Result Identity 去重；
8. 聚合分类计数和全部计数；
9. 汇总状态、错误和可展示提示；
10. 返回结果，不在请求路径写入业务记录。

### 2.3 关键设计决策

| 决策 | 结论 | 来源 |
|---|---|---|
| 搜索存储 | Odoo ORM + PostgreSQL 原生索引 | TV-01、TV-02 |
| 条件模型 | 结构化 Effective Conditions | BR-007、BR-008、BR-010 |
| 权限 | 每个资源、关系跳转和字段重新应用当前用户权限 | TV-04 |
| 配置 | Draft/Published 版本，读取只使用 Published | BR-014、BR-015 |
| Preview | 真实 Form View 读取，容器级只读 | TV-05、FR-SW-007 |
| 外部搜索引擎 | 不引入 | CON-005、TV-02 |

## 3. Search Service 设计

### 3.1 服务职责

Search Service 负责搜索语义编排、配置快照选择、权限边界、资源执行、结果聚合和错误协议。它不负责：

- 修改业务记录；
- 修改用户权限；
- 解释自然语言的全部细节；
- 提供 Form View 编辑能力；
- 绕过 Odoo Record Rule。

### 3.2 内部接口

逻辑接口：

```text
SearchResponse search(SearchRequest request, UserContext user_context)
```

`SearchRequest`：

```json
{
  "raw_query": "客户 本周 未完成",
  "parsed_conditions": [],
  "refinement_conditions": [],
  "resource_scope": [],
  "offset": 0,
  "limit": 50
}
```

`UserContext` 必须来自当前 Odoo 请求环境，至少包含：

```json
{
  "uid": 2,
  "company_id": 1,
  "company_ids": [1, 2],
  "lang": "zh_CN",
  "tz": "Asia/Shanghai"
}
```

UserContext 与服务入口的关系：

- HTTP/RPC Facade 是唯一允许读取 `request.env` 的层；
- Facade 创建不可由外部传入的 UserContext；
- Search Service 接受 Facade 创建的 UserContext 参数，不直接依赖 `request.env`，以便独立测试；
- Facade 不接受请求体中的 uid、公司、语言、时区或字段权限覆盖值。

获取规则：

- `uid`：`request.env.uid`；
- `company_id`：`request.env.company.id`；
- `company_ids`：`request.env.companies.ids`；
- `lang`：`request.env.user.lang`；
- `tz`：`request.env.user.tz`。

这些值在服务入口创建后只能向下传递，不能由请求体覆盖。
服务不得接受调用方自行声明的 uid、company_ids、groups 或可读字段作为可信权限输入。

### 3.3 Effective Conditions

每条条件至少包含：

```json
{
  "dimension": "state",
  "operator": "in",
  "values": ["draft", "sent"],
  "source": ["parsed", "refinement"],
  "business_resource": "sales_order",
  "timezone": null,
  "valid": true
}
```

约束：

- `dimension` 必须属于已发布配置；
- 同维度多值使用 OR；
- 不同维度使用 AND；
- 不支持否定和任意布尔表达式；
- 时间条件必须保存解析时使用的用户时区和语言；
- 无效解析条件不得进入 Effective Conditions；
- 不保存业务 ORM recordset，条件模型只保存可序列化值。

### 3.4 Parsed 与 Refinement 合并协议

1. 保留 Raw Query，不因 refinement 改写 Raw Query；
2. 过滤 `valid=false` 的 Parsed Conditions；
3. Refinement 同维度条件替换 Parsed 同维度条件；
4. 不同维度条件合并为 AND；
5. 同维度多个值合并为 OR；
6. 相同 `(dimension, operator, normalized_values, resource)` 去重；
7. 用户删除的 refinement 从 Effective Conditions 移除；
8. 输出稳定排序，供计数和缓存键使用。

路径 A（自然语言解析）和路径 B（Query Understanding/Refinement）必须只通过该协议进入执行器，不能各自实现一套过滤逻辑。

### 3.5 时间语义

- `today/week/month/year` 使用当前用户时区；
- DateTime 转日期先转换用户时区，再进行日期运算；
- 周起始使用当前用户语言配置的 `week_start`；
- 日期范围使用 `[start_inclusive, end_exclusive)`；
- 每个 Business Resource 使用其独立 Business Date 字段；
- 时间解析结果必须包含时区、语言和解析参考时间，便于审计和重现；
- 未配置 Business Date 时返回：

```json
{
  "scope": "resource",
  "resource": "<resource_key>",
  "code": "CONFIGURATION_ERROR",
  "message": "Business Date not configured for resource"
}
```

不得静默使用技术字段。

### 3.6 Result Identity 和计数

Result Identity：

```text
(business_resource_key, technical_model, record_id)
```

要求：

- 同一记录通过多个字段、关系或路径命中时只保留一个 Result Identity；
- 分类计数在去重后计算；
- “全部”计数对全局 Result Identity 集合计算；
- 分页不能改变计数；
- 结果合并必须保留 Business Resource、Technical Model、Record ID 和 Business Date；
- 同分排序使用稳定的最终键。

### 3.7 资源执行

每个 Business Resource 执行上下文包含：

```text
resource configuration
technical model
current user environment
field permission set
relation path policy
business date mapping
state mapping
snapshot mapping
resource timeout budget
```

资源执行器只能使用配置允许的字段和 operator。未知字段、未知模型、无效 domain 或配置版本错误必须转为配置错误。

### 3.8 超时与取消

- 总请求超时预算由 Performance Config 决定，默认 5 秒；
- 单资源超时预算由 Performance Config 决定，默认 3 秒；
- 单资源超时后，其他资源继续执行；
- 总请求超时后，返回已完成资源结果，状态为 `TIMEOUT`；
- `request_id` 由 Facade/服务端生成并在搜索响应和错误响应中返回；
- 客户端使用服务端返回的 `request_id` 发起取消；
- 取消接口为 `POST /wd_global_search/cancel`，请求体为 `{"request_id": "…"}`；
- 服务端必须校验 request_id 属于当前用户和当前会话；
- 取消只影响搜索任务和资源执行，不写入业务记录；
- 已完成结果仍按 Result Identity 去重后返回；
- 超时和取消必须释放执行上下文，不能留下未关闭的 ORM cursor 或线程任务。

### 3.9 并发控制

- 每用户并发搜索数由配置决定，默认 3；
- 资源执行允许并行，但并行度受全局 worker/队列上限约束；
- 每用户并发数小于等于 3 时立即执行；
- 超过 3 且用户队列未满时进入有界队列；
- 用户队列默认上限为 10，可由 Performance Config 调整；
- 队列等待超过总请求超时预算时返回 `RATE_LIMITED`；
- 队列已满时立即返回 `RATE_LIMITED`；
- 每用户和全局限制均由服务端执行，不依赖客户端；
- 并发控制不改变权限判断和计数语义。

### 3.10 分页

- `offset/limit` 应用于 Result Identity 去重和稳定排序之后；
- 分页不影响分类计数和“全部”计数；
- 分页不改变 Result Identity；
- 结果跨 Resource 统一分页；
- 大结果集优先使用带稳定排序键的 cursor；
- cursor 必须绑定配置版本、Effective Conditions、用户上下文摘要和排序版本，不能跨用户复用。

cursor 格式为服务端签名的 Base64 编码 JSON：

```json
{
  "config_version": "v17",
  "conditions_hash": "…",
  "user_context_hash": "…",
  "sort_version": "business-date-v1",
  "offset_key": ["2026-10-03", "sale.order", 5051],
  "issued_at": "2026-10-03T12:00:00Z",
  "expires_at": "2026-10-03T13:00:00Z"
}
```

签名使用服务端管理的 HMAC-SHA256 密钥。cursor 在以下情况失效：

- 配置版本变化；
- 用户上下文变化；
- 签名验证失败；
- 超过 1 小时；
- 排序版本变化。

### 3.11 配置快照

配置快照：

- 序列化为 JSON；
- 包含全部 Published Business Resource、模型映射、字段、Vocabulary、评分和性能配置；
- 不包含业务记录、ORM recordset 或用户私有结果；
- 快照大小上限默认 1 MB，可配置；
- 超过上限时发布失败，并产生 `CONFIGURATION_TOO_LARGE` 审计事件，提示管理员减少配置项或拆分配置域；
- 使用 canonical JSON 计算 checksum；
- 缓存键使用 `(config_domain, version_id, checksum)`；
- 快照解析失败时返回 `CONFIGURATION_ERROR`，不回退到旧的未知版本。

### 3.12 可观测性

每次请求的 observability metadata 至少包含：

- `request_id`；
- `config_version`；
- Resource；
- latency；
- result_count；
- error_code；
- completed/failed resources。

用户行为只记录 `raw_query_hash` 和 `conditions_hash`，不记录原始查询或业务字段值。两者分别计算为：

```text
raw_query_hash = SHA-256(raw_query + server_secret_salt)
conditions_hash = SHA-256(canonical_json(conditions) + server_secret_salt)
```

salt 是服务端密钥管理的秘密，不暴露给客户端；hash 不用于恢复原始输入。可观测性数据不包含业务记录内容，不参与搜索结果。

### 3.13 限流

- 每用户速率限制默认 60 次/分钟；
- 每请求最大结果数默认 200；
- 每请求最大字段数默认 50；
- 每请求最大 relation depth 和候选数由 Performance Config 限制；
- 超过限制返回 `RATE_LIMITED` 或 `CONFIGURATION_ERROR`，不得静默截断为成功；
- 限流由服务端执行，不能由客户端关闭。

### 3.14 国际化

- Vocabulary 按当前用户语言选择；
- Snapshot 标签按当前用户语言选择；
- 错误消息按当前用户语言选择；
- 日期格式按当前用户语言和时区；
- 缺失翻译回退到英文；
- 业务值不翻译，技术字段名不直接暴露给用户。

## 4. 配置模型设计

配置模型以“管理员可配置、发布后只读使用、版本可审计”为原则。下面是逻辑模型，不是代码类定义。

### 4.1 Business Resource 配置

| 属性 | 说明 | 约束 | SRS |
|---|---|---|---|
| key | 稳定业务资源键 | 唯一、不可随意复用 | CFG-001 |
| name | 用户可见名称 | 必填、可翻译 | CFG-001 |
| active | 是否参与搜索 | 发布版本内生效 | CFG-001 |
| technical_models | 模型映射 | 至少一个 | CFG-001 |
| composite | 是否复合资源 | 复合资源必须定义合并规则 | BR-003 |
| result_identity_scope | 去重范围 | 必须明确 | BR-011 |
| ranking_policy | 排序策略 | 必须可验证 | BR-003.1 |

### 4.2 复合资源合并规则

复合资源例如“订单”可映射多个 Technical Model。每个映射必须定义：

- 标题字段；
- Business Date 字段；
- State 映射；
- Snapshot 字段；
- Technical Model 优先级；
- 空日期策略；
- Result Identity 生成规则。

优先级必须在同一复合资源内唯一。冲突在发布前拒绝，不能在运行时任意覆盖。

### 4.3 Searchable Fields

逻辑字段配置：

| 属性 | 说明 |
|---|---|
| field_name | 技术字段名 |
| purpose | Identifier / Entity / Location / Text |
| operator_set | exact / prefix / contains 等允许操作 |
| searchable | 是否参与搜索 |
| readable_required | 是否要求当前用户字段可读 |
| index_strategy | btree / pattern_ops / gin_trgm / gist_trgm / none |
| weight | 评分权重引用 |
| relation_path | 关联字段路径 |

发布校验：

- 字段存在；
- 字段类型与用途兼容；
- 当前用户不可读字段不得进入执行字段集合；
- relation path 每跳模型存在且可读；
- operator 与 index strategy 兼容。

对应：CFG-002、CFG-011、FR-PM-005、CON-011。

### 4.4 Business Date 配置

每个 Resource/Technical Model 映射一个默认 Business Date 字段，可选：

- field_name；
- field_type；
- timezone_behavior；
- empty_date_policy；
- range_supported。

空日期默认不进入日期过滤结果，除非有明确的产品配置。对应 BR-009、BR-009.3、BR-009.4。

### 4.5 State、Snapshot 和 Vocabulary

**State 映射：**

```text
business_state -> technical_values[]
```

同一业务状态可映射多个技术值，映射必须无歧义且可校验。

**Snapshot：**

- 字段名；
- 用户标签；
- 格式化类型；
- 是否允许空值；
- 字段权限要求。

Snapshot 与 Form View 分离，不能把 Snapshot 读取当作 Form View 权限绕过。

**Vocabulary：**

- 业务词；
- Resource；
- 状态词；
- 时间词；
- 同义词；
- 语言；
- 版本。

Vocabulary 发布与 Resource 配置使用同一配置版本边界。

### 4.6 Entity 和评分配置

Entity 配置至少包含：

- 候选字段；
- relation path；
- 候选上限；
- 消歧阈值；
- 低于阈值的处理方式。

评分配置至少包含：

- 字段权重；
- 匹配类型权重；
- 结果阈值；
- 候选最大数量；
- 同分稳定排序规则。

具体评分公式属于后续测试设计和实现，不在本 TDD 冻结数学公式；但配置结构和上限必须冻结。对应 CFG-010、CFG-012、CFG-013。

### 4.7 性能配置

逻辑属性：

- 最大返回数；
- 每资源超时；
- 总请求超时；
- 最大 relation depth；
- 最大候选数；
- 最大计数扫描量；
- 并发/队列策略引用。

配置错误不得使用无界默认值。对应 CFG-011、NFR-001、FR-ER-002。

## 5. 配置版本与发布设计

### 5.1 生命周期

```text
DRAFT -> VALIDATING -> PUBLISHED
                     |
                     v
                 RETIRED

DRAFT -> REJECTED
```

- Draft 可编辑；
- Validating 执行完整结构和权限边界校验；
- Published 是唯一可被 Search Service 使用的版本；
- 同一配置域同时只能有一个 Published 版本；
- Published 不原地修改；
- Retired 不再被新请求选择，但保留审计。

对应 BR-014、BR-015、CFG-007。

### 5.2 发布校验

发布必须检查：

1. Resource key 唯一；
2. Technical Model 存在且可读；
3. 字段存在、类型兼容、权限策略完整；
4. Business Date 存在且类型正确；
5. State/Snapshot/Vocabulary 引用完整；
6. 复合资源优先级唯一；
7. 索引策略和 operator 兼容；
8. Relation Path 深度不超过限制；
9. 评分和候选上限有界；
10. 失败关闭策略完整。

任一项失败时：

- Draft 版本保留，状态设为 `REJECTED`；
- 失败原因和校验项写入审计事件；
- 当前 Published 版本不受影响；
- 管理员可修订该 Draft 后重新提交校验；
- REJECTED 版本不能被 Search Service 读取。

### 5.3 生效时间和缓存失效

发布事件产生：

```text
config_domain
version_id
published_at
published_by
checksum
```

Search Service 每次请求读取当前已发布版本标识。进程内缓存必须以 `(config_domain, version_id, checksum)` 校验，发现版本变化立即丢弃旧快照。

多 worker 不依赖进程重启。失效机制可使用 Odoo bus/通知或带版本检查的共享状态，但具体传输方式进入 Implementation 评审。

配置快照的 JSON 序列化和 checksum 约束见 §3.11。

### 5.4 审计

审计事件至少记录：

- 操作者；
- 时间；
- 配置域；
- 旧版本；
- 新版本；
- 校验结果；
- 失败原因；
- 发布/停用动作。

审计日志只追加，不进入普通搜索结果。配置校验失败、发布、停用和缓存失效均必须产生审计事件。

### 5.5 升级策略

- 配置模型使用 Odoo 标准模块升级机制；
- 索引迁移先在隔离数据库验证；
- 数据迁移使用 `mymodules/wd_global_search/migrations/` 下的版本化 migration script；
- migration 命名为 `<version>_<description>.py`；
- 版本和执行顺序遵循 Odoo 标准 migration 机制；
- 每个 migration 必须提供对应的 rollback 方案或明确的不可逆说明；
- 升级前备份，升级后执行结构、权限、索引和回滚验证；
- 新版本必须能读取旧版本配置，不能静默丢弃未知字段；
- 不兼容配置必须进入 `REJECTED` 并给出迁移提示；
- 索引迁移失败时恢复旧策略，不修改官方 addons。

## 6. 权限边界设计

### 6.1 当前用户原则

Search Service 从 Odoo 请求环境取得当前用户，所有 Resource Executor 使用该环境或等价的 `with_user()` 环境。禁止：

- `sudo()`；
- 使用管理员环境代替当前用户；
- 先管理员搜索再在结果层“猜测过滤”；
- 从客户端接受权限范围；
- 用缓存共享不同用户的未过滤结果。

本项目不把 `sudo()` 作为搜索权限例外。配置读取通过配置管理员/普通用户 ACL 控制，业务数据读取始终使用当前用户环境；审计和可观测性写入通过专用模型 ACL 或独立基础设施完成，不得借此读取或写入业务数据。任何需要提升权限的外围机制必须单独评审，不能由 Search Service 调用。

### 6.2 过滤层次

权限过滤在以下每一层执行：

1. Resource 模型读取权限；
2. Resource Record Rule；
3. 每个 Relation Path 跳转模型的读取权限和 Record Rule；
4. 每个 Searchable Field 的字段访问权限；
5. Preview Form View 和 Snapshot 字段读取；
6. 计数和分类聚合；
7. 错误和提示内容。

无权关联记录不能贡献结果、数量、标题或错误细节。

### 6.3 硬安全边界

公司、字段值、时间和配置生成的硬限制必须形成单一明确的 AND 边界，不能假设同组 Group Rule 自动 AND。配置生成器必须：

- 区分 Global Rule 与 Group Rule；
- 验证最终可见集合；
- 对阻断 fixture 做回归检查；
- 在权限模型异常时失败关闭。

### 6.4 字段权限

字段集合建立顺序：

1. 配置字段集合；
2. 当前用户 `fields_get`/字段权限过滤；
3. 类型、operator 和 relation path 校验；
4. 执行搜索；
5. 输出 Snapshot 再次过滤。

字段不可读时，不参与搜索，也不出现在计数解释或 Preview。

### 6.5 失败关闭

权限异常统一返回：

```json
{
  "status": "FAILED",
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Some search data is unavailable"
  },
  "results": [],
  "count": 0
}
```

不得返回“可能命中”的数量、记录 ID 或字段值。

## 7. Preview 容器设计

### 7.1 加载

Preview 使用当前用户权限加载真实 Odoo Form View 和记录读取结果：

- `get_view` 使用当前用户 Odoo 环境；
- `read` 使用当前用户 Odoo 环境；
- 字段权限由当前用户环境和字段 ACL/Record Rule 自动应用；
- Form View 的按钮节点在 Preview 容器层隐藏，不转化为可执行动作；
- 不复制或重写官方 Form View 作为业务编辑表单；
- 不调用 `create`、`write`、`unlink`、业务按钮或 Chatter 写方法。

字段权限验证：

- 单元测试使用受控权限矩阵验证无权字段不进入返回结构；
- ORM 集成测试使用真实用户、字段 ACL 和 Record Rule 验证无权字段不返回；
- Form View 声明了用户无权字段时，Preview 从实际可读字段集合中排除该字段；
- Preview 加载后权限发生变化时，下一次读取重新检查权限；
- 字段权限变化导致读取失败时返回 `PERMISSION_OR_DELETED`。

### 7.2 只读动作边界

Preview 必须同时在容器和客户端动作层阻断：

| 能力 | 策略 |
|---|---|
| Edit | 不渲染编辑入口 |
| Save | 不渲染保存入口，拦截保存快捷键 |
| Delete | 不渲染删除入口 |
| Business Button | 不暴露可执行按钮 |
| Chatter Post | 隐藏/禁用 |
| Attachment Upload | 隐藏/禁用 |
| Activity Action | 隐藏/禁用 |
| RPC 写操作 | 服务端不提供 Preview 写 API |

客户端隐藏不是唯一安全边界；服务端 Preview API 不接受写操作。

### 7.3 安全状态

记录不存在、记录权限变化、字段权限变化统一显示：

```text
PERMISSION_OR_DELETED
Record unavailable or permission changed
```

不向用户区分“删除”还是“权限变化”。

### 7.4 布局与兼容性

- 桌面：结果列表 + Preview 分栏；
- 窄屏：单栏，先结果后选中 Preview；
- 切换记录不重置 Raw Query 和 Refinement；
- 键盘操作不得触发写操作；
- 首轮目标浏览器：Chrome、Firefox、Safari 最新版；
- 每个浏览器都需验证控制台无错误和 RPC 无写请求。

## 8. 索引策略设计

### 8.1 默认映射

| 用途 | 默认索引 | 适用条件 |
|---|---|---|
| Exact Identifier | B-tree | 精确相等匹配 |
| Prefix Identifier | `text_pattern_ops` | 前缀匹配 |
| Selective Contains | GIN `gin_trgm_ops` | 选择性包含匹配 |
| Contains 特殊需求 | GiST `gist_trgm_ops` | 明确证明 GiST 价值 |
| 高选择率 | 允许 Seq Scan | PostgreSQL 成本估算占优 |

TV-02 数据支撑：B-tree Exact P95 0.033 ms、pattern_ops Prefix P95 0.036 ms、GIN Contains P95 9.226 ms、GiST Contains P95 8.805 ms。GiST 索引约 11.14 MiB，明显大于 GIN 约 3.30 MiB。

### 8.2 配置和校验

索引策略是字段用途配置的一部分，但发布校验必须确认：

- 数据类型支持该策略；
- PostgreSQL 扩展可用；
- operator 和索引一致；
- 生产迁移计划存在；
- 回滚策略存在；
- 高选择率不强制索引。

### 8.3 迁移/回滚

索引变更必须：

1. 在隔离数据库验证；
2. 记录旧索引和新索引；
3. 支持并行构建或维护窗口；
4. 验证查询计划和写入影响；
5. 失败时删除新索引并恢复旧策略；
6. 不修改 Odoo 官方 addons。

百万级和冷缓存的最终参数在补充 TV-01/TV-02 后冻结。

## 9. 错误与部分失败设计

### 9.1 状态

```text
SUCCESS
PARTIAL_SUCCESS
FAILED
TIMEOUT
```

### 9.2 返回结构

```json
{
  "status": "PARTIAL_SUCCESS",
  "results": [],
  "counts": {
    "all": 0,
    "by_resource": {}
  },
  "errors": [
    {
      "scope": "resource",
      "resource": "purchase_order",
      "code": "PERMISSION_DENIED",
      "message": "Some search data is unavailable",
      "retryable": false
    }
  ],
  "meta": {
    "request_id": "…",
    "config_version": "…",
    "completed_resources": [],
    "failed_resources": []
  }
}
```

### 9.3 处理规则

| 错误 | 是否允许部分结果 | 计数 | 提示 |
|---|---|---|---|
| 单资源读取异常 | 是，保留成功资源 | 只计成功资源 | 显示失败资源/通用原因 |
| 权限拒绝 | 按资源边界部分成功；若权限边界本身异常则失败关闭 | 不计无权资源 | 不泄露记录细节 |
| 超时 | 是，保留已完成资源 | 只计已完成资源 | `TIMEOUT` |
| 配置错误 | 否 | 0 | `CONFIGURATION_ERROR` |
| 协议/内部错误 | 否 | 0 | 通用错误和 request_id |

`retryable` 语义：

- `true`：客户端可在退避策略下重试；
- `false`：客户端不应自动重试，必须修复权限、配置或协议问题。

错误码规则：

| 错误码 | retryable |
|---|---|
| `TIMEOUT` | `true` |
| `RATE_LIMITED` | `true` |
| `PERMISSION_DENIED` | `false` |
| `CONFIGURATION_ERROR` | `false` |
| `CONFIGURATION_TOO_LARGE` | `false` |
| 协议/内部错误 | `false` |

部分失败的模型数必须可审计，但错误消息不得暴露无权字段、记录数量或 Record Rule 内容。

审计位置和内容：

- 记录到 observability metadata/审计事件；
- 包含 `request_id`、`config_version`、`failed_resources` 和 `error_codes`；
- 不包含业务记录数量、字段值、原始查询或 Record Rule 内容；
- 审计写入使用专用 ACL/基础设施，不允许通过 `sudo()` 扩大业务读取权限；
- 审计保留周期由配置决定。

## 10. 接口定义

### 10.1 内部 API

```text
SearchService.search(request, user_context) -> SearchResponse
ConditionMerger.merge(parsed, refinement, deleted) -> EffectiveConditions
ConfigurationProvider.published_snapshot(domain) -> ConfigSnapshot
PermissionBoundary.allowed_fields(model, user_context) -> FieldSet
ResourceExecutor.execute(resource, conditions, context) -> ResourceOutcome
ResultAggregator.merge(outcomes) -> SearchResponse
```

所有接口均为逻辑接口，具体类名、模块名和事务边界属于 Implementation。

### 10.2 前端 API

逻辑 HTTP/RPC：

```text
POST /wd_global_search/search
POST /wd_global_search/cancel
GET  /wd_global_search/preview
GET  /wd_global_search/preview/form
```

约束：

- Search API 返回结构化状态和错误；
- Search API 的 `request_id` 由服务端生成并返回；
- Cancel API 只接受当前用户拥有的 `request_id`；
- Preview API 只允许读取；
- `GET /wd_global_search/preview` 参数：
  - `model`：技术模型名，必填；
  - `record_id`：记录 ID，必填；
  - `view_id`：Form View ID，可选；
- `GET /wd_global_search/preview/form` 参数：
  - `model`：技术模型名，必填；
  - `view_id`：Form View ID，可选；
  - `view_type`：固定为 `form`；
- Preview API 不接受写 payload、字段写入值、按钮动作或 Chatter 动作；
- 当前用户由 Odoo session 派生；
- API 不返回无权记录的存在性信息。

### 10.3 配置 API

逻辑操作：

```text
draft_config()
validate_config(version_id)
publish_config(version_id)
retire_config(version_id)
get_published_version(domain)
```

发布和停用必须生成审计事件，并触发缓存版本变更。

## 11. 数据模型

### 11.1 配置模型

建议的逻辑模型。Implementation 阶段使用 Odoo 标准 `models.Model` 定义自定义配置模型，而不是把配置放入业务记录：

| 模型 | 关键字段 |
|---|---|
| Configuration Domain | key、name、active |
| Configuration Version | domain、version、state、checksum、published_at、published_by |
| Business Resource | version、key、name、composite、active |
| Resource Model Mapping | resource、model、priority、identity_policy |
| Searchable Field | mapping、field_name、purpose、operators、index_strategy、weight |
| Relation Path | resource、path、max_depth、permission_policy |
| Business Date Mapping | resource、model、field_name、empty_policy |
| State Mapping | resource、business_state、technical_values |
| Snapshot Field | resource、field_name、label、format |
| Vocabulary Entry | version、lang、term、dimension、value |
| Entity/Scoring Config | candidate_fields、threshold、limit、weights |
| Performance Config | result_limit、timeout、max_depth、candidate_limit |
| Audit Event | version、actor、action、timestamp、details |

配置模型权限：

- 配置管理员组可读写 Draft、执行校验、发布和停用；
- 普通用户不直接读取配置模型，也不需要配置模型 ACL；
- Search Service 通过受控内部接口读取 Published 配置；
- 普通用户只能通过 Search API 间接使用已发布配置；
- 普通用户不能修改配置版本或发布状态；
- Audit Event 只允许受控写入和管理员审计读取；
- 配置模型使用 ACL 和 Record Rule 控制，不以 `sudo()` 作为普通读取路径；
- 业务用户不能通过配置模型权限获得业务记录权限。

### 11.2 运行时状态

运行时状态不保存业务搜索结果作为长期事实。允许保存：

- request_id；
- config_version；
- start/end timestamps；
- resource outcome；
- error code；
- result count；
- latency；
- audit/observability metadata。

不得跨用户复用未经权限隔离的结果缓存。

## 12. 测试策略

### 12.1 单元测试

- Condition Merger：路径 A/B、冲突、去重、删除、无效解析；
- 时间解析：时区、语言周起始、跨日和 `[start,end)`；
- Result Identity：重复路径和复合资源；
- Error Aggregator：部分成功、超时、配置错误；
- Configuration Validator：字段、模型、优先级、索引和深度；
- Preview Action Policy：所有写操作均 false。

### 12.2 ORM 集成测试

- 当前用户 Record Rule；
- 每跳 relation path；
- 字段权限；
- 多公司、Portal、共享记录；
- 配置发布、停用、版本切换；
- 审计事件；
- Business Date 和 State 映射。

### 12.3 性能测试

- TV-01/TV-02 的 100k 回归；
- 百万级隔离环境补测；
- 冷/热缓存对照；
- 20 并发错误率和 P95/P99；
- Record Rule 额外开销；
- 索引迁移、回滚和写入影响。

### 12.4 权限测试

- 复用 TV-04 十类 fixture；
- 明确验证 Global Rule 与 Group Rule 组合；
- 结果、计数、Snapshot、错误提示均不得泄露；
- 权限运行时变化后使用新 Environment。

### 12.5 浏览器测试

- Chrome、Firefox、Safari；
- 桌面和窄屏；
- 三个 Form View；
- 只读、保存、按钮、Chatter、附件、活动；
- 删除/权限变化；
- 记录切换；
- 键盘和控制台/RPC；
- 失败状态和部分成功提示。

### 12.6 测试数据

- 使用固定随机种子生成可重复 fixture；
- 每个 TV/测试套件使用隔离数据库或唯一标记；
- 不依赖任意现有生产记录；
- 数据通过 Odoo ORM 创建、更新和清理；
- 覆盖多公司、多用户、多角色、Portal、共享记录和字段权限；
- 覆盖状态 OR、日期边界、时区、语言、空日期、部分失败和超时；
- 测试结束验证 fixture 数量为零、临时配置恢复、索引策略无残留。

## 13. 未解决问题

1. Search Service 的真实实现和事务/超时边界；
2. 配置发布的多 worker 缓存失效传输机制；
3. 百万级和冷缓存最终性能结论；
4. Preview 在隔离库、Firefox、Safari 和权限变化下的最终证据；
5. FR-ER-003 的最终产品文案；
6. Business Resource 配置管理员角色和审计保留周期；
7. 是否需要显式的配置回滚 UI；
8. 评分公式和候选上限的最终数值。

## 14. 与 SRS 的追溯矩阵

| SRS | TDD 章节 | 证据/状态 |
|---|---|---|
| BR-007 | §3.3、§3.4 | TV-06 harness 通过，服务层待接入 |
| BR-008 | §3.4 | TV-06/既有 GS-04 |
| BR-010 | §3.3、§3.4 | TV-06 OR 通过 |
| BR-011 | §3.6 | GS-04 去重，需服务回归 |
| BR-012 | §6 | TV-04 通过，需服务回归 |
| BR-013 | §3.6 | GS-04 计数去重 |
| FR-ER-002 | §9 | TV-01/TV-03/TV-06 输入 |
| FR-ER-003 | §9 | TV-06 harness 通过 |
| CFG-001~004 | §4 | 配置模型设计 |
| CFG-006、CFG-010 | §4.5、§4.6 | 配置模型设计 |
| CFG-007 | §5 | 版本与发布 |
| CFG-011 | §8 | TV-02 索引结论 |
| CFG-012、CFG-013 | §4.6、§11 | 配置模型设计 |
| BR-014、BR-015 | §5 | 生命周期和校验 |
| NFR-001 | §8、§12.3 | 100k 有条件通过，百万级待补 |
| NFR-002 | §5、§12.2 | 业务新鲜度通过，配置待补 |
| FR-PM-001~008 | §6 | TV-04 fixture 通过，服务待实现 |
| CON-008、CON-011 | §6.5 | 失败关闭和字段排除 |
| FR-SW-004 | §7.4 | TV-05 首轮浏览器通过 |
| FR-SW-007、CON-009 | §7 | TV-05 有条件通过 |

## 15. 与 TV 的追溯矩阵

| TV | 消费结论 | TDD 落点 | 后续动作 |
|---|---|---|---|
| TV-01 | 100k 性能基线、百万级待补 | §8、§12.3 | 补测百万级、冷缓存、权限开销 |
| TV-02 | 索引策略推荐 | §8 | 实现字段索引配置和迁移/回滚 |
| TV-03 | 业务新鲜度、配置未验证 | §5、§11 | 实现发布版本和缓存失效后重测 |
| TV-04 | 复杂权限通过、规则组合风险 | §6、§12.4 | 固化硬安全边界和权限回归 |
| TV-05 | Chromium Preview 有条件通过 | §7、§12.5 | 隔离库、多浏览器、权限变化回归 |
| TV-06 | 语义 harness 通过 | §3、§9、§12.1 | 接入真实服务和 UI 错误展示 |

## 16. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 基于 SRS V1.4、Spike 和 TV-01~06 生成 TDD Draft |
| v0.2 | 2026-10-03 | 根据评审补充 UserContext 获取、错误码、发布失败语义、权限/Preview 边界、API 参数、配置模型 ACL、超时并发、分页、快照、可观测性、限流、国际化、测试数据和升级策略 |
| v0.3 | 2026-10-03 | 根据 v0.2 评审补充 Facade/UserContext 边界、服务端 request_id、取消与队列策略、签名 cursor、快照上限、hash 规则、migration 路径、Preview 字段权限验证、retryable 规则和普通用户配置访问边界 |
