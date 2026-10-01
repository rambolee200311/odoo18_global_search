# TV-18：工作包状态机

## 验证结论

**可行。状态推进必须由后端业务动作控制，不能由前端直接写状态。**

## 状态

```text
draft → in_progress → done
   ↘             ↘
       cancel
```

推荐业务动作：

```text
action_start()
action_cancel()
action_complete()
```

`action_complete()` 必须验证：

- 所有有效盲盘单已审核；
- 所有有效处理单 Step 1 已完成；
- 所有有效处理单 Step 2 已完成；
- 没有未处理的有效货位；
- 工作包未被取消。

状态不能回退。Done 后不能添加新的盲盘单。

## 审计

状态变更应通过 chatter 或专用历史模型记录操作人、时间和原因。不能仅依赖当前状态字段。

## 对 SRS 的影响

SRS F0.4-F0.9 和 AC65-AC66 已足够；TDD 应冻结状态转移表和完成条件。

