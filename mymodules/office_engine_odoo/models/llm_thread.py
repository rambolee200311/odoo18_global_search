"""Safe internal handling of supported Office chat attachments."""

import logging
import os
from pathlib import Path

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

    def generate(self, user_message_body=None, attachment_ids=None, **kwargs):
        """Reject unsafe Office uploads, then let the native Assistant process them."""
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
                unsafe_suffixes = (".xlsm", ".xltm", ".docm", ".dotm", ".pptm", ".potm", ".ppsm")
                if any(Path(item.name or "").suffix.lower() in unsafe_suffixes for item in office):
                    error_message, event = self._post_error_message(
                        UserError(_("Macro-enabled Office files are not supported.")),
                        title=_("Attachment rejected"),
                    )
                    yield event
                    return error_message
                if any(item.file_size <= 0 or item.file_size > 32 * 1024 * 1024 for item in office):
                    error_message, event = self._post_error_message(
                        UserError(_("The Office attachment is empty or exceeds the file size limit.")),
                        title=_("Attachment rejected"),
                    )
                    yield event
                    return error_message
        yield from super().generate(user_message_body, attachment_ids=attachment_ids, **kwargs)

    def get_llm_messages(self, limit=25):
        """Keep the native history intact; mail.message serialization strips file payloads."""
        return super().get_llm_messages(limit=limit)

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
        return super()._prepare_chat_kwargs(message_history, use_streaming)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def openai_format_message(self, is_multimodal=False, is_audio_model=False):
        """Keep file-only Office uploads visible without serializing their bytes.

        The normal OpenAI serializer correctly omits Office binaries, but that
        also made an upload with an empty composer body serialize to ``None``.
        In that case the model received no user turn at all. Preserve a small
        filename-only cue so the native assistant can ask what to do or call
        the Office context tool.
        """
        self.ensure_one()
        formatted = super().openai_format_message(
            is_multimodal=is_multimodal,
            is_audio_model=is_audio_model,
        )
        if formatted is not None or self.llm_role != "user" or not self.attachment_ids:
            return formatted

        office_attachments = self.env["ir.attachment"]
        for attachment in self.attachment_ids:
            name = (attachment.name or "").lower()
            mimetype = (attachment.mimetype or "").lower().split(";", 1)[0]
            if name.endswith((".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".docm", ".pptx", ".ppt")) or mimetype in {
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            }:
                office_attachments |= attachment

        if not office_attachments:
            return formatted

        filenames = ", ".join(office_attachments.mapped("name"))
        return {
            "role": "user",
            "content": (
                f"Office file attached: {filenames}. The file bytes are intentionally "
                "omitted from this message. Use office_prepare_context if available to "
                "inspect the uploaded file, or ask the user what they want to do."
            ),
        }

    def _get_attachments_by_mimetype(self, mimetypes):
        """Retain Office message text while excluding every attached binary payload.

        Provider serializers share this helper for image, PDF, audio, and text
        attachments. An Office-like message is therefore serialized as its text
        body only, independent of which supported serializer is active.
        """
        self.ensure_one()
        office_mimetypes = {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel.sheet.macroenabled.12",
            "application/vnd.ms-word",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-word.document.macroenabled.12",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint.presentation.macroenabled.12",
        }
        office_suffixes = {".xls", ".xlsx", ".xlsm", ".doc", ".docx", ".docm", ".ppt", ".pptx", ".pptm"}
        if any(
            (attachment.mimetype or "").lower().split(";", 1)[0] in office_mimetypes
            or Path(attachment.name or "").suffix.lower() in office_suffixes
            for attachment in self.attachment_ids
        ):
            return self.env["ir.attachment"]
        return super()._get_attachments_by_mimetype(mimetypes)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _extras_to_store(self, store, format_reply):
        super()._extras_to_store(store, format_reply)
        for message in self:
            if message.model == "llm.thread" and message.is_error:
                store.add(message, {"is_error": True})
