from odoo import http, _
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from ..services.mapping_service import (
    confirm_mapping,
    get_mapping_card_context,
    save_mapping_edits,
    transition_session,
)


_UNAVAILABLE = "The mapping session is unavailable."


class OfficeMappingController(http.Controller):
    @http.route(
        "/office_engine_m2/mapping/context",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def mapping_context(self, session_id=None, expected_revision=None, **extra):
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
        return get_mapping_card_context(env, session.id, expected_revision)

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
        return confirm_mapping(env, session.id, expected_revision)

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
        return transition_session(env, session.id, "cancelled", expected_revision)
