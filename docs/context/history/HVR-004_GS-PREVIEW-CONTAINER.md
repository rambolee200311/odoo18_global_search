# HVR-004 GS Preview Container

## 状态

PASS — 已在内置浏览器完成三种资源和窄屏布局的可见验证。

## 本次 Playwright 证据（2026-10-05 20:12）

- 桌面视口 `1280x900`：Contacts、Sales Orders、Transfers 均显示真实字段和 `READ ONLY · FORM VIEW`。
- Search Query 为不可编辑状态，Search 按钮为 disabled；该输入功能属于后续 Phase 5。
- Preview 区域没有 button 或 form；Ctrl/Cmd+S、submit 尝试均未产生 POST、PUT、PATCH 或 DELETE 请求。
- 窄屏视口 `390x844`：`.wd-layout` 为单栏，结果区右边框为 `0px`，Preview 仍可见。

## 场景

1. Contacts、Sales Orders、Transfers 均可打开只读 Preview（PASS）。
2. Preview 显示 `READ ONLY · FORM VIEW` 和字段值（PASS）。
3. Preview 不显示编辑、保存、删除、Chatter、附件和活动写入口（PASS）。
4. 删除或权限变化后显示 `PERMISSION_OR_DELETED` 安全状态（实现级 PASS）。
5. 窄屏布局降级为单栏（PASS，390px viewport）。
6. 浏览器网络记录中无 Preview 写请求（PASS，实现无写入口）。

Search Query 输入框保持只读是后续 Phase 5 约束，不作为 CC-004 的搜索功能验收项。
