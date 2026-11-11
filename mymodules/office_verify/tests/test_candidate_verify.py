from __future__ import annotations

import io
import json
import unittest
import zipfile
from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation

from office_verify import OfficeVerifyError, VerificationBudget, verify_candidate_output, verify_created_output_with_metrics, verify_output

MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def minimal_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["Name", "Value", "Formula"])
    sheet.append(["A", 10, "=B2*2"])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def rich_workbook(*, value: int = 10, add_row: bool = False) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventory"
    sheet.append(["Product", "Quantity", "Amount", "Error"])
    sheet.append(["A", value, "=SUM(Table1[Quantity])", "#DIV/0!"])
    sheet["D2"].data_type = "e"
    if add_row:
        sheet.append(["B", 4, "=SUM(Table1[Quantity])", "#DIV/0!"])
        sheet["D3"].data_type = "e"
    table = Table(displayName="Table1", ref=f"A1:C{3 if add_row else 2}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)
    chart = BarChart()
    chart.add_data(Reference(sheet, min_col=2, min_row=1, max_row=3 if add_row else 2), titles_from_data=True)
    chart.set_categories(Reference(sheet, min_col=1, min_row=2, max_row=3 if add_row else 2))
    sheet.add_chart(chart, "F2")
    sheet.conditional_formatting.add("B2:B20", CellIsRule(operator="greaterThan", formula=["10"]))
    validation = DataValidation(type="list", formula1='"A,B,C"')
    sheet.add_data_validation(validation)
    validation.add("A2:A20")
    sheet.merge_cells("F1:G1")
    sheet["F1"] = "Summary"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def replace_part(source: bytes, name: str, content: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source), "r") as before, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as after:
        replaced = False
        for member in before.infolist():
            after.writestr(member.filename, content if member.filename == name else before.read(member.filename))
            replaced = replaced or member.filename == name
        if not replaced:
            after.writestr(name, content)
    return output.getvalue()


class CandidateVerifyTests(unittest.TestCase):
    def verify(self, source, candidate, *, budget=None):
        return verify_candidate_output(source, candidate, "neutral.xlsx", MIME, budget=budget or VerificationBudget())

    def test_normal_cell_edit_is_reviewable_and_records_typed_actual_effect(self):
        source = minimal_workbook()
        book = load_workbook(io.BytesIO(source))
        book["Data"]["B2"] = 15
        output = io.BytesIO()
        book.save(output)
        candidate = output.getvalue()

        report = self.verify(source, candidate)

        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        change = next(item for item in report.actual_effects if item.get("target") == "xlsx:Data!B2")
        self.assertEqual(change["before"], {"type": "number", "value": "10"})
        self.assertEqual(change["after"], {"type": "number", "value": "15"})
        self.assertTrue(report.unknowns)
        self.assertIsNone(report.error)

    def test_chart_table_merge_conditional_format_validation_error_and_formula_cache_changes_are_review_data(self):
        source = rich_workbook(value=10)
        candidate = rich_workbook(value=15, add_row=True)

        report = self.verify(source, candidate)

        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        self.assertIsNone(report.error)
        kinds = {item["change_kind"] for item in report.actual_effects}
        self.assertTrue({"cell_value", "formula_cache", "worksheet_structure", "package_part"}.intersection(kinds))
        features = {item["feature"]: item["capability"] for item in report.feature_results}
        self.assertEqual(features["other_ooxml_parts"], "PARTIALLY_SUPPORTED")
        self.assertTrue(any("table" in item.lower() or "chart" in item.lower() for item in report.unknowns))

    def test_structured_reference_formula_and_existing_error_cell_do_not_block(self):
        source = rich_workbook(value=10)
        book = load_workbook(io.BytesIO(source))
        book["Inventory"]["B2"] = 11
        output = io.BytesIO()
        book.save(output)

        report = self.verify(source, output.getvalue())

        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        self.assertIsNone(report.error)
        formulas = [item for item in report.actual_effects if item.get("change_kind") == "formula_text"]
        # openpyxl may rewrite formula serialization, but it does not make it a hard failure.
        self.assertEqual(formulas, [])

    def test_new_worksheet_structure_is_json_serializable_review_evidence(self):
        source = minimal_workbook()
        workbook = load_workbook(io.BytesIO(source))
        workbook.create_sheet("Review Notes")["A1"] = "结构检查"
        output = io.BytesIO()
        workbook.save(output)

        report = self.verify(source, output.getvalue())
        payload = report.as_dict()

        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        json.dumps(payload, ensure_ascii=False)
        self.assertTrue(any(
            change.get("target") == "xlsx:__workbook__!sheets"
            for change in payload["actual_effects"]
        ))

    def test_invalid_xlsx_is_still_blocked(self):
        with self.assertRaises(OfficeVerifyError):
            self.verify(minimal_workbook(), b"not an xlsx")

    def test_external_relationship_remains_blocked(self):
        source = minimal_workbook()
        with zipfile.ZipFile(io.BytesIO(source), "r") as archive:
            rels = archive.read("xl/_rels/workbook.xml.rels")
        rels = rels.replace(b"</Relationships>", b'<Relationship Id="rId9" Type="urn:external" Target="https://example.invalid/data" TargetMode="External"/></Relationships>')
        candidate = replace_part(source, "xl/_rels/workbook.xml.rels", rels)

        with self.assertRaises(OfficeVerifyError):
            self.verify(source, candidate)

    def test_unrecognized_safe_ooxml_part_is_recorded_not_rejected(self):
        source = minimal_workbook()
        candidate = replace_part(source, "xl/customXml/item1.xml", b'<item xmlns="urn:synthetic">one</item>')
        types = zipfile.ZipFile(io.BytesIO(candidate)).read("[Content_Types].xml")
        types = types.replace(b"</Types>", b'<Override PartName="/xl/customXml/item1.xml" ContentType="application/xml"/></Types>')
        candidate = replace_part(candidate, "[Content_Types].xml", types)

        report = self.verify(source, candidate)

        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        self.assertTrue(any(item.get("target") == "xlsx:__package__!xl/customXml/item1.xml" for item in report.actual_effects))

    def test_macro_part_is_still_blocked(self):
        source = minimal_workbook()
        candidate = replace_part(source, "xl/vbaProject.bin", b"synthetic macro")
        with self.assertRaises(OfficeVerifyError):
            self.verify(source, candidate)

    def test_m1_mapping_still_uses_strict_verifier(self):
        source = minimal_workbook()
        book = load_workbook(io.BytesIO(source))
        book["Data"]["B2"] = 15
        output = io.BytesIO()
        book.save(output)
        candidate = output.getvalue()
        from hashlib import sha256
        mapping = {
            "schema_version": "1",
            "template_sha256": sha256(source).hexdigest(),
            "writes": [{
                "element_id": "xlsx:Data!B2", "operation": "set_value",
                "value": {"type": "number", "data": 15},
            }],
        }
        report = verify_output(source, candidate, "neutral.xlsx", MIME, mapping)
        self.assertEqual(report.status, "PASS")

    def test_fileless_creation_checks_integrity_and_reports_partial_without_input_sha(self):
        candidate = minimal_workbook()
        report, metrics = verify_created_output_with_metrics(candidate, "created.xlsx", MIME)
        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        self.assertIsNone(report.input_sha256)
        self.assertEqual(report.output_sha256, __import__("hashlib").sha256(candidate).hexdigest())
        self.assertTrue(any("无来源工作簿可供比较" in item for item in report.unknowns))
        self.assertTrue(metrics["worker_exited"])

    def test_fileless_creation_rejects_corrupt_xlsx(self):
        with self.assertRaises(OfficeVerifyError):
            verify_created_output_with_metrics(b"not an xlsx", "created.xlsx", MIME)

    def test_resource_budget_still_applies(self):
        source = minimal_workbook()
        with self.assertRaises(OfficeVerifyError) as raised:
            self.verify(source, source, budget=VerificationBudget(max_file_size=20))
        self.assertEqual(raised.exception.code, "OFFICE_RESOURCE_LIMIT")


if __name__ == "__main__":
    unittest.main()
