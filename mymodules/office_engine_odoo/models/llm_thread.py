"""Provider-boundary attachment checks for LLM threads."""

import os

from odoo import _, models
from odoo.exceptions import AccessError, UserError

from ..services import inspect_attachment_identity


_REJECT_MESSAGE = _(
    "This attachment is an Office file or its type could not be verified safely. "
    "Office attachments are not available in this chat."
)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def _office_engine_attachment_header(self, attachment):
        """Return at most 2048 bytes through the user's Odoo filestore record."""
        attachment.check_access("read")
        if attachment.file_size <= 0:
            return b""

        if not attachment.store_fname:
            # Odoo's raw/datas/db_datas accessors materialize the complete
            # payload. Do not use them for signature checks.
            return None

        filestore = os.path.realpath(attachment._filestore())
        path = os.path.realpath(attachment._full_path(attachment.store_fname))
        if os.path.commonpath((filestore, path)) != filestore:
            raise OSError("Attachment storage path is outside the filestore")
        with open(path, "rb") as content:
            return content.read(2048)

    def _office_engine_validate_messages(self, messages):
        """Reject Office candidates and mark the originating user messages."""
        for message in messages:
            for attachment in message.attachment_ids:
                try:
                    attachment.check_access("read")
                    if attachment.url and not attachment.store_fname:
                        header = b""
                    elif attachment.store_fname:
                        header = self._office_engine_attachment_header(attachment)
                    else:
                        header = None

                    # If Odoo stores an attachment in the database, an Office
                    # declaration is enough to fail closed; non-Office
                    # database-backed attachments keep their existing path.
                    identity_header = header or b""
                    identity = inspect_attachment_identity(
                        attachment.name,
                        attachment.mimetype,
                        identity_header,
                        attachment.file_size,
                    )
                    if header is None and identity.is_office_candidate:
                        identity = None
                except (AccessError, OSError, ValueError):
                    message.write({"is_error": True})
                    raise UserError(_REJECT_MESSAGE) from None

                if identity is None or identity.is_office_candidate:
                    message.write({"is_error": True})
                    raise UserError(_REJECT_MESSAGE)

    def _check_unsupported_attachments(self, message=None):
        self.ensure_one()
        messages = message if message else self._get_context_messages()
        self._office_engine_validate_messages(messages)
        return super()._check_unsupported_attachments(message)

    def _prepare_chat_kwargs(self, message_history, use_streaming):
        self.ensure_one()
        self._office_engine_validate_messages(message_history)
        return super()._prepare_chat_kwargs(message_history, use_streaming)
