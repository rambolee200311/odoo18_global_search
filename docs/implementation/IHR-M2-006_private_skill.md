# IHR-M2-006：私有导出 Skill 保存、匹配与复用

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-006-PRIVATE-SKILL` |
| CC | `CC-M2-006` — FROZEN V1.0.0 |
| Addon | `office_engine_m2`，版本 `18.0.7.0.0` |
| 环境 | 项目 `venv`、`odoo.conf`、既有数据库 `odoo18ce` |
| Odoo / Python | Odoo 18.0 / Python 3.11.9 |
| 执行日期 | 2026-10-23 |
| Provider / 网络 | 未调用真实 Provider 或外网；自动化用例以本地 mock / 合成记录执行 |
| 上游代码 | 沿用当前工作树；本次不提交、不推送 |

## 2. 实施摘要

实现 `office.export.skill` 私有映射规则模型、只读 ACL 与 owner/company Record Rule；新增受控保存和匹配服务，并将成功卡片的保存入口、命中 Skill 的选择与确认流程接入现有 Owl/RPC 卡片。

Skill 只保存模板 SHA-256、技术模型名和经重新验证的映射规则，不保存业务值、样例、目标记录 ID、Prompt、模板文件或输出文件。Skill 命中仅跳过 LLM 映射推理；仍按当前用户重新检查规则及字段授权、实时调用 Retriever 取值，并要求用户确认后走现有 M1 渲染和回读交付。

## 3. 变更记录

- 新增 `models/office_export_skill.py`：字段只读；普通用户不能直接创建、修改或删除 Skill。模型创建仅接受服务层的受控上下文和精确字段集合，并拒绝包含业务值的规则结构。
- 新增 `security/office_export_skill_rules.xml` 和 ACL：Record Rule 限制 owner 与当前允许公司；普通用户仅有读取 ACL。
- 新增 `services/private_skill_service.py`：
  - `save_from_success()` 验证 Session 所有权、revision、完成状态、模板附件与线程/消息关系、M1 成功请求和输出附件、映射完整性后保存规则；重复保存具幂等行为。
  - `match_for_request()` 服务端计算模板指纹，按 owner/company/fingerprint/model/active 精确匹配；零匹配返回原 AI 路径，多个匹配要求选择，唯一匹配时重新授权取数并转待确认。
  - 命中时写入 `SKILL_MATCHED: <skill_id>` 日志。
- 扩展 `mapping_controller.py`：增加已认证的 Skill 上下文、保存、选择 RPC；Controller 和服务都基于当前 `request.env` 检查 Session 权限、owner、company 与 revision。
- 扩展 Owl 卡片：M1 交付成功后展示技能名称输入和“保存为技能”操作；命中时展示 Skill 名称、目标模型和本次目标摘要；用户仍须确认。
- 增加 `tests/test_private_skill.py`，覆盖保存门禁、隔离、精确匹配、无 LLM 调用、实时数据和 M1 引擎闭环。

## 4. 实际变更范围

- `mymodules/office_engine_m2/__manifest__.py`
- `mymodules/office_engine_m2/controllers/mapping_controller.py`
- `mymodules/office_engine_m2/models/__init__.py`
- `mymodules/office_engine_m2/models/office_export_skill.py`
- `mymodules/office_engine_m2/security/ir.model.access.csv`
- `mymodules/office_engine_m2/security/office_export_skill_rules.xml`
- `mymodules/office_engine_m2/services/__init__.py`
- `mymodules/office_engine_m2/services/private_skill_service.py`
- `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.js`
- `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.xml`
- `mymodules/office_engine_m2/tests/__init__.py`
- `mymodules/office_engine_m2/tests/test_private_skill.py`

未修改 Odoo 官方代码、其他 Addon、M1 `office_core` / `office_verify`、Provider 实现或依赖。

## 5. 配置与安全边界

为浏览器 HVR 临时在本地 Odoo 进程配置了只允许合成 `res.partner.name` 的数据字段基线，以验证 Skill 实时取数链路。验证后已停止该进程并按原 `odoo.conf` 环境重启 8091 服务；临时环境变量未写入配置文件。当前服务恢复默认拒绝数据外发/读取策略，实际生产或后续 AI 使用需由管理员通过正式部署配置批准安全字段基线。

HVR 使用合成伙伴和工作簿。为便于负责人从聊天页面复核，私有 Skill 和测试消息/附件仍留在既有开发库中；均归当前用户私有，未删除共享业务数据或直接操作 filestore。
