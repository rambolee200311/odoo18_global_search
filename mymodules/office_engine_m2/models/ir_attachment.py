"""Enforce private, immutable attachment binding for workbook versions."""

from odoo import _, api, models
from odoo.exceptions import AccessError

from .office_workbook_version import _VERSION_MUTATION


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _office_workbook_version_records(self):
        directly_bound = self.filtered(
            lambda attachment: attachment.res_model == "office.workbook.version"
            and bool(attachment.res_id)
        )
        final_delivery = self.env["office.workbook.version"].search(
            [("final_attachment_id", "in", self.ids)]
        ).mapped("final_attachment_id")
        return directly_bound | final_delivery

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("res_model") != "office.workbook.version":
                continue
            if not _VERSION_MUTATION.get():
                raise AccessError(_("Workbook version attachments can only be created by the version service."))
            res_id = vals.get("res_id")
            if isinstance(res_id, bool) or not isinstance(res_id, int) or res_id < 1:
                raise AccessError(_("The workbook version is unavailable."))
            version = self.env["office.workbook.version"].browse(res_id).exists()
            if not version:
                raise AccessError(_("The workbook version is unavailable."))
            version.check_access("write")
            if (
                version.owner_id.id != self.env.uid
                or vals.get("public") is not False
                or vals.get("type") != "binary"
                or vals.get("url")
                or vals.get("company_id") != version.company_id.id
            ):
                raise AccessError(_("Workbook version attachments must be private and Session-scoped."))
            version.thread_id.check_access("read")
        return super().create(vals_list)

    def write(self, vals):
        if self._office_workbook_version_records() or vals.get("res_model") == "office.workbook.version":
            raise AccessError(_("Workbook version attachments are immutable."))
        return super().write(vals)

    def unlink(self):
        if self._office_workbook_version_records():
            raise AccessError(_("Workbook version attachments cannot be deleted."))
        return super().unlink()
