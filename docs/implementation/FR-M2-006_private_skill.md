# FR-M2-006：私有导出 Skill 保存、匹配与复用

## 1. 追溯结论

| 来源要求 | 交付证据 | 状态 |
|---|---|---|
| CC-M2-006 私有 Skill 数据结构：用户/公司、模板指纹、目标模型、规则；不保存业务值或文件 | `office.export.skill` 字段约束、模型创建校验；`test_only_a_delivered_completed_session_creates_a_value_free_skill` | SATISFIED |
| 仅已成功完成并交付的 Session 可保存 | `save_from_success()` 校验 Session、revision、源附件关系、M1 generated 请求与输出附件；`test_uncompleted_session_cannot_save_a_skill`、`test_failure_or_missing_output_request_cannot_be_saved` | SATISFIED |
| 用户 A 的 Skill 对用户 B 不可读/不可用 | owner/company Record Rule、只读 ACL；`test_owner_and_company_record_rule_hides_another_users_skill` | SATISFIED |
| 同一模板指纹与目标模型精确匹配；变更后不复用 | 服务端重算模板 SHA-256；`test_fingerprint_and_model_must_match_exactly` | SATISFIED |
| 命中 Skill 时不调用 LLM；仍实时读取并要求确认 | `match_for_request()`、Provider 调用计数测试、浏览器 HVR | SATISFIED |
| 目标值变化后输出使用新值 | `test_skill_hit_uses_latest_data_through_m1_engine` 和 HVR ORM 工作簿回读 | SATISFIED |
| Skill 保存与匹配的聊天卡片交互 | Owl/RPC 保存按钮、匹配目标摘要和确认状态；内置浏览器 HVR | SATISFIED |

## 2. 限制与未覆盖范围

- 当前服务默认拒绝业务字段数据策略；本次 HVR 的 `res.partner.name` 临时合成字段批准只用于本地验证，已恢复默认运行配置。部署环境须另行配置经批准的字段基线。
- 本实现使用模板文件 SHA-256 精确匹配，不推断不同二进制文件的结构等价性。
- 本次没有真实 OpenAI Provider 请求；命中零 Provider 调用由 Mock/计数器自动化断言证明。
- 全量 Addon 回归的一个前序历史 Session 全表计数断言失败已在 ATR 中登记；不影响本 CC 定向用例 PASS，但全量套件不能标记全绿。

## 3. 总体状态

CC-M2-006 的本范围功能与安全追溯项均有实现或测试证据。等待负责人审阅 ATR/HVR 后关闭 CC；本记录不代表 M2 整体阶段关闭。
