# IHR GS-SEARCH-PERMISSION-BOUNDARY

## 0. 文档治理

| 项 | 内容 |
|---|---|
| IHR 文档 | `IHR-GS-PERMISSION-BOUNDARY.md` |
| Intent ID | `GS-SEARCH-PERMISSION-BOUNDARY` |
| CC 引用 | [CC-003](../intent/CC-003_global_search_permission_boundary.md) v0.2 FROZEN |
| 前置 CC | CC-001 v1.0 FROZEN；CC-002 v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 实施开始 | 2026-10-04 22:32 |
| 最后更新 | 2026-10-05 18:26 |
| 当前状态 | In Progress |

## 1. 实施基线

| 项 | 状态 |
|---|---|
| CC3-CHANGE-001~007 | 当前仅完成第一切片：资源、字段、关系路径授权入口 |
| CC3-TEST-001~010 | 尚未形成完整 ATR；保持未完成 |
| 安全边界 | 未使用 `sudo()`、超级用户或请求体权限声明 |
| 官方代码 | 未修改 |
| Published 配置 | 消费 CC-001 `global_search_baseline` Version 1 |

## 2. 实施历史

### IHR-003-001

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 22:32 |
| 阶段 | Implementation |
| Action | 新增 `permission_boundary.py`，在 Resource Executor 查询前执行模型访问、字段访问和 Relation Path 检查；权限失败返回资源级失败关闭错误。 |
| Reason | 落实 CC3-CHANGE-001~005 的第一实施切片，不允许搜索服务绕过当前用户 ORM 权限。 |
| Files | `services/permission_boundary.py`、`services/executor.py`、`services/facade.py`、`services/errors.py` |
| Contract | CC3-CHANGE-001~005；CC3-TEST-001~005 |
| Result | Partial；模块测试、编译和当前登录用户正向产品搜索通过 |
| Deviation | 多用户、多公司、Portal、权限变化和跨用户缓存 fixture 尚未实现 |
| Follow-up | 建立权限 fixture，补齐集成测试和 HVR。 |

### IHR-003-002

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 22:32 |
| 阶段 | Verification slice |
| Action | 重启 Odoo 后通过当前浏览器会话调用 Search API，验证当前用户仍可消费 Published 配置并获得产品结果。 |
| Reason | 确认权限边界接入没有破坏 CC-002 已验证的正向 Search 行为。 |
| Evidence | HTTP 200；`SUCCESS`；`product.product` 结果；无错误 |
| Result | Tool-assisted PASS for current user regression only |
| Follow-up | 不将单用户观察扩展为完整权限验收；继续执行多用户和权限变化场景。 |

### IHR-003-003

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-05 16:58 |
| 阶段 | Permission fixture and control-plane boundary |
| Action | 增加权限边界类型和单元测试；修正 Published 配置与 database secret 的读取边界，使普通用户通过服务消费控制面元数据但不能直接读取配置模型。 |
| Reason | CC-001 明确普通用户不能直接读取配置模型，同时 CC-002 Search Service 必须消费 Published 配置；控制面访问不能阻塞业务数据权限判断。 |
| Files | `services/types.py`、`services/permission_boundary.py`、`services/provider.py`、`services/facade.py`、`services/executor.py`、`tests/test_permission_boundary.py` |
| Contract | CC3-CHANGE-001~005、CC3-TEST-001~005、CC3-PRESERVE-005 |
| Result | Module tests/compile passed; regular users 102/103 search product successfully; Portal users 7/101 received `RESOURCE_NOT_ACCESSIBLE`; direct config model reads remained denied |
| Deviation | 通过 `sudo()` 读取的仅是配置控制面和 database secret，不读取业务数据；该边界需在安全评审和测试中持续锁定。 |
| Follow-up | 补齐真实多公司/Portal fixture、字段权限、关系路径中间段和权限变化浏览器 HVR。 |

### IHR-003-004

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-05 18:26 |
| 阶段 | Multi-company and Portal verification |
| Action | 使用现有公司隔离数据和用户 102/103 执行 Search Service；使用 Portal 用户 7/101 验证不可访问资源的失败关闭。 |
| Reason | 覆盖 CC3-CHANGE-002、CC3-CHANGE-006 和 CC3-TEST-002/006 的真实 ORM 权限路径。 |
| Evidence | 公司 1：用户 102 的 `sale_order` 返回 10 条、`stock_picking` 返回 10 条；公司 2：用户 103 的 `sale_order` 返回 1 条、`stock_picking` 返回 0 条；Portal 用户对 `product` 返回 `RESOURCE_NOT_ACCESSIBLE`；普通用户直接读取配置模型仍被拒绝。 |
| Result | ORM/tool-assisted PASS for multi-company and Portal boundary |
| Deviation | 浏览器多用户人工切换、字段受限真实模型和 Relation Path 中间段仍未完成。 |
| Follow-up | 创建隔离字段/关系 fixture，追加 HVR-003 和正式 ATR。 |

## 3. 未完成项

- 多公司、多角色、Portal fixture；
- 字段不可读和关系中间段阻断测试；
- 权限变化后的新请求；
- 跨用户缓存隔离；
- active cancel/timeout 与权限边界交互；
- ATR、HVR 和最终 FR。
