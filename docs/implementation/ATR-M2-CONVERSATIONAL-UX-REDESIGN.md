# ATR — M2 自然语言映射与版本化预览重构

| 项目 | 记录 |
|---|---|
| 关联基线 | SRS M2 V1.1.0 Frozen；TDD M2 V1.1.0 Frozen |
| 验收状态 | **自动化 PASS；浏览器 HVR PARTIAL** |
| 执行日期 | 2026-10-26 |
| 环境 | Odoo 18，项目 `venv`，`odoo.conf`，既有开发库 `odoo18ce` |
| Provider | 仅使用本机 OpenAI-compatible Mock Provider `M2 E2E Local Mock 20261026`；没有调用 OpenAI 外网 |
| 测试线程 | 合成流程 `llm.thread_2499`；真实 CMR 页面观察 `llm.thread_2500` |
| 日志 | `/private/tmp/office_engine_m2_m2ux_delivery_tests.log`；`/private/tmp/office_engine_m2_full_regression.log`；`/private/tmp/odoo_m2_conversation_e2e.log` |

## 1. 交付范围

- 冻结并记录自然语言对话式交互设计：废弃映射下拉 Owl 卡片，改用聊天输入框进行摘要、纠错和明确确认。
- Session 持久化 Proposal revision、模板指纹、数据指纹、预览附件及其对应 revision；增量更新和预览/确认均使用乐观锁。
- M1 预览与正式生成分开。预览失败保留合法 Proposal；确认时重新核验权限和源数据，数据变化时刷新预览并要求再次确认。
- 删除 `office_mapping_card` 的 JS、XML、SCSS 组件文件及其资产注册。
- 修复 M1 新游标提交的正式附件无法在原聊天事务快照中读取的问题：使用新游标校验 request/thread/owner/附件绑定后，在同一新快照创建 assistant 消息并返回 store payload。
- 修复跨游标最终消息把 `<p>` 原样显示的问题，正式交付的固定确认语句以安全纯文本显示。

## 2. 自动化验收

定向 Odoo TransactionCase：**12/12 通过**。

全量 `office_engine_m2` Addon 回归：**0 failed、0 error，78 项用例；日志统计 102 tests，191.90s，8049 queries**。一项旧 HttpCase 因当前环境未安装 `websocket-client` 被跳过；其余测试完成。完整日志见上表。

| 验收项 | 结果 | 断言摘要 |
|---|---|---|
| 首次请求 → Proposal → M1 预览 | PASS | Mock Provider 返回 Proposal；真实 `office_core` 写入合成 `.xlsx`，`office_verify` 回读通过；预览附件私有并绑定 Session/Proposal revision。 |
| 自然语言修改 B12 → 增量更新 → 新预览 | PASS | Prompt 含当前 Proposal 和本轮修改；未重读模板；未修改映射保留，Proposal revision 增加，预览写入新值。 |
| 再次修改 → 确认 → 正式附件 | PASS | 确认版本与当前 Proposal 绑定，M1 渲染桥接执行，生成结果进入 `completed` 并返回附件。 |
| 必填字段缺失 | PASS | 一次修复重试后仍未补全则进入澄清状态；解释缺项，不生成预览。 |
| 预览生成失败 | PASS | 保留已校验 Proposal 与版本；不留下可访问的半成品预览；返回错误信息。 |
| 旧 revision/并发覆盖 | PASS | 旧版本更新被拒绝；不会覆盖当前 Proposal 或预览。 |
| 权限撤销/预览后数据变化 | PASS | 权限失败不调用正式渲染；业务数据变化刷新预览并要求用户重新确认。 |

执行命令：

```sh
./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 \
  -u office_engine_m2 --test-enable \
  --test-tags /office_engine_m2:TestOfficeM2ChatEntryPoint,/office_engine_m2:TestOfficeM2ConversationalPreview,/office_engine_m2:TestOfficeM2RenderBridge \
  --stop-after-init --log-level=test

./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 \
  -u office_engine_m2 --test-enable --test-tags /office_engine_m2 \
  --stop-after-init --log-level=test
```

## 3. 浏览器人工模拟 HVR

内置浏览器中的合成聊天线程 `llm.thread_2499` 完成了自然语言纠错、更新预览、输入“确认”和正式下载附件展示。初始合成消息及 Excel 附件由 Odoo ORM 注入；随后纠错与确认由浏览器聊天输入框实际发送。聊天中可见两次预览附件卡片和最终 `.xlsx` 下载附件。

截图在本轮内置浏览器工具输出中捕获为两个连续视图：一个显示首次分析、初始预览、自然语言修改及更新预览；另一个显示确认消息和正式生成文件卡片。截图未另存为仓库文件。

限制：本次 CUA 文件选择能力未能完成对合成文件的系统文件选择器上传；因此不能把初始 ORM 注入表述成真实的 UI 文件选择上传。实际 CMR 对话线程 `llm.thread_2500` 在浏览器中显示 22 个未解决映射目标，系统停留在澄清回复、没有生成预览。这条真实模板流程没有使用真实 OpenAI Provider，也未进行实际生成验收。

| HVR 项 | 结果 | 说明 |
|---|---|---|
| 聊天摘要与附件卡片 | PASS（合成文件） | 浏览器可见首次摘要、预览附件和更新后的预览附件。 |
| 原生输入框多轮修改 | PASS（合成文件） | “把 B5 改为客户参考号”通过浏览器输入框发送，Proposal 和预览更新。 |
| 输入“确认”并交付正式文件 | PASS（合成文件） | 浏览器显示通过回读校验的文本和正式 `.xlsx` 附件卡片。 |
| 文件选择器上传合成文件 | NOT RUN | CUA 暴露的原始 CDP 不支持文件选择器设置；没有把服务端注入伪称为浏览器上传。 |
| 真实 CMR / 实际 Provider 六步流程 | PARTIAL | 页面检测到 22 个待澄清目标；没有实际 Provider 映射、预览或正式文件。 |

## 4. 安全与数据边界

- 本次 Provider 请求只发送到 `127.0.0.1:8909` 的本地 Mock 服务；未向 OpenAI 或其他第三方传输模板或业务数据。
- 自动化测试使用 Mock Provider；真实 M1 写读回读只使用合成工作簿和合成数据。
- 真实 CMR 页面只作结果观察；本报告不记录模板中的客户地址或字段样例。
- 没有修改官方 Odoo 或 Odoo-LLM 源码；没有安装或升级第三方依赖；没有创建隔离数据库。

## 5. 静态检查

- `py_compile`：修改的三个关键 Python 文件通过。
- `git diff --check`：通过。
- 当前为未提交工作树；本 ATR 不宣称代码已提交、推送或 M2 阶段关闭。

## 6. 结论

自然语言修改、版本锁、预览保留、数据变化重新确认和 M1 正式附件交付的自动化链路通过，合成数据浏览器交互也完成。实际 CMR 的 22 项澄清结果仍需要真实映射来源和真实文件输入闭环；因此整体 HVR 记为 **PARTIAL**，不能把本报告当成真实 Provider/真实 CMR 全流程 PASS。
