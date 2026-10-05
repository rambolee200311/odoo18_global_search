# IHR-GS-WORKSPACE-QUERY-REFINEMENT

## 实施范围

CC-005 首轮实现已接入 Search Workspace：Raw Query 输入、Business Resource 筛选、日期/状态 Refinement、Query Understanding、结果 Snapshot 卡片和 CC-004 Preview 联动。

## 关键实现

- Workspace 只通过 `/wd_global_search/api/search` 调用 CC-002 Search Service。
- Raw Query 在服务端转换为可序列化条件，Refinement 独立维护并在提交时合并。
- 结果使用当前用户 Search Service 权限边界；点击结果调用 CC-004 只读 Preview API。
- Raw Query 变化重置 Refinement；Refinement 变化保留 Raw Query。
- 前端没有业务写 RPC。

## 验证

- Odoo 模块测试和 Python 编译通过。
- 内置浏览器完成 Raw Query、Resource、Date Refinement、Query Understanding 和 Preview 联动验证。

## 当前限制

真实 request timeout/active cancel 仍属于 CC-002 后续修订；多浏览器矩阵和完整 Portal HVR 尚未关闭。
