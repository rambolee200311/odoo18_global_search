import json

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import validate_user_revision


_UNAVAILABLE = "The mapping session context is unavailable."
_MAX_MAPPING_GROUP_ROWS = 50


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
        or attachment not in message.attachment_ids
    ):
        raise AccessError(_(_UNAVAILABLE))
    if attachment.company_id and attachment.company_id not in env.companies:
        raise AccessError(_(_UNAVAILABLE))

    if target_model not in env.registry.models:
        raise AccessError(_(_UNAVAILABLE))
    target_model_recordset = env[target_model]
    target_model_recordset.browse().check_access("read")
    target = target_model_recordset.browse(target_record_id).exists()
    if not target:
        raise AccessError(_(_UNAVAILABLE))
    target.check_access("read")
    if "company_id" in target._fields and target.company_id and target.company_id not in env.companies:
        raise AccessError(_(_UNAVAILABLE))
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
        or set(context) - {"target_manifest", "allowed_fields", "mapping_groups"}
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
        detailed = set(group) == {
            "group_id", "collection_field", "relation_model", "row_count", "target_rows", "allowed_fields"
        }
        if not (simple or detailed):
            raise ValidationError(_("Invalid mapping groups."))
        if (
            not isinstance(group["group_id"], str)
            or not group["group_id"].isidentifier()
            or len(group["group_id"]) > 64
            or not isinstance(group["collection_field"], str)
            or not group["collection_field"].isidentifier()
            or type(group["row_count"]) is not int
            or not 1 <= group["row_count"] <= _MAX_MAPPING_GROUP_ROWS
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
                or not name.isidentifier()
                or kind not in {"string", "number", "boolean"}
                for name, kind in allowed_fields.items()
            ):
                raise ValidationError(_("Invalid mapping groups."))
            clean.update(
                {
                    "relation_model": group["relation_model"],
                    "target_rows": clean_rows,
                    "allowed_fields": dict(allowed_fields),
                }
            )
        normalized.append(clean)
        seen.add(group["group_id"])
    return normalized


def set_mapping_context(env, session_id, target_manifest, allowed_fields, mapping_groups=None):
    """Install server-owned TargetManifest/allowlist metadata for a session.

    This internal Python service is not exposed as an RPC route. It exists for
    trusted orchestration and deterministic test fixtures; browser input never
    supplies these values.
    """
    session = _owned_session(env, session_id)
    if not isinstance(target_manifest, list) or not isinstance(allowed_fields, dict):
        raise ValidationError(_("Invalid mapping context."))
    groups = _validate_mapping_groups(mapping_groups, target_manifest)
    target_model = env[session.target_model]
    for group in groups:
        if "relation_model" not in group:
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
    context = {"target_manifest": target_manifest, "allowed_fields": allowed_fields}
    if groups:
        context["mapping_groups"] = [
            {key: value for key, value in group.items() if key != "summary"}
            for group in groups
        ]
    session._set_context_from_service(
        json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    return {"session_id": session.id, "revision": session.revision}


def post_mapping_card(env, session_id):
    """Post a server-authored card reference without persisting business data."""
    session = _owned_session(env, session_id)
    return session.thread_id.message_post(
        body=_("Review the proposed document mapping."),
        llm_role="assistant",
        body_json={
            "office_mapping_card": {
                "type": "office_mapping_card_v1",
                "session_id": session.id,
                "revision": session.revision,
            }
        },
    )


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
        # The card remains usable for editing; without an approved data policy
        # no sample values are sent to the browser.
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
    mapping_rows = [
        {
            "row_id": item["element_id"],
            "element_id": item["element_id"],
            "label": group_targets.get(item["element_id"], {}).get("label", item["element_id"]),
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
                "label": field_id,
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

    if session.state == "collecting":
        new_state = "awaiting_confirmation" if report.ready_for_review else "needs_clarification"
    elif session.state == "needs_clarification":
        new_state = "editing" if report.ready_for_review else "needs_clarification"
    elif session.state == "awaiting_confirmation":
        new_state = "editing"
    elif session.state == "editing":
        new_state = "editing" if report.ready_for_review else "needs_clarification"
    else:
        raise ValidationError(_("The mapping session cannot be edited in its current state."))

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
    return session._confirm_mapping_from_service(expected_revision)
