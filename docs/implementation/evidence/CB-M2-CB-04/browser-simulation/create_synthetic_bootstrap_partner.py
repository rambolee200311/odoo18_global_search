"""Create one clearly synthetic ORM anchor for the authorized M1 bootstrap."""
import json
import uuid
from pathlib import Path

from odoo import api

base = Path("docs/implementation/evidence/CB-M2-CB-04/browser-simulation")
index_path = base / "synthetic-thread-index.json"
data = json.loads(index_path.read_text())
admin_id = data["owner_id"]
company_id = data["company_id"]
admin_env = api.Environment(env.cr, admin_id, {"allowed_company_ids": [company_id]})
partner = admin_env["res.partner"].create({
    "name": "CB04 Synthetic V1 Bootstrap " + uuid.uuid4().hex[:12],
    "email": "cb04-bootstrap-" + uuid.uuid4().hex[:12] + "@example.invalid",
    "company_type": "person",
})
env.cr.commit()
data["synthetic_anchor"] = {
    "model": "res.partner",
    "record_id": partner.id,
    "name": partner.name,
    "email": partner.email,
}
index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(data["synthetic_anchor"], ensure_ascii=False))
