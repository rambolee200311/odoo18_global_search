import sys
sys.stdout.reconfigure(line_buffering=True)

import json
import os
from odoo import api

base_env = env
users = base_env['res.users'].search([('name', '=', 'Mitchell Admin'), ('active', '=', True)])
print('UI_USER_MATCH_COUNT=%s' % len(users))
if len(users) != 1:
    raise RuntimeError('Could not identify exactly one Mitchell Admin user')
user = users[0]
user_env = api.Environment(base_env.cr, user.id, dict(base_env.context))
print('RETRIEVER_CALL uid=%s' % user.id)
tools = user_env['llm.tool'].search([('name', '=', 'odoo_record_retriever'), ('active', '=', True)], limit=2)
print('RETRIEVER_TOOL_COUNT=%s' % len(tools))
if len(tools) != 1:
    raise RuntimeError('Expected exactly one active odoo_record_retriever tool')
result = tools.execute({
    'model': 'res.currency',
    'domain': [['active', '=', True]],
    'fields': ['name', 'symbol'],
    'limit': 1,
})
print('RETRIEVER_RESULT=' + json.dumps(result, ensure_ascii=False, sort_keys=True))
print('RETRIEVER_PASS=' + str(isinstance(result, list) and len(result) <= 1 and all(set(row).issubset({'id','name','symbol'}) for row in result)))
base_env.cr.rollback()
os._exit(0)
