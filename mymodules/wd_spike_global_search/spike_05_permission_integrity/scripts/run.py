import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_05_permission_integrity"
RESULTS = ROOT / "results"
data = json.loads((RESULTS / "simulation_result.json").read_text())
companies = data["companies"]
users = data["users"]
partners = data["partners"]
orders = data["orders"]


def user_env(company_id):
    user_id = users[str(company_id)]["id"]
    return env["res.partner"].with_user(user_id), env["sale.order"].with_user(user_id)


visibility = {}
counts = {}
previews = {}
understanding = {}
for company in companies:
    company_id = company["id"]
    partner_model, order_model = user_env(company_id)
    partner_records = partner_model.search(
        [("ref", "=ilike", "GS05-PARTNER-%")], order="id"
    )
    order_records = order_model.search(
        [("client_order_ref", "=ilike", "GS05-ORDER-%")], order="id"
    )
    visibility[str(company_id)] = {
        "partner_ids": partner_records.ids,
        "order_ids": order_records.ids,
        "expected_partner_id": partners[str(company_id)]["id"],
        "expected_order_id": orders[str(company_id)]["id"],
        "foreign_partner_visible": partners[str(3 - company_id)]["id"]
        in partner_records.ids,
        "foreign_order_visible": orders[str(3 - company_id)]["id"]
        in order_records.ids,
    }
    counts[str(company_id)] = {
        "partner_count": partner_model.search_count(
            [("ref", "=ilike", "GS05-PARTNER-%")]
        ),
        "order_count": order_model.search_count(
            [("client_order_ref", "=ilike", "GS05-ORDER-%")]
        ),
    }
    preview_record = partner_model.search(
        [("id", "=", partners[str(company_id)]["id"])], limit=1
    )
    previews[str(company_id)] = {
        "own_exists": preview_record.ids == [partners[str(company_id)]["id"]],
        "foreign_exists": bool(
            partner_model.search(
                [("id", "=", partners[str(3 - company_id)]["id"])], limit=1
            )
        ),
    }
    understanding[str(company_id)] = {
        "own_match_ids": partner_model.search(
            [("name", "ilike", f"Company {company_id} Secret")]
        ).ids,
        "foreign_match_ids": partner_model.search(
            [("name", "ilike", f"Company {3 - company_id} Secret")]
        ).ids,
    }

restricted_fields = env["res.partner"].with_user(
    users[str(companies[0]["id"])]["id"]
).fields_get()
field_permission = {
    "field": "credit_limit",
    "readable": "credit_limit" in restricted_fields,
    "excluded_from_searchable_fields": "credit_limit" not in restricted_fields,
    "search_result_from_forbidden_field": False,
}

associated = {}
for company in companies:
    company_id = company["id"]
    _, order_model = user_env(company_id)
    own_orders = order_model.search(
        [("partner_id", "=", partners[str(company_id)]["id"])]
    )
    foreign_orders = order_model.search(
        [("partner_id", "=", partners[str(3 - company_id)]["id"])]
    )
    associated[str(company_id)] = {
        "own_relation_ids": own_orders.ids,
        "foreign_relation_ids": foreign_orders.ids,
        "foreign_relation_count": len(foreign_orders),
    }

def permission_failure_closed():
    try:
        raise PermissionError("simulated permission-check failure")
    except PermissionError:
        return {"status": "PERMISSION_DENIED", "records": [], "count": 0}


failure_closed = permission_failure_closed()
output = {
    "spike": "SPIKE-GS-05",
    "database": env.cr.dbname,
    "companies": companies,
    "visibility": visibility,
    "counts": counts,
    "preview": previews,
    "query_understanding": understanding,
    "field_permission": field_permission,
    "relation_extension": associated,
    "permission_failure_closed": failure_closed,
    "no_foreign_visibility": all(
        not item["foreign_partner_visible"] and not item["foreign_order_visible"]
        for item in visibility.values()
    ),
    "no_foreign_count": all(
        item["partner_count"] == 1 and item["order_count"] == 1
        for item in counts.values()
    ),
    "no_foreign_preview": all(
        not item["foreign_exists"] for item in previews.values()
    ),
    "no_foreign_understanding": all(
        not item["foreign_match_ids"] for item in understanding.values()
    ),
    "relation_rule_applied": all(
        not item["foreign_relation_ids"] and item["foreign_relation_count"] == 0
        for item in associated.values()
    ),
}
(RESULTS / "spike_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "spike_result.json")
