# ATR-M2-005-DYNAMIC-ROWS：动态列表映射自动化验收

| 项目 | 结果 |
|---|---|
| CC | `CC-M2-005` 动态列表映射 V1.0.0 |
| ATR 状态 | **PARTIAL（原生证据状态不变）；CC 处置：CONDITIONALLY CLOSED** |
| 环境 | 项目 `venv`、`odoo.conf`、既有数据库 `odoo18ce` |
| Odoo / Python | Odoo 18.0 / Python 3.11.9 |
| Provider | Mock；未发送真实业务数据或调用外网 |
| 日志 | 原定向：`/private/tmp/cc_m2_005_dynamic_rows_final.log`、`/private/tmp/cc_m2_005_dynamic_rows_render_engine_v3.log`；全量：`/private/tmp/cc_m2_005_dynamic_rows_final_all.log`；本轮最终定向回归：`/private/tmp/cc_m2_005_conditional_final.log` |

## 验收结果

| 验收项 | 状态 | 证据 |
|---|---|---|
| Owl 多行上下文 | PASS | 服务端测试返回 6 个稳定目标和 10 行循环摘要；当前聊天卡片展示 6 个独立下拉框。 |
| 下拉框状态独立 | PASS（浏览器） | 在内置浏览器把第一行从 `name` 改为 `phone` 后，其余五行值保持原样；未点击保存，未改变 Session 持久数据。 |
| AI 列表 Prompt 与 Retriever | PASS（Mock Provider + 真实 Odoo Retriever） | 定向 Odoo 测试验证 Prompt 包含服务端目标行、授权字段和两条明细；Retriever 对服务端关系 ID 逐条查询并保序。 |
| 5/20 不完整映射 | PASS（自动化） | 首次/修复响应均为 5/20 时，最多调用两次 Provider，15 项进入澄清，不调用 M1、不创建输出。 |
| 列表映射展开 | PASS | 桥接测试验证根字段和两条明细记录按关系顺序生成三个明确 M1 writes。 |
| 列表写入真实 Office 引擎 | PASS | `TestOfficeRenderBridge.test_list_rows_expand_to_explicit_m1_writes_in_relation_order` 使用真实 `office_core.render_candidate` 及独立 `office_verify.verify_output`；3 个目标回读通过，公式 `C1 = 1+1` 保留。 |
| 纯 Python Validator | PASS | `80 passed`；`office_mapping_verify` statement 与 branch coverage 均为 100%。 |
| 目标数据库 ORM 复核 | PASS | `odoo-bin shell -c odoo.conf -d odoo18ce` 只读确认 Addon `installed`、版本 `18.0.6.0.0`、`office.mapping.session` 已注册，既有 context/rules/revision 字段存在；未新增 Session 字段。 |
| 动态映射定向 Odoo 测试 | PASS | 28 tests，`0 failed, 0 error(s)`。 |
| 列表渲染桥接 Odoo 测试 | PASS | `TestOfficeRenderBridge` 7 tests，`0 failed, 0 error(s)`；其中列表测试真实调用纯 Python Office 引擎及独立回读。 |
| 全 Addon 回归 | FAIL（既有基线用例） | 53 项中 1 failure、0 error：`TestOfficeMappingSession.test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message` 在共享 `odoo18ce` 断言全表 Session 数为 0，实际有 4 条既有记录。该测试不在本次变更白名单内，未清除或改写用户/历史数据。全量日志：`/private/tmp/cc_m2_005_dynamic_rows_final_all.log`。 |
| 本轮最终定向 Odoo 回归 | PASS（限定测试范围） | 在当前实现代码上执行 AI 编排、真实 Office Core 集成和 Render Bridge 测试：`0 failed, 0 error(s) of 19 tests`。完整日志 `/private/tmp/cc_m2_005_conditional_final.log`。日志还记录既有未安装模块 `wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app` 的环境错误摘要；不属于本 CC 代码变更，测试进程退出码为 0。 |

## 未覆盖范围

- 未调用真实 `gpt-5.6-luna`；模型质量/真实 Token 延迟不属于本次动态映射实现证据。
- 浏览器验证使用既有合成 Session 卡片，证明多行 UI 和本地编辑隔离；未验证新上传到自动解析/建 Session 的全新产品入口，也未在该次 UI 操作中保存/确认/生成。
- 自动化证明明细映射生成的 writes 可进入真实 Office 引擎并通过回读；实际 M1 Odoo 请求模型附件交付仍以既有 M2-005 ATR/HVR 记录为准，不把本次纯 Python 引擎测试冒充为新的 Odoo 持久交付验证。
- 全 Addon 不能标记全绿，原因及基线测试失败必须在后续计划中单独处理。

## 结论

本次动态列表卡片、授权明细读取、有限目标展开及真实 `office_core` / `office_verify` 生成回读均通过。全 Addon 的共享开发库 Session 全表计数用例仍为 **FAIL**；不把失败改写为通过。负责人裁定该测试基建缺陷不阻塞 CC-M2-005 条件关闭，详见 `AUTHORIZATION_RECORDS.md` 的 `EXEMPTION-CC-M2-005-001`。原生 ATR 仍保持 **PARTIAL**。浏览器只验证未保存的独立行编辑，因此不宣称 UI 保存、确认和上传启动全部通过。

本轮提交前复核：变更 Python 文件 `py_compile` 通过；映射卡片 QWeb XML 解析通过；`office_mapping_verify` 为 80 passed，100% statement/branch coverage；Odoo 定向回归为 19 tests、0 failed、0 error(s)。运行环境中其他三个未安装 Addon 的 ERROR 摘要如上保留，不扩展为本 CC 的 PASS 证据。

## CC 条件关闭处置

负责人于 2026-10-23 明确批准 `CC-M2-005` **CONDITIONALLY CLOSED**。该行政处置接受上述全表计数测试失败不作为本 CC 关闭阻塞；原始 FAIL、局部 HVR 范围以及其他 PARTIAL 项均保留。后续单独修复测试基建，不在本次改写或扩大测试。
