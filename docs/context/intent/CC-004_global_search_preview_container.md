# CC-004 Global Search Preview 容器

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-004 |
| 版本 | v0.1 DRAFT |
| 状态 | Draft，待评审和冻结 |
| Intent ID | `GS-SEARCH-PREVIEW-CONTAINER` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 4 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 将当前用户可访问的真实 Odoo Form View 包装为不可写、失败关闭的只读 Preview 容器 |
| 批准冻结 | 待用户批准 |

本 CC 只冻结 Phase 4 Preview 容器，不实现 Search Workspace 查询输入、Query Understanding、Refinement UI、前端搜索结果流程或索引性能。

## 1. 上游与范围

### 1.1 SRS / TDD 追溯

| 来源 | 相关章节 | 本 CC 落实 |
|---|---|---|
| SRS FR-PM-001~008 | 当前用户和字段权限 | Preview 读取遵守 CC-003 |
| SRS FR-ER-002~003 | 安全状态和错误协议 | 删除/失权统一安全失败 |
| SRS BR-013 | 结果打开和记录预览 | 当前记录加载 |
| TDD §6 | 权限边界 | 不绕过 CC-003 |
| TDD §7.1~§7.5 | Form View、只读容器、按钮/Chatter/附件阻断 | 本 CC 核心 |
| TDD §10.3 | Preview API | 只读服务端入口 |

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

当前状态：**CC-004 DRAFT，待评审和冻结**。
