# Odoo 通用 Office 文档自动化引擎 M1 技术验证报告

| 项目 | 内容 |
|---|---|
| 报告编号 | TV-OFFICE-ENGINE-M1-REPORT |
| 报告版本 | 0.1 |
| 状态 | **部分完成；不构成 M1 TV 总体验收通过** |
| 计划基线 | `TV_Office_Engine_M1_Plan.md` V1.0.0 Frozen |
| 执行时间 | 2026-10-19（Asia/Shanghai；详见 `evidence/TV_Office_Engine_M1/TV_Office_Engine_M1_Results.json`） |
| 运行方式 | `venv/bin/python scripts/tv_m1/run_tv_m1.py` |
| Odoo 访问 | 未启动 Odoo、未连接数据库、未导入 Odoo 业务模型 |
| 样本 | 全部为自动生成的合成样本；未使用客户文件或业务附件 |

> **结论边界：** 本报告是当前开发环境的实测记录，不是对真实业务模板、目标 Linux 服务器或生产 Odoo Worker 的兼容性保证。关键覆盖项缺失或运行沙箱不允许采集的内容均标为 `INCONCLUSIVE` / `NOT RUN`，没有推断成通过。

## 1. 执行摘要

本轮按冻结计划执行了可在现有环境中安全完成的探测。结果支持以下有限结论：

1. 在当前 `openpyxl 3.0.9` 环境中，直接打开 `.xls` 失败；`xlrd 1.2.0` 可读取合成 `.xls` 的工作表、合并区域及样式索引，但公式单元格结果为空。LibreOffice 开发版可将该样本转为 `.xlsx` 再回转 `.xls`，公式表达式和合并区域保留，回转文件中的合计结果为 `687.5`。属性级样式仍有变化，不能据此宣称旧格式无损。
2. 对 `.xlsx` 的受控修改中，公式文本、合并范围、条件格式、数据验证、图片、命名区域和外部链接均可回读；预置的公式缓存值 `687.5` 在 `openpyxl` 保存后变为 `None`。当前 LibreOffice 开发版重新保存后，该合成公式的缓存值恢复为 `687.5`，但该重算路径还需在稳定版及真实业务文件上复核。
3. LibreOffice 将合成 `.docx` 转为 `.doc` 再转回 `.docx` 成功；VML 文本框被改写为 DrawingML，文本仍可抽取，但 OOXML 对象结构发生变化。中文字体/渲染环境不可靠，Word 的中文视觉保真结论为 `INCONCLUSIVE`。
4. 约 50,000 行合成 `.xlsx` 的 10 次修改/保存/回读总耗时中位数为 **1.924 秒**，范围 **1.389–2.160 秒**。该数字来自 macOS 开发环境和合成文件，且采样不包含进程后代的完整 RSS，不能直接用于 Worker OOM 或生产同步/异步决策。
5. 并发转换 1/2/4 路共 21 个小型合成任务均生成 PDF、未超时；profile 目录检查未发现残留 `*.lock`。系统禁止枚举全局 PID，因此不能判断是否遗留脱离父进程的 `soffice.bin`。
6. 对空文件、伪装脚本、截断 ZIP、坏 XML 和非 Office 高压缩 ZIP，`openpyxl` 均在独立进程中产生可捕获异常；LibreOffice 对空文件和脚本伪装样本却返回成功并生成 PDF，证明不能仅凭扩展名或转换进程返回码接受文件，必须先做服务端格式/容器校验。加密文件和宏样本未执行验证。

**整体判断：M1 技术验证仍未关闭。** 本轮提供了候选组件的方向性证据，但缺少 `python-docx`、经授权脱敏的真实业务样本、加密/宏样本、目标服务器/稳定版 LibreOffice、全局进程清点权限及 Odoo 实际运行预算。M1 TDD 可引用这些已验证的局部事实，但不得把未验证格式和性能边界写成已支持。

## 2. 环境、依赖与偏差

### 2.1 实际环境

| 项目 | 实测 |
|---|---|
| Python | 3.11.9，执行文件为仓库 `venv/bin/python` |
| OS/架构 | macOS 27.0.1 / arm64 |
| CPU/内存 | 10 logical CPUs / 16 GiB |
| `openpyxl` | 3.0.9（低于计划候选 3.1.x） |
| `python-docx` | 未安装；未联网或修改 venv 安装 |
| `xlrd` | 1.2.0（计划候选 2.0.1 未安装、未验证） |
| `xlwt` | 1.3.0 |
| `psutil` | 5.9.4 |
| Pillow | 9.4.0 |
| LibreOffice | `LibreOfficeDev 26.8.0.0.alpha0`，开发/Alpha 构建，不是稳定版 |
| PDF 工具 | `pdftoppm 26.05.0` |
| Odoo 配置 | `odoo.conf` 存在，但未配置 `workers`、`limit_time_cpu`、`limit_time_real`、`limit_memory_soft`、`limit_memory_hard` 这些被采集的显式预算值；本报告不代填 Odoo 默认值 |

### 2.2 运行限制及其影响

- 当前运行沙箱拒绝 `ps` 进程枚举和 `psutil.process_iter()`（`Operation not permitted: sysctl(KERN_PROC_ALL)`）。脚本可以记录自己启动的进程 PID，但不能可靠清点 LibreOffice 派生进程、系统级残留 `soffice.bin` 或总进程树 RSS。
- 子进程 RSS 使用短周期轮询，记录的是可见的启动 PID；不代表包含 LibreOffice 子进程的总峰值。部分极短任务的 RSS 采样可能低估峰值。性能 RSS 数字仅作本轮单进程观测，不作 OOM 结论。
- `fc-list` 能列出 macOS 的 Heiti/Songti/CJK fallback 字体，但 Fontconfig 报告没有可写缓存目录；LibreOffice 转换日志也有 Fontconfig 缓存警告。PDF 视觉样本中中文字符串“文档”未正常呈现。因此拉丁文字和简单布局差异可记录，中文字体、中文换行和企业模板版式结论为 `INCONCLUSIVE`。
- 当前主机不是经确认的目标 Linux Odoo 部署环境。没有用于旧版测试的授权真实 `.xls/.doc` 样本；样本均是由脚本生成的简单文件。

完整环境快照见 [`TV_Office_Engine_M1_Environment.txt`](evidence/TV_Office_Engine_M1/TV_Office_Engine_M1_Environment.txt)。

## 3. 验证矩阵结论

| TV 项 | 本轮状态 | 已执行 | 尚未覆盖/判定限制 |
|---|---|---|---|
| `TV-OFFICE-M1-01` 旧版格式 | **部分验证；总体 INCONCLUSIVE** | `.xls` 直接读取探测；LibreOffice `.xls → .xlsx → .xls`；合成 `.docx → .doc → .docx`；合并范围、公式、结构、PDF/PNG 比较 | 没有真实业务样本；无 `python-docx` 直接 `.doc` 检查；中文视觉受 Fontconfig 影响；仅 LibreOffice Alpha；旧版样式有元数据差异 |
| `TV-OFFICE-M1-02` 现代格式 | `.xlsx` 子项 VERIFIED（限当前版本/样本）；Word 子项 INCONCLUSIVE | 公式文本/缓存、OOXML 关系与结构、合并、条件格式、数据验证、图片、命名区域、外链；Word 原始包结构和 LibreOffice 往返 | 没有 `python-docx` 保存/静默丢失测试；没有真实复杂 `.docx`；无中文可靠视觉判定 |
| `TV-OFFICE-M1-03` 性能并发 | **部分测量；异步结论 INCONCLUSIVE** | 50k 行 `.xlsx` 10 次；约 9.73 MB `.docx` 包解析 3 次及 LibreOffice PDF 转换；1/2/4 路并发共 21 个任务 | 10 MB Word 样本由高熵图片构成，Python Word 库读写未测；Odoo 超时/Worker 预算未配置；全局进程 RSS/孤儿进程无法清点 |
| `TV-OFFICE-M1-04` 安全与伪装 | **部分验证；总体 INCONCLUSIVE** | 空文件、脚本伪装、截断 ZIP、无效 OOXML、受控高压缩 ZIP 的解析异常；有限读取上限；LibreOffice 对异常样本的行为 | 加密 Office、含宏旧格式未测试；未在 Odoo Worker 中运行；系统级子进程隔离/资源限制未验证 |

## 4. 维度一：旧版 `.xls` / `.doc` 转换

### 4.1 `.xls` 实测

合成文件包含一处合并标题、黄色粗体标题样式、货币格式、打印设置和 `SUM` 公式。

| 测试 | 结果 |
|---|---|
| `openpyxl 3.0.9` 直接打开 `.xls` | 失败，解析器返回可捕获的 `openpyxl.utils.exceptions.InvalidFileException`；与该库处理 OOXML 的边界一致 |
| `xlrd 1.2.0` 读取 | 成功读取 1 张表、13 行、3 列、1 个合并范围；检测到 20 个 XF 记录。公式单元格的读出值为空；该探测证明其能读取本样本结构/值，不证明可修改并保留样式 |
| LibreOffice `.xls → .xlsx` | 输出可重新打开，约 1.24 秒；合并范围保留，公式文本为 `=SUM(C3:C12)` |
| LibreOffice `.xlsx → .xls` 回转 | 输出可重新打开，约 0.99 秒；合并范围保留，公式单元格计算值为 `687.5`；XF 记录数由 20 变为 25 |
| PDF 第一页差异 | 页面尺寸相同；差异像素约 0.056%。仅为本合成样本的 LibreOffice 渲染差异，不等于真实模板无损 |

逐单元格样式摘要还发现：回转后的 XLS 在 `A1/A2` 的 `xlrd` 粗体元数据由 `True` 变为 `False`，而 PDF 视觉差异很低；货币格式字符串包含不同的转义表示。属性元数据与视觉证据并不完全一致，说明必须在目标 Office 应用及真实文件上复核，不能仅看 XF 计数或 PDF diff。样式明细在 [`TV_Office_Engine_M1_Style_Diff.csv`](evidence/TV_Office_Engine_M1/TV_Office_Engine_M1_Style_Diff.csv)，转换数据在 [`TV_Office_Engine_M1_Conversion_Matrix.csv`](evidence/TV_Office_Engine_M1/TV_Office_Engine_M1_Conversion_Matrix.csv)。

**本轮判定：** LibreOffice 对简单合成 `.xls` 往返可用作候选路径；旧版格式企业级样式保真仍 `INCONCLUSIVE`。不能据此冻结 `.xls` 的通用支持白名单。

### 4.2 `.doc` 实测

由于无法创建/取得独立真实 `.doc` 样本，本轮用手工构造的 OOXML `.docx`（包含表格、页眉页脚、VML 文本框、DrawingML 图片和中文文本）经 LibreOffice 转成 `.doc`，再转回 `.docx`。

- `.docx → .doc` 和 `.doc → .docx` 均生成可重新打开的文件。
- 表格数量、页眉和页脚保留；VML shape 数量从 1 变为 0，DrawingML drawing 数量从 1 变为 2；文本框指令文本仍可在回转包中抽取。该结果表明文本内容保留，但对象实现方式和段落结构改变。
- PDF 页面大小相同，第一页面像素差异约 0.481%；因为中文字体渲染存在缺字和 Fontconfig 警告，此差异仅作为合成拉丁布局的辅助指标。
- `python-docx` 未安装，故“`python-docx` 修改 `.docx` 后是否静默丢失文本框/图片”及“用 `python-docx` 直接读 `.doc`”均未执行。

视觉证据：[`docx-before-oldformat-page-1.png`](evidence/TV_Office_Engine_M1/artifacts/docx-before-oldformat-page-1.png)、[`docx-after-oldformat-page-1.png`](evidence/TV_Office_Engine_M1/artifacts/docx-after-oldformat-page-1.png)。

## 5. 维度二：现代格式结构与公式缓存

### 5.1 `.xlsx` 结构回读

合成文件的输入/回读对照显示，使用 `openpyxl 3.0.9` 修改非公式单元格后，以下结构仍被库对象模型识别：

- 公式单元格及表达式：`C12 =SUM(C2:C11)`；外部引用公式 `F2 ='[source.xlsx]Source'!A1`。
- 合并范围 `A1:C1`、1 条条件格式规则、1 条数据验证、1 张图片、命名区域 `OrderTotal`、1 个 external link。

这只是候选对象的存在性/语义摘要比较，不是完整 OOXML byte-for-byte 保真，也不覆盖图表、扩展 XML、所有绘图或真实外部工作簿刷新行为。明细见 [`TV_Office_Engine_M1_Structure_Diff.csv`](evidence/TV_Office_Engine_M1_Structure_Diff.csv)。

### 5.2 公式文本、缓存值与重算

使用测试夹具在 OOXML 中预置公式缓存值 `687.5`，确认读取状态并执行非公式单元格修改：

| 阶段 | 公式文本 | `data_only=True` 缓存值 |
|---|---|---:|
| 修改前 | `=SUM(C2:C11)` | `687.5` |
| `openpyxl` 保存后 | `=SUM(C2:C11)`（保留） | `None`（缓存丢失） |
| LibreOffice Alpha 打开/保存后 | `=SUM(C2:C11)`（保留） | `687.5`（恢复） |

本样本确认了 `openpyxl 3.0.9` 保存会使已有公式缓存不可用；当前 LibreOffice Alpha 对此受控公式能重算并回写缓存，单次约 1 秒。LibreOffice 重存还使部分样式 ID/货币格式序列化发生变化。需在稳定版 LibreOffice、更多公式类型（外部引用、日期、区域函数、兼容性函数）和真实工作簿上验证。TDD 应评估是否加入后端重算步骤及其副作用；本轮证据不支持把“用户按 F9”作为替代方案，也不证明所有公式可正确重算。

完整证据见 [`TV_Office_Engine_M1_Formula_Check.json`](evidence/TV_Office_Engine_M1/TV_Office_Engine_M1_Formula_Check.json)。

### 5.3 Word 现代格式边界

`python-docx` 未安装，因此库级 `.docx` 写入前后差异为 `INCONCLUSIVE`。手工构造的 `.docx` 原始 XML 只验证了样本可解析，不可替代 `python-docx` 的保存测试。本轮不得据此得出该库是否会静默删除 VML/文本框的结论。

## 6. 维度三：性能、内存和并发

### 6.1 大文件测量

| 样本/处理 | 运行次数 | 文件大小 | 耗时 | RSS 观测 |
|---|---:|---:|---:|---:|
| 50,000 行、3 列 `.xlsx`：完整载入、改单元格、保存、只读回读 | 10 | 975,879 bytes | 总耗时中位数 1.924 秒；范围 1.389–2.160 秒。解析中位数 0.931 秒；保存中位数 0.664 秒；回读中位数 0.002 秒 | 可见 Python 启动 PID 峰值 123–130 MiB；不含无法枚举的任何子进程 |
| 9.73 MB `.docx`：打开 ZIP、读取并解析 `word/document.xml` | 3 | 9,727,610 bytes | 总进程中位数约 0.051 秒；XML/ZIP 操作中位数约 0.0004 秒 | 可见启动 PID 约 15–17 MiB；仅是包结构检查，不是 `python-docx` 全文读取/写回 |
| 同一大 `.docx`：LibreOffice 导出 PDF | 1 | 9,727,610 bytes | 1.215 秒 | LibreOffice 启动 PID观测约 167 MiB；进程树总 RSS 不可见 |

大 `.docx` 的约 9.7 MB 由合成高熵 PNG 媒体构成，图片被放入文档包；它不代表多页真实 CMR、复杂表格或高密度 Word 文档的解析/渲染负载。脚本没有 `python-docx`，因此该样本的 Word 库解析和保存未测。

### 6.2 并发测量

| 并发度 | 任务数 | 成功生成 PDF | 单任务最大墙钟时间 | profile 检查 |
|---:|---:|---:|---:|---|
| 1 | 3 | 3/3 | 1.158 秒 | 任务后 profile 中未发现 `*.lock` |
| 2 | 6 | 6/6 | 1.516 秒 | 任务后 profile 中未发现 `*.lock` |
| 4 | 12 | 12/12 | 1.888 秒 | 任务后 profile 中未发现 `*.lock` |

上述 21 个任务未超时、未观察到输出串写；但是运行沙箱拒绝全局进程枚举，因此 `soffice.bin` 孤儿进程审计为 `INCONCLUSIVE`。单独 profile 的低并发结果不能证明生产机器长期高并发安全。

### 6.3 同步/异步结论

**结论：`INCONCLUSIVE`，本轮不能判定 `queue_job` 是否必须。** `.xlsx` 合成样本约 2 秒的耗时不代表真实模板；大 Word 的 Python 库读写未测；`odoo.conf` 未配置被本计划采集的 HTTP/Worker 预算；RSS 也不是完整进程树峰值。M1 TDD 应把目标部署超时、并发数、Worker 内存限额和基于真实模板的测量列为异步策略决策输入。在这些数据补齐前，不能写“同步安全”或“必须 queue_job”。

性能及并发原始数据：[`TV_Office_Engine_M1_Performance.csv`](evidence/TV_Office_Engine_M1_Performance.csv)、[`TV_Office_Engine_M1_Concurrency.csv`](evidence/TV_Office_Engine_M1_Concurrency.csv)。

## 7. 维度四：安全与格式伪装

### 7.1 Python 解析器异常

所有样本都在独立 Python 子进程中执行；测试包装层捕获到以下异常，进程以正常退出状态返回结构化异常类型：

| 输入 | `openpyxl` 结果 |
|---|---|
| 空文件 `.xlsx` | `zipfile.BadZipFile` |
| 脚本文本伪装 `.xlsx` | `zipfile.BadZipFile` |
| 截断 ZIP | `zipfile.BadZipFile` |
| ZIP 内必需 XML 格式错误 | `lxml.etree.XMLSyntaxError` |
| 高压缩比普通 ZIP 冒充 Office | `openpyxl.utils.exceptions.InvalidFileException` |

这是对这几个输入和当前版本的观察，不是解析器不存在崩溃漏洞的证明。

### 7.2 LibreOffice 返回码的陷阱

LibreOffice 对空文件和脚本文本伪装文件曾以返回码 0 生成 PDF；这不意味着输入有效或输出业务正确。截断 ZIP、坏 OOXML 和普通高压缩 ZIP 则返回非零且未生成 PDF。生产路径必须在 LibreOffice/库调用前验证容器签名、必需部件和大小/膨胀边界，并验证生成文件内容；不能仅根据扩展名、进程退出码或“输出文件存在”接受结果。

### 7.3 压缩炸弹样本

本轮受控 ZIP 含 16 MiB 重复数据，压缩文件约 16 KiB。限额读取器先检查条目声明未压缩大小，超过 1 MiB 上限即拒绝，读取内容字节数为 0；未触发大规模解压。该用例只验证了本测试包装脚本的拒绝逻辑，不证明 `openpyxl`/LibreOffice 内部解压过程也有同样限制。

### 7.4 未执行项

- 加密 `.xlsx/.docx`：没有可用加密样本生成器（`msoffcrypto-tool` 不在 `venv`，pip 缓存也不可用）；未伪造样本冒充加密测试。
- 含宏旧格式：没有合法宏样本；宏执行被禁止，因此本轮没有测试宏执行或宏保留。
- Odoo Worker 崩溃隔离：解析器完全脱离 Odoo 测试；不能据此说 Odoo Worker 一定不会受影响。
- 全局 `soffice.bin` 清点：系统进程列表权限被沙箱拒绝，未将“不能观察”记作“无残留”。

完整结果见 [`TV_Office_Engine_M1_Security_Matrix.csv`](evidence/TV_Office_Engine_M1_Security_Matrix.csv)。

## 8. 对 SRS / M1 TDD 的影响建议

以下是本轮证据形成的设计输入，不是对 SRS 的自动修改：

1. **旧版格式：** 保留 `.xls/.doc` 的 SRS 范围，但 M1 TDD 不应承诺所有旧版复杂对象无损。先用授权真实样本验证并定义按结构分类的白名单/拒绝策略；若拟限制冻结需求的可用范围，必须先走 SRS 变更。
2. **Excel 公式缓存：** 若交付文件要求公式结果缓存可直接读取/打印，`openpyxl` 保存后要单独处理缓存重算。LibreOffice 可作为候选重算器，但当前证据来自 Alpha 版，须稳定版/目标 OS 复核并对比重算后样式、外链和其它结构。
3. **Word：** `python-docx` 版本与文本框/VML/浮动对象保存行为仍未验证；TDD 不应在此证据缺口上做“无损支持”承诺。
4. **异步：** 本轮不足以决定使用/不使用 `queue_job`。TDD 需取得目标 Odoo 的显式超时和内存预算，并使用真实复杂文件重复测试；若耗时/内存接近预算，异步与限流必须成为设计项。
5. **输入安全：** 转换器可对格式伪装生成文件，必须在调用处理库前执行服务端格式/ZIP 结构校验，并设定大小、膨胀、条目数、超时和进程隔离边界。
6. **运行隔离：** profile 独立时的小规模转换未观察到 profile lock 残留；部署验收仍须在可枚举进程的目标主机检查进程后代、孤儿进程及整体 RSS。

## 9. 后续补验清单

要将 M1 TV 从部分完成推进到可评审关闭，至少补齐：

1. 在目标 Odoo 主机/操作系统上确认 Python、LibreOffice 稳定版、字体和 Odoo Worker 资源/超时配置，并重新执行环境快照。
2. 安装或纳入计划版本的 `python-docx` 后，实际修改 `.docx` 中的段落/表格，检查文本框、VML、图片、页眉页脚保存前后结构；记录精确版本和依赖变更。
3. 用经授权脱敏的真实 `.xls`、`.doc`、`.xlsx`、`.docx` 模板补测；至少包含真实公式/合并样式、复杂 Word 文本框、实际中文字体和分页布局。合成样本证据保留作回归基准。
4. 使用经验证的生成方式准备真实加密 Office 文件；加入加密输入探测。准备含宏的旧版样本，仅测试识别/拒绝/不执行边界。
5. 在允许进程枚举的测试主机上重复 LibreOffice 1/2/4 并发，记录每轮 `soffice.bin` 进程快照、profile lock、任务后孤儿进程和总进程树 RSS。
6. 根据实际 Odoo 请求预算和 Worker 限额复核性能数据，得出明确的同步/异步结论；未配置预算时维持 `INCONCLUSIVE`。
7. 在稳定版 LibreOffice 和目标 OS 上验证公式重算缓存、货币样式、外部链接、VML/DrawingML 和 PNG/PDF 视觉结果。

## 10. 可复现产物

探测脚本：

- [`run_tv_m1.py`](../../scripts/tv_m1/run_tv_m1.py)
- [`fixture_factory.py`](../../scripts/tv_m1/fixture_factory.py)

运行命令：

```bash
venv/bin/python scripts/tv_m1/run_tv_m1.py
```

脚本运行时在系统临时目录生成样本，运行完成后删除样本；证据目录只保留样本元数据/哈希、结果表、日志和合成 PDF/PNG。机器结果汇总见 [`TV_Office_Engine_M1_Results.json`](evidence/TV_Office_Engine_M1/TV_Office_Engine_M1_Results.json)。

本轮未提交客户/生产文件、未连接 Odoo、未联网安装 Python 包、未创建 TDD，也未运行 Odoo 集成测试。

## 11. 变更记录

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| 0.1 | 2026-10-19 | Partial | 按 TV Plan V1.0.0 执行当前 venv 可运行的合成样本探测；记录实际限制和剩余补验项。整体 TV 尚未关闭。 |
