import json, platform, sys, os
import odoo
checks={'odoo_version':odoo.release.version,'python':sys.version,'platform':platform.platform(),'uid':env.uid,'su':env.su,'database':env.cr.dbname}
env.cr.execute('SELECT version()')
checks['postgresql_version']=env.cr.fetchone()[0]
mod=env['ir.module.module'].search([('name','=','office_engine_odoo')],limit=1)
checks['office_engine_odoo_module']={'state':mod.state if mod else None,'installed_version':mod.installed_version if mod else None}
uuid='d8c5b6aa-3484-41da-a7a5-b297f0565c41'; filename='TV-SPAWN-RECOVERY-'+uuid+'.xlsx'
checks['fresh_shell_cleanup_check']={'request_count':env['office.document.request'].search_count([('request_uuid','=',uuid)]),'source_attachment_count':env['ir.attachment'].search_count([('name','=',filename)])}
print(json.dumps(checks,ensure_ascii=False,default=str))
