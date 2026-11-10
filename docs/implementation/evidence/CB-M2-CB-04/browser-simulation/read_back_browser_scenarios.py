"""Read back synthetic CB-04 browser candidates through Odoo ORM.

Run with: ./venv/bin/python ./odoo-bin shell -c odoo.conf -d odoo18ce --no-http
The script does not write or commit database records.
"""
from base64 import b64decode
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile

from openpyxl import load_workbook

env = env(user=2)
session = env["office.mapping.session"].browse(11628).exists()
assert session, "Synthetic browser simulation Session not found"
print("SESSION", session.id, "CURRENT", session.current_version_id.id,
      "LAST_VALID", session.last_valid_version_id.id,
      "DOCUMENT_REVISION", session.document_revision)

versions = env["office.workbook.version"].browse([687, 688, 689]).exists()
by_id = {version.id: version for version in versions}
assert set(by_id) == {687, 688, 689}, "Expected synthetic candidate versions are incomplete"

def workbook_bytes(version):
    attachment = version.output_attachment_id.with_user(2).exists()
    assert attachment, f"Version {version.id} output attachment is inaccessible"
    payload = b64decode(attachment.datas)
    actual_sha = sha256(payload).hexdigest()
    assert actual_sha == version.output_sha256, f"Version {version.id} attachment SHA mismatch"
    with ZipFile(BytesIO(payload)) as archive:
        bad_member = archive.testzip()
    assert bad_member is None, f"Version {version.id} ZIP member failed: {bad_member}"
    return payload

def values(payload):
    book = load_workbook(BytesIO(payload), data_only=False)
    return {
        sheet: {(cell.coordinate): (cell.value, cell.data_type, cell.number_format, cell.style_id)
                for row in book[sheet].iter_rows() for cell in row if cell.value is not None}
        for sheet in book.sheetnames
    }, book.sheetnames

payloads = {version_id: workbook_bytes(version) for version_id, version in by_id.items()}
states = {version_id: values(payload) for version_id, payload in payloads.items()}
for version_id in (687, 688, 689):
    version = by_id[version_id]
    print("VERSION", version_id, "STATE", version.state, "VALIDATION", version.validation_result,
          "PARENT", version.parent_version_id.id, "STORED_SHA", version.output_sha256,
          "ACTUAL_SHA", sha256(payloads[version_id]).hexdigest(), "SHEETS", states[version_id][1])

for candidate_id in (688, 689):
    before, before_sheets = states[by_id[candidate_id].parent_version_id.id]
    after, after_sheets = states[candidate_id]
    changes = []
    for sheet in sorted(set(before) | set(after)):
        left, right = before.get(sheet, {}), after.get(sheet, {})
        for coordinate in sorted(set(left) | set(right)):
            if left.get(coordinate) != right.get(coordinate):
                changes.append((sheet, coordinate, left.get(coordinate), right.get(coordinate)))
    print("DIFF", candidate_id, "COUNT", len(changes), "SHEET_LIST", before_sheets, "->", after_sheets)
    for change in changes:
        print("CHANGE", repr(change))

candidate3 = load_workbook(BytesIO(payloads[689]), data_only=False)
assert candidate3["Inventory"]["A1"].value == "产品编码"
assert candidate3["Inventory"]["B2"].value == 15
assert candidate3["Inventory"]["B3"].value == 20
assert candidate3["Inventory"]["D2"].value == "=B2*2"
assert candidate3["Inventory"]["D3"].value == "=B3*2"
assert candidate3["Notes"]["B2"].value == "Synthetic CB04 Browser Simulation"
assert candidate3["Notes"]["B3"].value == "Original"
assert candidate3.sheetnames == ["Inventory", "Notes"]
print("V3_ASSERTIONS PASS; FORMULA_CALCULATION NOT_CHECKED")
