"""Independent XLSX readback and allowed-effect diff checks for Candidate B TV."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "independent_verification.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell_value(value):
    if isinstance(value, (date, datetime)):
        return {"iso": value.isoformat(), "type": type(value).__name__}
    if isinstance(value, bool):
        return {"value": value, "type": "bool"}
    if value is None:
        return {"value": None, "type": "null"}
    return {"value": value, "type": type(value).__name__}


def color_signature(color):
    if color is None:
        return None
    return (color.type, color.rgb, color.indexed, color.theme, color.tint, color.auto)


def style_signature(cell):
    f = cell.font
    fill = cell.fill
    b = cell.border
    a = cell.alignment
    p = cell.protection
    return (
        cell.number_format,
        f.name, f.sz, f.bold, f.italic, f.underline, f.strike, color_signature(f.color),
        fill.fill_type, color_signature(fill.fgColor), color_signature(fill.bgColor), fill.patternType,
        tuple((side, getattr(b, side).style, color_signature(getattr(b, side).color))
              for side in ("left", "right", "top", "bottom", "diagonal", "vertical", "horizontal")),
        a.horizontal, a.vertical, a.text_rotation, a.wrap_text, a.shrink_to_fit, a.indent,
        p.locked, p.hidden,
    )


def sheet_structural_signature(ws):
    return {
        "title": ws.title,
        "sheet_state": ws.sheet_state,
        "max_row": ws.max_row,
        "max_column": ws.max_column,
        "freeze_panes": str(ws.freeze_panes) if ws.freeze_panes else None,
        "merged_ranges": sorted(str(x) for x in ws.merged_cells.ranges),
        "row_dimensions": sorted((index, dim.height, dim.hidden, dim.outlineLevel)
                                for index, dim in ws.row_dimensions.items()),
        "column_dimensions": sorted((key, dim.width, dim.hidden, dim.outlineLevel)
                                   for key, dim in ws.column_dimensions.items()),
        "data_validations": sorted((str(x.sqref), x.type, x.operator, x.formula1, x.formula2, x.allow_blank)
                                   for x in ws.data_validations.dataValidation),
        "conditional_formatting": sorted((str(key), repr(value))
                                         for key, value in ws.conditional_formatting._cf_rules.items()),
        "auto_filter": ws.auto_filter.ref,
        "tables": sorted((name, table.ref) for name, table in ws.tables.items()),
    }


def workbook_snapshot(path: Path):
    if not path.exists():
        raise FileNotFoundError(path.name)
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise AssertionError(f"ZIP CRC failure: {bad}")
    wb = load_workbook(path, data_only=False)
    snap = {"sheetnames": list(wb.sheetnames), "defined_names": {}, "sheets": {}}
    for name, defined in wb.defined_names.items():
        snap["defined_names"][name] = defined.attr_text
    for ws in wb.worksheets:
        cells = {}
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cells[cell.coordinate] = {
                    "value": cell_value(cell.value),
                    "data_type": cell.data_type,
                    "style": style_signature(cell),
                }
        snap["sheets"][ws.title] = {"structure": sheet_structural_signature(ws), "cells": cells}
    wb.close()
    return snap


def find_differences(before, after):
    diffs = []
    if before["sheetnames"] != after["sheetnames"]:
        diffs.append({"kind": "sheetnames", "before": before["sheetnames"], "after": after["sheetnames"]})
    if before["defined_names"] != after["defined_names"]:
        diffs.append({"kind": "defined_names", "before": before["defined_names"], "after": after["defined_names"]})
    for sheet in sorted(set(before["sheets"]) | set(after["sheets"])):
        if sheet not in before["sheets"] or sheet not in after["sheets"]:
            diffs.append({"kind": "sheet_presence", "sheet": sheet})
            continue
        bws, aws = before["sheets"][sheet], after["sheets"][sheet]
        if bws["structure"] != aws["structure"]:
            diffs.append({"kind": "sheet_structure", "sheet": sheet,
                          "before": bws["structure"], "after": aws["structure"]})
        for coord in sorted(set(bws["cells"]) | set(aws["cells"])):
            b = bws["cells"].get(coord)
            a = aws["cells"].get(coord)
            if b != a:
                diffs.append({"kind": "cell", "sheet": sheet, "coordinate": coord,
                              "before": _jsonable(b), "after": _jsonable(a)})
    return diffs


def _jsonable(value):
    if isinstance(value, tuple):
        return [_jsonable(x) for x in value]
    if isinstance(value, list):
        return [_jsonable(x) for x in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def verify_delta(case_id, before_path, after_path):
    before = workbook_snapshot(ROOT / before_path)
    after = workbook_snapshot(ROOT / after_path)
    diffs = find_differences(before, after)
    allowed = set()
    if case_id == "phase1b":
        allowed = {("Inventory", "B2", "value"), ("Inventory", "C3", "value")}
    elif case_id == "phase1c_v2":
        allowed = {("Inventory", "B2", "value")}
    elif case_id == "phase1c_v3":
        allowed = {("Inventory", "C3", "value")} | {
            ("Inventory", f"{col}3", "style") for col in "ABCD"
        }
    elif case_id == "phase1c_v4":
        allowed = set()  # the supplied V1 is already in ascending order
    elif case_id == "phase1d":
        allowed = {("Inventory", "B2", "value")}
    unexpected = []
    for diff in diffs:
        if diff["kind"] != "cell":
            unexpected.append(diff)
            continue
        old, new = diff.get("before") or {}, diff.get("after") or {}
        coord = diff["coordinate"]
        if (diff["sheet"], coord, "value") in allowed:
            style_allowed = (diff["sheet"], coord, "style") in allowed
            if (old.get("data_type") != new.get("data_type")
                    or (old.get("style") != new.get("style") and not style_allowed)):
                unexpected.append(diff)
        elif (diff["sheet"], coord, "style") in allowed:
            if old.get("value") != new.get("value") or old.get("data_type") != new.get("data_type"):
                unexpected.append(diff)
        else:
            unexpected.append(diff)
    wb = load_workbook(ROOT / after_path, data_only=False)
    ws = wb["Inventory"]
    checks = {"zip_integrity": "PASS", "sheetnames": wb.sheetnames}
    if case_id == "phase1b":
        checks.update({
            "Inventory_B2": ws["B2"].value == 15 and ws["B2"].data_type == "n",
            "Inventory_C3": ws["C3"].value == 9.5 and ws["C3"].data_type == "n",
            "formulas_preserved": ws["D2"].value == "=B2*C2" and ws["D3"].value == "=B3*C3",
            "ITEM_A_B3": ws["B3"].value == 20,
            "ITEM_B_C2": ws["C2"].value == 8.25,
            "false_preserved": ws["G2"].value is False and ws["G2"].data_type == "b",
            "zero_preserved": ws["F2"].value == 0 and ws["F2"].data_type == "n",
            "date_preserved": ws["E2"].value.date() == date(2026, 1, 5),
            "blank_preserved": ws["H2"].value is None,
            "notes_preserved": wb["Notes"]["B2"].value == "Synthetic TV" and wb["Notes"]["B3"].value == "Original",
        })
    elif case_id == "phase1c_v2":
        checks.update({
            "ITEM_A_quantity_15": ws["B2"].value == 15,
            "ITEM_B_C_unchanged": ws["B3"].value == 20 and ws["C3"].value == 8,
            "ITEM_C_unchanged": ws["A4"].value == "ITEM-C" and ws["B4"].value == 30 and ws["C4"].value == 4,
            "formulas_preserved": [ws.cell(r, 4).value for r in range(2, 5)] == ["=B2*C2", "=B3*C3", "=B4*C4"],
            "notes_preserved": wb["Notes"]["B3"].value == "V1 baseline",
        })
    elif case_id == "phase1c_v3":
        checks.update({
            "ITEM_A_quantity_retained": ws["B2"].value == 15,
            "ITEM_B_price_9_5": ws["C3"].value == 9.5,
            "ITEM_B_identity_retained": ws["A3"].value == "ITEM-B",
            "ITEM_C_unchanged": ws["A4"].value == "ITEM-C" and ws["B4"].value == 30 and ws["C4"].value == 4,
            "formulas_preserved": [ws.cell(r, 4).value for r in range(2, 5)] == ["=B2*C2", "=B3*C3", "=B4*C4"],
            "ITEM_B_row_light_yellow": all(_light_yellow(ws[f"{col}3"].fill) for col in "ABCD"),
            "Notes_unchanged": wb["Notes"]["B2"].value == "Source" and wb["Notes"]["B3"].value == "V1 baseline",
        })
    elif case_id == "phase1c_v4":
        order = [ws.cell(r, 1).value for r in range(2, 5)]
        checks.update({
            "product_order_ascending": order == sorted(order),
            "sort_exercised_row_reordering": order != ["ITEM-A", "ITEM-B", "ITEM-C"],
            "ITEM_A_quantity_retained": _value_by_key(ws, "ITEM-A", 2) == 15,
            "ITEM_B_price_retained": _value_by_key(ws, "ITEM-B", 3) == 9.5,
            "ITEM_B_light_yellow_follows_record": _row_light_yellow_by_key(ws, "ITEM-B"),
            "formulas_match_current_rows": all(ws.cell(r, 4).value == f"=B{r}*C{r}" for r in range(2, 5)),
            "Notes_unchanged": wb["Notes"]["B2"].value == "Source" and wb["Notes"]["B3"].value == "V1 baseline",
        })
    elif case_id == "phase1d":
        checks.update({
            "target_B2_11": ws["B2"].value == 11 and ws["B2"].data_type == "n",
            "formulas_text_and_references": [ws.cell(r, 4).value for r in range(2, 5)] == ["=B2*C2", "=B3*C3", "=B4*C4"],
            "freeze_panes": ws.freeze_panes == "A2",
            "merge_preserved": "A6:B6" in {str(x) for x in ws.merged_cells.ranges},
            "hidden_row_and_column": ws.row_dimensions[5].hidden and ws.column_dimensions["H"].hidden,
            "row_height_and_column_width": ws.row_dimensions[2].height == 22 and ws.column_dimensions["A"].width == 18,
            "date_and_format": ws["E2"].value.date() == date(2026, 2, 1) and ws["E2"].number_format == "yyyy-mm-dd",
            "data_validation": any(str(x.sqref) == "B2:B4" for x in ws.data_validations.dataValidation),
            "conditional_formatting": len(ws.conditional_formatting) == 1,
            "defined_name": wb.defined_names["InventoryAmounts"].attr_text == "'Inventory'!$D$2:$D$4",
            "boolean_false": ws["F2"].value is False and ws["F2"].data_type == "b",
            "numeric_zero": ws["G2"].value == 0 and ws["G2"].data_type == "n",
            "notes_preserved": wb["Notes"]["B2"].value == "Synthetic structure sentinel",
        })
    wb.close()
    return {
        "case": case_id,
        "input": {"file": before_path, "sha256": digest(ROOT / before_path)},
        "output": {"file": after_path, "bytes": (ROOT / after_path).stat().st_size,
                   "sha256": digest(ROOT / after_path)},
        "assertions": checks,
        "all_value_and_structure_differences": diffs,
        "unexpected_differences": unexpected,
        "status": "PASS" if all(checks.values()) and not unexpected else "FAIL",
    }


def _light_yellow(fill):
    color = fill.fgColor
    if fill.fill_type != "solid" or color.type != "rgb" or not color.rgb:
        return False
    rgb = color.rgb[-6:].upper()
    try:
        red, green, blue = (int(rgb[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    return red >= 240 and green >= 225 and blue >= 150 and red >= green >= blue


def _value_by_key(ws, key, column):
    for row in range(2, ws.max_row + 1):
        if ws.cell(row, 1).value == key:
            return ws.cell(row, column).value
    return None


def _row_light_yellow_by_key(ws, key):
    for row in range(2, ws.max_row + 1):
        if ws.cell(row, 1).value == key:
            return all(_light_yellow(ws.cell(row, col).fill) for col in range(1, 5))
    return False


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit("usage: verify_candidates.py CASE INPUT.xlsx OUTPUT.xlsx [CASE INPUT.xlsx OUTPUT.xlsx ...]")
    if len(args) % 3:
        raise SystemExit("arguments must be CASE INPUT.xlsx OUTPUT.xlsx groups")
    results = []
    for i in range(0, len(args), 3):
        results.append(verify_delta(args[i], args[i + 1], args[i + 2]))
    overall = {
        "cases": results,
        "overall": "PASS" if all(x["status"] == "PASS" for x in results) else "FAIL",
        "formula_scope": "formula text and references verified; no calculation engine/recalculation tested",
    }
    OUT.write_text(json.dumps(overall, indent=2, sort_keys=True) + "\n")
    print(json.dumps(overall, indent=2, sort_keys=True))
    if overall["overall"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
