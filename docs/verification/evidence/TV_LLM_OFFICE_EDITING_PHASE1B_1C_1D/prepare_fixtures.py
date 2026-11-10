"""Create the authorized local-only synthetic XLSX fixtures for TV preparation."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName


ROOT = Path(__file__).resolve().parent
HEADER_FILL = PatternFill(fill_type="solid", fgColor="1F4E78")
HEADER_FONT = Font(name="Arial", size=11, bold=True, color="FFFFFF")
THIN = Side(style="thin", color="808080")
CELL_BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def style_header(sheet) -> None:
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = CELL_BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    sheet.row_dimensions[1].height = 24


def set_inventory_formats(sheet, rows: range) -> None:
    for row in rows:
        sheet.cell(row, 2).number_format = "0"
        sheet.cell(row, 3).number_format = "0.00"
        sheet.cell(row, 4).number_format = "0.00"
        sheet.cell(row, 5).number_format = "yyyy-mm-dd"
        for column in range(1, sheet.max_column + 1):
            sheet.cell(row, column).border = CELL_BORDER
            sheet.cell(row, column).alignment = Alignment(vertical="center")


def build_phase1b() -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "Inventory"
    sheet.append(["Product", "Quantity", "Unit Price", "Amount", "Date", "Zero", "Enabled", "Blank"])
    sheet.append(["ITEM-A", 10, 5.0, "=B2*C2", date(2026, 1, 5), 0, False, None])
    sheet.append(["ITEM-B", 20, 8.0, "=B3*C3", date(2026, 1, 6), 0.0, False, None])
    style_header(sheet)
    set_inventory_formats(sheet, range(2, 4))
    sheet.column_dimensions["A"].width = 18
    for column in "BCDEFGH":
        sheet.column_dimensions[column].width = 14
    sheet.freeze_panes = "A2"

    notes = book.create_sheet("Notes")
    notes.append(["Key", "Value"])
    notes.append(["Source", "Synthetic TV"])
    notes.append(["Status", "Original"])
    style_header(notes)
    notes.column_dimensions["A"].width = 16
    notes.column_dimensions["B"].width = 24
    output = ROOT / "phase1b_input.xlsx"
    book.save(output)
    book.close()
    return output


def build_phase1c() -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "Inventory"
    sheet.append(["Product", "Quantity", "Unit Price", "Amount"])
    sheet.append(["ITEM-A", 10, 5, "=B2*C2"])
    sheet.append(["ITEM-B", 20, 8, "=B3*C3"])
    sheet.append(["ITEM-C", 30, 4, "=B4*C4"])
    style_header(sheet)
    set_inventory_formats(sheet, range(2, 5))
    sheet.freeze_panes = "A2"
    sheet.column_dimensions["A"].width = 18
    for column in "BCD":
        sheet.column_dimensions[column].width = 14

    notes = book.create_sheet("Notes")
    notes.append(["Key", "Value"])
    notes.append(["Source", "Synthetic TV"])
    notes.append(["Status", "V1 baseline"])
    style_header(notes)
    notes.column_dimensions["A"].width = 16
    notes.column_dimensions["B"].width = 24
    output = ROOT / "phase1c_v1.xlsx"
    book.save(output)
    book.close()
    return output


def build_phase1d() -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "Inventory"
    sheet.append(["Product", "Quantity", "Unit Price", "Amount", "Date", "Enabled", "Zero", "Blank"])
    sheet.append(["ITEM-A", 10, 5.0, "=B2*C2", date(2026, 2, 1), False, 0, None])
    sheet.append(["ITEM-B", 20, 8.0, "=B3*C3", date(2026, 2, 2), False, 0.0, None])
    sheet.append(["ITEM-C", 30, 4.0, "=B4*C4", date(2026, 2, 3), True, 0, None])
    style_header(sheet)
    set_inventory_formats(sheet, range(2, 5))
    sheet.freeze_panes = "A2"
    sheet.row_dimensions[2].height = 22
    sheet.row_dimensions[5].hidden = True
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 13
    sheet.column_dimensions["C"].width = 15
    sheet.column_dimensions["D"].width = 15
    sheet.column_dimensions["E"].width = 16
    sheet.column_dimensions["F"].width = 13
    sheet.column_dimensions["G"].width = 12
    sheet.column_dimensions["H"].width = 12
    sheet.column_dimensions["H"].hidden = True
    sheet.merge_cells("A6:B6")
    sheet["A6"] = "Structure sentinel — preserve merge"
    sheet["A6"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    sheet["A6"].font = Font(italic=True, color="1F1F1F")
    sheet["A6"].border = CELL_BORDER

    validation = DataValidation(type="whole", operator="between", formula1="0", formula2="999")
    validation.error = "Quantity must be a whole number between 0 and 999."
    validation.errorTitle = "Invalid quantity"
    sheet.add_data_validation(validation)
    validation.add("B2:B4")
    sheet.conditional_formatting.add(
        "C2:C4",
        CellIsRule(operator="lessThan", formula=["0"], fill=PatternFill(fill_type="solid", fgColor="FFC7CE")),
    )
    book.defined_names.add(DefinedName("InventoryAmounts", attr_text="'Inventory'!$D$2:$D$4"))

    notes = book.create_sheet("Notes")
    notes.append(["Key", "Value"])
    notes.append(["Source", "Synthetic structure sentinel"])
    notes.append(["Status", "Original"])
    style_header(notes)
    notes["B2"].alignment = Alignment(wrap_text=True)
    notes.column_dimensions["A"].width = 16
    notes.column_dimensions["B"].width = 32
    output = ROOT / "phase1d_input.xlsx"
    book.save(output)
    book.close()
    return output


def cell_value(value):
    if isinstance(value, (date,)):
        return value.isoformat()
    return value


def workbook_manifest(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise AssertionError(f"corrupt xlsx member: {bad_member}")
        zip_members = sorted(archive.namelist())
    book = load_workbook(path, data_only=False)
    sheets = {}
    for sheet in book.worksheets:
        cells = {}
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    color = cell.font.color
                    fill_color = cell.fill.fgColor
                    cells[cell.coordinate] = {
                        "value": cell_value(cell.value),
                        "python_type": type(cell.value).__name__,
                        "data_type": cell.data_type,
                        "number_format": cell.number_format,
                        "style_id": cell.style_id,
                        "font": {
                            "name": cell.font.name,
                            "size": cell.font.sz,
                            "bold": cell.font.bold,
                            "italic": cell.font.italic,
                            "color_type": color.type if color else None,
                            "color": color.rgb if color and color.type == "rgb" else None,
                        },
                        "fill": {
                            "type": cell.fill.fill_type,
                            "color_type": fill_color.type,
                            "color": fill_color.rgb if fill_color.type == "rgb" else None,
                        },
                        "border_sides": {
                            side: getattr(cell.border, side).style
                            for side in ("left", "right", "top", "bottom")
                        },
                        "alignment": {
                            "horizontal": cell.alignment.horizontal,
                            "vertical": cell.alignment.vertical,
                            "wrap_text": cell.alignment.wrap_text,
                        },
                    }
        sheets[sheet.title] = {
            "state": sheet.sheet_state,
            "max_row": sheet.max_row,
            "max_column": sheet.max_column,
            "freeze_panes": (
                sheet.freeze_panes.coordinate
                if hasattr(sheet.freeze_panes, "coordinate")
                else sheet.freeze_panes
            ),
            "merged_ranges": sorted(str(value) for value in sheet.merged_cells.ranges),
            "row_dimensions": {
                str(index): {"height": dim.height, "hidden": dim.hidden}
                for index, dim in sheet.row_dimensions.items()
                if dim.height is not None or dim.hidden
            },
            "column_dimensions": {
                key: {"width": dim.width, "hidden": dim.hidden}
                for key, dim in sheet.column_dimensions.items()
                if dim.width is not None or dim.hidden
            },
            "data_validations": [
                {
                    "type": item.type,
                    "operator": item.operator,
                    "formula1": item.formula1,
                    "formula2": item.formula2,
                    "sqref": str(item.sqref),
                }
                for item in sheet.data_validations.dataValidation
            ],
            "conditional_formatting": [str(item) for item in sheet.conditional_formatting],
            "cells": cells,
        }
    manifest = {
        "file": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "zip_members": zip_members,
        "sheetnames": book.sheetnames,
        "defined_names": {
            name: definition.attr_text
            for name, definition in book.defined_names.items()
        },
        "sheets": sheets,
    }
    book.close()
    return manifest


def run_offline_assertions(manifests: dict[str, dict]) -> dict:
    b = load_workbook(ROOT / "phase1b_input.xlsx", data_only=False)
    assert b.sheetnames == ["Inventory", "Notes"]
    assert b["Inventory"]["D2"].value == "=B2*C2"
    assert b["Inventory"]["D3"].value == "=B3*C3"
    assert type(b["Inventory"]["F2"].value) is int and b["Inventory"]["F2"].value == 0
    assert type(b["Inventory"]["F3"].value) in (int, float) and b["Inventory"]["F3"].value == 0
    assert b["Inventory"]["F3"].data_type == "n"
    assert type(b["Inventory"]["G2"].value) is bool and b["Inventory"]["G2"].value is False
    assert b["Inventory"]["H2"].value is None
    assert b["Inventory"]["C2"].number_format == "0.00"
    assert b["Inventory"]["E2"].number_format == "yyyy-mm-dd"
    assert b["Inventory"]["A1"].font.bold is True
    assert b["Inventory"]["A1"].fill.fgColor.rgb.endswith("1F4E78")
    assert b["Inventory"]["A1"].border.left.style == "thin"
    b.close()

    c = load_workbook(ROOT / "phase1c_v1.xlsx", data_only=False)
    assert [c["Inventory"].cell(row, 1).value for row in range(2, 5)] == ["ITEM-A", "ITEM-B", "ITEM-C"]
    assert [c["Inventory"].cell(row, 4).value for row in range(2, 5)] == ["=B2*C2", "=B3*C3", "=B4*C4"]
    c.close()

    d = load_workbook(ROOT / "phase1d_input.xlsx", data_only=False)
    s = d["Inventory"]
    assert d.sheetnames == ["Inventory", "Notes"]
    assert s.freeze_panes == "A2"
    assert "A6:B6" in {str(value) for value in s.merged_cells.ranges}
    assert s.row_dimensions[5].hidden is True
    assert s.column_dimensions["H"].hidden is True
    assert s["E2"].is_date is True
    assert s["D2"].value == "=B2*C2"
    assert len(s.data_validations.dataValidation) == 1
    assert len(s.conditional_formatting) == 1
    assert d.defined_names["InventoryAmounts"].attr_text == "'Inventory'!$D$2:$D$4"
    assert type(s["F2"].value) is bool and s["F2"].value is False
    assert type(s["G2"].value) is int and s["G2"].value == 0
    d.close()

    for name, manifest in manifests.items():
        assert manifest["size_bytes"] > 0
        assert manifest["sha256"]
        assert len(manifest["sheetnames"]) == 2
    return {
        "phase1b_fixture": "PASS",
        "phase1c_v1_fixture": "PASS",
        "phase1d_structure_fixture": "PASS",
        "zip_integrity_all": "PASS",
        "scope": "offline fixture checks only; no Provider calls or candidate edits",
    }


def main() -> None:
    expected_paths = [
        ROOT / "phase1b_input.xlsx",
        ROOT / "phase1c_v1.xlsx",
        ROOT / "phase1d_input.xlsx",
    ]
    if "--manifest-only" in sys.argv:
        if not all(path.exists() for path in expected_paths):
            raise FileNotFoundError("manifest-only mode requires all three existing fixtures")
        paths = expected_paths
    else:
        if any(path.exists() for path in expected_paths):
            raise FileExistsError("refusing to overwrite an existing synthetic fixture")
        paths = [build_phase1b(), build_phase1c(), build_phase1d()]
    manifests = {path.name: workbook_manifest(path) for path in paths}
    for filename, manifest in manifests.items():
        (ROOT / f"{Path(filename).stem}_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, default=str)
        )
    result = run_offline_assertions(manifests)
    (ROOT / "offline_preparation_result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({
        "result": result,
        "files": {
            filename: {
                "sha256": manifest["sha256"],
                "size_bytes": manifest["size_bytes"],
                "sheetnames": manifest["sheetnames"],
            }
            for filename, manifest in manifests.items()
        },
    }, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
