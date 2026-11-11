"""Read-only, current-user readback for CC-M2-CB-06 browser HVR."""

import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook


THREAD_ID = 15880
SESSION_ID = 12212
VERSION_ID = 1464
ATTACHMENT_ID = 39747
MESSAGE_ID = 101090
OUT = Path("docs/implementation/evidence/CB-M2-CB-06/finalized-current-1464.xlsx")

thread = env["llm.thread"].browse(THREAD_ID).exists()
assert thread, f"Thread {THREAD_ID} is missing"
user = thread.user_id
assert user, "HVR Thread has no owner"
user_env = env(user=user.id)
thread = user_env["llm.thread"].browse(THREAD_ID).exists()
session = user_env["office.mapping.session"].browse(SESSION_ID).exists()
version = user_env["office.workbook.version"].browse(VERSION_ID).exists()
attachment = user_env["ir.attachment"].browse(ATTACHMENT_ID).exists()
message = user_env["mail.message"].browse(MESSAGE_ID).exists()
for record in (thread, session, version, attachment, message):
    assert record, f"Expected HVR record is missing: {record._name}"
    record.check_access("read")

assert session.thread_id == thread
assert session.current_version_id == version
assert session.last_valid_version_id == version
assert version.session_id == session
assert version.final_attachment_id == attachment
assert version.final_message_id == message
assert version.delivery_state == "delivered"
assert version.state == "finalized"
assert version.validation_result == "PARTIALLY_VERIFIED"
assert message.model == thread._name and message.res_id == thread.id
assert message.llm_role == "assistant" and attachment in message.attachment_ids
assert attachment.public is False

content = attachment.raw
actual_sha = hashlib.sha256(content).hexdigest()
assert actual_sha == version.output_sha256
OUT.write_bytes(content)
wb = load_workbook(OUT, data_only=False, read_only=True)
sheet_summary = {
    name: {
        "max_row": wb[name].max_row,
        "max_column": wb[name].max_column,
        "A1": wb[name]["A1"].value,
        "A2": wb[name]["A2"].value,
        "C1": wb[name]["C1"].value,
    }
    for name in wb.sheetnames
}
wb.close()

print(json.dumps({
    "thread_id": thread.id,
    "session_id": session.id,
    "version_id": version.id,
    "version_no": version.version_no,
    "parent_version_id": version.parent_version_id.id or False,
    "state": version.state,
    "validation_result": version.validation_result,
    "delivery_state": version.delivery_state,
    "current_version_id": session.current_version_id.id,
    "last_valid_version_id": session.last_valid_version_id.id,
    "document_revision": session.document_revision,
    "output_sha256": version.output_sha256,
    "attachment_id": attachment.id,
    "attachment_sha256": actual_sha,
    "message_id": message.id,
    "message_thread_id": message.res_id,
    "message_role": message.llm_role,
    "attachment_public": attachment.public,
    "filename": version.filename,
    "mimetype": version.mimetype,
    "readback_file": str(OUT),
    "readback_size": len(content),
    "sheets": sheet_summary,
}, sort_keys=True, default=str))
