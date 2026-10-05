# IHR-GS-PREVIEW-CONTAINER

## 实施范围

CC-004 Preview 容器已实现：Preview 服务复用 CC-003 权限边界，使用当前用户 ORM 读取 Form View 可访问记录，并对返回字段标记为只读。权限、删除或字段不可读时返回 `PERMISSION_OR_DELETED`。

## 关键实现

- `services/preview.py` 集中处理模型授权、字段过滤、Form View 加载和安全序列化。
- Preview API 不提供 create、write、unlink、copy 或 Chatter/附件/活动写入口。
- 前端拦截 submit 和保存快捷键，并在窄屏下降级为单栏布局。
- Preview 响应使用 `SUCCESS`、`PERMISSION_OR_DELETED` 和 `INVALID_REQUEST` 状态。

## 验证

- Python `compileall` 通过。
- Odoo `--test-enable --stop-after-init` 通过。
- `git diff --check` 通过。
- 内置浏览器已加载 Preview 页面；资源按钮和只读页面继续用于 HVR。

## 当前限制

Search Query 输入、结果聚合和 Workspace 查询流程属于后续 Phase，不在 CC-004 范围内。
