import json
checks=[]
for request_uuid in ('40dd56ed-ec37-4b7a-8812-549aa23ac44e','d8c5b6aa-3484-41da-a7a5-b297f0565c41'):
    filename='TV-SPAWN-RECOVERY-'+request_uuid+'.xlsx'
    checks.append({'request_uuid':request_uuid,'request_count':env['office.document.request'].search_count([('request_uuid','=',request_uuid)]),'attachment_count':env['ir.attachment'].search_count([('name','=',filename)])})
print(json.dumps({'database':env.cr.dbname,'fresh_shell':True,'checks':checks},ensure_ascii=False))
