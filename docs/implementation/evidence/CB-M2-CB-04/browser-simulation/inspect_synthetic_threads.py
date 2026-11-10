threads = env['llm.thread'].browse([15102, 15103]).exists()
print('THREADS', [(t.id, t.name, t.user_id.id, t.tool_ids.mapped('name')) for t in threads])
print('OFFICE_TOOLS', env['llm.tool'].search([('name', 'in', ['office', 'office_prepare_context', 'office_save_mapping_preview', 'office_finalize'])]).mapped(lambda x: (x.id, x.name, x.active, x.decorator_model, x.decorator_method)))
print('SESSIONS', env['office.mapping.session'].search([('thread_id', 'in', threads.ids)]).mapped(lambda s: (s.id, s.thread_id.id, s.state, s.revision, s.proposal_revision, s.document_revision, s.current_version_id.id, s.last_valid_version_id.id)))
