"""Create one synthetic browser thread dedicated to HVR-SCN-005.

Run with ``odoo-bin shell -c odoo.conf -d odoo18ce < this_file``.
Only a synthetic workbook and the synthetic test owner are used.
"""

import hashlib
import json
import uuid
from pathlib import Path

from odoo import api

base = Path("docs/implementation/evidence/CB-M2-CB-04/browser-simulation")
index_path = base / "synthetic-thread-index.json"
workbook_path = base / "cb04-browser-synthetic-v1-input.xlsx"
index = json.loads(index_path.read_text())
content = workbook_path.read_bytes()
admin_id = index["owner_id"]
company_id = index["company_id"]
admin_env = api.Environment(env.cr, admin_id, {"allowed_company_ids": [company_id]})
source_thread = admin_env["llm.thread"].browse(index["threads"][1]["thread_id"])
suffix = uuid.uuid4().hex[:10]
thread = admin_env["llm.thread"].create({
    "name": f"CC04-HVR-Synthetic-continuity-{suffix}",
    "provider_id": source_thread.provider_id.id,
    "model_id": source_thread.model_id.id,
})
attachment = admin_env["ir.attachment"].create({
    "name": "cb04-synthetic-continuity.xlsx",
    "type": "binary",
    "raw": content,
    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "company_id": company_id,
    "public": False,
})
message = thread.message_post(
    body=(
        "Synthetic test workbook for CC-04 sequential editing. Inventory!A2:D3 contains "
        "synthetic rows, D2 and D3 are formulas, Notes contains fixed synthetic metadata, "
        "and Inventory!E2 is an initialization marker. No business data is included."
    ),
    llm_role="user",
    author_id=admin_env.user.partner_id.id,
    attachment_ids=[attachment.id],
)
entry = {
    "label": "continuity",
    "thread_id": thread.id,
    "upload_message_id": message.id,
    "attachment_id": attachment.id,
    "model": source_thread.model_id.name,
    "provider": source_thread.provider_id.service,
    "input_sha256": hashlib.sha256(content).hexdigest(),
}
if any(item.get("thread_id") == thread.id for item in index["threads"]):
    raise RuntimeError("duplicate thread identity")
index["threads"].append(entry)
index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
env.cr.commit()
print(json.dumps(entry, ensure_ascii=False, sort_keys=True))
