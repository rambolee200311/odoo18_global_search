"""Standalone, real office_core/office_verify integration (run with pytest)."""

from io import BytesIO

from openpyxl import Workbook, load_workbook
from odoo.tests import TransactionCase

from office_core import ResourceBudget, inspect_document, render_candidate
from office_verify import VerificationBudget, VerificationPolicy, verify_output


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _source_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "Customer"
    sheet["B1"] = None
    sheet["A2"] = "Detail"
    # Materialize the second target cell so inspect_document includes its
    # coordinate in the deterministic TargetManifest. A trailing empty cell
    # is omitted by openpyxl's OOXML serialization and is not a valid target.
    sheet["B2"] = "Placeholder"
    sheet["C1"] = "=1+1"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class TestOfficeCoreM2Integration(TransactionCase):
    def test_cc_test_007_real_engine_generates_and_independently_verifies_xlsx(self):
        source = _source_xlsx()
        resource_budget = ResourceBudget(
            max_file_size=8 * 1024 * 1024,
            max_expanded_size=32 * 1024 * 1024,
            max_zip_entries=128,
            max_entry_size=8 * 1024 * 1024,
            max_xml_elements=100_000,
            max_cells=50_000,
            max_paragraphs=10_000,
            max_memory_bytes=2 * 1024 * 1024 * 1024,
            timeout_seconds=15,
        )
        verify_budget = VerificationBudget(
            max_file_size=8 * 1024 * 1024,
            max_expanded_size=32 * 1024 * 1024,
            max_zip_entries=128,
            max_entry_size=8 * 1024 * 1024,
            max_xml_elements=100_000,
            max_cells=50_000,
            max_paragraphs=10_000,
            max_mapping_bytes=64 * 1024,
            max_memory_bytes=2 * 1024 * 1024 * 1024,
            timeout_seconds=15,
        )
        inspection = inspect_document(source, "cc-m2-005.xlsx", XLSX_MIME, resource_budget)
        self.assertEqual(inspection.format, "xlsx")
        available_targets = {item.element_id for item in inspection.elements}
        self.assertIn("xlsx:Sheet1!B1", available_targets)
        self.assertIn("xlsx:Sheet1!B2", available_targets)
        plan = {
            "schema_version": "1",
            "template_sha256": inspection.template_sha256,
            "writes": [
                {
                    "element_id": "xlsx:Sheet1!B1",
                    "operation": "set_value",
                    "value": {"type": "string", "data": "Synthetic Acme"},
                },
                {
                    "element_id": "xlsx:Sheet1!B2",
                    "operation": "set_value",
                    "value": {"type": "string", "data": "Synthetic detail"},
                },
            ],
        }
        candidate = render_candidate(source, "cc-m2-005.xlsx", XLSX_MIME, plan, resource_budget)
        report = verify_output(
            source,
            candidate.content,
            "cc-m2-005.xlsx",
            XLSX_MIME,
            plan,
            VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
            verify_budget,
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.checked_targets, 2)
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(rendered["Sheet1"]["B1"].value, "Synthetic Acme")
            self.assertEqual(rendered["Sheet1"]["B2"].value, "Synthetic detail")
            self.assertEqual(rendered["Sheet1"]["C1"].value, "=1+1")
        finally:
            rendered.close()
