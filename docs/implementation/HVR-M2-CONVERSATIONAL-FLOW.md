# HVR — M2 聊天式映射确认

| 项目 | 记录 |
|---|---|
| 状态 | **PARTIAL**：合成数据的聊天修改、预览及正式附件交付通过；真实 CMR / 真实 Provider 尚未验收 |
| 验证日期 | 2026-10-26 |
| 环境 | Odoo 18，数据库 `odoo18ce`，Codex 内置浏览器 |
| 合成流程 | `llm.thread_2499`，本地 Mock Provider，合成 Excel 和合成销售订单 |
| 真实模板观察 | `llm.thread_2500`；只记录无字段明文的概况 |
| 详细记录 | [ATR-M2-CONVERSATIONAL-UX-REDESIGN.md](ATR-M2-CONVERSATIONAL-UX-REDESIGN.md) |

## 验收记录

| 项目 | 结果 | 证据 |
|---|---|---|
| 映射表格和逐字段下拉框移除 | PASS | `office_mapping_card` JS/XML/SCSS 已删除，manifest 不再注册组件资产。 |
| 首次映射摘要和预览附件 | PASS（合成文件） | 内置浏览器展示 assistant 摘要及私有 `.xlsx` 预览附件卡片。 |
| 原生聊天输入框自然语言修订 | PASS（合成文件） | 浏览器发送 `把 B5 改为客户参考号`，assistant 显示修订摘要及新预览附件。 |
| 明确确认和正式输出附件 | PASS（合成文件） | 浏览器发送 `确认`，assistant 显示回读校验文本和正式 `.xlsx` 附件卡片。 |
| 文件选择器上传合成文件 | NOT RUN | 当前 CUA 原始 CDP 不支持设置文件选择器；初始合成用户消息/附件由 Odoo ORM 注入，未将其报告成 UI 文件上传。 |
| 真实 CMR 的自动映射/预览/生成 | PARTIAL | 浏览器中的真实 CMR 对话返回待澄清摘要（22 项），未生成预览或正式附件。使用的是本机 Mock Provider，不是 OpenAI 外网。 |

## 回归结果

- 对话入口、版本化预览和 M1 交付定向测试：12/12 PASS。
- `office_engine_m2` 全量测试：0 failed、0 error，78 项；1 项 HttpCase 因缺少 `websocket-client` 被跳过。
- 日志与逐项测试矩阵见 [ATR-M2-CONVERSATIONAL-UX-REDESIGN.md](ATR-M2-CONVERSATIONAL-UX-REDESIGN.md)。

## 截图证据

内置浏览器捕获了两个连续视图：首轮摘要/预览与自然语言修订/新预览；修订/确认与正式下载附件。截图图像已在本轮工具输出中展示，未另存到仓库。

## 结论

合成数据下，聊天原生输入、Proposal 增量更新、预览附件、确认和 M1 正式交付均通过。真实 CMR 仍有 22 个目标待澄清；真实 Provider 映射和真实模板的下载输出尚未验证，所以本 HVR 保持 `PARTIAL`。
