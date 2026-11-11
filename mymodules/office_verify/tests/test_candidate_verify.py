from __future__ import annotations

import hashlib
import io
import json
import unittest
import zipfile
from openpyxl import load_workbook

from office_verify import OfficeVerifyError, VerificationBudget, verify_candidate_output, verify_output
from office_verify.verify import _canonical_effect


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def workbook(a1: str = "10", b1: str = "KEEP", *, formula: str = "A1*2") -> bytes:
    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{REL}"><Relationship Id="rId1" '
            f'Type="{DOC_REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{MAIN}" xmlns:r="{DOC_REL}"><sheets>'
            '<sheet name="Data" sheetId="1" r:id="rId1"/>'
            '<sheet name="Notes" sheetId="2" r:id="rId2"/>'
            '</sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{REL}">'
            f'<Relationship Id="rId1" Type="{DOC_REL}/worksheet" Target="worksheets/sheet1.xml"/>'
            f'<Relationship Id="rId2" Type="{DOC_REL}/worksheet" Target="worksheets/sheet2.xml"/>'
            '</Relationships>'
        ),
        "xl/worksheets/sheet1.xml": (
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
            f'<c r="A1"><v>{a1}</v></c>'
            f'<c r="B1" t="inlineStr"><is><t>{b1}</t></is></c>'
            f'<c r="C1"><f>{formula}</f><v>20</v></c>'
            '</row></sheetData></worksheet>'
        ),
        "xl/worksheets/sheet2.xml": (
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
            '<c r="A1" t="inlineStr"><is><t>protected</t></is></c>'
            '</row></sheetData></worksheet>'
        ),
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content.encode())
    return stream.getvalue()


def effect_for(source: bytes, *, target="A1", sheet="Data", expected=15, unknowns=()):
    value = {
        "schema_version": "1",
        "parent_version_id": 17,
        "input_sha256": hashlib.sha256(source).hexdigest(),
        "target_scopes": [{"kind": "cell", "sheet": sheet, "address": target}],
        "allowed_change_kinds": ["cell_value"],
        "expected_assertions": [{
            "kind": "cell_value", "sheet": sheet, "address": target,
            "value_type": "number", "value": expected,
        }] if expected is not None else [],
        "unknowns": list(unknowns),
    }
    return seal_effect(value)


def date_effect_for(source: bytes, *, value_type: str, value: str):
    return seal_effect({
        "schema_version": "1",
        "parent_version_id": 17,
        "input_sha256": hashlib.sha256(source).hexdigest(),
        "target_scopes": [{"kind": "cell", "sheet": "Data", "address": "A1"}],
        "allowed_change_kinds": ["cell_value"],
        "expected_assertions": [{
            "kind": "cell_value", "sheet": "Data", "address": "A1",
            "value_type": value_type, "value": value,
        }],
        "unknowns": [],
    })


def zip_part(content: bytes, part_name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
        return archive.read(part_name)


def date_serial_workbook(
    *, value: str = "45294", number_format: str | None = None, builtin_num_format_id: int | None = None
):
    content = workbook(value)
    if number_format is None and builtin_num_format_id is None:
        return content
    worksheet = (
        f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
        f'<c r="A1" s="1"><v>{value}</v></c>'
        '<c r="B1" t="inlineStr"><is><t>KEEP</t></is></c>'
        '<c r="C1"><f>A1*2</f><v>20</v></c>'
        '</row></sheetData></worksheet>'
    ).encode()
    content = replace_part(content, "xl/worksheets/sheet1.xml", worksheet)
    if number_format is not None:
        styles_xml = (
            f'<styleSheet xmlns="{MAIN}"><numFmts count="1">'
            f'<numFmt numFmtId="164" formatCode="{number_format}"/>'
            '</numFmts><cellXfs count="2"><xf/><xf numFmtId="164" applyNumberFormat="1"/>'
            '</cellXfs></styleSheet>'
        )
    else:
        styles_xml = (
            f'<styleSheet xmlns="{MAIN}"><cellXfs count="2"><xf/>'
            f'<xf numFmtId="{builtin_num_format_id}" applyNumberFormat="1"/></cellXfs></styleSheet>'
        )
    styles = styles_xml.encode()
    content_types = zip_part(content, "[Content_Types].xml")
    content = replace_part(
        content,
        "[Content_Types].xml",
        content_types.replace(
            b"</Types>",
            b'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        ),
    )
    workbook_rels = zip_part(content, "xl/_rels/workbook.xml.rels")
    content = replace_part(
        content,
        "xl/_rels/workbook.xml.rels",
        workbook_rels.replace(
            b"</Relationships>",
            f'<Relationship Id="rId3" Type="{DOC_REL}/styles" Target="styles.xml"/></Relationships>'.encode(),
        ),
    )
    return replace_part(content, "xl/styles.xml", styles)


def seal_effect(value):
    payload = {key: item for key, item in value.items() if key != "effect_digest"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    value["effect_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return value


def replace_part(source: bytes, name: str, content: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source), "r") as before, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as after:
        replaced = False
        for member in before.infolist():
            value = content if member.filename == name else before.read(member.filename)
            replaced = replaced or member.filename == name
            after.writestr(member.filename, value)
        if not replaced:
            after.writestr(name, content)
    return output.getvalue()


def core_properties_xml(*, modified: str, title: str = "Synthetic workbook") -> bytes:
    return (
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{title}</dc:title>"
        "<dc:creator>Synthetic TV</dc:creator>"
        '<dcterms:created xsi:type="dcterms:W3CDTF">2026-11-10T00:00:00Z</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>'
        "</cp:coreProperties>"
    ).encode()


def with_core_properties(source: bytes, *, modified: str, title: str = "Synthetic workbook") -> bytes:
    content_types = zip_part(source, "[Content_Types].xml")
    content_types = content_types.replace(
        b"</Types>",
        b'<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>',
    )
    source = replace_part(source, "[Content_Types].xml", content_types)
    root_relationships = zip_part(source, "_rels/.rels")
    root_relationships = root_relationships.replace(
        b"</Relationships>",
        b'<Relationship Id="rIdCore" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>',
    )
    source = replace_part(source, "_rels/.rels", root_relationships)
    return replace_part(source, "docProps/core.xml", core_properties_xml(modified=modified, title=title))


class CandidateVerifyTests(unittest.TestCase):
    def verify(self, source, candidate, effect, **kwargs):
        return verify_candidate_output(
            source, candidate, "neutral.xlsx", MIME, effect,
            budget=kwargs.get("budget", VerificationBudget()),
        )

    def test_core_modified_timestamp_change_is_semantic_metadata_not_an_effect(self):
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        sheet = zip_part(source, "xl/worksheets/sheet1.xml").replace(b"<v>10</v>", b"<v>15</v>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", sheet)
        candidate = replace_part(
            candidate, "docProps/core.xml",
            core_properties_xml(modified="2026-11-11T01:32:14Z"),
        )

        report = self.verify(source, candidate, effect_for(source))

        self.assertEqual(report.validation_result, "VERIFIED", report.error)
        self.assertEqual([item["change_kind"] for item in report.actual_effects], ["cell_value"])
        self.assertIsNone(report.error)

    def test_core_properties_namespace_prefix_serialization_is_semantically_ignored(self):
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        sheet = zip_part(source, "xl/worksheets/sheet1.xml").replace(b"<v>10</v>", b"<v>15</v>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", sheet)
        core = core_properties_xml(modified="2026-11-11T01:32:14Z")
        core = core.replace(b"xmlns:dcterms=", b"xmlns:terms=").replace(b"dcterms:", b"terms:")
        core = core.replace(b"xmlns:xsi=", b"xmlns:i=").replace(b"xsi:type", b"i:type")
        candidate = replace_part(candidate, "docProps/core.xml", core)

        report = self.verify(source, candidate, effect_for(source))

        self.assertEqual(report.validation_result, "VERIFIED", report.error)
        self.assertEqual([item["change_kind"] for item in report.actual_effects], ["cell_value"])

    def test_core_metadata_change_does_not_authorize_non_target_cell_change(self):
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        sheet = zip_part(source, "xl/worksheets/sheet1.xml")
        sheet = sheet.replace(b"<v>10</v>", b"<v>15</v>").replace(b"<t>KEEP</t>", b"<t>UNAUTHORIZED</t>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", sheet)
        candidate = replace_part(
            candidate, "docProps/core.xml",
            core_properties_xml(modified="2026-11-11T01:32:14Z"),
        )

        report = self.verify(source, candidate, effect_for(source))

        self.assertEqual(report.validation_result, "FAILED")
        self.assertTrue(any(item["target"] == "xlsx:Data!B1" for item in report.actual_effects))
        self.assertEqual(report.error["error_code"], "OFFICE_TARGET_MISMATCH")
        self.assertIn("target=xlsx:Data!B1", report.error["message"])
        self.assertIn("actual_change=", report.error["message"])

    def test_core_metadata_change_does_not_bypass_unsupported_ooxml_structure(self):
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        candidate = replace_part(
            source, "docProps/core.xml",
            core_properties_xml(modified="2026-11-11T01:32:14Z"),
        )
        sheet = zip_part(candidate, "xl/worksheets/sheet1.xml")
        sheet = sheet.replace(b"</worksheet>", b"<externalLink/></worksheet>")
        candidate = replace_part(candidate, "xl/worksheets/sheet1.xml", sheet)

        with self.assertRaises(OfficeVerifyError) as raised:
            self.verify(source, candidate, effect_for(source))

        self.assertEqual(raised.exception.code, "OFFICE_UNSUPPORTED_FEATURE")
        self.assertEqual(raised.exception.stage, "structure")

    def test_core_metadata_change_does_not_hide_unknown_package_part_change(self):
        theme_before = b'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:name>Before</a:name></a:theme>'
        theme_after = theme_before.replace(b"Before", b"After")
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        source = replace_part(source, "xl/theme/theme1.xml", theme_before)
        sheet = zip_part(source, "xl/worksheets/sheet1.xml").replace(b"<v>10</v>", b"<v>15</v>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", sheet)
        candidate = replace_part(candidate, "xl/theme/theme1.xml", theme_after)
        candidate = replace_part(
            candidate, "docProps/core.xml",
            core_properties_xml(modified="2026-11-11T01:32:14Z"),
        )

        report = self.verify(source, candidate, effect_for(source))

        self.assertEqual(report.validation_result, "FAILED")
        self.assertEqual(report.error["error_code"], "OFFICE_UNSUPPORTED_FEATURE")
        self.assertFalse(any(item["target"] == "xlsx:__package__!docProps/core.xml" for item in report.actual_effects))
        self.assertIn("xl/theme/theme1.xml", report.error["message"])

    def test_core_title_change_is_not_ignored_with_the_modified_timestamp(self):
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        sheet = zip_part(source, "xl/worksheets/sheet1.xml").replace(b"<v>10</v>", b"<v>15</v>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", sheet)
        candidate = replace_part(
            candidate, "docProps/core.xml",
            core_properties_xml(modified="2026-11-11T01:32:14Z", title="Unexpected title"),
        )

        report = self.verify(source, candidate, effect_for(source))

        self.assertEqual(report.validation_result, "FAILED")
        self.assertEqual(report.error["error_code"], "OFFICE_UNSUPPORTED_FEATURE")
        core_change = next(item for item in report.actual_effects if item["target"] == "xlsx:__package__!docProps/core.xml")
        self.assertEqual(core_change["change_kind"], "unsupported_structure")

    def test_m1_mapping_keeps_its_existing_core_properties_behavior(self):
        source = with_core_properties(workbook("10"), modified="2026-11-10T00:00:00Z")
        sheet = zip_part(source, "xl/worksheets/sheet1.xml").replace(b"<v>10</v>", b"<v>15</v>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", sheet)
        candidate = replace_part(
            candidate, "docProps/core.xml",
            core_properties_xml(modified="2026-11-11T01:32:14Z"),
        )
        mapping = {
            "schema_version": "1",
            "template_sha256": hashlib.sha256(source).hexdigest(),
            "writes": [{
                "element_id": "xlsx:Data!A1", "operation": "set_value",
                "value": {"type": "number", "data": 15},
            }],
        }

        report = verify_output(source, candidate, "neutral.xlsx", MIME, mapping)

        self.assertEqual(report.status, "PASS")

    def test_in_scope_nonempty_value_change_is_verified_and_reported_as_risk_fact(self):
        source = workbook("10")
        candidate = workbook("15")
        report = self.verify(source, candidate, effect_for(source))
        self.assertEqual(report.validation_result, "VERIFIED")
        self.assertEqual(report.input_sha256, hashlib.sha256(source).hexdigest())
        self.assertEqual(report.output_sha256, hashlib.sha256(candidate).hexdigest())
        self.assertEqual(len(report.actual_effects), 1)
        self.assertEqual(report.actual_effects[0]["before"], {"type": "number", "value": "10"})
        self.assertEqual(report.actual_effects[0]["after"], {"type": "number", "value": "15"})
        self.assertIn("existing_value_replaced", {fact["kind"] for fact in report.risk_facts})
        self.assertEqual(report.feature_results[0]["capability"], "SUPPORTED")

    def test_non_target_value_change_is_failed_not_hidden_by_target_success(self):
        source = workbook("10", "KEEP")
        candidate = workbook("15", "CHANGED")
        report = self.verify(source, candidate, effect_for(source))
        self.assertEqual(report.validation_result, "FAILED")
        self.assertTrue(any(effect["target"] == "xlsx:Data!B1" for effect in report.actual_effects))

    def test_missing_precise_expectation_cannot_claim_full_semantic_verification(self):
        source = workbook("10")
        candidate = workbook("15")
        effect = effect_for(source, expected=None, unknowns=("desired result not specified",))
        report = self.verify(source, candidate, effect)
        self.assertEqual(report.validation_result, "PARTIALLY_VERIFIED")
        self.assertTrue(report.unknowns)

    def test_formula_change_requires_explicit_change_kind(self):
        source = workbook("10", formula="A1*2")
        candidate = workbook("15", formula="A1*3")
        effect = effect_for(source)
        report = self.verify(source, candidate, effect)
        self.assertEqual(report.validation_result, "FAILED")
        self.assertIn("formula_text", {effect["change_kind"] for effect in report.actual_effects})

    def test_formula_cache_change_is_detected_without_claiming_recalculation(self):
        source = workbook("10", formula="A1*2")
        candidate = workbook("15", formula="A1*2")
        candidate_xml = (
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
            '<c r="A1"><v>15</v></c><c r="B1" t="inlineStr"><is><t>KEEP</t></is></c>'
            '<c r="C1"><f>A1*2</f><v>30</v></c></row></sheetData></worksheet>'
        ).encode()
        candidate = replace_part(candidate, "xl/worksheets/sheet1.xml", candidate_xml)
        report = self.verify(source, candidate, effect_for(source))
        self.assertEqual(report.validation_result, "FAILED")
        caches = [item for item in report.actual_effects if item["change_kind"] == "formula_cache"]
        self.assertEqual(caches[0]["before"], "20")
        self.assertEqual(caches[0]["after"], "30")
        cache_feature = next(item for item in report.feature_results if item["feature"] == "formula_cached_values")
        self.assertEqual(cache_feature["capability"], "PARTIALLY_SUPPORTED")

    def test_malformed_or_tampered_effect_digest_is_rejected(self):
        source = workbook("10")
        candidate = workbook("15")
        effect = effect_for(source)
        effect["expected_assertions"][0]["value"] = 99
        with self.assertRaises(OfficeVerifyError):
            self.verify(source, candidate, effect)

    def test_corrupt_xlsx_fails_closed(self):
        source = workbook("10")
        with self.assertRaises(OfficeVerifyError):
            self.verify(source, b"not an xlsx", effect_for(source))

    def test_resource_budget_is_enforced_before_candidate_comparison(self):
        source = workbook("10")
        with self.assertRaises(OfficeVerifyError) as raised:
            self.verify(source, workbook("15"), effect_for(source), budget=VerificationBudget(max_file_size=20))
        self.assertEqual(raised.exception.code, "OFFICE_RESOURCE_LIMIT")

    def test_expected_effect_budget_is_separate_from_m1_mapping_budget(self):
        source = workbook("10")
        effect = effect_for(source, unknowns=("u" * 100,))
        budget = VerificationBudget(max_mapping_bytes=64, max_expected_effect_bytes=512)
        _, digest = _canonical_effect(effect, hashlib.sha256(source).hexdigest(), budget)
        self.assertEqual(digest, effect["effect_digest"])

        oversized = effect_for(source, unknowns=("u" * 250, "v" * 250))
        with self.assertRaises(OfficeVerifyError) as raised:
            _canonical_effect(oversized, hashlib.sha256(source).hexdigest(), budget)
        self.assertEqual(raised.exception.code, "OFFICE_RESOURCE_LIMIT")

    def test_zero_false_empty_text_and_blank_remain_distinct(self):
        source = workbook("1", "before")
        source_xml = (
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
            '<c r="A1"><v>1</v></c><c r="B1" t="inlineStr"><is><t>before</t></is></c>'
            '<c r="C1"><f>A1*2</f><v>2</v></c><c r="E1"><v>9</v></c>'
            '</row></sheetData></worksheet>'
        ).encode()
        source = replace_part(source, "xl/worksheets/sheet1.xml", source_xml)
        xml = (
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
            '<c r="A1"><v>0</v></c><c r="B1" t="b"><v>0</v></c>'
            '<c r="C1"><f>A1*2</f><v>2</v></c>'
            '<c r="D1" t="inlineStr"><is><t></t></is></c><c r="E1"/>'
            '<c r="F1"><v>0.0</v></c></row></sheetData></worksheet>'
        ).encode()
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", xml)
        effect = effect_for(source, expected=None)
        effect["target_scopes"] = [{"kind": "range", "sheet": "Data", "start": "A1", "end": "F1"}]
        effect["allowed_change_kinds"] = ["cell_value"]
        effect["expected_assertions"] = [
            {"kind": "cell_value", "sheet": "Data", "address": "A1", "value_type": "number", "value": 0},
            {"kind": "cell_value", "sheet": "Data", "address": "B1", "value_type": "boolean", "value": False},
            {"kind": "cell_value", "sheet": "Data", "address": "D1", "value_type": "string", "value": ""},
            {"kind": "cell_value", "sheet": "Data", "address": "E1", "value_type": "blank", "value": None},
            {"kind": "cell_value", "sheet": "Data", "address": "F1", "value_type": "number", "value": 0.0},
        ]
        seal_effect(effect)
        report = self.verify(source, candidate, effect)
        self.assertEqual(report.validation_result, "VERIFIED")
        actual = {item["target"]: item["after"] for item in report.actual_effects if item["change_kind"] == "cell_value"}
        self.assertEqual(actual["xlsx:Data!A1"], {"type": "number", "value": "0"})
        self.assertEqual(actual["xlsx:Data!B1"], {"type": "boolean", "value": False})
        self.assertEqual(actual["xlsx:Data!D1"], {"type": "string", "value": ""})
        self.assertEqual(actual["xlsx:Data!E1"], {"type": "blank", "value": None})
        self.assertEqual(actual["xlsx:Data!F1"], {"type": "number", "value": "0.0"})

    def test_date_expected_does_not_accept_general_numeric_cell(self):
        content = date_serial_workbook()
        report = self.verify(content, content, date_effect_for(content, value_type="date", value="2024-01-03"))
        self.assertEqual(report.validation_result, "FAILED")

    def test_date_formatted_excel_serial_matches_date_assertion(self):
        content = date_serial_workbook(number_format="yyyy-mm-dd")
        report = self.verify(content, content, date_effect_for(content, value_type="date", value="2024-01-03"))
        self.assertEqual(report.validation_result, "VERIFIED")

    def test_time_format_does_not_masquerade_as_calendar_date(self):
        content = date_serial_workbook(number_format="h:mm")
        report = self.verify(content, content, date_effect_for(content, value_type="date", value="2024-01-03"))
        self.assertEqual(report.validation_result, "FAILED")

    def test_locale_builtin_date_number_format_is_typed_as_date(self):
        content = date_serial_workbook(builtin_num_format_id=27)
        report = self.verify(content, content, date_effect_for(content, value_type="date", value="2024-01-03"))
        self.assertEqual(report.validation_result, "VERIFIED")

    def test_date_formatted_serial_with_time_matches_datetime_assertion(self):
        content = date_serial_workbook(value="45294.5208333333", number_format="yyyy-mm-dd")
        report = self.verify(content, content, date_effect_for(
            content, value_type="datetime", value="2024-01-03T12:30:00"
        ))
        self.assertEqual(report.validation_result, "VERIFIED")

    def test_iso_date_and_datetime_cells_preserve_their_types(self):
        def with_iso_values(date_value, datetime_value):
            base = workbook("10")
            xml = (
            f'<worksheet xmlns="{MAIN}"><sheetData><row r="1">'
            f'<c r="A1" t="d"><v>{date_value}</v></c>'
            f'<c r="B1" t="d"><v>{datetime_value}</v></c>'
            '<c r="C1"><f>A1*2</f><v>20</v></c>'
            '</row></sheetData></worksheet>'
            ).encode()
            return replace_part(base, "xl/worksheets/sheet1.xml", xml)

        source = with_iso_values("2024-01-02", "2024-01-02T12:30:00")
        candidate = with_iso_values("2024-01-03", "2024-01-03T12:30:00")
        effect = seal_effect({
            "schema_version": "1", "parent_version_id": 17,
            "input_sha256": hashlib.sha256(source).hexdigest(),
            "target_scopes": [{"kind": "range", "sheet": "Data", "start": "A1", "end": "B1"}],
            "allowed_change_kinds": ["cell_value"],
            "expected_assertions": [
                {"kind": "cell_value", "sheet": "Data", "address": "A1", "value_type": "date", "value": "2024-01-03"},
                {"kind": "cell_value", "sheet": "Data", "address": "B1", "value_type": "datetime", "value": "2024-01-03T12:30:00"},
            ],
            "unknowns": [],
        })
        report = self.verify(source, candidate, effect)
        self.assertEqual(report.validation_result, "VERIFIED")
        actual = {item["target"]: item for item in report.actual_effects}
        self.assertEqual(actual["xlsx:Data!A1"]["before"], {"type": "date", "value": "2024-01-02"})
        self.assertEqual(actual["xlsx:Data!A1"]["after"], {"type": "date", "value": "2024-01-03"})
        self.assertEqual(actual["xlsx:Data!B1"]["after"], {"type": "datetime", "value": "2024-01-03T12:30:00"})

    def test_openpyxl_independently_reads_candidate_and_formula_text(self):
        source = workbook("10")
        candidate = workbook("15")
        report = self.verify(source, candidate, effect_for(source))
        self.assertEqual(report.validation_result, "VERIFIED")
        reopened = load_workbook(io.BytesIO(candidate), data_only=False, read_only=True)
        self.assertEqual(reopened.sheetnames, ["Data", "Notes"])
        self.assertEqual(reopened["Data"]["A1"].value, 15)
        self.assertEqual(reopened["Data"]["C1"].value, "=A1*2")
        self.assertEqual(reopened["Notes"]["A1"].value, "protected")

    def test_blank_cell_write_with_derived_dimension_and_default_style_is_valid(self):
        source = workbook("10")
        source = replace_part(
            source,
            "[Content_Types].xml",
            zip_part(source, "[Content_Types].xml").replace(
                b"</Types>",
                b'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
            ),
        )
        source = replace_part(
            source,
            "xl/_rels/workbook.xml.rels",
            zip_part(source, "xl/_rels/workbook.xml.rels").replace(
                b"</Relationships>",
                f'<Relationship Id="rId3" Type="{DOC_REL}/styles" Target="styles.xml"/></Relationships>'.encode(),
            ),
        )
        source = replace_part(
            source,
            "xl/styles.xml",
            f'<styleSheet xmlns="{MAIN}"><cellXfs count="1"><xf/></cellXfs></styleSheet>'.encode(),
        )
        source_sheet = zip_part(source, "xl/worksheets/sheet1.xml")
        source_sheet = source_sheet.replace(
            f'<worksheet xmlns="{MAIN}">'.encode(),
            f'<worksheet xmlns="{MAIN}"><dimension ref="A1:C1"/>'.encode(),
        )
        source = replace_part(source, "xl/worksheets/sheet1.xml", source_sheet)

        candidate_sheet = source_sheet.replace(
            b"</sheetData>",
            b'<row r="2"><c r="A2" s="0"><v>20</v></c></row></sheetData>',
        ).replace(b'ref="A1:C1"', b'ref="A1:C2"')
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", candidate_sheet)
        effect = effect_for(source, target="A2", expected=20)

        report = self.verify(source, candidate, effect)

        self.assertEqual(report.validation_result, "VERIFIED", report.actual_effects)
        self.assertEqual([item["change_kind"] for item in report.actual_effects], ["cell_value"])
        self.assertEqual(report.actual_effects[0]["target"], "xlsx:Data!A2")
        reopened = load_workbook(io.BytesIO(candidate), data_only=False, read_only=True)
        self.assertEqual(reopened["Data"]["A2"].value, 20)
        self.assertEqual(reopened["Data"]["C1"].value, "=A1*2")

    def test_explicit_default_style_attributes_are_semantically_unchanged(self):
        source = workbook("10")
        source = replace_part(
            source,
            "[Content_Types].xml",
            zip_part(source, "[Content_Types].xml").replace(
                b"</Types>",
                b'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
            ),
        )
        source = replace_part(
            source,
            "xl/_rels/workbook.xml.rels",
            zip_part(source, "xl/_rels/workbook.xml.rels").replace(
                b"</Relationships>",
                f'<Relationship Id="rId3" Type="{DOC_REL}/styles" Target="styles.xml"/></Relationships>'.encode(),
            ),
        )
        source = replace_part(
            source,
            "xl/styles.xml",
            f'<styleSheet xmlns="{MAIN}"><cellXfs count="1"><xf/></cellXfs></styleSheet>'.encode(),
        )
        source_sheet = zip_part(source, "xl/worksheets/sheet1.xml")
        source_sheet = source_sheet.replace(
            f'<worksheet xmlns="{MAIN}">'.encode(),
            f'<worksheet xmlns="{MAIN}"><dimension ref="A1:C1"/>'.encode(),
        )
        source = replace_part(source, "xl/worksheets/sheet1.xml", source_sheet)

        candidate_sheet = source_sheet.replace(
            b"</sheetData>",
            b'<row r="2"><c r="A2" s="0"><v>20</v></c></row></sheetData>',
        ).replace(b'ref="A1:C1"', b'ref="A1:C2"')
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", candidate_sheet)
        candidate_styles = (
            f'<styleSheet xmlns="{MAIN}"><cellXfs count="1">'
            '<xf borderId="0" fillId="0" fontId="0" pivotButton="0" '
            'quotePrefix="0" xfId="0"/></cellXfs></styleSheet>'
        ).encode()
        candidate = replace_part(candidate, "xl/styles.xml", candidate_styles)
        effect = effect_for(source, target="A2", expected=20)

        report = self.verify(source, candidate, effect)

        self.assertEqual(report.validation_result, "VERIFIED", report.actual_effects)
        self.assertEqual([item["change_kind"] for item in report.actual_effects], ["cell_value"])

    def test_meaningful_row_structure_change_remains_rejected(self):
        source = workbook("10")
        source_sheet = zip_part(source, "xl/worksheets/sheet1.xml")
        source_sheet = source_sheet.replace(
            b"<row r=\"1\">",
            b"<row r=\"1\" ht=\"15\" customHeight=\"1\">",
        )
        source = replace_part(source, "xl/worksheets/sheet1.xml", source_sheet)
        candidate_sheet = source_sheet.replace(
            b"ht=\"15\" customHeight=\"1\"",
            b"ht=\"30\" customHeight=\"1\"",
        ).replace(b"<v>10</v>", b"<v>15</v>")
        candidate = replace_part(source, "xl/worksheets/sheet1.xml", candidate_sheet)

        report = self.verify(source, candidate, effect_for(source))

        self.assertEqual(report.validation_result, "FAILED")
        self.assertIn("worksheet_structure", {item["change_kind"] for item in report.actual_effects})

    def test_uninterpreted_package_part_change_is_not_silently_ignored(self):
        source = workbook("10")
        theme_before = f'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:name>Before</a:name></a:theme>'.encode()
        theme_after = theme_before.replace(b"Before", b"After")
        source = replace_part(source, "xl/theme/theme1.xml", theme_before)
        candidate = replace_part(workbook("15"), "xl/theme/theme1.xml", theme_after)
        report = self.verify(source, candidate, effect_for(source))
        self.assertEqual(report.validation_result, "FAILED")
        self.assertTrue(any(item["change_kind"] == "unsupported_structure" for item in report.actual_effects))

    def test_candidate_worker_reports_observed_resource_usage(self):
        from office_verify import verify_candidate_output_with_metrics

        source = workbook("10")
        candidate = workbook("15")
        report, metrics = verify_candidate_output_with_metrics(
            source, candidate, "neutral.xlsx", MIME, effect_for(source)
        )

        self.assertEqual(report.validation_result, "VERIFIED")
        self.assertGreaterEqual(metrics["elapsed_seconds"], 0)
        self.assertTrue(metrics["rss_observed"])
        self.assertIsInstance(metrics["max_observed_rss_bytes"], int)
        self.assertGreater(metrics["max_observed_rss_bytes"], 0)
        self.assertTrue(metrics["worker_exited"])


if __name__ == "__main__":
    unittest.main()
