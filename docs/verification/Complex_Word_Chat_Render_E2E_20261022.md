# 复杂 Word 聊天生成与回读验证 — 2026-10-22

## 结论

**M1 当前开放的 DOCX 基础段落/表格能力通过；浏览器文件选择器上传与点击下载未验证。**

在 `odoo18ce`、线程 `llm.thread(48)`、用户 uid `2` 下，DOCX 附件经 Odoo 服务端处理，Mapping Plan 写入两个表格字段，`office.document.request` 状态为 `generated`，独立 `office_verify` 回读为 `PASS`。内置浏览器聊天页面显示输入文件卡片和生成文件卡片。

本轮输入附件通过当前用户权限下的 Odoo ORM 创建并关联到用户消息；点击聊天别针未弹出文件选择器。因此这次验证**不证明浏览器选择文件并上传的交互链路**。点击输出卡片的下载控件也没有在本机下载目录观察到文件；下载按钮行为标记为 **NOT VERIFIED**。生成文件从已校验的 Odoo 附件读取后进行本地独立检查和渲染。

## 环境与记录

- 数据库：`odoo18ce`
- Odoo 用户：Mitchell Admin，uid `2`
- 聊天线程：`llm.thread` id `48`
- 输入消息：`26791`
- 输入附件：`6602`，`complex_word_template.docx`
- 输入 SHA-256：`b20e67480efdae2f300b427d1876bcc9492c20a6f30008c21aa9e7a79707a378`
- Office 请求：UUID `49758bee-22aa-474a-908a-6386c522bb77`，请求记录 id `113`
- 请求状态：`generated`
- 私有输出附件：`6603`
- 聊天输出附件：`6604`，`complex_word_template_filled.docx`
- 助手消息：`26792`
- 输出 SHA-256：`0fe8129f809357a0882b8dfddb5858fe11262f1d23517a2843bee1b937b6abd8`

## 样本与映射

正向样本由 `python-docx` 生成，保留在 `/tmp/complex_word_template.docx`。它覆盖标题与副标题、多个段落样式、一个含多文本运行的非目标段落、两张带边框的表格、蓝色表头底纹及粗体表头。未包含 M1 当前拒绝的页眉/页脚、图片、文本框、超链接、书签、嵌套表格等结构。

Mapping Plan 写入：

- `docx:table:1:row:4:cell:2:p:1` → `Acme Corporation`
- `docx:table:2:row:1:cell:2:p:1` → `EUR 2,000`

未调用 LLM Provider；本轮映射由测试调用方显式提供，符合 M1 当前能力边界。

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| M1 能读取并列出可映射 DOCX 段落/表格元素 | PASS | `office_core.inspect_document` 返回 24 个元素；两个目标均可写 |
| 写入两个显式 Mapping Plan 目标 | PASS | 服务端请求 `generated`，`applied_writes`/回读目标数为 2 |
| 独立回读校验 | PASS | `office_verify.status=PASS`，`checked_targets=2`，无警告 |
| 客户值与金额值 | PASS | 回读分别为 `Acme Corporation`、`EUR 2,000` |
| 非目标文本与多运行段落 | PASS | 原段落文本及两个 run 均保留 |
| 表格结构和样式 | PASS | 两张表格、行列数、`Table Grid`、蓝色表头底纹 `1F4E78`、粗体均保留 |
| OOXML 文件健康 | PASS | ZIP `testzip()` 无损坏；`python-docx` 成功重新打开 |
| 页面版式渲染 | PASS | LibreOffice 渲染一页；输出未见裁切、溢出或表格错位 |
| 聊天消息显示输入与输出附件卡片 | PASS | 内置浏览器线程 48 页面可见 `complex_word_template.docx` 和 `complex_word_template_filled.docx` 卡片 |
| 浏览器别针选择文件并上传 | NOT VERIFIED | 点击别针未弹出文件选择器；本轮通过 uid 2 ORM 挂载输入附件 |
| 点击聊天输出附件下载并取得本地文件 | NOT VERIFIED | 下载控件点击后未在 Downloads 观察到文件；本地结构核验读取的是同 SHA 的 Odoo 输出附件字节 |
| 原生 Microsoft Word/WPS 打开检查 | NOT VERIFIED | 未启动原生 Word/WPS 应用 |

输出文件副本位于 `/tmp/complex_word_template_filled.docx`。页面渲染图位于 `/tmp/complex_word_template_filled_render/page-1.png`。

## 真实复杂模板边界

另对开发环境已有的 `/Users/lijianqiang/Downloads/TARGET.docx` 做了只读 `office_core.inspect_document` 检查。该文件被 M1 以 `OFFICE_UNSUPPORTED_FEATURE`、阶段 `container` 拒绝；包内含 `docProps/custom.xml`、两个页眉、一个页脚和三张图片。这些部件不在当前 DOCX 支持白名单内，因此不能把上述正向结果外推为任意复杂 Word 文件均可处理。

## 证据与限制

- Odoo 服务端 `office.document.request` 调用输出：`state=generated`、输出附件 id `6603`、回读 `PASS`。
- 独立验证脚本输出：目标值、非目标多运行段落、表格数量/维度、表格样式、表头底纹/粗体和 ZIP 健康检查全部通过。
- 可视渲染在当前检查环境使用英文样本，避免渲染环境缺少中文字体造成方框字；这不验证中文字体呈现效果。
- 本报告不代表浏览器文件选择器上传、浏览器下载、原生 Word/WPS 打开或 M1 未开放的高级 Word 部件已通过。
