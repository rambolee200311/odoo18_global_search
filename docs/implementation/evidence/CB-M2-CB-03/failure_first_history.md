# Failure-first History — CB-M2-CB-03

本文件是失败记录摘要。早期两项 pytest 的完整终端输出未保存为文件；下列信息来自当时实际执行结果，不冒充原始完整日志。

1. **Candidate worker metrics — API absent before implementation**
   - Command: `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py -k observed_resource_usage`
   - Result: 1 failed。测试调用的 `verify_candidate_output_with_metrics` 尚未实现；随后在现有隔离 worker 上补充 Candidate 专用 metrics API，并保持 M1 `verify_output` 返回契约不变。

2. **Date typing — incorrect classification/read path**
   - Command: `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py -k 'date_expected or date_formatted or iso_date'`
   - Result: 2 failed, 1 passed。观察到 `General` 格式的数值被日期断言接受，以及 OOXML `t="d"` 日期没有按类型读取。修复后新增/执行日期格式、时间格式、日期时间及 locale built-in 格式测试；相关现状见 `pytest_office_verify_final.log`（43 passed）。

3. **Expected Effect byte bound — preserved raw failure**
   - Command: `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests/test_candidate_verify.py -k expected_effect_budget_is_separate_from_m1_mapping_budget`
   - Result before fix: 1 failed because `max_mapping_bytes=64` rejected a canonical Expected Effect despite the independent Candidate metadata budget being 512 bytes. Full raw output: `failure_expected_effect_uses_mapping_budget.log`.
   - Fix and final result: use separately named `max_expected_effect_bytes`; final proof: `pytest_expected_effect_budget_final.log` (1 passed).

