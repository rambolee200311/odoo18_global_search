# CB-M2-CB-07 本地验证证据索引

日期：2026-11-10。仅记录本轮实际运行的本地检查；未执行 Odoo 数据库、模块升级、Provider、服务或 Browser 操作。

## 1. Python 语法

```text
venv/bin/python -m py_compile \
  mymodules/office_engine_m2/models/llm_thread.py \
  mymodules/office_engine_m2/models/office_mapping_tools.py \
  mymodules/office_engine_m2/services/edit_orchestrator.py \
  mymodules/office_engine_m2/services/workbook_version_service.py \
  mymodules/office_engine_m2/services/candidate_validator.py \
  mymodules/office_engine_m2/tests/test_edit_orchestration.py \
  mymodules/office_engine_m2/tests/test_native_chat_integration.py \
  mymodules/office_engine_m2/tests/test_office_retriever_integration.py
exit=0
```

结果：`PASS`。

## 2. Office Core 集成子集与 Validator

```text
PYTHONPATH=mymodules venv/bin/python -m pytest -q \
  mymodules/office_core/tests/test_document_operations_integration.py \
  mymodules/office_verify/tests
57 passed, 1 warning in 5.53s
exit=0
```

唯一 warning：openpyxl 对无默认样式 XLSX 使用默认样式。结果不代表 Odoo TransactionCase 或 Provider/UI 验收。

## 2.1 完整纯 Python Core + Verifier 回归

```text
PYTHONPATH=mymodules venv/bin/python -m pytest -q \\
  mymodules/office_core/tests \\
  mymodules/office_verify/tests
97 passed, 1 warning in 16.80s
exit=0
```

这是本轮最终纯 Python Office Core + Verifier 回归结果；和下方 Odoo/Provider/UI 的 NOT RUN 项是不同证据层级。

## 3. 差异空白检查

```text
git diff --check
exit=0
```

结果：`PASS`。

## 4. 未执行的验证

- Odoo TransactionCase / ORM / ACL / Record Rules / M1 Odoo 回归：`NOT RUN`。
- Odoo 模块升级、服务重启或数据库修改：`NOT RUN`。
- 真实 Responses API / Hosted Code Interpreter：`NOT RUN`；没有向 Provider 发送文件或数据。
- 真实 Odoo UI / Browser HVR、Candidate 下载与 Finalize：`NOT RUN`。

## 5. 非项目 Python 首次尝试

系统 `python3` 的合并测试命令因缺少 `python-docx` 无法收集完整 Office Core 测试；单独运行 worker 集成文件时 9 项 worker 调用失败并返回通用 `OFFICE_ENGINE_FAILED`，2 项通过。使用项目 `venv` 重新执行后，较窄测试组合为 57 项通过，完整纯 Python Core + Verifier 回归为 97 项通过。系统 Python 结果作为环境不匹配记录保留，不作为最终测试基线。
