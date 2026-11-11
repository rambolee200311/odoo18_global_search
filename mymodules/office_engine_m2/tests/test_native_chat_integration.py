"""Native Odoo-LLM Office tool binding and safe message serialization tests."""

import hashlib
import json
from io import BytesIO
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils.datetime import from_excel, to_excel
from openpyxl.styles import PatternFill
from docx import Document
from lxml import etree
from odoo import tools
from odoo.exceptions import AccessError, UserError
from odoo.addons.llm_assistant.models.llm_thread import LLMThread as AssistantThread
from odoo.addons.llm_thread.models.llm_thread import LLMThread as NativeThread
from odoo.addons.llm_thread.controllers.main import LLMThreadController
from odoo.tests import TransactionCase
from office_core import inspect_document
from office_mapping_verify import MappingParseError
from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

from ..services.chat_entrypoint import (
    _field_candidates,
    _repeat_row_collection_candidates,
    _selected_record_context,
    _template_context,
)
from ..services.mapping_service import create_session, set_mapping_context
from ..services.render_bridge import _compile_plan
from ..models.office_mapping_tools import (
    _is_explicit_finalize_confirmation,
    _merge_mapping_patch,
    _normalize_merged_target_aliases,
)


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _finalize_inline_for_transactioncase(
    env, thread_id, session_id, expected_revision, proposal_revision, *, confirmation_proof=None
):
    """Keep TransactionCase fixtures in their rollback cursor; Browser covers root-cursor commits."""
    return env["office.mapping.tool"]._office_finalize(
        session_id,
        expected_revision,
        proposal_revision,
        expected_thread_id=thread_id,
        confirmation_proof=confirmation_proof,
    )


def _xlsx():
    workbook = Workbook()
    workbook.active["A1"] = "Customer"
    workbook.active["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _header_edit_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Orders"
    sheet["E1"] = "Description"
    sheet["F1"] = "Supplier Product Name"
    sheet["E2"] = "Keep this label"
    sheet["F2"] = "old value"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _date_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Dates"
    sheet["A1"] = "Order date"
    sheet["B1"] = datetime(2026, 11, 3, 9, 0)
    sheet["B1"].number_format = "yyyy-mm-dd hh:mm"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _date_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Orders"
    sheet["A1"] = "Selection"
    sheet["A3"] = "Order"
    sheet["B3"] = "Order date"
    sheet["A4"] = "example"
    sheet["B4"] = datetime(2026, 11, 3, 9, 0)
    sheet["B4"].number_format = "yyyy-mm-dd hh:mm"
    sheet["A5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].number_format = "yyyy-mm-dd hh:mm"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _docx():
    document = Document()
    document.add_paragraph("Contact: placeholder")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Reference"
    table.cell(0, 1).text = "placeholder"
    output = BytesIO()
    document.save(output)
    source = ZipFile(BytesIO(output.getvalue()), "r")
    clean = BytesIO()
    type_ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
    with ZipFile(clean, "w", ZIP_DEFLATED) as destination:
        for item in source.infolist():
            name = item.filename
            if name.startswith("customXml/") or name in {"word/stylesWithEffects.xml", "docProps/thumbnail.jpeg"}:
                continue
            raw = source.read(name)
            if name in {"word/_rels/document.xml.rels", "_rels/.rels"}:
                root = etree.fromstring(raw)
                for relationship in list(root):
                    relation_type = relationship.get("Type", "")
                    if relation_type.endswith("/customXml") or relation_type.endswith("/stylesWithEffects"):
                        root.remove(relationship)
                    elif name == "_rels/.rels" and relation_type.endswith("/thumbnail"):
                        root.remove(relationship)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif name == "[Content_Types].xml":
                root = etree.fromstring(raw)
                for node in list(root):
                    if node.get("PartName", "") in {"/customXml/itemProps1.xml", "/word/stylesWithEffects.xml"}:
                        root.remove(node)
                    elif node.tag == type_ns + "Default" and node.get("Extension") == "jpeg":
                        root.remove(node)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            destination.writestr(name, raw)
    source.close()
    return clean.getvalue()


def _repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "Parent"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A3"] = "Record"
    sheet["B3"] = "Name"
    sheet["B4"] = "example value"
    sheet["B4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["D4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["D5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A6"] = "Total"
    sheet["B6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["D6"] = "Total"
    sheet["E6"] = "=SUM(E4:E5)"
    sheet["F6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _no_summary_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Import"
    sheet["A1"] = "Record"
    sheet["B1"] = "Email"
    sheet["C1"] = "Unstyled email"
    sheet["A2"] = "example"
    for column in "A":
        sheet[f"{column}2"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    sheet["B2"].number_format = "@"
    # Keep an explicit, unstyled blank cell in the prototype row. Real import
    # sheets commonly contain these cells, and repeat-row writes must verify.
    sheet["B2"] = ""
    sheet["C2"] = ""
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _formula_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "Parent"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A3"] = "Record"
    sheet["B3"] = "Name"
    sheet["C3"] = "Weight"
    sheet["B4"] = "example value"
    sheet["B4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C4"] = "=B4*2"
    sheet["C5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A6"] = "Total"
    sheet["C6"] = "=SUM(C4:C5)"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _zero_numeric_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "Parent"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A3"] = "Record"
    sheet["B3"] = "Name"
    sheet["B4"] = "example value"
    sheet["B4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C3"] = "Color index"
    sheet["C4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A6"] = "Total"
    sheet["C6"] = "=SUM(C4:C5)"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _inventory_repeat_rows_xlsx():
    """Small inventory-shaped workbook for generic repeat/summary regressions."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventory"
    for column, label in enumerate(
        ["Product", "Name", "Warehouse", "Location", "Lot", "UoM", "On hand", "Reserved", "Native", "Calculated", "Delta"],
        start=1,
    ):
        cell = sheet.cell(1, column, label)
        cell.fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    for row in (2, 3):
        for column in range(7, 12):
            cell = sheet.cell(row, column)
            cell.fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet[f"G{row}"] = 0
        sheet[f"H{row}"] = 0
        sheet[f"I{row}"] = 0
        sheet[f"J{row}"] = f"=G{row}-H{row}"
        sheet[f"K{row}"] = f"=J{row}-I{row}"
    sheet["A4"] = "Total"
    for column in "GHIJK":
        sheet[f"{column}4"] = f"=SUM({column}2:{column}3)"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _confirmation_repeat_rows_xlsx(detail_capacity=2):
    """Neutral workbook for confirmation of generated repeat-row cell operations."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Rows"
    for column, label in enumerate(["Record", "Value", "Difference"], start=1):
        sheet.cell(1, column, label).fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    last_detail_row = detail_capacity + 1
    for row in range(2, last_detail_row + 1):
        sheet[f"B{row}"] = 0
        sheet[f"C{row}"] = f"=B{row}-B{row}"
        sheet[f"B{row}"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet[f"C{row}"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    summary_row = last_detail_row + 1
    sheet[f"A{summary_row}"] = "Total"
    sheet[f"B{summary_row}"] = f"=SUM(B2:B{last_detail_row})"
    sheet[f"C{summary_row}"] = f"=SUM(C2:C{last_detail_row})"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class TestNativeOfficeChatIntegration(TransactionCase):
    def test_repeat_rows_single_object_is_normalized_before_tool_validation(self):
        thread, _attachment, _upload = self._office_message(
            "Fill these records into the inventory rows.", raw=_inventory_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Repeat object row %s %s" % (index, uuid4().hex),
                "color": index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retriever_result = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-object-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "color"],
                    "limit": 100,
                },
                "status": "completed",
                "result": [{"id": record.id, "name": record.name, "color": record.color} for record in records],
            },
        )
        mapping_tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = mapping_tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "color"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        original_revision = session.revision
        original_rules = session.mapping_rules_json
        repeat_rows_object = {
            "collection_field": "selected_records",
            "sheet": "Inventory",
            "start_row": 2,
            "columns": [{"column": "G", "source_field": "color"}],
        }
        tool = self.env["llm.tool"].search(
            [("name", "=", "office_save_mapping_preview")], limit=1
        ).with_context(message=retriever_result)

        result = tool.execute({
            "session_id": session.id,
            "expected_revision": session.revision,
            "proposal": {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            "repeat_rows": repeat_rows_object,
        })

        self.assertEqual(result["status"], "needs_confirmation", result)
        self.assertEqual(result["error_code"], "confirmation_required")
        self.assertEqual(result["risks"][0]["risk_type"], "repeat_row_range_expansion")
        self.assertFalse(result["operation_executed"])
        self.assertFalse(session.preview_attachment_id)
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.mapping_rules_json, original_rules)

    def test_repeat_row_confirmation_authorizes_its_derived_cells_and_formulas(self):
        """A confirmed repeat-row expansion must not demand a second cell-edit approval."""
        thread, _attachment, _upload = self._office_message(
            "Fill the selected records into the repeated rows.",
            raw=_confirmation_repeat_rows_xlsx(),
        )
        records = self.env["res.partner"].create([
            {
                "name": f"Confirmed repeat row {index} {uuid4().hex}",
                "color": index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retrieval = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-confirm-derived-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "color"],
                    "limit": len(records),
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "color": record.color}
                    for record in records
                ],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retrieval)
        context = tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "color"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
        }
        repeat_rows = [{
            "collection_field": "selected_records",
            "sheet": "Rows",
            "start_row": 2,
            "columns": [
                {"column": "A", "source_field": "name"},
                {"column": "B", "source_field": "color"},
                {"column": "C", "formula": "=B{row}-B{row}"},
            ],
        }]
        revision = session.revision
        prior_preview_id = session.preview_attachment_id.id or False

        warning = tool.office_save_mapping_preview(
            session.id, revision, proposal, repeat_rows=repeat_rows
        )

        self.assertEqual(warning["status"], "needs_confirmation", warning)
        self.assertEqual(
            [risk["risk_type"] for risk in warning["risks"]],
            ["repeat_row_range_expansion"],
        )
        self.assertFalse(warning["operation_executed"])
        self.assertEqual(session.revision, revision)
        self.assertEqual(session.preview_attachment_id.id or False, prior_preview_id)

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        applied = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id, revision, proposal, repeat_rows=repeat_rows
        )

        self.assertEqual(applied["status"], "success", applied)
        self.assertEqual(applied["operation_status"], "preview_ready")
        self.assertTrue(applied["operation_executed"])
        self.assertGreater(session.revision, revision)
        self.assertEqual(session.preview_proposal_revision, session.proposal_revision)
        self.assertFalse(session.pending_cell_override_json)
        payload = session.preview_attachment_id.raw
        self.assertTrue(payload)
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
        workbook = load_workbook(BytesIO(payload), data_only=False)
        try:
            sheet = workbook["Rows"]
            self.assertEqual([sheet[f"A{row}"].value for row in range(2, 5)], records.mapped("name"))
            self.assertEqual([sheet[f"B{row}"].value for row in range(2, 5)], records.mapped("color"))
            self.assertEqual([sheet[f"C{row}"].value for row in range(2, 5)], [f"=B{row}-B{row}" for row in range(2, 5)])
            self.assertEqual(sheet["B5"].value, "=SUM(B2:B4)")
            self.assertEqual(sheet["C5"].value, "=SUM(C2:C4)")
            self.assertEqual(sheet["A1"].value, "Record")
            self.assertEqual(sheet["A1"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["B4"].fill.fgColor.rgb, "00FFFFFF")
        finally:
            workbook.close()

    def test_explicit_cell_edit_overrides_same_target_repeat_row_mapping(self):
        """A user-directed cell edit may override one derived repeated-row value."""
        thread, _attachment, upload = self._office_message(
            "Fill the selected records into the repeated rows.",
            raw=_confirmation_repeat_rows_xlsx(detail_capacity=3),
        )
        records = self.env["res.partner"].create([
            {
                "name": f"Cell override row {index} {uuid4().hex}",
                "color": index + 1,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retrieval = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-cell-override-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "color"],
                    "limit": len(records),
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "color": record.color}
                    for record in records
                ],
            },
        )
        context_tool = self.env["office.mapping.tool"].with_context(message=retrieval)
        context = context_tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "color"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        repeat_rows = [{
            "collection_field": "selected_records",
            "sheet": "Rows",
            "start_row": 2,
            "columns": [
                {"column": "A", "source_field": "name"},
                {"column": "B", "source_field": "color"},
            ],
        }]
        empty_proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
        }
        initial = self._save_repeat_rows_with_user_confirmation(
            context_tool, thread, session, empty_proposal, repeat_rows=repeat_rows
        )
        self.assertEqual(initial["status"], "success", initial)
        before_revision = session.revision
        before_preview = session.preview_attachment_id
        before_payload = before_preview.raw
        workbook = load_workbook(BytesIO(before_payload), data_only=False)
        try:
            self.assertEqual([workbook["Rows"][f"B{row}"].value for row in range(2, 5)], [1, 2, 3])
            before_style_id = workbook["Rows"]["B2"].style_id
        finally:
            workbook.close()

        edit = [{"element_id": "xlsx:Rows!B2", "value": "", "value_type": "string"}]
        request = thread.message_post(
            body="Clear the first selected record's value cell.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        tool = self.env["office.mapping.tool"].with_context(message=request)
        warning = tool.office_save_mapping_preview(
            session.id,
            before_revision,
            empty_proposal,
            repeat_rows=repeat_rows,
            cell_edits=edit,
        )

        self.assertEqual(warning["status"], "needs_confirmation", warning)
        self.assertEqual(warning["risk_type"], "content_clear")
        self.assertFalse(warning["operation_executed"])
        self.assertEqual(session.revision, before_revision)
        self.assertEqual(session.preview_attachment_id, before_preview)
        self.assertEqual(session.preview_attachment_id.raw, before_payload)

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        applied = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            before_revision,
            empty_proposal,
            repeat_rows=repeat_rows,
            cell_edits=edit,
        )
        self.assertEqual(applied["status"], "success", applied)
        self.assertEqual(applied["operation_status"], "preview_ready")
        self.assertTrue(applied["operation_executed"])
        self.assertEqual(session.preview_proposal_revision, session.proposal_revision)

        payload = session.preview_attachment_id.raw
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
        workbook = load_workbook(BytesIO(payload), data_only=False)
        try:
            sheet = workbook["Rows"]
            self.assertIn(sheet["B2"].value, (None, ""))
            self.assertEqual([sheet[f"B{row}"].value for row in (3, 4)], [2, 3])
            self.assertEqual([sheet[f"C{row}"].value for row in range(2, 5)], [
                "=B2-B2", "=B3-B3", "=B4-B4",
            ])
            self.assertEqual(sheet["B5"].value, "=SUM(B2:B4)")
            self.assertEqual(sheet["A1"].value, "Record")
            self.assertEqual(sheet["A1"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["B2"].style_id, before_style_id)
        finally:
            workbook.close()

    def test_record_targeted_cell_edit_follows_repeat_row_after_sort_and_confirmation(self):
        """A stable record/cell edit follows its row after the final sort."""
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Rows"
        for column, label in enumerate(["Contact", "Note", "Color", "Difference"], start=1):
            sheet.cell(1, column, label).fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
        for row in range(2, 5):
            sheet[f"B{row}"] = "template note"
            sheet[f"C{row}"] = 0
            sheet[f"D{row}"] = f"=C{row}-C{row}"
            for column in "BCD":
                sheet[f"{column}{row}"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet["A5"] = "Total"
        sheet["C5"] = "=SUM(C2:C4)"
        sheet["D5"] = "=SUM(D2:D4)"
        source = BytesIO()
        workbook.save(source)
        workbook.close()
        thread, _attachment, _upload = self._office_message(
            "Fill the selected records into the repeated rows.",
            raw=source.getvalue(),
        )
        records_by_label = {
            label: self.env["res.partner"].create({
                "name": f"{label} record target {uuid4().hex}",
                "comment": f"{label} note {uuid4().hex}",
                "color": value,
                "company_id": self.env.company.id,
            })
            for label, value in (("Zulu", 10), ("Alpha", 20), ("Mike", 30))
        }
        records = self.env["res.partner"].browse([
            records_by_label[label].id for label in ("Zulu", "Alpha", "Mike")
        ])
        retrieval = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-record-cell-edit-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "comment", "color"],
                    "limit": len(records),
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "comment": record.comment, "color": record.color}
                    for record in records
                ],
            },
        )
        context_tool = self.env["office.mapping.tool"].with_context(message=retrieval)
        context = context_tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "comment", "color"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        columns = [
            {"column": "A", "source_field": "name"},
            {"column": "B", "source_field": "comment"},
            {"column": "C", "source_field": "color"},
        ]
        initial_repeat_rows = [{
            "collection_field": "selected_records",
            "sheet": "Rows",
            "start_row": 2,
            "columns": columns,
            "sort_by": "name",
            "sort_direction": "asc",
        }]
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
        }
        initial = self._save_repeat_rows_with_user_confirmation(
            context_tool, thread, session, proposal, repeat_rows=initial_repeat_rows
        )
        self.assertEqual(initial["status"], "success", initial)
        initial_revision = session.revision
        initial_preview = session.preview_attachment_id
        original_values = {
            record.id: {"comment": record.comment, "color": record.color}
            for record in records
        }

        # This mirrors the live model call: it names the currently displayed
        # cell in the already sorted repeat band. The server must bind that
        # coordinate to the record at this final row position before saving.
        edit = [{
            "element_id": "xlsx:Rows!B2",
            "value": "",
            "value_type": "string",
        }]
        sorted_ascending = [{
            **initial_repeat_rows[0],
            "sort_by": "name",
            "sort_direction": "asc",
        }]
        sorted_descending = [{
            **initial_repeat_rows[0],
            "sort_by": "name",
            "sort_direction": "desc",
        }]
        request = thread.message_post(
            body="Clear Alpha's value after sorting the records by name descending.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        tool = self.env["office.mapping.tool"].with_context(message=request)
        warning = tool.office_save_mapping_preview(
            session.id,
            initial_revision,
            proposal,
            repeat_rows=sorted_ascending,
            cell_edits=edit,
        )

        self.assertEqual(warning["status"], "needs_confirmation", warning)
        self.assertFalse(warning.get("operation_executed"))
        self.assertEqual(session.revision, initial_revision)
        self.assertEqual(session.preview_attachment_id, initial_preview)
        self.assertEqual(session.preview_attachment_id.raw, initial_preview.raw)
        self.assertEqual(
            {record.id: {"comment": record.comment, "color": record.color} for record in records}, original_values,
            "Preparing a preview must not modify Odoo business records.",
        )

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        changed_scope = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            initial_revision,
            proposal,
            repeat_rows=sorted_descending,
            cell_edits=edit,
            force_override=True,
        )
        self.assertEqual(changed_scope["status"], "needs_confirmation", changed_scope)
        self.assertFalse(changed_scope.get("operation_executed"))
        self.assertEqual(session.revision, initial_revision)
        self.assertEqual(session.preview_attachment_id, initial_preview)
        self.assertEqual(
            {record.id: {"comment": record.comment, "color": record.color} for record in records}, original_values,
            "A stale confirmation must not mutate Odoo records or execute document writes.",
        )

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        reverted_scope = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            initial_revision,
            proposal,
            repeat_rows=sorted_ascending,
            cell_edits=edit,
            force_override=True,
        )
        self.assertEqual(reverted_scope["status"], "needs_confirmation", reverted_scope)
        self.assertFalse(reverted_scope.get("operation_executed"))
        self.assertEqual(session.revision, initial_revision)

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        applied = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            initial_revision,
            proposal,
            repeat_rows=sorted_ascending,
            # The model may carry the collection selector from its conversation
            # context rather than the server's generated repeat-group ID. The
            # server must resolve that alias only when it uniquely identifies
            # the authorized collection, then persist the canonical group ID.
            cell_edits=[{
                "record_target": {
                    "group_id": "selected_records",
                    "record_id": records_by_label["Alpha"].id,
                    "column": "B",
                },
                "value": "",
                "value_type": "string",
            }],
            force_override=True,
        )
        self.assertEqual(applied["status"], "success", applied)
        self.assertTrue(applied["operation_executed"])
        saved_rules = json.loads(session.mapping_rules_json)
        self.assertEqual(
            saved_rules["cell_edits"][0]["record_target"],
            {
                "group_id": "repeat_rows",
                "record_id": records_by_label["Alpha"].id,
                "column": "B",
            },
            "A repeat-band coordinate must be persisted as a stable record target.",
        )
        self.assertEqual(
            {record.id: {"comment": record.comment, "color": record.color} for record in records}, original_values,
            "Applying a document edit must not modify Odoo business records.",
        )

        payload = session.preview_attachment_id.raw
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
        workbook = load_workbook(BytesIO(payload), data_only=False)
        try:
            sheet = workbook["Rows"]
            self.assertEqual(
                [sheet[f"A{row}"].value for row in range(2, 5)],
                [records_by_label[label].name for label in ("Alpha", "Mike", "Zulu")],
            )
            self.assertIn(sheet["B2"].value, (None, ""), "Only Alpha's contact note is cleared.")
            self.assertEqual(sheet["B3"].value, original_values[records_by_label["Mike"].id]["comment"])
            self.assertEqual(sheet["B4"].value, original_values[records_by_label["Zulu"].id]["comment"])
            self.assertEqual(
                [sheet[f"C{row}"].value for row in range(2, 5)],
                [original_values[records_by_label[label].id]["color"] for label in ("Alpha", "Mike", "Zulu")],
            )
            self.assertEqual(
                [sheet[f"D{row}"].value for row in range(2, 5)],
                [f"=C{row}-C{row}" for row in range(2, 5)],
            )
            self.assertEqual(sheet["C5"].value, "=SUM(C2:C4)")
            self.assertEqual(sheet["D5"].value, "=SUM(D2:D4)")
            self.assertEqual(sheet["A1"].value, "Contact")
            self.assertEqual(sheet["A1"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["B2"].fill.fgColor.rgb, "00FFFFFF")
        finally:
            workbook.close()

        # A later re-sort recompiles the preview from the saved stable target;
        # the clear follows Alpha from row 2 to row 4, while the other values
        # remain attached to their records.
        sort_request = thread.message_post(
            body="Sort the records by name descending.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        resorted = self.env["office.mapping.tool"].with_context(message=sort_request).office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            repeat_rows=sorted_descending,
        )
        self.assertEqual(resorted["status"], "success", resorted)
        payload = session.preview_attachment_id.raw
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
        workbook = load_workbook(BytesIO(payload), data_only=False)
        try:
            sheet = workbook["Rows"]
            self.assertEqual(
                [sheet[f"A{row}"].value for row in range(2, 5)],
                [records_by_label[label].name for label in ("Zulu", "Mike", "Alpha")],
            )
            self.assertEqual(sheet["B2"].value, original_values[records_by_label["Zulu"].id]["comment"])
            self.assertEqual(sheet["B3"].value, original_values[records_by_label["Mike"].id]["comment"])
            self.assertIn(sheet["B4"].value, (None, ""), "The clear follows Alpha after resorting.")
            self.assertEqual(sheet["C2"].value, original_values[records_by_label["Zulu"].id]["color"])
            self.assertEqual(sheet["C3"].value, original_values[records_by_label["Mike"].id]["color"])
            self.assertEqual(sheet["C4"].value, original_values[records_by_label["Alpha"].id]["color"])
            self.assertEqual(sheet["D2"].value, "=C2-C2")
            self.assertEqual(sheet["C5"].value, "=SUM(C2:C4)")
            self.assertEqual(sheet["D5"].value, "=SUM(D2:D4)")
            self.assertEqual(sheet["A1"].value, "Contact")
            self.assertEqual(sheet["A1"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual([sheet[f"B{row}"].fill.fgColor.rgb for row in range(2, 5)], ["00FFFFFF"] * 3)
        finally:
            workbook.close()

    def test_repeated_coordinate_edit_replaces_saved_record_target_edit(self):
        """The same repeat-row cell edit can be retried by coordinate once."""
        thread, _attachment, _upload = self._office_message(
            "Fill the selected records into the repeated rows.",
            raw=_repeat_rows_xlsx(),
        )
        records = self.env["res.partner"].create([
            {
                "name": f"Batch summary contact {index} {uuid4().hex}",
                **({"comment": f"Existing note {index}"} if index else {}),
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retrieval = thread.message_post(
            body="Retrieved selected contacts",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "batch-summary-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "comment"],
                    "limit": len(records),
                },
                "status": "completed",
                "result": [
                    {"id": item.id, "name": item.name, "comment": item.comment}
                    for item in records
                ],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retrieval)
        context = tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "comment"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
        }
        initial_rows = [{
            "collection_field": "selected_records",
            "sheet": "Data",
            "start_row": 4,
            "sort_by": "name",
            "sort_direction": "asc",
            "columns": [
                {"column": "A", "source_field": "name"},
                {"column": "B", "source_field": "comment"},
            ],
        }]
        initial = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session, proposal, repeat_rows=initial_rows
        )
        self.assertEqual(initial["status"], "success", initial)

        first_record = sorted(records, key=lambda item: item.name)[0]
        clear = [{
            "record_target": {
                "group_id": "selected_records",
                "record_id": first_record.id,
                "column": "B",
            },
            "value": "",
            "value_type": "string",
        }]
        clear_request = thread.message_post(
            body=f"Clear {first_record.name}'s summary.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        warned = self.env["office.mapping.tool"].with_context(message=clear_request).office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            repeat_rows=initial_rows,
            cell_edits=clear,
        )
        self.assertEqual(warned["status"], "needs_confirmation", warned)
        self.assertFalse(warned["operation_executed"])
        confirm = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        cleared = self.env["office.mapping.tool"].with_context(message=confirm).office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            repeat_rows=initial_rows,
            cell_edits=clear,
            force_override=True,
        )
        self.assertEqual(cleared["status"], "success", cleared)
        self.assertIn("record_target", json.loads(session.mapping_rules_json)["cell_edits"][0])

        # A follow-up may point at the displayed coordinate rather than repeat
        # the stable record selector. After binding, it is the same logical
        # edit and must replace the persisted version instead of duplicating it.
        coordinate_clear = [{
            "element_id": "xlsx:Data!B4",
            "value": "",
            "value_type": "string",
        }]
        repeated = self._save_repeat_rows_with_user_confirmation(
            tool,
            thread,
            session,
            proposal,
            repeat_rows=initial_rows,
            cell_edits=coordinate_clear,
        )
        self.assertEqual(repeated["status"], "success", repeated)
        self.assertEqual(repeated["operation_status"], "unchanged")
        self.assertFalse(repeated["operation_executed"])
        persisted_edits = json.loads(session.mapping_rules_json).get("cell_edits", [])
        self.assertEqual(len(persisted_edits), 1)
        self.assertEqual(persisted_edits[0]["record_target"]["record_id"], first_record.id)
        with ZipFile(BytesIO(session.preview_attachment_id.raw)) as archive:
            self.assertIsNone(archive.testzip())
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Data"]
            expected = sorted(item.name for item in records)
            self.assertEqual([sheet[f"A{row}"].value for row in range(4, 7)], expected)
            self.assertIn(sheet["B4"].value, (None, ""))
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(5, 7)],
                [item.comment or None for item in sorted(records, key=lambda item: item.name)[1:]],
            )
            self.assertEqual(sheet["E7"].value, "=SUM(E4:E6)")
            self.assertEqual(sheet["A3"].value, "Record")
        finally:
            workbook.close()

        combined_rows = [{
            **initial_rows[0],
            "columns": [
                {"column": "A", "source_field": "name"},
                {"column": "B", "concat_fields": ["comment", "name"], "separator": " "},
            ],
        }]
        combined = self._save_repeat_rows_with_user_confirmation(
            tool,
            thread,
            session,
            proposal,
            repeat_rows=combined_rows,
        )
        self.assertEqual(combined["status"], "success", combined)
        self.assertFalse(json.loads(session.mapping_rules_json).get("cell_edits"))
        refreshed = tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "comment"],
        )
        self.assertEqual(
            refreshed["current_repeat_rows"][0]["columns"],
            [
                {"column": "A", "source_field": "name"},
                {"column": "B", "concat_fields": ["comment", "name"], "separator": " "},
            ],
        )
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Data"]
            ordered_records = sorted(records, key=lambda item: item.name)
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(4, 7)],
                [" ".join(part for part in (item.comment or "", item.name) if part) for item in ordered_records],
            )
            self.assertEqual([sheet[f"A{row}"].value for row in range(4, 7)], [item.name for item in ordered_records])
            self.assertEqual(sheet["E7"].value, "=SUM(E4:E6)")
            self.assertEqual(sheet["A3"].value, "Record")
        finally:
            workbook.close()

    def test_prepare_context_reauthorizes_requested_selected_record_fields(self):
        thread, _attachment, upload = self._office_message(
            "Fill the selected records into the inventory table.", raw=_inventory_repeat_rows_xlsx()
        )
        related = self.env["res.partner"].create(
            {"name": "Selected record related value " + uuid4().hex, "company_id": self.env.company.id}
        )
        records = self.env["res.partner"].create([
            {
                "name": "Selected record row " + uuid4().hex,
                "email": "selected-row-1@example.test",
                "parent_id": related.id,
                "company_id": self.env.company.id,
            },
            {
                "name": "Selected record row " + uuid4().hex,
                "email": "selected-row-2@example.test",
                "parent_id": related.id,
                "company_id": self.env.company.id,
            },
        ])
        retriever_result = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "selected-fields-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "email", "parent_id"],
                    "limit": 100,
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "email": record.email, "parent_id": [related.id, related.name]}
                    for record in records
                ],
            },
        )

        context = self.env["office.mapping.tool"].with_context(message=retriever_result).office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields_by_collection={
                "selected_records": ["email", "parent_id.name", "definitely_missing_field"]
            },
        )

        selected = next(
            item for item in context["repeat_row_collections"]
            if item["collection_field"] == "selected_records"
        )
        self.assertEqual(selected["allowed_fields"]["email"]["type"], "string")
        self.assertEqual(selected["allowed_fields"]["parent_id.name"]["type"], "string")
        self.assertEqual(
            context["unavailable_requested_collection_fields"],
            {"selected_records": ["definitely_missing_field"]},
        )
        self.assertEqual(
            context["unavailable_requested_collection_field_reasons"]["selected_records"][
                "definitely_missing_field"
            ],
            ["field_not_found"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        stored = json.loads(session.context_json)
        self.assertIn("email", stored["extra_authorized_fields"])
        self.assertIn("parent_id.name", stored["extra_authorized_fields"])
        self.assertNotIn("definitely_missing_field", stored["extra_authorized_fields"])

    def test_repeat_row_expansion_requires_exact_user_confirmation_before_write(self):
        thread, _attachment, upload = self._office_message(
            "Fill all selected records into the inventory table.", raw=_inventory_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {"name": f"Inventory row {index} {uuid4().hex}", "color": index, "company_id": self.env.company.id}
            for index in range(3)
        ])
        retriever_message = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "inventory-selected-records-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner", "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "color"], "limit": 100,
                },
                "status": "completed",
                "result": [{"id": record.id, "name": record.name, "color": record.color} for record in records],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids,
            requested_fields=["name", "color"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [], "clarifications": [], "skipped_targets": [],
        }
        omitted_repeat_rows = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                **proposal,
                "clarifications": [{
                    "element_id": "xlsx:Inventory!A2",
                    "reason_code": "missing_source",
                    "question": "Which field should be written here?",
                }],
            },
        )
        self.assertEqual(omitted_repeat_rows["status"], "error", omitted_repeat_rows)
        self.assertEqual(omitted_repeat_rows["error_code"], "repeat_rows_required")
        self.assertEqual(omitted_repeat_rows["unknown_targets"], [])
        self.assertEqual(omitted_repeat_rows["unresolved_targets"], ["xlsx:Inventory!A2"])
        self.assertFalse(omitted_repeat_rows["operation_executed"])
        self.assertEqual(omitted_repeat_rows["selected_record_count"], 3)
        self.assertEqual(omitted_repeat_rows["existing_row_capacity"], 2)
        self.assertFalse(session.preview_attachment_id)
        repeat_rows = [{
            "collection_field": "selected_records", "sheet": "Inventory", "start_row": 2,
            "columns": [
                {"column": "G", "source_field": "color"},
                {"column": "H", "source_field": "color"},
                {"column": "I", "source_field": "color"},
                {"column": "J", "formula": "=G{row}-H{row}"},
                {"column": "K", "formula": "=J{row}-I{row}"},
            ],
        }]
        original_revision = session.revision
        original_rules = session.mapping_rules_json
        warning = tool.office_save_mapping_preview(
            session.id, session.revision, proposal, repeat_rows=repeat_rows
        )

        self.assertEqual(warning["status"], "needs_confirmation", warning)
        self.assertEqual(warning["error_code"], "confirmation_required")
        self.assertFalse(warning["operation_executed"])
        self.assertEqual(warning["risks"][0]["risk_type"], "repeat_row_range_expansion")
        self.assertEqual(warning["risks"][0]["old_value"]["detail_rows"], [2, 3])
        self.assertEqual(warning["risks"][0]["new_value"]["detail_rows"], [2, 4])
        self.assertEqual(warning["risks"][0]["new_value"]["summary_row"], 5)
        self.assertTrue(warning["risks"][0]["formula_impacts"])
        self.assertFalse(session.preview_attachment_id)
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.mapping_rules_json, original_rules)

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        changed_scope = [{
            **repeat_rows[0], "sort_by": "name", "sort_direction": "desc",
        }]
        stale = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id, session.revision, proposal, repeat_rows=changed_scope, force_override=True
        )
        self.assertEqual(stale["status"], "needs_confirmation", stale)
        self.assertEqual(stale["error_code"], "confirmation_scope_changed")
        self.assertFalse(stale["operation_executed"])
        self.assertFalse(session.preview_attachment_id)
        self.assertEqual(session.revision, original_revision)

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        applied = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id, session.revision, proposal, repeat_rows=changed_scope
        )
        self.assertEqual(applied["status"], "success", applied)
        self.assertTrue(applied["operation_executed"])
        self.assertFalse(session.pending_cell_override_json)
        payload = session.preview_attachment_id.raw
        self.assertTrue(payload)
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIsNone(archive.testzip())
        workbook = load_workbook(BytesIO(payload), data_only=False)
        try:
            sheet = workbook["Inventory"]
            sorted_records = records.sorted("name", reverse=True)
            self.assertEqual([sheet[f"G{row}"].value for row in range(2, 5)], sorted_records.mapped("color"))
            self.assertEqual([sheet[f"J{row}"].value for row in range(2, 5)], [f"=G{row}-H{row}" for row in range(2, 5)])
            self.assertEqual([sheet[f"K{row}"].value for row in range(2, 5)], [f"=J{row}-I{row}" for row in range(2, 5)])
            self.assertEqual(sheet["G5"].value, "=SUM(G2:G4)")
            self.assertEqual(sheet["H5"].value, "=SUM(H2:H4)")
            self.assertEqual(sheet["I5"].value, "=SUM(I2:I4)")
            self.assertEqual(sheet["J5"].value, "=SUM(J2:J4)")
            self.assertEqual(sheet["K5"].value, "=SUM(K2:K4)")
            self.assertEqual(sheet["A1"].value, "Product")
        finally:
            workbook.close()

    def test_repeat_rows_can_compile_a_bounded_large_calculated_table_mapping(self):
        thread, _attachment, upload = self._office_message(
            "Fill nineteen selected records into repeated rows.", raw=_inventory_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {"name": f"Large repeat row {index:02d} {uuid4().hex}", "color": index % 12,
             "company_id": self.env.company.id}
            for index in range(19)
        ])
        retriever_message = thread.message_post(
            body="Retrieved nineteen readable records.",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "large-repeat-record-set",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner", "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "color"], "limit": len(records), "offset": 0,
                },
                "status": "completed",
                "result": {
                    "records": [{"id": item.id, "name": item.name, "color": item.color} for item in records],
                    "count": len(records), "offset": 0, "limit": len(records), "has_more": False,
                },
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids,
            requested_fields=["name", "color"],
        )
        self.assertEqual(context["status"], "ready", context)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        columns = [
            *[{"column": column, "source_field": "name"} for column in "ABCDEF"],
            *[{"column": column, "source_field": "color"} for column in "GHI"],
            {"column": "J", "formula": "=G{row}-H{row}"},
            {"column": "K", "formula": "=J{row}-I{row}"},
        ]
        repeat_rows = [{
            "collection_field": "selected_records", "sheet": "Inventory", "start_row": 2,
            "columns": columns,
        }]
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [], "clarifications": [], "skipped_targets": [],
        }
        warning = tool.office_save_mapping_preview(
            session.id, session.revision, proposal, repeat_rows=repeat_rows
        )
        self.assertEqual(warning["status"], "needs_confirmation", warning)
        self.assertFalse(warning["operation_executed"])
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id, session.revision, proposal, repeat_rows=repeat_rows, force_override=True
        )
        self.assertEqual(result["status"], "success", result)
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Inventory"]
            self.assertEqual(
                [sheet[f"A{row}"].value for row in range(2, 21)],
                records.mapped("name"),
            )
            self.assertEqual(
                [sheet[f"G{row}"].value for row in range(2, 21)],
                records.mapped("color"),
            )
            self.assertEqual(sheet["J20"].value, "=G20-H20")
            self.assertEqual(sheet["K20"].value, "=J20-I20")
            self.assertEqual(sheet["G21"].value, "=SUM(G2:G20)")
            self.assertEqual(sheet["K21"].value, "=SUM(K2:K20)")
        finally:
            workbook.close()

    def test_root_header_edit_replaces_stale_unsupported_skip_and_keeps_mapping(self):
        instruction = "Change one table header and preserve the saved mapping."
        thread, _attachment, upload = self._office_message(instruction, raw=_header_edit_xlsx())
        target = self.env["res.partner"].create(
            {"name": "Root header mapping source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        first = tool.office_save_mapping_preview(
            context["session_id"],
            context["revision"],
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(first["status"], "success", first)
        self.assertEqual(first["operation_status"], "preview_ready")
        session = self.env["office.mapping.session"].browse(context["session_id"])

        edit_request = thread.message_post(
            body="Change the header to 供应商商品描述 without changing the source mapping.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        edit_tool = self.env["office.mapping.tool"].with_context(message=edit_request)
        patch = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [
                {
                    "element_id": "xlsx:Orders!F1",
                    "reason_code": "unsupported_target",
                    "question": "The old manifest treated the header as unwritable.",
                }
            ],
            "skipped_targets": ["xlsx:Orders!F1"],
        }
        cell_edits = [
            {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}
        ]
        result = edit_tool.office_save_mapping_preview(
            session.id,
            session.revision,
            patch,
            cell_edits=cell_edits,
        )

        self.assertEqual(result["status"], "needs_confirmation", result)
        confirmation = thread.message_post(
            body="确认",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            patch,
            cell_edits=cell_edits,
            force_override=True,
        )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["operation_status"], "preview_ready")
        self.assertTrue(result["attachment_posted_to_thread"])
        saved = json.loads(session.mapping_rules_json)
        self.assertEqual(
            saved["mappings"],
            [{"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}],
        )
        self.assertEqual(
            saved["cell_edits"],
            [{"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}],
        )
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(workbook["Orders"]["F1"].value, "供应商商品描述")
            self.assertEqual(workbook["Orders"]["F2"].value, target.name)
            self.assertEqual(workbook["Orders"]["E1"].value, "Description")
            self.assertEqual(workbook["Orders"]["E2"].value, "Keep this label")
        finally:
            workbook.close()

    def test_explicit_header_edit_creates_preview_without_changing_source_mapping(self):
        instruction = "Change the header text, keep the data mapping unchanged."
        thread, _attachment, upload = self._office_message(instruction, raw=_header_edit_xlsx())
        target = self.env["res.partner"].create(
            {"name": "Header mapping source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        self.assertIn("explicit_coordinate_cell_edits", context["mapping_limits"]["supported"])
        self.assertNotIn("explicit_table_header_text_edits", context["mapping_limits"]["supported"])
        header = next(
            item for item in context["target_manifest"]
            if item["element_id"] == "xlsx:Orders!F1"
        )
        self.assertEqual(header["table_role"], "table_header")
        self.assertFalse(header["writable"])

        initial = tool.office_save_mapping_preview(
            context["session_id"],
            context["revision"],
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(initial["status"], "success", initial)
        self.assertEqual(initial["operation_status"], "preview_ready")
        session = self.env["office.mapping.session"].browse(context["session_id"])
        initial_revision = session.revision
        initial_proposal_revision = session.proposal_revision
        initial_preview_id = session.preview_attachment_id.id
        edit_request = thread.message_post(
            body="修改表头‘供应商产品名称’为‘供应商商品描述’，不得改变来源字段。",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        edit_tool = self.env["office.mapping.tool"].with_context(message=edit_request)
        patch = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [
                {
                    "element_id": "xlsx:Orders!F1",
                    "reason_code": "unsupported_target",
                    "question": "The old manifest treated the header as unwritable.",
                }
            ],
            "skipped_targets": ["xlsx:Orders!F1"],
        }
        cell_edits = [
            {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}
        ]
        result = edit_tool.office_save_mapping_preview(
            session.id, session.revision, patch, cell_edits=cell_edits
        )

        self.assertEqual(result["status"], "needs_confirmation", result)
        self.assertEqual(result["target"], "xlsx:Orders!F1")
        self.assertEqual(result["current_value"], "Supplier Product Name")
        self.assertEqual(result["requested_value"], "供应商商品描述")
        self.assertEqual(result["risk_type"], "table_header_change")
        self.assertEqual(result["affected_scope"], ["xlsx:Orders!F1"])
        self.assertEqual(result["operation_scope"]["action"], "office_mapping_update")
        self.assertEqual(result["operation_scope"]["thread_id"], thread.id)
        self.assertEqual(result["operation_scope"]["session_id"], session.id)
        self.assertEqual(result["operation_scope"]["mapping_targets"], ["xlsx:Orders!F2"])
        self.assertEqual(
            result["operation_scope"]["operations"],
            [{
                "action": "set_value",
                "target": "xlsx:Orders!F1",
                "value": "供应商商品描述",
                "value_type": "string",
            }],
        )
        self.assertEqual(len(result["operation_scope"]["operation_fingerprint"]), 64)
        self.assertEqual(result["risks"][0]["old_value"], "Supplier Product Name")
        self.assertEqual(result["risks"][0]["new_value"], "供应商商品描述")
        self.assertTrue(result["recommendation"])
        self.assertEqual(
            result["confirmation_question"],
            "F1 单元格原本是‘Supplier Product Name’，您确定要将其覆盖为‘供应商商品描述’吗？",
        )
        self.assertFalse(result.get("preview_attachment_id"))
        self.assertEqual(session.preview_attachment_id.id, initial_preview_id)
        self.assertEqual(session.revision, initial_revision)
        self.assertEqual(session.proposal_revision, initial_proposal_revision)
        self.assertFalse(json.loads(session.mapping_rules_json).get("cell_edits", []))
        pending = json.loads(session.pending_cell_override_json)
        self.assertEqual(pending["request_message_id"], edit_request.id)

        # A model-supplied force flag alone is not a user confirmation.
        unconfirmed = edit_tool.office_save_mapping_preview(
            session.id,
            session.revision,
            patch,
            cell_edits=cell_edits,
            force_override=True,
        )
        self.assertEqual(unconfirmed["status"], "needs_confirmation", unconfirmed)
        self.assertFalse(unconfirmed.get("preview_attachment_id"))
        self.assertEqual(session.preview_attachment_id.id, initial_preview_id)

        confirmation = thread.message_post(
            body="确认",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            patch,
            cell_edits=cell_edits,
            force_override=True,
        )

        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["operation_status"], "preview_ready")
        self.assertTrue(result["attachment_posted_to_thread"])
        self.assertEqual(result["message_id"] and result["attachment"]["id"], result["preview_attachment_id"])
        session.invalidate_recordset()
        saved = json.loads(session.mapping_rules_json)
        self.assertEqual(
            saved["mappings"],
            [{"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}],
        )
        self.assertEqual(
            saved["cell_edits"],
            [{"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}],
        )
        preview_bytes = session.preview_attachment_id.raw
        workbook = load_workbook(BytesIO(preview_bytes), data_only=False)
        try:
            self.assertEqual(workbook["Orders"]["F1"].value, "供应商商品描述")
            self.assertEqual(workbook["Orders"]["F2"].value, target.name)
            self.assertEqual(workbook["Orders"]["E1"].value, "Description")
            self.assertEqual(workbook["Orders"]["E2"].value, "Keep this label")
        finally:
            workbook.close()

    def test_legacy_required_target_omission_preserves_original_value(self):
        thread, _attachment, upload = self._office_message(
            "Prepare the workbook and leave unmentioned cells unchanged.", raw=_header_edit_xlsx()
        )
        target = self.env["res.partner"].create(
            {"name": "Legacy required omission source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        stored_context = json.loads(session.context_json)
        legacy_target = next(
            item for item in stored_context["target_manifest"]
            if item["element_id"] == "xlsx:Orders!F2"
        )
        self.assertTrue(legacy_target["writable"])
        legacy_target["required"] = True
        legacy_target["approved_to_skip"] = False
        session._set_context_from_service(json.dumps(stored_context, ensure_ascii=False))

        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
        }
        edits = [{
            "element_id": "xlsx:Orders!F1",
            "value": "Updated header",
            "value_type": "string",
        }]
        warning = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            cell_edits=edits,
        )

        self.assertEqual(warning["status"], "needs_confirmation", warning)
        self.assertEqual(warning["affected_scope"], ["xlsx:Orders!F1"])
        self.assertEqual(warning["risks"][0]["old_value"], "Supplier Product Name")
        self.assertEqual(warning["risks"][0]["new_value"], "Updated header")
        self.assertFalse(warning["operation_executed"])
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            cell_edits=edits,
            force_override=True,
        )
        self.assertEqual(result["status"], "success", result)
        saved = json.loads(session.mapping_rules_json)
        self.assertNotIn("xlsx:Orders!F2", saved.get("clear_targets", []))
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(workbook["Orders"]["F2"].value, "old value")
            self.assertEqual(workbook["Orders"]["F1"].value, "Updated header")
        finally:
            workbook.close()
        self.assertTrue(
            self.env["mail.message"].search_count(
                [("id", "=", result["message_id"]), ("model", "=", "llm.thread"), ("res_id", "=", thread.id)]
            )
        )

    def test_explicit_formula_overwrite_requires_confirmation_and_does_not_render_first(self):
        thread, _attachment, upload = self._office_message(
            "Fill the workbook and let me review it.", raw=_formula_repeat_rows_xlsx()
        )
        target = self.env["res.partner"].create(
            {"name": "Formula confirmation source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        initial = tool.office_save_mapping_preview(
            context["session_id"],
            context["revision"],
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B4", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(initial["status"], "success", initial)
        self.assertEqual(initial["operation_status"], "preview_ready")
        session = self.env["office.mapping.session"].browse(context["session_id"])
        revision_before = session.revision
        preview_before = session.preview_attachment_id.id
        edit_request = thread.message_post(
            body="Replace C4's formula with 12.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
        }
        cell_edits = [
            {"element_id": "xlsx:Data!C4", "value": 12, "value_type": "number"}
        ]
        result = self.env["office.mapping.tool"].with_context(message=edit_request).office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            cell_edits=cell_edits,
        )

        self.assertEqual(result["status"], "needs_confirmation", result)
        self.assertEqual(result["current_value"], {"formula": "=B4*2"})
        self.assertEqual(
            result["confirmation_question"],
            "C4 单元格原本是‘公式 =B4*2’，您确定要将其覆盖为‘12’吗？",
        )
        self.assertEqual(session.revision, revision_before)
        self.assertEqual(session.preview_attachment_id.id, preview_before)

        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        applied = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            proposal,
            cell_edits=cell_edits,
            force_override=True,
        )
        self.assertEqual(applied["status"], "success", applied)
        self.assertEqual(applied["operation_status"], "preview_ready")
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(workbook["Data"]["C4"].value, 12)
            self.assertIsNone(workbook["Data"]["C5"].value)
            self.assertEqual(workbook["Data"]["C6"].value, "=SUM(C4:C5)")
        finally:
            workbook.close()

    def test_cell_override_rejection_clears_pending_without_writing(self):
        thread, _attachment, upload = self._office_message(
            "Fill the workbook and let me review it.", raw=_header_edit_xlsx()
        )
        target = self.env["res.partner"].create(
            {"name": "Rejected overwrite source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        initial = tool.office_save_mapping_preview(
            context["session_id"], context["revision"],
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [
                {"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}
            ], "clarifications": [], "skipped_targets": []},
        )
        self.assertEqual(initial["status"], "success", initial)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        original_preview = session.preview_attachment_id
        original_bytes = original_preview.raw
        original_revision = session.revision
        original_proposal_revision = session.proposal_revision
        edits = [{"element_id": "xlsx:Orders!F1", "value": "Do not apply", "value_type": "string"}]
        request = thread.message_post(
            body="Replace the header with Do not apply.", llm_role="user", author_id=self.env.user.partner_id.id
        )
        first = self.env["office.mapping.tool"].with_context(message=request).office_save_mapping_preview(
            session.id, session.revision,
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []},
            cell_edits=edits,
        )
        self.assertEqual(first["status"], "needs_confirmation", first)
        refusal = thread.message_post(body="拒绝", llm_role="user", author_id=self.env.user.partner_id.id)
        rejected = self.env["office.mapping.tool"].with_context(message=refusal).office_save_mapping_preview(
            session.id, session.revision,
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []},
            cell_edits=edits, force_override=True,
        )
        self.assertEqual(rejected["status"], "blocked", rejected)
        self.assertEqual(rejected["error_code"], "user_rejected_confirmation")
        self.assertFalse(rejected["operation_executed"])
        self.assertFalse(session.pending_cell_override_json)
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.proposal_revision, original_proposal_revision)
        self.assertEqual(session.preview_attachment_id.id, original_preview.id)
        self.assertEqual(session.preview_attachment_id.raw, original_bytes)
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(workbook["Orders"]["F1"].value, "Supplier Product Name")
        finally:
            workbook.close()

    def test_confirmation_is_invalidated_when_preview_file_changes(self):
        thread, _attachment, upload = self._office_message(
            "Fill the workbook and let me review it.", raw=_header_edit_xlsx()
        )
        target = self.env["res.partner"].create(
            {"name": "Stale confirmation source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        initial = tool.office_save_mapping_preview(
            context["session_id"], context["revision"],
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [
                {"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}
            ], "clarifications": [], "skipped_targets": []},
        )
        self.assertEqual(initial["status"], "success", initial)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        edits = [{"element_id": "xlsx:Orders!F1", "value": "New label", "value_type": "string"}]
        request = thread.message_post(
            body="Set the header to New label.", llm_role="user", author_id=self.env.user.partner_id.id
        )
        patch = {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []}
        first = self.env["office.mapping.tool"].with_context(message=request).office_save_mapping_preview(
            session.id, session.revision, patch, cell_edits=edits
        )
        self.assertEqual(first["status"], "needs_confirmation", first)

        # Simulate a valid, independently changed preview document under the same
        # attachment identity. A prior approval must not authorize its new bytes.
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        workbook["Orders"]["E2"] = "changed after warning"
        changed = BytesIO()
        workbook.save(changed)
        workbook.close()
        session.preview_attachment_id.write({"raw": changed.getvalue()})
        confirmation = thread.message_post(body="确认", llm_role="user", author_id=self.env.user.partner_id.id)
        stale = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id, session.revision, patch, cell_edits=edits, force_override=True
        )
        self.assertEqual(stale["status"], "needs_confirmation", stale)
        self.assertEqual(stale["error_code"], "confirmation_scope_changed")
        self.assertFalse(stale["operation_executed"])
        self.assertEqual(session.revision, first["revision"])
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(workbook["Orders"]["F1"].value, "Supplier Product Name")
            self.assertEqual(workbook["Orders"]["E2"].value, "changed after warning")
        finally:
            workbook.close()

    def test_force_override_cannot_expand_to_target_outside_manifest(self):
        thread, _attachment, upload = self._office_message(
            "Fill the workbook.", raw=_header_edit_xlsx()
        )
        target = self.env["res.partner"].create(
            {"name": "Out of manifest source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        result = tool.office_save_mapping_preview(
            context["session_id"], context["revision"],
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []},
            cell_edits=[{"element_id": "xlsx:Orders!ZZ999", "value": "outside", "value_type": "string"}],
            force_override=True,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["error_code"], "target_outside_authorized_manifest")
        self.assertFalse(result["operation_executed"])
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertFalse(session.preview_attachment_id)
        self.assertEqual(session.revision, context["revision"])

    def test_confirmation_cannot_be_reused_after_mapping_scope_expands(self):
        thread, _attachment, upload = self._office_message(
            "Fill this workbook.", raw=_header_edit_xlsx()
        )
        target = self.env["res.partner"].create(
            {
                "name": "Confirmation scope source " + uuid4().hex,
                "email": "scope@example.test",
                "phone": "555-0101",
                "company_id": self.env.company.id,
            }
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        initial_proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        initial = tool.office_save_mapping_preview(
            context["session_id"], context["revision"], initial_proposal
        )
        self.assertEqual(initial["status"], "success", initial)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        old_preview = session.preview_attachment_id
        old_revision = session.revision
        cell_edits = [
            {"element_id": "xlsx:Orders!F1", "value": "Approved header", "value_type": "string"}
        ]
        request = thread.message_post(
            body="Change F1 to Approved header.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        pending_tool = self.env["office.mapping.tool"].with_context(message=request)
        warning = pending_tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []},
            cell_edits=cell_edits,
        )
        self.assertEqual(warning["status"], "needs_confirmation", warning)
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        expanded_proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Orders!F2", "source_field": "email", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        expanded = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            expanded_proposal,
            cell_edits=cell_edits,
            force_override=True,
        )
        self.assertEqual(expanded["status"], "needs_confirmation", expanded)
        self.assertEqual(expanded["error_code"], "confirmation_scope_changed")
        self.assertFalse(expanded["operation_executed"])
        self.assertEqual(session.revision, old_revision)
        self.assertEqual(session.preview_attachment_id, old_preview)
        self.assertEqual(json.loads(session.mapping_rules_json), initial_proposal)

    def test_explicit_clear_of_header_requires_confirmation_then_clears_only_that_cell(self):
        thread, _attachment, upload = self._office_message(
            "Fill the workbook and let me review it.", raw=_header_edit_xlsx()
        )
        target = self.env["res.partner"].create(
            {"name": "Header clear source " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Orders!F2", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        initial = tool.office_save_mapping_preview(context["session_id"], context["revision"], proposal)
        self.assertEqual(initial["status"], "success", initial)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        old_preview_id = session.preview_attachment_id.id
        before_revision = session.revision
        request = thread.message_post(
            body="Clear the heading in F1.", llm_role="user", author_id=self.env.user.partner_id.id
        )
        clear_proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
            "clear_targets": ["xlsx:Orders!F1"],
        }
        first = self.env["office.mapping.tool"].with_context(message=request).office_save_mapping_preview(
            session.id, session.revision, clear_proposal
        )
        self.assertEqual(first["status"], "needs_confirmation", first)
        self.assertEqual(first["risk_type"], "table_header_change")
        self.assertEqual(first["risks"][0]["operation"], "clear")
        self.assertFalse(first["operation_executed"])
        self.assertEqual(session.preview_attachment_id.id, old_preview_id)
        self.assertEqual(session.revision, before_revision)

        confirmation = thread.message_post(body="确认", llm_role="user", author_id=self.env.user.partner_id.id)
        final = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id, session.revision, clear_proposal, force_override=True
        )
        self.assertEqual(final["status"], "success", final)
        self.assertEqual(final["operation_status"], "preview_ready")
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertIsNone(workbook["Orders"]["F1"].value)
            self.assertEqual(workbook["Orders"]["F2"].value, target.name)
            self.assertEqual(workbook["Orders"]["E1"].value, "Description")
            self.assertEqual(workbook["Orders"]["E2"].value, "Keep this label")
        finally:
            workbook.close()

    def test_cell_edit_patch_preserves_other_mappings_and_migrates_legacy_header_edit(self):
        current = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {
                    "element_id": "xlsx:Orders!F2",
                    "source_field": "product_description_variants",
                    "value_type": "string",
                }
            ],
            "clarifications": [],
            "skipped_targets": [],
            "header_edits": [
                {"element_id": "xlsx:Orders!F1", "value": "供应商产品名称"}
            ],
        }
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
            "cell_edits": [
                {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}
            ],
        }

        merged = _merge_mapping_patch(current, patch_data)

        self.assertEqual(merged["mappings"], current["mappings"])
        self.assertEqual(
            merged["cell_edits"],
            [{"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}],
        )

    def test_explicit_cell_edit_supersedes_same_target_data_mapping(self):
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Orders!F1", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
            "cell_edits": [{"element_id": "xlsx:Orders!F1", "value": "New label", "value_type": "string"}],
        }

        merged = _merge_mapping_patch(
            {"mappings": [], "clarifications": [], "skipped_targets": []},
            patch_data,
        )
        self.assertEqual(merged["mappings"], [])
        self.assertEqual(merged["cell_edits"][0]["value"], "New label")

    def test_mapping_patch_rejects_same_target_mapping_and_clarification(self):
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Purchase Reconciliation!B4", "literal_value": 3329.15, "value_type": "number"}
            ],
            "clarifications": [
                {
                    "element_id": "xlsx:Purchase Reconciliation!B4",
                    "reason_code": "unsupported_value",
                    "question": "Please confirm the value.",
                }
            ],
            "skipped_targets": [],
        }
        with self.assertRaisesRegex(MappingParseError, "conflicting_patch_target"):
            _merge_mapping_patch({"mappings": [], "clarifications": [], "skipped_targets": []}, patch_data)

    def test_explicit_clear_wins_over_echoed_mapping_for_same_target(self):
        current = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Data!B3", "source_field": "partner_id.name", "value_type": "string"},
                {"element_id": "xlsx:Data!F18", "source_field": "client_order_ref", "value_type": "string"},
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Data!F18", "source_field": "client_order_ref", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
            "clear_targets": ["xlsx:Data!F18"],
        }

        merged = _merge_mapping_patch(current, patch_data)

        self.assertEqual(
            merged["mappings"],
            [{"element_id": "xlsx:Data!B3", "source_field": "partner_id.name", "value_type": "string"}],
        )
        self.assertEqual(merged["clear_targets"], ["xlsx:Data!F18"])

    def test_column_format_patch_replaces_older_cell_patches_in_that_column(self):
        current = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
            "format_patches": [
                {"element_id": "xlsx:Import!I2", "number_format": "0.00"},
                {"element_id": "xlsx:Import!I3", "number_format": "0.00"},
                {"element_id": "xlsx:Import!H2", "number_format": "yyyy-mm-dd"},
            ],
        }
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
            "format_patches": [
                {"sheet": "Import", "column": "I", "number_format": "0.0"}
            ],
        }

        merged = _merge_mapping_patch(current, patch_data)

        self.assertEqual(
            merged["format_patches"],
            [
                {"element_id": "xlsx:Import!H2", "number_format": "yyyy-mm-dd"},
                {"sheet": "Import", "column": "I", "number_format": "0.0"},
            ],
        )

    def test_numeric_literal_mapping_writes_computed_value_to_preview(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Purchase Reconciliation"
        sheet["A1"] = "Adjusted amount (EUR)"
        sheet["B1"].number_format = "0.00"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread = self.env["llm.thread"].create(
            {
                "name": "Numeric literal mapping " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "numeric-literal.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": output.getvalue(),
                "company_id": self.env.company.id,
            }
        )
        user_message = thread.message_post(
            body="Fill the adjusted amount",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        retriever_result = thread.message_post(
            body="Authorized record lookup",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "numeric-literal-retriever-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", self.env.user.partner_id.id]], "fields": ["id", "name"], "limit": 1},
                "status": "completed",
                "result": [{"id": self.env.user.partner_id.id, "name": self.env.user.partner_id.name}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", self.env.user.partner_id.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Purchase Reconciliation!B1", "literal_value": 3329.15, "value_type": "number"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(result["status"], "success", result)
        self.assertTrue(result["operation_executed"])
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Purchase Reconciliation"]["B1"].value, 3329.15)
            self.assertEqual(rendered["Purchase Reconciliation"]["A1"].value, "Adjusted amount (EUR)")
        finally:
            rendered.close()

    def test_date_offset_mapping_writes_a_typed_excel_datetime_plus_seven_days(self):
        thread, _attachment, user_message = self._office_message(
            "Delay every selected order date by seven days", raw=_date_xlsx()
        )
        target = self.env.user.partner_id
        retriever_result = thread.message_post(
            body="Authorized date field lookup",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "date-offset-retriever-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["create_date"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "create_date": "2026-11-03T09:00:00"}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context(
            "res.partner", target.id, requested_fields=["create_date"]
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(context["allowed_fields"]["create_date"]["type"], "datetime")
        target_spec = next(
            item for item in context["target_manifest"] if item["element_id"] == "xlsx:Dates!B1"
        )
        self.assertIn("datetime", target_spec["allowed_value_types"])

        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {
                    "element_id": "xlsx:Dates!B1",
                    "source_field": "create_date",
                    "value_type": "datetime",
                    "transform": {"type": "date_offset", "days": 7},
                }
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        with patch(
            "odoo.addons.office_engine_m2.services.render_bridge._retrieve_record",
            return_value={"create_date": "2026-11-03T09:00:00"},
        ):
            result = tool.office_save_mapping_preview(session.id, session.revision, proposal)
        self.assertEqual(result["status"], "success", result)
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            value = workbook["Dates"]["B1"].value
            self.assertEqual(value, datetime(2026, 11, 10, 9, 0))
            self.assertEqual(workbook["Dates"]["B1"].number_format, "yyyy-mm-dd hh:mm")
            self.assertEqual(workbook["Dates"]["A1"].value, "Order date")
        finally:
            workbook.close()

    def test_repeat_row_date_offset_is_applied_to_each_authorized_record(self):
        thread, _attachment, user_message = self._office_message(
            "Delay all selected dates by one week", raw=_date_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create(
            [
                {
                    "name": "Date offset row %s %s" % (index, uuid4().hex),
                    "company_id": self.env.company.id,
                }
                for index in range(3)
            ]
        )
        expected = {
            record.name: record.create_date.replace(tzinfo=None) + timedelta(days=7)
            for record in records
        }
        retriever_message = thread.message_post(
            body="Retrieved the selected records and their dates",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "date-offset-selected-records-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "create_date"],
                    "limit": len(records),
                    "include_pagination": True,
                },
                "status": "completed",
                "result": {
                    "records": [
                        {
                            "id": record.id,
                            "name": record.name,
                            "create_date": record.create_date.isoformat(sep=" "),
                        }
                        for record in records
                    ],
                    "count": len(records),
                    "offset": 0,
                    "limit": len(records),
                    "has_more": False,
                },
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["name", "create_date"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        repeat_rows = [
            {
                "collection_field": "selected_records",
                "sheet": "Orders",
                "start_row": 4,
                "sort_by": "name",
                "sort_direction": "asc",
                "columns": [
                    {
                        "column": "B",
                        "source_field": "create_date",
                        "transform": {"type": "date_offset", "days": 7},
                    }
                ],
            }
        ]
        result = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=repeat_rows,
        )
        self.assertEqual(result["status"], "success", result)
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            actual = [workbook["Orders"][f"B{row}"].value for row in range(4, 7)]
            self.assertEqual(
                actual,
                [
                    from_excel(to_excel(expected[record.name]))
                    for record in sorted(records, key=lambda item: item.name)
                ],
            )
            self.assertEqual(workbook["Orders"]["B4"].number_format, "yyyy-mm-dd hh:mm")
            self.assertEqual(workbook["Orders"]["B3"].value, "Order date")
        finally:
            workbook.close()
        # Re-submitting the same repeat definition must reconstruct the saved
        # transform rather than losing it during unexpansion/revision.
        second_result = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=repeat_rows,
        )
        self.assertEqual(second_result["status"], "success", second_result)
        self.assertIn(second_result["operation_status"], {"preview_ready", "unchanged"})
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            actual = [workbook["Orders"][f"B{row}"].value for row in range(4, 7)]
            self.assertEqual(
                actual,
                [
                    from_excel(to_excel(expected[record.name]))
                    for record in sorted(records, key=lambda item: item.name)
                ],
            )
        finally:
            workbook.close()

    def test_sse_client_disconnect_does_not_cancel_native_tool_loop(self):
        """The server must finish tool/model work even if the SSE reader closes."""
        events = []

        def generate(*args, **kwargs):
            events.append("assistant_tool_call")
            yield {"type": "message_create", "message": {"id": 1}}
            events.append("tool_result_processed")
            yield {"type": "message_update", "message": {"id": 2}}
            events.append("assistant_followup_processed")
            yield {"type": "message_create", "message": {"id": 3}}

        thread = SimpleNamespace(exists=lambda: True, generate=generate)
        model = SimpleNamespace(browse=lambda _thread_id: thread)
        class FakeEnv:
            uid = self.env.uid
            context = dict(self.env.context)

            def __getitem__(self, _name):
                return model

        env = FakeEnv()
        cursor = SimpleNamespace()

        class CursorContext:
            def __enter__(self):
                return cursor

            def __exit__(self, *_args):
                return False

        cursor_context = CursorContext()
        registry = SimpleNamespace(cursor=lambda: cursor_context)

        with (
            patch("odoo.addons.llm_thread.controllers.main.Registry", return_value=registry),
            patch("odoo.addons.llm_thread.controllers.main.api.Environment", return_value=env),
        ):
            response = LLMThreadController._llm_thread_generate(
                "test_db", env, 4242, None
            )
            next(response)
            response.close()

        self.assertEqual(
            events,
            ["assistant_tool_call", "tool_result_processed", "assistant_followup_processed"],
        )

    def test_native_docx_context_and_mapping_preview_use_generic_paragraph_targets(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Native DOCX thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        target = self.env["res.partner"].create(
            {"name": "DOCX target " + uuid4().hex, "company_id": self.env.company.id}
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "native-office-" + uuid4().hex + ".docx",
                "type": "binary",
                "mimetype": DOCX_MIME,
                "raw": _docx(),
                "company_id": self.env.company.id,
            }
        )
        thread.message_post(
            body="Fill the contact paragraph",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "docx-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )

        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        self.assertEqual(context["document_format"], "docx")
        self.assertIn("docx:p:1", {item["element_id"] for item in context["target_manifest"]})
        self.assertIn("docx:table:1:row:1:cell:2:p:1", {item["element_id"] for item in context["target_manifest"]})
        self.assertIn("docx_simple_paragraph_replacement", context["mapping_limits"]["supported"])
        self.assertNotIn("docx", context["mapping_limits"]["unsupported"])
        result = tool.office_save_mapping_preview(
            context["session_id"],
            context["revision"],
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {
                        "element_id": "docx:p:1",
                        "source_field": "name",
                        "value_type": "string",
                    }
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )

        self.assertEqual(result["status"], "success")
        preview = self.env["office.mapping.session"].browse(context["session_id"]).preview_attachment_id
        self.assertTrue(preview.name.endswith(".docx"))
        rendered = Document(BytesIO(preview.raw))
        self.assertEqual(rendered.paragraphs[0].text, target.name)

    def test_finalize_gate_accepts_only_exact_supported_confirmation_phrases(self):
        self.assertTrue(_is_explicit_finalize_confirmation("<p>确认并生成正式文件</p>"))
        self.assertTrue(_is_explicit_finalize_confirmation("<p>确认生成正式文件</p>"))
        self.assertFalse(_is_explicit_finalize_confirmation("请确认并生成正式文件"))
        self.assertFalse(_is_explicit_finalize_confirmation("确认并生成正式文件：S05457"))

    def test_finalize_carries_current_turn_confirmation_into_isolated_transaction(self):
        """The current user message is uncommitted while the LLM tool opens a root cursor."""
        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        preview = SimpleNamespace(
            id=987654320,
            raw=b"synthetic validated preview bytes",
            check_access=lambda _mode: None,
        )
        session = SimpleNamespace(
            id=700,
            thread_id=thread,
            owner_id=self.env.user,
            revision=9,
            proposal_revision=4,
            preview_proposal_revision=4,
            confirmed_revision=0,
            state="confirmation_required",
            preview_attachment_id=preview,
            invalidate_recordset=lambda *_args: None,
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=confirmation)
        result_metadata = {
            "status": "finalized",
            "state": "completed",
            "output_attachment_id": 987654321,
            "filename": "office-output-verified.xlsx",
            "mimetype": XLSX_MIME,
            "delivery_message_id": 987654322,
            "attachment_posted_to_thread": True,
        }

        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.finalize_confirmed_mapping_in_isolated_transaction",
                return_value=result_metadata,
            ) as isolated_finalize,
        ):
            result = tool_model.office_finalize(session.id, session.revision, session.proposal_revision)

        self.assertEqual(result["status"], "finalized")
        self.assertIn(
            "confirmation_proof",
            isolated_finalize.call_args.kwargs,
            "The root cursor cannot see the uncommitted user message, so the caller must pass an internal scoped proof.",
        )
        proof = isolated_finalize.call_args.kwargs["confirmation_proof"]
        self.assertEqual(proof.thread_id, thread.id)
        self.assertEqual(proof.session_id, session.id)
        self.assertEqual(proof.owner_id, self.env.uid)
        self.assertEqual(proof.user_message_id, confirmation.id)
        self.assertEqual(proof.session_revision, session.revision)
        self.assertEqual(proof.proposal_revision, session.proposal_revision)
        self.assertEqual(proof.preview_attachment_id, preview.id)

    def test_finalize_uses_committed_output_metadata_without_reloading_stale_attachment(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=701,
            thread_id=thread,
            owner_id=self.env.user,
            revision=9,
            proposal_revision=4,
            preview_proposal_revision=4,
            confirmed_revision=4,
            state="confirmation_required",
            preview_attachment_id=SimpleNamespace(
                id=987654320,
                raw=b"synthetic validated preview bytes",
                check_access=lambda _mode: None,
            ),
            invalidate_recordset=lambda *_args: None,
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=confirmation)
        result_metadata = {
            "state": "completed",
            "output_attachment_id": 987654321,
            "filename": "office-output-verified.xlsx",
            "mimetype": XLSX_MIME,
            "download_url": "/web/content/987654321?download=true",
            "delivery_message_id": 987654322,
        }
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.finalize_confirmed_mapping_in_isolated_transaction",
                side_effect=_finalize_inline_for_transactioncase,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.render_confirmed_mapping",
                return_value=result_metadata,
            ),
            patch.object(
                type(self.env["ir.attachment"]),
                "browse",
                side_effect=AssertionError("Finalize must not re-read M1's committed attachment in the stale cursor"),
            ),
        ):
            result = tool_model.office_finalize(session.id, session.revision, session.proposal_revision)

        self.assertEqual(result["status"], "finalized")
        self.assertEqual(result["filename"], result_metadata["filename"])
        self.assertEqual(result["mimetype"], XLSX_MIME)
        self.assertEqual(result["attachment_id"], result_metadata["output_attachment_id"])
        self.assertEqual(result["delivery_message_id"], result_metadata["delivery_message_id"])
        self.assertTrue(result["attachment_posted_to_thread"])

    def test_finalize_replay_returns_same_committed_delivery_after_session_completed(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        replay_message = thread.message_post(
            body="请重新显示刚生成的正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=702,
            thread_id=thread,
            owner_id=self.env.user,
            revision=12,
            proposal_revision=4,
            preview_proposal_revision=4,
            confirmed_revision=4,
            state="completed",
            invalidate_recordset=lambda *_args: None,
        )
        existing = {
            "state": "completed",
            "output_attachment_id": 987654321,
            "filename": "office-output-verified.xlsx",
            "mimetype": XLSX_MIME,
            "download_url": "/web/content/987654321?download=true",
            "delivery_message_id": 987654322,
        }
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.finalize_confirmed_mapping_in_isolated_transaction",
                side_effect=_finalize_inline_for_transactioncase,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.render_confirmed_mapping",
                return_value=existing,
            ),
        ):
            result = self.env["office.mapping.tool"].with_context(message=replay_message).office_finalize(
                session.id, expected_revision=9, proposal_revision=session.proposal_revision
            )

        self.assertEqual(result["status"], "finalized")
        self.assertEqual(result["attachment_id"], existing["output_attachment_id"])
        self.assertEqual(result["delivery_message_id"], existing["delivery_message_id"])

    def test_finalize_stale_revision_returns_structured_failure(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=703,
            thread_id=thread,
            owner_id=self.env.user,
            revision=12,
            proposal_revision=5,
            preview_proposal_revision=5,
            confirmed_revision=5,
            state="confirmation_required",
            preview_attachment_id=SimpleNamespace(
                id=987654323,
                raw=b"synthetic stale preview bytes",
                check_access=lambda _mode: None,
            ),
            invalidate_recordset=lambda *_args: None,
        )
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.finalize_confirmed_mapping_in_isolated_transaction",
                side_effect=_finalize_inline_for_transactioncase,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
        ):
            result = self.env["office.mapping.tool"].with_context(message=confirmation).office_finalize(
                session.id, expected_revision=12, proposal_revision=4
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "mapping_revision_stale")

    def test_finalize_reports_generated_artifact_when_chat_delivery_is_pending(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=704,
            thread_id=thread,
            owner_id=self.env.user,
            revision=15,
            proposal_revision=8,
            preview_proposal_revision=8,
            confirmed_revision=0,
            state="confirmation_required",
            preview_attachment_id=SimpleNamespace(
                id=987654324,
                raw=b"synthetic pending-delivery preview bytes",
                check_access=lambda _mode: None,
            ),
            invalidate_recordset=lambda *_args: None,
        )
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.finalize_confirmed_mapping_in_isolated_transaction",
                side_effect=_finalize_inline_for_transactioncase,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.render_confirmed_mapping",
                return_value={
                    "state": "failed",
                    "revision": 18,
                    "error_code": "office_delivery_pending",
                    "failed_stage": "chat_delivery",
                    "artifact_state": "generated",
                    "delivery_state": "pending",
                    "message": "Artifact exists; chat message publication must be retried.",
                    "output_attachment_id": False,
                },
            ),
        ):
            result = self.env["office.mapping.tool"].with_context(message=confirmation).office_finalize(
                session.id, session.revision, session.proposal_revision
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["artifact_state"], "generated")
        self.assertEqual(result["delivery_state"], "pending")
        self.assertEqual(result["failed_stage"], "chat_delivery")
        self.assertFalse(result.get("attachment_id"))
        self.assertEqual(
            result["message"],
            "Artifact exists; chat message publication must be retried.",
        )

    def test_finalize_emits_committed_attachment_message_to_live_store(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        self._activate_legacy_m1_session(thread, _source, _upload)
        result = {
            "status": "finalized",
            "attachment_id": 901,
            "delivery_message_id": 902,
            "attachment_posted_to_thread": True,
        }
        tool_message = SimpleNamespace(get_tool_data=lambda: {"result": result})

        def execute_tool_call(_thread, _tool_call, _assistant_message):
            yield {"type": "message_create", "message": {"id": 900}}
            return tool_message

        message_data = {"id": 902, "attachment_ids": [901]}
        store_data = {
            "mail.message": [message_data],
            "ir.attachment": [{"id": 901, "name": "office-output.xlsx", "mimetype": XLSX_MIME}],
        }
        with (
            patch.object(AssistantThread, "_execute_tool_call", execute_tool_call),
            patch.object(
                type(thread),
                "_office_committed_message_store_payload",
                return_value=(message_data, store_data),
            ),
        ):
            events = list(
                thread._execute_tool_call(
                    {"function": {"name": "office_finalize"}}, assistant_message=None
                )
            )

        self.assertEqual(events[-1]["type"], "message_create")
        self.assertEqual(events[-1]["message"], message_data)
        self.assertEqual(events[-1]["store_data"], store_data)

    def test_finalize_store_failure_updates_tool_result_and_live_message(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        self._activate_legacy_m1_session(thread, _source, _upload)
        tool_data = {
            "status": "completed",
            "result": {
                "status": "finalized",
                "attachment_id": 911,
                "delivery_message_id": 912,
                "attachment_posted_to_thread": True,
            },
        }

        class ToolMessage:
            def get_tool_data(self):
                return tool_data

            def write(self, values):
                tool_data.update(values["body_json"])

            def to_store_format(self):
                return {"id": 910, "body_json": tool_data}

        tool_message = ToolMessage()

        def execute_tool_call(_thread, _tool_call, _assistant_message):
            yield {"type": "message_create", "message": {"id": 910}}
            return tool_message

        with (
            patch.object(AssistantThread, "_execute_tool_call", execute_tool_call),
            patch.object(
                type(thread),
                "_office_committed_message_store_payload",
                side_effect=UserError("attachment read failed"),
            ),
        ):
            events = list(
                thread._execute_tool_call(
                    {"function": {"name": "office_finalize"}}, assistant_message=None
                )
            )

        self.assertEqual(tool_data["status"], "error")
        self.assertEqual(tool_data["result"]["status"], "failed")
        self.assertEqual(tool_data["result"]["error_code"], "final_attachment_not_visible")
        self.assertEqual(events[-1]["type"], "message_update")
        self.assertEqual(events[-1]["message"]["body_json"]["result"]["status"], "failed")

    def test_candidate_b_office_finalize_streams_attachment_card_to_live_store(self):
        thread, _source, _upload = self._office_message("Please deliver the accepted workbook")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "candidate-b-final.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
                "public": False,
            }
        )
        delivery_message = thread.message_post(
            body="Finalized workbook: candidate-b-final.xlsx",
            llm_role="assistant",
            author_id=False,
            attachment_ids=[attachment.id],
        )
        tool_call = {
            "id": "call_candidate_b_finalize",
            "type": "function",
            "function": {"name": "office", "arguments": '{"action":"finalize"}'},
        }
        tool_data = {
            "type": "tool_execution",
            "tool_call_id": tool_call["id"],
            "tool_call": tool_call,
            "tool_name": "office",
            "arguments": {"action": "finalize"},
            "status": "completed",
            "result": {
                "action": "finalize",
                "status": "completed",
                "operation_status": "finalized",
                "delivery_state": "delivered",
                "attachment_posted_to_thread": True,
                "attachment_id": attachment.id,
                "delivery_message_id": delivery_message.id,
            },
        }
        tool_result_message = thread.message_post(
            body="Finalize tool result",
            llm_role="tool",
            body_json=tool_data,
        )
        assistant_message = thread.message_post(body="Finalize tool call", llm_role="assistant")

        def execute_tool(_thread, _call, _assistant_message):
            yield {"type": "message_create", "message": tool_result_message.to_store_format()}
            return tool_result_message

        with patch.object(AssistantThread, "_execute_tool_call", autospec=True, side_effect=execute_tool):
            events = list(thread._execute_tool_call(tool_call, assistant_message))

        attachment_events = [
            event for event in events
            if event.get("type") == "message_create"
            and event.get("message", {}).get("id") == delivery_message.id
        ]
        self.assertEqual(len(attachment_events), 1)
        event = attachment_events[0]
        self.assertIn("mail.message", event["store_data"])
        self.assertIn("ir.attachment", event["store_data"])
        stored_attachment = next(
            item for item in event["store_data"]["ir.attachment"] if item["id"] == attachment.id
        )
        self.assertEqual(stored_attachment["name"], attachment.name)
        self.assertEqual(stored_attachment["mimetype"], XLSX_MIME)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "Native Office test " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "multimodal",
            }
        )

    def _office_message(self, body, raw=None):
        thread = self.env["llm.thread"].create(
            {
                "name": "Native Office thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "native-office-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": raw or _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        message = thread.message_post(
            body=body,
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        return thread, attachment, message

    def _activate_legacy_m1_session(self, thread, attachment, upload):
        """Keep legacy mapping-tool tests on the explicit M1 route."""
        target = self.env["res.partner"].create({
            "name": "M1 route test target " + uuid4().hex,
            "company_id": self.env.company.id,
        })
        return create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=upload.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )

    def _save_repeat_rows_with_user_confirmation(
        self, tool, thread, session, proposal, **operation
    ):
        """Exercise the real two-call structural confirmation flow in tests."""
        revision = session.revision
        prior_preview_id = session.preview_attachment_id.id or False
        result = tool.office_save_mapping_preview(
            session.id, revision, proposal, **operation
        )
        if result.get("status") != "needs_confirmation":
            return result

        self.assertFalse(result.get("operation_executed"), result)
        self.assertIn(
            result.get("risk_type"),
            {"repeat_row_range_expansion", "multiple_business_risks"},
            result,
        )
        self.assertEqual(session.revision, revision)
        self.assertEqual(session.preview_attachment_id.id or False, prior_preview_id)
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        return tool.with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            revision,
            proposal,
            **operation,
            force_override=True,
        )

    def test_prepare_context_returns_chat_recoverable_result_when_template_is_missing(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "No-template Office thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        message = thread.message_post(
            body="Please fill the workbook",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        target = self.env["res.partner"].create(
            {"name": "No-template target " + uuid4().hex, "company_id": self.env.company.id}
        )

        result = self.env["office.mapping.tool"].with_context(message=message).office_prepare_context(
            "res.partner", target.id
        )

        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["error_code"], "office_template_missing")
        self.assertIn("attach one", result["message"])
        self.assertFalse(thread._office_active_session())

    def test_prepare_context_reuses_thread_bound_session_when_followup_omits_record_identity(self):
        thread, _attachment, upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {"name": "Bound Session target " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)

        initial = tool.office_prepare_context("res.partner", target.id)
        resumed = tool.office_prepare_context("unknown", 0)

        self.assertEqual(initial["status"], "ready")
        self.assertEqual(resumed["status"], "ready")
        self.assertEqual(resumed["session_id"], initial["session_id"])
        self.assertEqual(resumed["target_model"], "res.partner")
        self.assertEqual(resumed["target_record_id"], target.id)
        self.assertEqual(resumed["revision"], initial["revision"])

    def test_assistant_html_and_markdown_render_without_literal_tags_or_fake_attachment_links(self):
        thread = self.env["llm.thread"]
        response = (
            "&lt;p&gt;预览已生成。&lt;/p&gt; "
            "&lt;ul&gt;&lt;li&gt;&lt;strong&gt;地址&lt;/strong&gt;：完整地址&lt;/li&gt;&lt;/ul&gt; "
            "&lt;div class=\"attachment-card\"&gt;"
            "&lt;a href=\"attachment://15727\"&gt;preview_S05457.xlsx&lt;/a&gt;&lt;/div&gt;"
        )

        rendered = thread._process_llm_body(response)
        plain = tools.html2plaintext(str(rendered), include_references=False)

        self.assertIn("<p>预览已生成。</p>", str(rendered))
        self.assertIn("<strong>地址</strong>", str(rendered))
        self.assertNotIn("&lt;p&gt;", str(rendered))
        self.assertNotIn("attachment://", str(rendered))
        self.assertNotIn("attachment-card", str(rendered))
        self.assertNotIn("<p>", plain)
        self.assertIn("preview_S05457.xlsx", plain)
        self.assertIn("<strong>Markdown</strong>", str(thread._process_llm_body("**Markdown**")))

    def test_office_candidate_download_href_trailing_space_is_normalized(self):
        from markupsafe import Markup

        thread, _attachment, _message = self._office_message("Review this synthetic workbook")
        response = (
            '<p><a href="/web/content/38112?download=true%20">下载 Candidate</a> '
            '<a href="https://example.invalid/?download=true%20">external</a></p>'
        )

        processed = thread._process_llm_body(response)
        rendered = str(processed)

        self.assertIsInstance(processed, Markup)
        self.assertIn("<a ", rendered)
        self.assertIn('href="/web/content/38112?download=true"', rendered)
        self.assertNotIn('/web/content/38112?download=true%20', rendered)
        self.assertIn('href="https://example.invalid/?download=true%20"', rendered)

    def test_preview_tool_streams_attachment_metadata_to_native_chat_store(self):
        thread, _source_attachment, _source_message = self._office_message(
            "Fill this workbook"
        )
        self._activate_legacy_m1_session(thread, _source_attachment, _source_message)
        preview = self.env["ir.attachment"].create(
            {
                "name": "preview_store_payload.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        tool_call = {
            "id": "call_preview_store_payload",
            "type": "function",
            "function": {
                "name": "office_save_mapping_preview",
                "arguments": "{}",
            },
        }
        preview_message = thread.message_post(
            body="已生成并通过回读验证的 Office 预览。",
            llm_role="assistant",
            author_id=False,
            attachment_ids=[preview.id],
        )
        tool_result_message = thread.message_post(
            body="Preview tool result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": tool_call["id"],
                "tool_call": tool_call,
                "tool_name": "office_save_mapping_preview",
                "arguments": {},
                "status": "completed",
                "result": {
                    "status": "success",
                    "operation_status": "preview_ready",
                    "preview_attachment_id": preview.id,
                    "filename": preview.name,
                    "attachment_posted_to_thread": True,
                    "attachment": {
                        "id": preview.id,
                        "name": preview.name,
                        "mimetype": XLSX_MIME,
                        "message_id": preview_message.id,
                    },
                },
            },
        )
        assistant_message = thread.message_post(
            body="Preview tool call",
            llm_role="assistant",
        )

        def execute_tool(_thread, _call, _assistant_message):
            yield {
                "type": "message_create",
                "message": tool_result_message.to_store_format(),
            }
            return tool_result_message

        with patch.object(
            AssistantThread,
            "_execute_tool_call",
            autospec=True,
            side_effect=execute_tool,
        ):
            events = list(thread._execute_tool_call(tool_call, assistant_message))

        preview_events = [
            event
            for event in events
            if event.get("type") == "message_create"
            and event.get("message", {}).get("id") == preview_message.id
        ]
        self.assertEqual(len(preview_events), 1)
        event = preview_events[0]
        self.assertIn("mail.message", event["store_data"])
        self.assertIn("ir.attachment", event["store_data"])
        stored_attachment = next(
            item
            for item in event["store_data"]["ir.attachment"]
            if item["id"] == preview.id
        )
        self.assertEqual(stored_attachment["name"], preview.name)
        self.assertEqual(stored_attachment["mimetype"], XLSX_MIME)
        self.assertEqual(event["message"]["id"], preview_message.id)

    def test_partial_mapping_update_preserves_other_rules_and_returns_published_attachment(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        for coordinate in ("B3", "F16"):
            sheet[coordinate].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet.merge_cells("E17:H17")
        sheet["E17"] = "old reference"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread = self.env["llm.thread"].create(
            {
                "name": "Incremental mapping thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "incremental-mapping.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": output.getvalue(),
                "company_id": self.env.company.id,
            }
        )
        upload = thread.message_post(
            body="Fill this workbook",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        target = self.env["res.partner"].create(
            {
                "name": "Incremental target " + uuid4().hex,
                "email": "first@example.test",
                "phone": "+1-555-0100",
                "company_id": self.env.company.id,
            }
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "incremental-target-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name", "email", "phone"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        first = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B3", "source_field": "name", "value_type": "string"},
                    {"element_id": "xlsx:Data!F16", "source_field": "email", "value_type": "string"},
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(first["status"], "success", first)

        # This is a true patch: only F16 and F17 are mentioned in this turn.
        patch = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Data!F16", "source_field": "phone", "value_type": "string"},
                {"element_id": "F17", "value": ""},
            ],
            "clarifications": [],
            "skipped_targets": [],
            "clear_targets": ["F17"],
        }
        second = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            patch,
        )

        self.assertEqual(second["status"], "needs_confirmation", second)
        self.assertFalse(second["operation_executed"])
        self.assertEqual(second["affected_scope"], ["xlsx:Data!E17"])
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        second = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            patch,
            force_override=True,
        )
        self.assertEqual(second["status"], "success", second)
        self.assertEqual(second["operation_status"], "preview_ready")
        saved = json.loads(session.mapping_rules_json)
        self.assertEqual(
            {item["element_id"]: item.get("source_field") for item in saved["mappings"]},
            {"xlsx:Data!B3": "name", "xlsx:Data!F16": "phone"},
        )
        self.assertEqual(saved["clear_targets"], ["xlsx:Data!E17"])
        final_preview = session.preview_attachment_id
        rendered = load_workbook(BytesIO(final_preview.raw), data_only=False)
        try:
            self.assertEqual(rendered["Data"]["B3"].value, target.name)
            self.assertEqual(rendered["Data"]["F16"].value, target.phone)
            self.assertIsNone(rendered["Data"]["E17"].value)
            self.assertIsNone(rendered["Data"]["F17"].value)
        finally:
            rendered.close()

        self.assertTrue(second["attachment_posted_to_thread"])
        self.assertEqual(
            second["attachment"],
            {
                "id": final_preview.id,
                "name": final_preview.name,
                "mimetype": XLSX_MIME,
                "message_id": second["message_id"],
            },
        )
        posted_message = self.env["mail.message"].browse(second["message_id"])
        self.assertIn(final_preview, posted_message.attachment_ids)
        self.assertEqual(posted_message.model, "llm.thread")
        self.assertEqual(posted_message.res_id, thread.id)

    def test_merged_range_alias_normalizes_to_the_single_writable_anchor(self):
        manifest = [
            {
                "element_id": "xlsx:Data!E17",
                "merge_range": "E17:H17",
                "write_target": "xlsx:Data!E17",
                "writable": True,
            }
        ]
        rules = {
            "mappings": [{"element_id": "E17:H17", "value": ""}],
            "clear_targets": ["E17:H17"],
            "skipped_targets": [],
            "clarifications": [],
        }

        _normalize_merged_target_aliases(rules, manifest)

        self.assertEqual(rules["mappings"][0]["element_id"], "xlsx:Data!E17")
        self.assertEqual(rules["clear_targets"], ["xlsx:Data!E17"])

        qualified = {
            "mappings": [{"element_id": "xlsx:Data!E17:H17", "value": ""}],
            "clear_targets": [],
            "skipped_targets": [],
            "clarifications": [],
        }
        _normalize_merged_target_aliases(qualified, manifest)
        self.assertEqual(qualified["mappings"][0]["element_id"], "xlsx:Data!E17")

        ambiguous_manifest = manifest + [
            {
                "element_id": "xlsx:Other!E17",
                "merge_range": "E17:H17",
                "write_target": "xlsx:Other!E17",
                "writable": True,
            }
        ]
        ambiguous = {
            "mappings": [{"element_id": "E17:H17", "value": ""}],
            "clear_targets": [],
            "skipped_targets": [],
            "clarifications": [],
        }
        _normalize_merged_target_aliases(ambiguous, ambiguous_manifest)
        self.assertEqual(ambiguous["mappings"][0]["element_id"], "E17:H17")

    def test_restore_current_proposal_returns_existing_preview_instead_of_history_error(self):
        thread, attachment, _upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {"name": "Current revision target " + uuid4().hex, "company_id": self.env.company.id}
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "current-revision-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", target.id]], "fields": ["id", "name"], "limit": 1},
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        generated = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [{"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(generated["status"], "success", generated)
        proposal_revision = session.proposal_revision
        revision = session.revision
        preview_id = session.preview_attachment_id.id

        restored = tool.office_restore_proposal_revision(session.id, revision, proposal_revision)

        self.assertEqual(restored["status"], "unchanged")
        self.assertEqual(restored["restored_from_proposal_revision"], proposal_revision)
        self.assertEqual(restored["preview_attachment_id"], preview_id)
        self.assertTrue(restored["attachment_posted_to_thread"])
        self.assertEqual(session.revision, revision)
        self.assertEqual(session.preview_attachment_id.id, preview_id)

    def test_historical_restore_creates_new_revision_and_publishes_restored_preview(self):
        thread, _attachment, _upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {
                "name": "Historical restore target " + uuid4().hex,
                "email": "historical@example.test",
                "company_id": self.env.company.id,
            }
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "historical-restore-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name", "email"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name, "email": target.email}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        first_proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        first = tool.office_save_mapping_preview(session.id, session.revision, first_proposal)
        self.assertEqual(first["status"], "success", first)
        self.assertEqual(session.proposal_revision, 1)

        second = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                **first_proposal,
                "mappings": [
                    {"element_id": "xlsx:Sheet!B1", "source_field": "email", "value_type": "string"}
                ],
            },
        )
        self.assertEqual(second["status"], "success", second)
        self.assertEqual(session.proposal_revision, 2)

        restored = tool.office_restore_proposal_revision(
            session.id, session.revision, proposal_revision=1
        )

        self.assertEqual(restored["status"], "preview_ready", restored)
        self.assertEqual(restored["restored_from_proposal_revision"], 1)
        self.assertEqual(session.proposal_revision, 3)
        self.assertEqual(json.loads(session.mapping_rules_json), first_proposal)
        self.assertTrue(restored["attachment_posted_to_thread"])
        preview = session.preview_attachment_id
        self.assertEqual(restored["preview_attachment_id"], preview.id)
        posted = self.env["mail.message"].browse(restored["message_id"])
        self.assertEqual((posted.model, posted.res_id), ("llm.thread", thread.id))
        self.assertIn(preview, posted.attachment_ids)
        workbook = load_workbook(BytesIO(preview.raw), data_only=False)
        try:
            self.assertEqual(workbook["Sheet"]["B1"].value, target.name)
        finally:
            workbook.close()

    def test_preview_failure_rolls_back_patch_and_preserves_previous_preview_delivery(self):
        thread, _attachment, _upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {
                "name": "Preview rollback target " + uuid4().hex,
                "email": "before@example.test",
                "company_id": self.env.company.id,
            }
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "preview-rollback-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name", "email"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name, "email": target.email}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        original = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        generated = tool.office_save_mapping_preview(session.id, session.revision, original)
        self.assertEqual(generated["status"], "success", generated)
        session.invalidate_recordset()
        original_rules = session.mapping_rules_json
        original_revision = session.revision
        original_proposal_revision = session.proposal_revision
        original_preview = session.preview_attachment_id
        original_message_ids = thread.message_ids.ids

        with patch(
            "odoo.addons.office_engine_m2.models.office_mapping_tools.render_preview",
            side_effect=UserError("synthetic preview rendering failure"),
        ):
            failed = tool.office_save_mapping_preview(
                session.id,
                session.revision,
                {
                    **original,
                    "mappings": [
                        {"element_id": "xlsx:Sheet!B1", "source_field": "email", "value_type": "string"}
                    ],
                },
            )

        self.assertEqual(failed["status"], "error", failed)
        self.assertFalse(failed["operation_executed"])
        self.assertIn("synthetic preview rendering failure", failed["message"])

        session.invalidate_recordset()
        self.assertEqual(session.mapping_rules_json, original_rules)
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.proposal_revision, original_proposal_revision)
        self.assertEqual(session.preview_attachment_id, original_preview)
        self.assertTrue(original_preview.exists())
        self.assertEqual(thread.message_ids.ids, original_message_ids)
        self.assertTrue(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("attachment_ids", "in", [original_preview.id]),
                ]
            )
        )

    def test_related_full_address_is_discovered_only_through_readable_relations(self):
        fields = _field_candidates(self.env, self.env.company)
        self.assertEqual(fields.get("partner_id.contact_address"), "string")

        root = self.env["res.partner"].create(
            {"name": "Address root " + uuid4().hex, "company_id": self.env.company.id}
        )
        parent = self.env["res.partner"].create(
            {"name": "Address parent " + uuid4().hex, "parent_id": root.id, "company_id": self.env.company.id}
        )
        target = self.env["res.partner"].create(
            {"name": "Address target " + uuid4().hex, "parent_id": parent.id, "company_id": self.env.company.id}
        )
        nested_fields = _field_candidates(self.env, target)
        self.assertEqual(nested_fields.get("parent_id.parent_id.contact_address"), "string")

    def test_fallback_uses_second_authorized_address_when_first_is_empty(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Address fallback thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "address-fallback.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        source_message = thread.message_post(
            body="Use the available company address",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        inspection = inspect_document(attachment.raw, attachment.name, attachment.mimetype, _resource_budget())
        manifest, template_text = _template_context(inspection)
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=source_message.id,
            source_attachment_id=attachment.id,
            target_model="res.company",
            target_record_id=self.env.company.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        set_mapping_context(
            self.env,
            session.id,
            manifest,
            {"partner_id.contact_address": "string", "partner_id.street": "string"},
            template_text=template_text,
        )
        rules = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {
                    "element_id": "xlsx:Sheet!B1",
                    "source_fields": ["partner_id.contact_address", "partner_id.street"],
                    "value_type": "string",
                }
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        session._save_mapping_from_service(json.dumps(rules), session.revision, "revision_pending")

        with patch(
            "odoo.addons.office_engine_m2.services.render_bridge._retrieve_record",
            return_value={
                "partner_id.contact_address": False,
                "partner_id.street": "250 Executive Park Blvd, Suite 3400, San Francisco, CA 94134",
            },
        ):
            plan, _snapshot_hash, _summary = _compile_plan(self.env, session)

        self.assertEqual(
            plan["writes"],
            [
                {
                    "element_id": "xlsx:Sheet!B1",
                    "operation": "set_value",
                    "value": {
                        "type": "string",
                        "data": "250 Executive Park Blvd, Suite 3400, San Francisco, CA 94134",
                    },
                }
            ],
        )

    def test_openai_payload_keeps_user_text_and_excludes_office_attachment_bytes(self):
        instruction = "如果订单没有仓库，b4就用本公司地址。"
        thread, attachment, message = self._office_message(instruction)

        # The same native history used by llm_assistant still contains the upload.
        self.assertIn(message, thread.get_llm_messages())
        payload = message.openai_format_message(is_multimodal=True)
        self.assertEqual(payload, {"role": "user", "content": instruction})
        self.assertEqual(message._get_attachments_by_mimetype((XLSX_MIME,)), self.env["ir.attachment"])
        encoded = attachment.datas
        if isinstance(encoded, bytes):
            encoded = encoded.decode("ascii")
        self.assertNotIn(encoded, json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("base64", json.dumps(payload, ensure_ascii=False).lower())

    def test_linked_chat_thread_reuses_parent_office_tools_and_template(self):
        parent, attachment, upload = self._office_message("已上传的模板")
        child = self.env["llm.thread"].create(
            {
                "name": "Linked chat thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
                "model": "llm.thread",
                "res_id": parent.id,
            }
        )
        linked_attachment_ids = child._office_linked_template_attachment_ids([])
        self.assertEqual(linked_attachment_ids, [attachment.id])
        child_upload = child.message_post(
            body="用可读的业务记录填写已上传模板",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=linked_attachment_ids,
        )

        # The chatter's AI Chat creates a linked child Thread. It must inherit
        # Office capability and carry the existing attachment reference on the
        # first native child-chat turn. This lets existing M1 request validation
        # work while the Provider serializer keeps Office bytes out of payloads.
        self.assertTrue(child._office_is_active())
        found_upload, found_attachment = child._office_latest_upload()
        self.assertEqual(found_upload, child_upload)
        self.assertEqual(found_attachment, attachment)
        self.assertFalse(child._office_linked_template_attachment_ids([]))
        provider_payload = child_upload.openai_format_message(is_multimodal=True)
        self.assertEqual(provider_payload, {"role": "user", "content": "用可读的业务记录填写已上传模板"})
        self.assertEqual(
            set(child._office_bind_tools().mapped("name")),
            {
                "office",
                "office_prepare_context",
                "office_save_mapping_preview",
                "office_restore_proposal_revision",
                "office_finalize",
                "odoo_record_retriever",
            },
        )

        target = self.env["res.partner"].create(
            {"name": "Linked child target " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool_message = child.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "linked-child-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", target.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        context = self.env["office.mapping.tool"].with_context(message=tool_message).office_prepare_context(
            "res.partner", target.id
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.thread_id, child)
        self.assertEqual(session.source_message_id, child_upload)
        self.assertEqual(session.source_attachment_id, attachment)

    def test_template_targets_are_optional_even_when_next_to_labels(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["A1"] = "Customer:"
        sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet["B4"] = "Warehouse address"
        sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet["B6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

        inspection = inspect_document(output.getvalue(), "labels.xlsx", XLSX_MIME, _resource_budget())
        manifest, _template_text = _template_context(inspection)
        required_by_id = {item["element_id"]: item["required"] for item in manifest}

        self.assertFalse(required_by_id["xlsx:Data!B1"])
        self.assertFalse(required_by_id["xlsx:Data!B5"])
        self.assertFalse(required_by_id["xlsx:Data!B6"])

    def test_office_message_is_one_native_user_message_not_reposted_by_m2(self):
        thread, _attachment, message = self._office_message("Read this workbook")
        self.assertEqual(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "user"),
                    ("body", "ilike", "Read this workbook"),
                ]
            ),
            1,
        )
        self.assertEqual(message.author_id, self.env.user.partner_id)

    def test_retriever_uses_current_user_model_and_field_rights(self):
        thread, _attachment, message = self._office_message("Fill the workbook")
        retriever = self.env["llm.tool"].with_context(message=message)
        # ``sale`` is intentionally not an addon dependency, so Odoo's
        # isolated module test registry may omit it. In the live 8091
        # environment the same assertion is exercised against sale.order.
        retrieval_model, retrieval_field = (
            ("sale.order", "amount_total")
            if "sale.order" in self.env.registry.models
            else ("res.partner", "email")
        )
        result = retriever.odoo_record_retriever_execute(
            model=retrieval_model,
            domain=[["name", "=", "NO-SUCH-OFFICE-ORDER"]],
            fields=[retrieval_field],
            limit=1,
        )
        self.assertEqual(result, [])

        limited_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Office Retriever Limited User " + uuid4().hex,
                "login": "office-retriever-limited-" + uuid4().hex,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        limited_retriever = self.env["llm.tool"].with_user(limited_user).with_context(message=message)
        with self.assertRaises(AccessError):
            limited_retriever.odoo_record_retriever_execute(
                "ir.config_parameter", [["key", "=", "database.uuid"]], ["key"], 1
            )

    def test_native_retriever_honors_model_limit_for_duplicate_matches(self):
        thread, _attachment, user_message = self._office_message("用同名记录填工作簿")
        duplicate_name = "Office duplicate " + uuid4().hex
        records = self.env["res.partner"].create([
            {"name": duplicate_name, "company_id": self.env.company.id},
            {"name": duplicate_name, "company_id": self.env.company.id},
        ])
        rows = self.env["llm.tool"].with_context(message=user_message).odoo_record_retriever_execute(
            "res.partner", [["name", "=", duplicate_name]], ["id", "name"], 1
        )
        self.assertEqual(len(rows), 1)
        self.assertIn(rows[0]["id"], records.ids)

        # office_prepare_context accepts an ACL-readable target directly; it
        # does not require a Retriever transcript or silently choose a record.
        context = self.env["office.mapping.tool"].with_context(
            message=user_message
        ).office_prepare_context("res.partner", records[0].id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.target_record_id, records[0].id)
        self.assertEqual(session.thread_id, thread)

    def test_native_retriever_pages_with_stable_order_and_current_user_count(self):
        thread, _attachment, user_message = self._office_message("Read these records in pages")
        records = self.env["res.partner"].create(
            [
                {"name": f"Paged partner {index} {uuid4().hex}", "company_id": self.env.company.id}
                for index in range(5)
            ]
        )
        retriever = self.env["llm.tool"].with_context(message=user_message)
        first = retriever.odoo_record_retriever_execute(
            "res.partner",
            [["id", "in", records.ids]],
            ["name"],
            2,
            offset=0,
            order="name asc",
            include_pagination=True,
        )
        second = retriever.odoo_record_retriever_execute(
            "res.partner",
            [["id", "in", records.ids]],
            ["name"],
            2,
            offset=2,
            order="name asc",
            include_pagination=True,
        )
        final = retriever.odoo_record_retriever_execute(
            "res.partner",
            [["id", "in", records.ids]],
            ["name"],
            2,
            offset=4,
            order="name asc",
            include_pagination=True,
        )
        self.assertEqual(first["count"], 5)
        self.assertEqual(first["offset"], 0)
        self.assertTrue(first["has_more"])
        self.assertTrue(second["has_more"])
        self.assertFalse(final["has_more"])
        self.assertEqual(len(first["records"]), 2)
        self.assertEqual(len(second["records"]), 2)
        self.assertEqual(len(final["records"]), 1)
        self.assertEqual(
            [item["name"] for page in (first, second, final) for item in page["records"]],
            sorted(records.mapped("name")),
        )

    def test_selected_root_records_fill_sorted_repeat_rows_without_losing_identity(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Selected-record repeat thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "selected-records.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        upload = thread.message_post(
            body="Fill every selected record into repeated rows",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        names = ["Selected E", "Selected C", "Selected A", "Selected D", "Selected B"]
        records = self.env["res.partner"].create(
            [{"name": name + " " + uuid4().hex, "company_id": self.env.company.id} for name in names]
        )
        retriever_message = thread.message_post(
            body="Retrieved all selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "selected-record-page-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name"],
                    "limit": 100,
                    "offset": 0,
                    "order": "name asc",
                    "include_pagination": True,
                },
                "status": "completed",
                "result": {
                    "records": [{"id": item.id, "name": item.name} for item in records],
                    "count": len(records),
                    "offset": 0,
                    "limit": 100,
                    "has_more": False,
                },
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids
        )
        self.assertEqual(context["source_records"]["count"], len(records))
        selected_collection = next(
            item for item in context["repeat_row_collections"]
            if item["collection_field"] == "selected_records"
        )
        self.assertEqual(selected_collection["row_count"], len(records))
        self.assertIn("name", selected_collection["allowed_fields"])

        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "selected_records",
                    "sheet": "Data",
                    "start_row": 4,
                    "sort_by": "name",
                    "sort_direction": "asc",
                    "columns": [{"column": "B", "source_field": "name"}],
                }
            ],
        )
        self.assertEqual(result["status"], "success", result)
        session.invalidate_recordset(["context_json", "preview_attachment_id"])
        stored_context = json.loads(session.context_json)
        group = stored_context["mapping_groups"][0]
        self.assertEqual(group["record_ids"], records.ids)
        self.assertEqual(len(group["target_rows"]), len(records))
        preview = session.preview_attachment_id
        self.assertTrue(preview.raw)
        workbook = load_workbook(BytesIO(preview.raw), data_only=False)
        self.assertEqual(
            [workbook["Data"][f"B{row}"].value for row in range(4, 9)],
            sorted(records.mapped("name")),
        )
        self.assertEqual(workbook["Data"]["A1"].value, "Parent")
        workbook.close()

    def test_selected_root_records_reauthorize_explicit_retrieved_fields_for_repeat_rows(self):
        """Fields returned by an authorized Retriever remain usable after context refresh."""
        thread, _attachment, user_message = self._office_message(
            "Fill the selected records into repeated rows", raw=_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Explicit field row %s %s" % (index, uuid4().hex),
                "email": "row%s@example.invalid" % index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        tool = self.env["office.mapping.tool"].with_context(message=user_message)
        context = tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["email", "create_date"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertIn("email", context["allowed_fields"])
        self.assertIn("create_date", context["allowed_fields"])
        self.assertEqual(context["unavailable_requested_fields"], [])
        collection = next(
            item for item in context["repeat_row_collections"]
            if item["collection_field"] == "selected_records"
        )
        self.assertIn("email", collection["allowed_fields"])
        self.assertIn("create_date", collection["allowed_fields"])

        result = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "selected_records",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "source_field": "email"},
                        {"column": "D", "source_field": "create_date"},
                    ],
                }
            ],
        )
        self.assertEqual(result["status"], "success", result)
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [workbook["Data"][f"C{row}"].value for row in range(4, 7)],
                records.mapped("email"),
            )
            self.assertTrue(all(workbook["Data"][f"D{row}"].value for row in range(4, 7)))
        finally:
            workbook.close()

    def test_selected_records_generate_preview_for_append_only_template(self):
        thread, _attachment, user_message = self._office_message(
            "Fill selected records into this import sheet", raw=_no_summary_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Append-only record %s %s" % (index, uuid4().hex),
                "email": "append%s@example.invalid" % index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retriever_message = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "append-only-record-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "email"],
                    "limit": 100,
                    "offset": 0,
                    "order": "name asc",
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "email": record.email}
                    for record in records
                ],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []},
            repeat_rows=[
                {
                    "collection_field": "selected_records",
                    "sheet": "Import",
                    "start_row": 2,
                    "sort_by": "name",
                    "sort_direction": "asc",
                    "columns": [
                        {"column": "A", "source_field": "name"},
                        {"column": "B", "source_field": "email"},
                        {"column": "C", "source_field": "email"},
                    ],
                }
            ],
        )
        self.assertEqual(result["status"], "success", result)
        self.assertTrue(session.preview_attachment_id.raw)
        self.assertTrue(session.preview_attachment_id.name.endswith(".xlsx"))
        self.assertEqual(session.preview_attachment_id.mimetype, XLSX_MIME)

        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Import"]
            self.assertEqual(sheet["A1"].value, "Record")
            self.assertEqual(
                [sheet[f"A{row}"].value for row in range(2, 5)],
                sorted(records.mapped("name")),
            )
            by_name = {record.name: record.email for record in records}
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(2, 5)],
                [by_name[name] for name in sorted(by_name)],
            )
            self.assertEqual(
                [sheet[f"C{row}"].value for row in range(2, 5)],
                [by_name[name] for name in sorted(by_name)],
            )
            self.assertEqual(sheet["A4"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["B4"].number_format, "@")
        finally:
            workbook.close()

    def test_repeat_rows_can_clear_an_unmapped_physical_cell_in_data_band(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Import"
        sheet["A1"] = "Record"
        sheet["B1"] = "Email"
        sheet["M1"] = "Summary"
        sheet["A2"] = "example"
        sheet["A2"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
        sheet["B2"] = ""
        sheet["B2"].number_format = "@"
        source = BytesIO()
        workbook.save(source)
        workbook.close()
        thread, _attachment, _user_message = self._office_message(
            "Fill selected records into this import sheet", raw=source.getvalue()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Clearable repeat record %s %s" % (index, uuid4().hex),
                "email": "clearable%s@example.invalid" % index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retriever_message = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "clear-repeat-cell-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "email"],
                    "limit": 10,
                    "offset": 0,
                    "order": "name asc",
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "email": record.email}
                    for record in records
                ],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        repeat_rows = [
            {
                "collection_field": "selected_records",
                "sheet": "Import",
                "start_row": 2,
                "sort_by": "name",
                "sort_direction": "asc",
                "columns": [
                    {"column": "A", "source_field": "name"},
                    {"column": "B", "source_field": "email"},
                ],
            }
        ]
        initial = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=repeat_rows,
        )
        self.assertEqual(initial["status"], "success", initial)
        before_revision = session.revision
        result = tool.office_save_mapping_preview(
            session.id,
            before_revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                # Match the compact blank-write representation emitted by
                # the live model. Sheet-qualified coordinates without the
                # internal xlsx: prefix must still resolve to this sheet.
                "mappings": [
                    {"element_id": f"Import!C{row}", "value": ""}
                    for row in range(2, 5)
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )

        self.assertEqual(result["status"], "success", result)
        self.assertGreater(session.revision, before_revision)
        self.assertEqual(result["revision"], session.revision)
        self.assertEqual(session.preview_attachment_id.file_size, len(session.preview_attachment_id.raw))
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Import"]
            self.assertEqual(sheet["A1"].value, "Record")
            self.assertEqual([sheet[f"A{row}"].value for row in range(2, 5)], sorted(records.mapped("name")))
            by_name = {record.name: record.email for record in records}
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(2, 5)],
                [by_name[name] for name in sorted(by_name)],
            )
            self.assertEqual([sheet[f"C{row}"].value for row in range(2, 5)], [None, None, None])
        finally:
            workbook.close()

        # A model may include the current repeat_rows again when applying a
        # conversational clear. The existing mapped rows and explicit blank
        # writes must remain valid in that full-plan submission.
        retry = self._save_repeat_rows_with_user_confirmation(
            tool, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": f"Import!C{row}", "value": ""}
                    for row in range(2, 5)
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=repeat_rows,
        )
        self.assertEqual(retry["status"], "success", retry)
        self.assertIn(retry["operation_status"], {"preview_ready", "unchanged"})

    def test_explicit_field_discovery_does_not_bypass_current_user_field_acl(self):
        limited_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Office Field ACL User " + uuid4().hex,
                "login": "office-field-acl-" + uuid4().hex,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        user_env = self.env(user=limited_user)
        _records, fields = _selected_record_context(
            user_env, "res.users", [limited_user.id], requested_fields=["totp_secret"]
        )
        self.assertNotIn("totp_secret", fields)

    def test_office_retriever_supports_acl_readable_relational_fields(self):
        thread, _attachment, message = self._office_message("Read the related records")
        parent = self.env["res.partner"].create(
            {"name": "Office relation parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        child = self.env["res.partner"].create(
            {"name": "Office relation child " + uuid4().hex, "parent_id": parent.id}
        )
        retriever = self.env["llm.tool"].with_context(message=message)
        rows = retriever.odoo_record_retriever_execute(
            model="res.partner",
            domain=[["name", "=", parent.name]],
            fields=["id", "name", "child_ids"],
            limit=1,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], parent.id)
        self.assertIn(child.id, rows[0]["child_ids"])

    def test_office_prepare_advertises_repeat_rows_from_readable_one2many(self):
        thread, _attachment, user_message = self._office_message("填充订单明细")
        parent = self.env["res.partner"].create(
            {"name": "Repeat parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Repeat child 1 " + uuid4().hex, "parent_id": parent.id},
            {"name": "Repeat child 2 " + uuid4().hex, "parent_id": parent.id},
        ])
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-parent-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", parent.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        context = self.env["office.mapping.tool"].with_context(
            message=retriever_result
        ).office_prepare_context("res.partner", parent.id)

        self.assertIn("repeat_rows", context["mapping_limits"]["supported"])
        self.assertNotIn("repeat_rows", context["mapping_limits"]["unsupported"])
        candidates = context["repeat_row_collections"]
        candidate = next(item for item in candidates if item["collection_field"] == "child_ids")
        self.assertEqual(candidate["relation_model"], "res.partner")
        self.assertEqual(candidate["row_count"], len(children))
        self.assertIn("name", candidate["allowed_fields"])
        self.assertNotIn("sample", candidate)

    def test_repeat_row_candidates_keep_product_identifiers_and_weight_in_bounded_schema(self):
        class Rows:
            def __bool__(self):
                return True

            def __len__(self):
                return 6

            def check_access(self, _operation):
                return None

        class Target:
            _fields = {
                "order_line": SimpleNamespace(
                    type="one2many", comodel_name="sale.order.line", inverse_name="order_id"
                )
            }

            def check_access(self, _operation):
                return None

            def check_field_access_rights(self, _operation, _field_names):
                return None

            def __getitem__(self, _field_name):
                return Rows()

        discovered_fields = {f"unrelated_{index}": "string" for index in range(200)}
        discovered_fields.update(
            {
                "product_id.default_code": "string",
                "product_id.barcode": "string",
                "product_id.weight": "number",
                "product_id.net_weight": "number",
                "product_uom_qty": "number",
            }
        )
        with patch("odoo.addons.office_engine_m2.services.chat_entrypoint._field_candidates", return_value=discovered_fields):
            candidate = _repeat_row_collection_candidates(self.env, Target())[0]

        self.assertIn("product_id.default_code", candidate["allowed_fields"])
        self.assertIn("product_id.barcode", candidate["allowed_fields"])
        self.assertIn("product_id.weight", candidate["allowed_fields"])
        self.assertIn("product_uom_qty", candidate["allowed_fields"])

    def test_repeat_row_candidates_preserve_direct_fields_before_related_field_overflow(self):
        class Rows:
            def __bool__(self):
                return True

            def __len__(self):
                return 2

            def check_access(self, _operation):
                return None

        class Target:
            _fields = {
                "quant_ids": SimpleNamespace(
                    type="one2many", comodel_name="stock.quant", inverse_name="location_id"
                )
            }

            def check_access(self, _operation):
                return None

            def check_field_access_rights(self, _operation, _field_names):
                return None

            def __getitem__(self, _field_name):
                return Rows()

        discovered_fields = {
            **{f"aaa_relation_{index:03d}.unrelated": "string" for index in range(200)},
            "quantity": "number",
            "reserved_quantity": "number",
            "available_quantity": "number",
            "location_id.complete_name": "string",
            "product_id.default_code": "string",
        }
        with patch(
            "odoo.addons.office_engine_m2.services.chat_entrypoint._field_candidates",
            return_value=discovered_fields,
        ):
            candidate = _repeat_row_collection_candidates(self.env, Target())[0]

        self.assertLessEqual(len(candidate["allowed_fields"]), 160)
        self.assertIn("quantity", candidate["allowed_fields"])
        self.assertIn("reserved_quantity", candidate["allowed_fields"])
        self.assertIn("available_quantity", candidate["allowed_fields"])
        self.assertIn("location_id.complete_name", candidate["allowed_fields"])
        self.assertIn("product_id.default_code", candidate["allowed_fields"])

    def test_repeat_row_candidates_reauthorize_explicit_related_paths_missing_from_discovery(self):
        parent = self.env["res.partner"].create(
            {
                "name": "Requested-path parent " + uuid4().hex,
                "email": "parent@example.test",
                "company_id": self.env.company.id,
            }
        )
        children = self.env["res.partner"].create([
            {"name": "Requested-path child 1 " + uuid4().hex, "parent_id": parent.id},
            {"name": "Requested-path child 2 " + uuid4().hex, "parent_id": parent.id},
        ])
        # Simulate a bounded discovery list in which a valid but lower-ranked
        # related field is omitted. An explicit hint must be authorized against
        # the live rows rather than trusted from this discovery list.
        discovered_fields = {
            **{f"parent_id.unranked_{index:03d}": "string" for index in range(200)},
        }
        with patch(
            "odoo.addons.office_engine_m2.services.chat_entrypoint._field_candidates",
            return_value=discovered_fields,
        ):
            candidate = _repeat_row_collection_candidates(
                self.env,
                parent,
                requested_fields_by_collection={
                    "child_ids": [
                        "parent_id.email",
                        "parent_id.no_such_field",
                        "parent_id.email.extra",
                    ]
                },
            )[0]

        self.assertEqual(candidate["row_count"], len(children))
        self.assertEqual(candidate["allowed_fields"]["parent_id.email"], "string")
        self.assertIn("parent_id.email", candidate["allowed_fields"])
        self.assertEqual(
            candidate["unavailable_requested_fields"],
            ["parent_id.no_such_field", "parent_id.email.extra"],
        )
        self.assertEqual(
            candidate["unavailable_requested_field_reasons"],
            {
                "parent_id.no_such_field": ["field_not_found"],
                "parent_id.email.extra": ["path_segment_is_not_many2one"],
            },
        )

    def test_repeat_row_candidates_reauthorize_related_paths_clipped_by_schema_budget(self):
        parent = self.env["res.partner"].create(
            {
                "name": "Requested-path parent " + uuid4().hex,
                "email": "parent@example.test",
                "company_id": self.env.company.id,
            }
        )
        children = self.env["res.partner"].create([
            {"name": "Requested-path child 1 " + uuid4().hex, "parent_id": parent.id},
            {"name": "Requested-path child 2 " + uuid4().hex, "parent_id": parent.id},
        ])
        # Fill the related-field budget with names that sort before email. The
        # field exists in discovery, but the bounded public schema omits it.
        # An explicit request should still reauthorize just that path.
        discovered_fields = {
            **{f"parent_id.a_unranked_{index:03d}": "string" for index in range(200)},
            "parent_id.email": "string",
        }
        with patch(
            "odoo.addons.office_engine_m2.services.chat_entrypoint._field_candidates",
            return_value=discovered_fields,
        ):
            without_hint = _repeat_row_collection_candidates(self.env, parent)[0]
            candidate = _repeat_row_collection_candidates(
                self.env,
                parent,
                requested_fields_by_collection={
                    "child_ids": ["parent_id.email", "parent_id.no_such_field"]
                },
            )[0]

        self.assertEqual(candidate["row_count"], len(children))
        self.assertEqual(candidate["collection_field"], "child_ids")
        self.assertNotIn("parent_id.email", without_hint["allowed_fields"])
        self.assertEqual(candidate["allowed_fields"]["parent_id.email"], "string")
        self.assertIn("parent_id.email", candidate["allowed_fields"])
        self.assertLessEqual(len(candidate["allowed_fields"]), 160)
        self.assertEqual(len(candidate["allowed_fields"]), 160)
        self.assertEqual(candidate["unavailable_requested_fields"], ["parent_id.no_such_field"])

    def test_office_retriever_uses_requested_domain_inside_active_session(self):
        thread, _attachment, message = self._office_message("读取关联明细")
        parent = self.env["res.partner"].create(
            {"name": "Bound parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Bound child A " + uuid4().hex, "parent_id": parent.id},
            {"name": "Bound child B " + uuid4().hex, "parent_id": parent.id},
        ])
        other = self.env["res.partner"].create(
            {"name": "Other readable record " + uuid4().hex, "company_id": self.env.company.id}
        )
        from ..services.mapping_service import create_session, set_mapping_context

        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=message.attachment_ids.id,
            target_model="res.partner",
            target_record_id=parent.id,
        )
        set_mapping_context(self.env, created["session_id"], [], {"name": "string"})
        retriever = self.env["llm.tool"].with_context(message=message)

        # Even in an active Office Session, the native Retriever receives the
        # supplied model/domain/fields/limit unchanged. The caller's ACLs and
        # record rules are the only record-visibility policy.
        linked_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["parent_id", "=", parent.id]], ["id", "name"], 2
        )
        other_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "=", other.id]], ["id", "name"], 1
        )
        self.assertEqual({row["id"] for row in linked_rows}, set(children.ids))
        self.assertEqual(other_rows, [{"id": other.id, "name": other.name}])
    def test_mapping_accepts_new_live_readable_field_not_in_session_discovery_snapshot(self):
        thread, attachment, upload = self._office_message("Fill the workbook from the contact record")
        target = self.env["res.partner"].create(
            {
                "name": "Newly requested mapping field " + uuid4().hex,
                "email": "newly-requested@example.test",
                "company_id": self.env.company.id,
            }
        )
        from ..services.mapping_service import create_session

        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=upload.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        inspection = inspect_document(attachment.raw, attachment.name, attachment.mimetype, _resource_budget())
        manifest, visible_text = _template_context(inspection)
        set_mapping_context(
            self.env,
            created["session_id"],
            manifest,
            {"name": "string"},
            template_text=visible_text,
            document_format="xlsx",
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        retriever_result = thread.message_post(
            body="Verified target record",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "verified-target-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        result = self.env["office.mapping.tool"].with_context(message=retriever_result).office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Sheet!A1", "source_field": "email", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )

        self.assertEqual(result["status"], "success", result)
        self.assertEqual(json.loads(session.context_json)["allowed_fields"]["email"], "string")
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered.active["A1"].value, target.email)
        finally:
            rendered.close()

    def test_office_retriever_allows_acl_readable_records_before_prepare(self):
        thread, _attachment, user_message = self._office_message("Fill the workbook from this parent")
        parent = self.env["res.partner"].create(
            {"name": "Pre-session parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Pre-session child A " + uuid4().hex, "parent_id": parent.id},
            {"name": "Pre-session child B " + uuid4().hex, "parent_id": parent.id},
        ])
        unrelated = self.env["res.partner"].create(
            {"name": "Unretrieved parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        retriever = self.env["llm.tool"].with_context(message=user_message)

        rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["parent_id", "=", parent.id]], ["id", "name", "parent_id"], 10
        )
        exact_unretrieved = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "=", unrelated.id]], ["id", "name"], 1
        )
        self.assertEqual({row["id"] for row in rows}, set(children.ids))
        self.assertEqual({row["parent_id"][0] for row in rows}, {parent.id})
        self.assertEqual(exact_unretrieved, [{"id": unrelated.id, "name": unrelated.name}])
        self.assertFalse(self.env["office.mapping.session"].search([("thread_id", "=", thread.id)]))
    def test_office_retriever_uses_native_search_read_for_relation_queries(self):
        _thread, _attachment, user_message = self._office_message("Fill the workbook from this parent")
        parent = self.env["res.partner"].create(
            {"name": "Relation parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Relation child A " + uuid4().hex, "parent_id": parent.id},
            {"name": "Relation child B " + uuid4().hex, "parent_id": parent.id},
        ])
        retriever = self.env["llm.tool"].with_context(message=user_message)

        child_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "in", children.ids]], ["id", "name", "parent_id"], len(children)
        )
        parent_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "=", parent.id]], ["id", "name", "contact_address"], 1
        )

        self.assertEqual({row["id"] for row in child_rows}, set(children.ids))
        self.assertEqual({row["parent_id"][0] for row in child_rows}, {parent.id})
        self.assertEqual(parent_rows[0]["id"], parent.id)
        self.assertEqual(parent_rows[0]["contact_address"], parent.contact_address)
    def test_native_repeat_rows_tool_runs_generic_expansion_and_m1_preview(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Repeat rows native thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repeat-rows-native.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        upload = thread.message_post(
            body="请把关联明细填入重复行",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        parent = self.env["res.partner"].create(
            {
                "name": "Repeat parent value",
                "email": "repeat-parent@example.test",
                "company_id": self.env.company.id,
            }
        )
        children = self.env["res.partner"].create([
            {"name": "Repeat value C", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat value A", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat value B", "parent_id": parent.id, "company_id": self.env.company.id},
        ])
        repeat_candidates = next(
            item for item in _repeat_row_collection_candidates(self.env, parent)
            if item["collection_field"] == "child_ids"
        )
        self.assertTrue(
            {"name", "contact_address"}.issubset(repeat_candidates["allowed_fields"]),
            sorted(repeat_candidates["allowed_fields"]),
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-native-parent-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", parent.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool_model.office_prepare_context(
            "res.partner",
            parent.id,
            requested_fields_by_collection={"child_ids": ["parent_id.email"]},
        )
        self.assertIn(
            "parent_id.email",
            next(
                item["allowed_fields"]
                for item in context["repeat_row_collections"]
                if item["collection_field"] == "child_ids"
            ),
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(
            json.loads(session.context_json)["extra_authorized_collection_fields"],
            {"child_ids": ["parent_id.email"]},
        )
        result = self._save_repeat_rows_with_user_confirmation(
            tool_model, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [
                    {
                        "element_id": "xlsx:Data!B4",
                        "reason_code": "missing_source",
                        "question": "This cell is already handled by the repeat-row column mapping.",
                    },
                    {
                        "element_id": "xlsx:Data!F6",
                        "reason_code": "missing_source",
                        "question": "This blank neighbor belongs to the template's formula summary row.",
                    }
                ],
                "skipped_targets": ["xlsx:Data!B4", "xlsx:Data!B6", "xlsx:Data!C6"],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "sort_by": "name",
                    "sort_direction": "asc",
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "source_field": "parent_id.email"},
                        # Provider tool calls sometimes omit Excel's leading
                        # equals sign. The service should canonicalize the
                        # safe arithmetic before validation and rendering.
                        {"column": "D", "formula": "1*3+E{row}*0"},
                    ],
                }
            ],
        )
        refreshed_context = tool_model.office_prepare_context("res.partner", parent.id)

        self.assertEqual(result["status"], "success", result)
        saved_rules = json.loads(session.mapping_rules_json)
        self.assertNotIn("xlsx:Data!F7", [item["element_id"] for item in saved_rules["clarifications"]])
        self.assertIn("xlsx:Data!F7", saved_rules["skipped_targets"])
        self.assertEqual(session.source_message_id, upload)
        self.assertTrue(session.preview_attachment_id.name.startswith("preview_"))
        self.assertTrue(session.preview_attachment_id.name.endswith(".xlsx"))
        self.assertEqual(session.preview_attachment_id.mimetype, XLSX_MIME)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = rendered["Data"]
            self.assertEqual(sheet["B1"].value, parent.name)
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(4, 7)],
                sorted(child.name for child in children),
            )
            self.assertEqual(
                [sheet[f"C{row}"].value for row in range(4, 7)],
                [parent.email] * len(children),
            )
            self.assertEqual(
                [sheet[f"D{row}"].value for row in range(4, 7)],
                [f"=1*3+E{row}*0" for row in range(4, 7)],
            )
            self.assertEqual(sheet["E7"].value, "=SUM(E4:E6)")
        finally:
            rendered.close()

        # A later repeat-row patch that omits ordering preserves the already
        # saved sort rule; omission is not an implicit unsort operation.
        second_result = self._save_repeat_rows_with_user_confirmation(
            tool_model, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "fallback_fields": ["name", "contact_address"]},
                        {"column": "D", "formula": "1*3+E{row}*0"},
                    ],
                }
            ],
        )
        self.assertEqual(second_result["status"], "success", second_result)
        self.assertIn(second_result["operation_status"], {"preview_ready", "unchanged"})
        refreshed_context = tool_model.office_prepare_context("res.partner", parent.id)
        self.assertEqual(
            refreshed_context["current_repeat_rows"][0]["columns"],
            [
                {"column": "B", "source_field": "name"},
                {"column": "C", "fallback_fields": ["name", "contact_address"]},
                {"column": "D", "formula": "=1*3+E{row}*0"},
            ],
        )
        self.assertEqual(refreshed_context["current_repeat_rows"][0]["sort_by"], "name")
        self.assertEqual(refreshed_context["current_repeat_rows"][0]["sort_direction"], "asc")
        final_preview = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [final_preview["Data"][f"B{row}"].value for row in range(4, 7)],
                sorted(child.name for child in children),
            )
        finally:
            final_preview.close()

    def test_native_repeat_rows_preserves_zero_numeric_values(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Repeat zero numeric thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repeat-zero-numeric.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _zero_numeric_repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        thread.message_post(
            body="Map the child names and zero-valued numeric field.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        parent = self.env["res.partner"].create(
            {"name": "Zero parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Zero child A " + uuid4().hex, "parent_id": parent.id, "color": 0},
            {"name": "Zero child B " + uuid4().hex, "parent_id": parent.id, "color": 0},
        ])
        candidate = next(
            item for item in _repeat_row_collection_candidates(self.env, parent)
            if item["collection_field"] == "child_ids"
        )
        self.assertEqual(candidate["allowed_fields"].get("color"), "number")
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-zero-parent-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner", "domain": [["id", "=", parent.id]],
                    "fields": ["name"], "limit": 1,
                },
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool_model.office_prepare_context("res.partner", parent.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = self._save_repeat_rows_with_user_confirmation(
            tool_model, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "source_field": "color"},
                    ],
                }
            ],
        )

        self.assertEqual(result["status"], "success", result)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = rendered["Data"]
            self.assertEqual(sheet["B1"].value, parent.name)
            self.assertEqual(
                [sheet[f"B{row}"].value for row in (4, 5)], [child.name for child in children]
            )
            self.assertEqual([sheet[f"C{row}"].value for row in (4, 5)], [0, 0])
        finally:
            rendered.close()

    def test_repeat_context_allows_explicit_overwrite_of_existing_formula_columns(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Repeat formula guard thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repeat-formula-guard.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _formula_repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        thread.message_post(
            body="Fill the related rows",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        parent = self.env["res.partner"].create(
            {"name": "Repeat formula parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Repeat formula child A", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat formula child B", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat formula child C", "parent_id": parent.id, "company_id": self.env.company.id},
        ])
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-formula-guard-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", parent.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool_model.office_prepare_context("res.partner", parent.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = self._save_repeat_rows_with_user_confirmation(
            tool_model, thread, session,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "=B{row}*2"},
                    ],
                }
            ],
        )

        self.assertEqual(len(children), 3)
        self.assertIn(
            "xlsx:Data!C4",
            {item["element_id"] for item in context["mapping_limits"]["template_formula_cells"]},
        )
        self.assertIn("template_formula_cells", context["mapping_limits"])
        self.assertEqual(result["status"], "success", result)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [f"=B{row}*2" for row in range(4, 7)],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

        # A repeat column initially populated by formulas remains a valid
        # target for a later explicit literal-value patch. The initial
        # operation choice must not permanently narrow the cell's type.
        session.invalidate_recordset(["context_json"])
        persisted_manifest = json.loads(session.context_json)["target_manifest"]
        c4_target = next(item for item in persisted_manifest if item["element_id"] == "xlsx:Data!C4")
        self.assertIn("number", c4_target["allowed_value_types"])
        self.assertIn("formula", c4_target["allowed_value_types"])
        literal_patch = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": f"xlsx:Data!C{row}", "literal_value": value, "value_type": "number"}
                    for row, value in zip(range(4, 7), (10, 11, 12))
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(literal_patch["status"], "success", literal_patch)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [rendered["Data"][f"B{row}"].value for row in range(4, 7)],
                [child.name for child in children],
            )
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [10, 11, 12],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

        # Clears inside the expanded repeat band are already expressed in
        # post-expansion coordinates. They must remain on the data rows and
        # must not shift onto (and clear) the moved summary formula.
        clear_result = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
                "clear_targets": ["xlsx:Data!C4", "xlsx:Data!C5", "xlsx:Data!C6"],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "=B{row}*2"},
                    ],
                }
            ],
        )
        self.assertEqual(clear_result["status"], "needs_confirmation", clear_result)
        affected_scope = set(clear_result["affected_scope"])
        self.assertEqual(clear_result["risk_type"], "multiple_business_risks")
        self.assertTrue(
            {"xlsx:Data!C4", "xlsx:Data!C5", "xlsx:Data!C6"}.issubset(affected_scope),
            clear_result,
        )
        self.assertIn("xlsx:Data!B6:B6", affected_scope)
        self.assertIn("xlsx:Data!C6:C6", affected_scope)
        self.assertIn("xlsx:Data!C7", affected_scope)
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        clear_result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
                "clear_targets": ["xlsx:Data!C4", "xlsx:Data!C5", "xlsx:Data!C6"],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "=B{row}*2"},
                    ],
                }
            ],
            force_override=True,
        )
        self.assertEqual(clear_result["status"], "success", clear_result)
        cleared_preview_id = session.preview_attachment_id.id
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [None, None, None],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

        # A row-number token outside a cell reference must not silently
        # become a constant calculation or replace the valid preview.
        existing_preview_id = session.preview_attachment_id.id
        existing_revision = session.revision
        invalid_formula = tool_model.office_save_mapping_preview(
            session.id,
            existing_revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "{row}*{row}*2"},
                    ],
                }
            ],
        )
        self.assertEqual(invalid_formula["status"], "error")
        self.assertEqual(invalid_formula["operation_status"], "invalid")
        self.assertEqual(invalid_formula["error_code"], "repeat_rows_not_renderable")
        self.assertIn("Use {row} inside a cell reference", invalid_formula["message"])
        self.assertEqual(session.revision, existing_revision)
        self.assertEqual(session.preview_attachment_id.id, existing_preview_id)
        self.assertEqual(existing_preview_id, cleared_preview_id)

        # The live Provider schema exposes format_patches beside proposal.
        # They must reach the tool executor instead of being silently ignored.
        column_operations = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            format_patches=[
                {"element_id": "xlsx:Data!B4", "number_format": "0.00"}
            ],
        )
        self.assertEqual(column_operations["status"], "success", column_operations)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Data"]["B1"].value, parent.name)
            self.assertEqual(rendered["Data"]["B4"].value, children[0].name)
            self.assertEqual(rendered["Data"]["B4"].number_format, "0.00")
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [None, None, None],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

    def test_top_level_clear_column_reaches_preview_executor(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Orders"
        sheet["A3"] = "Order"
        sheet["B3"] = "Partner"
        sheet["C3"] = "Amount"
        sheet["A4"] = "SO-1"
        sheet["C4"] = 10
        sheet["A5"] = "SO-2"
        sheet["C5"] = 20
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread, _attachment, upload = self._office_message("Update the partner and clear amounts", output.getvalue())
        target = self.env["res.partner"].create(
            {"name": "Top-level operation partner " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])

        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Orders!B4", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            clear_columns=[{"sheet": "Orders", "column": "C"}],
            format_patches=[
                {"element_id": "xlsx:Orders!C4", "number_format": "0.00"}
            ],
        )
        self.assertEqual(result["status"], "needs_confirmation", result)
        self.assertEqual(result["affected_scope"], ["xlsx:Orders!C4", "xlsx:Orders!C5"])
        self.assertFalse(result["operation_executed"])
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Orders!B4", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            clear_columns=[{"sheet": "Orders", "column": "C"}],
            format_patches=[{"element_id": "xlsx:Orders!C4", "number_format": "0.00"}],
            force_override=True,
        )
        self.assertEqual(result["status"], "success", result)
        self.assertTrue(result["attachment_posted_to_thread"])
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Orders"]["A3"].value, "Order")
            self.assertEqual(rendered["Orders"]["B3"].value, "Partner")
            self.assertEqual(rendered["Orders"]["C3"].value, "Amount")
            self.assertEqual(rendered["Orders"]["A4"].value, "SO-1")
            self.assertEqual(rendered["Orders"]["B4"].value, target.name)
            self.assertIsNone(rendered["Orders"]["C4"].value)
            self.assertEqual(rendered["Orders"]["C4"].number_format, "0.00")
            self.assertIsNone(rendered["Orders"]["C5"].value)
            self.assertEqual(rendered["Orders"]["A5"].value, "SO-2")
        finally:
            rendered.close()

    def test_explicit_clear_preserves_omitted_legacy_required_target_and_formula(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["F16"] = "old order number"
        sheet.merge_cells("E17:H17")
        sheet["E17"] = "old merged placeholder"
        sheet["F18"] = "old legacy-required placeholder"
        sheet["F24"] = "=SUM(F20:F23)"
        sheet["F25"] = "=SUM(F20:F24)"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread = self.env["llm.thread"].create({
            "name": "Explicit clear test " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        attachment = self.env["ir.attachment"].create({
            "name": "clear-target-test-" + uuid4().hex + ".xlsx",
            "type": "binary",
            "mimetype": XLSX_MIME,
            "raw": output.getvalue(),
            "company_id": self.env.company.id,
        })
        upload = thread.message_post(
            body="Put the order number in F16 and clear F17.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        target = self.env["res.partner"].create({"name": "S05457", "company_id": self.env.company.id})
        tool_message = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "explicit-clear-test-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        inspection = inspect_document(
            attachment.raw, attachment.name, attachment.mimetype, _resource_budget()
        )
        manifest, visible_text = _template_context(inspection)
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=upload.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        set_mapping_context(self.env, session.id, manifest, {"name": "string"}, template_text=visible_text)
        # Simulate a persisted legacy Session whose writable F18 target was
        # marked required. The user only requested F17 be blank, so F18 must
        # remain unchanged and must not be added to the clear scope.
        context = json.loads(session.context_json)
        legacy_required = next(
            item for item in context["target_manifest"]
            if item["element_id"] == "xlsx:Data!F18"
        )
        legacy_required["required"] = True
        legacy_required["approved_to_skip"] = False
        session._set_context_from_service(json.dumps(context, ensure_ascii=False))

        tool = self.env["office.mapping.tool"].with_context(message=tool_message)
        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [{
                    "element_id": "xlsx:Data!F16",
                    "source_field": "name",
                    "value_type": "string",
                }, {
                    # The compact provider form is an explicit blank write.
                    "element_id": "xlsx:Data!F17",
                    "value": "",
                }],
                "clarifications": [],
                "skipped_targets": ["xlsx:Data!F24", "xlsx:Data!F25", "xlsx:Data!Z999"],
                "clear_targets": ["xlsx:Data!F24"],
            },
        )

        self.assertEqual(result["status"], "needs_confirmation", result)
        self.assertEqual(result["affected_scope"], ["xlsx:Data!E17", "xlsx:Data!F24"])
        self.assertFalse(result["operation_executed"])
        self.assertFalse(session.preview_attachment_id)
        confirmation = thread.message_post(
            body="确认", llm_role="user", author_id=self.env.user.partner_id.id
        )
        result = self.env["office.mapping.tool"].with_context(message=confirmation).office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [{
                    "element_id": "xlsx:Data!F16",
                    "source_field": "name",
                    "value_type": "string",
                }, {
                    "element_id": "xlsx:Data!F17",
                    "value": "",
                }],
                "clarifications": [],
                "skipped_targets": ["xlsx:Data!F24", "xlsx:Data!F25", "xlsx:Data!Z999"],
                "clear_targets": ["xlsx:Data!F24"],
            },
            force_override=True,
        )
        self.assertEqual(result["status"], "success", result)
        rules = json.loads(session.mapping_rules_json)
        self.assertEqual(rules["clear_targets"], ["xlsx:Data!E17", "xlsx:Data!F24"])
        self.assertEqual([item["element_id"] for item in rules["mappings"]], ["xlsx:Data!F16"])
        self.assertEqual(rules["skipped_targets"], [])
        self.assertNotIn("xlsx:Data!F24", rules["skipped_targets"])
        self.assertNotIn("xlsx:Data!F25", rules["skipped_targets"])
        self.assertNotIn("xlsx:Data!F18", rules["clear_targets"])
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Data"]["F16"].value, "S05457")
            self.assertIsNone(rendered["Data"]["E17"].value)
            self.assertIsNone(rendered["Data"]["F17"].value)
            self.assertEqual(rendered["Data"]["F18"].value, "old legacy-required placeholder")
            self.assertIsNone(rendered["Data"]["F24"].value)
            self.assertEqual(rendered["Data"]["F25"].value, "=SUM(F20:F24)")
        finally:
            rendered.close()

    def test_new_office_upload_is_not_blocked_by_an_older_active_session(self):
        thread, old_attachment, old_message = self._office_message("Old workbook request")
        old_target = self.env["res.partner"].create(
            {"name": "Old Office target " + uuid4().hex, "company_id": self.env.company.id}
        )
        from ..services.mapping_service import create_session

        create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=old_message.id,
            source_attachment_id=old_attachment.id,
            target_model="res.partner",
            target_record_id=old_target.id,
        )

        new_attachment = self.env["ir.attachment"].create(
            {
                "name": "new-office-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        latest_upload = thread.message_post(
            body="Fill the new workbook",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[new_attachment.id],
        )
        self.assertFalse(thread._office_active_session())

        retriever = self.env["llm.tool"].with_context(message=latest_upload)
        rows = retriever.odoo_record_retriever_execute(
            model="res.partner",
            domain=[["name", "=", old_target.name]],
            fields=["id", "name"],
            limit=1,
        )
        self.assertEqual([row["id"] for row in rows], [old_target.id])

        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "new-upload-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["name", "=", old_target.name]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": rows,
            },
        )
        context = self.env["office.mapping.tool"].with_context(
            message=retriever_result
        ).office_prepare_context("res.partner", old_target.id)
        new_session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(new_session.source_message_id, latest_upload)
        self.assertEqual(new_session.source_attachment_id, new_attachment)

    def test_office_retriever_uses_current_user_permissions_without_environment_gate(self):
        _thread, _attachment, message = self._office_message("Fill the workbook")
        retriever = self.env["llm.tool"].with_context(message=message)
        retrieval_model = "sale.order" if "sale.order" in self.env.registry.models else "res.partner"
        result = retriever.odoo_record_retriever_execute(
            retrieval_model,
            [["name", "=", "NO-SUCH-OFFICE-RECORD"]],
            ["name"],
            1,
        )
        self.assertEqual(result, [])

    def test_fileless_xlsx_request_binds_route_b_tools_for_create_and_followup_turns(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Fileless Office create thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        self.assertFalse(thread._office_is_active())

        first_request = "导出本公司的产品档案到 Excel，任意选择 5 条并生成 XLSX。"
        with patch.object(
            NativeThread, "generate", autospec=True, return_value=iter(())
        ) as native_generate:
            list(thread.generate(first_request, attachment_ids=[]))

        self.assertTrue(native_generate.called)
        self.assertEqual(
            set(thread.tool_ids.mapped("name")) & {"office", "odoo_record_retriever"},
            {"office", "odoo_record_retriever"},
        )

        # The native generate loop stores the incoming user message before it
        # builds the provider request. Reproduce that boundary and verify the
        # actual Route B schema and create guidance are now active.
        thread.message_post(
            body=first_request,
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        self.assertTrue(thread._office_is_active())
        self.assertTrue(thread._office_is_candidate_b_route())
        values = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
        self.assertEqual(
            set(values["tools"].mapped("name")),
            {"office", "odoo_record_retriever"},
        )
        route_b_prompt = next(
            message["content"]
            for message in values["prepend_messages"]
            if message.get("role") == "system"
            and "office(action='create')" in message.get("content", "")
        )
        self.assertIn("call office(action='create') once", route_b_prompt)

        # A natural-language follow-up can omit the word Excel: the unresolved
        # workbook request in this same user-owned Thread keeps the same tools
        # available without another upload or a new Office session.
        followup = "从本公司的产品档案里任意选择 5 个产品。"
        with patch.object(
            NativeThread, "generate", autospec=True, return_value=iter(())
        ) as native_generate:
            list(thread.generate(followup, attachment_ids=[]))
        self.assertTrue(native_generate.called)
        self.assertTrue(thread._office_is_active())
        values = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
        self.assertEqual(
            set(values["tools"].mapped("name")),
            {"office", "odoo_record_retriever"},
        )

    def test_office_thread_uses_native_tools_and_prepare_binds_current_upload_and_record(self):
        instruction = "用联系人记录填这个工作簿"
        thread, _attachment, user_message = self._office_message(instruction)
        # This test covers the legacy M1 mapping prompt. An explicit active
        # business-record Session keeps that compatibility route distinct from
        # a fresh Route B upload, which now uses the native file lifecycle.
        from odoo.addons.office_engine_m2.services.mapping_service import create_session

        target = self.env["res.partner"].create({
            "name": "M1 tool prompt target " + uuid4().hex,
            "company_id": False,
        })
        latest_upload, upload_attachment = thread._office_latest_upload()
        create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=latest_upload.id,
            source_attachment_id=upload_attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        tool_names = set(thread._office_bind_tools().mapped("name"))
        self.assertEqual(
            tool_names,
            {
                "office",
                "office_prepare_context",
                "office_save_mapping_preview",
                "office_restore_proposal_revision",
                "office_finalize",
                "odoo_record_retriever",
            },
        )
        schemas = {
            tool.name: tool.get_input_schema()
            for tool in thread.tool_ids.filtered(lambda item: item.name in tool_names)
        }
        self.assertEqual(schemas["office"]["required"], ["action"])
        self.assertFalse(schemas["office"]["additionalProperties"])
        self.assertEqual(
            schemas["office"]["properties"]["action"]["enum"],
            ["status", "create", "edit", "accept", "reject", "finalize"],
        )
        self.assertNotIn("expected_effect", schemas["office"]["properties"])
        self.assertNotIn("interpretation", schemas["office"]["properties"])
        self.assertNotIn("effect_digest", schemas["office"]["properties"])
        self.assertNotIn("workbook_inspection_id", schemas["office"]["properties"])
        self.assertTrue(
            thread._office_is_active(),
            "an Office upload must activate Office-specific tools and instructions",
        )
        self.assertIn("model", schemas["odoo_record_retriever"]["properties"])
        self.assertIn("model", schemas["odoo_record_retriever"]["required"])
        self.assertIn("target_model", schemas["office_prepare_context"]["properties"])
        self.assertIn("proposal", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("session_id", schemas["office_finalize"]["properties"])
        proposal_schema = schemas["office_save_mapping_preview"]["properties"]["proposal"]
        self.assertEqual(
            proposal_schema["required"],
            ["schema_version", "mappings", "clarifications", "skipped_targets"],
        )
        self.assertIn("clear_targets", proposal_schema["properties"])
        self.assertNotIn("clear_targets", proposal_schema["required"])
        mapping_schema = proposal_schema["properties"]["mappings"]["items"]
        self.assertEqual(mapping_schema["required"], ["element_id"])
        self.assertEqual(mapping_schema["properties"]["value"]["enum"], [""])
        self.assertIn("literal_value", mapping_schema["properties"])
        self.assertIn("transform", mapping_schema["properties"])
        self.assertIn("date", mapping_schema["properties"]["value_type"]["enum"])
        self.assertIn("datetime", mapping_schema["properties"]["value_type"]["enum"])
        repeat_column_schema = schemas["office_save_mapping_preview"]["properties"]["repeat_rows"]["items"]["properties"]["columns"]["items"]
        self.assertIn("transform", repeat_column_schema["properties"])
        self.assertFalse(mapping_schema["additionalProperties"])
        kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=True)
        # This method preserves the value supplied by llm_assistant; the
        # Office-specific non-streaming choice is made at the native response
        # handler boundary in LLMThread._generate_assistant_response.
        self.assertTrue(kwargs["stream"])
        self.assertEqual(set(kwargs["tools"].mapped("name")), tool_names)
        self.assertEqual(kwargs["messages"], thread.get_llm_messages())

        office_system_message = next(
            message
            for message in kwargs["prepend_messages"]
            if message.get("role") == "system"
            and "For an initial Office mapping request" in message.get("content", "")
            and "Do not issue an overwrite confirmation request from your own guess or a visual/text description"
            in message.get("content", "")
        )
        self.assertIn("that request authorizes a draft preview", office_system_message["content"])
        self.assertIn("Do not ask the user to separately approve or confirm a preview", office_system_message["content"])
        self.assertIn("Do not issue an overwrite confirmation request from your own guess or a visual/text description", office_system_message["content"])
        self.assertIn("Whenever the user explicitly asks to change or clear an existing coordinate, first call office_save_mapping_preview with the exact cell_edits", office_system_message["content"])
        self.assertIn("only a tool result with status needs_confirmation authorizes you to ask the user to confirm", office_system_message["content"])
        self.assertIn("ask one concise natural-language question in this chat", office_system_message["content"])
        self.assertIn("Never direct the user to a record-picker dialog", office_system_message["content"])
        self.assertIn("request at least two results", office_system_message["content"])
        self.assertIn("no match or multiple matches", office_system_message["content"])
        self.assertIn("fields argument accepts only direct fields", office_system_message["content"])
        self.assertIn("Odoo's current-user ACLs", office_system_message["content"])
        self.assertIn("continue that Session and its saved Proposal", office_system_message["content"])
        self.assertIn("literal_value", office_system_message["content"])
        self.assertIn("date_offset", office_system_message["content"])
        self.assertNotIn("Retriever constrains the result to the current Session", office_system_message["content"])
        self.assertIn("retain the existing `office_finalize` action and its current confirmation behavior", office_system_message["content"])
        self.assertIn("do not mix the two finalization paths", office_system_message["content"])

        target = self.env["res.partner"].create(
            {"name": "Authorized Office target", "company_id": self.env.company.id}
        )
        # This tool result stands in for the preceding Retriever tool result in
        # this isolated handler test; it is not evidence of a live LLM call.
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "test-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["name", "=", target.name]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        context = self.env["office.mapping.tool"].with_context(message=retriever_result).office_prepare_context(
            "res.partner", target.id
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.thread_id, thread)
        self.assertEqual(session.source_message_id, user_message)
        self.assertEqual(session.source_attachment_id, user_message.attachment_ids)
        self.assertEqual(session.target_record_id, target.id)
        self.assertIn("name", context["allowed_fields"])
        self.assertEqual(context["allowed_fields"]["name"]["type"], "string")
        self.assertEqual(
            context["allowed_fields"]["name"]["label"],
            self.env["res.partner"]._fields["name"].string,
        )

    def test_prepare_context_accepts_selected_record_ids_without_anchor_id(self):
        """A selected record set needs no redundant singular ID from the model."""
        thread, _attachment, user_message = self._office_message(
            "Fill the selected business records into repeated rows", raw=_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {"name": "Batch anchor %s" % uuid4().hex, "company_id": self.env.company.id},
            {"name": "Batch row %s" % uuid4().hex, "company_id": self.env.company.id},
        ])
        tool = self.env["office.mapping.tool"].with_context(message=user_message)

        context = tool.office_prepare_context(
            target_model="res.partner", target_record_ids=records.ids
        )

        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.target_record_id, records[0].id)
        self.assertEqual(
            json.loads(session.context_json)["selected_record_ids"], records.ids
        )
        prepare_tool = thread._office_bind_tools().filtered(
            lambda item: item.name == "office_prepare_context"
        )
        schema = prepare_tool.get_input_schema()
        self.assertNotIn("target_record_id", schema.get("required", []))
        self.assertIn("target_record_ids", schema["properties"])

    def test_resumed_thread_with_bound_office_tools_uses_gpt5_compatible_reasoning_effort(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Resumed Office tool thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        thread._office_bind_tools()

        # This reproduces a resumed Thread whose Office tools remain bound
        # after its Session is no longer active. Native llm_assistant still
        # passes those tools to the Provider, so GPT-5 must not inherit an
        # unsupported model-level reasoning_effort value.
        self.assertFalse(thread._office_is_active())
        with patch.object(
            type(self.model),
            "chat",
            autospec=True,
            return_value={"content": "Native Office tool continuation", "tool_calls": []},
        ) as provider_call:
            events = list(thread._generate_assistant_response())

        self.assertTrue(events)
        kwargs = provider_call.call_args.kwargs
        self.assertFalse(kwargs["stream"])
        self.assertEqual(kwargs["reasoning_effort"], "none")
        self.assertIn("odoo_record_retriever", kwargs["tools"].mapped("name"))

    def test_prepare_context_refreshes_server_field_schema_without_losing_proposal_revision(self):
        thread, attachment, upload = self._office_message("用联系人记录填这个工作簿")
        target = self.env["res.partner"].create(
            {"name": "Address context refresh " + uuid4().hex, "company_id": self.env.company.id}
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "address-context-refresh-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        first_context = tool_model.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(first_context["session_id"])
        original_revision = session.revision
        original_rules = session.mapping_rules_json
        original_state = session.state

        # A completed repeat-row setup can contain targets created by M1
        # row expansion that are absent from the original uploaded XLSX.
        # Refreshing only the field dictionary must preserve this expanded
        # manifest and its server-owned group.
        expanded_manifest = [
            *first_context["target_manifest"],
            *[
                {
                    "element_id": f"xlsx:Sheet!B{row_number}",
                    "required": True,
                    "writable": True,
                    "allowed_value_types": ["string"],
                    "approved_to_skip": False,
                }
                for row_number in (23, 24)
            ],
        ]
        repeat_group = {
            "group_id": "repeat_rows",
            "collection_field": "child_ids",
            "relation_model": "res.partner",
            "row_count": 2,
            "target_rows": [
                {
                    "row_index": index,
                    "targets": [
                        {"column_id": "B", "element_id": f"xlsx:Sheet!B{23 + index}"}
                    ],
                }
                for index in range(2)
            ],
            "allowed_fields": {"name": "string"},
        }

        # Simulate a Session created before a newly authorized field path
        # (such as contact_address) was added to server discovery.
        set_mapping_context(
            self.env,
            session.id,
            expanded_manifest,
            {"name": "string"},
            mapping_groups=[repeat_group],
            template_text=first_context["template_text"],
        )
        refreshed = tool_model.office_prepare_context("res.partner", target.id)

        self.assertEqual(session.source_message_id, upload)
        self.assertEqual(session.source_attachment_id, attachment)
        self.assertIn("contact_address", refreshed["allowed_fields"])
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.mapping_rules_json, original_rules)
        self.assertEqual(session.state, original_state)
        self.assertTrue(
            {"xlsx:Sheet!B23", "xlsx:Sheet!B24"}.issubset(
                {item["element_id"] for item in refreshed["target_manifest"]}
            )
        )
        refreshed_context = json.loads(session.context_json)
        self.assertEqual(refreshed_context["mapping_groups"][0]["collection_field"], "child_ids")
        self.assertEqual(refreshed_context["mapping_groups"][0]["row_count"], 2)

    def test_office_tool_provider_schemas_include_required_arguments(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Native Office schema thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        tools = thread._office_bind_tools()
        schemas = {tool.name: tool.get_input_schema() for tool in tools}
        self.assertIn("finalize", schemas["office"]["properties"]["action"]["enum"])
        self.assertIn("model", schemas["odoo_record_retriever"]["properties"])
        self.assertIn("model", schemas["odoo_record_retriever"]["required"])
        for argument in ("offset", "order", "include_pagination"):
            self.assertIn(argument, schemas["odoo_record_retriever"]["properties"])
        self.assertIn("target_model", schemas["office_prepare_context"]["properties"])
        self.assertNotIn("target_record_id", schemas["office_prepare_context"].get("required", []))
        self.assertIn("target_record_ids", schemas["office_prepare_context"]["properties"])
        self.assertIn("requested_fields", schemas["office_prepare_context"]["properties"])
        self.assertIn("requested_fields_by_collection", schemas["office_prepare_context"]["properties"])
        self.assertIn("proposal", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("repeat_rows", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("clear_columns", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("format_patches", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("cell_edits", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("force_override", schemas["office_save_mapping_preview"]["properties"])
        self.assertNotIn("force_override", schemas["office_save_mapping_preview"].get("required", []))
        self.assertNotIn("header_edits", schemas["office_save_mapping_preview"]["properties"])
        self.assertNotIn(
            "cell_edits",
            schemas["office_save_mapping_preview"]["properties"]["proposal"]["properties"],
        )
        repeat_schema = schemas["office_save_mapping_preview"]["properties"]["repeat_rows"]
        self.assertEqual(repeat_schema["type"], "array")
        self.assertEqual(repeat_schema["maxItems"], 1)
        self.assertIn("collection_field", repeat_schema["items"]["properties"])
        self.assertIn("fallback_fields", repeat_schema["items"]["properties"]["columns"]["items"]["properties"])
        self.assertIn("concat_fields", repeat_schema["items"]["properties"]["columns"]["items"]["properties"])
        self.assertIn("separator", repeat_schema["items"]["properties"]["columns"]["items"]["properties"])
        self.assertIn("formula", repeat_schema["items"]["properties"]["columns"]["items"]["properties"])
        self.assertIn("source_fields", schemas["office_save_mapping_preview"]["properties"]["proposal"]["properties"]["mappings"]["items"]["properties"])
        self.assertIn("session_id", schemas["office_finalize"]["properties"])
