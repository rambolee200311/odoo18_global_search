"""Independent readback for the CC-05 synthetic two-stage HVR artifacts."""

import hashlib
import zipfile
from pathlib import Path
from openpyxl import load_workbook


ROOT = Path(__file__).parent / "hvr_artifacts_20261110"
EXPECTED = {
    "hvr_v1_input.xlsx": "210c33c9c5490b7930ce8806e889d3830a9237bdcaa261f7ab1e6f5ba352282b",
    "hvr_v2_candidate.xlsx": "2fd550748e270db754943a66e7445955abd2db047d2bef1e5624c96ff5806928",
    "hvr_v3_candidate.xlsx": "c7bc3c001ced2374cb94a278461ec8169921d0f8b31b3e2679c9a2b6f7e7a8b6",
}
ROWS = [
    ("CB05 Contact 0 c8432cb6cdf64dce84d972ed9b419190", "+12025550000", "cb05-c8432cb6cdf64dce84d972ed9b419190-0@example.invalid"),
    ("CB05 Contact 1 c8432cb6cdf64dce84d972ed9b419190", "+12025550001", "cb05-c8432cb6cdf64dce84d972ed9b419190-1@example.invalid"),
    ("CB05 Contact 2 c8432cb6cdf64dce84d972ed9b419190", "+12025550002", "cb05-c8432cb6cdf64dce84d972ed9b419190-2@example.invalid"),
]
ADDRESSES = [
    "100 Synthetic Street, Test City 0, 10000",
    "101 Synthetic Street, Unit 2, Test City 1, 10001",
    "102 Synthetic Street, Test City 2, 10002",
]


def read(name):
    path = ROOT / name
    data = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, f"ZIP integrity failed: {name}"
    workbook = load_workbook(path, data_only=False)
    assert workbook.sheetnames == ["Contacts"], (name, workbook.sheetnames)
    return path, data, workbook


v1_path, v1_data, v1 = read("hvr_v1_input.xlsx")
v2_path, v2_data, v2 = read("hvr_v2_candidate.xlsx")
v3_path, v3_data, v3 = read("hvr_v3_candidate.xlsx")
assert hashlib.sha256(v1_data).hexdigest() == EXPECTED[v1_path.name]
assert hashlib.sha256(v2_data).hexdigest() == EXPECTED[v2_path.name]
assert hashlib.sha256(v3_data).hexdigest() == EXPECTED[v3_path.name]
assert [v1["Contacts"].cell(1, column).value for column in range(1, 4)] == ["名称", "电话", "邮件"]
assert [v2["Contacts"].cell(1, column).value for column in range(1, 4)] == ["名称", "电话", "邮件"]
for row_number, expected in enumerate(ROWS, start=2):
    assert tuple(v2["Contacts"].cell(row_number, column).value for column in range(1, 4)) == expected
    assert tuple(v3["Contacts"].cell(row_number, column).value for column in range(1, 4)) == expected
assert v3["Contacts"]["D1"].value == "地址"
assert [v3["Contacts"][f"D{row}"].value for row in range(2, 5)] == ADDRESSES

for name, path, data in (
    ("V1", v1_path, v1_data),
    ("V2", v2_path, v2_data),
    ("V3", v3_path, v3_data),
):
    print(f"{name}: PASS; path={path}; bytes={len(data)}; sha256={hashlib.sha256(data).hexdigest()}; ZIP/openpyxl=PASS")
print("V1 headers: PASS")
print("V2 contact values A2:C4: PASS")
print("V3 A2:C4 preserved from V2: PASS")
print("V3 D1:D4 addresses: PASS")
v1.close()
v2.close()
v3.close()
