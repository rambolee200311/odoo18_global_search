# 旧版 Office 格式补验报告（`.xls` / `.doc`）

| 项目 | 记录 |
|---|---|
| 验证日期 | 2026-10-22（Asia/Shanghai） |
| 验证类型 | M1 TV 补充验证；独立 Python/LibreOffice 进程，不访问 Odoo 数据库或 Provider |
| 上游基线 | `docs/verification/TV_Office_Engine_M1_Plan.md` V1.0.0 Frozen；既有 `TV_Office_Engine_M1_Report.md` 保持原样 |
| 环境 | 项目 Python 3.11.9 venv；LibreOfficeDev 26.8.0.0 Alpha |
| 结论状态 | **候选转换路径部分可行；旧格式仍未获准由产品引擎处理** |

## 1. 结论摘要

1. `openpyxl 3.1.5` 不能直接打开 `.xls`，`python-docx 1.1.2` 不能直接打开 `.doc`。当前 `office_core` 对两种格式均返回 `OFFICE_UNSUPPORTED_FEATURE`，这是现行能力白名单的拒绝结果。
2. `xlrd 2.0.1` 能读取本次两个 Odoo `.xls` 样本及一个合成公式样本；它是读取器，不提供保真写回能力。LibreOffice Alpha 能完成这些样本的 `.xls → .xlsx → .xls` 转换。
3. 合成 `.xls` 的 `SUM(C3:C12)` 公式在转成 `.xlsx`、转回 `.xls` 后再次转换检查，公式仍为 `=SUM(C3:C12)`，计算缓存为 `687.5`；合并范围 `A1:C1` 保留。但 XF 记录数从 20 增至 25，PDF 页面像素差异约 3.71%，标题和表头相对位置发生可见变化。因此不能判为无损。
4. 两个仓库 `.doc` 样本均可由 LibreOffice 转成 `.docx`，再转回 `.doc` 并重新转成 `.docx`。提取文本哈希相同，简单样本页面数不变；一个 `.docx` 包部件数增加。样本缺少真实复杂表格、浮动对象和版式，因此不能证明复杂 `.doc` 的格式保真。
5. LibreOffice 版本是 Alpha，且 Fontconfig 报告缓存目录不可写。本次结论仅描述当前本机候选行为，不代表目标生产版本、Microsoft Word/Excel 或真实业务模板的兼容性。

**当前处置建议：继续在聊天入口拒绝 `.xls` 和 `.doc`，不要因“转换成功”就开放上传或写回。** 如果要支持旧格式，应另行完成真实业务样本验证、目标稳定版转换器验证、格式/对象白名单和用户可见转换提示评审，再更新技术基线与实施契约。

## 2. 样本与隔离

所有源样本来自仓库内的 Odoo 测试夹具或演示数据；没有使用用户附件。另生成一个 `.xls` 合成夹具，用于公式、合并单元格和样式专项验证。转换输入副本、输出、PDF、PNG 和 LibreOffice profile 都位于 `/tmp/legacy-office-tv-20261022/`，未覆盖源文件。

| 样本 | 来源 | 大小 | SHA-256 前缀 | 结构/用途 |
|---|---|---:|---|---|
| MRP BOM `.xls` | `addons/mrp/static/xls/mrp_bom.xls` | 31,232 B | `92b0f00b1e9b` | `Template` 与 `Import FAQ` 两张表；模板布局 |
| Odoo MIME `.xls` | `odoo/addons/test_mimetypes/tests/testfiles/case.xls` | 7,168 B | `2fbbd5c9f7a0` | 3 张表，含空表 |
| 合成公式 `.xls` | 本轮临时生成 | 5,632 B | `98997974ae15` | `SUM` 公式、`A1:C1` 合并、货币和标题样式 |
| Odoo MIME `.doc` | `odoo/addons/test_mimetypes/tests/testfiles/case.doc` | 49,664 B | `3ef9bbd34efc` | OLE Word 测试夹具；转换后正文仅 2 个字符 |
| HR 演示 CV `.doc` | `addons/hr_recruitment/data/hr_recruitment_demo_williams_cv.doc` | 10,240 B | `1269075447d8` | 17 段正文，提取文本 271 字符 |

完整哈希、转换命令输出摘要和结构化结果见[机器可读证据](/Users/lijianqiang/Documents/odoo18_global_search/docs/verification/evidence/Legacy_Office_Formats/Legacy_Office_Validation_20261022.json)。

## 3. `.xls` 验证

### 3.1 直接读取与当前引擎行为

- `openpyxl.load_workbook(.xls)` 对所有 XLS 样本抛出 `InvalidFileException`，符合其 OOXML 范围边界。
- `xlrd 2.0.1` 成功读取工作表、有效行列、合并区域和 XF 索引；不把 XF 索引变化解释为样式保真。
- `office_core.inspect_document(..., application/vnd.ms-excel, ...)` 对这些文件返回 `OFFICE_UNSUPPORTED_FEATURE` / `format`，没有尝试转换或写回。

### 3.2 LibreOffice 转换与回读

LibreOffice Alpha 对三个输入均成功执行 `.xls → .xlsx` 和 `.xlsx → .xls`。每次单向转换耗时约 0.59–0.74 秒；命令返回 0 且目标文件可由 `openpyxl` 或 `xlrd` 重新打开。这个耗时只代表本机小文件冷/热转换，不是 Odoo 请求耗时或生产基准。

合成公式样本的回读结果：

| 检查项 | 转换前 | `.xls → .xlsx → .xls → .xlsx` 后 | 判定 |
|---|---|---|---|
| 公式 | `C13 =SUM(C3:C12)` | 仍为 `=SUM(C3:C12)` | 保留（限此样本） |
| 公式缓存 | LibreOffice 渲染/回读结果 687.5 | `data_only=True` 读到 687.5 | 保留/重算（限此公式） |
| 合并区域 | `A1:C1` | `A1:C1` | 保留 |
| XF 记录总数 | 20 | 25 | 元数据变化 |
| 页面渲染 | 1 页 | 1 页 | 页面数相同，但首屏像素差异约 3.71%，标题与表头布局发生变化 |

MRP BOM 样本保持 2 张工作表、名称和行列数据；XF 记录数从 30 增至 31。Odoo MIME 夹具原有 3 张表名保留，但两个空表在 `.xlsx` 对象模型中的有效尺寸变为 1×1，说明空表边界也存在结构变化。PDF 首页面像素差异分别约 0.33% 和 0.22%，不能据此代替目标 Office 软件中的人工业务验收。

## 4. `.doc` 验证

### 4.1 直接读取与当前引擎行为

- `python-docx 1.1.2` 直接读取 `.doc` 抛出 `BadZipFile`；它只解析 OOXML `.docx` 容器。
- `office_core.inspect_document(..., application/msword, ...)` 对两个样本均返回 `OFFICE_UNSUPPORTED_FEATURE` / `format`。

### 4.2 LibreOffice 往返

两个样本均完成 `.doc → .docx → .doc → .docx`。转换后 `python-docx` 能重新读取最终 DOCX，正文文本 SHA-256 与首次转出的 DOCX 相同，页数及页面尺寸未变；测试夹具像素差异约 0.045%，CV 演示样本像素差异为 0%。但这两个文件均不是复杂文档：测试夹具的正文只有 2 个字符，CV 演示文档没有表格、图片或浮动对象。`case.doc` 转换后包含一个媒体部件，而 `python-docx` 的 `inline_shapes` 为 0，提示某些对象可能位于非正文区域，不能只看正文抽取结果。

包结构也发生变化：两个样本往返后 DOCX 部件数各增加 1。既有 M1 TV 合成复杂 Word 探测还记录过 VML 文本框在 `.docx → .doc → .docx` 往返中从 1 个变为 0，绘图节点数量发生改变；该既有报告结论仍有效，进一步说明“正文文本相同”不等于 Word 对象和版式无损。

## 5. 风险与边界

- 当前 Odoo 聊天引擎仍只启用 `.xlsx/.docx`；旧格式应被拒绝为不支持格式，不应显示为文件损坏或安全签名伪造。
- `.xls` 的公式、缓存和合并结构在少量样本可往返；样式 XF 与页面排版发生差异。不得把该结果推广到宏、外部链接、批注、图表、数据验证、打印区域或复杂企业模板。
- `.doc` 简单文本往返可行，但复杂分页、浮动图片、文本框、域、修订、批注、嵌入对象和字体替换尚未验证；此前合成 VML 证据显示对象结构会变化。
- LibreOffice 的 Alpha 版本与 Fontconfig 警告限制了视觉证据；没有 Microsoft Office/WPS 实际打开验收，也没有目标服务器稳定版 LibreOffice 实测。
- 转换结果输出成 `.xlsx/.docx` 是格式升级，原 `.xls/.doc` 格式并未被原生编辑。用户是否接受自动升级、是否要求保留格式，仍需产品决策。

## 6. 本轮未做事项

- 没有把 `.xls/.doc` 上传至 Odoo 聊天、没有写 Odoo 数据库、没有调用任何 LLM Provider。
- 没有启用旧格式产品支持，没有改依赖、模块逻辑、冻结 SRS/TDD/TV Plan。
- 没有使用用户真实业务 `.xls/.doc`；没有在稳定版 LibreOffice、Microsoft Excel/Word 或 WPS 中验收。

因此本轮旧版格式结论是：**候选转换在限定样本上可运行，但产品级支持仍 `INCONCLUSIVE`；当前安全拒绝策略保持正确。**
