# Office Engine M1 TV P0 补验报告

| 项目 | 内容 |
|---|---|
| 报告编号 | TV-OFFICE-ENGINE-M1-P0-FOLLOWUP |
| 版本 | 0.2 |
| 执行日期 | 2026-10-19（Asia/Shanghai） |
| 基线 | `TV_Office_Engine_M1_Plan.md` V1.0.0 Frozen |
| 原始 TV 状态 | `Partial` |
| 本次结论 | P0-A `BLOCKED`；P0-B `PARTIAL`；P0-C `BLOCKED`（本机配置/模块源码已检查，目标预算仍缺） |

## 1. 执行摘要

本轮使用用户指定的真实工作簿，在隔离临时目录内完成了 P0-B 的读写和回读测试；原件未修改，测试副本在测试结束后清理。P0-C 检查了当前 `odoo.conf` 的非敏感运行参数和用户指定的 `queue_job` 源码。没有启动 Odoo、连接数据库、安装依赖或修改服务配置。

主要发现：

- 当前项目 venv 的 `openpyxl 3.0.9` 能保存并保留该样本的 89 个公式表达式，但保存后 89 个公式缓存全部不可用；并且库明确警告该工作簿中的条件格式扩展及未知 OOXML 扩展不受支持、保存时将被移除。它不适合在未经修复/替代引擎验证的情况下直接用于此工作簿的生产写回。
- 当前 LibreOffice Alpha 对该样本另存后恢复了 89 个公式缓存，公式表达式与原件一致；89 个缓存值与原件缓存值一致，其中 75 个可由独立 Python 计算器覆盖且全部一致，另 14 个公式模式未被独立计算器覆盖。LibreOffice 对 335 个样式单元格的属性摘要有广泛差异，且中文字体环境有 Fontconfig 警告；本轮未作人工视觉通过判定，因此不能据此认定格式无损。
- `queue_job` 代码目录存在，但当前 `odoo.conf` 的 addons 路径未包含 `mymodules/queue`，用 Odoo 模块发现函数按该配置解析时找不到 `queue_job`。当前有效 `workers=0`，`server_wide_modules` 为 `base,web`，没有显式 Worker 超时/内存预算。OCA 配置说明要求生产 Jobrunner 以 `queue_job` 加载并配置大于 1 的 Worker 数量。以上是本地开发配置检查，不证明其他目标环境状态。

因此，P0-B 已取得真实样本证据但仅为 `PARTIAL`；P0-C 的源代码和本机配置审查完成，目标部署资源预算仍 `BLOCKED`。M1 TV 继续保持 `Partial`。

## 2. P0-A：真实 `.docx`

**状态：`BLOCKED`，本轮未执行。** 本轮只收到 `.xlsx` 路径，没有真实脱敏 `.docx` 样本。项目 venv 中仍未安装 `python-docx`；没有安装依赖，也没有使用 Odoo 测试夹具替代。原始 P0-A 阻塞记录保留在 `P0_Docx_Results.json`。

## 3. P0-B：真实 `.xlsx` 公式与格式

### 3.1 样本和环境

| 项目 | 记录 |
|---|---|
| 样本 | `mymodules/odoo-llm/docs/tv_docs/销售管理模板.xlsx` |
| 原件大小 | 30,395 bytes |
| SHA-256 | `4bc43b901a26d467c3772feaf892105019b952bcf26ca223fc8a2bf92e14bfe7` |
| ZIP 容器 | 37 个条目；总解压声明大小 81,791 bytes；`testzip()` 未发现损坏；未发现 VBA 项 |
| Python / `openpyxl` | Python 3.11.9 / `openpyxl 3.0.9` |
| LibreOffice | `LibreOfficeDev 26.8.0.0.alpha0`，开发版/Alpha，不是目标稳定版 |
| 原件处理 | 原件只读；仅复制到系统临时目录进行保存/转换测试；临时副本测试后清理 |

工作簿有 4 张表、89 个公式、10 个合并区域、4 条常规条件格式规则、1 个数据验证、每张表各 1 张图片；未发现外部工作簿链接。公式表达式包含逐行乘法、`SUM`、`COUNTIF`、`SUMIF`、`COUNTIFS`、`IFERROR` 和 `HYPERLINK`。没有把单元格业务值写入证据文件。

### 3.2 保存和公式结果

| 阶段 | 公式表达式 | 缓存值 | 独立核对 |
|---|---|---:|---|
| 原始工作簿 | 89/89 可读取 | 89/89 存在 | 本地独立计算器覆盖 75 个公式；75/75 与原缓存一致，0 个不一致；另 14 个公式模式未覆盖 |
| `openpyxl 3.0.9` 在副本上保存后 | 89/89 与原表达式一致 | **0/89 存在** | 缓存为空，不能提供公式计算结果 |
| LibreOffice Alpha 对 `openpyxl` 副本另存后 | 89/89 与原表达式一致 | 89/89 存在 | 89 个缓存结果与原文件缓存一致；独立计算器覆盖的 75 个仍全部一致，14 个未独立核对 |

另存时只在“使用说明”表的空白样式单元格 `D3` 写入了测试标记，以验证读取、修改和回读链路。标记仅写在临时副本，未写回原文件。公式映射哈希在原件、`openpyxl` 输出和 LibreOffice 输出间一致。

LibreOffice 尝试记录：首次使用显式 Calc 导出过滤器时返回码为 1、未生成输出；改用 LibreOffice 默认 `xlsx` 过滤器后，分别对原件副本和 `openpyxl` 输出副本执行成功，返回码为 0。没有隐藏首次失败。

### 3.3 格式与 OOXML 结构差异

- `openpyxl` 读取时发出 `Conditional Formatting extension is not supported and will be removed` 与 `Unknown extension is not supported and will be removed` 警告。工作簿扩展节点由 8 个变为 4 个；`styles.xml`、`workbook.xml` 和第一张工作表中的扩展节点未保留。常规条件格式规则计数、合并区域、数据验证和图片引用仍能从对象模型读回，但不能据此说扩展格式内容保留。
- OOXML 条目由 37 个变为 28 个。实际文件部件中 `docProps/custom.xml` 不再存在；`xl/sharedStrings.xml` 被改写为内联字符串形式。ZIP 目录条目的减少单独视为容器序列化变化。自定义属性是否承载业务必要信息，本轮没有查看或记录其内容。
- `openpyxl` 前后比较 335 个非空/带样式单元格的样式摘要，差异数为 0。
- LibreOffice Alpha 对 `openpyxl` 输出另存后，公式、合并区域、常规条件格式计数、数据验证和图片数量均可回读；但相对原件的 335 个样式单元格中，58 个数字格式、153 个字体摘要、34 个填充摘要、332 个对齐摘要发生变化，边框摘要无差异。这些是属性级差异，不等价于已证明视觉损坏或视觉保真。
- 同一 LibreOffice Alpha 将原件副本与 `openpyxl` 无编辑保存副本各导出为 6 页 PDF，页数相同；逐页像素差异比例约为 0.39%–8.31%。这是量化比对，没有进行逐页人工视觉验收；存在 Fontconfig 缓存/字体警告，中文呈现结论不确定。

### 3.4 P0-B 判定

**`PARTIAL`。** 已在真实样本上证实公式表达式保留与缓存处理行为，并发现当前候选库的明确限制。`openpyxl 3.0.9` 写回会清空所有公式缓存并丢弃扩展 OOXML 内容；LibreOffice Alpha 能恢复本样本缓存，但其样式属性差异较多，视觉未通过人工确认。测试运行版本也低于计划的 `openpyxl 3.1.x` 候选版本。当前证据不足以批准该组合用于生产模板写回。

完整脱敏结构化数据见 `P0_Xlsx_Results_20261019_RealSample.json`。原始模板及临时输出文件不复制到 evidence 目录。

## 4. P0-C：目标 Odoo 资源预算与 `queue_job`

### 4.1 `queue_job` 源码检查

用户提供的目录包含 OCA `queue_job` 模块源码，Manifest 版本为 `18.0.3.1.3`，Python 外部依赖为 `requests`；当前项目 venv 中 `requests 2.31.0` 已安装。源码 README 描述 Jobrunner 将延迟任务通过独立事务调度给可用 Odoo worker；其配置文档示例要求 `server_wide_modules` 包含 `queue_job`，并说明生产 Jobrunner 需要 `workers > 1`。

目录存在不代表模块已在数据库中安装，也不代表 Jobrunner 正在运行。本轮不连接数据库，因此安装状态和运行状态均未核实。

### 4.2 当前 `odoo.conf` 的本机检查

以 `-c odoo.conf` 解析有效 Odoo 配置并调用 Odoo 模块查找函数；该操作未连接数据库。观察到：

- 配置的 `addons_path` 包含 `mymodules` 和 `mymodules/odoo-llm`，不包含 `mymodules/queue`。
- 按该配置调用 `get_module_path("queue_job")` 返回未发现；因此当前配置下 `queue_job` 不可被 Odoo 模块发现。
- 当前解析的有效 `workers=0`；`server_wide_modules=base,web`，未包含 `queue_job`。
- `workers`、`limit_time_cpu`、`limit_time_real`、`limit_memory_soft`、`limit_memory_hard` 在 `odoo.conf` 中没有显式设置。反向代理超时、容器限制和队列运行参数未提供。

这证明当前本地配置还不能按源码路径启用 Jobrunner；它不是对目标服务器配置的结论。没有更改 `odoo.conf` 或 Odoo 服务。

### 4.3 P0-C 判定

**`BLOCKED`（本机源代码/配置审查完成，目标预算未取得）。** `queue_job` 源码存在且其 Python 依赖可用，但本机 addons 路径、server-wide modules 和 worker 配置不满足该模块 README 描述的生产 Jobrunner 配置。目标主机配置、代理时限、内存上限、并发预算及完整进程树 RSS 未取得，故仍不能判断同步方案安全，也不能得出 `queue_job` 必须或无需使用的最终结论。

资源预算与 `queue_job` 检查结构化记录见 `P0_Resource_Budget_20261019.md` 和 `P0_QueueJob_Inspection.json`。

## 5. 需要补齐的材料与后续动作

1. 提供一份获准测试、脱敏的真实 `.docx` 样本，并确认可修改的安全文本位置；P0-A 仍阻塞。
2. 确认本次 `.xlsx` 的 `openpyxl 3.0.9` 结果是否只是当前 venv 的环境证据；如需要验证计划候选 3.1.x，应由项目负责人授权在独立 venv/目标环境准备该版本后重跑，不覆盖当前证据。
3. 对 Excel 输出做目标稳定版 LibreOffice 或 Excel/Calc 的人工视觉检查，重点检查扩展条件格式、自定义属性、数字/货币格式、中文字体和打印布局；不得将 Alpha 的属性差异解释为已通过。
4. 提供/确认目标 Odoo 主机的 Python、库及 LibreOffice 稳定版，Worker 数量、CPU/real time 与 soft/hard memory 限制、容器资源限额、代理超时、预期并发和进程树观测能力。
5. 在目标部署配置中确认 `queue_job` 的 addons 路径、安装状态、`server_wide_modules`、Worker 数及 channels。当前证据只说明源码可用，不说明安装或启动完成。

## 6. 总体结论

当前真实 `.xlsx` 已暴露出会影响产品路线的写回边界，值得在 M1 TDD 中重点处理；但本轮不能冻结 Office 写回引擎选择。P0-A 仍未执行，P0-C 的目标资源预算仍缺，**M1 TV 维持 `Partial`**。本报告是补充证据，不修改冻结的 SRS、TV Plan，也不替代 M1 TDD。
