# CC-M2-CB-04 v3.0 — Browser / Playwright Attempt

## Scope

The requested UI validation was to use synthetic data, the existing Odoo user flow, and a mock Candidate adapter only. External Provider dispatch was not enabled. No chat prompt was sent during this attempt.

## Observed execution

1. The existing in-app browser tab for the dedicated loopback Odoo 8092 flow initially displayed `You are offline`.
2. A default-sandbox start of the dedicated process failed before serving HTTP because the sandbox denied its configured local database connection (`Operation not permitted`). It did not restart 8091 or change configuration.
3. Under the already granted Odoo test authorization, the dedicated `odoo-bin` process was started on `127.0.0.1:8092` with workers and cron disabled and the browser-simulation hook restricted to synthetic Thread `15154`. The authenticated in-app browser loaded the Odoo action page; the request log shows the action page returned HTTP 200. No prompt was submitted, so no chat/Provider request or Candidate operation occurred. The process was then stopped cleanly.
4. The Python Playwright package and Chromium executable are installed. The available browser session is authenticated inside the Codex in-app browser, but the standalone Playwright runner had no supported session bridge to that session in this task. Credentials were not extracted, copied, or changed, and no alternate account was created.

## Result

- Odoo UI page-load smoke through the built-in browser: **PASS** (page loaded; not a scenario test).
- Playwright T01–T15 scenario execution: **NOT RUN**.
- Screenshots/trace: **NOT GENERATED**. The built-in browser page-load did not produce a Playwright trace or persisted screenshot.
- Provider calls: **0**.
- Candidate operations: **0** in this attempt.
- 8091 restart: **none**.

This is an access/tooling limitation for the Playwright layer, not evidence that the tested scenarios pass or fail. Existing earlier built-in-browser simulations remain separately documented in the HVR and were not relabelled as Playwright evidence.
