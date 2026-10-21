"""Keep generated Office outputs immutable and private after delivery."""

from odoo import _, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _office_engine_output_records(self):
        return self.filtered(
            lambda attachment: attachment.res_model == "office.document.request" and bool(attachment.res_id)
        )

    def write(self, vals):
        if self._office_engine_output_records() and not self.env.su:
            raise AccessError(_("Generated Office result attachments are immutable."))
        return super().write(vals)

    def unlink(self):
        if self._office_engine_output_records() and not self.env.su:
            raise AccessError(_("Generated Office result attachments cannot be deleted."))
        return super().unlink()
