import logging

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)
_ALLOWED_FIELDS = {"partner_id.name", "amount_total"}


class TVOfficeM2Controller(http.Controller):
    @http.route(
        "/tv_office_m2_owl/validate_selection",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def validate_selection(self, field_key=None):
        accepted = isinstance(field_key, str) and field_key in _ALLOWED_FIELDS
        _logger.info(
            "TV_M2_003_RPC uid=%s field_key=%s accepted=%s",
            request.env.uid,
            field_key if isinstance(field_key, str) else "<invalid-type>",
            accepted,
        )
        return {"accepted": accepted, "field_key": field_key if accepted else False}
