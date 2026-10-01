---
name: odoo-e2e-user-simulation
description: Odoo 18 E2E user simulation and Playwright testing skill. Use for designing, implementing, reviewing, debugging, or validating real-user browser flows in Odoo Backend Web Client and Portal, including OWL/JS, RPC actualisation, persistence, responsive layouts, uploads, Chatter, weak-network scenarios, and HVR acceptance mapping. Treat Playwright as the user-facing E2E layer alongside Python ORM tests and QUnit/OWL tests.
---

# Odoo E2E User Simulation & Playwright Testing

## Purpose

Simulate how a real Odoo user completes a business goal in a browser, then verify the business-visible result and persistence. The skill covers both Backend Web Client and Portal.

## Core testing model

Use the correct layer:

- **Python ORM / server tests**: business logic, constraints, ACLs, computed fields, model behavior.
- **QUnit / OWL tests**: isolated JavaScript/OWL component behavior.
- **Playwright E2E**: real browser journeys across UI + JS/OWL + RPC + Odoo backend, including responsive and failure behavior.

Do not use Playwright as a replacement for lower-level tests, and do not use ORM/database assertions as a substitute for user-visible E2E behavior.

## User simulation workflow

For every requested E2E scenario:

1. Identify the **user role**.
2. Identify the **business goal**.
3. Identify the **realistic browser journey**.
4. Execute the journey with Playwright.
5. Wait for **business UI readiness**, not generic network quietness.
6. Assert the visible business outcome.
7. If the requirement is persistent, reload/reopen and verify persistence.
8. Capture trace/screenshot on failure.
9. Map the scenario to the relevant HVR acceptance item when applicable.

Think from the user's perspective: the user knows what they want to accomplish, not Odoo's internal model, RPC, DOM structure, or database implementation.

## Odoo readiness and actualisation

### Never use as a generic rule

- `page.wait_for_load_state("networkidle")`
- waiting for a particular Odoo JS asset such as `web.assets_frontend_lazy.js`
- arbitrary `sleep()` delays

Odoo's OWL client may continuously perform RPC, bus, asset, or other browser activity.

### Preferred order

1. Wait for the expected **business UI state**.
2. If the UI cannot expose a reliable signal, wait for a specific relevant RPC.
3. Assert the target element/state.
4. Increase timeout only when there is evidence the environment needs it.

## Persistence rule

For Save/Submit requirements, a strong E2E pattern is:

`edit → save/submit → observe success → reopen/reload → verify persisted result`

Checking only the current DOM immediately after clicking Save is weaker because it may only prove that the current client state changed.

## Selector Contract

Preferred order:

1. `get_by_role()`
2. `get_by_label()`
3. `get_by_text()`
4. `get_by_test_id()`
5. another stable semantic locator

Avoid selectors coupled to Odoo CSS classes or DOM nesting when a semantic selector is available.

For custom modules, define stable `data-testid` values during TDD. Treat them as a UI Test Contract, not as an implementation detail invented after coding.

## Authentication

Prefer reusable Playwright `storage_state` files for Backend and Portal sessions. Keep authentication state out of source control.

## Backend simulation

Typical flows include:

- Odoo Backend navigation and forms
- Many2one interaction and actualisation
- Extend Preview
- Chatter-aware layout
- tab navigation
- Warehouse VAS workflows
- Global Search
- responsive viewport behavior
- save/submit persistence

Validate what the employee/operator/admin can see and accomplish.

## Portal simulation

Portal E2E may exercise:

- Portal login
- product list/search/filter/pagination
- product detail and tabs
- attachments/downloads
- change-request forms
- validation and cancellation
- upload and submit
- Chatter/messages
- responsive layouts
- weak-network behavior
- JS/OWL + RPC integration

Portal E2E is explicitly capable of testing JS/OWL behavior through the real browser. Use QUnit separately for isolated component-level assertions.

Do not hard-code arbitrary record IDs. Use controlled fixture data or data-driven navigation.

For custom OWL dropdowns, simulate the actual user interaction. Use `select_option()` only for native HTML `<select>` controls.

When using `bounding_box()`, first ensure the element is visible/attached and handle a possible `None` result.

## Network / weak-network testing

If CDP network emulation is used, label the scenario **Chromium-specific** unless equivalent support is intentionally implemented for other browsers.

Do not confuse network emulation with Odoo readiness. Weak-network tests should verify the user-visible behavior under degraded conditions.

## Data isolation

Use isolated test data and controlled records. Prefer unique identifiers where parallel/repeated execution can collide. Do not depend on arbitrary existing production-like records.

## CI / debugging

Recommended failure evidence:

- Playwright trace
- screenshot
- optionally video
- browser console/network evidence when useful

Use headed mode / slow motion / Codegen / REPL during development as appropriate, but keep final tests deterministic and business-state driven.

## SRS → TDD → Implementation → E2E → HVR

For projects using contract-driven development:

`SRS → TDD (including UI Test Contract) → Implementation → Playwright E2E → HVR`

The E2E test should validate the frozen business contract rather than inventing new requirements. If a test reveals a missing or contradictory requirement, record it as a requirement/design issue instead of silently expanding scope.

## Output expectations for coding agents

When asked to create or modify tests, report:

- user role and business goal
- files/tests changed
- selectors and any new `data-testid` contract
- readiness/actualisation strategy
- persistence verification strategy
- browsers/scenarios covered
- test command
- failures and retained evidence
- HVR mapping, if applicable

Do not claim a test passed unless it was actually executed and the result is available.

## Reference files

Read the relevant reference before implementing a substantial test:

- `references/general.md` — common Odoo Playwright rules
- `references/backend.md` — Backend Web Client patterns
- `references/portal.md` — Portal + JS/OWL patterns
