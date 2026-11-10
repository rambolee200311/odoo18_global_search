from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).parent
FILES = {
    "V2_current": ROOT / "hvr-rerun-v2-current-20261110.xlsx",
    "V3_candidate": ROOT / "hvr-rerun-v3-candidate-20261110.xlsx",
}


for label, path in FILES.items():
    payload = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        bad_member = archive.testzip()
    workbook = load_workbook(io.BytesIO(payload), data_only=False)
    sheet = workbook["Inventory"]
    print(
        label,
        "sha256=" + hashlib.sha256(payload).hexdigest(),
        "zip_bad_member=" + repr(bad_member),
        "sheets=" + repr(workbook.sheetnames),
        "A1=" + repr(sheet["A1"].value),
        "A2=" + repr(sheet["A2"].value),
        "C1=" + repr(sheet["C1"].value),
        "dimension=" + sheet.calculate_dimension(),
        "A2_style_id=" + repr(sheet["A2"].style_id),
    )
