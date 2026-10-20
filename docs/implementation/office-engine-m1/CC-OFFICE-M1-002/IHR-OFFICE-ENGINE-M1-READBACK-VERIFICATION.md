<!-- 使用 Coding/IHR 模板；仅记录 CC-OFFICE-M1-002 的实施事实。 -->

# IHR — CC-OFFICE-M1-002

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-READBACK-VERIFICATION` |
| CC 引用 | [CC-OFFICE-M1-002](../../../context/intent/CC-OFFICE-M1-002.md)，`v1.0.0 Frozen` |
| 模块 | `mymodules/office_verify`（独立纯 Python 包） |
| 工作类型 | 新功能 / Office 文件完整性回读 |
| 实施负责人 | Codex Agent；实施授权人为业务负责人 |
| 开始 / 最后更新 | 2026-10-20 |
| 当前实施状态 | **Implementation Complete；尚未作 CC 关闭判定** |
| SRS / TDD / Plan | SRS V1.0.0 Frozen；TDD V0.3 Frozen；Implementation Plan V0.2 Frozen |
| Base Commit | `d3045d43609bd7b3898f803074457e27f138dca5` |
| 当前代码基线 | `WT-office_verify:694ae1ee324d9dcfb7e100ba72f35a3c8f0a89f1cbb97459c1cf5fd1abddabfd`（包内 `.py/.txt` 按相对路径排序，以 `path + NUL + byte_length + NUL + bytes` 计算；未提交工作树） |

## 2. Coding Contract 基线

只引用 [CC-OFFICE-M1-002](../../../../context/intent/CC-OFFICE-M1-002.md) §3—§13。实施限于 `CC-CHANGE-001—006`；未改 `office_core`、Odoo Addon、上游 SRS/TDD/Implementation Plan、TV/P0 报告或数据库。

## 3. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC-CHANGE 落实 | 6 / 6 |
| Preservation Impact | Potential Impact；输入只读、公式/结构回读、独立包边界由 ATR 验证 |
| Deviation | None |
| Stop Condition 触发 | No；处理了 macOS `RLIMIT_AS` 无法限制常规 Python 虚拟地址空间的问题，改用实际 RSS 监控，未改变 CC 范围 |
| Open Issues | 1 项环境边界；非关闭前置：RSS 监控仅实现 macOS/Linux，其他平台 fail closed |
| Revert | No |
| 当前状态 | **Implementation Complete；等待后续 FR / 负责人关闭评估** |

## 4. 实施历史条目（仅追加）

### IHR-001

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Implementation |
| Action | 冻结 `office_verify` 直接依赖为项目 venv 已安装的 `lxml==4.9.3`；未安装或升级任何依赖 |
| Reason | 按负责人批准和 CC-DEC-002 建立固定依赖基线 |
| Files / Components | `mymodules/office_verify/requirements.txt`；项目 `venv` |
| Contract Reference | CC-CHANGE-006、CC-TEST-001、CC-DEC-002 |
| Upstream Reference | TDD V0.3 §§3—4、§7 |
| Result | Completed；Python 3.11.9、lxml 4.9.3、BSD-3-Clause 元数据已记录 |
| Deviation | None |
| Follow-up | 不升级；目标 Linux 部署环境仍须按其自身预算复核 |

### IHR-002

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Implementation |
| Action | 新增独立同步回读 API、Mapping Plan 校验、ZIP/XML 结构检查、XLSX/DOCX 语义读取、脱敏报告和稳定错误 |
| Reason | 落实六项 CC-CHANGE，并保持写入器与校验器的 Python 包边界隔离 |
| Files / Components | `mymodules/office_verify/{__init__,errors,models,security,service,verify}.py` |
| Contract Reference | CC-CHANGE-001—006；CC-PRESERVE-001—006 |
| Upstream Reference | TDD §§3.2—3.4、§§4、6—7 |
| Result | Completed；仅接受 `.xlsx/.docx` 当前基础能力；公式缓存逐公式报告但不返回缓存值 |
| Deviation | None |
| Follow-up | 不含 Odoo、附件、聊天、HTTP、Provider 或 Queue Job |

### IHR-003

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Fix |
| Action | 首轮测试显示 macOS 不能将 `RLIMIT_AS` 设为 4 GiB；普通 Python 进程虚拟地址预留超过该阈值，导致子进程在解析前被拒绝。改为父进程通过 macOS `proc_pidinfo(PROC_PIDTASKINFO)` 或 Linux `/proc/<pid>/status` 监控 RSS，超预算即终止子进程；未支持平台 fail closed |
| Reason | 首轮实测表明地址空间上限不适用于本机 Python 运行时；需保留可用回读路径且不虚称内存限制通过 |
| Files / Components | `mymodules/office_verify/service.py`、资源预算测试 |
| Contract Reference | CC-CHANGE-005、CC-TEST-006、CC-PRESERVE-002 |
| Upstream Reference | TDD §§6—7；CC §12 |
| Result | Completed；超时、内存预算过小均返回稳定资源错误并清理进程 |
| Deviation | None；CC 只要求有界资源预算，未指定使用 `RLIMIT_AS` |
| Follow-up | RSS 以 10 ms 周期观测；并非生产容量或瞬时内存峰值的环境认证，部署预算仍需单独评估 |

### IHR-004

| 字段 | 记录 |
|---|---|
| 时间 | 2026-10-20 |
| 阶段 | Fix |
| Action | 测试发现通用高级节点拒绝清单曾误含标准 `mergeCell`；移除误拒绝并增加合并区域丢失失败用例 |
| Reason | 合并单元格属于本 CC 要求保留并检查的 XLSX 结构 |
| Files / Components | `mymodules/office_verify/security.py`、`tests/test_office_verify.py` |
| Contract Reference | CC-CHANGE-002、CC-TEST-005/007 |
| Upstream Reference | TDD §4；CC §3.1 |
| Result | Completed；原合并区域保留时正常校验，结构改变时 Fatal |
| Deviation | None |
| Follow-up | 自动化失败与修复后的当前 Run 分别记于 ATR |

## 5. 实际变更清单

| 文件 | 动作 | 实际变更 | CC 来源 |
|---|---|---|---|
| `mymodules/office_verify/requirements.txt` | Added | 仅锁定直接依赖 `lxml==4.9.3` | CC-CHANGE-006 |
| `mymodules/office_verify/__init__.py` | Added | 导出独立公开 API 和数据类型 | CC-CHANGE-001 |
| `mymodules/office_verify/errors.py` | Added | 稳定、脱敏错误契约 | CC-CHANGE-005 |
| `mymodules/office_verify/models.py` | Added | 资源预算、验证策略、可序列化结果 | CC-CHANGE-001/005 |
| `mymodules/office_verify/security.py` | Added | 有界 ZIP 读取、路径/重复项/CRC 检查、安全 XML、关系和 Content Types 校验 | CC-CHANGE-002/005/006 |
| `mymodules/office_verify/verify.py` | Added | Mapping、XLSX/DOCX 目标/公式/结构/样式回读 | CC-CHANGE-002—005 |
| `mymodules/office_verify/service.py` | Added | 可终止子进程、墙钟超时和 RSS 预算监控 | CC-CHANGE-001/005 |
| `mymodules/office_verify/tests/` | Added | 15 个合成 OOXML 自动测试 | CC-TEST-001—009 |
| 本证据目录 | Added | IHR、ATR、HVR-N/A 和 Run 日志 | CC §13 |

## 6. 偏离与停止条件

**Deviation: None。** 没有升级依赖。首次 `RLIMIT_AS` 方案失败的实际事实保留在 IHR-003 和 ATR-RUN-001；采用 RSS 监控后在同一 venv 重新运行测试。

## 7. 遗留问题与后续

| ID | 问题 | 类别 | 级别 | 状态 | 处理 |
|---|---|---|---|---|---|
| OI-001 | 目标生产平台的内存/时间预算未在真实部署环境验证；Darwin RSS 采用 10 ms 采样，不能等同生产峰值容量证明 | 环境/资源 | Informational | Open | M1 平台容量阶段据实际部署环境评估；超过预算仍 fail closed |
| OI-002 | 未准入对象、`.xls/.doc/.xlsm` 和真实复杂模板仍拒绝 | 格式/能力 | Expected | Open | 需独立能力验证和授权后再开放 |
| OI-003 | 没有 Odoo 附件持久化、UI 或产品交付流程 | 范围 | N/A | By CC | 留给后续实施阶段 |

## 8. 移交摘要

`office_verify` 实施完成，当前自动验证证据见 ATR-RUN-002。HVR 按 CC 的“人工验证：否”记录为 N/A。没有提交 Git，也没有执行 Odoo UI、真实模板或生产容量验证；本 IHR 不作 CC 关闭判断。
