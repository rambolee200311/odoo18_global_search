# HVR — CC-018 Phase 1 Waiver Record

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| IHR | [IHR-GS-CC018-PHASE-1.md](IHR-GS-CC018-PHASE-1.md) |
| ATR | [ATR-GS-CC018-PHASE-1.md](ATR-GS-CC018-PHASE-1.md) |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Decision date | 2026-10-15 |

## 2. Status

Manual human verification and Safari HVR were **waived for this execution by
the user**, who accepted the built-in browser evidence and authorized
transition to later phases. This is a waiver, not a human PASS. No human
verifier or manual scenario result is fabricated here.

## 3. Waiver Coverage

| Requirement | Disposition |
|---|---|
| HVR-001–HVR-012 | WAIVED for this execution; automated Chromium/WebKit evidence is referenced in ATR, but is not represented as human execution. |
| Safari latest-version HVR | WAIVED for this execution. |
| Firefox / full browser matrix | Chromium-only waiver was previously approved; WebKit was run and passed, Firefox was blocked by macOS browser startup restrictions. |

## 4. Authorization Evidence

The user selected the explicit option to waive HVR/Safari for this execution,
accept current built-in browser evidence, and authorize progression to phases
2–5. The waiver is limited to this CC-018 execution and does not revise the
frozen contract text.

## 5. Evidence References

- [CC-018 browser evidence index](../../../mymodules/wd_global_search/tests/ui/evidence/INDEX.md)
- [ATR-GS-CC018-PHASE-1.md](ATR-GS-CC018-PHASE-1.md)

## 6. Limitations

No human HVR scenario is marked PASS. The user-approved waiver permits phase
progression for this run; it does not establish that HVR scenarios were
manually executed.
