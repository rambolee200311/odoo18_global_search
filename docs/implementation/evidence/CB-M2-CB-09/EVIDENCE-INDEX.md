# CC-M2-CB-09 Evidence Index

**Current status:** FINAL ACCEPTED — CLOSED by owner on 2026-11-11. Evidence below combines the documented local tests with the authorized 2026-11-11 Odoo/Provider/UI run. The owner’s manual acceptance is the closure decision; no extra manual steps are inferred. Raw Odoo/test logs and the downloaded real-product XLSX remain outside the repository; sanitized summaries are indexed here.

| Evidence | Scope | Result |
|---|---|---|
| Local `ATR-office-verify.log` | Output-only XLSX verifier unit tests | 12 passed; raw log excluded from Git |
| Local `ATR-responses-adapter.log` | Isolated Responses Adapter SDK Mock and compatibility tests | 30 passed; raw log excluded from Git |
| Local `ATR-python-syntax.log` | Python syntax compilation | PASS; raw log excluded from Git |
| Local `ATR-fileless-current-fix-focused.log` | Focused Odoo fileless Current → edit → Finalize regression, plus module upgrade | 1 passed; raw log excluded from Git |
| Local `ATR-fileless-current-fix-full-regression.log` | `office_engine_m2` + `office_engine_odoo` upgrade and full test regression | 240 tests, 0 failed, 0 errors; module stats discrepancy retained in ATR; raw log excluded from Git |
| Local `ATR-post-run-integrity.log` | Final source syntax, evidence JSON parse and scoped whitespace check | PASS; raw log excluded from Git |
| `HVR-provider-calls.json` | Sanitized real Responses API + Hosted Code Interpreter create/edit calls, IDs, usage and cleanup | 2 requests completed |
| Local `HVR-odoo-8091.log` | Non-production Odoo 8091 service trace and Discuss attachment download requests | Final download HTTP 200; raw log excluded from Git |
| `HVR-xlsx-readback.json` | Version, download controller, SHA, ZIP and independent workbook readback assertions | PASS |
| `HVR-products-readback-20261111.json` | Authorized real product Retriever → `office(create)` V1, Discuss download and independent XLSX checks | PASS; 5 rows match Retriever |
| Local `ATR-fileless-tool-binding-and-current-20261111-rerun.log` | Fileless Route B tool binding and fileless Current regression | 2 tests, 0 failed, 0 errors; raw log excluded from Git |
| Local `ATR-fileless-tool-binding-and-current-20261111.log` | Initial unprivileged test launch; blocked before test startup by sandbox DB connection restriction | NOT RUN; no DB or module change; raw log excluded from Git |
| `HVR-products-discuss-20261111.md` | Root cause and real Odoo Discuss product archive creation/download HVR | PASS; `PARTIALLY_VERIFIED` retained |
| Local-only downloaded workbook | Actual file downloaded from Discuss attachment card; local independent readback | SHA `f84d034b…d4d8e9`; workbook omitted from Git to avoid publishing extracted business data |
| `CC09_Synthetic_V1.xlsx` | Read-only bytes for V1 attachment 49336 | SHA/openpyxl/ZIP PASS |
| `CC09_Synthetic_Final_V2.xlsx` | Read-only bytes for finalized attachment 49337 | SHA/openpyxl/ZIP PASS |
| `../../HVR-M2-CB-09.md` | Same-thread real Provider/UI create → V1 → edit → Candidate V2 → Accept → Finalize → download/readback | PASS; partial-verification boundary retained |
| `../../FR-M2-CB-09.md` | Final acceptance mapping and owner decision | APPROVED / CLOSED, limited to CC-09 scope |
| `../../../design/TDD_office_engine_m2_v2.1.2_CC09_Fileless_Create_AsBuilt_Amendment.md` | Versioned as-built TDD amendment; V2.1.0 frozen source retained unchanged | CC-09 fileless creation semantics recorded |

The two `CC09_Synthetic_*.xlsx` files contain synthetic workbook data. The downloaded product workbook contains Odoo-derived data and is intentionally not committed. The embedded browser for the synthetic HVR did not expose a local download path; the UI download request returned HTTP 200 and the exact linked attachment bytes were independently read back from attachment 49337.
