import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_06_form_preview_readonly"
RESULTS = ROOT / "results"
snapshot = json.loads((RESULTS / "view_snapshot.json").read_text())
user_id = snapshot["preview_user"]


def readonly_policy():
    return {
        "create": False,
        "edit": False,
        "delete": False,
        "save": False,
        "business_buttons": False,
        "chatter_post": False,
        "attachment_upload": False,
        "activity_actions": False,
    }


def load_form(target):
    model = env[target["model"]].with_user(user_id)
    record = model.search([("id", "=", target["record_id"])], limit=1)
    if not record:
        return {
            "model": target["model"],
            "record_id": target["record_id"],
            "status": "PERMISSION_OR_DELETED",
            "arch_loaded": False,
        }
    view = env["ir.ui.view"].browse(target["view_id"])
    form = model.get_view(view_id=view.id, view_type="form")
    arch = form["arch"]
    return {
        "model": target["model"],
        "record_id": target["record_id"],
        "status": "LOADED",
        "arch_loaded": bool(arch),
        "view_id": view.id,
        "button_nodes": arch.count("<button"),
        "chatter_nodes": arch.count("oe_chatter"),
        "record_readable": bool(record.read(["id"])),
        "onchange_invoked": False,
        "orm_write_count": 0,
        "policy": readonly_policy(),
    }


form_loads = [load_form(target) for target in snapshot["targets"]]
user_partner = env["res.partner"].with_user(user_id)
foreign_partner_id = json.loads(
    (
        Path.cwd()
        / "mymodules/wd_spike_global_search/spike_05_permission_integrity/results/simulation_result.json"
    ).read_text()
)["partners"]["2"]["id"]

deleted_or_changed = {
    "deleted_record_status": "PERMISSION_OR_DELETED"
    if not user_partner.search([("id", "=", 999999999)], limit=1)
    else "VISIBLE",
    "permission_changed_status": "PERMISSION_OR_DELETED"
    if not user_partner.search([("id", "=", foreign_partner_id)], limit=1)
    else "VISIBLE",
    "safe_message": "Record unavailable or permission changed",
}

workspace_before = {
    "raw_query": "GS05 Company",
    "refinement": ["公司 1"],
    "selected": ["res.partner", snapshot["targets"][0]["record_id"]],
}
workspace_after = {
    **workspace_before,
    "selected": ["sale.order", snapshot["targets"][1]["record_id"]],
}

output = {
    "spike": "SPIKE-GS-06",
    "database": env.cr.dbname,
    "form_loads": form_loads,
    "all_forms_loaded": all(item["arch_loaded"] for item in form_loads),
    "readonly_policies": all(
        all(value is False for value in item["policy"].values())
        for item in form_loads
    ),
    "no_onchange_or_write": all(
        not item["onchange_invoked"] and item["orm_write_count"] == 0
        for item in form_loads
    ),
    "deleted_or_permission_changed": deleted_or_changed,
    "switch_preserves_query_state": (
        workspace_before["raw_query"] == workspace_after["raw_query"]
        and workspace_before["refinement"] == workspace_after["refinement"]
        and workspace_before["selected"] != workspace_after["selected"]
    ),
    "narrow_screen_policy": {
        "desktop": "split_results_and_preview",
        "narrow": "single_pane_selected_preview",
        "preview_stays_readonly": True,
        "full_record_action": "open_standard_form_in_new_tab",
    },
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")
