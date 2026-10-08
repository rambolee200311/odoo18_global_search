# HVR-012 GS Dynamic Resource Selector and Counts

## 状态

PARTIAL — Chromium 场景通过，跨浏览器矩阵未完成。

## 验证环境

- URL：`http://127.0.0.1:8091/wd_global_search`
- 数据库：`odoo18ce`
- Published Configuration：`global_search_baseline`
- 浏览器：Chromium
- 日期：2026-10-08

## 已验证场景

1. 打开 Workspace，Resource Selector 自动显示 Published Configuration 中的：
   Warehouse、Storage Location、Product、Contact、Stock Transfer、Sales Order、
   Purchase Order。
2. 输入 `GS-CUSTOMER-001` 并提交。
3. Resource Count 显示：
   - Contact：`1`
   - Stock Transfer：`20`
   - Sales Order：`20`
   - 其他当前查询无匹配 Resource：`0`
4. 点击 Contact，按钮进入 pressed 状态，结果只保留 Contact。
5. 再点击 Sales Order，Contact 和 Sales Order 同时处于 pressed 状态，
   结果同时包含 Contact 与 Sales Order。
6. 点击 All，清除 Resource 选择并恢复全部授权 Resource 搜索。
7. Query Understanding 显示 `name=GS-CUSTOMER-001`。

## 证据

浏览器结果包括：

```text
GS-CUSTOMER-001  contact
GS-SO-0001       sale_order
GS-SO-0006       sale_order
GS-SO-0011       sale_order
...
```

Search API 返回：

```json
{
  "counts": {
    "all": 41,
    "by_resource": {
      "contact": 1,
      "stock_picking": 20,
      "sale_order": 20
    }
  }
}
```

## 未运行项目

- Firefox 最新版桌面/窄屏；
- Safari 最新版桌面/窄屏；
- Edge 最新版桌面/窄屏；
- 无权 Resource、多用户和多公司会话；
- Count P95、刷新 P95 和大结果集性能；
- 生产级失败注入和完整观测链路。

以上项目保持 `NOT RUN`，不以 Chromium 证据替代。
