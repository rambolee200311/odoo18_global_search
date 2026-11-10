# ATR-M2-CB-01 — Responses Provider Adapter

**当前关闭状态（2026-11-06）：**负责人已接受本 CC；`Contract Verified`；`Integration Passed`；`Final Accepted`。

以下 §1–§6 保留初始本地实施阶段的原始结论；其中当时的 `Integration Pending / NOT ACCEPTED` 是真实历史状态，现由 §7 的单独授权真实集成证据更新，不予删除或改写。

**执行结论：**`Contract Verified`（本地 Adapter / 离线 Mock 范围）

**集成结论：**`Integration Pending`

**最终接受：**`NOT ACCEPTED` — 本 CC 仍缺本授权范围外的真实 Provider 文件闭环证据

**授权：**负责人于 2026-11-06 明确批准冻结 CC v0.2 并开始实施；按 `CC-M2-CB-01_Responses_Provider_Adapter_v0.2.md` 第 12 节的本地/离线边界执行。

## 1. 基线、范围与变更

开始时：branch `main`，HEAD `f9801fca76f7c248a9cc823c583138ab0191b978`，工作区 `main...origin/main [ahead 1]`，存在多个既有未跟踪文档、报告和证据目录；tracked diff 为空。它们均予保留。未执行 Git stage、commit、push、reset 或 clean。

环境：Python 3.11.9；OpenAI Python SDK 2.54.0；pytest 8.4.2。读取本地 SDK 类型签名以确认可用接口；未创建带凭据的 SDK client、未读取环境变量或 Odoo Provider 凭据、未发出网络请求。

实际新增/修改仅限 CC 允许范围：

- `docs/implementation/CC-M2-CB-01_Responses_Provider_Adapter_v0.2.md`：登记冻结及有界 Coding Authorization。
- `docs/implementation/IHR-M2-CB-01.md`、本报告：执行记录。
- `mymodules/odoo-llm/llm_openai/services/__init__.py`、`services/responses_adapter.py`：独立的纯 Python Adapter。
- `mymodules/odoo-llm/llm_openai/tests/test_responses_adapter.py`：SDK Mock/故障注入回归。

未修改 `openai_provider.py`、Addon `__init__.py`、Manifest、`office_engine_m2`、Usage ORM/服务、冻结 SRS/TDD/Implementation Plan 或历史 TV 文件。既有 Chat Completions 文件与 HEAD 相同；运行时 Chat Completions 行为未在本轮启动 Odoo 测试，见 §5。

## 2. 实现与架构证据

`ResponsesAdapter.execute()` 接收上层已配置的 SDK client、由调用方策略限定的模型、实际 XLSX bytes、指令和资源限制。Adapter 不创建客户端、不接收 Key、不访问业务/会话权限，也不自动替换 Provider 或模型。

每次调用使用 `client.with_options(timeout=..., max_retries=0)`，以 inline XLSX data URL 调用 Responses API + Code Interpreter；容器请求禁用网络并采用显式内存、输出 Token 和文件大小限制。响应只接受恰好一个 `.xlsx` container citation；缺失、多文件、或容器 ID 冲突都不会猜测目标文件。候选内容通过 SDK 流式接口下载，受输出字节上限约束。

最低候选检查只验证 ZIP CRC、必要 OOXML 包部件、条目数及解压大小。它不读取单元格、不比较公式/样式/非目标区域、不判断自然语言意图；这些仍属于后续 CB-03 Validator。Candidate bytes 只保存在进程内结果对象；`to_dict()` 返回 JSON 安全元数据，不序列化文件字节。

连接/超时且没有 Response 时返回 `indeterminate`，不自动重试；已收到 Response 但文件下载失败返回 `failed` 并保留已知 Response/Container/File 标识。容器清理是一次最佳努力删除：成功记 `completed`，失败记 `cleanup_pending`；已发起请求但没有可用容器标识时记 `unknown`。若上层要求保证远端清理，Adapter 在上传前以 `blocked` 拒绝，因为当前组件不能给出该保证。

Usage 只保留规定 token 字段；数值零原样保留，`False`、负数、非整数和缺失值成为未知，不改写为零。异常分类不包含 Provider 原始消息、响应 body、Prompt、文件字节或凭据。

通用性自查：执行路径只依赖 XLSX/Responses 协议和显式资源策略，没有 Odoo 模型、客户、模板名称、表格坐标或业务字段分支。合成测试额外用不同工作表名验证 Adapter 不依赖 `Inventory` 等固定 Sheet。没有新 Canonical Document Operation，也没有绕过本地 Validator 的生产接入路径。

## 3. 实际自动化结果

### 静态检查

执行命令：

```text
venv/bin/python -m py_compile \
  mymodules/odoo-llm/llm_openai/services/__init__.py \
  mymodules/odoo-llm/llm_openai/services/responses_adapter.py \
  mymodules/odoo-llm/llm_openai/tests/test_responses_adapter.py
```

结果：退出码 0。

执行源文件 trailing whitespace 扫描：修改文件 `none`。执行 `git diff --check`：无输出；新增文件由单独空白扫描覆盖。

### Python Mock 测试

第一次直接执行 `venv/bin/pytest -q mymodules/odoo-llm/llm_openai/tests/test_responses_adapter.py` 时，pytest 因目录位于 Odoo addon 包内而导入了现有 `llm_openai/__init__.py`，随后 Odoo 的 addon 模块命名断言失败；显示为 20 个 setup/collection errors，尚未运行测试函数。这是测试加载上下文错误，不计为功能断言失败，也保留在此记录。

之后使用以下隔离测试入口：在 pytest collection 前以临时 `ModuleType` namespace stub 遮蔽 addon 父包初始化，再导入同一测试文件。该做法不改仓库文件、不创建 Odoo registry、不访问 DB，测试体仍直接导入实际 Adapter 源码：

```python
import sys, types
from pathlib import Path
root = Path.cwd()
addon = root / "mymodules/odoo-llm/llm_openai"
for name, path in {
    "llm_openai": addon,
    "llm_openai.tests": addon / "tests",
    "mymodules": root / "mymodules",
    "mymodules.odoo-llm": root / "mymodules/odoo-llm",
    "mymodules.odoo-llm.llm_openai": addon,
    "mymodules.odoo-llm.llm_openai.tests": addon / "tests",
}.items():
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module
import pytest
raise SystemExit(pytest.main([
    "--import-mode=importlib", "-q", "--tb=short",
    str(addon / "tests/test_responses_adapter.py"),
]))
```

最终复跑实际结果：`25 passed in 0.54s`，退出码 0。测试覆盖：请求形状、inline XLSX 编码、网络关闭、模型策略、输入 SHA/大小/ZIP 门禁、重试禁用、响应/工具/文件 ID、流式下载及 SHA、候选容器检查、openpyxl 文件回读、不同 Sheet 名、非空/歧义/损坏/不完整响应、超时/连接不确定、HTTP 错误、下载失败、大小上限、cleanup pending/unknown、Usage 的零值与非法值语义、无 Odoo 依赖/无执行器。

独立回读是在测试进程内对 Mock 返回的 XLSX bytes 使用 `openpyxl` 和 `zipfile` 完成。核对了目标值、未改记录、公式文本、第二张表和 XLSX ZIP 完整性。这里的候选由测试夹具生成后交给 Mock；它不是模型编辑产物，也不是 Provider E2E 证据。公式没有被重新计算。

## 4. 测试级别与结论分栏

| 验收层 | 结果 | 证据/限制 |
|---|---|---|
| Python 语法检查 | PASS | 上述 `py_compile`。 |
| SDK Mock 契约测试 | PASS | 25 项通过；无真实 HTTP。 |
| 纯 Python 合成 XLSX 回读 | PASS（Mock 候选） | `openpyxl` 读取值/公式并用 `zipfile.testzip()` 检查；不是 Provider 生成文件。 |
| 真实 OpenAI Provider / Responses | NOT RUN | 本次授权是本地/离线范围，没有读取凭据或调用 API。历史 Phase 1A-2 成功仅为先前一次 TV 证据；本轮不复用为当前 Adapter Integration PASS。 |
| Odoo TransactionCase / ORM / Usage 集成 | NOT RUN | 未启动服务、DB 或测试 registry；本轮没有 Odoo 消费方。 |
| Browser / Preview / Finalize / Attachment | NOT RUN | 在本 CC 及本次 Coding Authorization 范围外。 |
| 生产可用性 | NOT ACCEPTED | 没有真实 Provider Adapter 接入、独立 Validator/版本服务/调用方门禁或端到端验收。 |

本地 Adapter 范围为 `Contract Verified`。真实集成为 `Integration Pending`；根据 CC 定义，不能标记 `Integration Passed` 或 `Final Accepted`。

## 5. 留存问题与边界

1. 本 Adapter 尚未由真实 Odoo Provider client 调用；`openai_provider.py` 的配置凭据未读取，生产调用路径未接入。需另行授权 SRS/数据政策处理、真实 Provider 请求预算及 Runtime Validation 后，才能进行集成验收。
2. 既有 Chat Completions 源文件未修改，且新 Adapter 不改 Provider 调用链；但本轮没有实际执行 `content`、`tool_calls` 或 streaming 消费方回归，故行为级兼容性仍 `UNVERIFIED`。
3. 远端 Code Interpreter 容器清理仅为一次最佳努力；要求硬性删除保证的调用策略在上传前会被拒绝。`store=False` 避免创建可持久检索的 Response，但不是远端数据处理政策的替代。
4. `candidate_received` 只表示得到非空、通过有界 ZIP/OOXML 最低检查的字节。单元格效果、公式、格式、结构、非目标 Diff、用户意图和 Preview/Finalize 均未在本 CC 本地 Adapter 中验证。
5. 公式重算、复杂 XLSX 功能保真、浏览器附件显示和错误后端到端恢复仍未验证。

## 6. 工作区状态

完成后 branch/HEAD 仍为 `main` / `f9801fca76f7c248a9cc823c583138ab0191b978`；工作树仅在开始时已存在的未跟踪材料基础上增加本报告、IHR 更新、CC 冻结记录和本 CC 新增 Service/测试文件。未执行任何 Git 暂存、提交、推送、清理或重置。`openai_provider.py`、Addon 顶层注册、Manifest、Usage ORM/服务和 M2 业务代码未修改。

## 7. Separately Authorized Real Provider Integration and Closeout Addendum — 2026-11-06

负责人后续单独授权最多 10 次顺序 Responses API 创建请求，使用现有 OpenAI Provider 配置、固定模型 `gpt-5.6-luna` 和纯合成 XLSX。实际使用 1 次请求；未并发、未重试、未切换模型。此次范围仅验证 Adapter Provider 集成与 Chat Completions 兼容，不接入生产路径。

### 7.1 实际 Provider 调用

- 通过只读 Odoo ORM 选择唯一 active/default `gpt-5.6-luna` 模型及 OpenAI Provider，确认 API base 为获批的 `https://api.openai.com/v1`。通过既有 `provider.client` 安全工厂取得 SDK client；Key 未读取输出、打印或持久化。
- 真实调用路径：`run_real_provider.py` → 既有 Provider ORM client → `ResponsesAdapter.execute()` → Responses API + Hosted Code Interpreter。请求含 `store=False`、`max_retries=0`、120 秒超时、4,000 输出 token、2 MB 输入/输出上限、1 GB 容器和禁网策略。
- Adapter 返回 `candidate_received`，下载真实 Provider XLSX 字节，最小 ZIP/OOXML 检查通过；容器清理状态 `completed`。
- 请求计数：1/10。Responses 创建耗时 24,919 ms；本地端到端计时 24.957 秒。
- Response ID：`resp_08d257b63d57f6c1016aed953b25b887d288a414dec2c8ed93`；Request ID：`req_2d5daa2765b44dc2bcd8e3f1207d3a55`；Tool ID：`ci_08d257b63d57f6c1016aed954295f887d2a29c3f8e9a36db5e`；Container ID：`cntr_6aed953e1e908191908c4929d71f46830e6895d01718b496`；container file ID：`cfile_6aed954637888191ac5bf1f739cee762`。

### 7.2 文件字节与独立回读

合成输入 5,563 bytes，输入 SHA-256 `756a1ffa467e24da035952cbbf63c5d1c0ad8d47bf53bf17a4b8e4613e95d82b`。Provider 下载候选 5,567 bytes，输出 SHA-256 `9b2a7c48928737a0a8ee7878770e7206bafbc394f2631a764e1b0ece55f8266f`。

独立脚本 `verify_candidate.py` 用 `zipfile` 与 `openpyxl` 重新读取实际下载文件，结果 `PASS`：

- `Inventory!B2` 是整数 15；`Inventory!C2 == "KEEP"`。
- `Inventory!D2` 仍是公式文本 `=B2*2`；未声称公式已重算。
- Inventory 第二条记录未改变；`Notes` 工作表数据未改变。
- 工作表名称/顺序、已填单元格类型、数字格式和样式保持；差异仅 `Inventory!B2`。
- 输入与输出 XLSX ZIP 容器均通过完整性检查。

### 7.3 Usage、费用可见性及清理

Provider usage：2,149 input tokens、693 output tokens（其中 331 reasoning tokens）、2,842 total tokens。按本次执行时官方 token/tool/container 单价计算的本地估值为 USD 0.0337614；这是估算，不是账单，账户实际费用 `UNVERIFIED`，也不是账户级硬预算保证。此次授权未设费用硬上限；实际请求数未超过 10 次。SDK 自动重试为 0。请求使用 `store=False`；Hosted Code Interpreter container 删除成功。没有单独删除 Response/File 对象，因为 Response 未存储，输出为容器文件并随容器删除。

### 7.4 Chat Completions 兼容性

`openai_provider.py` 与 HEAD 无差异。将三项 SDK Mock 兼容测试追加至允许的 `test_responses_adapter.py`，用窄 Odoo import stubs 导入实际未改动 Provider 源码，不创建 Odoo Registry、不连接数据库、不发起 Chat Completions 网络请求。覆盖非流式 `content` 和 `tool_calls` 的旧消费者结构、Streaming 内容/工具调用拼装，以及现有 OpenAI client 构造器的 `api_key`/`api_base` 参数契约（仅用合成占位值）。结果为方法级 Mock `PASS`；Provider ORM 配置读取/实际 Odoo Runtime 集成未测试，因此不声称 Odoo Integration PASS。

### 7.5 本地验证与准确状态

本次 `py_compile` 命令覆盖 Adapter、测试文件和两个证据脚本，退出码 0。使用 ATR §3 所列隔离 pytest namespace shim 对同一测试文件运行，最新结果为 **28 passed in 0.56s**，退出码 0；其中原 25 项 Adapter SDK Mock 回归和新加 3 项 Chat Completions 方法级兼容测试均通过。历史直接 pytest addon collection/setup 错误仍保留在 §3，没有删除或改写。

没有运行 Odoo TransactionCase、Preview/Finalize/Attachment、Browser E2E、部署或业务数据访问；没有验证复杂工作簿保真、公式计算或长期 Provider 可靠性。`openai_provider.py` 与当前 HEAD 一致，未修改生产 Provider、M2 业务代码或冻结设计基线。

**执行时关闭建议（接受前状态）：**Adapter Mock 契约 `Contract Verified`；合成数据 Responses/Code Interpreter/Adapter 下载及独立 XLSX 回读 `Integration Passed`；Chat Completions 方法级兼容回归 `PASS (Mock)`。当时提交 `READY FOR FINAL ACCEPTANCE`。

### 7.6 负责人最终接受

2026-11-06，项目负责人明确批准关闭 CC-M2-CB-01。按 CC v0.2 §8、§9 的关闭条件，记录本 CC 为 **`Final Accepted`**。该接受仅关闭 CB-01，不代表生产发布、M2 阶段整体验收或 CB-02 自动获准实施。CB-02 需独立契约冻结及 Coding Authorization。
