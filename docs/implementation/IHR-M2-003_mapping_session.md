# IHR-M2-003：Odoo 编排层基础与 Mapping Session

| 项目 | 值 |
|---|---|
| CC | `CC-M2-003` — FROZEN V1.0.0 |
| 状态 | CLOSED — 负责人于 2026-10-23 批准关闭 CC-M2-003 |
| Intent ID | `OFFICE-ENGINE-M2-003` |
| 上游代码基线 | `42f29a0c25c7af6871587eb07f1182c53bf84de4`（`origin/main`） |
| 分支 | `main` |
| Odoo / Python | Odoo 18.0 / Python 3.11.9 |
| 数据库 / 配置 | `odoo18ce` / `odoo.conf`；既有开发环境 |
| 最终模块版本 | `office_engine_m2` `18.0.2.0.0` |
| 实施代码提交 | `1e33a25148f29ef7de6dfa25de8a9be973384b8b`（`feat: add M2 mapping session orchestration`） |
| ATR | [`ATR-M2-003.md`](ATR-M2-003.md) |
| FR | [`FR-M2-003_mapping_session.md`](FR-M2-003_mapping_session.md) |

## 基线与裁定

负责人于 2026-10-23 批准冻结 CC-M2-003 并进入实施，状态机裁定为冻结 TDD V1.0.0 §8.2 的 8 个状态：`collecting`、`needs_clarification`、`awaiting_confirmation`、`editing`、`rendering`、`completed`、`failed`、`cancelled`。原始需求中的 6 个状态值不作为数据库枚举；未修改 SRS、TDD 或 Implementation Plan。

## 实施记录

| 日期 | 变更 / 验证 | 结果 |
|---|---|---|
| 2026-10-23 | 冻结 CC-M2-003 V1.0.0，关闭状态机、Thread/Message/Attachment 关系和 `error_code` 三个 OPEN 项。 | 完成 |
| 2026-10-23 | 扩展 `office_engine_m2`：新增 `office.mapping.session` 和 8 状态受控转换，含乐观 `revision`、受限错误类别和保护字段写入。 | 完成；详见 ATR CC-TEST-001/004/005 |
| 2026-10-23 | 新增 `mapping_service.py`：按当前用户环境校验 thread、source message、attachment 与目标业务记录；附件必须属于指定 Thread 的源消息；创建和查询仅返回最小元数据。 | 完成；详见 ATR CC-TEST-001–003/006 |
| 2026-10-23 | 增加 Session 普通用户 ACL 与 owner/company 全局记录规则；保持 Usage ACL 不变。 | 完成；详见 ATR CC-TEST-006/007 |
| 2026-10-23 | 执行 `odoo-bin -u office_engine_m2 --test-enable --test-tags /office_engine_m2 --stop-after-init`，使用既有 `odoo18ce`。 | 最终结果 `0 failed, 0 error(s) of 21 tests`；日志见 ATR |
| 2026-10-23 | Python 编译、XML 解析、权限静态扫描、模块状态与测试残留复核。 | 通过；详见 ATR |

## 变更范围

本次代码变化限于 `mymodules/office_engine_m2/`：

- 更新 Addon 名称、版本、摘要并加载 Session Record Rule。
- 新增 `models/office_mapping_session.py`。
- 新增 `services/mapping_service.py` 并导出内部服务。
- 新增 `security/office_mapping_session_rules.xml`，并增加 Session ACL。
- 新增 `tests/test_mapping_session.py` 并注册 Odoo TransactionCase。

没有修改 Odoo 官方代码、`mymodules/odoo-llm/`、其他 Addon、Provider 实现或 CC-M2-002 Usage 模型/权限。无新外部依赖、HTTP Controller 或用户界面。

## 验收状态

- CC-TEST-001–008：最终运行全部 PASS，证据见 [`ATR-M2-003.md`](ATR-M2-003.md)。
- IHR：本文记录代码与变更过程。
- ATR：自动化、静态检查、数据库状态及清理记录已归档。
- FR：[`FR-M2-003_mapping_session.md`](FR-M2-003_mapping_session.md)，基于本 IHR/ATR 对 Frozen CC 的义务作出 `SATISFIED` 评估。
- HVR：N/A；本 CC 没有用户可见 UI。
- Git：实现已提交至 `1e33a25148f29ef7de6dfa25de8a9be973384b8b`；关闭记录与 FR 随后归档。Implementation Plan 阶段 3 的 XML-RPC 安装/升级子门禁仍缺证据，CC 关闭不等于阶段 Gate 通过。

## 后续边界

本交付只完成 M2 阶段 3 的 Session 持久化和权限边界，不包括 AI/Retriever、Mapping Card/RPC、M1 渲染或 Skill。CC 关闭、FR 归档和后续 CC 启动仍需负责人分别批准。
