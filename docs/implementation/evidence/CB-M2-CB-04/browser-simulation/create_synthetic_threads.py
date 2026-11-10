"""Run with `odoo-bin shell -c odoo.conf -d odoo18ce` to create synthetic HVR threads."""
import json
import uuid
from pathlib import Path
from odoo import api

base = Path("docs/implementation/evidence/CB-M2-CB-04/browser-simulation")
xlsx_path = base / "cb04-browser-synthetic-v1-input.xlsx"
content = xlsx_path.read_bytes()
admin_id = env.ref("base.user_admin").id
company_id = env.ref("base.main_company").id
admin_env = api.Environment(env.cr, admin_id, {"allowed_company_ids": [company_id]})
source_note = (
    "Synthetic test workbook. The Inventory data area is A2:D3; A1:D1 are headers. "
    "Inventory!D2 and D3 are formulas. Notes contains fixed synthetic metadata and must be preserved. "
    "Inventory!E2 is an initialization marker outside the data area and must be preserved. "
    "No real Odoo business data is included."
)
provider = admin_env["llm.thread"].browse(15101).provider_id
model = admin_env["llm.thread"].browse(15101).model_id
threads = []
for label in ("primary", "sequential"):
    suffix = uuid.uuid4().hex[:10]
    thread = admin_env["llm.thread"].create({
        "name": f"CC04-HVR-Synthetic-{label}-{suffix}",
        "provider_id": provider.id,
        "model_id": model.id,
    })
    attachment = admin_env["ir.attachment"].create({
        "name": f"cb04-synthetic-{label}.xlsx",
        "type": "binary",
        "raw": content,
        "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "company_id": company_id,
        "public": False,
    })
    upload = thread.message_post(
        body=source_note,
        llm_role="user",
        author_id=admin_env.user.partner_id.id,
        attachment_ids=[attachment.id],
    )
    threads.append({
        "label": label,
        "thread_id": thread.id,
        "upload_message_id": upload.id,
        "attachment_id": attachment.id,
        "model": model.name,
        "provider": provider.service,
    })
env.cr.commit()
(base / "synthetic-thread-index.json").write_text(json.dumps({
    "database": env.cr.dbname,
    "owner_id": admin_id,
    "company_id": company_id,
    "input_sha256": __import__("hashlib").sha256(content).hexdigest(),
    "threads": threads,
}, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"input_sha256": __import__("hashlib").sha256(content).hexdigest(), "threads": threads}, ensure_ascii=False))
