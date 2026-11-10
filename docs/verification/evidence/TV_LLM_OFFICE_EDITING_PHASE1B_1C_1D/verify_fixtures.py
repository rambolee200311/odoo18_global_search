"""Independent read-only verification of synthetic Phase 1B/1C/1D fixtures."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_zip_valid(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, path.name


def verify_phase1b() -> dict:
    path = ROOT / "phase1b_input.xlsx"
    assert_zip_valid(path)
    book = load_workbook(path, data_only=False)
    sheet = book["Inventory"]
    assert book.sheetnames == ["Inventory", "Notes"]
    assert sheet["A2"].value == "ITEM-A"
    assert sheet["B2"].value == 10
    assert sheet["C2"].value == 5
    assert sheet["D2"].value == "=B2*C2"
    assert sheet["B3"].value == 20
    assert sheet["D3"].value == "=B3*C3"
    assert sheet["E2"].value.date() == date(2026, 1, 5)
    assert sheet["F2"].value == 0 and sheet["F2"].data_type == "n"
    assert sheet["G2"].value is False and sheet["G2"].data_type == "b"
    assert sheet["H2"].value is None
    assert sheet["C2"].number_format == "0.00"
    assert sheet["E2"].number_format == "yyyy-mm-dd"
    assert sheet["A1"].font.bold is True
    assert sheet["A1"].fill.fgColor.rgb.endswith("1F4E78")
    assert sheet["A1"].border.left.style == "thin"
    assert book["Notes"]["B2"].value == "Synthetic TV"
    book.close()
    return {"file": path.name, "sha256": digest(path), "zip": "PASS", "fixture_checks": "PASS"}


def verify_phase1c() -> dict:
    path = ROOT / "phase1c_v1.xlsx"
    assert_zip_valid(path)
    book = load_workbook(path, data_only=False)
    sheet = book["Inventory"]
    assert book.sheetnames == ["Inventory", "Notes"]
    assert [sheet.cell(row, 1).value for row in range(2, 5)] == ["ITEM-A", "ITEM-B", "ITEM-C"]
    assert [sheet.cell(row, 2).value for row in range(2, 5)] == [10, 20, 30]
    assert [sheet.cell(row, 3).value for row in range(2, 5)] == [5, 8, 4]
    assert [sheet.cell(row, 4).value for row in range(2, 5)] == ["=B2*C2", "=B3*C3", "=B4*C4"]
    assert book["Notes"]["B3"].value == "V1 baseline"
    book.close()
    return {"file": path.name, "sha256": digest(path), "zip": "PASS", "fixture_checks": "PASS"}


def verify_phase1d() -> dict:
    path = ROOT / "phase1d_input.xlsx"
    assert_zip_valid(path)
    book = load_workbook(path, data_only=False)
    sheet = book["Inventory"]
    assert book.sheetnames == ["Inventory", "Notes"]
    assert sheet.freeze_panes == "A2"
    assert "A6:B6" in {str(value) for value in sheet.merged_cells.ranges}
    assert sheet["A6"].value == "Structure sentinel — preserve merge"
    assert sheet.row_dimensions[5].hidden is True
    assert sheet.column_dimensions["H"].hidden is True
    assert sheet.row_dimensions[2].height == 22
    assert sheet.column_dimensions["A"].width == 18
    assert sheet["E2"].value.date() == date(2026, 2, 1)
    assert sheet["E2"].number_format == "yyyy-mm-dd"
    assert [sheet.cell(row, 4).value for row in range(2, 5)] == ["=B2*C2", "=B3*C3", "=B4*C4"]
    assert len(sheet.data_validations.dataValidation) == 1
    validation = sheet.data_validations.dataValidation[0]
    assert str(validation.sqref) == "B2:B4"
    assert len(sheet.conditional_formatting) == 1
    assert book.defined_names["InventoryAmounts"].attr_text == "'Inventory'!$D$2:$D$4"
    assert sheet["F2"].value is False and sheet["F2"].data_type == "b"
    assert sheet["G2"].value == 0 and sheet["G2"].data_type == "n"
    assert sheet["A1"].font.bold is True
    assert sheet["A1"].border.left.style == "thin"
    assert book["Notes"]["B2"].value == "Synthetic structure sentinel"
    book.close()
    return {"file": path.name, "sha256": digest(path), "zip": "PASS", "fixture_checks": "PASS"}


def verify_manifests(results: list[dict]) -> None:
    for result in results:
        path = ROOT / result["file"]
        manifest_path = ROOT / f"{path.stem}_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["sha256"] == result["sha256"]
        assert manifest["size_bytes"] == path.stat().st_size
        assert manifest["sheetnames"] == ["Inventory", "Notes"]


def main() -> None:
    results = [verify_phase1b(), verify_phase1c(), verify_phase1d()]
    verify_manifests(results)
    result = {
        "offline_fixture_verification": "PASS",
        "provider_calls": 0,
        "candidate_edits": 0,
        "results": results,
        "formula_semantics": "formula text only; no recalculation performed",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
