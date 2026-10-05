# CC-004 Global Search Preview 容器

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-004 |
| 版本 | v0.2 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-PREVIEW-CONTAINER` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 4 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 将当前用户可访问的真实 Odoo Form View 包装为不可写、失败关闭的只读 Preview 容器 |
| 批准冻结 | 2026-10-05 20:20，用户批准完成 HVR 后冻结并提交 |

本 CC 只冻结 Phase 4 Preview 容器，不实现 Search Workspace 查询输入、Query Understanding、Refinement UI、前端搜索结果流程或索引性能。

## 1. 上游与范围

### 1.1 SRS / TDD 追溯

| 来源 | 相关章节 | 本 CC 落实 |
|---|---|---|
| SRS FR-PM-001~008 | 当前用户和字段权限 | Preview 读取遵守 CC-003 |
| SRS FR-ER-002~003 | 安全状态和错误协议 | 删除/失权统一安全失败 |
| SRS FR-SW-004 | Form Preview | 在范围内 |
| SRS FR-SW-005 | 打开完整记录 | 在范围内 |
| SRS FR-SW-007 | Form Preview 编辑能力 | 在范围内，Preview 明确禁止编辑 |
| SRS BR-013 | 结果打开和记录预览 | 当前记录加载 |
| SRS CON-009 | Preview 只读 | 在范围内 |
| SRS NFR-004 | 响应式窄屏降级 | 在范围内 |
| TDD §6 | 权限边界 | 不绕过 CC-003 |
| TDD §6.5 | 失败关闭 | 权限/删除/View 异常返回安全状态 |
| TDD §7.1~§7.5 | Form View、只读容器、按钮/Chatter/附件阻断 | 本 CC 核心 |
| TDD §10.3 | Preview API | 只读服务端入口 |
| TDD §12.5 | 浏览器测试 | HVR 验证 |
| TDD §3.14 | 国际化 | 标签、错误、日期和数字格式 |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- 当前用户 Form View 加载；
- 当前用户记录读取和字段过滤；
- 服务端只读 Preview API；
- 编辑、创建、保存、删除、复制、Chatter、附件、活动和按钮双层阻断；
- 记录删除或权限变化时返回 `PERMISSION_OR_DELETED`；
- 桌面分栏和窄屏单栏 Preview 布局；
- Preview 单元、集成、浏览器和只读写操作回归测试；
- 与 CC-003 的当前用户权限边界集成。

### 1.3 超出范围

- Search Query 输入框、Search Workspace、Refinement UI；
- Query Understanding、计数和搜索结果聚合；
- 新增业务模型、改变业务 ACL 或修改官方代码；
- PostgreSQL 索引、性能压测和外部搜索引擎；
- 业务数据写入、迁移和 `sudo()` 权限旁路。

## 2. 变更边界

### 2.1 允许

- `controllers/main.py` 的只读 Preview API；
- `static/src/` Preview 容器 JS/CSS；
- Preview 服务、字段序列化和错误状态；
- 当前用户 UI/ORM 集成测试、浏览器 HVR 和文档记录。

### 2.2 禁止

- 修改 `odoo/` 或官方 addons；
- Preview 中调用业务写入 RPC；
- 使用 `sudo()` 读取业务数据；
- 把隐藏按钮当成唯一安全边界；
- 将 readonly UI 解释为 Search Workspace 已完成；
- 在权限或记录状态不明确时返回业务字段值。

## 3. 必需行为变更

| ID | 当前缺口 | 期望行为 | 验证 |
|---|---|---|---|
| CC4-CHANGE-001 | Preview 记录入口未形成完整容器契约 | 当前用户可访问记录加载真实 Form View 字段 | CC4-TEST-001 |
| CC4-CHANGE-002 | UI 只读阻断与服务端写保护未统一 | 创建/编辑/保存/删除/复制/按钮均不可执行 | CC4-TEST-002 |
| CC4-CHANGE-003 | Chatter、附件和活动可能成为写入口 | Preview 隐藏或拒绝所有写相关入口 | CC4-TEST-003 |
| CC4-CHANGE-004 | 删除或失权状态缺少统一响应 | 返回 `PERMISSION_OR_DELETED`，不泄露记录细节 | CC4-TEST-004 |
| CC4-CHANGE-005 | 桌面/窄屏布局缺少验证 | 桌面分栏、375px 窄屏单栏可用 | CC4-TEST-005 |
| CC4-CHANGE-006 | Preview 与 CC-003 权限边界缺少回归证据 | 只显示当前用户授权字段和记录 | CC4-TEST-006 |

### 3.1 Preview 与 CC-003 权限边界交互

- Preview 通过 `PermissionBoundary.authorize_resource` 校验模型和记录访问；
- Preview 通过 `PermissionBoundary.filter_readable_fields` 过滤序列化字段；
- `authorize_resource` 返回 `PERMISSION_DENIED`、`RESOURCE_NOT_ACCESSIBLE` 或 `RELATION_PATH_BLOCKED` 时，Preview 返回 `PERMISSION_OR_DELETED`；
- `filter_readable_fields` 返回部分不可读字段时，仅序列化可读字段；
- 全部字段不可读时返回 `PERMISSION_OR_DELETED`；
- 任何权限异常、记录删除或 View 加载异常均失败关闭。

## 4. 既有行为保留

| ID | 行为 |
|---|---|
| CC4-PRESERVE-001 | CC-001 配置管理员菜单和普通用户配置模型隔离不变 |
| CC4-PRESERVE-002 | CC-002 Search/Cancel API 协议不被 Preview 改写 |
| CC4-PRESERVE-003 | CC-003 的当前用户 ORM 权限、字段过滤和失败关闭继续生效 |
| CC4-PRESERVE-004 | Preview 不产生业务写操作，不使用 `sudo()` 读取业务数据 |

## 5. 安全 / API 契约

| 接口 | 规则 |
|---|---|
| `GET /wd_global_search` | 只提供 Preview 容器页面，不提供写入口 |
| `GET /wd_global_search/api/preview` | 只读取当前用户可访问记录；异常返回 `PERMISSION_OR_DELETED` 或 `INVALID_REQUEST` |
| Form View | 使用当前用户环境加载，不信任请求体用户/公司声明 |
| 写操作 | Preview 页面和服务端 API 均不得调用 create/write/unlink/copy |

安全要求：

- 当前用户来自 `request.env`；
- 字段先经 CC-003 过滤再序列化；
- 任何权限异常、删除记录或 View 加载失败默认失败关闭；
- 不记录原始字段值、令牌、SQL 或 Record Rule 内容；
- 不把前端隐藏按钮当作安全控制。

Preview 成功响应：

```json
{
  "status": "SUCCESS",
  "model": "res.partner",
  "record_id": 42,
  "view_id": 126,
  "fields": [
    {"name": "name", "label": "显示名称", "value": "Acme Corporation", "type": "char", "readonly": true}
  ],
  "meta": {"request_id": "...", "config_version": "..."}
}
```

Preview 失败响应：

```json
{
  "status": "PERMISSION_OR_DELETED",
  "error": {"code": "PERMISSION_OR_DELETED", "message": "Record unavailable or permission changed"}
}
```

## 6. 测试契约

| ID | 测试内容 | 类型 | 预期结果 | 人工验证 |
|---|---|---|---|---|
| CC4-TEST-001 | 三个目标模型 Form View 加载 | ORM+浏览器 | 当前用户可访问记录显示只读字段 | 是 |
| CC4-TEST-002 | 写入口阻断 | 浏览器+RPC 监控 | 无 create/write/unlink/copy/按钮写 RPC | 是 |
| CC4-TEST-003 | Chatter/附件/活动阻断 | 浏览器 | 不显示或不能执行写相关入口 | 是 |
| CC4-TEST-004 | 删除/失权记录 | 集成+浏览器 | `PERMISSION_OR_DELETED`，不泄露业务数据 | 是 |
| CC4-TEST-005 | 桌面和 375px 窄屏 | 浏览器 | 分栏/单栏布局符合契约，无控制台错误 | 是 |
| CC4-TEST-006 | CC-003 权限回归 | 多用户 ORM+浏览器 | 只返回当前用户授权字段和记录 | 是 |
| CC4-TEST-007 | Search/Config 回归 | 模块+浏览器 | CC-001/CC-002 既有行为不回归 | 是 |
| CC4-TEST-008 | 记录切换 | 浏览器 | Preview 更新，Raw Query 和 Refinement 状态保持 | 是 |

写操作监控要求：

- 监听 ORM `create`、`write`、`unlink`、`copy`；
- 监听 `/web/dataset/call_kw` 写操作；
- 监听 `message_post`、`ir.attachment.create`、`mail.activity.create`；
- CC4-TEST-002/003 断言所有写调用次数为 0。

## 7. 停止条件 / 完成定义

停止条件：

1. 需要业务写入、`sudo()` 或官方代码修改：立即停止；
2. 需要 Search Workspace 或 Query UI：进入后续 Phase 5 CC；
3. 无法证明服务端只读：不得完成；
4. 记录删除或失权仍返回字段值：停止并修订 CC-003/CC-004；
5. 浏览器存在未知写 RPC：停止并修复。

完成定义：

1. CC4-CHANGE-001~006 全部实现并有 IHR；
2. CC4-TEST-001~007 全部执行并有 ATR；
3. 至少三种模型 Form View 完成浏览器 HVR；
4. 桌面和 375px 窄屏验证通过；
5. 写 RPC、Chatter、附件和活动入口均被阻断；
6. CC-003 权限回归通过；
7. 无官方代码修改、无业务数据 `sudo()`、无 Workspace 完成宣称。
8. Preview 加载时间 P95 ≤ 1 秒；该项为软闸门，作为 TV-01 输入。

## 8. 实施结构

```text
services/
  preview.py              # 当前用户只读 Preview 服务
  permission_boundary.py  # 消费 CC-003
controllers/main.py       # Preview 页面/API
static/src/js/preview.js  # 只读容器交互
static/src/css/preview.css
tests/test_preview.py
```

建议接口：

```python
def load_preview(env, model_name: str, record_id: int) -> PreviewResult: ...
def serialize_readonly_view(env, model_name: str, record_id: int) -> dict: ...
def reject_write_action(action: str) -> PreviewError: ...
```

类型定义：

```python
PreviewResult:
  status: str  # SUCCESS, PERMISSION_OR_DELETED, INVALID_REQUEST
  model: str
  record_id: int
  view_id: int | None
  fields: list[PreviewField]
  error: PreviewError | None

PreviewField:
  name: str
  label: str
  value: str
  type: str
  readonly: bool = True

PreviewError:
  code: str  # PERMISSION_OR_DELETED, INVALID_REQUEST, INTERNAL_ERROR
  message: str
```

### 8.1 字段序列化规范

- 字段顺序按 Form View 定义顺序；
- 支持 `char`、`text`、`integer`、`float`、`date`、`datetime`、`boolean`、`selection`、`many2one`、`monetary`；
- 字段标签按当前用户语言翻译；
- 日期/时间按当前用户时区格式化；
- selection 序列化为当前语言 label；
- many2one 序列化为 `display_name`；
- 空值显示为 `—`；
- 无权字段不序列化。

### 8.2 只读动作清单

以下动作必须在服务端和容器层阻断：

- Edit、Save、Delete、Duplicate、Archive、Unarchive；
- Chatter Post、附件上传/删除、活动创建/完成；
- 所有业务按钮、工作流动作和状态变更；
- Print、Export、Import、Share、Follow、Unfollow。

### 8.3 浏览器兼容性矩阵

| 浏览器 | 最新桌面 | 最新窄屏 |
|---|---|---|
| Chrome | 必须通过 | 必须通过 |
| Firefox | 必须通过 | 必须通过 |
| Safari | 必须通过 | 必须通过 |
| Edge | 必须通过 | 必须通过 |

### 8.4 安全状态、国际化和性能

安全状态：

- `SUCCESS`
- `PERMISSION_OR_DELETED`
- `INVALID_REQUEST`
- `VIEW_NOT_FOUND`
- `MODEL_NOT_FOUND`
- `INTERNAL_ERROR`

国际化：

- 标签、错误、日期、数字和货币按当前用户语言/时区；
- 缺失翻译回退英文；
- 不把原始字段值写入日志。

性能预算（软闸门）：

- Preview 加载 P95 ≤ 1 秒；
- 字段序列化 P95 ≤ 200 ms；
- 权限过滤 P95 ≤ 100 ms；
- Form View 加载 P95 ≤ 300 ms。

### 8.5 日志和 fixture 规范

日志位置：`services/preview.py`、`controllers/main.py`。记录级别和字段：

- INFO：成功；
- WARNING：权限/删除失败；
- ERROR：内部错误；
- `request_id`、`user_id`、`model`、`record_id`、`view_id`、`status`、`latency`。

禁止记录字段值、SQL、Record Rule 内容和令牌。

Fixture 位置：`tests/fixtures/preview/`，使用 Python/ORM 创建：

- 普通用户、Portal 用户、多公司用户；
- 可访问、不可访问、已删除记录；
- 可读、不可读字段；
- 标准和自定义 Form View；
- 每个套件使用唯一标记，测试结束检查无残留。

### 8.6 验收和 HVR 场景

验收场景：

1. 用户打开记录，Preview 显示真实 Form View；
2. Preview 无编辑、保存、删除按钮；
3. Chatter、附件和活动不可写；
4. 写 RPC 被拒绝且调用次数为 0；
5. 删除或失权记录返回 `PERMISSION_OR_DELETED`；
6. 切换记录时 Preview 更新，Raw Query/Refinement 保持；
7. 桌面和 375px 窄屏布局通过；
8. Chrome、Firefox、Safari 无控制台错误。

HVR 场景：

1. 人工打开 Preview 并确认只读；
2. 尝试编辑、保存、删除；
3. 尝试 Chatter、附件和活动操作；
4. 尝试业务按钮；
5. 检查控制台无错误；
6. 检查无写 RPC；
7. 切换至少两条记录；
8. 验证窄屏单栏布局。

当前状态：**CC-004 v0.2 DRAFT / Ready for Freeze**。
