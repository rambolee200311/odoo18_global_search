# ATR-M2-PHASE-C-DOCUMENT-OPERATIONS：自动化测试与验收记录

| 项目 | 值 |
|---|---|
| 日期 | 2026-11-03 |
| 状态 | **最新补充：PASS（本轮指定的 Odoo TransactionCase + Sales/Purchase 浏览器 E2E）；初始 BLOCKED 已由文末执行证据更新** |
| 分支 | `main` |
| 工作区基线 | 开始前记录 82 项已有未提交状态；结束复核 91 项状态；暂存项 0 |
| Odoo 运行状态 | `127.0.0.1:8091` 仍监听（PID 33826）；本次未重启、未升级模块 |
| 最终 Python 测试日志 | `/private/tmp/phase_c_final_python_tests.log` |
| 关联实现记录 | [`IHR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md`](IHR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md) |

## 测试执行记录（阶段 C 首轮核心验收时）

### 1. 纯 Python 回归 — PASS

执行命令：

```bash
PYTHONPATH=mymodules venv/bin/python -m pytest -q \
  mymodules/office_document_operations/tests \
  mymodules/office_core/tests \
  mymodules/office_verify/tests
```

最后一次实际输出：

```text
........................................................................ [ 80%]
..................                                                       [100%]
90 passed in 12.70s
```

覆盖范围包括：

- Schema 预检、操作参数与执行结果；
- 插行/repeat-row、排序、格式、清空、写值及整行关系保护；
- 公式文本写入及回读（不包括公式重算）；
- 输入文件与输出文件隔离、操作失败时不发布部分输出；
- 旧 Mapping Writes 到 Schema 1.1 操作序列的转换；
- repeat-row 与 Mapping Writes 进入同一 core 操作路径；
- 显式未格式化坐标写入和授权清空；
- 保存候选重新打开、ZIP 完整性、内容状态与 SHA 回读；
- stale source fingerprint 拒绝；
- DOCX 既有兼容候选的独立回读。

完整 pytest 日志见 [`/private/tmp/phase_c_final_python_tests.log`](/private/tmp/phase_c_final_python_tests.log)。

### 2. Python 编译检查 — PASS

执行命令：

```bash
venv/bin/python -m compileall -q \
  mymodules/office_core \
  mymodules/office_document_operations \
  mymodules/office_verify \
  mymodules/office_engine_m2/services/render_bridge.py \
  mymodules/office_engine_odoo/models/office_document_request.py
```

退出码为 0，无编译错误输出。

### 3. Diff 空白检查 — PASS

执行命令：

```bash
git diff --check
```

退出码为 0，无 whitespace error 输出。

### 4. Odoo TransactionCase / 模块升级 — NOT RUN（BLOCKED）

- 曾尝试用普通 pytest 收集 `office_engine_m2` 的 Odoo TransactionCase；在 addon 导入阶段失败，错误为 Odoo 要求模型模块导入名以 `odoo.addons.*` 开头。该失败属于测试启动方式，不是测试断言通过。
- 没有隔离数据库和隔离 filestore。当前 8091 使用共享开发环境，因此没有在其上执行可能提交事务或改附件的 TransactionCase，也没有调用 `button_immediate_upgrade`。
- 未验证 Odoo registry、真实 spawn Worker 的 addon 搜索路径、Session/Revision 持久化、附件与 mail.message 关联。
- 上述普通 pytest 收集失败的完整 shell 命令及独立日志未保存在本 ATR 的证据目录，因此不伪造精确命令行或 traceback；其事实和限制也记在 TDD 第 10.3 节。

### 5. 浏览器 / Provider E2E — NOT RUN（BLOCKED）

本次未操作浏览器、未调用真实 Provider、未生成预览或正式文件。8091 监听状态仅证明服务端口仍在运行，不证明本轮代码已加载或聊天流程可用。既有历史 HVR/浏览器记录不计作本次 Phase C 验收证据。

### 6. 保存后独立文件回读 — PASS（仅纯 Python fixture）

测试通过临时 XLSX 输入和候选文件验证值、格式、日期/数字类型、零值、未修改单元格、公式文本、ZIP 和重新打开结果。没有生成或交付真实 Odoo 业务文件；公式值未由 Excel/LibreOffice 重算。

## 阶段判定

| 验收层 | 状态 | 结论 |
|---|---|---|
| 独立 Python Document Operations | PASS | 90 项通过 |
| `office_core` / `office_verify` 纯 Python 集成 | PASS | Mapping 兼容转换、repeat-row、验证报告与 SHA 回读通过 |
| Odoo `TransactionCase` | BLOCKED | 没有隔离数据库/filestore；普通 pytest addon 收集失败 |
| M2 / `office.document.request` 集成 | BLOCKED | 未在 Odoo registry 和真实 Worker 环境运行 |
| 浏览器 / 真实 Provider | NOT RUN | 没有本轮真实 Thread 验收 |
| 真实 Odoo 文件附件及独立下载回读 | NOT RUN | 本轮未创建生产附件或文件 |
| 阶段 C 总体 | **BLOCKED** | 纯 Python 证据不足以完成 Odoo 生产集成验收 |

## Git 与副作用记录

- 开始前工作区有 82 项未提交状态；结束时 `git status --short` 有 91 项状态，包含本项目既有历史改动及本阶段文件，不能把总数差异全部归因于本 ATR。
- 当前分支 `main`；暂存项 0。本轮没有执行 `git add`、commit、push、reset 或 clean。
- 8091 仍由 PID 33826 监听；本轮未终止或重启服务。
- 本轮自动化使用临时文件夹/内存 fixture；没有写入 Odoo 数据库或附件。

## 结论

纯 Python 操作执行与回读测试通过，但 Odoo TransactionCase、模块升级、真实 Thread、附件可见性及浏览器端下载均未验证。因此阶段 C **不能标记 PASS**。解除 BLOCKED 的最低条件是提供隔离 Odoo 数据库与 filestore，在该环境运行定向 TransactionCase/模块升级，然后在可控验收 Thread 完成真实预览与交付回读。

---

## 2026-11-03 最终集成验收补充（覆盖上面的首轮 BLOCKED 结论）

> 上面的 BLOCKED 是阶段 C 刚完成纯 Python 核心实现时的历史状态。本补充记录随后获准在共享开发库 `odoo18ce` 上执行的 TransactionCase 和真实 8091 浏览器验收；当前判断以本节证据为准。

### 1. 真实缺陷与修复

真实下载的采购预览曾与助手回复不一致：金额格式仍为 `General`，M4 仍含模板占位文本。浏览器中的真实 Tool Call 将 `format_patches` 和 `clear_columns` 放在 `proposal` 顶层；当时的 `office_save_mapping_preview()` 方法签名没有接收它们，导致渲染前没把操作送入 Mapping parser / Render Bridge。此后用户虽然看到 `preview_ready`，文件回读证明操作没有执行。这个旧结果记录为失败，不计作通过。

本轮最小修复：

1. `mymodules/office_engine_m2/models/office_mapping_tools.py:1251`：给 `office_save_mapping_preview()` 增加可选 `clear_columns`、`format_patches` 参数；合并顶层操作到 proposal 再解析；同一键重复出现在两个位置时拒绝，避免顺序覆盖。
2. `mymodules/office_engine_m2/models/llm_thread.py:658`：Provider Schema 将同一操作 Schema 放在工具调用顶层，且仍允许兼容旧的嵌套输入。
3. `mymodules/office_engine_m2/tests/test_native_chat_integration.py:2828`：新增 TransactionCase，调用真实 Odoo Tool 模型并检查已生成 Preview 的附件字节，断言表头及订单号保留、明确目标列的数据清空、数字格式生效。
4. `mymodules/office_engine_m2/tests/test_native_chat_integration.py:2578` 起：回归覆盖 repeat-row 生成的公式目标随后被用户明确数字值覆盖；公式列仍允许目标被覆盖，未要求改动的公式保持原样。

### 2. 自动化测试实际执行

#### 纯 Python：PASS

命令：

```bash
PYTHONPATH=mymodules venv/bin/python -m pytest -q \
  mymodules/office_document_operations/tests \
  mymodules/office_core/tests \
  mymodules/office_verify/tests
```

最终输出：

```text
97 passed in 13.05s
```

日志：`/private/tmp/phase_c_final_python_tests_after_opsfix.log`。

#### Odoo TransactionCase / 模块回归：PASS

在用户明确授权的共享 Odoo 开发数据库 `odoo18ce` 上执行：

```bash
venv/bin/python odoo-bin -c odoo.conf -d odoo18ce \
  -u office_engine_m2,office_engine_odoo \
  --test-enable --test-tags /office_engine_m2,/office_engine_odoo \
  --stop-after-init --http-port=0 --log-level=info \
  --logfile /private/tmp/phase_c_odoo_transactioncases_final.log
```

Odoo 日志摘要：

```text
office_engine_m2: 166 tests 225.13s 12769 queries
office_engine_odoo: 26 tests 22.45s 1537 queries
0 failed, 0 error(s) of 160 tests when loading database 'odoo18ce'
```

本次包含旧 Mapping/渲染、repeat-row、Preview、Revision、附件关联、Finalize 失败后重试、确认状态保护及 top-level 清空/格式操作的 TransactionCase。测试中有意注入的渲染/发布错误和权限拒绝日志属于断言场景；最终 Odoo 测试结果为 0 failures、0 errors。没有运行普通 pytest 冒充 Odoo 测试。

### 3. 真实 Provider / 浏览器 E2E

#### Sales → CRM 风格 Excel：PASS

- Provider：OpenAI `gpt-5.6-luna`；真实聊天 Thread `10004`。
- Retriever 读取当前用户可访问的 `sale.order` 记录 IDs `5052..5054`，编号 `GS-SO-0001..0003`，按订单号升序输出；金额分别为 EUR 25.41、26.62、27.83。
- 真实 Preview：`/Users/lijianqiang/Downloads/preview_GS-SO-0001_sales_crm_template.xlsx`，5,609 bytes。
- 真实 Finalize 下载：`/Users/lijianqiang/Downloads/office-output-fe5e854c-f847-5f8f-a015-5a805fe45ae7.xlsx`，5,608 bytes。
- Python/openpyxl 回读 Preview 与 Final 文件：编号及金额顺序正确、金额列格式 `0.00`、M4:M6 为空、M3 `Review Note` 与 A1 标题保留；XLSX ZIP 校验通过。

#### Purchase → 对账 Excel：PASS

- Provider：OpenAI `gpt-5.6-luna`；真实浏览器 Thread `10125`、Session `7872`。
- Odoo 日志记录 Retriever 调用 `purchase.order`，domain 为 `id in [1, 2]`，查询字段包括 `amount_total`、`currency_id`、`date_order`、`name`、`partner_id`。模型最终选择 P00001/P00002，并在 Mapping 中按 `name` 升序；对账金额按实际 EUR 两位小数计算：3026.50×1.1=3329.15，3095.00×1.1=3404.50。
- 修正后的真实 Preview Tool Call：`call_YBrwOvK0QXCMfOMB6yTdOKDv`，返回 `status=preview_ready`、Session 7872、revision 10、proposal revision 3、附件 25658、消息 68379，`attachment_posted_to_thread=true`。
- Finalize Tool Call：`call_ZTHNjOvj3ayhdCn6xdsgfLrn`，返回 `status=finalized`、proposal revision 3、revision 13、附件 25659、消息 68384，MIME 为 XLSX 且 `attachment_posted_to_thread=true`。浏览器中显示正式文件附件卡片，并从卡片触发下载；Odoo HTTP 日志确认 `/web/content/25659?...&download=true` 返回 200。
- 修正后的 Preview：`/Users/lijianqiang/Downloads/preview_P00001_purchase_reconciliation_template (2).xlsx`，5,556 bytes。
- Final 文件：`/Users/lijianqiang/Downloads/office-output-a1de374a-0d59-5107-89e3-ed64fa40945e.xlsx`，5,556 bytes，SHA-256 `1be41584f761570fc8f0843160f04e11a3ced67acea3af16f8374bf79b23512e`。
- 独立回读断言：Records!A4:A5=`P00001`,`P00002`；B4:B5=`Wood Corner`,`Gemini Furniture`；D4:D5=`3026.5`,`3095.0`；E4:E5=`3329.15`,`3404.5`（数值，非公式）；D4:E5 number format=`0.00`；F4:F5=`EUR`；M3=`Review Note`，M4:M5 为空；A1 标题及第 3 行表头保留；ZIP `testzip()` 返回无坏成员。Preview 和正式文件都满足上述断言。

### 4. 端口、工作树与副作用

- 8091 已在 TransactionCase/模块更新后重启并加载当前代码；当前监听 PID `49929`。浏览器下载日志见 `/private/tmp/phase_c_8091_runtime_after_opsfix.log`。
- 分支仍为 `main...origin/main [ahead 3]`。工作树已有大量未提交改动，本轮没有 reset、clean、stage、commit 或 push；变更保持在原工作树中。
- `git diff --check` 通过。
- 浏览器最终画面显示 `office_finalize` 的真实工具结果和 XLSX 附件卡片；此轮截图已随 Codex 执行记录显示。实际下载文件路径和回读断言见上文。

### 5. 最终判定及范围

| 验收层 | 当前结果 | 证据 |
|---|---|---|
| Python Document Operations / core / verify | PASS | 97 项 pytest |
| Odoo TransactionCase | PASS | `odoo18ce`，最终 0 failed / 0 error(s) of 160 tests |
| Sales 多记录 / 排序 / 金额格式 / M 列清空 / Preview / Finalize | PASS | 真实 Provider + Thread 10004 + 两个实际下载文件回读 |
| Purchase 多记录 / 排序 / 金额格式 / M 列清空 / Preview / Finalize | PASS | 真实 Provider + Thread 10125 + 附件/消息 ID + 下载 HTTP 200 + Preview/Final 回读 |
| 公式重算 | 未执行 / 不适用 | 调整后金额按用户要求直接写数值；没有把公式文本校验冒充重算 |
| 浏览器故障注入后的附件恢复 | 本轮未做真实浏览器注入 | Odoo TransactionCase 覆盖 retry 与保留有效 Preview；不能称为浏览器恢复 E2E |

**就本任务要求的 Stage C TransactionCase 与两个跨模型真实聊天验收项，结果为 PASS。** 该判定不扩大为任意 Office 格式、任意模型、公式计算引擎或浏览器故障恢复均已验证。
