import json

env = env(user=2)
session = env["office.mapping.session"].browse(11579).exists()
request = env["office.document.request"].search(
    [("request_uuid", "=", session.final_request_uuid)], limit=1
) if session else env["office.document.request"]
fields = [
    "id", "state", "revision", "proposal_revision", "document_revision",
    "current_version_id", "last_valid_version_id", "final_request_uuid",
]
session_data = {name: (getattr(session, name).id if name.endswith("_id") and getattr(session, name) else getattr(session, name)) for name in fields} if session else {}
request_fields = [
    "id", "request_uuid", "state", "owner_id", "thread_id", "source_attachment_id",
    "input_message_id", "input_sha256", "output_attachment_id", "output_sha256",
    "m1_validation_status", "m1_validator_policy_version", "m1_validation_report_id",
    "m1_validation_report_sha256", "m1_validation_input_sha256", "m1_validation_output_sha256",
    "m1_version_session_id", "m1_version_session_revision", "m1_version_proposal_revision",
]
request_data = {}
if request:
    for name in request_fields:
        value = getattr(request, name)
        request_data[name] = value.id if hasattr(value, "id") else value
    request_data["output_attachment_owner"] = [request.output_attachment_id.res_model, request.output_attachment_id.res_id]
    request_data["actual_output_size"] = len(request.output_attachment_id.raw or b"")
print(json.dumps({"session": session_data, "request": request_data}, default=str, ensure_ascii=False, sort_keys=True))
