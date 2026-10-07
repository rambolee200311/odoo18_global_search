# IHR-GS-I18N-TIMEZONE

## 实施范围

CC-009 已冻结并进入实施。首轮实现提供服务端翻译英文回退、用户时区 DateTime
转换和语言周起始 helper，不从浏览器或请求体读取语言/时区。

## 已实现

- `services/i18n.py`：
  - 当前语言翻译；
  - `en_US` 回退；
  - UTC 到用户时区转换；
  - `en_US` 周日、其他受支持语言周一起始。
- `tests/test_i18n_timezone.py` 覆盖翻译回退、上海/UTC 时间和周起始。

## 边界

现有 Odoo View、Selection、Monetary 和完整浏览器多语言 HVR 仍需继续接线验证。

## 验证结果

- TV-06 时间、周起始和日期边界回归通过；
- 内置浏览器确认当前用户语言下 Preview 字段标签为中文；
- `390x844` 窄屏无横向溢出；
- 完整多用户、多时区和多浏览器矩阵仍未关闭。
