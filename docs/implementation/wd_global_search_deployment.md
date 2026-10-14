# wd_global_search Deployment Constraint

## Supported Odoo worker mode

`wd_global_search` supports a single Odoo process only. Configure Odoo with `workers = 0` (or the equivalent `--workers=0`) and keep that setting explicit in the deployment configuration.

Odoo may still handle concurrent HTTP requests with threads in this mode. The in-process per-user limiter uses a lock to coordinate those threads. Search request ownership and cancellation state are also held in that process's memory.

## Multi-worker mode is not supported

Do not run this module with `workers > 0`. Each Odoo worker would have independent limiter counters and request/cancellation state. A request and its cancellation could be routed to different workers, and the effective rate/concurrency limits would not be consistent across the deployment.

Do not treat the current in-memory implementation as providing cross-worker coordination. If a deployment requires multiple Odoo worker processes, stop and obtain an approved design/contract before enabling that mode for this module.

## Deployment verification

1. Set `workers = 0` in the active Odoo configuration or pass `--workers=0`.
2. Restart Odoo after changing the worker setting.
3. Confirm the active process configuration before enabling Global Search for users.
