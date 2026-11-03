"""Structural spreadsheet row expansion tests with a generic workbook fixture."""

from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from odoo.tests import TransactionCase

from office_core import (
    OfficeCoreError,
    ResourceBudget,
    expand_repeat_rows,
    expand_xlsx_rows,
    find_summary_row,
)


def _budget():
    return ResourceBudget(
        max_file_size=32 * 1024 * 1024,
        max_expanded_size=128 * 1024 * 1024,
        max_zip_entries=2000,
        max_entry_size=32 * 1024 * 1024,
        max_xml_elements=500_000,
        max_cells=100_000,
        max_paragraphs=100_000,
        max_memory_bytes=512 * 1024 * 1024,
        timeout_seconds=20,
    )


def _source():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["B3"] = "Repeating value"
    sheet["D3"] = "Quantity"
    for row in (4, 5):
        for column in "BCDEFG":
            sheet[f"{column}{row}"].fill = PatternFill("solid", fgColor="D9EAF7")
    # The template only has formulas in the first detail row. Expansion must
    # carry those row-relative formulas into newly created detail rows.
    sheet["F4"] = "=D4*E4"
    sheet["G4"] = "=F4*3"
    sheet["B6"] = "TOTAL"
    sheet["D6"] = "=SUM(D3:D5)"
    sheet["F6"] = "=SUM(F3:F5)"
    sheet["G6"] = "=SUM(G3:G5)"
    sheet.merge_cells("B8:G12")
    sheet["H8"] = "Content below the repeating section"
    sheet["H20"] = "=D6"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class TestXlsxRowExpansion(TransactionCase):
    def _expanded(self, count):
        source = _source()
        summary_row = find_summary_row(
            source, sheet_name="Data", first_row=3, budget=_budget()
        )
        content = expand_xlsx_rows(
            source,
            sheet_name="Data",
            first_row=3,
            row_count=count,
            summary_row=summary_row,
            budget=_budget(),
        )
        workbook = load_workbook(BytesIO(content), data_only=False)
        return content, workbook, workbook["Data"]

    def test_five_rows_shift_summary_formulas_merges_and_references(self):
        _content, workbook, sheet = self._expanded(5)
        try:
            self.assertEqual(sheet["F6"].value, "=D6*E6")
            self.assertEqual(sheet["G7"].value, "=F7*3")
            self.assertEqual(sheet["F7"].value, "=D7*E7")
            self.assertEqual(sheet["B8"].value, "TOTAL")
            self.assertEqual(sheet["D8"].value, "=SUM(D3:D7)")
            self.assertEqual(sheet["F8"].value, "=SUM(F3:F7)")
            self.assertIn("B10:G14", {str(item) for item in sheet.merged_cells.ranges})
            self.assertEqual(sheet["H10"].value, "Content below the repeating section")
            self.assertEqual(sheet["H22"].value, "=D8")
            self.assertTrue(sheet["B6"].fill.fgColor.rgb.endswith("D9EAF7"))
        finally:
            workbook.close()

    def test_twenty_rows_have_no_template_line_count_cap(self):
        _content, workbook, sheet = self._expanded(20)
        try:
            self.assertEqual(sheet["F22"].value, "=D22*E22")
            self.assertEqual(sheet["G22"].value, "=F22*3")
            self.assertEqual(sheet["F21"].value, "=D21*E21")
            self.assertEqual(sheet["B23"].value, "TOTAL")
            self.assertEqual(sheet["D23"].value, "=SUM(D3:D22)")
            self.assertEqual(sheet["H25"].value, "Content below the repeating section")
            self.assertIn("B25:G29", {str(item) for item in sheet.merged_cells.ranges})
        finally:
            workbook.close()

    def test_existing_capacity_is_unchanged(self):
        source = _source()
        summary_row = find_summary_row(
            source, sheet_name="Data", first_row=3, budget=_budget()
        )
        result = expand_xlsx_rows(
            source,
            sheet_name="Data",
            first_row=3,
            row_count=3,
            summary_row=summary_row,
            budget=_budget(),
        )
        self.assertEqual(result, source)

    def test_summary_row_is_discovered_from_formula_structure(self):
        self.assertEqual(
            find_summary_row(_source(), sheet_name="Data", first_row=3, budget=_budget()), 6
        )

    def test_invalid_row_arguments_are_rejected(self):
        source = _source()
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(OfficeCoreError):
                expand_xlsx_rows(
                    source,
                    sheet_name="Data",
                    first_row=3,
                    row_count=count,
                    summary_row=6,
                    budget=_budget(),
                )

    def test_generic_instruction_expands_five_rows_and_moves_summary_to_row_28(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Blad1"
        sheet["B23"] = "first detail"
        sheet["F23"] = "=D23*E23"
        for row in (24, 25):
            sheet[f"B{row}"] = None
        sheet["D26"] = "=SUM(D23:D25)"
        sheet["F26"] = "=SUM(F23:F25)"
        sheet["B30"] = "Content below the repeated region"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        result = expand_repeat_rows(
            output.getvalue(),
            {
                "action": "insert_repeat_rows",
                "sheet": "Blad1",
                "start_row": 23,
                "record_count": 5,
                "columns": {"B": "line.name", "D": "line.quantity", "F": "line.total"},
            },
            _budget(),
        )
        self.assertEqual(result.inserted_rows, 2)
        self.assertEqual(result.summary_row_before, 26)
        self.assertEqual(result.summary_row_after, 28)
        self.assertEqual(result.columns["D"], "line.quantity")

        expanded = load_workbook(BytesIO(result.content), data_only=False)
        try:
            sheet = expanded["Blad1"]
            self.assertEqual(sheet["F23"].value, "=D23*E23")
            self.assertEqual(sheet["F27"].value, "=D27*E27")
            self.assertEqual(sheet["D28"].value, "=SUM(D23:D27)")
            self.assertEqual(sheet["F28"].value, "=SUM(F23:F27)")
            self.assertEqual(sheet["B32"].value, "Content below the repeated region")
        finally:
            expanded.close()

    def test_generic_instruction_appends_rows_when_template_has_no_summary(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Import"
        sheet["A1"] = "Order"
        sheet["B1"] = "Amount"
        sheet["A2"] = "prototype"
        sheet["A2"].fill = PatternFill("solid", fgColor="D9EAF7")
        sheet["B2"].number_format = "0.00"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        result = expand_repeat_rows(
            output.getvalue(),
            {
                "action": "insert_repeat_rows",
                "sheet": "Import",
                "start_row": 2,
                "record_count": 5,
                "columns": {"A": "name", "B": "amount_total"},
            },
            _budget(),
        )
        self.assertEqual(result.inserted_rows, 4)
        self.assertIsNone(result.summary_row_before)
        self.assertIsNone(result.summary_row_after)

        expanded = load_workbook(BytesIO(result.content), data_only=False)
        try:
            sheet = expanded["Import"]
            self.assertEqual([sheet.cell(row=row, column=1).value for row in range(1, 7)],
                             ["Order", "prototype", None, None, None, None])
            self.assertEqual(sheet["A2"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["A6"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["B6"].number_format, "0.00")
            self.assertEqual(sheet.max_row, 6)
        finally:
            expanded.close()

    def test_no_summary_repeat_rows_rejects_content_below_prototype(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Import"
        sheet["A1"] = "Order"
        sheet["A2"] = "prototype"
        sheet["A8"] = "Footer"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        with self.assertRaises(OfficeCoreError):
            expand_repeat_rows(
                output.getvalue(),
                {
                    "action": "insert_repeat_rows",
                    "sheet": "Import",
                    "start_row": 2,
                    "record_count": 5,
                    "columns": {"A": "name"},
                },
                _budget(),
            )

    def test_generic_instruction_fails_closed_for_unknown_keys_or_bad_columns(self):
        source = _source()
        base = {
            "action": "insert_repeat_rows",
            "sheet": "Data",
            "start_row": 3,
            "record_count": 5,
            "columns": {"B": "line.name"},
        }
        invalid = (
            {**base, "unexpected": True},
            {**base, "columns": {"B1": "line.name"}},
            {**base, "columns": {"B": " "}},
            {**base, "action": "business_specific_action"},
        )
        for instruction in invalid:
            with self.subTest(instruction=instruction), self.assertRaises(OfficeCoreError):
                expand_repeat_rows(source, instruction, _budget())


if __name__ == "__main__":
    import unittest

    unittest.main()
