# IHR-GS-ERROR-PARTIAL-FAILURE

## 实施范围

CC-007 首轮实现统一 Search Service 的错误状态、空结果和部分成功聚合行为，并保持权限与配置错误失败关闭。

## 已实现

- 错误码增加 `CANCELLED` 和 `EMPTY`；
- 成功资源才进入 `counts.by_resource`；
- 错误按资源去重并稳定排序；
- 无错误且无结果返回 `EMPTY`；
- 取消中的请求显式产生 `CANCELLED` outcome；
- Workspace 显示部分成功和错误状态，不再把失败响应显示成普通空结果。

## 边界

自动重试退避和错误上报保留为 Implementation TODO；TV-06 真实错误注入和浏览器 HVR 已完成。

## 真实验证结果

- TV-06 ORM reference harness 十项语义检查全部通过；
- 部分失败保留成功结果，成功计数为 3；
- 超时保留已完成结果；
- 配置错误返回 0 结果并失败关闭；
- 浏览器验证 `EMPTY`、`RATE_LIMITED`、`PARTIAL_SUCCESS` 和
  `PERMISSION_OR_DELETED` 安全提示。

TV-06 报告明确标记生产 Search Service 尚未覆盖，因此本记录不宣称生产服务级 TV-06 已完全关闭。
