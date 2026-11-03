# HVR — M2 通用 Office 与多轮对话垂直切片

| 项目 | 结果 |
|---|---|
| 日期 | 2026-10-29 |
| 状态 | 自动化与浏览器人工模拟通过；等待负责人业务验收 |
| 环境 | Odoo 18 CE，数据库 `odoo18ce`，本地 UI `http://127.0.0.1:8091` |
| Provider | 已配置的 OpenAI Provider，模型 `gpt-5.6-luna`；本次浏览器流程为真实 Provider 调用 |
| 模板 / 数据模型 | 通用两段 DOCX 联系人模板 / `res.partner` |
| Session / 方案 | Session `5171`，最终预览关联 Proposal revision `1` |

## 验收目标

使用不同于 CMR/销售订单的模板和 Odoo 数据模型，从原生聊天上传 Office 文件、由模型自主调用工具建立映射、生成预览，并下载回读文件确认实际内容。此次仅生成预览，不创建正式输出。

## 浏览器操作记录

1. 在 8091 的原生 LLM Chat 中上传 `generic_contact_profile.docx`，内容为两段占位文本：`Contact name: [value]` 与 `Email address: [value]`。
2. 输入指令：请从当前用户可访问的 Odoo 联系人记录读取 `M2 Generic Audit Contact 20261029`，第一段填写联系人名称，第二段填写邮箱地址；生成和验证预览，不生成正式文件。
3. 浏览器中实际观察到真实工具调用顺序：
   - `odoo_record_retriever` — `call_6gKNicsyOhTvUAE10PdmzdGb`，成功；
   - `office_prepare_context` — `call_ywM0r6dN2ppxZcXgrRfVoriO`，成功；
   - `office_save_mapping_preview` — `call_DFWC2KWBc174sIUs9UopL3oo`，成功。
4. 聊天流出现可下载的 `preview_document_generic_contact_profile.docx` 附件卡片。聊天回复明确标注这是预览，未生成正式文件。
5. 从浏览器点击附件下载，保存到 `/Users/lijianqiang/Downloads/preview_document_generic_contact_profile.docx`，再用 Python `python-docx` 回读：

```text
paragraphs = [
  'M2 Generic Audit Contact 20261029',
  'm2-generic-audit@example.invalid'
]
```

## 实际记录与结果

| 项目 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 上传与正文保留 | DOCX 附件和自然语言指令进入同一原生聊天 | 用户消息 `50372` 绑定源附件 `17647`；后续指令消息 `50374` 保持在同一 Thread `6306` | PASS |
| 模型理解及工具链 | Provider 根据指令选择检索、模板上下文与预览工具 | 浏览器显示上述三个成功 Tool Call；使用真实 `gpt-5.6-luna`，没有本地 Mock Provider | PASS |
| Odoo 数据权限读取 | 以当前 Odoo 用户权限检索联系人 | 检索到合成联系人名称与邮箱；会话绑定当前 Thread/用户，未通过 `sudo()` 读取 | PASS |
| 映射持久化 | 规则对应两段并与预览版本关联 | Session `5171`，状态 `confirmation_required`，revision `4`；规则为 `docx:p:1 <- name`、`docx:p:2 <- email`；预览 Proposal revision `1` | PASS |
| DOCX 预览 | 附件名和 MIME 正确，生成内容可读 | 附件 `17648`，名称 `preview_document_generic_contact_profile.docx`，MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document`，大小 20,204 bytes | PASS |
| 下载及内容回读 | 下载文件的内容与映射结果一致 | 浏览器下载成功；Python 回读的两个段落分别为联系人名称和邮箱 | PASS |
| 正式输出边界 | 仅预览，不提前归档正式文件 | Session 未处于 completed；聊天声明“未生成正式文件”；本次没有 Finalize | PASS |

浏览器证据：本地原生聊天 Thread `6306`，地址 `http://127.0.0.1:8091/odoo/action-631?debug=assets&active_id=llm.thread_6306`。聊天中可见工具调用、DOCX 预览卡片和映射摘要。源附件和预览附件 ID 分别为 `17647`、`17648`。下载文件位于上表路径。

## 核心实现文件

本工作树原本已有多项未提交改动；以下是与本次通用切片调用链和验证直接相关的实现位置，不表示工作树中所有改动均由本次任务产生：

- `mymodules/office_core/engine.py`、`mymodules/office_core/tests/test_office_core.py`：通用文件读写和重复区域/公式执行能力及回归用例。
- `mymodules/office_engine_m2/services/chat_entrypoint.py`、`models/llm_thread.py`、`models/office_mapping_tools.py`、`data/office_tools.xml`：原生 Thread 工具循环、模板上下文和映射预览工具注册。
- `mymodules/office_engine_m2/models/office_mapping_session.py`、`services/mapping_service.py`：会话绑定、Proposal 版本历史、恢复旧方案为新 revision。
- `mymodules/office_engine_m2/services/render_bridge.py`：按当前用户权限重新读取数据、调用 M1 并验证输出；DOCX 简单段落规则按文本值处理。
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`、`test_mapping_session.py`、`test_conversational_preview.py`：原生工具集成、Proposal revision 和预览链路的自动化覆盖。
- `mymodules/office_engine_odoo/models/office_document_request.py`、`models/llm_thread.py`：现有 M1 文档入口和附件消息扩展点。

## 自动化验证

- 定向 DOCX + `res.partner` 映射/渲染/readback TransactionCase：通过，日志 `/private/tmp/m2_docx_target_test.log`。
- `office_engine_m2` 全量升级及测试：`0 failed, 0 error(s) of 100 tests`；addon 统计 `office_engine_m2: 128 tests, 184.19s, 7960 queries`。日志 `/private/tmp/m2_generic_slice_final.log`。
- `git diff --check`：通过。
- 未调用真实外网文件服务；Provider 是浏览器验收中实际配置的 OpenAI API Provider。

## 异常与恢复

第一次浏览器提交在服务器仍运行旧 Python 进程时失败。Provider 返回 HTTP 400：`gpt-5.6-luna` 在 Chat Completions 工具调用下不接受非 `none` 的 `reasoning_effort`。部署进程重启加载本次代码后，后续真实浏览器调用成功。失败消息保留在 Thread 中作为运行证据，没有删除或隐藏。

## 适用范围与未验证事项

- 本次证明的是简单 DOCX 段落直接映射、`res.partner` 读取、真实原生工具调用、预览生成及下载回读；不是 DOCX 通用版式覆盖认证。
- Word 表格、复杂段落/样式、页眉页脚、嵌入对象、条件表达式和 DOCX 重复行未由本次人工场景验证。XLSX 的公式与动态重复行需参考其各自自动化测试和此前验证记录，不由本 HVR 扩大结论。
- 本次遵从指令只生成预览，故没有执行最终确认、正式文件归档或正式文件下载验收。
- 浏览器生成的联系人为本次合成测试记录；测试后已将其归档（`active=False`）。
- 首次上传时浏览器状态未加载附件，因此该轮没有附件；刷新后在消息 `50372` 中成功上传。另一次服务器旧进程导致的 Provider 400 已如上记录。
- 当前 Git 工作树包含大量本任务开始前已有的未提交改动。本次未暂存、提交、重置或清理这些改动；报告文件为新增交付物。

## 人工验收步骤

1. 在 8091 打开 Thread `6306`，确认工具调用和 `preview_document_generic_contact_profile.docx` 卡片可见。
2. 下载预览并打开，确认第一段是 `M2 Generic Audit Contact 20261029`、第二段是 `m2-generic-audit@example.invalid`。
3. 负责人确认 DOCX 预览格式和展示满足业务要求后，再单独发出正式生成确认；本次未代替负责人确认。
