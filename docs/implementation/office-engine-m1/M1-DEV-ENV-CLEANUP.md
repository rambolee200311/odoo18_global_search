# M1 开发环境残留清理记录

| 项目 | 结果 |
|---|---|
| 日期 | 2026-10-22 |
| Odoo 配置/数据库 | `odoo.conf` / `odoo18ce` |
| 清理方式 | `./venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce`，使用 ORM；未直接删除 filestore 文件 |
| shell 身份 | Odoo shell 默认 `uid=1`、`env.su=True`；脚本未调用 `sudo()` |
| 清理结果 | 4 条 M1 Office 请求、5 条合成聊天消息、9 个明确属于测试的附件已删除并提交 |
| 新 shell 复核 | Office 请求 0 条；目标测试附件 0 个；目标测试消息 0 条 |
| 用户上传文件 | CMR 模板 8 个、`TARGET.docx` 2 个、WMS 操作手册 1 个均仍存在，未触碰 |
| Odoo 服务 | 8091 端口 PID 10428 仍运行；保留给后续 M2 需求评审/开发环境使用 |

## 清理对象

| 类型 | ID | 清理前标识 |
|---|---:|---|
| `office.document.request` | 61 | 失败请求 UUID `47cff856-8511-4b49-969a-bd544ddd05b3` |
| `office.document.request` | 76 | 生成请求 UUID `915b7085-cd97-4c43-9778-de089c7eb7c2` |
| `office.document.request` | 112 | 生成请求 UUID `92dc911f-06eb-4db5-b74c-f563fd6773ae` |
| `office.document.request` | 113 | 生成请求 UUID `49758bee-22aa-474a-908a-6386c522bb77` |
| `mail.message` | 26427, 26785, 26786, 26791, 26792 | 本阶段生成的合成 XLSX/DOCX 测试消息 |
| `ir.attachment` | 6406, 6460, 6461, 6596, 6597, 6599, 6602, 6603, 6604 | `real_valid.xlsx`、复杂 XLSX/DOCX 样本及其生成结果 |

清理前脚本逐条核对请求 UUID、状态、附件 ID、附件名称和消息线程关联；所有前置条件通过后才执行 ORM `unlink()` 与 `env.cr.commit()`。在新 `odoo-bin shell` 会话内复核上述记录均不存在。

未删除线程 48、用户上传的 CMR/Word 文件、已归档的测试报告或本地验证证据。底层 filestore 的物理对象按 Odoo 原生 GC 生命周期处理；没有执行 `rm` 或直接磁盘清理。
