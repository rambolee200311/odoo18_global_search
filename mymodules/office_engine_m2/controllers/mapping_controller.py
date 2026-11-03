from odoo import http, _
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from ..services.mapping_service import (
    get_mapping_card_context,
    get_mapping_status,
    save_mapping_edits,
    transition_session,
)
from ..services.private_skill_service import (
    save_from_success,
    select_skill_for_request,
    skill_context_for_request,
)


_UNAVAILABLE = "The mapping session is unavailable."


class OfficeMappingController(http.Controller):
    @http.route(
        "/office_engine_m2/mapping/status",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def mapping_status(self, session_id=None, expected_revision=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid or session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid mapping status request."))
        return get_mapping_status(env, session.id, expected_revision)

    @http.route(
        "/office_engine_m2/mapping/start",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def start_mapping(self, session_id=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid:
            raise AccessError(_(_UNAVAILABLE))
        if session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid mapping start request."))
        raise ValidationError(_("Mapping is started through the native Assistant tool loop."))

    @http.route(
        "/office_engine_m2/mapping/context",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def mapping_context(self, session_id=None, expected_revision=None, skill_id=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid:
            raise AccessError(_(_UNAVAILABLE))
        if session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid mapping context request."))
        result = get_mapping_card_context(env, session.id, expected_revision)
        if skill_id is not None:
            result["skill_match"] = skill_context_for_request(env, session.id, skill_id)
        elif session.state == "completed":
            result["saved_skills"] = skill_context_for_request(env, session.id).get("saved_skills", [])
        return result

    @http.route(
        "/office_engine_m2/mapping/skill_context",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def mapping_skill_context(self, session_id=None, expected_revision=None, skill_id=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid or session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra or type(expected_revision) is not int or expected_revision != session.revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: refresh the Skill card."))
        return skill_context_for_request(env, session.id, skill_id)

    @http.route(
        "/office_engine_m2/mapping/save_skill",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def save_skill(self, session_id=None, expected_revision=None, name=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid or session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid private Skill save request."))
        return save_from_success(env, session.id, expected_revision, name)

    @http.route(
        "/office_engine_m2/mapping/select_skill",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def select_skill(self, session_id=None, expected_revision=None, skill_id=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid or session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid private Skill selection request."))
        return select_skill_for_request(env, session.id, expected_revision, skill_id)

    @http.route(
        "/office_engine_m2/mapping/update",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def update_mapping(self, session_id=None, expected_revision=None, edits=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid:
            raise AccessError(_(_UNAVAILABLE))
        if session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid mapping update request."))
        return save_mapping_edits(env, session.id, expected_revision, edits)

    @http.route(
        "/office_engine_m2/mapping/confirm",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def confirm_mapping_session(self, session_id=None, expected_revision=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid:
            raise AccessError(_(_UNAVAILABLE))
        if session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid mapping confirmation request."))
        raise AccessError(_("Final generation requires explicit confirmation in the native chat."))

    @http.route(
        "/office_engine_m2/mapping/cancel",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def cancel_mapping_session(self, session_id=None, expected_revision=None, **extra):
        env = request.env
        session = env["office.mapping.session"].browse(session_id).exists()
        if not session:
            raise AccessError(_(_UNAVAILABLE))
        session.check_access("read")
        if session.owner_id.id != env.uid:
            raise AccessError(_(_UNAVAILABLE))
        if session.company_id.id not in env.companies.ids:
            raise AccessError(_(_UNAVAILABLE))
        if extra:
            raise ValidationError(_("Invalid mapping cancellation request."))
        return transition_session(env, session.id, "failed", expected_revision)
