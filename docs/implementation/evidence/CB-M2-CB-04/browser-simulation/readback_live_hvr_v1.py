"""Read-only ORM evidence for live HVR thread 15880 / session 12212.

Run with: ./venv/bin/python ./odoo-bin shell -c odoo.conf -d odoo18ce --no-http < this_file
No ORM writes are performed.
"""
import hashlib
import json
import zipfile
from io import BytesIO

from openpyxl import load_workbook

env = env(user=2)
session = env["office.mapping.session"].browse(12212).exists()
thread = env["llm.thread"].browse(15880).exists()
versions = env["office.workbook.version"].search([("session_id", "=", session.id)], order="version_no") if session else env["office.workbook.version"]
requests = env["office.document.request"].search([("thread_id", "=", thread.id)], order="id desc", limit=10) if thread else env["office.document.request"]

def attachment_info(attachment):
    if not attachment:
        return None
    raw = attachment.raw or b""
    return {
        "id": attachment.id,
        "name": attachment.name,
        "mimetype": attachment.mimetype,
        "file_size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "res_model": attachment.res_model,
        "res_id": attachment.res_id,
    }

def workbook_info(attachment):
    if not attachment:
        return None
    raw = attachment.raw or b""
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        bad_member = archive.testzip()
    workbook = load_workbook(BytesIO(raw), data_only=False, read_only=True)
    result = {
        "zip_test_error": bad_member,
        "sheetnames": workbook.sheetnames,
        "Inventory_A1": {"value": workbook["Inventory"]["A1"].value, "data_type": workbook["Inventory"]["A1"].data_type},
        "Inventory_A2": {"value": workbook["Inventory"]["A2"].value, "data_type": workbook["Inventory"]["A2"].data_type},
        "Inventory_C1": {"value": workbook["Inventory"]["C1"].value, "data_type": workbook["Inventory"]["C1"].data_type},
        "Notes_A1": workbook["Notes"]["A1"].value,
        "Notes_A2": workbook["Notes"]["A2"].value,
        "Notes_B2": workbook["Notes"]["B2"].value,
    }
    workbook.close()
    return result

def workbook_diff(before_attachment, after_attachment):
    before = load_workbook(BytesIO(before_attachment.raw), data_only=False)
    after = load_workbook(BytesIO(after_attachment.raw), data_only=False)
    diff = {"sheetnames_before": before.sheetnames, "sheetnames_after": after.sheetnames, "sheets": {}}
    for name in sorted(set(before.sheetnames) | set(after.sheetnames)):
        if name not in before.sheetnames or name not in after.sheetnames:
            diff["sheets"][name] = {"present_before": name in before.sheetnames, "present_after": name in after.sheetnames}
            continue
        left, right = before[name], after[name]
        sheet_diff = {
            "dimensions": [left.calculate_dimension(), right.calculate_dimension()],
            "merged_ranges": [sorted(str(r) for r in left.merged_cells.ranges), sorted(str(r) for r in right.merged_cells.ranges)],
            "freeze_panes": [str(left.freeze_panes), str(right.freeze_panes)],
            "sheet_state": [left.sheet_state, right.sheet_state],
            "cell_values": [],
            "cell_styles": [],
            "row_dimensions": [],
            "column_dimensions": [],
            "conditional_formatting_count": [len(left.conditional_formatting), len(right.conditional_formatting)],
            "data_validation_count": [len(left.data_validations.dataValidation), len(right.data_validations.dataValidation)],
        }
        max_row, max_col = max(left.max_row, right.max_row), max(left.max_column, right.max_column)
        for row in range(1, max_row + 1):
            for col in range(1, max_col + 1):
                a, b = left.cell(row, col), right.cell(row, col)
                if (a.value, a.data_type) != (b.value, b.data_type):
                    sheet_diff["cell_values"].append([a.coordinate, a.value, a.data_type, b.value, b.data_type])
                if a._style != b._style:
                    sheet_diff["cell_styles"].append([a.coordinate, str(a._style), str(b._style)])
        row_keys = set(left.row_dimensions) | set(right.row_dimensions)
        for key in sorted(row_keys):
            a, b = left.row_dimensions.get(key), right.row_dimensions.get(key)
            av = None if a is None else (a.height, a.hidden, a.outlineLevel)
            bv = None if b is None else (b.height, b.hidden, b.outlineLevel)
            if av != bv:
                sheet_diff["row_dimensions"].append([key, av, bv])
        col_keys = set(left.column_dimensions) | set(right.column_dimensions)
        for key in sorted(col_keys):
            a, b = left.column_dimensions.get(key), right.column_dimensions.get(key)
            av = None if a is None else (a.width, a.hidden, a.min, a.max, a.outlineLevel)
            bv = None if b is None else (b.width, b.hidden, b.min, b.max, b.outlineLevel)
            if av != bv:
                sheet_diff["column_dimensions"].append([key, av, bv])
        diff["sheets"][name] = sheet_diff
    before.close()
    after.close()
    return diff

print("SESSION", json.dumps({
    "id": session.id if session else None,
    "owner_id": session.owner_id.id if session else None,
    "thread_id": session.thread_id.id if session else None,
    "state": session.state if session else None,
    "revision": session.revision if session else None,
    "proposal_revision": session.proposal_revision if session else None,
    "document_revision": session.document_revision if session else None,
    "current_version_id": session.current_version_id.id if session and session.current_version_id else None,
    "last_valid_version_id": session.last_valid_version_id.id if session and session.last_valid_version_id else None,
    "final_request_uuid": session.final_request_uuid if session else None,
}, sort_keys=True))
print("VERSIONS", json.dumps([{
    "id": version.id,
    "version_no": version.version_no,
    "state": version.state,
    "parent_version_id": version.parent_version_id.id if version.parent_version_id else None,
    "input_sha256": version.input_sha256,
    "output_sha256": version.output_sha256,
    "validation_result": version.validation_result,
    "error_code": version.error_code,
    "validation_report_id": version.validation_report_id,
    "validation_report_sha256": version.validation_report_sha256,
    "validated_candidate_sha256": version.validated_candidate_sha256,
    "accepted_document_revision": version.accepted_document_revision,
    "attachment": attachment_info(version.output_attachment_id),
    "workbook_readback": workbook_info(version.output_attachment_id),
    "final_attachment": attachment_info(version.final_attachment_id),
} for version in versions], sort_keys=True, default=str))
if len(versions) >= 3:
    print("V2_TO_V3_WORKBOOK_DIFF", json.dumps(workbook_diff(versions[1].output_attachment_id, versions[2].output_attachment_id), sort_keys=True, default=str))
print("REQUESTS", json.dumps([{
    "id": request.id,
    "uuid": request.request_uuid,
    "state": request.state,
    "owner_id": request.owner_id.id if request.owner_id else None,
    "thread_id": request.thread_id.id if request.thread_id else None,
    "input_sha256": request.input_sha256,
    "output_sha256": request.output_sha256,
    "m1_validation_status": request.m1_validation_status,
    "output_attachment": attachment_info(request.output_attachment_id),
} for request in requests], sort_keys=True, default=str))
