"""Independent local XLSX readback for the real Provider candidate."""

from __future__ import annotations

import hashlib
import argparse
import json
import zipfile
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "input_synthetic.xlsx"
DEFAULT_OUTPUT = ROOT / "output_candidate_01.xlsx"
DEFAULT_RESULT = ROOT / "independent_readback_01.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> dict:
    if not input_path.is_file() or not output_path.is_file():
        raise SystemExit("required_real_input_or_candidate_missing")
    for path in (input_path, output_path):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise SystemExit(f"xlsx_zip_integrity_failed:{path.name}")

    source = load_workbook(input_path, data_only=False)
    candidate = load_workbook(output_path, data_only=False)
    assert candidate.sheetnames == source.sheetnames == ["Inventory", "Notes"]
    assert candidate["Inventory"]["B2"].value == 15
    assert type(candidate["Inventory"]["B2"].value) is int
    assert candidate["Inventory"]["C2"].value == "KEEP"
    assert candidate["Inventory"]["D2"].value == "=B2*2"
    assert candidate["Inventory"]["A2"].value == "ITEM-A"
    assert candidate["Inventory"]["A3"].value == "ITEM-B"
    assert candidate["Inventory"]["B3"].value == 20
    assert candidate["Inventory"]["C3"].value == "KEEP-B"
    assert candidate["Inventory"]["D3"].value == "=B3*2"
    assert candidate["Notes"]["A2"].value == "Source"
    assert candidate["Notes"]["B2"].value == "Synthetic CC-01"
    assert candidate["Notes"]["A3"].value == "Status"
    assert candidate["Notes"]["B3"].value == "Original"

    # Compare every populated cell's value/type and style outside the one
    # explicitly requested target. Formula calculation is not tested.
    changed_cells = []
    for sheet_name in source.sheetnames:
        before = source[sheet_name]
        after = candidate[sheet_name]
        assert before.max_row == after.max_row
        assert before.max_column == after.max_column
        for row in range(1, max(before.max_row, after.max_row) + 1):
            for column in range(1, max(before.max_column, after.max_column) + 1):
                old = before.cell(row, column)
                new = after.cell(row, column)
                if (old.value, old.data_type, old.number_format, old.style_id) != (
                    new.value,
                    new.data_type,
                    new.number_format,
                    new.style_id,
                ):
                    address = old.coordinate
                    changed_cells.append(f"{sheet_name}!{address}")
                    assert (sheet_name, address) == ("Inventory", "B2")

    result = {
        "verification": "PASS",
        "input_bytes": input_path.stat().st_size,
        "input_sha256": digest(input_path),
        "output_bytes": output_path.stat().st_size,
        "output_sha256": digest(output_path),
        "sheetnames": candidate.sheetnames,
        "assertions": {
            "Inventory!B2_numeric_15": True,
            "Inventory!C2_KEEP": True,
            "Inventory!D2_formula_text": True,
            "Inventory_other_rows_unchanged": True,
            "Notes_values_unchanged": True,
            "no_non_target_value_type_or_style_changes": True,
            "both_zip_containers_valid": True,
        },
        "changed_cells": changed_cells,
        "formula_recalculation": "NOT TESTED",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    result = verify(args.input, args.output)
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
