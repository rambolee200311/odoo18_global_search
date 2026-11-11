# CC-M2-CB-08 Evidence Index

| 证据 | 内容 / 层级 |
|---|---|
| `ATR-CC08-T2-T3-focused-final.log` | 最终两项 Odoo TransactionCase：2 个 Starting Test，进程退出码 0 |
| `T2-T3-result.json` | T2/T3 测试名、合成记录 ID、断言范围、零 Provider 调用和回滚说明 |
| `T1-real-provider-result-attempt-01.json` | 一次真实 Responses API / Hosted Code Interpreter 请求及响应 ID、请求 ID、文件 ID、Usage、Provider Candidate 元数据 |
| `T1-real-provider-shell-rerun.log` | 真实 Provider Odoo shell 调用原始日志；首次后处理断言触发前事务回滚 |
| `T1-input.xlsx` | 合成输入工作簿 |
| `T1-candidate.xlsx` | 真实 Provider 返回 XLSX |
| `T1-corrected-readback.json` | ZIP、XLSX、值、公式、工作表、目标格式、非目标 style ID 和 SHA 独立回读 |
| `T1-real-provider-result.json` | 首轮脚本完整结果，保留其 StyleProxy 相等断言失败事实 |
| `T1-replay-accept-result.json` | 精确同 SHA Provider 字节经测试 ReplayAdapter 进入正式 Candidate/Validator/Accept；0 Provider request；Candidate 3109，Partial 保持，Current/Last Valid/Revision 及 SHA |
| `T1-replay-accept-shell-verified.log` | 正式 Accept 字节回放 Odoo shell 日志；结束时回滚测试记录 |
| `T1-accepted-v1.xlsx` | 接受回放导出的 XLSX；字节 SHA 与真实 Provider 输出相同 |
| `ATR-CC08-T2-T3*.log` | 早期失败尝试与最终定向运行，均保留，不以早期调试日志替代最终证据 |
| `ATR-CC08-retriever-module.log` | 旧 Retriever 测试模块尝试；其失败边界已在 ATR 说明 |
| `t1_real_provider_shell.py` | 单次真实 Provider T1 shell runner（不记录密钥） |
| `t1_replay_accept_shell.py` | 零 Provider 请求的输出字节回放与正式 Accept runner |
| `T4-baseline.json` | HEAD、worktree dirty 状态、源码/测试 SHA、环境和调用证据基线；不含密钥 |
