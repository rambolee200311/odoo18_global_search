# HVR-009 GS Internationalization and Timezone

## 状态

PARTIAL — 已完成当前用户语言和窄屏的内置浏览器验证；多用户语言/时区矩阵待继续。

## 已验证（2026-10-07）

1. Workspace 搜索 `Acme`，结果正常显示；
2. Query Understanding 显示 `name=Acme`；
3. Preview 显示只读 Form View；
4. Preview 字段标签按当前用户语言显示为中文：
   - `显示名称`
   - `参考`
   - `电子邮件`
   - `电话`
   - `公司`
5. 窄屏 viewport `390x844`：
   - layout width `351`；
   - layout scrollWidth `349`；
   - body scrollWidth `375`；
   - viewport width `390`；
   - 未出现横向溢出。
6. TV-06 十项时间/周起始/部分失败语义检查通过。

## 待验证

- 独立 en_US、zh_CN、多时区用户会话；
- 缺失翻译英文回退的浏览器验证；
- DateTime、货币、Selection 和 Many2one 的完整 Preview 矩阵；
- Firefox、Safari、Edge 浏览器验证。
