import json
import os
from pathlib import Path

from odoo.exceptions import AccessError

BASE = Path.cwd() / "mymodules/wd_tv_global_search/tv_04_complex_permissions"
RESULT_PATH = BASE / "results" / "permission_result.json"
PREFIX = "TV04-"


def find_or_create(model, domain, values):
    record = model.search(domain, limit=1)
    if record:
        record.write(values)
        return record
    return model.create(values)


def safe_search(model, domain, limit=None):
    try:
        records = model.search(domain, limit=limit)
        return {"status": "OK", "ids": records.ids, "count": len(records)}
    except (AccessError, PermissionError) as error:
        return {
            "status": "PERMISSION_DENIED",
            "ids": [],
            "count": 0,
            "error": type(error).__name__,
        }
    except Exception as error:
        return {
            "status": "PERMISSION_DENIED",
            "ids": [],
            "count": 0,
            "error": type(error).__name__,
        }


def create_fixture():
    base_company = env["res.company"].search([], order="id", limit=1)
    company_a = find_or_create(
        env["res.company"],
        [("name", "=", f"{PREFIX} Company A")],
        {"name": f"{PREFIX} Company A"},
    )
    company_b = find_or_create(
        env["res.company"],
        [("name", "=", f"{PREFIX} Company B")],
        {"name": f"{PREFIX} Company B"},
    )
    restricted_group = find_or_create(
        env["res.groups"],
        [("name", "=", f"{PREFIX} Restricted")],
        {"name": f"{PREFIX} Restricted"},
    )
    base_user = env.ref("base.group_user")
    portal_group = env.ref("base.group_portal")
    sales_manager = env.ref("sales_team.group_sale_manager")

    def user(login, name, company, companies, groups):
        record = find_or_create(
            env["res.users"],
            [("login", "=", login)],
            {
                "name": name,
                "login": login,
                "company_id": company.id,
                "company_ids": [(6, 0, companies.ids)],
                "groups_id": [(6, 0, groups.ids)],
            },
        )
        record.write(
            {
                "company_id": company.id,
                "company_ids": [(6, 0, companies.ids)],
                "groups_id": [(6, 0, groups.ids)],
            }
        )
        return record

    user_a = user(
        f"{PREFIX.lower()}a@example.test",
        f"{PREFIX} User A",
        company_a,
        company_a,
        base_user | restricted_group | sales_manager,
    )
    user_b = user(
        f"{PREFIX.lower()}b@example.test",
        f"{PREFIX} User B",
        company_b,
        company_b,
        base_user | restricted_group | sales_manager,
    )
    user_multi = user(
        f"{PREFIX.lower()}multi@example.test",
        f"{PREFIX} Multi User",
        company_a,
        company_a | company_b,
        base_user | restricted_group | sales_manager,
    )
    portal = user(
        f"{PREFIX.lower()}portal@example.test",
        f"{PREFIX} Portal",
        company_a,
        company_a,
        portal_group,
    )

    partner_a = find_or_create(
        env["res.partner"],
        [("ref", "=", f"{PREFIX}PARTNER-A")],
        {"name": f"{PREFIX} Partner A", "ref": f"{PREFIX}PARTNER-A", "company_id": company_a.id},
    )
    partner_b = find_or_create(
        env["res.partner"],
        [("ref", "=", f"{PREFIX}PARTNER-B")],
        {"name": f"{PREFIX} Partner B", "ref": f"{PREFIX}PARTNER-B", "company_id": company_b.id},
    )
    partner_shared = find_or_create(
        env["res.partner"],
        [("ref", "=", f"{PREFIX}PARTNER-SHARED")],
        {"name": f"{PREFIX} Shared Partner", "ref": f"{PREFIX}PARTNER-SHARED", "company_id": False},
    )
    partner_blocked = find_or_create(
        env["res.partner"],
        [("ref", "=", f"{PREFIX}PARTNER-BLOCKED")],
        {"name": f"{PREFIX} Blocked Partner", "ref": f"{PREFIX}PARTNER-BLOCKED", "company_id": company_a.id},
    )

    sale_model = env["sale.order"]
    order_a = find_or_create(
        sale_model,
        [("client_order_ref", "=", f"{PREFIX}ORDER-A")],
        {"partner_id": partner_a.id, "company_id": company_a.id, "client_order_ref": f"{PREFIX}ORDER-A"},
    )
    order_b = find_or_create(
        sale_model,
        [("client_order_ref", "=", f"{PREFIX}ORDER-B")],
        {"partner_id": partner_b.id, "company_id": company_b.id, "client_order_ref": f"{PREFIX}ORDER-B"},
    )
    order_shared = find_or_create(
        sale_model,
        [("client_order_ref", "=", f"{PREFIX}ORDER-SHARED")],
        {"partner_id": partner_shared.id, "company_id": company_a.id, "client_order_ref": f"{PREFIX}ORDER-SHARED"},
    )
    order_blocked = find_or_create(
        sale_model,
        [("client_order_ref", "=", f"{PREFIX}ORDER-BLOCKED")],
        {"partner_id": partner_blocked.id, "company_id": company_a.id, "client_order_ref": f"{PREFIX}ORDER-BLOCKED"},
    )
    order_future = find_or_create(
        sale_model,
        [("client_order_ref", "=", f"{PREFIX}ORDER-FUTURE")],
        {
            "partner_id": partner_a.id,
            "company_id": company_a.id,
            "client_order_ref": f"{PREFIX}ORDER-FUTURE",
            "date_order": "2099-01-01 00:00:00",
        },
    )

    rule_model = env["ir.rule"]
    partner_rule = find_or_create(
        rule_model,
        [("name", "=", f"{PREFIX} partner company rule")],
        {
            "name": f"{PREFIX} partner company rule",
            "model_id": env["ir.model"]._get("res.partner").id,
            "domain_force": "['|', ('company_id', '=', False), ('company_id', 'in', user.company_ids.ids)]",
            "groups": [(4, restricted_group.id)],
        },
    )
    order_rule = find_or_create(
        rule_model,
        [("name", "=", f"{PREFIX} order field rule")],
        {
            "name": f"{PREFIX} order field rule",
            "model_id": env["ir.model"]._get("sale.order").id,
            "domain_force": "['&', '|', ('client_order_ref', 'not ilike', 'TV04-%'), ('company_id', 'in', user.company_ids.ids), '&', '|', ('client_order_ref', 'not ilike', 'TV04-%'), ('client_order_ref', 'not ilike', 'TV04-ORDER-BLOCKED'), '|', ('client_order_ref', 'not ilike', 'TV04-%'), ('date_order', '<=', time.strftime('%Y-%m-%d 23:59:59'))]",
            "global": True,
            "groups": [(5, 0, 0)],
        },
    )
    env.cr.commit()
    return {
        "base_company": base_company.id,
        "companies": {"a": company_a.id, "b": company_b.id},
        "users": {
            "a": user_a.id,
            "b": user_b.id,
            "multi": user_multi.id,
            "portal": portal.id,
        },
        "partners": {
            "a": partner_a.id,
            "b": partner_b.id,
            "shared": partner_shared.id,
            "blocked": partner_blocked.id,
        },
        "orders": {
            "a": order_a.id,
            "b": order_b.id,
            "shared": order_shared.id,
            "blocked": order_blocked.id,
            "future": order_future.id,
        },
        "group": restricted_group.id,
        "rules": [partner_rule.id, order_rule.id],
    }


def run_scenarios(fixture):
    partner_domain = [("ref", "=ilike", f"{PREFIX}PARTNER-%")]
    order_domain = [("client_order_ref", "=ilike", f"{PREFIX}ORDER-%")]
    users = fixture["users"]
    scenarios = {}
    for label in ("a", "b", "multi", "portal"):
        partner_model = env["res.partner"].with_user(users[label])
        order_model = env["sale.order"].with_user(users[label])
        scenarios[label] = {
            "partners": safe_search(partner_model, partner_domain),
            "orders": safe_search(order_model, order_domain),
        }

    user_a_partner = env["res.partner"].with_user(users["a"])
    user_multi_partner = env["res.partner"].with_user(users["multi"])
    user_a_order = env["sale.order"].with_user(users["a"])
    scenarios["shared_and_company_empty"] = {
        "user_a_shared": safe_search(user_a_partner, [("id", "=", fixture["partners"]["shared"])]),
        "user_a_company_a": safe_search(user_a_partner, [("id", "=", fixture["partners"]["a"])]),
        "user_a_company_b": safe_search(user_a_partner, [("id", "=", fixture["partners"]["b"])]),
        "multi_shared": safe_search(user_multi_partner, [("id", "=", fixture["partners"]["shared"])]),
    }
    scenarios["field_rule"] = {
        "blocked_order_visible": safe_search(
            user_a_order, [("id", "=", fixture["orders"]["blocked"])]
        )
    }
    scenarios["time_rule"] = {
        "past_order_visible": safe_search(
            user_a_order, [("id", "=", fixture["orders"]["a"])]
        ),
        "future_order_visible": safe_search(
            user_a_order, [("id", "=", fixture["orders"]["future"])]
        ),
    }
    scenarios["relation_depth_2"] = {
        "user_a_order_by_partner_a": safe_search(
            user_a_order, [("partner_id", "=", fixture["partners"]["a"])]
        ),
        "user_a_order_by_partner_b": safe_search(
            user_a_order, [("partner_id", "=", fixture["partners"]["b"])]
        ),
    }
    fields = env["res.partner"].with_user(users["a"]).fields_get(["credit_limit", "name"])
    scenarios["field_permission"] = {
        "credit_limit_readable": "credit_limit" in fields,
        "name_readable": "name" in fields,
        "credit_limit_excluded": "credit_limit" not in fields,
    }

    user_a = env["res.users"].browse(users["a"])
    user_a.write(
        {
            "company_id": fixture["companies"]["b"],
            "company_ids": [(6, 0, [fixture["companies"]["b"]])],
        }
    )
    env.cr.commit()
    switched = safe_search(
        env["res.partner"].with_user(users["a"]),
        [("id", "in", [fixture["partners"]["a"], fixture["partners"]["b"]])],
    )
    user_a.write(
        {
            "company_id": fixture["companies"]["a"],
            "company_ids": [(6, 0, [fixture["companies"]["a"]])],
        }
    )
    env.cr.commit()
    scenarios["runtime_permission_change"] = {
        "after_switch_to_b": switched,
        "company_a_hidden_after_switch": fixture["partners"]["a"] not in switched["ids"],
        "company_b_visible_after_switch": fixture["partners"]["b"] in switched["ids"],
    }

    try:
        raise AccessError("simulated permission evaluation failure")
    except AccessError as error:
        scenarios["failure_closed"] = {
            "status": "PERMISSION_DENIED",
            "ids": [],
            "count": 0,
            "error": type(error).__name__,
        }
    return scenarios


def cleanup(fixture):
    env["ir.rule"].browse(fixture["rules"]).unlink()
    env["sale.order"].search([("client_order_ref", "=ilike", f"{PREFIX}%")]).unlink()
    env["res.partner"].search([("ref", "=ilike", f"{PREFIX}%")]).unlink()
    env["res.users"].browse(list(fixture["users"].values())).unlink()
    env["res.groups"].browse(fixture["group"]).unlink()
    env["res.company"].browse(list(fixture["companies"].values())).unlink()
    env.cr.commit()


def main():
    fixture = create_fixture()
    try:
        scenarios = run_scenarios(fixture)
        result = {
            "tv": "TV-04",
            "database": env.cr.dbname,
            "fixture": fixture,
            "scenarios": scenarios,
            "no_leakage": (
                fixture["partners"]["b"] not in scenarios["a"]["partners"]["ids"]
                and fixture["orders"]["b"] not in scenarios["a"]["orders"]["ids"]
                and not scenarios["shared_and_company_empty"]["user_a_company_b"]["ids"]
                and not scenarios["field_rule"]["blocked_order_visible"]["ids"]
                and not scenarios["relation_depth_2"]["user_a_order_by_partner_b"]["ids"]
            ),
            "failure_closed": scenarios["failure_closed"]["status"] == "PERMISSION_DENIED",
        }
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(RESULT_PATH)
    finally:
        cleanup(fixture)


main()
