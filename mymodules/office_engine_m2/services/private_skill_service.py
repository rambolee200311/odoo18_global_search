"""Current-user services for private Office mapping Skills."""

from __future__ import annotations

import json
import logging
import re

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import validate_proposal

from .mapping_service import _load_mapping_data, _owned_session
from .render_bridge import _stable_request_uuid


_logger = logging.getLogger(__name__)
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_CREATE_FROM_SERVICE = "_office_engine_m2_private_skill_create"
_UNAVAILABLE = "The private Skill is unavailable."


def _inspect_session_template(env, session):
    session.thread_id.check_access("read")
    session.source_message_id.check_access("read")
    session.source_attachment_id.check("read")
    if (
        session.thread_id.user_id.id != env.uid
        or session.company_id.id not in env.companies.ids
        or session.source_message_id.model != "llm.thread"
        or session.source_message_id.res_id != session.thread_id.id
        or session.source_attachment_id not in session.source_message_id.attachment_ids
    ):
        raise AccessError(_(_UNAVAILABLE))
    inspection = env["office.document.request"]._inspect_chat_attachment(
        session.source_attachment_id,
        session.thread_id,
        session.source_message_id,
    )
    fingerprint = inspection.get("template_sha256")
    if not isinstance(fingerprint, str) or not _FINGERPRINT.fullmatch(fingerprint):
        raise UserError(_("The server could not verify the template fingerprint."))
    return fingerprint


def _generated_request(env, session, fingerprint):
    request_uuid = _stable_request_uuid(env, session)
    request = env["office.document.request"].search(
        [("request_uuid", "=", request_uuid)], limit=1
    )
    if not request:
        raise ValidationError(_("A successfully delivered M1 request is required."))
    request.check_access("read")
    if (
        request.owner_id.id != env.uid
        or request.state != "generated"
        or request.input_sha256 != fingerprint
        or request.source_attachment_id != session.source_attachment_id
        or request.thread_id != session.thread_id
        or request.input_message_id != session.source_message_id
        or not request.output_attachment_id
    ):
        raise ValidationError(_("A successfully delivered M1 request is required."))
    request.output_attachment_id.check("read")
    if (
        request.output_attachment_id.res_model != request._name
        or request.output_attachment_id.res_id != request.id
    ):
        raise AccessError(_(_UNAVAILABLE))
    return request


def _authorized_mapping_fields(env, session, configured_fields, groups):
    from .ai_orchestrator import (
        _approved_collection_field_types,
        _approved_field_types,
        _mapping_field_types,
        _retrieve_collection,
        _retrieve_record,
    )

    _target, root_fields = _approved_field_types(env, session, configured_fields)
    group_fields = {}
    for group in groups:
        if "relation_model" not in group:
            continue
        fields = _approved_collection_field_types(env, session, group)
        # Re-read the collection under the current user's access. This is a
        # permission/shape check only; no value is stored in the Skill.
        _retrieve_collection(env, session, group, fields)
        group_fields[group["group_id"]] = fields
    current_values = _retrieve_record(env, session, list(root_fields))
    if not isinstance(current_values, dict):
        raise UserError(_("The current target record could not be read."))
    return _mapping_field_types(root_fields, groups, group_fields)


def _validated_session_rules(env, session):
    rules, manifest, configured_fields, groups = _load_mapping_data(session)
    if not isinstance(manifest, list) or not isinstance(configured_fields, dict):
        raise ValidationError(_("The mapping rules are unavailable."))
    allowed_fields = _authorized_mapping_fields(env, session, configured_fields, groups)
    report = validate_proposal(rules, manifest, allowed_fields)
    if not report.ready_for_review:
        raise ValidationError(_("The saved mapping is no longer complete or authorized."))
    return rules, manifest, allowed_fields


def _clean_name(name):
    if not isinstance(name, str):
        raise ValidationError(_("Enter a name for this private Skill."))
    name = name.strip()
    if not name or len(name) > 128 or any(ord(char) < 32 for char in name):
        raise ValidationError(_("Enter a name between 1 and 128 characters."))
    return name


def save_from_success(env, session_id, expected_revision, name):
    """Save only rules from the current user's completed and delivered M1 run."""
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    if session.revision != expected_revision:
        raise ValidationError(_("MAPPING_REVISION_STALE: refresh the completed mapping card."))
    if session.state != "completed" or session.confirmed_revision < 1:
        raise ValidationError(_("A successfully completed mapping is required to save a Skill."))
    name = _clean_name(name)
    fingerprint = _inspect_session_template(env, session)
    _generated_request(env, session, fingerprint)
    rules, _manifest, _allowed = _validated_session_rules(env, session)
    normalized_rules = json.dumps(rules, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    # A retry of the same save action is idempotent. The domain runs as the
    # current user, so Record Rules never expose another owner's Skill.
    existing = env["office.export.skill"].search(
        [
            ("owner_id", "=", env.uid),
            ("company_id", "=", session.company_id.id),
            ("template_fingerprint", "=", fingerprint),
            ("model_name", "=", session.target_model),
            ("name", "=", name),
            ("state", "=", "active"),
        ],
        order="id",
    )
    for skill in existing:
        if json.dumps(
            json.loads(skill.mapping_rules_json), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ) == normalized_rules:
            return {"skill_id": skill.id, "name": skill.name, "already_exists": True}

    values = {
        "name": name,
        "owner_id": env.uid,
        "company_id": session.company_id.id,
        "template_fingerprint": fingerprint,
        "model_name": session.target_model,
        "mapping_rules_json": normalized_rules,
        "state": "active",
        "revision": 1,
    }
    # This is the sole narrow elevation for Skill creation. All session,
    # request, attachment, owner/company, mapping, and output checks above ran
    # in the original user environment. Skill reads never use sudo.
    skill = env["office.export.skill"].sudo().with_context(
        **{_CREATE_FROM_SERVICE: True}
    ).create(values)
    return {"skill_id": skill.id, "name": skill.name, "already_exists": False}


def _candidate_domain(env, session, fingerprint):
    return [
        ("owner_id", "=", env.uid),
        ("company_id", "=", session.company_id.id),
        ("template_fingerprint", "=", fingerprint),
        ("model_name", "=", session.target_model),
        ("state", "=", "active"),
    ]


def _target_summary(env, session):
    model = env[session.target_model]
    model.check_access("read")
    target = model.browse(session.target_record_id).exists()
    if not target:
        raise AccessError(_(_UNAVAILABLE))
    target.check_access("read")
    return target.display_name


def _prepare_candidate(env, session, skill):
    _current_rules, manifest, configured_fields, groups = _load_mapping_data(session)
    allowed_fields = _authorized_mapping_fields(env, session, configured_fields, groups)
    try:
        saved_rules = json.loads(skill.mapping_rules_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError(_("The private Skill rules are invalid.")) from exc
    report = validate_proposal(saved_rules, manifest, allowed_fields)
    if not report.ready_for_review:
        raise ValidationError(_("The private Skill is no longer compatible with this request."))
    return saved_rules


def _post_skill_card(env, session, skill=None, candidates=None):
    if skill:
        body = _("已匹配私有技能“%(name)s”（模型 %(model)s）。我正在按当前记录生成预览；请检查后再确认。", name=skill.name, model=skill.model_name)
    elif candidates:
        names = "、".join(item.name for item in candidates)
        body = _("匹配到多个私有技能：%(names)s。请先缩小模板/模型范围后重试。", names=names)
    else:
        body = _("正在使用已验证的私有技能准备本次导出预览。")
    message = session.thread_id.message_post(
        body=body,
        llm_role="assistant",
    )
    return message


def _apply_skill(env, session, skill):
    rules = _prepare_candidate(env, session, skill)
    result = session._save_mapping_from_service(
        json.dumps(rules, ensure_ascii=False, separators=(",", ":")),
        session.revision,
        "revision_pending",
    )
    session.invalidate_recordset(["revision", "state", "mapping_rules_json"])
    return result


def match_for_request(
    env,
    session_id,
    template_fingerprint=None,
    model_name=None,
    *,
    selected_skill_id=None,
    post_card=True,
):
    """Resolve a private Skill using server-derived template/model context.

    Optional fingerprint/model parameters are consistency assertions only;
    client-provided values can never become the matching source of truth.
    """
    session = _owned_session(env, session_id)
    if session.state != "analyzing":
        return {"status": "not_applicable", "session_id": session.id}
    server_fingerprint = _inspect_session_template(env, session)
    if template_fingerprint is not None and template_fingerprint != server_fingerprint:
        raise ValidationError(_("The supplied template fingerprint did not match the uploaded file."))
    if model_name is not None and model_name != session.target_model:
        raise ValidationError(_("The supplied target model did not match the mapping session."))

    candidates = env["office.export.skill"].search(
        _candidate_domain(env, session, server_fingerprint), order="id"
    )
    if selected_skill_id is not None:
        if type(selected_skill_id) is not int or selected_skill_id < 1:
            raise ValidationError(_("Invalid private Skill selection."))
        candidates = candidates.filtered(lambda item: item.id == selected_skill_id)
        if len(candidates) != 1:
            raise AccessError(_(_UNAVAILABLE))
    elif not candidates:
        return {"status": "none", "session_id": session.id}
    elif len(candidates) > 1:
        message = _post_skill_card(env, session, candidates=candidates)
        return {
            "status": "multiple",
            "session_id": session.id,
            "revision": session.revision,
            "message_id": message.id,
            "candidates": [
                {"skill_id": item.id, "name": item.name, "model_name": item.model_name}
                for item in candidates
            ],
        }

    skill = candidates
    try:
        _prepare_candidate(env, session, skill)
    except (AccessError, UserError, ValidationError):
        if selected_skill_id is not None:
            raise
        return {"status": "none", "session_id": session.id}

    _apply_skill(env, session, skill)
    from .render_bridge import render_preview

    preview = render_preview(env, session.id, session.revision)
    _logger.info("SKILL_MATCHED: %s", skill.id)
    message = None
    if post_card:
        session.invalidate_recordset(["preview_attachment_id", "revision"])
        message = session.thread_id.message_post(
            body=_(
                "已匹配私有技能“%(name)s”。预览已通过回读校验，请检查附件；确认后回复‘确认’生成正式文件。",
                name=skill.name,
            ),
            llm_role="assistant",
            author_id=False,
            attachment_ids=[preview["preview_attachment_id"]],
        )
    return {
        "status": "matched",
        "session_id": session.id,
        "revision": session.revision,
        "message_id": message.id if message else False,
        "skill_id": skill.id,
        "skill_name": skill.name,
        "model_name": skill.model_name,
        "target_summary": _target_summary(env, session),
        "requires_confirmation": True,
        "preview_attachment_id": preview["preview_attachment_id"],
    }


def select_skill_for_request(env, session_id, expected_revision, skill_id):
    session = _owned_session(env, session_id)
    if (
        type(expected_revision) is not int
        or expected_revision < 1
        or session.state != "analyzing"
        or session.revision != expected_revision
    ):
        raise ValidationError(_("MAPPING_REVISION_STALE: refresh the Skill choices."))
    result = match_for_request(
        env, session.id, selected_skill_id=skill_id, post_card=False
    )
    return result


def skill_context_for_request(env, session_id, skill_id=None):
    session = _owned_session(env, session_id)
    fingerprint = _inspect_session_template(env, session)
    if skill_id is not None:
        if type(skill_id) is not int or skill_id < 1:
            raise ValidationError(_("Invalid private Skill reference."))
        skill = env["office.export.skill"].search(
            _candidate_domain(env, session, fingerprint) + [("id", "=", skill_id)], limit=1
        )
        if not skill:
            raise AccessError(_(_UNAVAILABLE))
        _prepare_candidate(env, session, skill)
        return {
            "skill_id": skill.id,
            "name": skill.name,
            "model_name": skill.model_name,
            "target_summary": _target_summary(env, session),
            "requires_confirmation": True,
        }

    saved = []
    if session.state == "completed":
        # This is presentation-only state for an already completed request.
        # Do not make reopening the card depend on the current data-policy
        # environment: authorization is rechecked when a Skill is matched and
        # before any new M1 render. The saved Skill still contains rules only,
        # never values, and the lookup remains owner/company scoped.
        try:
            completed_rules = json.loads(session.mapping_rules_json)
        except (TypeError, json.JSONDecodeError):
            completed_rules = None
        canonical = (
            json.dumps(
                completed_rules,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            if isinstance(completed_rules, dict)
            else None
        )
        skills = env["office.export.skill"].search(
            _candidate_domain(env, session, fingerprint), order="id"
        )
        saved = [
            {"skill_id": item.id, "name": item.name}
            for item in skills
            if json.dumps(
                json.loads(item.mapping_rules_json),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ) == canonical
        ]
    return {"saved_skills": saved}
