from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import io
import unittest
import zipfile
from pathlib import Path

from office_verify import OfficeVerifyError, VerificationBudget, VerificationPolicy, verify_output


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def make_zip(parts: dict[str, str | bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in parts.items():
            archive.writestr(name, value.encode("utf-8") if isinstance(value, str) else value)
    return stream.getvalue()


def xlsx(sheet_xml: str | None = None, styles_xml: str | None = None, extra: dict[str, str] | None = None) -> bytes:
    parts: dict[str, str] = {
        "[Content_Types].xml": f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>',
        "_rels/.rels": f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<workbook xmlns="{MAIN}" xmlns:r="{DOC_REL}"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": sheet_xml or f'<worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>old</t></is></c><c r="B1"><f>SUM(A1:A1)</f><v>3</v></c><c r="C1"><v>7</v></c></row><row r="2"/></sheetData><mergeCells count="1"><mergeCell ref="A2:B2"/></mergeCells></worksheet>',
    }
    if styles_xml is not None:
        parts["xl/styles.xml"] = styles_xml
    if extra:
        parts.update(extra)
    return make_zip(parts)


def docx(document_xml: str | None = None, styles_xml: str | None = None) -> bytes:
    parts: dict[str, str] = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/_rels/document.xml.rels": f'<Relationships xmlns="{REL}"/>',
        "word/document.xml": document_xml or f'<w:document xmlns:w="{DOC}"><w:body><w:p><w:r><w:t>Hello </w:t></w:r><w:r><w:t>there</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>old cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>',
    }
    if styles_xml is not None:
        parts["word/styles.xml"] = styles_xml
    return make_zip(parts)


def plan_for(content: bytes, element_id: str, kind: str, data: object) -> dict[str, object]:
    return {
        "schema_version": "1",
        "template_sha256": hashlib.sha256(content).hexdigest(),
        "writes": [{"element_id": element_id, "operation": "set_value", "value": {"type": kind, "data": data}}],
    }


def changed_xlsx(value: str = "new", formula: str = "SUM(A1:A1)", cache: str | None = "", other: str = "7") -> bytes:
    formula_value = "" if cache is None else f"<v>{cache}</v>"
    return xlsx(
        f'<worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>{value}</t></is></c><c r="B1"><f>{formula}</f>{formula_value}</c><c r="C1"><v>{other}</v></c></row><row r="2"/></sheetData><mergeCells count="1"><mergeCell ref="A2:B2"/></mergeCells></worksheet>'
    )


def xlsx_with_custom_properties(*, include_directories: bool = True, value: str = "stable") -> bytes:
    base = xlsx()
    with zipfile.ZipFile(io.BytesIO(base), "r") as source:
        parts = {item.filename: source.read(item.filename) for item in source.infolist() if not item.is_dir()}
    parts["_rels/.rels"] = parts["_rels/.rels"].replace(
        b"</Relationships>",
        b'<Relationship Id="rIdCustom" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/></Relationships>',
    )
    parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
        b"</Types>",
        b'<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/></Types>',
    )
    parts["docProps/custom.xml"] = (
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f'<property name="Probe" fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="2"><vt:lpwstr>{value}</vt:lpwstr></property>'
        "</Properties>"
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
        if include_directories:
            archive.writestr("docProps/", b"")
            archive.writestr("xl/", b"")
    return output.getvalue()


def replace_xlsx_text(source: bytes, old: bytes, new: bytes, *, include_directories: bool = False) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source), "r") as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as candidate:
        for item in original.infolist():
            if item.is_dir():
                continue
            content = original.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                content = content.replace(old, new)
            candidate.writestr(item.filename, content)
        if include_directories:
            candidate.writestr("docProps/", b"")
            candidate.writestr("xl/", b"")
    return output.getvalue()


class OfficeVerifyTests(unittest.TestCase):
    def verify(self, source: bytes, candidate: bytes, filename: str, mime: str, plan: dict[str, object], **kwargs):
        return verify_output(source, candidate, filename, mime, plan, **kwargs)

    def test_dependencies_and_package_boundary(self):
        import lxml

        self.assertEqual(lxml.__version__, "4.9.3")
        self.assertEqual(importlib.metadata.version("lxml"), "4.9.3")
        root = Path(__file__).parents[1]
        requirement_lines = (root / "requirements.txt").read_text().splitlines()
        self.assertEqual(requirement_lines, ["lxml==4.9.3"])
        for path in root.glob("*.py"):
            source = path.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    self.assertFalse(name.startswith(("office_core", "odoo", "llm_", "requests", "httpx", "queue")), (path, name))
        parser_source = (root / "security.py").read_text()
        for setting in ("resolve_entities=False", "load_dtd=False", "no_network=True", "huge_tree=False", "recover=False"):
            self.assertIn(setting, parser_source)

    def test_valid_xlsx_value_formula_cache_and_structure(self):
        source = xlsx()
        candidate = changed_xlsx()
        before = hashlib.sha256(source).hexdigest()
        after = hashlib.sha256(candidate).hexdigest()
        report = self.verify(source, candidate, "sample.xlsx", XLSX_MIME, plan_for(source, "xlsx:Sheet1!A1", "string", "new"))
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.checked_targets, 1)
        self.assertEqual(report.checked_formulas, 1)
        self.assertTrue(report.cached_value_changed)
        self.assertEqual(report.formula_cache_status, ({
            "element_id": "xlsx:Sheet1!B1",
            "source_cache": "present",
            "output_cache": "missing",
            "cached_value_changed": True,
        },))
        self.assertEqual(hashlib.sha256(source).hexdigest(), before)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), after)
        self.assertEqual(report.as_dict()["cached_value_changed"], True)

    def test_blank_cells_between_used_cells_are_valid_targets(self):
        source = xlsx(
            f'<worksheet xmlns="{MAIN}"><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>客户名称</t></is></c><c r="C1"><f>B2*1.13</f></c></row>'
            '<row r="2"><c r="A2" t="inlineStr"><is><t>金额</t></is></c><c r="C2"><f>SUM(B2:B5)</f></c></row>'
            '</sheetData></worksheet>'
        )
        candidate = xlsx(
            f'<worksheet xmlns="{MAIN}"><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>客户名称</t></is></c><c r="B1" t="inlineStr"><is><t>Acme Corporation</t></is></c><c r="C1"><f>B2*1.13</f></c></row>'
            '<row r="2"><c r="A2" t="inlineStr"><is><t>金额</t></is></c><c r="B2"><v>2000</v></c><c r="C2"><f>SUM(B2:B5)</f></c></row>'
            '</sheetData></worksheet>'
        )
        plan = {
            "schema_version": "1",
            "template_sha256": hashlib.sha256(source).hexdigest(),
            "writes": [
                {"element_id": "xlsx:Sheet1!B1", "operation": "set_value", "value": {"type": "string", "data": "Acme Corporation"}},
                {"element_id": "xlsx:Sheet1!B2", "operation": "set_value", "value": {"type": "number", "data": 2000}},
            ],
        }
        report = self.verify(source, candidate, "complex.xlsx", XLSX_MIME, plan)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.checked_targets, 2)
        self.assertEqual(report.checked_formulas, 2)

    def test_hidden_sheet_visibility_change_fails(self):
        source = xlsx()
        with zipfile.ZipFile(io.BytesIO(source), "r") as archive:
            parts = {item.filename: archive.read(item.filename) for item in archive.infolist() if not item.is_dir()}
        parts["xl/workbook.xml"] = parts["xl/workbook.xml"].replace(
            b'name="Sheet1" sheetId="1"', b'name="Sheet1" sheetId="1" state="hidden"'
        )
        hidden_source = make_zip(parts)
        changed = dict(parts)
        changed["xl/workbook.xml"] = changed["xl/workbook.xml"].replace(b'state="hidden"', b'state="veryHidden"')
        changed_output = make_zip(changed)
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(
                hidden_source,
                changed_output,
                "sample.xlsx",
                XLSX_MIME,
                plan_for(hidden_source, "xlsx:Sheet1!A1", "string", "old"),
            )
        self.assertEqual(caught.exception.code, "OFFICE_STRUCTURE_MISMATCH")

    def test_custom_properties_and_explicit_zip_directories_are_supported(self):
        source = xlsx_with_custom_properties()
        candidate = replace_xlsx_text(source, b">old</t>", b">new</t>")
        report = self.verify(
            source,
            candidate,
            "custom.xlsx",
            XLSX_MIME,
            plan_for(source, "xlsx:Sheet1!A1", "string", "new"),
        )
        self.assertEqual(report.status, "PASS")

        changed_metadata = xlsx_with_custom_properties(include_directories=False, value="changed")
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(
                source,
                replace_xlsx_text(changed_metadata, b">old</t>", b">new</t>"),
                "custom.xlsx",
                XLSX_MIME,
                plan_for(source, "xlsx:Sheet1!A1", "string", "new"),
            )
        self.assertEqual(caught.exception.code, "OFFICE_STRUCTURE_MISMATCH")

    def test_xlsx_formula_change_fails_and_cache_value_not_exposed(self):
        source = xlsx()
        plan = plan_for(source, "xlsx:Sheet1!A1", "string", "new")
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(source, changed_xlsx(formula="SUM(A1:C1)"), "sample.xlsx", XLSX_MIME, plan)
        self.assertEqual(caught.exception.code, "OFFICE_FORMULA_MISMATCH")
        self.assertNotIn("3", str(caught.exception))

    def test_target_value_mismatch_and_non_target_mutation_fail(self):
        source = xlsx()
        plan = plan_for(source, "xlsx:Sheet1!A1", "string", "expected")
        with self.assertRaises(OfficeVerifyError) as target:
            self.verify(source, changed_xlsx(), "sample.xlsx", XLSX_MIME, plan)
        self.assertEqual(target.exception.code, "OFFICE_TARGET_MISMATCH")
        altered = changed_xlsx(other="8")
        with self.assertRaises(OfficeVerifyError) as non_target:
            self.verify(source, altered, "sample.xlsx", XLSX_MIME, plan_for(source, "xlsx:Sheet1!A1", "string", "new"))
        self.assertEqual(non_target.exception.code, "OFFICE_STRUCTURE_MISMATCH")

    def test_merge_structure_and_required_parts_are_enforced(self):
        source = xlsx()
        candidate = changed_xlsx()
        plan = plan_for(source, "xlsx:Sheet1!A1", "string", "new")
        merged_xml = zipfile.ZipFile(io.BytesIO(candidate)).read("xl/worksheets/sheet1.xml").decode()
        merged_xml = merged_xml.replace('<mergeCells count="1"><mergeCell ref="A2:B2"/></mergeCells>', "")
        changed_merge = xlsx(merged_xml)
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(source, changed_merge, "sample.xlsx", XLSX_MIME, plan)
        self.assertEqual(caught.exception.code, "OFFICE_STRUCTURE_MISMATCH")
        with self.assertRaises(OfficeVerifyError):
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME, plan,
                        policy=VerificationPolicy(required_parts=("xl/styles.xml",)))

    def test_xlsx_unknown_mapping_formula_target_and_null_fail(self):
        source = xlsx()
        base = plan_for(source, "xlsx:Sheet1!A1", "string", "new")
        bad = dict(base, unexpected=True)
        for plan, expected in (
            (bad, "OFFICE_MAPPING_INVALID"),
            (plan_for(source, "xlsx:Sheet1!B1", "string", "oops"), "OFFICE_MAPPING_INVALID"),
            (plan_for(source, "xlsx:Sheet1!A1", "string", None), "NULL_NOT_SUPPORTED"),
        ):
            with self.subTest(expected=expected):
                with self.assertRaises(OfficeVerifyError) as caught:
                    self.verify(source, changed_xlsx(), "sample.xlsx", XLSX_MIME, plan)
                self.assertEqual(caught.exception.code, expected)

    def test_docx_plain_text_is_compared_across_run_splits(self):
        source = docx()
        candidate = docx(f'<w:document xmlns:w="{DOC}"><w:body><w:p><w:r><w:t>Hello </w:t></w:r><w:r><w:t>world</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>old cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>')
        report = self.verify(source, candidate, "sample.docx", DOCX_MIME, plan_for(source, "docx:p:1", "string", "Hello world"))
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.checked_targets, 1)

    def test_docx_table_target_and_non_target_change(self):
        source = docx()
        candidate_xml = f'<w:document xmlns:w="{DOC}"><w:body><w:p><w:r><w:t>Hello </w:t></w:r><w:r><w:t>there</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>new cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>'
        plan = plan_for(source, "docx:table:1:row:1:cell:1:p:1", "string", "new cell")
        self.assertEqual(self.verify(source, docx(candidate_xml), "sample.docx", DOCX_MIME, plan).status, "PASS")
        changed = candidate_xml.replace("Hello ", "Changed ")
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(source, docx(changed), "sample.docx", DOCX_MIME, plan)
        self.assertEqual(caught.exception.code, "OFFICE_STRUCTURE_MISMATCH")

    def test_docx_non_target_run_style_change_is_warning_or_fatal_by_policy(self):
        source = docx()
        styled_xml = f'<w:document xmlns:w="{DOC}"><w:body><w:p><w:r><w:t>Hello </w:t></w:r><w:r><w:t>world</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>old cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>'
        candidate = docx(styled_xml)
        plan = plan_for(source, "docx:p:1", "string", "Hello world")
        report = self.verify(source, candidate, "sample.docx", DOCX_MIME, plan)
        self.assertIn("NON_TARGET_STYLE_CHANGED", [item["code"] for item in report.warnings])
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(source, candidate, "sample.docx", DOCX_MIME, plan, policy=VerificationPolicy(require_styles=True))
        self.assertEqual(caught.exception.code, "OFFICE_STRUCTURE_MISMATCH")

    def test_docx_unsupported_control_structure_fails_closed(self):
        source = docx()
        unsafe = docx(f'<w:document xmlns:w="{DOC}"><w:body><w:p><w:r><w:tab/></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>old cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr/></w:body></w:document>')
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(source, unsafe, "sample.docx", DOCX_MIME, plan_for(source, "docx:p:1", "string", "x"))
        self.assertEqual(caught.exception.code, "OFFICE_STRUCTURE_MISMATCH")

    def test_styles_are_warning_unless_policy_requires_them(self):
        style_a = f'<styleSheet xmlns="{MAIN}"><fonts count="1"/></styleSheet>'
        style_b = f'<styleSheet xmlns="{MAIN}"><fonts count="2"/></styleSheet>'
        source = xlsx(styles_xml=style_a)
        # Keep the candidate's changed cell/formula data while changing only styles.
        base = changed_xlsx()
        candidate_parts = zipfile.ZipFile(io.BytesIO(base)).read("xl/worksheets/sheet1.xml").decode()
        candidate = xlsx(candidate_parts, styles_xml=style_b)
        plan = plan_for(source, "xlsx:Sheet1!A1", "string", "new")
        report = self.verify(source, candidate, "sample.xlsx", XLSX_MIME, plan)
        self.assertIn("NON_TARGET_STYLE_PART_CHANGED", [item["code"] for item in report.warnings])
        with self.assertRaises(OfficeVerifyError):
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME, plan, policy=VerificationPolicy(require_styles=True))

    def test_empty_fake_truncated_crc_and_path_traversal_fail(self):
        valid = xlsx()
        plan = plan_for(valid, "xlsx:Sheet1!A1", "string", "new")
        for bad in (b"", b"not an office file", valid[:-12]):
            with self.subTest(size=len(bad)):
                with self.assertRaises(OfficeVerifyError):
                    self.verify(bad, valid, "sample.xlsx", XLSX_MIME, plan)
        corrupt = bytearray(valid)
        corrupt[-20] ^= 0xFF
        with self.assertRaises(OfficeVerifyError):
            self.verify(valid, bytes(corrupt), "sample.xlsx", XLSX_MIME, plan)
        traversal = xlsx(extra={"../escape.txt": "bad"})
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(traversal, valid, "sample.xlsx", XLSX_MIME, plan_for(traversal, "xlsx:Sheet1!A1", "string", "new"))
        self.assertEqual(caught.exception.code, "OFFICE_INVALID_OR_MISMATCHED")

    def test_unknown_parts_external_links_and_old_format_are_rejected(self):
        source = xlsx()
        plan = plan_for(source, "xlsx:Sheet1!A1", "string", "new")
        unknown = xlsx(extra={"xl/drawings/drawing1.xml": "<drawing/>"})
        with self.assertRaises(OfficeVerifyError):
            self.verify(unknown, unknown, "sample.xlsx", XLSX_MIME, plan_for(unknown, "xlsx:Sheet1!A1", "string", "new"))
        external = make_zip({
            "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
            "_rels/.rels": f'<Relationships xmlns="{REL}"><Relationship Id="rId1" Type="x" Target="https://invalid.example" TargetMode="External"/></Relationships>',
            "xl/workbook.xml": f'<workbook xmlns="{MAIN}"/>',
            "xl/_rels/workbook.xml.rels": f'<Relationships xmlns="{REL}"/>',
            "xl/worksheets/sheet1.xml": f'<worksheet xmlns="{MAIN}"><sheetData/></worksheet>',
        })
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(external, external, "sample.xlsx", XLSX_MIME, plan_for(external, "x", "string", "x"))
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        external_formula = xlsx(
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>old</t></is></c><c r="B1"><f>\'[other.xlsx]Sheet1\'!A1</f><v>1</v></c></row></sheetData></worksheet>'
        )
        with self.assertRaises(OfficeVerifyError) as formula_caught:
            self.verify(external_formula, external_formula, "sample.xlsx", XLSX_MIME,
                        plan_for(external_formula, "xlsx:Sheet1!A1", "string", "old"))
        self.assertEqual(formula_caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        with self.assertRaises(OfficeVerifyError):
            self.verify(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", b"", "old.xls", "application/vnd.ms-excel", {})

    def test_doctype_entities_rejected_and_predefined_entities_accepted(self):
        safe_source = xlsx(sheet_xml=f'<worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>A&amp;B</t></is></c></row></sheetData></worksheet>')
        safe_candidate = xlsx(sheet_xml=f'<worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>A&amp;B!</t></is></c></row></sheetData></worksheet>')
        self.assertEqual(self.verify(safe_source, safe_candidate, "sample.xlsx", XLSX_MIME, plan_for(safe_source, "xlsx:Sheet1!A1", "string", "A&B!")).status, "PASS")
        hostile_sheet = f'<!DOCTYPE worksheet [<!ENTITY xxe "secret">]><worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>&xxe;</t></is></c></row></sheetData></worksheet>'
        hostile = xlsx(sheet_xml=hostile_sheet)
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(hostile, hostile, "sample.xlsx", XLSX_MIME, plan_for(hostile, "x", "string", "x"))
        self.assertEqual(caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        self.assertNotIn("secret", str(caught.exception))
        external_sheet = f'<!DOCTYPE worksheet [<!ENTITY xxe SYSTEM "file:///etc/hosts">]><worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>&xxe;</t></is></c></row></sheetData></worksheet>'
        external = xlsx(sheet_xml=external_sheet)
        with self.assertRaises(OfficeVerifyError) as external_caught:
            self.verify(external, external, "sample.xlsx", XLSX_MIME, plan_for(external, "unknown", "string", "x"))
        self.assertEqual(external_caught.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        self.assertNotIn("localhost", str(external_caught.exception))

    def test_resource_budgets_are_enforced_without_partial_pass(self):
        source = xlsx()
        candidate = changed_xlsx()
        tiny = VerificationBudget(max_file_size=100, max_expanded_size=100, max_zip_entries=20, max_entry_size=80,
                                  max_xml_elements=100, max_cells=100, max_paragraphs=100,
                                  max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as caught:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME, plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=tiny)
        self.assertEqual(caught.exception.code, "OFFICE_RESOURCE_LIMIT")
        expanded_budget = VerificationBudget(max_file_size=1024 * 1024, max_expanded_size=100,
                                             max_zip_entries=20, max_entry_size=1024 * 1024,
                                             max_xml_elements=1000, max_cells=100, max_paragraphs=100,
                                             max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as expanded:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME,
                        plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=expanded_budget)
        self.assertEqual(expanded.exception.code, "OFFICE_RESOURCE_LIMIT")
        entries_budget = VerificationBudget(max_file_size=1024 * 1024, max_expanded_size=1024 * 1024,
                                            max_zip_entries=1, max_entry_size=1024 * 1024,
                                            max_xml_elements=1000, max_cells=100, max_paragraphs=100,
                                            max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as entries:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME,
                        plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=entries_budget)
        self.assertEqual(entries.exception.code, "OFFICE_RESOURCE_LIMIT")
        xml_budget = VerificationBudget(max_file_size=1024 * 1024, max_expanded_size=1024 * 1024,
                                        max_zip_entries=20, max_entry_size=1024 * 1024,
                                        max_xml_elements=3, max_cells=100, max_paragraphs=100,
                                        max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as xml_nodes:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME,
                        plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=xml_budget)
        self.assertEqual(xml_nodes.exception.code, "OFFICE_RESOURCE_LIMIT")
        entry_size_budget = VerificationBudget(max_file_size=1024 * 1024, max_expanded_size=1024 * 1024,
                                               max_zip_entries=20, max_entry_size=32,
                                               max_xml_elements=1000, max_cells=100, max_paragraphs=100,
                                               max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as entry_size:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME,
                        plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=entry_size_budget)
        self.assertEqual(entry_size.exception.code, "OFFICE_RESOURCE_LIMIT")
        doc = docx()
        paragraph_budget = VerificationBudget(max_file_size=1024 * 1024, max_expanded_size=1024 * 1024,
                                              max_zip_entries=20, max_entry_size=1024 * 1024,
                                              max_xml_elements=1000, max_cells=100, max_paragraphs=1,
                                              max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as paragraphs:
            self.verify(doc, doc, "sample.docx", DOCX_MIME,
                        plan_for(doc, "docx:p:1", "string", "Hello there"), budget=paragraph_budget)
        self.assertEqual(paragraphs.exception.code, "OFFICE_RESOURCE_LIMIT")
        memory_budget = VerificationBudget(max_file_size=1024 * 1024, max_expanded_size=1024 * 1024,
                                           max_zip_entries=20, max_entry_size=1024 * 1024,
                                           max_xml_elements=100, max_cells=100, max_paragraphs=100,
                                           max_memory_bytes=1024 * 1024, timeout_seconds=10)
        with self.assertRaises(OfficeVerifyError) as memory:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME,
                        plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=memory_budget)
        self.assertEqual(memory.exception.code, "OFFICE_RESOURCE_LIMIT")
        timeout_budget = VerificationBudget(max_memory_bytes=4 * 1024 * 1024 * 1024, timeout_seconds=0.001)
        with self.assertRaises(OfficeVerifyError) as timeout:
            self.verify(source, candidate, "sample.xlsx", XLSX_MIME, plan_for(source, "xlsx:Sheet1!A1", "string", "new"), budget=timeout_budget)
        self.assertEqual(timeout.exception.code, "OFFICE_RESOURCE_LIMIT")


if __name__ == "__main__":
    unittest.main()
