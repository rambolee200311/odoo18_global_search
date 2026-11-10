env = env(user=2)
session = env['office.mapping.session'].browse(11579).exists()
request = env['office.document.request'].search([('request_uuid', '=', session.final_request_uuid)], limit=1)
print('SESSION', {
    'id': session.id, 'state': session.state, 'revision': session.revision,
    'proposal_revision': session.proposal_revision, 'document_revision': session.document_revision,
    'current_version_id': session.current_version_id.id, 'last_valid_version_id': session.last_valid_version_id.id,
    'final_request_uuid': session.final_request_uuid,
})
print('REQUEST', {
    'id': request.id, 'state': request.state, 'owner_id': request.owner_id.id,
    'thread_id': request.thread_id.id, 'source_attachment_id': request.source_attachment_id.id,
    'input_message_id': request.input_message_id.id, 'input_sha256': request.input_sha256,
    'output_attachment_id': request.output_attachment_id.id, 'output_sha256': request.output_sha256,
    'validation_status': request.m1_validation_status, 'validation_policy': request.m1_validator_policy_version,
    'validation_input_sha256': request.m1_validation_input_sha256,
    'validation_output_sha256': request.m1_validation_output_sha256,
    'validation_session_id': request.m1_version_session_id,
    'validation_session_revision': request.m1_version_session_revision,
    'validation_proposal_revision': request.m1_version_proposal_revision,
    'validation_report_sha256': request.m1_validation_report_sha256,
})
