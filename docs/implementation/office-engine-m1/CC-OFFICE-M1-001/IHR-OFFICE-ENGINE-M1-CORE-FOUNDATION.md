<!-- 使用 Coding/IHR 模板；模板同步检查 PASS（2026-10-20） -->

# IHR — CC-OFFICE-M1-001

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `CC-OFFICE-M1-001` |
| CC | [CC-OFFICE-M1-001](../../../context/intent/CC-OFFICE-M1-001.md) `v1.0.0 Frozen` |
| 模块 | `mymodules/office_core`（纯 Python） |
| 工作类型 | 新功能 / 文件安全底座 |
| 实施负责人 | Codex Agent；人类批准人见 CC 冻结记录 |
| 开始 / 最后更新 | 2026-10-20 |
| 当前实施状态 | **Implementation Complete；用户已批准关闭 CC（2026-10-20）** |
| TDD 基线 | `TDD_office_engine_m1.md` V0.3 Frozen |
| SRS 基线 | `SRS_office_document_automation.md` V1.0.0 Frozen |
| Implementation Plan | `IMPLEMENTATION_PLAN_office_engine_m1.md` V0.2 Frozen |
| Git 基线 | Base commit `ae9e42e7e46394ed3d5c212b7779ee05c3882db9`；工作树有其他既存变更，未提交 |

## 2. Coding Contract 基线

范围、变更边界、保留项、测试合同和停止条件均只引用 CC §3–§13。实际实现限于 `CC-CHANGE-001` 至 `CC-CHANGE-007`；未修改 SRS、TDD、实施计划、TV 报告、Odoo Addon 或数据库。

## 3. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC-CHANGE 落实 | 7 / 7（依赖门禁、纯 Python 服务、容器/结构检查、Mapping 校验、候选写入、资源边界） |
| Preservation Impact | Potential Impact；由 ATR-RUN-011 验证输入不可变、公式只读、失败关闭及纯 Python 边界 |
| Deviation | None |
| Stop Condition | macOS 低地址空间预算不能由 `RLIMIT_AS` 强制；按 CC §12 #5 对该预算拒绝处理，记为开放环境限制 |
| Open Issues | 2 个 Major + 1 个 Informational；见 §7 |
| Revert | No |
| 当前状态 | Implementation Complete；CC 关闭评估见 FR-OFFICE-ENGINE-M1-001 |

## 4. 实施历史条目（仅追加）

### IHR-001

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Implementation |
| Action | 建立专属依赖清单，并在项目 `venv` 安装 CC 锁定版本；通过依赖一致性和合成 Office 读写门禁 |
| Reason | 落实 CC-CHANGE-007；CC 冻结后依赖验证是核心代码前置门禁 |
| Files / Components | `mymodules/office_core/requirements.txt`、项目 `venv` |
| Contract Reference | CC-CHANGE-007、CC-TEST-001、CC-DEC-002 |
| Upstream Reference | TDD V0.3 §9；CC §11.1 |
| Result | Completed |
| Deviation | None |
| Follow-up | 依赖及许可证据见 ATR §9 |

### IHR-002

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Implementation |
| Action | 新增无状态同步 Office 服务、严格 Mapping 校验、OOXML 安全预检、隔离候选渲染及稳定错误类型 |
| Reason | 落实 CC-CHANGE-001 至 CC-CHANGE-006 |
| Files / Components | `mymodules/office_core/*.py` |
| Contract Reference | CC-CHANGE-001—006；CC-PRESERVE-001—006 |
| Upstream Reference | TDD V0.3 §§2–4、§7；SRS AC-02—09 |
| Result | Completed |
| Deviation | None |
| Follow-up | 仅基础 OOXML 结构进入候选能力；无 Odoo/聊天/附件/回读交付实现 |

### IHR-003

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Fix |
| Action | 修正包内绝对关系 URI 的解析、显式空字符串的 OOXML 检查、损坏 ZIP 的 zlib 错误分类及 Office 最小测试夹具 |
| Reason | 自动化验证发现关系路径合法性、空字符串序列化和损坏容器边界问题 |
| Files / Components | `mymodules/office_core/security.py`、`engine.py`、`models.py`、`tests/test_office_core.py` |
| Contract Reference | CC-CHANGE-002、004、005、006；CC-PRESERVE-002、006 |
| Upstream Reference | TDD V0.3 §§3.3、7.1—7.3 |
| Result | Completed |
| Deviation | None |
| Follow-up | 历史失败及修复后重跑见 ATR §5；失败记录保留 |

### IHR-004

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Implementation |
| Action | 对指定真实 `销售管理模板.xlsx` 和 `TARGET.docx` 执行 fail-closed 检查；两者均因未启用的高级 OOXML 部件被拒绝，原文件只读未改 |
| Reason | 确认已提供真实样本不会被错误宣称为当前已支持格式 |
| Files / Components | 两个 `mymodules/odoo-llm/docs/tv_docs/` 样本；纯 Python 测试 |
| Contract Reference | CC-CHANGE-002、003、006；CC-PRESERVE-004 |
| Upstream Reference | TDD V0.3 §4；TV P0-A/P0-B 仍为 PARTIAL |
| Result | Completed |
| Deviation | None |
| Follow-up | 当前样本不获处理能力；须以后续经批准的能力/样本门禁开启 |

### IHR-005

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Closure evidence portability |
| Action | 将可复现自动化测试改为使用合成 OOXML 扩展结构，不再要求仓库包含用户提供的真实 Office 样本；真实样本此前在本机 ATR-RUN-010 对应测试中已按策略拒绝 |
| Reason | 用户提供的 Word 样本包含敏感招标内容，不适合推送到 GitHub；保护样本内容的同时保持从干净检出可运行的拒绝策略测试 |
| Files / Components | `mymodules/office_core/tests/test_office_core.py`；ATR-RUN-011 |
| Contract Reference | CC-TEST-002、CC-TEST-006、CC-PRESERVE-004 |
| Upstream Reference | TDD V0.3 §4；CC §3.1、§11 |
| Result | 合成 XLSX 扩展结构与 DOCX 文本框结构均验证为稳定拒绝；17 项测试通过 |
| Deviation | 无运行时产品代码变化；测试夹具从外部真实文件改为仓库内合成输入 |
| Follow-up | 原始用户 Office 样本及其渲染件不纳入提交；原 TV/P0 报告和本机测试事实不覆盖 |

## 5. 实际变更清单

| 文件 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `mymodules/office_core/requirements.txt` | Added | 三项直接依赖精确 pin | CC-CHANGE-007 |
| `mymodules/office_core/__init__.py` | Added | 独立纯 Python API 导出 | CC-CHANGE-001 |
| `mymodules/office_core/errors.py` | Added | 稳定且脱敏的错误类型 | CC-CHANGE-001/002/004/006 |
| `mymodules/office_core/models.py` | Added | 资源预算、元素、检查和候选结果数据类型 | CC-CHANGE-001/003/005/006 |
| `mymodules/office_core/security.py` | Added | 有界 ZIP/OLE/OOXML 检查、安全 XML、关系和活动结构拒绝 | CC-CHANGE-002/006 |
| `mymodules/office_core/engine.py` | Added | `.xlsx/.docx` 基础结构读取、Mapping 校验和候选渲染 | CC-CHANGE-003/004/005/006 |
| `mymodules/office_core/service.py` | Added | 隔离子进程、CPU/内存上限、墙钟超时与失败清理 | CC-CHANGE-001/006 |
| `mymodules/office_core/tests/` | Added | 安全、结构、映射、资源、合成高级结构拒绝及纯 Python 边界自动化测试；真实样本只在本机证据中使用 | CC-TEST-002—009 |
| `docs/implementation/office-engine-m1/CC-OFFICE-M1-001/` | Added | 本 IHR、ATR、HVR 和测试证据日志 | CC §4.1 |

## 6. 偏离与停止条件

**Deviation: None。**

触发并处置：在当前 macOS 运行时，`RLIMIT_AS` 无法设置低于 Python 进程地址空间基线的 4 GB 限值。服务返回稳定 `OFFICE_RESOURCE_LIMIT` 并拒绝处理，不绕过限制；该结果作为环境限制保留，生产内存预算未验证。没有修改冻结基线，也未用超大合成测试预算宣称生产容量已满足。

## 7. 遗留问题与后续

| ID | 问题 | 类别 | 级别 | 状态 | 责任方 |
|---|---|---|---|---|---|
| OI-001 | 当前 macOS 的小型 `max_memory_bytes` 无法由 `RLIMIT_AS` 强制，4 GB 请求安全拒绝；需要在目标部署平台验证资源限制实现 | 技术 / 环境 | Major | Open；生产能力不开放 | 后续平台/部署负责人 |
| OI-002 | 已提供真实 `.xlsx/.docx` 因扩展、图片或其他未准入部件被拒绝；当前能力只覆盖通过严格结构门禁的基础格式 | 格式 / TV | Major | Open；保持 fail-closed | 后续 CC 负责人 |
| OI-003 | 尚无用户端 Office UI；本 CC 是纯 Python 包，未装入 Odoo、没有上传/聊天/附件流程 | 范围 / 人工验收 | Informational | 按 CC 记录正式人工 UI 验收 N/A；用户已批准 CC 关闭，见 FR | 业务负责人 |

## 8. 移交摘要

已实现 CC-CHANGE-001—007，实施变更均在 CC 范围内。最新自动化结果由 ATR-RUN-011 记录；本机真实样本拒绝事实见 IHR-004/ATR-RUN-010，仓库自动化使用合成结构；浏览器观察与人工验证边界见 HVR。真实业务样本和 macOS 低内存预算保持拒绝；没有声明 Odoo UI、附件回传或 `office_verify` 已完成。CC 关闭评估见 FR；本 IHR 不作关闭判断。
