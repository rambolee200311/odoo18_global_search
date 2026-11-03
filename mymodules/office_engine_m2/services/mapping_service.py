import json
import re

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import validate_proposal, validate_user_revision


_UNAVAILABLE = "The mapping session context is unavailable."


def _positive_id(value, label):
    if type(value) is not int or value < 1:
        raise ValidationError(_("Invalid %s reference.") % label)
    return value


def _validate_session_bindings(
    env,
    *,
    thread_id,
    source_message_id,
    source_attachment_id,
    target_model,
    target_record_id,
):
    """Validate all references under the caller's current Odoo environment."""
    thread_id = _positive_id(thread_id, "thread")
    source_message_id = _positive_id(source_message_id, "source message")
    source_attachment_id = _positive_id(source_attachment_id, "source attachment")
    target_record_id = _positive_id(target_record_id, "target record")
    if not isinstance(target_model, str) or not target_model.strip():
        raise ValidationError(_("Invalid target model."))

    thread = env["llm.thread"].browse(thread_id).exists()
    message = env["mail.message"].browse(source_message_id).exists()
    attachment = env["ir.attachment"].browse(source_attachment_id).exists()
    if not thread or not message or not attachment:
        raise AccessError(_(_UNAVAILABLE))

    # Check access before examining relationships so a forged ID cannot be used
    # to discover another user's thread, message, or attachment.
    thread.check_access("read")
    if thread.user_id.id != env.uid:
        raise AccessError(_(_UNAVAILABLE))
    message.check_access("read")
    attachment.check_access("read")

    if (
        message.model != "llm.thread"
        or message.res_id != thread.id
        or message not in thread.message_ids
        or message.llm_role != "user"
        or message.author_id.id != env.user.partner_id.id
        or message.is_error
        or attachment not in message.attachment_ids
    ):
        raise AccessError(_(_UNAVAILABLE))
    if target_model not in env.registry.models:
        raise AccessError(_(_UNAVAILABLE))
    target_model_recordset = env[target_model]
    target_model_recordset.browse().check_access("read")
    target = target_model_recordset.browse(target_record_id).exists()
    if not target:
        raise AccessError(_(_UNAVAILABLE))
    target.check_access("read")
    return thread, message, attachment, target


def create_session(
    env,
    *,
    thread_id,
    source_message_id,
    source_attachment_id,
    target_model,
    target_record_id,
):
    """Create a minimal session after rechecking every binding as the caller."""
    values = {
        "thread_id": thread_id,
        "source_message_id": source_message_id,
        "source_attachment_id": source_attachment_id,
        "target_model": target_model,
        "target_record_id": target_record_id,
    }
    session = env["office.mapping.session"]._create_from_mapping_service(values)
    return get_session_context(env, session.id)


def get_session_context(env, session_id):
    """Return allowlisted metadata for a session owned by the current user."""
    session_id = _positive_id(session_id, "mapping session")
    session = env["office.mapping.session"].search([("id", "=", session_id)], limit=1)
    if not session:
        raise AccessError(_(_UNAVAILABLE))
    session.check_access("read")
    return {
        "session_id": session.id,
        "owner_id": session.owner_id.id,
        "company_id": session.company_id.id,
        "thread_id": session.thread_id.id,
        "source_message_id": session.source_message_id.id,
        "source_attachment_id": session.source_attachment_id.id,
        "target_model": session.target_model,
        "target_record_id": session.target_record_id,
        "state": session.state,
        "revision": session.revision,
        "error_code": session.error_code or None,
    }


def transition_session(env, session_id, target_state, expected_revision, *, error_code=None):
    """Apply one server-authorized state change with optimistic revision control."""
    session_id = _positive_id(session_id, "mapping session")
    session = env["office.mapping.session"].search([("id", "=", session_id)], limit=1)
    if not session:
        raise AccessError(_(_UNAVAILABLE))
    result = session._transition_from_service(
        target_state,
        expected_revision,
        error_code=error_code,
    )
    return result


def _owned_session(env, session_id):
    session_id = _positive_id(session_id, "mapping session")
    session = env["office.mapping.session"].browse(session_id).exists()
    if not session:
        raise AccessError(_(_UNAVAILABLE))
    session.check_access("read")
    if session.owner_id.id != env.uid or session.company_id.id not in env.companies.ids:
        raise AccessError(_(_UNAVAILABLE))
    return session


def _load_mapping_data(session):
    try:
        rules = json.loads(session.mapping_rules_json or "{}")
        context = json.loads(session.context_json or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError(_("The mapping context is invalid.")) from exc
    if (
        not isinstance(rules, dict)
        or not isinstance(context, dict)
        or not {"target_manifest", "allowed_fields"}.issubset(context)
        or set(context) - {
            "target_manifest", "allowed_fields", "mapping_groups", "template_text",
            "manifest_metadata_version", "document_format", "selected_record_ids",
            "extra_authorized_fields",
        }
    ):
        raise ValidationError(_("The mapping context is invalid."))
    return (
        rules,
        context["target_manifest"],
        context["allowed_fields"],
        context.get("mapping_groups", []),
    )


def _validate_mapping_groups(mapping_groups, target_manifest=None):
    if mapping_groups is None:
        return []
    if not isinstance(mapping_groups, list) or len(mapping_groups) > 50:
        raise ValidationError(_("Invalid mapping groups."))
    normalized = []
    seen = set()
    manifest_ids = {
        item.get("element_id")
        for item in (target_manifest or [])
        if isinstance(item, dict) and isinstance(item.get("element_id"), str)
    }
    occupied_targets = set()
    for group in mapping_groups:
        if not isinstance(group, dict):
            raise ValidationError(_("Invalid mapping groups."))
        simple = set(group) == {"group_id", "collection_field", "row_count"}
        detailed_required = {
            "group_id", "collection_field", "relation_model", "row_count", "target_rows", "allowed_fields"
        }
        detailed_optional = {"sort_by", "sort_direction", "record_ids"}
        detailed = (
            detailed_required.issubset(group)
            and not (set(group) - detailed_required - detailed_optional)
            and ("sort_by" in group) == ("sort_direction" in group)
        )
        if not (simple or detailed):
            raise ValidationError(_("Invalid mapping groups."))
        if (
            not isinstance(group["group_id"], str)
            or not group["group_id"].isidentifier()
            or len(group["group_id"]) > 64
            or not isinstance(group["collection_field"], str)
            or not group["collection_field"].isidentifier()
            or type(group["row_count"]) is not int
            or group["row_count"] < 1
            or group["group_id"] in seen
        ):
            raise ValidationError(_("Invalid mapping groups."))
        clean = {
            "group_id": group["group_id"],
            "collection_field": group["collection_field"],
            "row_count": group["row_count"],
            "summary": "将遍历 %s 明细，循环填充 %s 行"
            % (group["collection_field"], group["row_count"]),
        }
        if detailed:
            rows = group["target_rows"]
            allowed_fields = group["allowed_fields"]
            if (
                not isinstance(group["relation_model"], str)
                or not group["relation_model"].strip()
                or not isinstance(rows, list)
                or len(rows) != group["row_count"]
                or not isinstance(allowed_fields, dict)
                or not allowed_fields
            ):
                raise ValidationError(_("Invalid mapping groups."))
            record_ids = group.get("record_ids")
            if record_ids is not None and (
                not isinstance(record_ids, list)
                or len(record_ids) != group["row_count"]
                or any(type(record_id) is not int or record_id < 1 for record_id in record_ids)
                or len(set(record_ids)) != len(record_ids)
            ):
                raise ValidationError(_("Invalid mapping group record references."))
            if group["collection_field"] == "selected_records" and record_ids is None:
                raise ValidationError(_("A selected-record mapping group must retain its source record IDs."))
            clean_rows = []
            expected_columns = None
            for index, row in enumerate(rows):
                if (
                    not isinstance(row, dict)
                    or set(row) != {"row_index", "targets"}
                    or type(row["row_index"]) is not int
                    or row["row_index"] != index
                    or not isinstance(row["targets"], list)
                    or not row["targets"]
                ):
                    raise ValidationError(_("Invalid mapping groups."))
                clean_targets = []
                columns = set()
                for item in row["targets"]:
                    if (
                        not isinstance(item, dict)
                        or set(item) != {"column_id", "element_id"}
                        or not isinstance(item["column_id"], str)
                        or not item["column_id"].isidentifier()
                        or not isinstance(item["element_id"], str)
                        or item["element_id"] not in manifest_ids
                        or item["element_id"] in occupied_targets
                        or item["column_id"] in columns
                    ):
                        raise ValidationError(_("Invalid mapping groups."))
                    columns.add(item["column_id"])
                    occupied_targets.add(item["element_id"])
                    clean_targets.append(dict(item))
                if expected_columns is None:
                    expected_columns = columns
                elif columns != expected_columns:
                    raise ValidationError(_("Invalid mapping groups."))
                clean_rows.append({"row_index": index, "targets": clean_targets})
            if any(
                not isinstance(name, str)
                or not re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){0,2}", name
                )
                or kind not in {"string", "number", "boolean"}
                for name, kind in allowed_fields.items()
            ):
                raise ValidationError(_("Invalid mapping groups."))
            if "sort_by" in group:
                sort_by = group["sort_by"]
                sort_direction = group["sort_direction"]
                if (
                    not isinstance(sort_by, str)
                    or sort_by not in allowed_fields
                    or sort_direction not in {"asc", "desc"}
                ):
                    raise ValidationError(_("Invalid mapping group ordering."))
            clean.update(
                {
                    "relation_model": group["relation_model"],
                    "target_rows": clean_rows,
                    "allowed_fields": dict(allowed_fields),
                }
            )
            if "sort_by" in group:
                clean.update({"sort_by": group["sort_by"], "sort_direction": group["sort_direction"]})
            if record_ids is not None:
                clean["record_ids"] = list(record_ids)
        normalized.append(clean)
        seen.add(group["group_id"])
    return normalized


def set_mapping_context(
    env,
    session_id,
    target_manifest,
    allowed_fields,
    mapping_groups=None,
    template_text=None,
    document_format=None,
    selected_record_ids=None,
    extra_authorized_fields=None,
):
    """Install server-owned TargetManifest/allowlist metadata for a session.

    This internal Python service is not exposed as an RPC route. It exists for
    trusted orchestration and deterministic test fixtures; browser input never
    supplies these values.
    """
    session = _owned_session(env, session_id)
    if not isinstance(target_manifest, list) or not isinstance(allowed_fields, dict):
        raise ValidationError(_("Invalid mapping context."))
    if document_format is not None and document_format not in {"xlsx", "docx"}:
        raise ValidationError(_("Invalid Office document format."))
    if extra_authorized_fields is None:
        extra_authorized_fields = []
    if (
        not isinstance(extra_authorized_fields, list)
        or len(extra_authorized_fields) > 64
        or any(not isinstance(name, str) or not name.strip() or len(name) > 255 for name in extra_authorized_fields)
        or len(set(extra_authorized_fields)) != len(extra_authorized_fields)
        or any(name not in allowed_fields for name in extra_authorized_fields)
    ):
        raise ValidationError(_("Invalid explicitly authorized field context."))
    groups = _validate_mapping_groups(mapping_groups, target_manifest)
    target_model = env[session.target_model]
    if selected_record_ids is None:
        selected_record_ids = [session.target_record_id]
    if (
        not isinstance(selected_record_ids, list)
        or not selected_record_ids
        or len(selected_record_ids) > 100
        or any(type(record_id) is not int or record_id < 1 for record_id in selected_record_ids)
        or len(set(selected_record_ids)) != len(selected_record_ids)
        or selected_record_ids[0] != session.target_record_id
    ):
        raise ValidationError(_("Invalid selected record context."))
    target_model.check_access("read")
    selected_records = target_model.browse(selected_record_ids).exists()
    if set(selected_records.ids) != set(selected_record_ids):
        raise AccessError(_("One or more selected records are unavailable."))
    selected_records.check_access("read")
    for record in selected_records:
        record.check_access("read")
    for group in groups:
        if "relation_model" not in group:
            continue
        if group["collection_field"] == "selected_records":
            if (
                group["relation_model"] != session.target_model
                or group.get("record_ids") != selected_record_ids
            ):
                raise ValidationError(_("A selected-record mapping group does not match its Session context."))
            continue
        relation = target_model._fields.get(group["collection_field"])
        if not relation or relation.type not in {"one2many", "many2many"}:
            raise ValidationError(_("A mapping group must use a relational collection field."))
        if "relation_model" in group and relation.comodel_name != group["relation_model"]:
            raise ValidationError(_("The mapping group model does not match its relation field."))
    proposal = {
        "schema_version": "m2.mapping-proposal.v1",
        "mappings": [],
        "clarifications": [],
        "skipped_targets": [],
    }
    report = validate_user_revision(proposal, [], target_manifest, allowed_fields)
    if report.status == "invalid":
        raise ValidationError(_("Invalid mapping context."))
    if template_text is not None and (
        not isinstance(template_text, list)
        or len(template_text) > 160
        or any(
            not isinstance(item, dict)
            or set(item) != {"element_id", "text"}
            or not isinstance(item["element_id"], str)
            or not isinstance(item["text"], str)
            or len(item["text"]) > 600
            for item in template_text
        )
    ):
        raise ValidationError(_("Invalid template text context."))
    context = {
        "target_manifest": target_manifest,
        "allowed_fields": allowed_fields,
        "manifest_metadata_version": 2,
        "selected_record_ids": selected_record_ids,
        "extra_authorized_fields": extra_authorized_fields,
    }
    if document_format is not None:
        context["document_format"] = document_format
    if template_text is not None:
        context["template_text"] = template_text
    if groups:
        context["mapping_groups"] = [
            {key: value for key, value in group.items() if key != "summary"}
            for group in groups
        ]
    session._set_context_from_service(
        json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    return {"session_id": session.id, "revision": session.revision}


def restore_proposal_revision(env, session_id, expected_revision, proposal_revision):
    """Restore a prior validated rules snapshot as a new Proposal revision.

    A historical revision is never made current by changing the revision
    counter backwards. It is reauthorized against the live Session context and
    saved as a new version under the same optimistic lock used by edits.
    """
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision != session.revision:
        raise ValidationError(_("MAPPING_REVISION_STALE: reload the current proposal before restoring."))
    if type(proposal_revision) is not int or proposal_revision < 1:
        raise ValidationError(_("Invalid Proposal revision."))
    try:
        history = json.loads(session.proposal_history_json or "[]")
        context = json.loads(session.context_json or "{}")
        current_rules = json.loads(session.mapping_rules_json or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError(_("The Proposal history is invalid.")) from exc
    if not isinstance(history, list) or not isinstance(context, dict):
        raise ValidationError(_("The Proposal history is invalid."))
    if proposal_revision == session.proposal_revision:
        return {
            "status": "unchanged",
            "session_id": session.id,
            "revision": session.revision,
            "proposal_revision": session.proposal_revision,
            "restored_from_proposal_revision": proposal_revision,
        }
    selected = next(
        (
            entry.get("mapping_rules")
            for entry in history
            if isinstance(entry, dict)
            and entry.get("proposal_revision") == proposal_revision
            and isinstance(entry.get("mapping_rules"), dict)
        ),
        None,
    )
    if selected is None:
        raise ValidationError(_("The requested Proposal revision is no longer available."))
    canonical = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    current = json.dumps(current_rules, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if canonical == current:
        return {
            "status": "unchanged",
            "session_id": session.id,
            "revision": session.revision,
            "proposal_revision": session.proposal_revision,
            "restored_from_proposal_revision": proposal_revision,
        }

    from .ai_orchestrator import (
        _approved_collection_field_types,
        _approved_field_types,
        _mapping_field_types,
    )

    _target, root_fields = _approved_field_types(
        env, session, context.get("allowed_fields", {})
    )
    groups = context.get("mapping_groups", [])
    group_fields = {
        group["group_id"]: _approved_collection_field_types(env, session, group)
        for group in groups
        if isinstance(group, dict) and "relation_model" in group
    }
    proposal_fields = _mapping_field_types(root_fields, groups, group_fields)
    if context.get("document_format") == "docx":
        # M1 DOCX writes text paragraphs. Scalar values are safely serialized
        # to text; authorization still uses their actual Odoo field types.
        proposal_fields = {name: "string" for name in proposal_fields}
    report = validate_proposal(
        selected,
        context.get("target_manifest", []),
        proposal_fields,
    )
    if not report.ready_for_review:
        raise ValidationError(_("The historical Proposal is no longer valid or authorized."))
    saved = session._save_mapping_from_service(
        canonical, expected_revision, "revision_pending"
    )
    return {
        **saved,
        "status": "restored",
        "proposal_revision": session.proposal_revision,
        "restored_from_proposal_revision": proposal_revision,
    }


def post_mapping_card(env, session_id):
    """Deprecated compatibility helper; mapping review now uses chat prose and file previews."""
    session = _owned_session(env, session_id)
    return session.thread_id.message_post(
        body=_("我已准备当前映射预览。请查看附件，并直接在聊天中描述需要修改的内容。"),
        llm_role="assistant",
    )


def get_mapping_status(env, session_id, expected_revision):
    """Return a minimal Session status without inspecting the template or records."""
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    result = {
        "session_id": session.id,
        "state": session.state,
        "revision": session.revision,
        "download_url": False,
    }
    if session.state == "completed":
        from .render_bridge import _render_result_url, _stable_request_uuid

        request_uuid = _stable_request_uuid(env, session)
        request = env["office.document.request"].search(
            [("request_uuid", "=", request_uuid)], limit=1
        )
        if request and request.output_attachment_id:
            request.check_access("read")
            request.output_attachment_id.check_access("read")
            result["download_url"] = _render_result_url(request.output_attachment_id.id)
    return result


def _template_display_labels(session, manifest):
    """Read bounded nearby labels transiently; never persist template text."""
    try:
        from office_core import inspect_document
        from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget
        from .ai_orchestrator import _target_label_context

        attachment = session.source_attachment_id
        attachment.check_access("read")
        inspected = inspect_document(
            attachment.raw or b"",
            attachment.name or "template.xlsx",
            attachment.mimetype or "application/octet-stream",
            _resource_budget(),
        )
        if inspected.format != "xlsx":
            return {}
        elements = [
            {"element_id": item.element_id, "text": item.value.strip()[:160]}
            for item in inspected.elements
            if item.kind == "cell" and isinstance(item.value, str) and item.value.strip()
        ][:300]
        contexts = _target_label_context(manifest, elements)
        result = {}
        for item in contexts:
            labels = item.get("nearby_labels") or []
            if labels:
                result[item["element_id"]] = labels[0]["text"]
        return result
    except Exception:
        # Card context remains available if an older/unsupported template
        # cannot be re-inspected; labels fall back to stable target IDs.
        return {}


def get_mapping_card_context(env, session_id, expected_revision):
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    rules, manifest, allowed_fields, groups = _load_mapping_data(session)
    if not isinstance(manifest, list) or not isinstance(allowed_fields, dict):
        raise ValidationError(_("The mapping context is invalid."))
    mapped = {item["element_id"]: item for item in rules.get("mappings", [])}
    group_targets = {}
    for group in groups:
        for row in group.get("target_rows", []):
            for target in row["targets"]:
                group_targets[target["element_id"]] = {
                    "group_id": group["group_id"],
                    "row_index": row["row_index"],
                    "column_id": target["column_id"],
                    "collection_field": group["collection_field"],
                    "label": "%s 第 %s 行 · %s (%s)"
                    % (
                        group["collection_field"],
                        row["row_index"] + 1,
                        target["column_id"],
                        target["element_id"],
                    ),
                }
    sample_values = {}
    try:
        from .ai_orchestrator import (
            _approved_collection_field_types,
            _approved_field_types,
            _retrieve_collection,
            _retrieve_record,
        )

        _target, permitted = _approved_field_types(env, session, allowed_fields)
        record_values = _retrieve_record(env, session, permitted)
        sample_values = {field_name: record_values.get(field_name) for field_name in permitted}
        for group in groups:
            if "relation_model" not in group:
                continue
            group_fields = _approved_collection_field_types(env, session, group)
            group_records = _retrieve_collection(env, session, group, group_fields)
            for field_name in group_fields:
                sample_values[f"{group['group_id']}::{field_name}"] = (
                    group_records[0].get(field_name) if group_records else None
                )
    except (AccessError, UserError, ValidationError):
        # Keep the card usable if the current user's ORM access prevents samples.
        sample_values = {}
    download_url = None
    if session.state == "completed":
        # A card message can be reopened after the rendering RPC committed.
        # Resolve the result from M1's idempotency key under this user's ACLs
        # so the completed state is not reduced to a stale-revision warning.
        from .render_bridge import _render_result_url, _stable_request_uuid

        request_uuid = _stable_request_uuid(env, session)
        request_record = env["office.document.request"].search(
            [("request_uuid", "=", request_uuid)], limit=1
        )
        if request_record and request_record.output_attachment_id:
            request_record.check_access("read")
            request_record.output_attachment_id.check("read")
            download_url = _render_result_url(request_record.output_attachment_id.id)
    template_labels = _template_display_labels(session, manifest)
    mapping_rows = [
        {
            "row_id": item["element_id"],
            "element_id": item["element_id"],
            "label": template_labels.get(item["element_id"])
            or group_targets.get(item["element_id"], {}).get("label", item["element_id"]),
            "required": item["required"],
            "source_field": mapped.get(item["element_id"], {}).get("source_field", ""),
            "clarification": next(
                (
                    clarification["question"]
                    for clarification in rules.get("clarifications", [])
                    if clarification.get("element_id") == item["element_id"]
                ),
                "",
            ),
            **group_targets.get(item["element_id"], {}),
        }
        for item in manifest
    ]
    mapping_groups = [
        {
            "group_id": group["group_id"],
            "collection_field": group["collection_field"],
            "row_count": group["row_count"],
            "summary": group["summary"],
        }
        for group in _validate_mapping_groups(groups, manifest)
    ]
    mapping_fields = dict(allowed_fields)
    for group in groups:
        mapping_fields.update(
            {
                f"{group['group_id']}::{field_name}": value_type
                for field_name, value_type in group.get("allowed_fields", {}).items()
            }
        )
    return {
        "session_id": session.id,
        "revision": session.revision,
        "state": session.state,
        "download_url": download_url,
        "stale": expected_revision != session.revision,
        "mapping_rows": mapping_rows,
        # Compatibility alias for callers predating the mapping_rows contract.
        "targets": mapping_rows,
        "mapping_groups": mapping_groups,
        "fields": [
            {
                "field_id": field_id,
                "label": (
                    env[session.target_model]._fields[field_id].string or field_id
                    if "::" not in field_id and field_id in env[session.target_model]._fields
                    else field_id
                ),
                "value_type": value_type,
                "sample": sample_values.get(field_id),
            }
            for field_id, value_type in sorted(mapping_fields.items())
        ],
        "clarifications": [
            item["question"]
            for item in rules.get("clarifications", [])
            if isinstance(item, dict) and isinstance(item.get("question"), str)
        ],
    }


def save_mapping_edits(env, session_id, expected_revision, edits):
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    if not isinstance(edits, list):
        raise ValidationError(_("Invalid mapping edits."))
    rules, manifest, allowed_fields, groups = _load_mapping_data(session)
    mapping_fields = dict(allowed_fields)
    for group in groups:
        mapping_fields.update(
            {
                f"{group['group_id']}::{field_name}": value_type
                for field_name, value_type in group.get("allowed_fields", {}).items()
            }
        )
    report = validate_user_revision(rules, edits, manifest, mapping_fields)
    if report.status == "invalid":
        raise ValidationError(_("One or more mapping choices are invalid."))

    edits_by_target = {item["element_id"]: dict(item) for item in edits}
    updated = dict(rules)
    updated["mappings"] = [
        edits_by_target.pop(item["element_id"], dict(item))
        for item in rules.get("mappings", [])
    ]
    updated["mappings"].extend(edits_by_target.values())
    edited_ids = {item["element_id"] for item in edits}
    updated["clarifications"] = [
        item for item in rules.get("clarifications", [])
        if item.get("element_id") not in edited_ids
    ]
    updated["skipped_targets"] = [
        item for item in rules.get("skipped_targets", []) if item not in edited_ids
    ]
    if "clear_targets" in updated:
        updated["clear_targets"] = [
            item for item in rules.get("clear_targets", []) if item not in edited_ids
        ]

    if session.state not in {"analyzing", "revision_pending", "confirmation_required"}:
        raise ValidationError(_("The mapping session cannot be edited in its current state."))
    new_state = "revision_pending"

    return session._save_mapping_from_service(
        json.dumps(updated, ensure_ascii=False, separators=(",", ":")),
        expected_revision,
        new_state,
    )


def confirm_mapping(env, session_id, expected_revision):
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    rules, manifest, allowed_fields, groups = _load_mapping_data(session)
    mapping_fields = dict(allowed_fields)
    for group in groups:
        mapping_fields.update(
            {
                f"{group['group_id']}::{field_name}": value_type
                for field_name, value_type in group.get("allowed_fields", {}).items()
            }
        )
    report = validate_user_revision(rules, [], manifest, mapping_fields)
    if not report.ready_for_review:
        raise ValidationError(_("Complete all required mapping choices before confirming."))
    if session.state != "confirmation_required" or session.revision != expected_revision:
        raise ValidationError(_("MAPPING_REVISION_STALE: refresh the current preview and confirm again."))
    if session.preview_proposal_revision != session.proposal_revision:
        raise ValidationError(_("The current preview does not match the saved proposal."))
    return {
        "session_id": session.id,
        "state": session.state,
        "revision": session.revision,
        "proposal_revision": session.proposal_revision,
    }
