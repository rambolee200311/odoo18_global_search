import json
from pathlib import Path


ROOT = Path.cwd() / "mymodules/wd_spike_global_search/spike_05_permission_integrity"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
MARKER = "GS05-"
companies = env["res.company"].search([], order="id")[:2]
if len(companies) != 2:
    raise RuntimeError("SPIKE-GS-05 requires two companies")

base_user = env.ref("base.group_user")
sales_manager = env.ref("sales_team.group_sale_manager")
users = {}
partners = {}
orders = {}
for index, company in enumerate(companies, 1):
    login = f"gs05_user_{company.id}@example.test"
    user = env["res.users"].search([("login", "=", login)], limit=1)
    if not user:
        user = env["res.users"].create(
            {
                "name": f"GS05 User {company.id}",
                "login": login,
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "groups_id": [(6, 0, [base_user.id, sales_manager.id])],
            }
        )
    elif sales_manager not in user.groups_id:
        user.write({"groups_id": [(4, sales_manager.id)]})
    users[str(company.id)] = {"id": user.id, "login": user.login}

    partner_ref = f"{MARKER}PARTNER-{company.id}"
    partner = env["res.partner"].search([("ref", "=", partner_ref)], limit=1)
    if not partner:
        partner = env["res.partner"].create(
            {
                "name": f"{MARKER} Company {company.id} Secret",
                "ref": partner_ref,
                "email": f"{MARKER.lower()}company{company.id}@example.test",
                "company_id": company.id,
            }
        )
    partners[str(company.id)] = {"id": partner.id, "name": partner.name}

    order_ref = f"{MARKER}ORDER-{company.id}"
    order = env["sale.order"].search(
        [("client_order_ref", "=", order_ref)], limit=1
    )
    if not order:
        order = env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "client_order_ref": order_ref,
            }
        )
    orders[str(company.id)] = {"id": order.id, "name": order.name}

env.cr.commit()
output = {
    "spike": "SPIKE-GS-05",
    "database": env.cr.dbname,
    "uid": env.uid,
    "marker": MARKER,
    "companies": [{"id": company.id, "name": company.name} for company in companies],
    "users": users,
    "partners": partners,
    "orders": orders,
    "orm_write": True,
}
(RESULTS / "simulation_result.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n"
)
print(RESULTS / "simulation_result.json")
