# IHR-GS-FINAL-ACCEPTANCE

## 状态

CC-011 已批准冻结并进入实施。

## 首轮实施记录

- 建立 SRS/TDD/TV/CC 统一最终验收门禁；
- 执行 `python -m compileall`；
- 执行 `git diff --check`；
- 执行 Odoo 模块升级和测试；
- 执行 TV-06 时间、多值、部分失败回归；
- 汇总既有 CC-001 至 CC-010 的 ATR/HVR/IHR 证据；
- 对未完成的多浏览器、真实生产 Search Service 错误注入、隔离数据库回滚演练保持 `PARTIAL`，未伪造为通过。

## 复现命令

```bash
./venv/bin/python -m compileall -q mymodules/wd_global_search
./venv/bin/python odoo-bin -c odoo.conf --http-port=8092 \
  -d odoo18ce -u wd_global_search --test-enable \
  --stop-after-init --log-level=test
./venv/bin/python odoo-bin shell -c odoo.conf \
  -d wd_tv_gs01_20261002_100k --no-http \
  < mymodules/wd_tv_global_search/tv_06_multi_value_time_failure/scripts/run.py
```
