# Skill Addendum — General Rules

This reference is based on the project's Odoo Playwright manual. The following rules take precedence over any older example in this reference:

- Playwright is the **E2E / real-user simulation layer**. It does not replace Python ORM tests or QUnit/OWL component tests.
- Do not use `networkidle` as a generic Odoo readiness condition. Odoo's OWL client may keep RPC, bus, asset, or other activity alive.
- Do not make a specific JS asset URL such as `web.assets_frontend_lazy.js` a required readiness condition. Wait for visible/enabled business UI instead.
- After a field change or other actualisation trigger, prefer business UI state; only wait for a specific RPC when the business UI cannot provide a reliable signal.
- After Save/Submit, persistence should be verified by reopening/reloading when the requirement is persistence, not merely by checking the current DOM.
- `storage_state` is preferred for reusable authenticated sessions.
- `data-testid` is a UI Test Contract for custom modules and should be designed in TDD.
- Weak-network CDP emulation is Chromium-specific unless the implementation explicitly supports another browser.

## User Simulation Principle

When asked to test a business flow, first identify the user role and business goal, then simulate the smallest realistic browser journey that a real user would perform. Do not use internal ORM knowledge, model names, RPC details, or database state as substitutes for user-visible behavior.


---

# Playwright 测试 Odoo 完整实操流程

## 手册结构

```
docs/odoo-playwright-testing/
├── README.md                # 总入口
├── 01-general.md            # 通用规范（Backend + Portal 共用）
├── 02-backend.md            # Backend 实例
└── 03-portal.md             # Portal 实例
```

---

# 01-general.md：通用规范

## 结论前置

Playwright 是 Odoo 的**最终用户视角验收层**，覆盖 Backend Web Client、Portal、Website。核心原则：

- 用 `storage_state` 保存一次登录态复用
- 等待**业务 UI 状态就绪**，不等 JS asset、不等 `networkidle`
- 字段 actualisation 后**等业务状态稳定**，不硬等 API URL
- Save/Submit 后**刷新验证持久化**

## 测试层级定位

```
                    Odoo Testing
                         │
          ┌──────────────┴──────────────┐
          │                             │
      内部实现测试                    用户行为测试
          │                             │
    ┌─────┴─────┐                ┌──────┴──────┐
    │            │                │             │
 Python ORM   QUnit           Playwright    API/HTTP
    │            │                │
业务规则      OWL组件          Backend Web
JS逻辑        JS状态           Portal
权限          事件             Website
```

Playwright **不负责**验证 `record.create()`、`constraint`、`ACL`、`computed field`。

## 1. 安装

```bash
pip install pytest-playwright
playwright install chromium firefox webkit
```

## 2. 目录结构

```
tests/e2e/
├── conftest.py                      # 全局 fixture
├── .auth/
│   ├── backend.json                 # Backend 登录态
│   └── portal.json                  # Portal 登录态
│
├── backend/                         # 后台 Web Client 测试
│   ├── conftest.py
│   ├── test_contact.py
│   ├── record_panel/
│   │   ├── test_official_mode.py
│   │   ├── test_tab_mode.py
│   │   ├── test_extend_mode.py
│   │   └── test_chatter_layout.py
│   ├── warehouse_vas/
│   │   └── test_vas_flow.py
│   └── global_search/
│       └── test_search.py
│
└── portal/                          # Portal 客户界面测试
    ├── conftest.py
    ├── test_product_list.py
    ├── test_product_detail.py
    ├── test_change_request.py
    ├── test_messages.py
    └── test_responsive.py
```

## 3. 保存登录态

`scripts/save_auth.py`：

```python
from playwright.sync_api import sync_playwright, expect

ODOO_URL = "http://your-odoo:8069"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    # Backend 登录
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(f"{ODOO_URL}/web/login")
    expect(page.get_by_label("Email")).to_be_visible()
    expect(page.get_by_role("button", name="Log in")).to_be_enabled()
    page.get_by_label("Email").fill("admin")
    page.get_by_label("Password").fill("admin")
    page.get_by_role("button", name="Log in").click()
    expect(page).to_have_url("**/odoo/**")
    ctx.storage_state(path="tests/e2e/.auth/backend.json")
    ctx.close()

    # Portal 登录
    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(f"{ODOO_URL}/web/login?redirect=/my")
    expect(page.get_by_label("Email")).to_be_visible()
    page.get_by_label("Email").fill("customer@example.com")
    page.get_by_label("Password").fill("customer_password")
    page.get_by_role("button", name="Log in").click()
    expect(page).to_have_url("**/my**")
    ctx.storage_state(path="tests/e2e/.auth/portal.json")
    ctx.close()

    browser.close()
```

`tests/e2e/.auth/` 加入 `.gitignore`。

## 4. 全局 `conftest.py`

```python
import pytest

ODOO_URL = "http://your-odoo:8069"

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "base_url": ODOO_URL}
```

**不要用 `networkidle`**：Odoo 是持续运行的 OWL 应用，后台可能持续有 RPC、bus、assets 活动。

## 5. 定位器优先级（Selector Contract）

```
1. get_by_role()          # 按钮、链接、文本框
2. get_by_label()         # 表单字段
3. get_by_text()          # 文本内容
4. get_by_test_id()       # 自己的模块 UI
5. locator() + 稳定属性
6. CSS class / DOM 结构   # 尽量避免
```

**自己模块的 UI 主动加 `data-testid`**，形成 UI Test Contract。

## 6. `expect()` 断言

```python
from playwright.sync_api import expect

expect(page.locator(".o_form_view")).to_be_visible()
expect(page.get_by_label("Name")).to_have_value("Acme Corp")
expect(page.locator(".o_notification")).to_contain_text("Saved")
expect(page.get_by_role("button", name="New")).to_be_enabled()
```

## 7. Odoo 最大的坑：actualisation

**现象**：改了一个 Many2one 字段后立刻操作下一个字段，第一个字段被「还原」。

**规范**：等待业务 UI 状态稳定，而不是硬等 API URL。

优先级：

```
① 等待业务状态变化
② 等待明确的 RPC（确实需要时）
③ expect() 等待目标元素状态
④ 最后才考虑 timeout
```

**推荐**：

```python
page.get_by_label("Source Service Line").click()
page.get_by_role("option", name="Assurance axa").click()
expect(page.get_by_role("button", name="Save")).to_be_enabled()
```

**确实需要时**才等待具体 RPC：

```python
page.wait_for_response(lambda r: "lease4.amendment.service_line" in r.url)
```

## 8. Save / Submit 后持久化验证

**仅断言表单值不够**：

```python
# 不够强
expect(page.get_by_role("textbox", name="Name")).to_have_value("Test Company")
```

**更强的 E2E**：

```python
page.get_by_role("button", name="Save").click()
expect(page.get_by_role("button", name="Edit")).to_be_visible()
page.reload()
expect(page.get_by_role("textbox", name="Name")).to_have_value(name)
```

## 9. 弱网模拟

```python
client = page.context.new_cdp_session(page)
client.send("Network.emulateNetworkConditions", {
    "offline": False,
    "latency": 300,
    "uploadThroughput": 100 * 1024 / 8,
    "downloadThroughput": 500 * 1024 / 8,
})
```

## 10. 数据隔离

用唯一标识避免数据库污染：

```python
from uuid import uuid4
name = f"PW Test {uuid4().hex[:8]}"
```

推荐在独立测试数据库上跑 CI，跑完销毁。

## 11. 运行与 CI

```bash
# 调试：带界面
pytest tests/e2e/ --headed --slowmo 300

# CI：多浏览器
pytest tests/e2e/ --browser chromium --browser firefox --browser webkit

# 失败保留 trace 和截图
pytest tests/e2e/ --tracing retain-on-failure --screenshot only-on-failure
```

## 12. 调试技巧

```bash
# Codegen
playwright codegen http://your-odoo:8069/odoo
playwright codegen http://your-odoo:8069/my

# REPL
python -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.launch(headless=False)
page = b.new_page()
page.goto('http://your-odoo:8069/my/products')
input()
"
```

## 13. 与 CC / HVR 对接

```
SRS
 ↓
TDD（定义 data-testid 契约）
 ↓
Implementation
 ↓
Playwright E2E（Backend + Portal 分别）
 ↓
HVR
```

---

