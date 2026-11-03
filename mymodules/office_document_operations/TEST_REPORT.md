# M2 Phase B — Independent Document Operation Engine Test Report

**Result: PASS for the Phase B standalone XLSX scope.** This does not claim M2
integration or Odoo end-to-end acceptance; both are explicitly out of scope for
Phase B and remain for a later stage.

## Scope and environment

- Repository baseline: branch main, commit ec0913af451f6cb051fffca7c5ed933260459822.
- Before implementation, the worktree contained 82 pre-existing modified or
  untracked status entries. They were preserved. The only new worktree entry
  from this task is the mymodules/office_document_operations/ package.
- Runtime used: Python 3.11.9, openpyxl 3.0.9, jsonschema 4.26.0, pytest 9.1.1.
- No dependency installation, Odoo startup, database access, Provider call,
  M2 integration, or official Odoo source edit was performed.
- All XLSX fixtures and values are synthetic and created by the independent
  test suite. They are not represented as real Odoo business data.

## Implemented package

- schemas/document_operation_v1.0.schema.json: strict, versioned Draft
  2020-12 Operation List Schema for sort, format, clear, insert_rows, and
  set_value.
- schema.py: loads and validates the complete operation list before file
  access, rejects duplicate operation IDs and invalid typed values.
- engine.py: executes operations in order against an in-memory simulation
  first, applies them to a separate workbook, saves a candidate, and promotes
  it only after independent validation.
- xlsx_adapter.py: openpyxl implementation for the five supported
  operations, typed values, header/formula/merged-range checks, and
  conservative row-insertion structure checks.
- validator.py: independently reloads the original and saved candidate,
  checks the XLSX ZIP, replays operations through a separate reference
  interpreter, and compares normalized workbook state.
- errors.py: stable structured operation and stage errors.
- tests/test_engine.py: real on-disk XLSX fixture tests, including
  save/read-back failure protection.
- README.md and requirements.txt: package contract, examples, known
  limits, and the scoped JSON Schema dependency.

No M2, Mapping, Session, Preview, Finalize, Odoo ORM, or LLM files were modified
by this Phase B implementation.

## Verification

Commands executed successfully from the repository root:

    python3 -m py_compile mymodules/office_document_operations/*.py mymodules/office_document_operations/tests/*.py
    PYTHONPATH=mymodules python3 -m pytest -q mymodules/office_document_operations/tests

Result: **28 passed, 0 failed, 0 blocked**. The final verbose pytest log is
/private/tmp/m2_document_operation_final_pytest.log.

Coverage includes:

- Complete ordered operation sequence on saved XLSX files.
- Tail row append without a SUM row.
- Schema version, required-parameter, unknown-operation/key and duplicate-ID
  rejection.
- Missing sheet, invalid range, and protected-header behavior.
- Zero, false, null, empty string, date, datetime, formula-looking text, and
  timezone-aware datetime rejection.
- Row-preserving sort, stable equal keys, blank sort keys, and partial-row
  rejection.
- Number format, clear-values style preservation, clear-formats, clear-all,
  formula preservation and explicit formula clearing.
- Mid-sheet insertion refusal for formulas, merged ranges, and Excel Tables.
- Later-operation failure, save failure, validation failure, and atomic
  publication failure preserving the source and any existing destination.
- Corrupt/empty output rejection and explicit confirmation that openpyxl does
  not recalculate formulas.

Python compilation completed without errors. A static search of package Python
files found no Odoo imports, LLM imports, business model identifiers, or
template-specific identifiers.

## Independent saved-file read-back

The test fixture was also run as a standalone saved-file check. Artifacts:

- Input: /private/tmp/m2_document_operation_phase_b/operations_source.xlsx
- Output: /private/tmp/m2_document_operation_phase_b/operations_output.xlsx
- Machine-readable assertions:
  /private/tmp/m2_document_operation_phase_b/readback_report.json
- Output size: **5,733 bytes**
- SHA-256: 068feca1b4fe415d8140826c10ebce65e486c60e4c2d00a8d014323b7e0e9c82
- ZIP integrity and independent openpyxl read: **PASS**

All independent assertions passed:

| Assertion | Result |
| --- | --- |
| Header row unchanged | PASS |
| Five complete records sorted by order ID | PASS |
| Supplier values remain aligned with each row | PASS |
| Amounts and 0.0 number format | PASS |
| Target M5:M9 cleared | PASS |
| Existing zero and false retained | PASS |
| Date value retained | PASS |
| Untargeted M2/M3 and P1 values retained | PASS |
| Protected yellow P1 and inserted-row style retained | PASS |

The formula test verifies formula text and preservation only. Formula
calculation/recalculation is **not** provided by openpyxl and was not claimed.

## Known limits

- Only .xlsx and the five schema operations above are implemented. DOCX and
  other formats are not supported in this phase.
- format supports number_format only.
- Formula creation and recalculation are not supported.
- Mid-sheet row insertion is rejected when formulas, defined names, merged
  cells, tables, filters, drawings, conditional formatting, or data validation
  might need reference updates. Tail insertion is supported.
- Sorting rejects formula cells and partial record-row target ranges.
- clear uses a bounded header heuristic plus Excel Table header metadata;
  callers can explicitly opt into clearing a header.
- Advanced workbook features not covered by the comparison model require
  further compatibility testing before claiming support.
- No Odoo/M2 Preview, Finalize, attachment delivery, real-provider, or browser
  flow was run in this phase.

## Worktree handling

No files were staged, committed, pushed, reset, cleaned, or rolled back. The
pre-existing worktree changes remain in place. The package is untracked and
ready for review.
