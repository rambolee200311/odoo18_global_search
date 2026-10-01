# TV-11：键盘模拟输入与焦点管理

## 验证结论

**可行。使用 OWL `useRef`、`onMounted`/`onPatched` 和输入框 `keydown` 处理扫描头输入。**

## 推荐方式

```javascript
this.inputRef = useRef("scannerInput");

onMounted(() => this.inputRef.el?.focus());

async onKeydown(ev) {
    if (ev.key !== "Enter") {
        return;
    }
    ev.preventDefault();
    await this.handleScan(ev.currentTarget.value);
    ev.currentTarget.value = "";
    this.inputRef.el?.focus();
}
```

输入框应设置：

```html
autocomplete="off"
autocorrect="off"
autocapitalize="off"
spellcheck="false"
```

不能依赖任意 `sleep()` 等待扫描结束。扫描头通常以键盘事件快速输入并以 Enter 结束，组件应以 Enter 作为提交边界。

## 手动输入与扫描输入

PDA v1.7 不要求区分二者。若未来需要区分，应采用输入时间窗口或设备配置，但不能将启发式判断作为业务正确性依据。

## 风险与 SRS 影响

- 页面失焦、弹窗和错误提示可能抢占输入；
- 快速扫描期间不能重复触发提交；
- `handleScan` 应增加忙碌锁，避免并发 RPC；
- 最终应在 Chromium/PDA 浏览器上执行真实键盘输入 E2E。

SRS 无需改变；TDD 应加入焦点保持、Enter 提交和重复触发防护。

