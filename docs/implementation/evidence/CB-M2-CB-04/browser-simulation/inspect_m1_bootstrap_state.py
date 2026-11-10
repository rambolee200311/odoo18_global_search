threads = env['llm.thread'].browse([15102, 15103]).exists()
print('THREADS', [(t.id, t.name, t.user_id.id, t.tool_ids.mapped('name')) for t in threads])
sessions = env['office.mapping.session'].search([('thread_id', 'in', threads.ids)], order='id')
print('SESSIONS', [(s.id, s.thread_id.id, s.state, s.revision, s.proposal_revision, s.preview_proposal_revision, s.document_revision, s.current_version_id.id, s.last_valid_version_id.id, s.source_message_id.id, s.source_attachment_id.id, s.final_request_uuid, s.preview_attachment_id.id) for s in sessions])
for session in sessions:
    requests = env['office.document.request'].search([('thread_id', '=', session.thread_id.id)], order='id')
    print('REQUESTS', session.thread_id.id, [(r.id, r.request_uuid, r.state, r.owner_id.id, r.input_message_id.id, r.source_attachment_id.id, r.output_attachment_id.id, r.input_sha256, r.output_sha256, r.m1_validation_status, r.m1_version_session_id, r.m1_version_session_revision, r.m1_version_proposal_revision, r.m1_validation_report_id, r.m1_validation_input_sha256, r.m1_validation_output_sha256, r.m1_validation_completed_at) for r in requests])
    versions = env['office.workbook.version'].search([('session_id', '=', session.id)], order='version_no')
    print('VERSIONS', session.id, [(v.id, v.version_no, v.version_kind, v.state, v.output_sha256, v.output_attachment_id.id, v.validation_result, v.validation_report_id) for v in versions])
for thread in threads:
    messages = env['mail.message'].search([('model', '=', 'llm.thread'), ('res_id', '=', thread.id)], order='id')
    for message in messages:
        data = message.get_tool_data() or {}
        if data:
            print('TOOLMSG', thread.id, message.id, data)
