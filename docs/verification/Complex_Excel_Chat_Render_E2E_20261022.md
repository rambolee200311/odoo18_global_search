# Complex Excel Chat Render E2E — 2026-10-22

## 结论

**业务写入和聊天下载链路通过；原生 WPS/Excel 打开告警项未验证。** 生成文件在 Odoo 服务端独立回读通过，浏览器聊天回复显示可下载附件，下载后的文件结构和内容断言全部通过。

## 环境与记录

- Odoo 数据库：`odoo18ce`
- Odoo 用户：Mitchell Admin（uid `2`）
- 聊天线程：`llm.thread` id `48`
- 输入消息：`26785`
- 输入附件：`6596`，`complex_template.xlsx`
- Office 请求 UUID：`92dc911f-06eb-4db5-b74c-f563fd6773ae`
- 请求状态：`generated`
- 请求私有输出附件：`6597`
- 聊天回复：`26786`，角色 `assistant`
- 聊天下载附件：`6599`，`complex_template_filled.xlsx`
- 输入 SHA-256：`00bb6817092c67405dd35aa781baa2eeaa870c69120f8885c90c6b28a143f6ea`
- 输出 SHA-256：`a39282ff72abd80e0bc19504fc31d13d344619bc260ad44e31ac42567ef62b97`
- 聊天附件字节与请求私有输出 SHA-256 一致。

## 验收断言

| 验收项 | 结果 | 证据 |
|---|---|---|
| B1 为 `Acme Corporation` | PASS | 浏览器下载文件由 openpyxl 回读 |
| B2 为数值 `2000` | PASS | 浏览器下载文件由 openpyxl 回读 |
| C1 公式 `=B2*1.13` 保留 | PASS | 公式文本回读一致 |
| C2 公式 `=SUM(B2:B5)` 保留 | PASS | 公式文本回读一致 |
| `D1:F2` 合并保留 | PASS | 合并区域回读一致 |
| D1 红色底纹和粗体保留 | PASS | RGB `FFFF0000`，粗体为真；服务端启用 `require_styles=True` |
| `Hidden_Data` 隐藏状态保留 | PASS | sheet state 为 `hidden` |
| 隐藏表 A1 为 `Secret_Test_Value` | PASS | 值回读一致 |
| OOXML ZIP 文件健康 | PASS | `ZipFile.testzip()` 返回无坏条目；openpyxl 成功加载 |
| 聊天回复附件卡片可下载 | PASS | 内置浏览器点击下载，下载路径 `/Users/lijianqiang/Downloads/complex_template_filled.xlsx` |
| 聊天界面无本轮红色错误，浏览器 console error | PASS | 最新消息为生成成功文本和附件卡片；console error 列表为空 |
| Excel/WPS 原生“修复文件”警告 | NOT VERIFIED | 尝试通过 LaunchServices 启动 `/Applications/wpsoffice.app` 返回 OSStatus `-10827`；未能打开 WPS UI，因此不宣称此项通过 |

公式缓存没有被本样本计算或刷新：输入和输出的公式缓存均缺失，服务端报告 `cached_value_changed=false`。本次验收确认公式表达式完整，不代表公式计算结果已刷新。

## 修复记录

真实模板第一次运行时暴露空白目标单元格没有进入结构目录的问题，B1/B2 因而无法通过 Mapping Plan 校验。修复后，结构检查将已用行中间的空白格作为明确目标；公式格仍为只读。独立 `office_verify` 同步验证这些空白目标，并比较工作表可见性状态。

- [office_core engine](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/engine.py)
- [office_core tests](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/tests/test_office_core.py)
- [office_verify verifier](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_verify/verify.py)
- [office_verify tests](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_verify/tests/test_office_verify.py)
- [Odoo request wrapper](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_odoo/models/office_document_request.py)

聊天服务层的回读策略已设置为严格保留样式；公式、目标值、工作表及合并结构仍由独立校验器核对。

## 自动化验证

- `office_core`：20/20 tests PASS。
- `office_verify`：18/18 tests PASS。
- 真实 Odoo ORM 请求：`generated`，`checked_targets=2`，`checked_formulas=2`，回读状态 `PASS`，无警告。
- 浏览器下载文件重新读取：字段、公式、合并、样式、隐藏工作表与输入模板预期全部匹配。
- 浏览器截图：[complex-office-chat-hvr.jpg](/tmp/complex-office-chat-hvr.jpg)

## 额外处理

跨游标 Odoo 提交后，原 shell 环境缓存未立即看到请求输出记录；第一次构造的空聊天附件被发现并删除。随后在新 shell 环境中从已生成的私有输出重新读取字节，创建正确的线程附件并验证 SHA-256 与请求输出一致。聊天消息最终只关联正确的非空附件 `6599`。
