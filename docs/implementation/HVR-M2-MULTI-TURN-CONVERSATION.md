# HVR — M2 自然语言多轮对话验收

| 项目 | 记录 |
|---|---|
| HVR 状态 | **FAIL（真实链路已运行；多轮变更和最终文件门禁未通过）** |
| 执行日期 | 2026-10-29（Asia/Shanghai） |
| 环境 | Odoo 18.0 / Python 3.11.9 / 数据库 `odoo18ce` / 本地 8091 |
| Provider / Model | OpenAI Provider / `gpt-5.6-luna`（真实 API，无 Mock） |
| Thread / Session | Thread `5180` / Session `5241` |
| Odoo 代码基线 | `ec0913af451f6cb051fffca7c5ed933260459822`；工作树包含大量既有未提交变更 |
| 模板 | `M2-multiturn-CMR.xlsx`，SHA-256 `7a5dd0dc94580b0765a4cc280502b307c138a0c802edd060f8801b3e36820cf1` |
| 实际预览 | `preview_S05457_M2-multiturn-CMR.xlsx`，附件 ID `17841`，MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |

## 结论

四条指定的自然语言确实通过 8091 的原生 `llm_thread.generate` 进入当前真实 OpenAI Provider；日志记录了 OpenAI Chat Completions 的 HTTP 200 和真实 `odoo_record_retriever` / `office_save_mapping_preview` 工具调用。第一轮生成了预览；第三轮也创建了新预览。

**验收不通过，不能宣告 M2 多轮修改闭环完成。** 第二轮命中既有送货地址规则并返回 `unchanged`；第三轮提交的工具参数没有表达 `×2`，回读仍是 `=D*E`；第四轮同样返回 `unchanged`，没有新增净重规则。四轮发生在带有早期尝试与旧附件的 Thread `5180` 中，不是干净会话。最终 Session 停在 `confirmation_required`，本次没有执行正式 Finalize，也没有正式归档文件。

## 环境与证据来源

- 当前 Odoo：`odoo-bin --version` → `Odoo Server 18.0`；配置数据库为 `odoo18ce`；Python `3.11.9`。
- 浏览器中 Provider 显示 `OpenAI`、模型 `gpt-5.6-luna`；本地服务日志记录请求目标为 `https://api.openai.com/v1/chat/completions`，没有连接 8909 Mock。
- 8091 进程日志：`/private/tmp/odoo8091_everything_conversation.log`。
- Addon 测试日志：`/private/tmp/m2_everything_conversation_test.log`。
- 测试结果摘录：`office_engine_m2: 27 tests, 22.59s`；测试汇总 `0 failed, 0 error(s) of 25 tests`。启动日志仍报告三个既有不可安装模块：`wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app`。
- 浏览器 Thread：<http://127.0.0.1:8091/odoo/action-631?debug=assets&active_id=llm.thread_5180>。
- 真实预览附件由 Odoo ORM 只读读取，并用 Python `openpyxl` 回读。直接附件下载端点 `/web/content/17841?...&download=true` 在服务日志中返回 HTTP 200（日志行 521）。

## 本次 UI 与消息输入记录

本次四条输入原文和时间：

1. 16:15 — `用 S05457 填写这个模板。`
2. 16:16 — `客户地址要使用完整的送货地址，不是开票地址。`
3. 16:18 — `总毛重改为单件毛重乘数量再乘以 2。`
4. 16:19 — `没有净重数据就留空，不要填 0。`

这四条均由浏览器聊天框提交；服务器分别记录了 `/llm/thread/generate?thread_id=5180` 请求和实际 Provider 调用。未通过本地正则或测试脚本代发。

**会话污染限制：** Thread `5180` 已包含 15:18、15:19、15:33、15:36、15:37、15:38 等此前的尝试及 `M2-multiturn-CMR.xlsx` 附件。本次 16:15 的新消息没有重新上传文件，而是复用该 Thread 里的既有附件和 Session。曾创建空 Thread `6411`，但本次内置浏览器的附件控件未能完成文件选择，因此没有把它当作干净上传验收。由此第二轮观察到的“送货地址已存在”不能证明模型在本次四轮中完成了从开票地址到送货地址的增量修改。

浏览器截图已在本次 Codex 会话工具输出中捕获，包含首轮工具链、第二轮 unchanged、第三轮预览附件和第四轮回复；**截图未保存为仓库 PNG 文件**，因此本报告不伪造本地截图路径，也不能称为一张覆盖四轮全部内容的完整截图。

## 四轮验收矩阵

| 轮次 | 真实执行与工具证据 | 结果与断言 | 判定 |
|---|---|---|---|
| 1 | `odoo_record_retriever`：`sale.order` 按 `name=S05457` 检索；实际命中记录 ID `5489`。之后调用 `office_prepare_context`，再次检索 6 条 `sale.order.line`，调用 `office_save_mapping_preview`（`call_KT3Wi4zzLrRatEbn8yGD0x7Q`）。 | 结果 `preview_ready`，Session `5241`、revision `4`、Proposal revision `1`、附件 `17840`。聊天出现 XLSX 预览卡片。数据检索及首轮预览真实成功；但源附件来自旧 Thread 历史，不是本轮新上传。 | **部分通过** |
| 2 | `office_save_mapping_preview`（`call_KvKxCtTt4rxCtnxRBYPM1rSC`）。 | 返回 `{"status":"unchanged","session_id":5241,"revision":4,"proposal_revision":1,"preview_attachment_id":17840,...}`。助手报告当前已使用 `partner_shipping_id.contact_address`。规则和版本没有变化，没有新附件。由于 Thread/Session 已有历史映射，不能证明本轮完成了要求的字段切换。 | **FAIL（增量切换未证实）** |
| 3 | `office_save_mapping_preview`（`call_O6NswUugwDOwtRwS6EnqGXea`），真实 Provider 工具参数见下文。 | 返回 `preview_ready`，revision `7`、Proposal revision `2`、附件 `17841`。工具参数没有 `formula` / `multiplier: 2` 或等价规则；实际 XLSX 的 `F23:F28` 仍为 `=D行*E行`。 | **FAIL（×2 未实现）** |
| 4 | `office_save_mapping_preview`（`call_vN9FP6GdPkftfBVNqPSIp9N3`）。 | 返回 `unchanged`，revision `7`、Proposal revision `2`、仍引用附件 `17841`。Proposal 只有 `product_id.weight` 映射，没有独立净重来源或净重目标规则；助手的“当前预览已符合”不能证明本轮新增了留空规则。 | **FAIL（规则变更未证实）** |

## 真实工具调用摘录

### 首轮数据检索

本地 Odoo 日志记录真实 Retriever 执行（`odoo8091_everything_conversation.log:231`）：

```text
Executing Odoo Record Retriever with:
model=sale.order,
domain=[['name', '=', 'S05457'], '|', ('company_id', '=', False), ('company_id', 'in', [2, 3, 1])],
fields=['id', 'name'], limit=2
```

明细读取日志（同一日志 `:354`）：

```text
model=sale.order.line,
domain=[['order_id', '=', 5489], ('id', 'in', [636, 637, 638, 639, 640, 641]), ...],
fields=['name', 'product_id', 'product_uom_qty'], limit=100
```

### 第三轮模型提交的 Mapping Tool 参数

下列真实参数来自聊天中 `office_save_mapping_preview` 工具调用详情。它包含重复行列映射，但没有表达用户要求的 `×2` 公式：

```json
{
  "session_id": 5241,
  "expected_revision": 4,
  "proposal": {
    "schema_version": "m2.mapping-proposal.v1",
    "mappings": [
      {"element_id": "xlsx:Blad1!B3", "source_field": "partner_id.name", "value_type": "string"},
      {"element_id": "xlsx:Blad1!B4", "source_field": "warehouse_id.partner_id.contact_address", "value_type": "string"},
      {"element_id": "xlsx:Blad1!B7", "source_field": "partner_shipping_id.contact_address", "value_type": "string"},
      {"element_id": "xlsx:Blad1!E17", "source_field": "name", "value_type": "string"},
      {"element_id": "xlsx:Blad1!E19", "source_field": "client_order_ref", "value_type": "string"}
    ],
    "clarifications": [],
    "skipped_targets": ["xlsx:Blad1!G23", "xlsx:Blad1!G24", "xlsx:Blad1!G25"]
  },
  "repeat_rows": [{
    "collection_field": "order_line",
    "sheet": "Blad1",
    "start_row": 23,
    "columns": [
      {"column": "B", "source_field": "name"},
      {"column": "C", "source_field": "product_id.default_code"},
      {"column": "D", "source_field": "product_uom_qty"},
      {"column": "E", "source_field": "product_id.weight"}
    ]
  }]
}
```

本地日志确认四轮对应的消息均走 `/llm/thread/generate`，并且 OpenAI Chat Completions 请求返回 HTTP 200：第一轮日志行 `227–284`，第二轮 `366–398`，第三轮 `404–482`，第四轮 `488–521`。第四轮生成历史还出现 Provider 警告：`Removing tool message with ID call_SvzJ70C7yPPsZwsodF4RucTS because it has no matching assistant message with tool_calls`（日志行 `489`），这是对话历史工具消息完整性的额外风险。

## XLSX 实际回读断言

对 Odoo 附件 `17841`（`preview_S05457_M2-multiturn-CMR.xlsx`）的只读 ORM 数据使用 Python `openpyxl` 读取，工作表 `Blad1`：

| 单元格/范围 | 实际内容 | 断言 |
|---|---|---|
| `B3` | `Azure Interior` | 客户名称已填 |
| `B4` | `My Company (San Francisco)` 及多行公司/仓库地址 | 有地址文本；本次没有独立核对其与期望仓库地址记录的逐字段一致性 |
| `B7` | `Azure Interior`，送货地址 `4557 De Silva St, Fremont CA 94538, United States` | 当前 Proposal 来源为 `partner_shipping_id.contact_address` |
| `E17` | `S05457` | 订单号已填 |
| `E19` | `None` | 参考号为空，未填 0 或默认文字 |
| `B23:B28` | 6 条订单明细 | 重复行扩展和 6 行数据实际存在 |
| `D23:D28` | `1, 2, 3, 4, 5, 6` | 数量数据已写入 |
| `F23:F28` | `=D23*E23` 至 `=D28*E28` | **不是用户要求的 `单件毛重 × 数量 × 2`** |
| `D29`、`F29`、`G29` | `=SUM(D23:D28)`、`=SUM(F23:F28)`、`=SUM(G23:G28)` | 合计行在第 29 行，汇总引用随 6 行明细更新 |
| 净重目标 | Proposal 无独立净重映射 | 只能证明未映射格子没有由本次 Proposal 写入；不能证明模型在第四轮新增了显式“无数据留空”规则 |

因此，回读证明了真实的明细扩展和预览文件，但**不证明 `×2` 规则已完成，也不证明第四轮修改被保存**。Session 当前状态为 `confirmation_required`；没有额外发送正式确认消息，没有正式文件或正式归档，本报告不把预览冒称为正式文件。

## 交互与权限 UI 变化

已移除 Thread Header 中用于关联/选择记录的 `Link` 控件，以聊天文本澄清代替；当前页面截图中未显示记录选择弹窗入口。相关工作树路径：

- `mymodules/odoo-llm/llm_thread/static/src/components/llm_thread_header/llm_thread_header.js`
- `mymodules/odoo-llm/llm_thread/static/src/components/llm_thread_header/llm_thread_header.xml`
- `mymodules/odoo-llm/llm_thread/__manifest__.py`
- `mymodules/office_engine_m2/models/llm_thread.py`
- `mymodules/office_engine_m2/models/office_mapping_tools.py`

针对模型返回多个记录候选的回归测试已加入 `mymodules/office_engine_m2/tests/test_native_chat_integration.py`。当前 Thread 顶栏仍显示 Provider/Model/Assistant 配置状态；它不是用户业务记录选择器。本轮未声称验证了系统中所有其他菜单/设置页面均不存在模型选择控件。

## 最终验收矩阵

| 硬门禁 | 结果 |
|---|---|
| 4 条原文通过真实 `gpt-5.6-luna` 原生聊天请求 | **PASS**（Thread 有历史污染） |
| 首轮 Odoo Retriever 读取 S05457 和 6 条明细 | **PASS** |
| 首轮预览附件真实生成并显示 | **PASS** |
| 第二轮将地址字段从旧规则增量切换到送货地址 | **FAIL / 无法证明**（当前规则原已为送货地址，工具为 unchanged） |
| 第三轮公式改为 `×2`，且其他映射保留 | **FAIL**（Tool 参数无公式，回读仍为 `=D*E`） |
| 第四轮保存净重无值留空规则 | **FAIL / 无法证明**（Tool 返回 unchanged，Proposal 无净重规则） |
| 每轮生成一份最新预览 | **FAIL**（第 2、4 轮均复用旧附件；没有变化时服务端未重渲染） |
| 最终确认与正式文件下载 | **NOT RUN**（Session 为 `confirmation_required`，没有正式确认消息） |
| 新鲜、无历史污染的四轮对话 | **FAIL**（Thread 5180 有旧消息和旧附件） |

## 证据与历史记录说明

- 浏览器当前 Thread：<http://127.0.0.1:8091/odoo/action-631?debug=assets&active_id=llm.thread_5180>。
- 最新服务日志：`/private/tmp/odoo8091_everything_conversation.log`。
- 全量测试日志：`/private/tmp/m2_everything_conversation_test.log`。
- 本地模板校验副本：`/private/tmp/M2-multiturn-CMR.xlsx`。
- 本报告此前版本关于部署数据使用开关阻断的结论已被本次运行取代：本次确实完成真实 API 调用和 Odoo Retriever 查询，数据使用开关不再是本次阻塞原因。
- 本次报告没有删改或重置其他工作树内容；未暂存、提交或推送代码。

---

## 定向回归补充：F16 写订单号、F17 清空（2026-10-29）

### 结果

**定向场景：PASS。** 此结果只覆盖本节的两项映射要求，不改变上方“四轮对话验收矩阵”的结论；四轮中的 `×2` 公式和净重空值规则仍为 FAIL / 无法证明，不能据此宣称完整四轮 HVR 已通过。

### 环境与真实浏览器证据

- Odoo：本机 `http://127.0.0.1:8091`，数据库 `odoo18ce`，当前 Thread `llm.thread_5180`。
- Provider / Model：聊天界面显示 `OpenAI` / `gpt-5.6-luna`；本次没有使用本地 Mock Provider。
- 用户输入：`请基于当前会话绑定的销售订单 S05457，将订单号写入 F16，并清空 F17 对应目标（如合并区域请清空可写合并目标）；仅执行这两项，其余规则不变。`
- 浏览器中真实显示了成功的 `odoo_record_retriever`、`office_prepare_context`、`office_save_mapping_preview` 工具调用，以及附件卡片 `preview_S05457_CMR-危险品禾麦CMR模板.xlsx`（XLSX 图标）。模型回复明确列出 F16 写入 `S05457`、合并目标 `E17:H17` 已清空、其他规则不变。
- Odoo 日志 `/private/tmp/odoo8091_required_clear.log`：真实聊天入口请求见 `10:19:03`；实际 OpenAI Chat Completions 返回 HTTP 200 见 `10:19:06`、`10:19:10`、`10:19:16`；附件 `ir.attachment` ID `18838` 的下载 URL 在 `10:19:41` 和 `10:20:22` 均返回 HTTP 200。
- 最终只读健康检查：授权网络访问后 `http://127.0.0.1:8091/web/login` 返回 HTTP 200；启动第二个实例因 8091 已占用而退出，原服务保持运行。
- 浏览器附件卡片截图已在本次 Codex 会话的工具证据中捕获。截图没有另存为 HVR 旁边的图片文件，因此本报告不声称存在可独立链接的截图文件。

### 实际附件回读

对本次会话附件 `18838` 的 XLSX 字节进行只读导出和 `openpyxl` 回读，文件副本为 [`preview_S05457_current.xlsx`](/private/tmp/preview_S05457_current.xlsx)，SHA-256：`915db1f48263b5059ee5943193b724eb84b2d5cd7984452b0b3c49d056fa0104`。

2026-10-29 最终复核时，我又从当前聊天附件卡片点击 **Download** 实际下载文件至 `/Users/lijianqiang/Downloads/preview_S05457_CMR-危险品禾麦CMR模板 (7).xlsx`。下载文件大小为 9,277 字节，SHA-256 与附件导出副本一致；并对这个浏览器实际下载文件再次执行下方回读断言。

| 检查项 | 结果 |
|---|---|
| 工作表 | `Blad1` |
| `F16` | `S05457`（通过） |
| 合并范围 | `E17:H17` |
| 合并锚点 `E17` | `None`（空白） |
| 合并从属单元格 `F17` | `None`（空白） |
| 公式 `F24` / `F25` | 原公式 `=D24*E24` / `=D25*E25` 保留 |
| 下载端点 | `/web/content/18838?...&download=true` 返回 HTTP 200 |

预览文件中 `F17` 是合并区域的从属单元格，实际内容存储在锚点 `E17`。因此本次清空通过回读 `E17=None` 与 `F17=None` 一并确认，没有写入空格或默认值。原只读公式未被当作必须跳过项，也未被改写。

### 自动化回归

- 纯 Python 校验器：`PYTHONPATH=. ./venv/bin/pytest -q mymodules/office_mapping_verify/tests/test_parser.py mymodules/office_mapping_verify/tests/test_validator.py` → **106 passed**（2026-10-29 最终复跑）。
- Odoo Addon 全量测试：`/private/tmp/m2_required_clear_final_tests.log` → `office_engine_m2: 129 tests, 169.42s, 8373 queries`；最终结果 **0 failed, 0 error(s) of 101 tests**。
- 新增 TransactionCase 覆盖：F16 写入、明确清空覆盖旧映射、历史 `required` 元数据不阻断、公式坐标作为跳过声明时保持公式、过期重复行跳过坐标不阻断当前模板。

### 代码范围与状态

本次为处理该定向失败，改动涉及 `office_mapping_verify` Proposal/clear 目标校验、`office_engine_m2` 的映射工具/渲染桥接/Session Proposal 持久化及回归测试。当前工作树仍有大量此前未提交修改；本轮没有暂存、提交、推送，也没有清理或回滚其他改动。

**本节结论：F16/F17 定向预览通过真实 OpenAI Tool Calling、Odoo 附件下载 HTTP 200 和 XLSX 字节回读验证。完整四轮验收状态仍为 FAIL。**

### 最终复核补充（2026-10-29）

- 6:19 的用户修订真实创建预览附件 `18838`。在最后的校验器修正和模块升级后，6:35 再次通过浏览器提交相同请求；真实 Provider 调用了 `odoo_record_retriever`（`call_AjBsbCc1cwg2K3Y6YctERITH`）、`office_prepare_context`（`call_n0sxNG9N0aI5Qp2YIZLCP3zw`）和 `office_save_mapping_preview`（`call_B0Iv4VisMvN6GyEzowhqiK7Z`）。Odoo 日志 `/private/tmp/odoo8091_required_clear.log` 在 `10:35:35` 至 `10:35:49` 记录了 4 次 OpenAI Chat Completions HTTP 200。服务端发现 Proposal 与请求一致，正确返回 `unchanged` 并复用现有预览，没有重复创建附件。
- 我从当前聊天附件卡片再次点击 Download，取得 `/Users/lijianqiang/Downloads/preview_S05457_CMR-危险品禾麦CMR模板 (8).xlsx`，再用 Python/openpyxl 回读：`Blad1!F16 = S05457`；合并区域 `E17:H17` 的锚点 `E17 = None`，从属格 `F17 = None`；`F24`、`F25` 原公式仍为 `=D24*E24`、`=D25*E25`。下载文件大小为 9,277 字节，SHA-256：`915db1f48263b5059ee5943193b724eb84b2d5cd7984452b0b3c49d056fa0104`。因此最新代码状态下完成了真实请求与现有预览下载回读；这次重复请求未产生第二份新附件。
- 最终纯 Python 定向集：**106 passed in 0.06s**。
- 最终 Odoo Addon 全量运行仍为 **0 failed / 0 error**；记录见上方完整测试日志路径。
- 8091 服务仍在监听，浏览器 Thread `llm.thread_5180` 当前显示成功工具调用、预览附件卡片和生成摘要。截图已在本次会话中展示；没有另存独立 PNG 文件。

---

## 2026-10-29 最终清空与公式回归补充

### 结论边界

本次移除了 `required` 元数据对目标缺失/明确清空的业务性阻断，也允许用户明确映射或清空模板原有公式格；未触及的公式仍保持原样。JSON 结构、目标清单、字段存在性和公式语法检查继续执行。重复行坐标修复及新的浏览器修订生成了正确预览。

**严格四轮验收仍为 FAIL。** 原四条消息后模型多次选错公式语法和列位置；最终正确文件是在额外纠正消息后才生成。该结果证明“最终规则可被校正并渲染”，不证明最初四轮一次通过或每轮均产生新附件。

### 最新真实聊天修订

- Thread：`llm.thread_5180`；Session：`5242`。
- 用户在 19:52 通过 8091 输入：`请重新执行刚才的纠正：总毛重写入 F23:F28，公式为 =E{row}*D{row}*2；清空 G23:G28，但保留 G29 及其模板公式；F17 对应合并单元格保持空白，B7 保持送货地址，净重无数据就留空。只清空明细区 G23:G28，不移动或清除合计行。请基于当前方案生成新预览。`
- Provider：真实 OpenAI API，界面显示 `gpt-5.6-luna`。本次模型先请求 `odoo_record_retriever`、`office_prepare_context`，再发起真实 Tool Call `call_Vgk9dm5NcrAU4kcr5uZbMk6R`。
- 保存调用的关键输入：Session `5242`、`expected_revision=16`；`repeat_rows` 的 F 列公式为 `=E{row}*D{row}*2`；`clear_targets` 包含 `E17` 和 `G23:G28`。
- 服务端结果：`preview_ready`，Session revision `19`，Proposal revision `6`，预览附件 ID `19512`。浏览器聊天流显示 XLSX 附件卡片和成功摘要。
- 同一 Thread 里此前的模型调用确实有失败：工具先把公式放在 G 列、随后清除坐标被错误下移；修正后的调用才成功。报告不把失败尝试略去。

### 最新 XLSX 回读

附件 `19512` 已从 Odoo 只读导出为 [`preview_S05457_M2_final_revised.xlsx`](/private/tmp/preview_S05457_M2_final_revised.xlsx)，大小 9,395 字节，SHA-256 `77358209762675fac57b0505cb5faf9d9caa9b924df691efd9c131b994370230`。`openpyxl` 对该文件的断言结果：

| 检查 | 回读值 | 结果 |
|---|---|---|
| 订单号 `Blad1!F16` | `S05457` | PASS |
| 合并单元格锚点 `E17` / 从属格 `F17` | `None` / `None` | PASS（明确清空） |
| `B7` | 完整地址文本 | PASS（等于 `partner_shipping_id.contact_address`） |
| 送货/开票地址是否不同 | `partner_shipping_id == partner_invoice_id` 为 True | 无法证明地址语义差异；本例两者数据相同，只能证明映射来源字段为送货地址字段 |
| 6 行明细 `B23:B28` | 六个产品描述 | PASS |
| 数量 `D23:D28` | `1,2,3,4,5,6` | PASS |
| 计算公式 `F23:F28` | `=E23*D23*2` 至 `=E28*D28*2` | PASS（公式文本；未运行 Excel/LibreOffice 重新计算缓存） |
| 明细 Points `G23:G28` | 全空 | PASS（清空目标没有误移到合计行） |
| 总毛重合计 `F29` | `=SUM(F23:F28)` | PASS |
| Points 合计 `G29` | `=SUM(G23:G28)` | PASS（模板原公式保留） |
| 净重 | 模板第 22 行列标题没有独立净重列 | N/A；不能据此声称净重规则在专用单元格得到验证 |

预览附件卡片在浏览器可见，带 XLSX 图标和 Download 控件。**本次没有取得浏览器下载事件的 HTTP 200 证据**；上述本地回读文件是通过只读 ORM 导出，不伪称由浏览器下载。`/web/content/19512?download=true` 的直接导航被浏览器客户端拦截。

### 回归结果

- 纯 Python：`PYTHONPATH=. ./venv/bin/pytest -q mymodules/office_mapping_verify/tests` → **107 passed**。
- Odoo 定向用例 `TestNativeOfficeChatIntegration.test_repeat_context_allows_explicit_overwrite_of_existing_formula_columns` → **0 failed, 0 error(s) of 1 tests**；日志 [`m2_repeat_band_clear_regression.log`](/private/tmp/m2_repeat_band_clear_regression.log)。它扩展为 3 行触发插行，断言 C4:C6 清空且 C7 合计公式不被误清除；非法 `{row}*{row}*2` 被拒绝且旧预览/revision 保留。
- Odoo Addon 全量：`office_engine_m2: 130 tests, 173.99s, 8625 queries`；汇总 **0 failed, 0 error(s) of 102 tests**；日志 [`m2_explicit_clear_formula_full_final.log`](/private/tmp/m2_explicit_clear_formula_full_final.log)。
- `py_compile` 与 `git diff --check` 通过。
- 8091 服务已在本机继续监听，当前浏览器位于 Thread `5180` 并显示最新预览卡片。截图出现在本次 Codex 工具输出中，但未保存为独立 PNG 文件。

### 本次代码范围

本次针对当前用户要求的实现和回归涉及 `office_mapping_verify/validator.py`、`office_core/engine.py`、`office_verify/verify.py`、`office_engine_m2/services/chat_entrypoint.py`、`office_engine_m2/models/office_mapping_tools.py`、`office_engine_m2/models/llm_thread.py` 及相应测试。新增重复区清空坐标用例，确保已展开的明细区坐标不再被重复下移。工作树仍包含大量此前未提交文件；本次没有暂存、提交、推送、清理或回滚它们。


### 显式空字符串映射与最终回归（2026-10-29）

为让 Provider 可直接表达用户指定的 `{"element_id":"xlsx:...!F17","value":""}`，Proposal parser 和验证器现在将该精确结构规范化为 `clear_targets`；非空字面量仍不接受。Provider 工具 JSON Schema 允许 `value` 仅取空字符串，系统提示也说明该形式只用于明确清空。被省略的目标仍不因此被清除，未被明确操作的公式仍保留。

| 验收项 | 证据 | 结果 |
|---|---|---|
| 纯 Python 解析/校验 | `PYTHONPATH=. ./venv/bin/pytest -q mymodules/office_mapping_verify/tests` | **109 passed** |
| Odoo Schema 与空字符串清空集成 | `TestNativeOfficeChatIntegration.test_explicit_clear_renders_blank_and_ignored_formula_skip_preserves_formula` 与 `...test_office_thread_uses_native_tools_and_prepare_binds_current_upload_and_record`，日志 [`m2_compact_blank_merged_anchor_test.log`](/private/tmp/m2_compact_blank_merged_anchor_test.log) | **0 failed, 0 error(s) of 2 tests** |
| Addon 全量回归 | 日志 [`m2_explicit_blank_merged_alias_full.log`](/private/tmp/m2_explicit_blank_merged_alias_full.log)；`office_engine_m2: 130 tests, 172.53s, 8624 queries` | **0 failed, 0 error(s) of 102 tests** |
| 源码静态检查 | `py_compile`、`git diff --check` | **PASS** |
| 最新真实预览 | Thread `5180` / Session `5242` / 附件 `19512`；由 ORM 只读导出并以 `openpyxl` 回读 | **定向内容 PASS**；见上节回读表 |

最新真实浏览器修订明确要求清空 `F17`、清空 `G23:G28`，保留 `G29` 原公式，并将 `F23:F28` 设为 `=E{row}*D{row}*2`。Provider 在该次实时调用中使用了 `clear_targets` 表达清空；紧凑 `value:""` 变体由 Odoo 集成测试直接覆盖，未把测试调用冒充为真实模型 Tool Call。集成用例使用真实合并区域 `E17:H17`，提交子坐标 `F17` 后由服务映射到可写锚点 `E17`，确认锚点为空且未触及的公式仍保留。附件卡片在当前聊天可见。最新附件由 ORM 导出，已验证 XLSX MIME、文件名后缀和字节内容；本次没有取得浏览器下载事件，因此不声称用户端下载已完成。

**验收状态仍为 FAIL（完整四轮对话）。** 最新文件对已明确修正的字段、六行明细、`×2` 公式、清空范围和合计公式回读正确；但它是在四轮原始交互后追加澄清/纠正才生成，且此记录不能证明四轮每一轮都产生附件或送货地址与开票地址有语义差异。完整四轮目标未达成，不能以本次空字符串支持或单份最终预览改报 PASS。
## 实际浏览器重跑与文件回读（2026-10-30，追加记录）

本节追加在既有 HVR 之后，不覆盖先前记录。此前 FAIL 结论仍保留；本节记录本次 8091 真实聊天重跑、最终预览及其边界。

### 环境与绑定

| 项目 | 本次实测 |
|---|---|
| Odoo | 18.0，数据库 `odoo18ce`，Python 3.11.9 |
| 当前代码基线 | `ec0913af451f6cb051fffca7c5ed933260459822`（工作树另有未提交修改） |
| Provider / 模型 | OpenAI / `gpt-5.6-luna`；本次浏览器请求在 Odoo 日志中对应真实 `POST https://api.openai.com/v1/chat/completions`，HTTP 200 |
| 聊天 | 浏览器 Thread `llm.thread/7661`，入口页面 `/odoo/llm.thread/7501?debug=assets` |
| Office Session | `6310`，绑定 `sale.order(5489)` / `S05457`；完成时 revision `13`、proposal revision `4` |
| 模板 | `CMR-危险品禾麦CMR模板.xlsx`，附件 `19955`；Session 指纹 `7a5dd0dc94580b0765a4cc280502b307c138a0c802edd060f8801b3e36820cf1` |
| 最终预览 | 附件 `20680`，`preview_S05457_CMR-危险品禾麦CMR模板.xlsx`，XLSX MIME，9,285 bytes；导出回读文件 SHA-256 `2b9c153dff8d33ebf68d770c27d59a93d8b6f239bf0b86ce2ce29eef5488ac5a` |

### 实际对话与工具结果

四轮原始用户消息均由 8091 的原生聊天入口发送到真实 Provider：

1. `用 S05457 填写这个模板。`：生成预览附件 `20677`。
2. `客户地址要使用完整的送货地址，不是开票地址。`：生成修订预览 `20678`。模型通过 `odoo_record_retriever` 读取送货地址关系后保存方案。
3. `总毛重改为单件毛重乘数量再乘以 2。`：生成修订预览 `20679`；Tool Call `call_kPZX11IlONrgH9C0rGXA8gAv` 返回成功。
4. `没有净重数据就留空，不要填 0。`：模型调用 `call_ctE0p1VUyS43p0TFeTU3PWLG` 后判定当前方案没有净重目标或需变更规则，回复“当前预览无需变更”，没有新建重复附件。

随后追加一条纠正消息，明确给出字段、清空锚点、六行重复映射和公式。第一次提交曾返回 `invalid_mapping_shape`；它不是 Odoo ACL 拒绝。检查发现 Proposal parser 对带 `value_type` 元数据的显式空值映射结构过于严格。本次在纯 Python parser 中补齐了该语法并加测试；随后模型按 Tool Schema 改用根级 `clear_targets`，真实 Tool Call `call_s9gLtoZ2G0RrWhvXnkSocucE` 成功，生成附件 `20680`。最终回复明确列出 B3/B4/B7/F16/F18、清空 E17、六行明细以及重复列规则。浏览器截图由 CUA 在本次 Codex 会话中捕获并展示，当前消息流可见成功 Tool Call 和 XLSX 下载卡片；截图未另存为独立 PNG。

服务器日志 `/private/tmp/m2_native_chat_8091_final.log` 记录了真实 Provider HTTP 200、Thread `7661` 的 generation 以及浏览器点击附件后对 `/web/content/20680?...&download=true` 的 HTTP 200 响应。该证据证明浏览器下载请求得到文件响应；本地用于回读的文件通过当前 Odoo 用户可访问的 Session 附件只读导出，不冒称来自浏览器下载事件的本地路径。

### 最终 XLSX 回读

附件 `20680` 以只读 ORM 导出至 `/private/tmp/s05457_latest_preview.xlsx`，再用 `openpyxl` 读取。原附件中公式文本存在，但原始 XLSX 没有保存计算缓存；另以 LibreOffice 对临时副本重算，只用于核对公式计算，不修改 Odoo 附件。

| 核对项 | 结果 | 说明 |
|---|---|---|
| `B3` | `Azure Interior` | 与订单 `partner_id.name` 相同 |
| `B4` | 完整仓库地址 | 与 `warehouse_id.partner_id.contact_address` 相同 |
| `B7` | 完整送货地址 | 与 `partner_shipping_id.contact_address` 相同；本库此订单的发票地址与送货地址记录相同，不能据此证明二者文本不同 |
| `F16` | `S05457` | 与订单 `name` 相同 |
| `E17` / `F17` | `None` / `None` | `E17:H17` 为合并范围；锚点和从属格均为空 |
| `F18` | `None` | 订单 `client_order_ref` 为空，未填默认文字 |
| 明细行 | `23–28` 共六行 | 数量为 `1,2,3,4,5,6`；`E23:E28` 使用可读产品重量 |
| 产品编码 | 第 23 行为空，其余行按当前数据写入 | 第 23 行的 `default_code` 与 `barcode` 都为空，系统未编造编码 |
| `F23:F28` | `=E{row}*D{row}` | 公式文本逐行正确；LibreOffice 临时副本重算值依次为 `0.01, 0.02, 3, 0.04, 5, 0.06` |
| `G23:G28` | `=F{row}*2` | 公式文本逐行正确；重算值依次为 `0.02, 0.04, 6, 0.08, 10, 0.12` |
| 合计行 `F29` / `G29` | `=SUM(F23:F28)` / `=SUM(G23:G28)` | 重算值分别为 `8.13` / `16.26`；原模板合计公式保留 |
| 净重 | N/A | 模板没有独立净重目标列；本次无法证明净重已写入专用单元格，也未写入 0 |

### 代码修复、权限边界与测试

- `mymodules/office_mapping_verify/contracts.py`：显式空值可带受支持的 `value_type` 元数据并规范化为 `clear_targets`；非空字面量仍须通过已定义的映射形式。
- `mymodules/office_mapping_verify/tests/test_parser.py`：增加带类型的空值映射解析测试。
- `mymodules/office_engine_m2/models/llm_thread.py`：补充原生 Retriever 的字段路径使用说明，避免把 dotted relation path 直接传给只接受当前模型字段的 `search_read`。
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`：覆盖上述 Retriever 指引及权限描述。
- 验证：`PYTHONPATH=. ./venv/bin/pytest -q mymodules/office_mapping_verify/tests`，**110 passed**；`git diff --check` 通过。
- 8091 当前运行配置使用真实 OpenAI Provider。业务数据读取没有通过 `sudo()`；Retriever 与关联字段读取继续执行当前用户 ORM 权限检查。
- `office_mapping_tools.py` 中未发现用户描述的“无法唯一解析”业务判定代码；其中仍有 Session/Thread 绑定、附件类型、Schema、单元格目标和安全公式校验。它们不是模型或数据模型白名单，也不是本次请求的 ACL 拒绝。本次没有删除这些保护。实际的 `invalid_mapping_shape` 根因在 Proposal JSON 结构兼容性，已通过 parser 补充解决。

### 验收结论

- **最终预览和指定单元格/公式回读：PASS。** 浏览器附件下载请求得到 HTTP 200；本地回读、地址来源比对、六行公式和合计公式检查均有数据证据。
- **严格“四轮每轮均生成新附件”的验收：FAIL。** 第四轮内容没有产生 Proposal 差异，系统没有重复渲染；最终正确文件是在额外纠正消息后生成。此前若将完整四轮宣布为 PASS，证据不足，本次不作该声明。
- **Odoo Addon 全量回归：PASS。** 在当前工作树重跑 `-u office_engine_m2 --test-enable --test-tags /office_engine_m2 --stop-after-init --http-port=0`；日志 [`m2_hvr_final_addon_test.log`](/private/tmp/m2_hvr_final_addon_test.log)，`office_engine_m2: 132 tests, 173.79s, 8519 queries`，汇总 `0 failed, 0 error(s) of 104 tests`。
- **纯 Python parser/validator：PASS。** 当前工作树 `110 passed`；`git diff --check` 通过。
- **服务可用：PASS。** 测试进程退出后，8091 仍由 Odoo PID `40884` 监听，`GET /web/login` 返回 HTTP 200。
- **交付下载本地路径：未证实。** 浏览器确实请求并收到 HTTP 200，文件卡片显示 Download；浏览器运行时未提供可核验的本地下载事件路径。

## 用户本轮要求的复测（2026-10-30，当前 8091 主线程）

本节记录本轮直接在内置浏览器复测的结果。它不覆盖前述历史，也不把未完成的轮次推断为通过。

| 项目 | 实测结果 |
|---|---|
| 浏览器 / Thread | 8091 内置浏览器，`llm.thread/7501`；当前 Provider 为 OpenAI，模型 `gpt-5.6-luna`；绑定 `office_prepare_context`、`office_save_mapping_preview`、`office_finalize`、`office_restore_proposal_revision` 等工具。 |
| Office Session | `6145`；模板文件名 `CMR-危险品禾麦CMR模板.xlsx`。 |
| 第一轮 | 用户输入 `用 S05457 填写这个模板。`。原生聊天中可见模型调用 Retriever、Context 和 Save Preview；保存工具真实返回 `status=preview_ready`、`preview_attachment_id=21122`、`revision=10`、`proposal_revision=3`，文件名 `preview_S05457_CMR-危险品禾麦CMR模板.xlsx`。聊天流显示 XLSX 下载卡片。**第一轮 PASS。** |
| 第二轮 | 用户输入 `客户地址要使用完整的送货地址，不是开票地址。`。真实模型调用 `office_prepare_context` 成功，返回 `status=ready`、Session `6145`、revision `10`、Proposal revision `3`，TargetManifest 与字段字典可见。刷新浏览器后仍停在该工具结果，没有助手总结、`office_save_mapping_preview` 调用或新附件；revision 和预览未改变。**未完成。** |
| 第三、四轮 | 未发送，因为第二轮没有完成，不能把它们记作已验收。 |
| 文件 | 当前复测只产出第一轮预览附件 `21122`，不是四轮对话的最终文件。浏览器卡片可见；后续已只读导出并回读该第一轮文件，见本节补充。没有把它冒称为四轮最终文件。 |

### 本轮代码与测试证据

- `mymodules/office_engine_m2/models/office_mapping_tools.py` 的 `_office_source_upload()` 对缺失/多个附件返回 `needs_input` 结构，对宏文件或不支持格式返回结构化状态；`office_prepare_context()` 消费该结果。该文件当前没有直接 `raise UserError` 语句。ACL、Thread/Session 绑定、输入 Schema 和渲染失败处理仍由后端执行，不能表述为“移除了所有服务端校验”或“绕过 Odoo 权限”。
- 新增 `test_prepare_context_returns_chat_recoverable_result_when_template_is_missing`，验证缺少模板时以可恢复的结构化结果返回。
- 纯 Python：`PYTHONPATH=. ./venv/bin/pytest -q mymodules/office_mapping_verify/tests`：**110 passed**。
- Odoo Addon 全量：日志 [`m2_usererror_structured_full_final.log`](/private/tmp/m2_usererror_structured_full_final.log)，`office_engine_m2: 133 tests`；`0 failed, 0 error(s) of 105 tests`。
- `py_compile` 和 `git diff --check` 通过。日志仍包含项目既有未加载模块 `wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app` 的提示，与本 CC 用例结果分开记录。

### 线程记录更正及验收结论

此前 2026-10-30 追加记录中的 Thread `7661` / Session `6310` / 附件 `20680` 属于同库的辅助 AI Chat 路径；本次用户当前浏览器页面实际是 Thread `7501` / Session `6145`，两者不可混写。本节记录的是当前浏览器主线程。

当前代码修改和自动化测试通过；浏览器第一轮成功生成预览，第二轮只成功取得 Office Context，模型未完成回答或保存新预览。第三、四轮未执行，当前 `21122` 也没有完成最终工作簿回读。因此本轮完整四轮验收仍为 **FAIL / INCOMPLETE**，不能宣布工作完成。用户可在当前浏览器线程中看到第一轮预览卡片和第二轮工具结果。

### 第一轮预览文件的只读回读补充

当前会话的 Odoo 附件 `21122` 已通过只读 ORM 导出为 [`preview_S05457_thread7501_first_turn.xlsx`](/private/tmp/preview_S05457_thread7501_first_turn.xlsx)，文件名 `preview_S05457_CMR-危险品禾麦CMR模板.xlsx`，MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，大小 9,449 字节，SHA-256 `f279cd0e07f18210f025d77718567b9836976fb0b6c9b10ec64af3f171c9e8be`。由 `openpyxl` 只读回读结果：

| 单元格/区域 | 回读结果 |
|---|---|
| `B3` / `B4` / `B7` | 客户名 `Azure Interior`；完整仓库地址；完整送货地址。 |
| `E17` / `F17` | 合并区域 `E17:H17` 的锚点 `E17` 为 `S05457`，从属单元格 `F17` 为空。 |
| `F16` / `F18` | 分别仍是模板文字 `REF号` 和 `Unloading ref号`；本轮并未按此前其他指令把订单号写入 F16。 |
| `B23:B28` / `D23:D28` | 六条明细与数量 `1,2,3,4,5,6` 已写入。 |
| `F23:F28` / `G23:G28` | 本轮初始公式分别是 `=D{row}*E{row}` 和 `=F{row}*3`，不是后续所要求的 `×2` 规则。 |
| `F29` / `G29` | 保留 `=SUM(F23:F28)` / `=SUM(G23:G28)`。 |

这份文件只证明第一轮预览数据，不证明四轮增量修改或最终文件。导出发生在本地 Odoo 进程中，没有通过浏览器下载事件取得本地路径；浏览器当前聊天卡片仍可直接下载附件 `21122`。
