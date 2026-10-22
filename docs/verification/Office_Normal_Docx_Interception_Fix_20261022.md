# Word 正常文件误拦截修复记录 — 2026-10-22

## 结论

`TARGET.docx` 与 `晨阳项目+WMS+操作手册.docx` 均已通过当前用户上下文下的 Odoo Office 检查。两份文件也完成了本地候选写入及独立回读，`office_verify` 均返回 `PASS`，无警告。

此前的拒绝是支持范围过窄造成的，不是这两份文件损坏：第一份含标准图片、页眉页脚、自定义文档属性及目录域；第二份大于原 20 MiB 输入上限，但 ZIP 展开后仍在现有压缩展开及单部件资源上限内。

## 修改

- DOCX 安全部件白名单现在接受标准 `headerN.xml`、`footerN.xml`、`docProps/custom.xml` 和 `word/media/imageN.png/jpeg`。
- 只接受符合格式签名的 PNG/JPEG，验证图片关系指向包内受控媒体部件；外部关系仍然拒绝。
- 允许安全的 Word 目录/页码域（如 `TOC`、`PAGEREF`、`PAGE`）及书签作为只读结构保留；包含这些结构的段落不会成为 Mapping Plan 写入目标。
- 对内嵌 DrawingML 图片执行结构白名单检查；文本框、VML、OLE、宏、外链及未识别绘图仍拒绝。
- 上传与独立回读文件上限从 20 MiB 调为 32 MiB；ZIP 展开上限仍为 100 MiB，单部件上限仍为 20 MiB。
- `office_engine_odoo` manifest 版本更新为 `18.0.1.4.0`。

页眉、页脚、图片与自定义属性会保留，但不会作为 M1 的映射目标暴露。该结果只覆盖此处列明并实际验证的部件，不代表任意 DOCX 高级对象都已支持。

## 验证

| 验证项 | 结果 |
|---|---|
| `office_core` 单元测试 | PASS，21 项 |
| `office_verify` 单元测试 | PASS，18 项 |
| `py_compile` 修改的 Python 文件 | PASS |
| `TARGET.docx` 本地结构检查 | PASS，259 个可见正文元素 |
| `TARGET.docx` 候选写入与独立回读 | PASS，1 个测试目标，0 个警告；页眉、页脚、图片及其他部件保留 |
| `晨阳项目+WMS+操作手册.docx` 本地结构检查 | PASS，76 个可见正文元素 |
| `晨阳项目+WMS+操作手册.docx` 候选写入与独立回读 | PASS，1 个测试目标，0 个警告；图片及其他部件保留 |
| Odoo `odoo18ce` / uid 2 的只读 `_inspect_chat_attachment` 复验 | PASS，两份附件均返回 `format=docx`，无数据库写入、无 Provider 调用 |
| Odoo addon 版本 | `18.0.1.4.0`，已安装升级 |

实际文件数据：

- `TARGET.docx`：462,827 字节；包内有 3 张 PNG、两个页眉、一个页脚及 `docProps/custom.xml`。
- `晨阳项目+WMS+操作手册.docx`：26,890,400 字节（约 25.64 MiB）；ZIP 展开约 30.33 MB，最大单个媒体部件约 5.45 MiB。

## 聊天 UI 验收限制

修复后的 Odoo 只读服务路径已验证，但本轮没有通过 `llm.thread.generate()` 重新发送附件。自动审查拒绝了该复放操作，因为它会创建持久聊天记录，且无法预先证明消息一定不会走到外部 Provider。未绕过该阻断。因此截图中的两条历史拒绝消息仍会保留；重新上传或重新发送文件后，才会看到新的接收结果。

## 后续范围记录

本次针对两份实际文件开放的结构需纳入 M1 技术基线的后续变更记录。不得把这次样本结果外推为所有 Word 文件兼容；含文本框、VML、外部链接、嵌入对象或未知 OOXML 部件的文件仍受控拒绝。
