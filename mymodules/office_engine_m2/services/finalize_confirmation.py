"""Internal, version-bound proof for the current Office finalize turn.

The proof transports a user message which is visible in the chat RPC's open
transaction into the isolated root transaction used by the legacy M1 renderer.
It is an in-process value object, never an RPC or Agent-tool argument.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from odoo import _, tools
from odoo.exceptions import AccessError, ValidationError


_CONFIRMATIONS = frozenset(
    {
        "确认",
        "确认生成",
        "确认并生成",
        "生成正式文件",
        "确认生成正式文件",
        "确认并生成正式文件",
    }
)


@dataclass(frozen=True)
class FinalizeConfirmationProof:
    thread_id: int
    session_id: int
    owner_id: int
    user_partner_id: int
    user_message_id: int
    user_message_body_sha256: str
    confirmation_text: str
    session_revision: int
    proposal_revision: int
    preview_attachment_id: int
    preview_sha256: str


def normalized_confirmation_text(body):
    return tools.html2plaintext(body or "").strip()


def is_explicit_finalize_confirmation(body):
    return normalized_confirmation_text(body) in _CONFIRMATIONS


def build_finalize_confirmation_proof(env, thread, session, message, expected_revision, proposal_revision):
    """Capture the current user's message and preview while they share a transaction."""
    if (
        message.model != "llm.thread"
        or message.res_id != thread.id
        or message.llm_role != "user"
        or message.author_id.id != env.user.partner_id.id
        or message.is_error
    ):
        raise AccessError(_("The confirming user message is unavailable."))
    if (
        session.thread_id != thread
        or session.owner_id.id != env.uid
        or session.revision != expected_revision
        or session.proposal_revision != proposal_revision
        or session.preview_proposal_revision != proposal_revision
    ):
        raise ValidationError(_("MAPPING_REVISION_STALE: generate a current preview and confirm again."))

    preview = session.preview_attachment_id
    if not preview:
        raise ValidationError(_("The current validated preview is unavailable."))
    preview.check_access("read")
    preview_bytes = preview.raw or b""
    if not preview_bytes:
        raise ValidationError(_("The current validated preview is empty."))

    body = message.body or ""
    return FinalizeConfirmationProof(
        thread_id=thread.id,
        session_id=session.id,
        owner_id=env.uid,
        user_partner_id=env.user.partner_id.id,
        user_message_id=message.id,
        user_message_body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        confirmation_text=normalized_confirmation_text(body),
        session_revision=session.revision,
        proposal_revision=session.proposal_revision,
        preview_attachment_id=preview.id,
        preview_sha256=hashlib.sha256(preview_bytes).hexdigest(),
    )


def validate_finalize_confirmation_proof(
    env,
    proof,
    thread,
    session,
    expected_revision,
    proposal_revision,
):
    """Revalidate proof scope against the fresh root-cursor state before effects."""
    if not isinstance(proof, FinalizeConfirmationProof):
        raise AccessError(_("An explicit current-user confirmation is required."))
    if proof.confirmation_text not in _CONFIRMATIONS:
        raise AccessError(_("Send an explicit confirmation message before final file generation."))
    if (
        proof.thread_id != thread.id
        or proof.session_id != session.id
        or proof.owner_id != env.uid
        or proof.user_partner_id != env.user.partner_id.id
        or proof.session_revision != expected_revision
        or proof.session_revision != session.revision
        or proof.proposal_revision != proposal_revision
        or proof.proposal_revision != session.proposal_revision
        or session.preview_proposal_revision != proposal_revision
        or proof.preview_attachment_id != session.preview_attachment_id.id
    ):
        raise ValidationError(_("MAPPING_REVISION_STALE: the confirmed target or preview changed; confirm again."))

    # If the message has become visible in this cursor, verify its identity and
    # bytes. If it is still uncommitted in the caller's transaction, a newer
    # committed user message invalidates the proof instead of reviving an older
    # confirmation.
    message = env["mail.message"].browse(proof.user_message_id).exists()
    if message:
        if (
            message.model != "llm.thread"
            or message.res_id != thread.id
            or message.llm_role != "user"
            or message.author_id.id != env.user.partner_id.id
            or message.is_error
            or hashlib.sha256((message.body or "").encode("utf-8")).hexdigest()
            != proof.user_message_body_sha256
            or normalized_confirmation_text(message.body) != proof.confirmation_text
        ):
            raise AccessError(_("The confirming user message is no longer valid."))
    else:
        latest_visible = env["mail.message"].search(
            [
                ("model", "=", "llm.thread"),
                ("res_id", "=", thread.id),
                ("llm_role", "=", "user"),
                ("author_id", "=", env.user.partner_id.id),
                ("is_error", "=", False),
            ],
            order="id desc",
            limit=1,
        )
        if latest_visible and latest_visible.id > proof.user_message_id:
            raise AccessError(_("A newer user message invalidated this confirmation."))

    preview = session.preview_attachment_id
    preview.check_access("read")
    preview_bytes = preview.raw or b""
    if not preview_bytes or hashlib.sha256(preview_bytes).hexdigest() != proof.preview_sha256:
        raise ValidationError(_("The preview changed after confirmation; generate and confirm it again."))
    return True
