import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_06_form_preview_readonly"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

security_data = json.loads(
    (
        Path.cwd()
        / "mymodules/wd_spike_global_search/spike_05_permission_integrity/results/simulation_result.json"
    ).read_text()
)
preview_user = security_data["users"]["1"]["id"]
stock_user = env.ref("stock.group_stock_user")
user = env["res.users"].browse(preview_user)
if stock_user not in user.groups_id:
    user.write({"groups_id": [(4, stock_user.id)]})
env.cr.commit()

targets = [
    ("res.partner", security_data["partners"]["1"]["id"]),
    ("sale.order", security_data["orders"]["1"]["id"]),
    (
        "stock.picking",
        env["stock.picking"]
        .search([("origin", "=", "GS03-PICKING-2")], limit=1)
        .id,
    ),
]
if not targets[-1][1]:
    raise RuntimeError("GS03 stock picking is required for SPIKE-GS-06")

snapshot = []
for model_name, record_id in targets:
    model = env[model_name].with_user(preview_user)
    view = env["ir.ui.view"].search(
        [("model", "=", model_name), ("type", "=", "form")],
        order="priority,id",
        limit=1,
    )
    if not view:
        raise RuntimeError(f"No form view for {model_name}")
    record = model.browse(record_id)
    readable = record.read(["id", "display_name"])
    view_data = view.read(["id", "name", "arch"])[0]
    snapshot.append(
        {
            "model": model_name,
            "record_id": record_id,
            "display_name": readable[0]["display_name"],
            "view_id": view_data["id"],
            "view_name": view_data["name"],
            "arch": view_data["arch"],
            "user_id": preview_user,
        }
    )

output = {
    "spike": "SPIKE-GS-06",
    "database": env.cr.dbname,
    "uid": env.uid,
    "preview_user": preview_user,
    "targets": snapshot,
    "orm_read": True,
    "business_write": False,
}
(RESULTS / "view_snapshot.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "view_snapshot.json")

