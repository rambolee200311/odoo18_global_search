# Office Engine M1 TV P0 补验报告

| 项目 | 内容 |
|---|---|
| 报告编号 | TV-OFFICE-ENGINE-M1-P0-FOLLOWUP |
| 版本 | 0.4 |
| 执行日期 | 2026-10-19（Asia/Shanghai） |
| 基线 | `TV_Office_Engine_M1_Plan.md` V1.0.0 Frozen |
| 本版新增 | 使用用户指定 `TARGET.docx` 完成 P0-A 隔离副本读写和结构检查 |
| 当前结论 | P0-A `PARTIAL`；P0-B `PARTIAL`；P0-C 本机队列链路 `PASS`、生产预算 `INCONCLUSIVE`；M1 TV 仍为 `Partial` |

## 1. 执行摘要

本版在 v0.3 的 P0-B/P0-C 证据基础上，使用 [TARGET.docx](../../../../../mymodules/odoo-llm/docs/tv_docs/TARGET.docx) 完成真实 DOCX 样本检查。原件保持只读，在 `/private/tmp` 隔离副本中使用 `python-docx 1.2.0` 对一个简单单行段落追加短测试标记，保存后重新打开并比较 OOXML 包结构。没有发现 package part、图片、关系、表格、页眉/页脚数量变化；除预期的 `word/document.xml` 外，其余 DOCX 部件哈希不变。

P0-A 判为 **`PARTIAL`**，不是完整通过：项目 Odoo `venv` 中没有 `python-docx`，此次采用文档工作区提供的 Python 3.12.14 / `python-docx 1.2.0`，与计划候选 `python-docx 1.1.x` 及 Odoo 部署运行时不同；LibreOffice 的中文字体回退导致标题文字渲染为缺字方框，无法据此确认中文排版保真。该样本本身没有文本框或 VML，不能用它证明这些对象的保留能力。

## 2. P0 状态汇总

| 项目 | 状态 | 判断 |
|---|---|---|
| P0-A 真实 `.docx` | `PARTIAL` | 隔离副本读写和结构保留通过；目标 venv、计划库版本和中文字体视觉验证缺口仍在。 |
| P0-B 真实 `.xlsx` | `PARTIAL` | 结论及真实模板数据沿用 v0.2 / v0.3；公式缓存及扩展 OOXML 风险未关闭。 |
| P0-C Queue Job | 本机链路 `PASS`；生产预算 `INCONCLUSIVE` | 安装与只读异步任务执行已验证；真实 Office 负载、prefork 及生产资源预算未验证。 |
| M1 TV | `Partial` | 不因单一 DOCX 样本通过而扩大格式承诺。 |

## 3. P0-A：`TARGET.docx` 读写与回读

### 3.1 样本及运行环境

| 项目 | 实测 |
|---|---|
| 样本路径 | `mymodules/odoo-llm/docs/tv_docs/TARGET.docx` |
| 文件大小 | 462,827 bytes |
| SHA-256 | `10f37d9fe8c924da3f790313451cba121d3b943fdd7e6c80b85dc8c786839d9a` |
| 容器检查 | ZIP 17 项；`testzip()` 为 OK |
| Odoo 项目 venv | Python 3.11.9；未安装 `python-docx`；未修改依赖 |
| 隔离测试运行时 | workspace Python 3.12.14；`python-docx 1.2.0`；`lxml 6.1.1` |
| 渲染器 | `render_docx.py`；LibreOfficeDev `26.8.0.0.alpha0` |

原件哈希在验证后复核，与验证前一致。测试副本和 PDF/PNG 只用于本地差异检查；记录结构与像素摘要后已清理临时目录，没有把包含原文的副本、PDF 或页面图提交到 evidence 目录。

### 3.2 样本结构覆盖

样本包含正文段落 216 个、表格 3 个、节 3 个、图片 3 张、带文字页眉部件 2 个和页脚部件 1 个。完整 OOXML XML 部件计数为段落 319、表格 3、DrawingML drawing 节点 3、图片节点 3。未发现文本框、VML、超链接、外部关系、批注、脚注、尾注、修订插入/删除、嵌入对象或宏相关部件。

### 3.3 隔离副本修改与结构结果

只对首个满足“非空、单 run、无 drawing/字段结构”的正文段落（零基索引 3，原字符数 14）追加测试标记。原件未写入。

| 检查项 | 修改前 | 修改后 | 结果 |
|---|---:|---:|---|
| ZIP 部件数 | 17 | 17 | 一致 |
| 新增/删除部件 | — | 0 / 0 | 无新增或删除 |
| 变化部件 | — | `word/document.xml` | 仅预期编辑部件变化 |
| 正文段落 | 216 | 216 | 一致 |
| 表格 / 节 | 3 / 3 | 3 / 3 | 一致 |
| 图片 / DrawingML drawing | 3 / 3 | 3 / 3 | 一致，媒体哈希不变 |
| 页眉 / 页脚部件 | 2 / 1 | 2 / 1 | 一致 |
| 关系文件 | 1 | 1 | 内容哈希不变 |
| 保存后重开 | — | 成功 | 测试标记可回读 |

隔离副本保存耗时约 `0.0127 s`，库加载耗时约 `0.0052 s`。耗时来自一次轻量编辑，不代表大文档或完整业务流程性能。

### 3.4 PDF/PNG 视觉对比

原件和测试副本均渲染为 38 页，页图尺寸均为 1414 × 2000。修改后的第 2–38 页与原件页图逐像素一致；第 1 页只有测试段落所在区域不同，像素差异比例为 `0.00001101`，页数未变化。第 1 页已人工检查，未见新增分页或裁切。

但 LibreOffice 把 `Noto Sans CJK SC` 回退到 Verdana，把 SimSun 回退到 Times New Roman；基线页图中原有中文也显示为缺字方框。因此这次视觉比较只能证明同一错误字体环境下修改前后页面布局接近，**不能证明中文字体、字形和真实目标环境中的版式正确**，视觉结论标记为 `INCONCLUSIVE`。

### 3.5 P0-A 判定与适用范围

**样本中的普通段落文本修改：通过。P0-A 整体：`PARTIAL`。** `python-docx 1.2.0` 对此文件的普通段落修改和 OOXML 回读没有静默移除已观察到的图片、关系、表格、页眉/页脚或其它 package parts。

本结论只覆盖该文件中实际存在的结构。由于样本不含文本框/VML，未验证其保留；由于没有对 Odoo `venv` 安装 `python-docx`，未验证 Odoo 运行时可直接调用；由于缺少 CJK 字体，未完成目标字体版式验收。实际部署仍需锁定并验证采用的库版本。

结构化记录见 `P0_Docx_Results_20261019_TARGET.json`。临时编辑副本的 OOXML 不进入仓库。

## 4. P0-B 与 P0-C

P0-B 真实 Excel 样本的公式缓存、扩展 OOXML、LibreOffice 样式差异及限制沿用 [`P0_Followup_Report_v0.2.md`](P0_Followup_Report_v0.2.md)。P0-C 的模块安装、queue runner host 修正、两条只读任务完成记录及生产预算限制沿用 [`P0_Followup_Report_v0.3.md`](P0_Followup_Report_v0.3.md)。本版不更改这两项的证据和结论。

## 5. 后续补验

1. 若 M1 目标环境使用 Odoo 项目 `venv`，应在依赖决策后验证获准锁定的 `python-docx` 版本；当前 venv 尚无此库。
2. 在渲染主机安装并记录目标业务可用的 CJK 字体，重跑前后 PDF/PNG 对比。没有匹配字体时，中文视觉结果继续标记 `INCONCLUSIVE`。
3. 如业务模板含文本框、VML、浮动对象、批注或其它高级 OOXML，提供包含这些对象的授权脱敏样本单独验证；本样本未覆盖这些结构。
4. P0-A 的结果不替代 DOCX 大文件性能、畸形文件隔离或 Office 全流程队列测试。

**总体结论：M1 TV 继续保持 `Partial`。** 本次为真实 DOCX 建立了可复核的普通段落写回与结构保留证据，但不能据此宣称所有 DOCX 模板或目标运行环境已通过。
