from __future__ import annotations

import ast
import hashlib
import copy
import multiprocessing
import sys
import struct
import warnings
import zipfile
import zlib
from datetime import date, datetime
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from docx import Document
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Border, PatternFill, Side
from lxml import etree

from office_core import OfficeCoreError, ResourceBudget, inspect_document, render_candidate
from office_core.engine import _parser_warning_gate
from office_verify import VerificationBudget, VerificationPolicy, verify_output


ROOT = Path(__file__).resolve().parents[3]


def budget(**overrides):
    values = {
        "max_file_size": 2_000_000,
        "max_expanded_size": 8_000_000,
        "max_zip_entries": 128,
        "max_entry_size": 2_000_000,
        "max_xml_elements": 100_000,
        "max_cells": 100_000,
        "max_paragraphs": 10_000,
        # macOS Python maps a very large shared address-space region; this is a
        # local structural-test limit only, not a production memory budget.
        "max_memory_bytes": 2_000_000_000_000,
        "timeout_seconds": 15,
    }
    values.update(overrides)
    return ResourceBudget(**values)


def make_xlsx(*, formula=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "old"
    if formula:
        sheet["B1"] = "=1+1"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def make_xlsx_with_header_table():
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


def sanitize_docx(content):
    source = ZipFile(BytesIO(content), "r")
    clean = BytesIO()
    type_ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
    with zipfile.ZipFile(clean, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in source.infolist():
            name = item.filename
            if name.startswith("customXml/") or name in {"word/stylesWithEffects.xml", "docProps/thumbnail.jpeg"}:
                continue
            raw = source.read(name)
            if name == "word/_rels/document.xml.rels":
                root = etree.fromstring(raw)
                for rel in list(root):
                    if rel.get("Type", "").endswith("/customXml") or rel.get("Type", "").endswith("/stylesWithEffects"):
                        root.remove(rel)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif name == "_rels/.rels":
                root = etree.fromstring(raw)
                for rel in list(root):
                    if rel.get("Type", "").endswith("/thumbnail"):
                        root.remove(rel)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif name == "[Content_Types].xml":
                root = etree.fromstring(raw)
                for item_node in list(root):
                    part_name = item_node.get("PartName", "")
                    if part_name in {"/customXml/itemProps1.xml", "/word/stylesWithEffects.xml"}:
                        root.remove(item_node)
                    elif item_node.tag == type_ns + "Default" and item_node.get("Extension") == "jpeg":
                        root.remove(item_node)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            dst.writestr(name, raw)
    return clean.getvalue()


def make_docx():
    document = Document()
    document.add_paragraph("Existing title")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Existing cell"
    output = BytesIO()
    document.save(output)
    return sanitize_docx(output.getvalue())


def make_docx_with_standard_parts():
    def png_chunk(kind, value):
        return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff"))
        + png_chunk(b"IEND", b"")
    )
    document = Document()
    paragraph = document.add_paragraph("Word with standard parts")
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    bookmark_start = OxmlElement("w:bookmarkStart")
    bookmark_start.set(qn("w:id"), "1")
    bookmark_start.set(qn("w:name"), "Contents")
    paragraph._p.insert(0, bookmark_start)
    field_run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    field_run._r.append(begin)
    instruction_run = paragraph.add_run()
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    instruction_run._r.append(instruction)
    separate_run = paragraph.add_run()
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separate_run._r.append(separate)
    result_run = paragraph.add_run("1")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    result_run._r.append(end)
    paragraph.add_run().add_picture(BytesIO(png))
    bookmark_end = OxmlElement("w:bookmarkEnd")
    bookmark_end.set(qn("w:id"), "1")
    paragraph._p.append(bookmark_end)
    section = document.sections[0]
    section.header.paragraphs[0].text = "Document header"
    section.footer.paragraphs[0].text = "Document footer"
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Editable table value"
    output = BytesIO()
    document.save(output)
    return sanitize_docx(output.getvalue())


def mapping_for(inspection, element_id, value):
    return {
        "schema_version": "1",
        "template_sha256": inspection.template_sha256,
        "writes": [{"element_id": element_id, "operation": "set_value", "value": value}],
    }


def with_extra_part(content: bytes, name: str, payload: bytes) -> bytes:
    src = zipfile.ZipFile(BytesIO(content), "r")
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            dst.writestr(item, src.read(item.filename))
        dst.writestr(name, payload)
    return output.getvalue()


def with_xml_child(content: bytes, member_name: str, child_xml: bytes) -> bytes:
    source = zipfile.ZipFile(BytesIO(content), "r")
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in source.infolist():
            raw = source.read(item.filename)
            if item.filename == member_name:
                root = etree.fromstring(raw)
                root.append(etree.fromstring(child_xml))
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            dst.writestr(item, raw)
    return output.getvalue()


def corrupt_zip_member(content: bytes, member_name: str) -> bytes:
    archive = ZipFile(BytesIO(content), "r")
    info = archive.getinfo(member_name)
    data = bytearray(content)
    name_len, extra_len = struct.unpack_from("<HH", data, info.header_offset + 26)
    payload_offset = info.header_offset + 30 + name_len + extra_len
    data[payload_offset] ^= 0xFF
    return bytes(data)


class OfficeCoreTests(unittest.TestCase):
    def test_explicit_header_text_operation_uses_canonical_value_write_and_preserves_other_cells(self):
        source = make_xlsx_with_header_table()
        inspection = inspect_document(source, "table.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget())
        header = next(item for item in inspection.elements if item.element_id == "xlsx:Orders!F1")
        self.assertEqual(header.table_role, "table_header")
        self.assertFalse(header.writable)
        plan = {"schema_version": "1", "template_sha256": inspection.template_sha256, "writes": []}

        with self.assertRaises(OfficeCoreError):
            render_candidate(
                source,
                "table.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                mapping_for(inspection, "xlsx:Orders!F1", {"type": "string", "data": "Supplier Description"}),
                budget(),
            )

        candidate = render_candidate(
            source,
            "table.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            plan,
            budget(),
            explicit_header_edits=[{"element_id": "xlsx:Orders!F1", "value": "Supplier Description"}],
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(rendered["Orders"]["F1"].value, "Supplier Description")
            self.assertEqual(rendered["Orders"]["F2"].value, "old value")
            self.assertEqual(rendered["Orders"]["E1"].value, "Description")
            self.assertEqual(rendered["Orders"]["E2"].value, "Keep this label")
        finally:
            rendered.close()

    def test_legacy_header_edit_alias_uses_generic_cell_write_for_existing_data(self):
        source = make_xlsx_with_header_table()
        inspection = inspect_document(source, "table.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget())
        plan = {"schema_version": "1", "template_sha256": inspection.template_sha256, "writes": []}
        candidate = render_candidate(
            source,
            "table.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            plan,
            budget(),
            explicit_header_edits=[{"element_id": "xlsx:Orders!F2", "value": "Not a header"}],
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(rendered["Orders"]["F2"].value, "Not a header")
        finally:
            rendered.close()

    def test_explicit_cell_edits_overwrite_authorized_existing_header_and_data_cells(self):
        source = make_xlsx_with_header_table()
        workbook = load_workbook(BytesIO(source), data_only=False)
        workbook["Orders"]["F1"].number_format = "@"
        workbook["Orders"]["F2"].number_format = "0.00"
        source_with_styles = BytesIO()
        workbook.save(source_with_styles)
        workbook.close()
        source = source_with_styles.getvalue()
        inspection = inspect_document(source, "table.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget())
        plan = {"schema_version": "1", "template_sha256": inspection.template_sha256, "writes": []}

        candidate = render_candidate(
            source,
            "table.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            plan,
            budget(),
            explicit_cell_edits=[
                {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"},
                {"element_id": "xlsx:Orders!F2", "value": "new value", "value_type": "string"},
            ],
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(rendered["Orders"]["F1"].value, "供应商商品描述")
            self.assertEqual(rendered["Orders"]["F2"].value, "new value")
            self.assertEqual(rendered["Orders"]["F1"].number_format, "@")
            self.assertEqual(rendered["Orders"]["F2"].number_format, "0.00")
            self.assertEqual(rendered["Orders"]["E1"].value, "Description")
            self.assertEqual(rendered["Orders"]["E2"].value, "Keep this label")
        finally:
            rendered.close()

    def test_explicit_cell_edit_is_ordered_after_mapping_write_but_duplicate_mappings_still_conflict(self):
        source = make_xlsx()
        inspection = inspect_document(
            source,
            "ordered-edit.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        mapping = {
            "schema_version": "1",
            "template_sha256": inspection.template_sha256,
            "writes": [
                {
                    "element_id": "xlsx:Sheet1!A1",
                    "operation": "set_value",
                    "value": {"type": "string", "data": "mapped value"},
                }
            ],
        }
        candidate = render_candidate(
            source,
            "ordered-edit.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            mapping,
            budget(),
            explicit_cell_edits=[
                {"element_id": "xlsx:Sheet1!A1", "value": "user edit", "value_type": "string"}
            ],
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(rendered["Sheet1"]["A1"].value, "user edit")
        finally:
            rendered.close()

        duplicate_mapping = {
            **mapping,
            "writes": [mapping["writes"][0], mapping["writes"][0]],
        }
        with self.assertRaises(OfficeCoreError):
            render_candidate(
                source,
                "ordered-edit.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                duplicate_mapping,
                budget(),
            )

    def test_explicit_clear_is_final_after_numeric_mapping_to_same_cell(self):
        source = make_xlsx()
        inspection = inspect_document(
            source,
            "ordered-clear.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        mapping = {
            "schema_version": "1",
            "template_sha256": inspection.template_sha256,
            "writes": [{
                "element_id": "xlsx:Sheet1!A1",
                "operation": "set_value",
                "value": {"type": "number", "data": 0},
            }],
        }
        candidate = render_candidate(
            source,
            "ordered-clear.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            mapping,
            budget(),
            explicit_cell_edits=[
                {"element_id": "xlsx:Sheet1!A1", "value": "", "value_type": "string"}
            ],
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertIn(rendered["Sheet1"]["A1"].value, (None, ""))
        finally:
            rendered.close()

    def test_explicit_cell_edit_rejects_target_outside_inspected_document(self):
        source = make_xlsx_with_header_table()
        inspection = inspect_document(source, "table.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget())
        plan = {"schema_version": "1", "template_sha256": inspection.template_sha256, "writes": []}
        with self.assertRaises(OfficeCoreError):
            render_candidate(
                source,
                "table.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                plan,
                budget(),
                explicit_cell_edits=[
                    {"element_id": "xlsx:Orders!Z999", "value": "outside", "value_type": "string"}
                ],
            )

    def test_explicit_cell_edit_replaces_formula_at_the_named_target(self):
        source = make_xlsx(formula=True)
        inspection = inspect_document(
            source,
            "formula.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        plan = {"schema_version": "1", "template_sha256": inspection.template_sha256, "writes": []}
        candidate = render_candidate(
            source,
            "formula.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            plan,
            budget(),
            explicit_cell_edits=[
                {"element_id": "xlsx:Sheet1!B1", "value": 9.5, "value_type": "number"}
            ],
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(rendered["Sheet1"]["B1"].value, 9.5)
            self.assertEqual(rendered["Sheet1"]["A1"].value, "old")
        finally:
            rendered.close()

    def test_xlsx_inspection_identifies_formula_cells_as_explicit_write_targets(self):
        result = inspect_document(
            make_xlsx(formula=True), "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        items = {item.element_id: item for item in result.elements}
        self.assertIn("xlsx:Sheet1!A1", items)
        self.assertEqual(items["xlsx:Sheet1!A1"].value, "old")
        self.assertTrue(items["xlsx:Sheet1!B1"].writable)
        self.assertEqual(items["xlsx:Sheet1!B1"].kind, "formula")

    def test_xlsx_inspection_exposes_merged_anchor_and_physical_range(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet["F16"] = "Order number"
        sheet.merge_cells("E17:H17")
        sheet["E17"] = "existing placeholder"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        inspected = inspect_document(
            output.getvalue(),
            "merged-target.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        target = next(item for item in inspected.elements if item.element_id == "xlsx:Sheet1!E17")
        self.assertEqual(target.merged_range, "E17:H17")
        self.assertTrue(target.writable)
        self.assertFalse(any(item.element_id == "xlsx:Sheet1!F17" for item in inspected.elements))

    def test_xlsx_blank_cells_between_used_cells_are_writable_mapping_targets(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet["A1"] = "客户名称"
        sheet["C1"] = "=B2*1.13"
        sheet["A2"] = "金额"
        sheet["C2"] = "=SUM(B2:B5)"
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "blank-targets.xlsx", mime, budget())
        elements = {item.element_id: item for item in inspected.elements}
        self.assertIn("xlsx:Sheet1!B1", elements)
        self.assertIn("xlsx:Sheet1!B2", elements)
        self.assertIsNone(elements["xlsx:Sheet1!B1"].value)
        self.assertTrue(elements["xlsx:Sheet1!B1"].writable)
        self.assertTrue(elements["xlsx:Sheet1!B2"].writable)
        self.assertTrue(elements["xlsx:Sheet1!C1"].writable)
        plan = {
            "schema_version": "1",
            "template_sha256": inspected.template_sha256,
            "writes": [
                {"element_id": "xlsx:Sheet1!B1", "operation": "set_value", "value": {"type": "string", "data": "Acme Corporation"}},
                {"element_id": "xlsx:Sheet1!B2", "operation": "set_value", "value": {"type": "number", "data": 2000}},
            ],
        }
        candidate = render_candidate(source, "blank-targets.xlsx", mime, plan, budget())
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertEqual(rendered["Sheet1"]["B1"].value, "Acme Corporation")
        self.assertEqual(rendered["Sheet1"]["B2"].value, 2000)
        self.assertEqual(rendered["Sheet1"]["C1"].value, "=B2*1.13")
        self.assertEqual(rendered["Sheet1"]["C2"].value, "=SUM(B2:B5)")
        rendered.close()

    def test_xlsx_table_header_and_blank_first_data_row_are_distinguished(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Orders"
        sheet["A1"] = "Order"
        sheet["B1"] = "Customer"
        sheet["C1"] = "Amount"
        # Real-world templates often style only some of the blank data row.
        sheet["B2"].number_format = "0.00"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        inspected = inspect_document(
            output.getvalue(),
            "table.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        elements = {item.element_id: item for item in inspected.elements}
        self.assertEqual(elements["xlsx:Orders!A1"].table_role, "table_header")
        self.assertFalse(elements["xlsx:Orders!A1"].writable)
        for coordinate in ("A2", "B2", "C2"):
            item = elements[f"xlsx:Orders!{coordinate}"]
            self.assertEqual(item.table_role, "table_data")
            self.assertTrue(item.writable)

    def test_xlsx_row_formulas_do_not_hide_unstyled_blank_table_columns(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Inventory"
        headings = [
            "Code", "Product", "Warehouse", "Location", "Lot", "UoM",
            "On hand", "Reserved", "Native available", "Calculated available", "Delta",
        ]
        for column, heading in enumerate(headings, start=1):
            sheet.cell(1, column, heading)
        # A:I are intentionally blank and unstyled, as in a structure-only
        # template. J:K contain per-row formulas, while row 4 is the aggregate.
        for row in (2, 3):
            sheet[f"J{row}"] = f"=G{row}-H{row}"
            sheet[f"K{row}"] = f"=J{row}-I{row}"
        sheet["A4"] = "Total"
        for column in "GHIJK":
            sheet[f"{column}4"] = f"=SUM({column}2:{column}3)"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        inspected = inspect_document(
            output.getvalue(),
            "inventory.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        elements = {item.element_id: item for item in inspected.elements}
        for row in (2, 3):
            for column in "ABCDEFGHI":
                item = elements[f"xlsx:Inventory!{column}{row}"]
                self.assertEqual(item.table_role, "table_data")
                self.assertTrue(item.writable)
            self.assertEqual(elements[f"xlsx:Inventory!J{row}"].table_role, "table_data")
            self.assertEqual(elements[f"xlsx:Inventory!K{row}"].table_role, "table_data")
        self.assertEqual(elements["xlsx:Inventory!G4"].kind, "formula")
        self.assertIsNone(elements["xlsx:Inventory!G4"].table_role)

    def test_xlsx_number_format_patch_changes_display_format_without_changing_value(self):
        workbook = Workbook()
        workbook.active.title = "Orders"
        workbook.active["C2"] = 4332
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "format.xlsx", mime, budget())
        plan = {
            "schema_version": "1",
            "template_sha256": inspected.template_sha256,
            "writes": [{
                "element_id": "xlsx:Orders!C2",
                "operation": "set_number_format",
                "value": {"type": "number_format", "data": "0.0"},
            }],
        }
        candidate = render_candidate(source, "format.xlsx", mime, plan, budget())
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertEqual(rendered["Orders"]["C2"].value, 4332)
        self.assertEqual(rendered["Orders"]["C2"].number_format, "0.0")
        rendered.close()
        report = verify_output(
            source,
            candidate.content,
            "format.xlsx",
            mime,
            plan,
            VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
            VerificationBudget(
                max_file_size=2_000_000,
                max_expanded_size=8_000_000,
                max_zip_entries=128,
                max_entry_size=2_000_000,
                max_xml_elements=100_000,
                max_cells=100_000,
                max_paragraphs=10_000,
                max_mapping_bytes=64_000,
                max_memory_bytes=2_000_000_000_000,
                timeout_seconds=15,
            ),
        )
        self.assertEqual(report.status, "PASS")

    def test_xlsx_value_and_number_format_patches_can_target_same_cell(self):
        workbook = Workbook()
        workbook.active.title = "Orders"
        workbook.active["C2"] = 1
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "format-and-value.xlsx", mime, budget())
        plan = {
            "schema_version": "1",
            "template_sha256": inspected.template_sha256,
            "writes": [
                {
                    "element_id": "xlsx:Orders!C2",
                    "operation": "set_value",
                    "value": {"type": "number", "data": 4332},
                },
                {
                    "element_id": "xlsx:Orders!C2",
                    "operation": "set_number_format",
                    "value": {"type": "number_format", "data": "0.0"},
                },
            ],
        }
        candidate = render_candidate(source, "format-and-value.xlsx", mime, plan, budget())
        result = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertEqual(result["Orders"]["C2"].value, 4332)
        self.assertEqual(result["Orders"]["C2"].number_format, "0.0")
        result.close()
        report = verify_output(
            source,
            candidate.content,
            "format-and-value.xlsx",
            mime,
            plan,
            VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
            VerificationBudget(
                max_file_size=2_000_000,
                max_expanded_size=8_000_000,
                max_zip_entries=128,
                max_entry_size=2_000_000,
                max_xml_elements=100_000,
                max_cells=100_000,
                max_paragraphs=10_000,
                max_mapping_bytes=64_000,
                max_memory_bytes=2_000_000_000_000,
                timeout_seconds=15,
            ),
        )
        self.assertEqual(report.status, "PASS")

    def test_xlsx_can_write_restricted_arithmetic_formula_to_non_formula_cell(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet["D23"] = 2
        sheet["E23"] = 1.5
        sheet["G23"] = "总毛重*3"
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "formula-target.xlsx", mime, budget())
        target = next(item for item in inspected.elements if item.element_id == "xlsx:Sheet1!G23")
        self.assertTrue(target.writable)
        plan = {
            "schema_version": "1",
            "template_sha256": inspected.template_sha256,
            "writes": [
                {
                    "element_id": "xlsx:Sheet1!G23",
                    "operation": "set_formula",
                    "value": {"type": "formula", "data": "=D23*E23*3"},
                }
            ],
        }
        candidate = render_candidate(source, "formula-target.xlsx", mime, plan, budget())
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertEqual(rendered["Sheet1"]["G23"].value, "=D23*E23*3")
        rendered.close()
        report = verify_output(
            source,
            candidate.content,
            "formula-target.xlsx",
            mime,
            plan,
            VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
            VerificationBudget(
                max_file_size=2_000_000,
                max_expanded_size=8_000_000,
                max_zip_entries=128,
                max_entry_size=2_000_000,
                max_xml_elements=100_000,
                max_cells=100_000,
                max_paragraphs=10_000,
                max_mapping_bytes=64_000,
                max_memory_bytes=2_000_000_000_000,
                timeout_seconds=15,
            ),
        )
        self.assertEqual(report.status, "PASS")

    def test_xlsx_string_null_clears_a_prepopulated_target(self):
        source = make_xlsx()
        inspected = inspect_document(
            source,
            "clear.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            budget(),
        )
        plan = {
            "schema_version": "1",
            "template_sha256": inspected.template_sha256,
            "writes": [
                {
                    "element_id": "xlsx:Sheet1!A1",
                    "operation": "set_value",
                    "value": {"type": "string", "data": None},
                }
            ],
        }
        candidate = render_candidate(
            source,
            "clear.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            plan,
            budget(),
        )
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertIsNone(rendered.active["A1"].value)
        rendered.close()

    def test_xlsx_render_preserves_style_catalog_and_blank_styled_cells(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet["A1"] = "Customer"
        sheet["C1"] = "=1+1"
        sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFF0000")
        sheet["B1"].border = Border(bottom=Side(style="thin", color="FF000000"))
        sheet["B2"].fill = PatternFill(fill_type="solid", fgColor="FF00FF00")
        sheet.merge_cells("D1:E1")
        sheet["D1"].font = copy.copy(sheet["A1"].font)
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "styled-blanks.xlsx", mime, budget())
        plan = mapping_for(inspected, "xlsx:Sheet1!A1", {"type": "string", "data": "Acme"})
        candidate = render_candidate(source, "styled-blanks.xlsx", mime, plan, budget())

        with ZipFile(BytesIO(source)) as original, ZipFile(BytesIO(candidate.content)) as rendered:
            self.assertEqual(original.read("xl/styles.xml"), rendered.read("xl/styles.xml"))
            source_root = etree.fromstring(original.read("xl/worksheets/sheet1.xml"))
            output_root = etree.fromstring(rendered.read("xl/worksheets/sheet1.xml"))
            ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            source_cells = {
                cell.get("r"): cell
                for cell in source_root.xpath(".//x:sheetData/x:row/x:c", namespaces=ns)
            }
            output_cells = {
                cell.get("r"): cell
                for cell in output_root.xpath(".//x:sheetData/x:row/x:c", namespaces=ns)
            }
            self.assertEqual(source_cells["B1"].get("s"), output_cells["B1"].get("s"))
            self.assertEqual(source_cells["B2"].get("s"), output_cells["B2"].get("s"))
            self.assertIn("B2", output_cells)

        report = verify_output(
            source,
            candidate.content,
            "styled-blanks.xlsx",
            mime,
            plan,
            VerificationPolicy(enabled_formats=("xlsx", "docx"), require_styles=True),
            VerificationBudget(),
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.checked_targets, 1)
        rendered = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertEqual(rendered["Sheet1"]["A1"].value, "Acme")
        self.assertEqual(rendered["Sheet1"]["C1"].value, "=1+1")
        self.assertIn("D1:E1", {str(item) for item in rendered["Sheet1"].merged_cells.ranges})
        rendered.close()

    def test_xlsx_float_write_uses_canonical_decimal_for_readback(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet["A1"] = "Weight"
        sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFFFF")
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "float.xlsx", mime, budget())
        plan = mapping_for(inspected, "xlsx:Sheet1!B1", {"type": "number", "data": 8.3})
        candidate = render_candidate(source, "float.xlsx", mime, plan, budget())
        report = verify_output(
            source,
            candidate.content,
            "float.xlsx",
            mime,
            plan,
            VerificationPolicy(enabled_formats=("xlsx", "docx"), require_styles=True),
            VerificationBudget(),
        )
        self.assertEqual(report.status, "PASS")
        with ZipFile(BytesIO(candidate.content)) as archive:
            root = etree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            value = root.xpath(
                ".//x:sheetData/x:row/x:c[@r='B1']/x:v/text()",
                namespaces={"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"},
            )
        self.assertEqual(value, ["8.3"])

    def test_xlsx_mapping_writes_typed_date_and_datetime_values(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet["A1"] = "Date"
        sheet["B1"].number_format = "yyyy-mm-dd"
        sheet["A2"] = "Datetime"
        sheet["B2"].number_format = "yyyy-mm-dd hh:mm"
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        source = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        inspected = inspect_document(source, "typed-dates.xlsx", mime, budget())

        date_candidate = render_candidate(
            source,
            "typed-dates.xlsx",
            mime,
            mapping_for(inspected, "xlsx:Sheet1!B1", {"type": "date", "data": "2026-11-10"}),
            budget(),
        )
        datetime_candidate = render_candidate(
            source,
            "typed-dates.xlsx",
            mime,
            mapping_for(
                inspected,
                "xlsx:Sheet1!B2",
                {"type": "datetime", "data": "2026-11-10T09:00:00"},
            ),
            budget(),
        )
        date_book = load_workbook(BytesIO(date_candidate.content), data_only=False)
        datetime_book = load_workbook(BytesIO(datetime_candidate.content), data_only=False)
        try:
            actual_date = date_book["Sheet1"]["B1"].value
            self.assertEqual(actual_date.date(), date(2026, 11, 10))
            self.assertEqual(actual_date.time(), datetime.min.time())
            self.assertEqual(date_book["Sheet1"]["B1"].number_format, "yyyy-mm-dd")
            self.assertEqual(datetime_book["Sheet1"]["B2"].value, datetime(2026, 11, 10, 9, 0))
            self.assertEqual(datetime_book["Sheet1"]["B2"].number_format, "yyyy-mm-dd hh:mm")
        finally:
            date_book.close()
            datetime_book.close()

    def test_docx_inspection_and_candidate_render_for_plain_paragraph_and_table(self):
        source = make_docx()
        source_hash = hashlib.sha256(source).hexdigest()
        inspected = inspect_document(
            source, "source.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", budget(),
        )
        ids = [item.element_id for item in inspected.elements]
        self.assertEqual(ids, ["docx:p:1", "docx:table:1:row:1:cell:1:p:1"])
        plan = mapping_for(inspected, ids[0], {"type": "string", "data": "Changed"})
        candidate = render_candidate(
            source, "source.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", plan, budget(),
        )
        self.assertEqual(candidate.content[:2], b"PK")
        self.assertEqual(candidate.delivery_status, "candidate_not_delivered")
        self.assertEqual(candidate.verification["status"], "PASS")
        self.assertEqual(candidate.verification["office_verify"]["format"], "docx")
        self.assertEqual(candidate.verification["output_sha256"], candidate.candidate_sha256)
        reopened = Document(BytesIO(candidate.content))
        self.assertEqual(reopened.paragraphs[0].text, "Changed")
        self.assertEqual(hashlib.sha256(source).hexdigest(), source_hash)

    def test_docx_standard_images_headers_footers_and_safe_fields_roundtrip(self):
        source = make_docx_with_standard_parts()
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        inspected = inspect_document(source, "standard-parts.docx", mime, budget())
        writable = next(element for element in inspected.elements if element.writable)
        plan = mapping_for(inspected, writable.element_id, {"type": "string", "data": "Updated table value"})
        candidate = render_candidate(source, "standard-parts.docx", mime, plan, budget())
        report = verify_output(
            source,
            candidate.content,
            "standard-parts.docx",
            mime,
            plan,
            VerificationPolicy(enabled_formats=("xlsx", "docx")),
            VerificationBudget(),
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.checked_targets, 1)
        with ZipFile(BytesIO(source)) as original, ZipFile(BytesIO(candidate.content)) as rendered:
            self.assertIn("word/header1.xml", original.namelist())
            self.assertIn("word/footer1.xml", original.namelist())
            image_parts = [name for name in original.namelist() if name.startswith("word/media/")]
            self.assertTrue(image_parts)
            for name in image_parts + ["word/header1.xml", "word/footer1.xml"]:
                self.assertEqual(original.read(name), rendered.read(name))

    def test_xlsx_candidate_render_preserves_source_and_uses_new_bytes(self):
        source = make_xlsx()
        inspected = inspect_document(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        plan = mapping_for(inspected, "xlsx:Sheet1!A1", {"type": "string", "data": "changed"})
        candidate = render_candidate(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", plan, budget(),
        )
        self.assertEqual(load_cell(candidate.content), "changed")
        self.assertEqual(load_cell(source), "old")
        self.assertEqual(candidate.applied_writes, 1)

    def test_formula_workbook_can_render_non_formula_cells_and_preserves_formula_text(self):
        source = make_xlsx(formula=True)
        inspected = inspect_document(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        plan = mapping_for(inspected, "xlsx:Sheet1!A1", {"type": "string", "data": "changed"})
        candidate = render_candidate(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", plan, budget(),
        )
        workbook = load_workbook(BytesIO(candidate.content), data_only=False)
        self.assertEqual(workbook["Sheet1"]["A1"].value, "changed")
        self.assertEqual(workbook["Sheet1"]["B1"].value, "=1+1")
        workbook.close()

    def test_explicit_mapping_can_clear_a_formula_cell(self):
        source = make_xlsx(formula=True)
        inspected = inspect_document(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        candidate = render_candidate(
            source,
            "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            mapping_for(inspected, "xlsx:Sheet1!B1", {"type": "string", "data": ""}),
            budget(),
        )
        workbook = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertIsNone(workbook["Sheet1"]["B1"].value)
        finally:
            workbook.close()

    def test_explicit_mapping_can_replace_a_formula_cell_value(self):
        source = make_xlsx(formula=True)
        inspected = inspect_document(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        candidate = render_candidate(
            source,
            "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            mapping_for(inspected, "xlsx:Sheet1!B1", {"type": "string", "data": "user value"}),
            budget(),
        )
        workbook = load_workbook(BytesIO(candidate.content), data_only=False)
        try:
            self.assertEqual(workbook["Sheet1"]["B1"].value, "user value")
        finally:
            workbook.close()

    def test_mapping_rejects_unknown_missing_duplicate_and_bad_values(self):
        source = make_xlsx(formula=True)
        inspected = inspect_document(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        cases = [
            {"schema_version": "1", "template_sha256": inspected.template_sha256, "writes": [], "extra": True},
            {"schema_version": "1", "template_sha256": inspected.template_sha256, "writes": [{"element_id": "missing", "operation": "set_value", "value": {"type": "string", "data": "x"}}]},
            {"schema_version": "1", "template_sha256": inspected.template_sha256, "writes": [
                {"element_id": "xlsx:Sheet1!A1", "operation": "set_value", "value": {"type": "string", "data": "x"}},
                {"element_id": "xlsx:Sheet1!A1", "operation": "set_value", "value": {"type": "string", "data": "y"}},
            ]},
            mapping_for(inspected, "xlsx:Sheet1!A1", {"type": "number", "data": True}),
            {"schema_version": "2", "template_sha256": inspected.template_sha256, "writes": []},
            {"schema_version": "1", "template_sha256": "0" * 64, "writes": []},
            mapping_for(inspected, "xlsx:Sheet1!A1", {"type": "string", "data": "x", "extra": 1}),
            {"schema_version": "1", "template_sha256": inspected.template_sha256, "writes": [
                {"element_id": "xlsx:Sheet1!A1", "operation": "delete", "value": {"type": "string", "data": "x"}},
            ]},
        ]
        for plan in cases:
            with self.subTest(plan=plan), self.assertRaises(OfficeCoreError) as caught:
                render_candidate(
                    source, "source.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", plan, budget(),
                )
            self.assertEqual(caught.exception.code, "OFFICE_MAPPING_INVALID")

    def test_mapping_distinguishes_empty_string_zero_and_invalid_null(self):
        source = make_xlsx()
        inspected = inspect_document(
            source, "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
        )
        for value, expected in (({"type": "string", "data": ""}, ""), ({"type": "number", "data": 0}, 0)):
            plan = mapping_for(inspected, "xlsx:Sheet1!A1", value)
            result = render_candidate(
                source, "source.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", plan, budget(),
            )
            self.assertEqual(load_cell(result.content), expected)

    def test_container_rejects_empty_mismatch_truncated_and_unknown_parts(self):
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        invalid = [(b"", "empty.xlsx", mime), (b"not a workbook", "fake.xlsx", mime), (make_xlsx(), "fake.docx", mime)]
        for content, filename, declared in invalid:
            with self.subTest(filename=filename), self.assertRaises(OfficeCoreError) as caught:
                inspect_document(content, filename, declared, budget())
            self.assertEqual(caught.exception.code, "OFFICE_INVALID_OR_MISMATCHED")
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(b"PK\x03\x04truncated", "broken.xlsx", mime, budget())
        self.assertEqual(caught.exception.code, "OFFICE_INVALID_OR_MISMATCHED")
        hostile = with_extra_part(make_xlsx(), "xl/vbaProject.bin", b"MZ fake active object")
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(hostile, "active.xlsx", mime, budget())
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        corrupt = corrupt_zip_member(make_xlsx(), "xl/workbook.xml")
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(corrupt, "corrupt.xlsx", mime, budget())
        self.assertEqual(caught.exception.code, "OFFICE_INVALID_OR_MISMATCHED")
        encrypted_container = bytes.fromhex("D0CF11E0A1B11AE1") + bytes(64)
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(encrypted_container, "encrypted.xlsx", mime, budget())
        self.assertEqual(caught.exception.code, "OFFICE_INVALID_OR_MISMATCHED")

    def test_external_relationship_is_rejected(self):
        source = make_xlsx()
        archive = ZipFile(BytesIO(source), "r")
        output = BytesIO()
        rel_name = "xl/_rels/workbook.xml.rels"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in archive.infolist():
                raw = archive.read(item.filename)
                if item.filename == rel_name:
                    root = etree.fromstring(raw)
                    rel = etree.SubElement(root, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
                    rel.set("Id", "external")
                    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink")
                    rel.set("Target", "https://example.invalid/")
                    rel.set("TargetMode", "External")
                    raw = etree.tostring(root)
                dst.writestr(item, raw)
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                output.getvalue(), "external.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
            )
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")

    def test_disabled_legacy_and_macro_formats_are_refused(self):
        # Valid CFB signature is sufficient for format recognition; content reading stays disabled.
        cfb = bytes.fromhex("D0CF11E0A1B11AE1") + bytes(64)
        for filename, mime in (("legacy.xls", "application/vnd.ms-excel"), ("legacy.doc", "application/msword")):
            with self.subTest(filename=filename), self.assertRaises(OfficeCoreError) as caught:
                inspect_document(cfb, filename, mime, budget())
            self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        with self.assertRaises(OfficeCoreError):
            inspect_document(make_xlsx(), "macro.xlsm", "application/vnd.ms-excel.sheet.macroEnabled.12", budget())

    def test_hostile_xml_doctype_is_rejected_without_entity_resolution(self):
        source = make_xlsx()
        archive = zipfile.ZipFile(BytesIO(source), "r")
        payload = b'<!DOCTYPE x [<!ENTITY boom "boom">]><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>&boom;</t></is></c></row></sheetData></worksheet>'
        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in archive.infolist():
                dst.writestr(item, payload if item.filename == "xl/worksheets/sheet1.xml" else archive.read(item.filename))
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                output.getvalue(), "hostile.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
            )
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")

    def test_declared_file_expanded_entry_and_count_budgets(self):
        source = make_xlsx()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        for limited in (
            budget(max_file_size=10),
            budget(max_expanded_size=10),
            budget(max_zip_entries=1),
            budget(max_entry_size=10),
            budget(max_xml_elements=1),
        ):
            with self.subTest(limited=limited), self.assertRaises(OfficeCoreError) as caught:
                inspect_document(source, "source.xlsx", mime, limited)
            self.assertEqual(caught.exception.code, "OFFICE_RESOURCE_LIMIT")

    def test_invalid_policy_and_timeout_are_stable_and_cleanup_worker(self):
        with self.assertRaises(ValueError):
            budget(max_expanded_size=0).validate()
        for timeout in (float("nan"), float("inf"), 10**10000):
            with self.subTest(timeout_type=type(timeout).__name__), self.assertRaises(ValueError):
                budget(timeout_seconds=timeout).validate()
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                make_xlsx(), "source.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                budget(timeout_seconds=0.001),
            )
        self.assertEqual(caught.exception.code, "OFFICE_RESOURCE_LIMIT")
        self.assertEqual(multiprocessing.active_children(), [])

    def test_rss_budget_allows_normal_worker_and_fails_closed_when_unobservable(self):
        source = make_xlsx()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        result = inspect_document(
            source, "source.xlsx", mime,
            budget(max_memory_bytes=4_000_000_000),
        )
        self.assertEqual(result.format, "xlsx")

        with patch("office_core.service._process_rss_bytes", return_value=None):
            with self.assertRaises(OfficeCoreError) as caught:
                inspect_document(source, "source.xlsx", mime, budget())
        self.assertEqual(caught.exception.code, "OFFICE_RESOURCE_LIMIT")
        self.assertEqual(multiprocessing.active_children(), [])

    def test_rss_budget_terminates_worker_above_limit(self):
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                make_xlsx(),
                "source.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                budget(max_memory_bytes=1),
            )
        self.assertEqual(caught.exception.code, "OFFICE_RESOURCE_LIMIT")
        self.assertEqual(multiprocessing.active_children(), [])

    def test_synthetic_xlsx_extension_structure_fails_closed(self):
        source = with_xml_child(
            make_xlsx(),
            "xl/worksheets/sheet1.xml",
            b'<extLst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>',
        )
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                source, "synthetic-extension.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
            )
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")

    def test_docx_textbox_is_rejected_as_unverified_structure(self):
        source = make_docx()
        archive = ZipFile(BytesIO(source), "r")
        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in archive.infolist():
                raw = archive.read(item.filename)
                if item.filename == "word/document.xml":
                    root = etree.fromstring(raw)
                    root.append(etree.fromstring(
                        b'<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:txbxContent/></w:r></w:p>'
                    ))
                    raw = etree.tostring(root)
                dst.writestr(item, raw)
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                output.getvalue(), "textbox.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", budget(),
            )
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")

    def test_warning_classifier_fails_closed(self):
        item = warnings.WarningMessage(UserWarning("Conditional Formatting extension is unsupported and will be removed"), UserWarning, "x.py", 1)
        with self.assertRaises(OfficeCoreError) as caught:
            _parser_warning_gate([item], "warning-test")
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")

    def test_public_errors_are_stable_and_sanitized(self):
        with self.assertRaises(OfficeCoreError) as caught:
            inspect_document(
                b"not a document", "private-template.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", budget(),
            )
        error = caught.exception.as_dict()
        self.assertEqual(set(error), {"error_code", "failed_stage", "message"})
        self.assertEqual(error["error_code"], "OFFICE_INVALID_OR_MISMATCHED")
        self.assertNotIn("Traceback", str(error))
        self.assertNotIn(str(ROOT), str(error))

    def test_package_boundary_has_no_forbidden_imports_or_ignore_warning(self):
        package_root = Path(__file__).resolve().parents[1]
        forbidden = {"odoo", "llm", "requests", "httpx", "urllib", "subprocess"}
        for path in package_root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name.split(".")[0] in forbidden for alias in node.names), path.name)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], forbidden, path.name)
            self.assertNotIn('simplefilter("ignore")', source)
            self.assertNotIn("simplefilter('ignore')", source)


def load_cell(content: bytes):
    from openpyxl import load_workbook

    workbook = load_workbook(BytesIO(content), data_only=False)
    cell = workbook.active["A1"]
    result = "" if cell.value is None and cell.data_type == "inlineStr" else cell.value
    workbook.close()
    return result


if __name__ == "__main__":
    unittest.main()
