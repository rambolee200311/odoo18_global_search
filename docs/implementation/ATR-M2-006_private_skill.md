# ATR-M2-006：私有导出 Skill 保存、匹配与复用

## 1. 验收摘要

| 项目 | 结果 |
|---|---|
| CC | `CC-M2-006` — FROZEN V1.0.0；等待负责人关闭 |
| Addon | `office_engine_m2` 18.0.7.0.0 |
| 环境 | Odoo 18.0 / Python 3.11.9 / 既有 `odoo18ce` |
| 定向测试 | **PASS：12 项，0 failed，0 error** |
| Addon 全量测试 | **1 failed / 0 error of 64**；失败是已知历史 Session 全表计数断言，不属于本 CC |
| 真实 Provider / 外网 | 未调用 |
| 最终定向日志 | `/private/tmp/cc_m2_006_test_targeted_final2.log` |
| 全量日志 | `/private/tmp/cc_m2_006_test_full.log` |
| 浏览器验证 | PASS；见 [HVR-M2-006](HVR-M2-006_private_skill.md) |

## 2. 测试执行

定向命令：

```bash
./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 \
  -u office_engine_m2 --test-enable \
  --test-tags /office_engine_m2:TestPrivateOfficeExportSkill \
  --stop-after-init --log-level=test \
  --logfile=/private/tmp/cc_m2_006_test_targeted_final2.log
```

日志结尾：`0 failed, 0 error(s) of 12 tests when loading database 'odoo18ce'`。命中分支实际输出 `SKILL_MATCHED: 62` 和 `SKILL_MATCHED: 65`，证明命中服务被执行。定向类 Odoo 模块统计为 14 个运行测试行为；测试结果汇总为 12 tests。

## 3. CC 验收矩阵

| 验收项 | 结果 | 自动化证据 |
|---|---|---|
| 未完成 Session 不能保存 Skill | PASS | `test_uncompleted_session_cannot_save_a_skill` |
| 仅已成功交付 M1 的 Session 可保存，持久内容不含样例值 | PASS | `test_only_a_delivered_completed_session_creates_a_value_free_skill` |
| 失败或缺少输出附件不能保存 | PASS | `test_failure_or_missing_output_request_cannot_be_saved` |
| 普通用户不能直接创建、写入或删除 Skill | PASS | `test_skill_model_denies_client_create_write_and_unlink` |
| 用户 A 的 Skill 对用户 B 隔离 | PASS | `test_owner_and_company_record_rule_hides_another_users_skill` |
| 只有模板 SHA-256 和模型精确匹配 | PASS | `test_fingerprint_and_model_must_match_exactly` |
| Skill 命中后 Provider 调用次数为 0，并保留确认步骤 | PASS | `test_matching_logs_skill_id_skips_provider_and_keeps_confirmation`；日志含 `SKILL_MATCHED` |
| 业务数据变化后使用最新值生成 | PASS | `test_skill_hit_uses_latest_data_through_m1_engine`：实际调用 M1 `office_core` 和 `office_verify`，校验输出值来自本次 Retriever 结果 |
| 多匹配要求用户选择；无效/停用 Skill 不命中 | PASS | `test_multiple_matches_are_returned_for_user_selection`、`test_inactive_or_invalid_skill_does_not_match` |
| 过期 revision 和非法名称拒绝 | PASS | `test_stale_revision_and_invalid_skill_name_are_rejected` |
| 完成卡片展示已保存 Skill 不依赖当前数据策略环境 | PASS | `test_completed_card_can_show_saved_skill_without_data_policy_environment` |

## 4. 全量回归的既有失败

全量命令：

```bash
./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 \
  -u office_engine_m2 --test-enable --test-tags /office_engine_m2 \
  --stop-after-init --log-level=test \
  --logfile=/private/tmp/cc_m2_006_test_full.log
```

结果为 `1 failed, 0 error(s) of 64 tests`。唯一失败是既有 `TestOfficeMappingSession.test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message` 把共享开发库全表 Session 数断言为 0；运行时实际存在 4 条历史 Session，导致 `AssertionError: 4 != 0`。这项历史测试基建问题在 CC-M2-005 交付记录中已明确记录为非阻塞技术债，本次未修改该前序测试、也未清理历史数据。不得把全量回归描述为全绿。

## 5. 静态与运行检查

- `py_compile`：新增/修改的模型、服务、Controller、测试通过。
- `node --check`：映射卡片 JS 通过。
- `lxml`：安全规则和卡片 XML 均可解析。
- `git diff --check`：通过。
- 8091 原 Odoo 服务已用项目 `venv` 和 `odoo.conf` 恢复运行；临时 HVR 数据字段环境变量未持久化。

## 6. 结论

本 CC 的 12 项定向自动化验收与浏览器 HVR 均通过。全量 Addon 仍保留一项前序共享数据库历史数据断言失败；此 ATR 如实记录该失败，不将其改写为 PASS。当前实现等待负责人最终评审和关闭。
