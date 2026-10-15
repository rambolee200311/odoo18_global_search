from odoo import api, fields, models

class AuditEvent(models.Model):
    _name = "wd.gs.audit.event"
    _description = "Global Search Configuration Audit Event"
    _order = "create_date desc, id desc"

    action = fields.Selection(
        [
            ("publish", "Publish"),
            ("retire", "Retire"),
            ("reject", "Reject"),
            ("stage", "Stage"),
            ("apply", "Apply"),
            ("apply_rejected", "Apply Rejected"),
            ("invalidate", "Invalidate"),
            ("upgrade", "Upgrade"),
        ],
        required=True,
    )
    domain_id = fields.Many2one("wd.gs.config.domain", ondelete="set null", index=True)
    version_id = fields.Many2one("wd.gs.config.version", ondelete="set null", index=True)
    previous_checksum = fields.Char(readonly=True)
    checksum = fields.Char(readonly=True)
    error_code = fields.Char(readonly=True)
    message = fields.Text(readonly=True)
    request_id = fields.Char(readonly=True)
    user_id = fields.Many2one("res.users", readonly=True, default=lambda self: self.env.user)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("request_id", self.env.context.get("request_id"))
            vals.setdefault("user_id", self.env.user.id)
        return super().create(vals_list)
