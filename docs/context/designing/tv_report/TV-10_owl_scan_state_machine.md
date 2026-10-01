# TV-10：OWL 扫描顺序状态机

## 验证结论

**可行。推荐使用 OWL `useState` 管理扫描状态，使用明确的状态转移方法，不把业务规则放在模板中。**

## 状态模型

建议状态：

```text
SCAN_LOCATION
SCAN_PACKAGE
SCAN_PRODUCT
SCAN_SERIAL
SCAN_LOT
INPUT_QUANTITY
READY_TO_FINISH
```

核心状态：

```javascript
this.state = useState({
    step: "SCAN_LOCATION",
    locationCode: "",
    packageCode: "",
    product: null,
    lotName: "",
    quantity: 1,
    lines: [],
    error: null,
});
```

每次扫描都应进入统一的 `handleScan(value)`，由当前状态分派到对应处理方法。非法输入直接设置错误状态，不推进状态机。

## 撤销

扫描历史应在成功提交明细后追加：

```javascript
this.state.lines.push(line);
this.state.history.push(line.id);
```

撤销只允许移除最近一条有效明细，并调用后端撤销业务动作；不能让前端单独删除数据库记录。

## 风险与 SRS 影响

- 前端状态机不能替代后端权限和业务校验；
- 页面刷新或重复提交需要后端幂等；
- 输入焦点切换应在状态变更后执行；
- UI 测试需要为扫描步骤和错误提示定义稳定 `data-testid`。

SRS 无需改变；TDD 应冻结状态枚举、非法转移和错误提示契约。

