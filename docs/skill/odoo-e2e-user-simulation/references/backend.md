# Skill Addendum — Backend User Simulation

Use this reference for Odoo Backend Web Client E2E tests. The test should represent a real employee/operator/admin workflow and verify business-visible outcomes.

Precedence rules:
- Prefer role/label/text/test-id locators over CSS structure.
- Treat `data-testid` as the explicit UI Test Contract for custom Backend UI.
- For Many2one actualisation, wait for the resulting business UI state rather than a generic network condition.
- For Extend Preview + Chatter + responsive layout, verify layout relationships from the user's viewport perspective.
- Save/Submit flows should verify persistence when the requirement depends on stored data.


---

# 02-backend.md：Backend 实例

## 1. Backend `conftest.py`

`tests/e2e/backend/conftest.py`：

```python
import pytest
from playwright.sync_api import expect

@pytest.fixture
def odoo_page(browser, browser_context_args):
    """Backend：已登录的 Odoo 后台页面"""
    ctx = browser.new_context(
        **browser_context_args,
        storage_state="tests/e2e/.auth/backend.json",
    )
    page = ctx.new_page()
    yield page
    ctx.close()

@pytest.fixture
def backend_home(odoo_page):
    """进入后台首页，等待可操作"""
    odoo_page.goto("/odoo")
    expect(odoo_page.get_by_role("button", name="New")).to_be_enabled()
    return odoo_page
```

## 2. Backend `data-testid` 契约

```html
<!-- Record Panel -->
<div class="o_wd_preview_panel" data-testid="m2o-preview-panel">
<button data-testid="m2o-preview-close">
<div data-testid="m2o-preview-record">

<!-- Warehouse VAS -->
<div data-testid="vas-service-list">
<button data-testid="vas-add-service">
<div data-testid="vas-summary">

<!-- Global Search -->
<input data-testid="global-search-input">
<div data-testid="global-search-results">
```

## 3. 录入操作

**文本字段**：

```python
page.get_by_label("Customer").fill("Acme Corp")
page.get_by_role("textbox", name="Phone").fill("+3112345678")
```

**下拉选择（Many2one）**：

```python
page.get_by_label("Salesperson").click()
page.wait_for_selector(".o_field_many2one .o_dropdown")
page.get_by_role("option", name="John Doe").click()
```

**按钮**：

```python
page.get_by_role("button", name="Save").click()
page.get_by_role("button", name="New").click()
page.get_by_role("button", name="Confirm").click()
```

**文件上传**：

```python
# 方式一：直接设置隐藏 input
page.locator("input[type='file']").set_input_files("./photo.jpg")

# 方式二：拦截文件选择器
with page.expect_file_chooser() as fc_info:
    page.get_by_title("Upload Image").click()
fc_info.value.set_files("./photo.jpg")
```

## 4. 完整示例：创建联系人

`tests/e2e/backend/test_contact.py`：

```python
from playwright.sync_api import Page, expect
from uuid import uuid4

def test_create_contact(backend_home: Page):
    name = f"PW Test {uuid4().hex[:8]}"

    backend_home.goto("/odoo/contacts")
    expect(backend_home.locator(".o_list_view")).to_be_visible()

    backend_home.get_by_role("button", name="New").click()
    expect(backend_home.locator(".o_form_view")).to_be_visible()

    backend_home.get_by_role("textbox", name="Name").fill(name)
    backend_home.get_by_role("textbox", name="Phone").fill("+3112345678")

    backend_home.get_by_role("button", name="Save").click()
    expect(backend_home.get_by_role("button", name="Edit")).to_be_visible()

    backend_home.reload()
    expect(backend_home.get_by_role("textbox", name="Name")).to_have_value(name)
```

## 5. Record Panel 布局测试

`tests/e2e/backend/record_panel/test_chatter_layout.py`：

```python
from playwright.sync_api import Page, expect

def test_extend_preview_with_chatter_wide(odoo_page: Page):
    """CC-04：Wide 布局下 Chatter 在业务表单下方"""
    odoo_page.set_viewport_size({"width": 1920, "height": 1080})
    # 打开 Sale Order，触发 Many2one extend preview
    preview = odoo_page.get_by_test_id("m2o-preview-panel")
    chatter = odoo_page.locator(".o_chatter")
    expect(preview).to_be_visible()
    assert chatter.bounding_box()["y"] > preview.bounding_box()["y"]

def test_extend_preview_with_chatter_narrow(odoo_page: Page):
    """CC-04：Narrow 布局下三者垂直排列"""
    odoo_page.set_viewport_size({"width": 900, "height": 900})
    # 打开 Sale Order，触发 Many2one extend preview
    preview = odoo_page.get_by_test_id("m2o-preview-panel")
    chatter = odoo_page.locator(".o_chatter")
    expect(preview).to_be_visible()
    assert chatter.bounding_box()["y"] > preview.bounding_box()["y"]

def test_preview_close_button(odoo_page: Page):
    """关闭 Preview 面板"""
    # 打开 extend preview
    odoo_page.get_by_test_id("m2o-preview-close").click()
    expect(odoo_page.get_by_test_id("m2o-preview-panel")).not_to_be_visible()
```

## 6. Warehouse VAS 流程

`tests/e2e/backend/warehouse_vas/test_vas_flow.py`：

```python
from playwright.sync_api import Page, expect

def test_add_vas_service(odoo_page: Page):
    """添加增值服务"""
    odoo_page.goto("/odoo/inventory")
    # 进入 VAS 服务列表
    odoo_page.get_by_role("button", name="New").click()

    odoo_page.get_by_label("Service Type").click()
    odoo_page.get_by_role("option", name="Packaging").click()
    expect(odoo_page.get_by_role("button", name="Save")).to_be_enabled()

    odoo_page.get_by_label("Quantity").fill("10")
    odoo_page.get_by_role("button", name="Save").click()
    expect(odoo_page.get_by_role("button", name="Edit")).to_be_visible()
```

## 7. Global Search

`tests/e2e/backend/global_search/test_search.py`：

```python
from playwright.sync_api import Page, expect

def test_global_search_finds_record(backend_home: Page):
    backend_home.get_by_test_id("global-search-input").fill("Acme")
    backend_home.keyboard.press("Enter")
    expect(backend_home.get_by_test_id("global-search-results")).to_be_visible()
    expect(backend_home.get_by_text("Acme Corp")).to_be_visible()
```

---

