"""Safe internal handling of supported Office chat attachments."""

import logging
import os

from markupsafe import Markup
from odoo import _, models
from odoo.exceptions import AccessError, UserError

from ..services import inspect_attachment_identity


_logger = logging.getLogger(__name__)
_REJECT_MESSAGE = _(
    "The Office attachment is invalid, unsupported, or could not be safely inspected. "
    "It was not sent to the AI provider."
)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def _office_engine_attachment_header(self, attachment):
        """Return at most 2048 bytes through the user's Odoo filestore record."""
        attachment.check("read")
        if attachment.file_size <= 0:
            return b""
        if not attachment.store_fname:
            # Do not materialize a database-backed payload merely to check its
            # signature. Office candidates without bounded header access fail closed.
            return None
        filestore = os.path.realpath(attachment._filestore())
        path = os.path.realpath(attachment._full_path(attachment.store_fname))
        if os.path.commonpath((filestore, path)) != filestore:
            raise OSError("Attachment storage path is outside the filestore")
        with open(path, "rb") as content:
            return content.read(2048)

    def _office_engine_classify_attachments(self, attachments):
        """Return Office candidates and reject declaration/signature conflicts."""
        office = self.env["ir.attachment"]
        for attachment in attachments:
            attachment.check("read")
            header = self._office_engine_attachment_header(attachment)
            identity = inspect_attachment_identity(
                attachment.name,
                attachment.mimetype,
                header or b"",
                attachment.file_size,
            )
            if header is None and identity.is_office_candidate:
                raise UserError(_REJECT_MESSAGE)
            if identity.is_mismatch:
                raise UserError(_REJECT_MESSAGE)
            if identity.is_office_candidate:
                office |= attachment
        return office

    def _office_engine_message_has_office(self, message):
        try:
            return bool(self._office_engine_classify_attachments(message.attachment_ids))
        except (AccessError, OSError, UserError, ValueError):
            # Never include an attachment with an unverifiable Office-like
            # declaration in a Provider context.
            return True

    def _office_engine_messages_without_office(self, messages):
        return messages.filtered(lambda message: not self._office_engine_message_has_office(message))

    def _office_engine_generate_inspection(self, user_message_body, attachment_ids):
        """Accept, inspect, and summarize Office files without Provider dispatch."""
        if isinstance(attachment_ids, int) and not isinstance(attachment_ids, bool):
            attachment_ids = [attachment_ids]
        else:
            attachment_ids = list(attachment_ids)
        with self._generation_lock():
            attachments = self.env["ir.attachment"].browse(list(attachment_ids)).exists()
            if len(attachments) != len(set(attachment_ids)):
                error = UserError(_REJECT_MESSAGE)
                _error_message, event = self._post_error_message(error, title=_("Attachment rejected"))
                yield event
                return _error_message
            office = self._office_engine_classify_attachments(attachments)
            if not office:
                return None

            message = self.message_post(
                body=user_message_body or "",
                llm_role="user",
                author_id=self.env.user.partner_id.id,
                attachment_ids=attachments.ids,
            )
            yield {"type": "message_create", "message": message.to_store_format()}

            try:
                if len(office) != 1 or len(attachments) != 1:
                    raise UserError(_("Please upload one Office file per chat message."))
                source = office.ensure_one()
                filename = (source.name or "").lower()
                if filename.endswith((".xlsm", ".xltm", ".docm", ".dotm", ".pptm", ".potm", ".ppsm")):
                    raise UserError(_("Macro-enabled Office files are not supported."))
                summary = self.env["office.document.request"]._inspect_chat_attachment(
                    source, self, message
                )
            except (AccessError, UserError):
                message.write({"is_error": True})
                error = UserError(_REJECT_MESSAGE)
                _error_message, event = self._post_error_message(error, title=_("Attachment rejected"))
                yield event
                return _error_message
            except Exception as exc:
                message.write({"is_error": True})
                _logger.warning(
                    "Office chat inspection rejected attachment; thread_id=%s attachment_id=%s error_type=%s",
                    self.id,
                    source.id if "source" in locals() else 0,
                    type(exc).__name__,
                )
                error = UserError(_REJECT_MESSAGE)
                _error_message, event = self._post_error_message(error, title=_("Attachment rejected"))
                yield event
                return _error_message

            sheet_names = ", ".join(summary["sheet_names"]) or _("not applicable")
            result = _(
                "文件已接收并完成安全结构检查。格式：%(format)s；工作表：%(sheets)s；"
                "识别到的内容项：%(elements)s；公式：%(formulas)s。"
                "文件内容没有发送给 AI Provider；当前版本尚未执行字段映射或生成填充文件。",
                format=summary["format"],
                sheets=sheet_names,
                elements=summary["element_count"],
                formulas=summary["formula_count"],
            )
            assistant = self.message_post(
                body=Markup.escape(result), llm_role="assistant", author_id=False
            )
            yield {"type": "message_create", "message": assistant.to_store_format()}
            return assistant

    def generate(self, user_message_body=None, attachment_ids=None, **kwargs):
        """Route verified Office uploads to internal inspection before Provider calls."""
        self.ensure_one()
        if attachment_ids:
            if isinstance(attachment_ids, int) and not isinstance(attachment_ids, bool):
                attachment_ids = [attachment_ids]
            else:
                attachment_ids = list(attachment_ids)
            try:
                attachments = self.env["ir.attachment"].browse(list(attachment_ids)).exists()
                office = self._office_engine_classify_attachments(attachments)
            except (AccessError, OSError, UserError, ValueError):
                _error_message, event = self._post_error_message(
                    UserError(_REJECT_MESSAGE), title=_("Attachment rejected")
                )
                yield event
                return _error_message
            if office:
                yield from self._office_engine_generate_inspection(
                    user_message_body, attachment_ids
                )
                return
        yield from super().generate(user_message_body, attachment_ids=attachment_ids, **kwargs)

    def get_llm_messages(self, limit=25):
        """Keep Office file messages out of every Provider context."""
        messages = super().get_llm_messages(limit=limit)
        return self._office_engine_messages_without_office(messages)

    def _check_unsupported_attachments(self, message=None):
        self.ensure_one()
        messages = message if message else self._get_context_messages()
        self._office_engine_classify_attachments(
            messages.mapped("attachment_ids")
        )
        filtered = self._office_engine_messages_without_office(messages)
        if not filtered:
            return []
        return super()._check_unsupported_attachments(filtered)

    def _prepare_chat_kwargs(self, message_history, use_streaming):
        self.ensure_one()
        safe_history = self._office_engine_messages_without_office(message_history)
        return super()._prepare_chat_kwargs(safe_history, use_streaming)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _extras_to_store(self, store, format_reply):
        super()._extras_to_store(store, format_reply)
        for message in self:
            if message.model == "llm.thread" and message.is_error:
                store.add(message, {"is_error": True})
