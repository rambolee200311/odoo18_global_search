# ATR-GS-P0-CUSTOM-DATE-RANGE

## 0. 执行元数据

| 项 | 内容 |
|---|---|
| 修复 | P0-01 自定义日期范围 |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 环境 | macOS；Odoo 18 CE；本地授权 Workspace |
| 执行日期 | 2026-10-14 |
| 执行者 | Copilot assistant；浏览器部分为 agent-assisted |

## 1. 自动化验证

| 验证项 | 结果 | 实际证明 |
|---|---|---|
| `test_request_boundary` | **16/16 PASS** | 接受合法 custom range；拒绝缺键、多余键、非法日期、相等/倒序边界、错误 dimension/operator 和 scalar/object 错配 |
| `test_service_core` | **35/35 PASS** | 合法范围产生 Business Date `>= start` 且 `< end` 的半开区间 domain；其它 Search Core 回归通过 |
| Python 编译 | **PASS** | request boundary 与 controller 文件编译成功 |
| JavaScript 语法 | **PASS** | `node --check static/src/js/preview.js` 成功 |
| `git diff --check` | **PASS** | 当前补丁无 whitespace errors |

执行方式使用 Odoo addon namespace unittest，不连接数据库：

```sh
./venv/bin/python -c "import odoo, unittest, sys; odoo.tools.config.parse_config(['-c', 'odoo.conf']); suite=unittest.defaultTestLoader.loadTestsFromName('odoo.addons.wd_global_search.tests.test_request_boundary'); result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())"
./venv/bin/python -c "import odoo, unittest, sys; odoo.tools.config.parse_config(['-c', 'odoo.conf']); suite=unittest.defaultTestLoader.loadTestsFromName('odoo.addons.wd_global_search.tests.test_service_core'); result=unittest.TextTestRunner(verbosity=1).run(suite); sys.exit(not result.wasSuccessful())"
```

## 2. Agent-assisted 浏览器验证

在现有授权 Search Workspace 的隔离端口运行页面，仅执行只读搜索：

| 场景 | 观察 | 结果 |
|---|---|---|
| 合法范围 `2026-06-01` 至 `2026-07-01` | 请求包含 `{"dimension":"date","value":{"start":"2026-06-01","end":"2026-07-01"},"operator":"between"}`；服务返回结果并显示 `Showing 1–10 of 3247` | PASS |
| 已应用范围后清空 From、保留 To | 显示 “Choose both dates for a custom range.”；Search API 请求数 0；此前日期 chip 与结果摘要不变 | PASS |
| To 不晚于 From | 显示 “The To date must be after the From date.”；Search API 请求数 0 | PASS |

浏览器观察证明了实际界面交互和请求形状；它不是人类签署的 HVR。第二个范围的实际过滤边界另由 `test_service_core` 断言。

## 3. 回归与限制

- 仅对本问题运行定向单元测试；未运行需直接连接 Odoo 数据库的完整模块套件。
- 未改变 Resource、权限、Count、分页、错误语义或现有预设日期行为。
- 人工 HVR 签署仍待执行；不得将 agent-assisted 记录当作用户验收。

## 4. 当前结论

**P0-01 定向自动化与浏览器验证通过。** 合法范围可请求并形成半开日期 domain；不完整和倒序范围不会发起搜索或清除已应用条件。Formal Human Verification 仍待人工签署。
