from odoo.addons.wd_global_search.services.upgrade import run_post_migration


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    run_post_migration(env)
