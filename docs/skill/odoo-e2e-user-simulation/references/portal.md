# Skill Addendum — Portal User Simulation

Use this reference for Portal HTML/QWeb + JS/OWL + RPC E2E tests.

Precedence rules:
- Portal E2E can and should exercise JS/OWL behavior through the browser; QUnit remains appropriate for isolated component logic.
- Do not hard-code arbitrary record IDs such as `/my/products/123`. Use controlled fixture data, a known created record, or a data-driven locator/path.
- Test custom OWL dropdowns through their user-visible interaction, not `select_option()` unless the control is a native `<select>`.
- When using `bounding_box()`, handle a possible `None` result after asserting visibility/attachment.
- Upload, submit, validation, chatter, responsive, and weak-network flows should be expressed as user journeys with business-visible assertions.
- Chromium-only CDP network emulation must be explicitly marked as such.


---

# 03-portal.md：Portal 实例

## 1. Portal `conftest.py`

`tests/e2e/portal/conftest.py`：

```python
import pytest
from playwright.sync_api import expect

@pytest.fixture
def portal_page(browser, browser_context_args):
    """Portal：已登录的客户 Portal 页面"""
    ctx = browser.new_context(
        **browser_context_args,
        storage_state="tests/e2e/.auth/portal.json",
    )
    page = ctx.new_page()
    yield page
    ctx.close()

@pytest.fixture
def portal_home(portal_page):
    portal_page.goto("/my")
    expect(portal_page.locator(".o_portal_my_home")).to_be_visible()
    return portal_page

@pytest.fixture
def portal_products(portal_page):
    portal_page.goto("/my/products")
    expect(portal_page.get_by_test_id("product-list")).to_be_visible()
    return portal_page

@pytest.fixture
def portal_product_detail(portal_page):
    portal_page.goto("/my/products/123")
    expect(portal_page.get_by_test_id("product-detail")).to_be_visible()
    return portal_page
```

## 2. Portal `data-testid` 契约

```html
<!-- 列表页 -->
<div data-testid="product-list">
<input data-testid="product-search-input">
<select data-testid="product-category-filter">
<div data-testid="product-pagination">
<div data-testid="product-row" data-product-id="123">

<!-- 详情页 -->
<div data-testid="product-detail">
<div data-testid="product-tabs">
<div data-testid="product-attachments">
<div data-testid="product-actions">

<!-- 修改申请 -->
<div data-testid="change-request-form">
<input data-testid="change-request-name">
<textarea data-testid="change-request-reason">
<input data-testid="change-request-attachment" type="file">
<button data-testid="change-request-submit">
<div data-testid="success-message">
<div data-testid="error-message">

<!-- Chatter -->
<div data-testid="portal-chatter">
<textarea data-testid="chatter-input">
<button data-testid="chatter-send">
<div data-testid="chatter-message">
```

## 3. 列表交互：搜索 / 过滤 / 分页

`tests/e2e/portal/test_product_list.py`：

```python
from playwright.sync_api import Page, expect

def test_search_product(portal_products: Page):
    search = portal_products.get_by_test_id("product-search-input")
    search.fill("Product A")
    search.press("Enter")
    expect(portal_products.get_by_test_id("product-row")).to_have_count(1)
    expect(portal_products.get_by_text("Product A")).to_be_visible()

def test_filter_by_category(portal_products: Page):
    portal_products.get_by_test_id("product-category-filter").select_option("Electronics")
    expect(portal_products.get_by_test_id("product-row")).not_to_have_count(0)

def test_pagination(portal_products: Page):
    first = portal_products.get_by_test_id("product-row").first.text_content()
    portal_products.get_by_test_id("product-pagination").get_by_role("link", name="Next").click()
    expect(portal_products.get_by_test_id("product-row")).to_be_visible()
    second = portal_products.get_by_test_id("product-row").first.text_content()
    assert first != second

def test_open_detail_from_list(portal_products: Page):
    portal_products.get_by_test_id("product-row").first.click()
    expect(portal_products.get_by_test_id("product-detail")).to_be_visible()
```

## 4. 详情交互：Tab / 附件

`tests/e2e/portal/test_product_detail.py`：

```python
from playwright.sync_api import Page, expect

def test_switch_tabs(portal_product_detail: Page):
    tabs = portal_product_detail.get_by_test_id("product-tabs")
    tabs.get_by_role("tab", name="Attachments").click()
    expect(portal_product_detail.get_by_test_id("product-attachments")).to_be_visible()
    tabs.get_by_role("tab", name="History").click()
    expect(portal_product_detail.get_by_test_id("product-history")).to_be_visible()

def test_download_attachment(portal_product_detail: Page):
    with portal_product_detail.expect_download() as download_info:
        portal_product_detail.get_by_test_id("product-attachments").get_by_role("link").first.click()
    assert download_info.value.suggested_filename.endswith(".pdf")
```

## 5. 修改申请：表单 + 上传 + 提交

`tests/e2e/portal/test_change_request.py`：

```python
from playwright.sync_api import Page, expect
from uuid import uuid4

def test_submit_change_request_with_attachment(portal_product_detail: Page):
    unique = uuid4().hex[:8]
    new_name = f"Product A Updated {unique}"

    # 打开表单
    portal_product_detail.get_by_role("button", name="Request Change").click()
    expect(portal_product_detail.get_by_test_id("change-request-form")).to_be_visible()

    # 填写字段
    portal_product_detail.get_by_test_id("change-request-name").fill(new_name)
    portal_product_detail.get_by_test_id("change-request-reason").fill(
        "Need to update product name for compliance"
    )

    # 上传附件
    portal_product_detail.get_by_test_id("change-request-attachment").set_input_files(
        "./fixtures/compliance.pdf"
    )

    # 提交
    portal_product_detail.get_by_test_id("change-request-submit").click()
    expect(portal_product_detail.get_by_test_id("success-message")).to_contain_text(
        "submitted", timeout=15000
    )

    # 刷新验证持久化
    portal_product_detail.reload()
    expect(portal_product_detail.get_by_text(new_name)).to_be_visible()

def test_validation_error_on_empty_form(portal_product_detail: Page):
    portal_product_detail.get_by_role("button", name="Request Change").click()
    portal_product_detail.get_by_test_id("change-request-submit").click()
    expect(portal_product_detail.get_by_test_id("error-message")).to_be_visible()
    expect(portal_product_detail.get_by_test_id("change-request-form")).to_be_visible()

def test_cancel_change_request(portal_product_detail: Page):
    portal_product_detail.get_by_role("button", name="Request Change").click()
    portal_product_detail.get_by_test_id("change-request-name").fill("Should Not Save")
    portal_product_detail.get_by_role("button", name="Cancel").click()
    expect(portal_product_detail.get_by_test_id("change-request-form")).not_to_be_visible()
    portal_product_detail.reload()
    expect(portal_product_detail.get_by_text("Should Not Save")).not_to_be_visible()
```

## 6. Chatter 消息

`tests/e2e/portal/test_messages.py`：

```python
from playwright.sync_api import Page, expect
from uuid import uuid4

def test_send_message_on_portal(portal_product_detail: Page):
    message = f"Portal message {uuid4().hex[:8]}"
    portal_product_detail.get_by_test_id("chatter-input").fill(message)
    portal_product_detail.get_by_test_id("chatter-send").click()
    expect(portal_product_detail.get_by_test_id("chatter-message")).to_contain_text(
        message, timeout=10000
    )
    portal_product_detail.reload()
    expect(portal_product_detail.get_by_test_id("chatter-message")).to_contain_text(message)
```

## 7. 响应式布局

`tests/e2e/portal/test_responsive.py`：

```python
from playwright.sync_api import Page, expect

def test_mobile_layout_order(portal_page: Page):
    portal_page.set_viewport_size({"width": 390, "height": 844})
    portal_page.goto("/my/products/123")
    detail = portal_page.get_by_test_id("product-detail").bounding_box()
    actions = portal_page.get_by_test_id("product-actions").bounding_box()
    assert actions["y"] > detail["y"]

def test_desktop_layout(portal_page: Page):
    portal_page.set_viewport_size({"width": 1440, "height": 900})
    portal_page.goto("/my/products/123")
    detail = portal_page.get_by_test_id("product-detail").bounding_box()
    actions = portal_page.get_by_test_id("product-actions").bounding_box()
    assert actions["x"] > detail["x"]

def test_mobile_menu_toggle(portal_page: Page):
    portal_page.set_viewport_size({"width": 390, "height": 844})
    portal_page.goto("/my")
    portal_page.get_by_role("button", name="Menu").click()
    expect(portal_page.get_by_test_id("mobile-nav")).to_be_visible()
```

## 8. 弱网上传

```python
def test_upload_slow_network(portal_product_detail: Page):
    client = portal_product_detail.context.new_cdp_session(portal_product_detail)
    client.send("Network.emulateNetworkConditions", {
        "offline": False,
        "latency": 300,
        "uploadThroughput": 100 * 1024 / 8,
        "downloadThroughput": 500 * 1024 / 8,
    })

    portal_product_detail.get_by_role("button", name="Request Change").click()
    portal_product_detail.get_by_test_id("change-request-attachment").set_input_files(
        "./fixtures/large_photo.jpg"
    )
    portal_product_detail.get_by_test_id("change-request-submit").click()
    expect(portal_product_detail.get_by_test_id("upload-progress")).to_be_visible()
```

---

# 与 CC / HVR 对接

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

| HVR 项目 | Playwright |
|---|---|
| Backend Extend Preview 显示 | 自动 |
| Backend Chatter 在底部 | 自动 |
| Backend Wide / Narrow layout | 自动 |
| Backend Save 后状态 | 自动 |
| Portal 搜索 / 过滤 / 分页 | 自动 |
| Portal Tab / 附件下载 | 自动 |
| Portal 修改申请提交 | 自动 |
| Portal 空表单校验 | 自动 |
| Portal 取消表单 | 自动 |
| Portal Chatter 消息 | 自动 |
| Portal 响应式布局 | 自动 |
| Portal 弱网上传反馈 | 自动 |
| 人工视觉检查 | 保留 |

---

# 一句话总结

**1 个手册，3 部分**：通用规范（01）+ Backend 实例（02）+ Portal 实例（03）。通用内容只写一遍，Backend 和 Portal 的差异放在各自章节。用 `storage_state` 复用登录态；等业务状态就绪；actualisation 后等业务 UI 稳定；Save/Submit 后刷新验证持久化；用 `data-testid` 契约定位；用唯一标识隔离数据。
