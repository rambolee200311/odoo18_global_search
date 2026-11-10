import json
import traceback

from odoo.tools import html2plaintext

import odoo.addons.office_engine_odoo.models.office_document_request as request_module

original_deliver = request_module.OfficeDocumentRequest._deliver_result

def traced_deliver(self, *args, **kwargs):
    try:
        return original_deliver(self, *args, **kwargs)
    except Exception as exc:
        print('DELIVER_EXCEPTION_TYPE', type(exc).__name__)
        print('DELIVER_EXCEPTION', str(exc)[:1000])
        traceback.print_exc()
        raise

request_module.OfficeDocumentRequest._deliver_result = traced_deliver
env = env(user=2)

thread = env['llm.thread'].browse(15102).exists()
session = env['office.mapping.session'].browse(11579).exists()
assert thread and session and session.thread_id == thread
assert thread.user_id.id == env.uid == 2
assert session.state == 'confirmation_required'
assert session.preview_proposal_revision == session.proposal_revision
latest_user = env['mail.message'].search([
    ('model', '=', 'llm.thread'), ('res_id', '=', thread.id),
    ('llm_role', '=', 'user'), ('author_id', '=', env.user.partner_id.id),
    ('is_error', '=', False),
], order='id desc', limit=1)
assert html2plaintext(latest_user.body).strip() == '确认并生成正式文件', repr(latest_user.body)
context_message = latest_user
result = env['office.mapping.tool'].with_context(message=context_message).office_finalize(
    session.id, session.revision, session.proposal_revision
)
print('FINALIZE_RESULT', json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
env.cr.commit()
print('SESSION_AFTER', json.dumps({
    'id': session.id,
    'state': session.state,
    'revision': session.revision,
    'proposal_revision': session.proposal_revision,
    'document_revision': session.document_revision,
    'current_version_id': session.current_version_id.id,
    'last_valid_version_id': session.last_valid_version_id.id,
    'final_request_uuid': session.final_request_uuid,
}, ensure_ascii=False, sort_keys=True))
