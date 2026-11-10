"""Bind Office tools to native Odoo-LLM chat without replacing its loop."""

import json
import logging
import re

from markupsafe import Markup

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.modules.registry import Registry


_logger = logging.getLogger(__name__)


_OFFICE_TOOL_NAMES = {
    "office",
    "office_prepare_context",
    "office_save_mapping_preview",
    "office_restore_proposal_revision",
    "office_finalize",
    "odoo_record_retriever",
}


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def _office_active_session(self):
        self.ensure_one()
        upload, attachment = self._office_latest_upload()
        Session = self.env["office.mapping.session"]
        if not upload or not attachment:
            return Session
        return self.env["office.mapping.session"].search(
            [
                ("thread_id", "=", self.id),
                ("owner_id", "=", self.env.uid),
                ("company_id", "in", self.env.companies.ids),
                ("source_message_id", "=", upload.id),
                ("source_attachment_id", "=", attachment.id),
                ("state", "in", ["analyzing", "preview_ready", "revision_pending", "confirmation_required"]),
            ],
            order="write_date desc, id desc",
            limit=1,
        )

    def _office_related_thread(self):
        """Return the owned parent Thread when this chat was opened from its chatter."""
        self.ensure_one()
        if self.model != self._name or not self.res_id:
            return self.env["llm.thread"]
        related = self.env["llm.thread"].browse(self.res_id).exists()
        if not related:
            return related
        related.check_access("read")
        if related.user_id.id != self.env.uid:
            return self.env["llm.thread"]
        return related

    def _office_upload_from_thread(self, source_thread):
        messages = self.env["mail.message"].search(
            [
                ("model", "=", self._name),
                ("res_id", "=", source_thread.id),
                ("llm_role", "=", "user"),
                ("author_id", "=", self.env.user.partner_id.id),
                ("is_error", "=", False),
            ],
            order="id desc",
            limit=25,
        )
        for message in messages:
            office = source_thread._office_engine_classify_attachments(message.attachment_ids)
            if not office:
                continue
            # A malformed/mixed upload is still the newest Office request;
            # do not reactivate an older valid source file.
            if len(office) != 1 or len(message.attachment_ids) != 1:
                return message, self.env["ir.attachment"]
            return message, office
        return self.env["mail.message"], self.env["ir.attachment"]

    def _office_latest_upload(self):
        """Return the newest Office upload on this chat or its linked parent Thread."""
        self.ensure_one()
        upload, attachment = self._office_upload_from_thread(self)
        if upload:
            return upload, attachment
        parent = self._office_related_thread()
        if parent:
            return self._office_upload_from_thread(parent)
        return upload, attachment

    def _office_linked_template_attachment_ids(self, attachment_ids):
        """Attach a linked parent's template to the first child-chat user turn."""
        self.ensure_one()
        if attachment_ids:
            return attachment_ids
        own_upload, _own_attachment = self._office_upload_from_thread(self)
        if own_upload:
            return attachment_ids
        parent = self._office_related_thread()
        if not parent:
            return attachment_ids
        upload, attachment = self._office_upload_from_thread(parent)
        if not upload or not attachment or len(upload.attachment_ids) != 1:
            return attachment_ids
        return [attachment.id]

    def _office_bind_tools(self):
        """Attach only the native Retriever and Office tools to this owned Thread."""
        self.ensure_one()
        names = sorted(_OFFICE_TOOL_NAMES)
        tools = self.env["llm.tool"].search(
            [("name", "in", names), ("active", "=", True)]
        )
        found = set(tools.mapped("name"))
        required = _OFFICE_TOOL_NAMES
        if found != required:
            raise UserError(_("The approved Office Assistant tools are not fully registered."))
        missing = tools - self.tool_ids
        if missing:
            self.write({"tool_ids": [(4, item.id) for item in missing]})
        return tools

    def _office_is_active(self, incoming_office=False):
        self.ensure_one()
        if incoming_office:
            return True
        upload, _attachment = self._office_latest_upload()
        return bool(upload) or bool(self._office_active_session())

    def _office_has_versioned_current(self):
        """Return whether this Thread has an accepted Candidate B workbook.

        A finalized M1 V1 remains the source of the first Candidate B edit.
        Once a version exists, exposing the M1 context/mapping tools invites
        the model to start a new mapping Session, even though the completed
        M1 Session is intentionally no longer considered active.
        """
        self.ensure_one()
        if self.user_id.id != self.env.uid:
            return False
        upload, attachment = self._office_latest_upload()
        if not upload or not attachment:
            return False
        session = self.env["office.mapping.session"].search(
            [
                ("thread_id", "=", self.id),
                ("owner_id", "=", self.env.uid),
                ("company_id", "in", self.env.companies.ids),
                ("source_message_id", "=", upload.id),
                ("source_attachment_id", "=", attachment.id),
                ("current_version_id", "!=", False),
            ],
            order="id desc",
            limit=1,
        )
        if not session:
            return False
        session.check_access("read")
        version = session.current_version_id
        if not version:
            return False
        version.check_access("read")
        return bool(
            version.session_id == session
            and version.version_kind in {"initial", "edit", "restore"}
            and version.state in {"accepted_current", "finalized"}
            and session.last_valid_version_id == version
        )

    def generate(self, user_message_body=None, attachment_ids=None, **kwargs):
        """Run the original generate loop after M1 preflight and tool binding."""
        self.ensure_one()
        attachment_ids = self._office_linked_template_attachment_ids(attachment_ids)
        incoming_office = False
        if attachment_ids:
            ids = [attachment_ids] if isinstance(attachment_ids, int) else list(attachment_ids)
            attachments = self.env["ir.attachment"].browse(ids).exists()
            try:
                incoming_office = bool(self._office_engine_classify_attachments(attachments))
            except Exception:
                # M1's native generate preflight owns the user-visible reject path.
                incoming_office = False
        if self._office_is_active(incoming_office):
            self._office_bind_tools()
        yield from super().generate(user_message_body, attachment_ids=attachment_ids, **kwargs)

    def _prepare_chat_kwargs(self, message_history, use_streaming):
        values = super()._prepare_chat_kwargs(message_history, use_streaming)
        # A resumed Thread can keep its Office tools after its last Session has
        # left an active state. The native assistant still includes those
        # bound tools in its next model call, so gpt-5 Chat Completions must
        # receive the compatible reasoning_effort value even on that path.
        tools = values.get("tools") or self.env["llm.tool"]
        if (
            self.model_id.provider_id.service == "openai"
            and self.model_id.name.startswith("gpt-5")
            and any(tool.name in _OFFICE_TOOL_NAMES for tool in tools)
        ):
            values["reasoning_effort"] = "none"
        if self._office_is_active():
            if self._office_has_versioned_current():
                # Candidate B owns every edit after M1 has accepted V1. Keep
                # M1 mapping tools available only before a versioned current
                # exists; the `office` facade is the sole edit entry point thereafter.
                values["tools"] = self.tool_ids.filtered(lambda tool: tool.name == "office")
            else:
                values["tools"] = self.tool_ids.filtered(lambda tool: tool.name in _OFFICE_TOOL_NAMES)
            office_rules = {
                "role": "system",
                "content": (
                    "For a Thread with an accepted, versioned current workbook, use the single `office` facade "
                    "for Candidate B actions (status, plan, edit, accept, reject). First submit a generic "
                    "interpretation and the frozen CB-03 Expected Effect to `office` action=plan. Expected Effect "
                    "is a bounded declaration for the existing deterministic Validator, not an Excel editing DSL; "
                    "describe target scopes and allowed change kinds at the coarsest accurate level, include exact "
                    "assertions only when known, and list business aspects that cannot be proven in `unknowns`. "
                    "Do not invent exact cell outcomes for complex edits. The model, not local heuristics, decides "
                    "whether the request is ambiguous (`target_scope.basis='ambiguous'`) and whether an un-authorized "
                    "material business risk requires confirmation (`confirmation_required` and `confirmation_reason`). "
                    "For every plan, explicitly send confirmation_required=true or false; when true, provide a concise "
                    "confirmation_reason and repeat both values unchanged in edit. Never infer authorization from an "
                    "old confirmation or from model claims. "
                    "Nonempty original values, headers, formulas, broad scope, model risk claims, and unknowns do not "
                    "by themselves trigger a local business decision. If clarification is required, ask one focused "
                    "question and do not edit. If a plan returns operation_status=plan_ready with a model-requested "
                    "confirmation, explain the model-provided risk and wait for the current user's exact 确认 or 拒绝; "
                    "then call edit with the unchanged bound plan. A returned operation_status=candidate_review_required "
                    "is a different decision: display verified_facts, actual_effects as observed deterministic differences, "
                    "model_claims, and unverified_aspects; do not reinterpret a local difference label as business-risk judgment. Explain that "
                    "the Candidate is not Current. For VERIFIED or PARTIALLY_VERIFIED, provide the authenticated candidate_download_url and ask the current user to reply exactly 接受 or 拒绝. "
                    "When a PARTIALLY_VERIFIED Candidate is accepted, keep its grade unchanged and state that its unverified aspects remain unverified. "
                    "Local code "
                    "validates the real user's reply, identity, Thread, Session, parent version, file SHA and revisions, "
                    "but does not reassess whether the business risk is real or already authorized. A confirmed plan "
                    "permits candidate generation only; it does not accept the Candidate. External Provider file "
                    "processing is currently blocked by the SRS/data-policy release gate; do not claim an edit occurred "
                    "unless a real tool result contains a Candidate. Always distinguish local `verified_facts`, "
                    "`model_claims`, and `unverified_aspects`. A PARTIALLY_VERIFIED Candidate may be shown for review "
                    "when CB-03 reports no technical failure; it is not VERIFIED. A FAILED Candidate is blocked and "
                    "cannot be made acceptable by user confirmation. A VERIFIED or PARTIALLY_VERIFIED Candidate remains non-current "
                    "until the current user explicitly replies 接受; the risk-plan reply 确认 does not accept a Candidate. "
                    "A scoped CB-02 acceptance may move a PARTIALLY_VERIFIED edit Candidate to Current without changing its validation grade; a scoped rejection leaves Current and Last Valid unchanged. "
                    "Do not claim the "
                    "user's complete natural-language intent is independently proven. Never claim Finalize, "
                    "attachment delivery, or download: those remain a separate CB-06 lifecycle. The current accepted "
                    "XLSX version, not chat history, is authoritative file content. Do not use the M1 Mapping "
                    "tools to edit a workbook after it has an accepted Candidate B current version. "
                    "When the user asks to add or refresh Odoo data in the current workbook, first call the single "
                    "office facade with action=retrieve and a query_spec using only the fields and records needed. "
                    "Use include_pagination=true for result sets and continue by offset while has_more is true. "
                    "Use returned record IDs for later reads; where the existing Retriever accepts only simple "
                    "domain clauses, retrieve multiple known IDs with separate exact id-equality calls rather than "
                    "using spreadsheet row positions or guessed names. Retrieval is read-only and does not require "
                    "a Current/Revision gate or change the workbook. After retrieval, use the existing plan/edit/review "
                    "flow; do not claim an Excel change until that flow returns a Candidate. "
                    "For an initial Office mapping request, use odoo_record_retriever to identify the exact "
                    "business record from the user's request, then call office_prepare_context. Use only the "
                    "returned target_manifest and allowed_fields. "
                    "For repeat-row mappings, if an exact scalar Many2one path needed from a readable related "
                    "collection is missing from that collection's allowed_fields, pass the exact path under "
                    "requested_fields_by_collection when calling office_prepare_context; the server will check "
                    "each requested path with the current user's ORM access before adding it. "
                    "For a follow-up in a Thread that already has an active Office Session, continue that "
                    "Session and its saved Proposal; do not start a new mapping task or discard prior rules. "
                    "Reuse the bound target_model and target_record_id from the prior Office context. If those "
                    "identifiers are not present in the conversation context, call office_prepare_context with "
                    "target_model='unknown' and target_record_id=0 so the server can resolve only the existing "
                    "Thread-bound Session. "
                    "Resolve record identifiers stated by the user directly with the Retriever. For an "
                    "identifier or name lookup, request at least two results so duplicate matches remain visible. "
                    "When the user asks for one record, proceed to office_prepare_context only when exactly one "
                    "authorized record matches. If the Retriever returns no match or multiple matches for a "
                    "singular request, ask one concise natural-language question "
                    "in this chat. Never direct the user to a record-picker dialog, dropdown, or separate "
                    "selection UI. When the user requests a set of records without narrowing criteria, do not "
                    "silently select one or invent filters: retrieve all matching pages with include_pagination=true, "
                    "advance offset until has_more is false, and pass the ordered IDs in target_record_ids to "
                    "office_prepare_context. If the result exceeds the Office batch limit, report the exact "
                    "returned/total counts and ask the user to narrow the request. "
                    "For requests to undo or restore a previous saved Proposal, use "
                    "office_restore_proposal_revision with a revision listed in available_proposal_revisions; "
                    "the service revalidates the saved version and creates a fresh preview. "
                    "For template labels asking for an address, full address, or detailed address, compare "
                    "the returned field label and help metadata and prefer fields whose names or descriptions "
                    "indicate contact_address, street, city, or postal address. Do not use display_name or "
                    "name as a postal address merely because it is available; if no suitable address field is "
                    "available, explain the gap or ask for clarification. This is a semantic selection rule, "
                    "not permission to use a field absent from allowed_fields. "
                    "For a returned repeat_row_collections entry, retrieve its rows with "
                    "odoo_record_retriever using the exact inverse_field = target_record_id filter. "
                    "If collection_field is selected_records, use the already retrieved records and pass all their "
                    "IDs as target_record_ids; the server reauthorizes that ordered set in the current Session. "
                    "If fields returned by the Retriever for those selected records are missing from Office Context's "
                    "allowed_fields, call office_prepare_context with their exact paths in requested_fields before mapping; "
                    "do not replace them with a guessed field or an out-of-manifest cell. "
                    "The native Retriever uses search_read, whose fields argument accepts only direct "
                    "fields on the requested model, not dotted paths. If Office Context lists a related "
                    "path such as relation.field, first retrieve the relation field itself from the parent "
                    "record, then retrieve the linked record using its returned ID and the direct field "
                    "name on that related model. For a one2many collection, retrieve its rows with the "
                    "inverse-field domain and direct fields, then follow returned many2one IDs in separate "
                    "Retriever calls when needed. Odoo's current-user ACLs, field access rights, and record "
                    "rules apply to every call; do not assume dotted fields are accepted by search_read. "
                    "Return a complete m2.mapping-proposal.v1 mapping to office_save_mapping_preview. "
                    "When the user asks to fill the uploaded template, that request authorizes a draft preview: "
                    "once the business record and a valid supported Proposal are available, call "
                    "office_save_mapping_preview immediately. Do not ask the user to separately approve or "
                    "confirm a preview. Ask a focused clarification only when a required source or rule is "
                    "genuinely ambiguous or unavailable; do not block a preview for optional targets the "
                    "user permits to remain blank. For a valid natural-language correction, update the "
                    "Proposal and create the replacement preview in the same turn. "
                    "Its proposal object must have exactly these root keys: schema_version, mappings, "
                    "clarifications, skipped_targets, with optional clear_targets and cell_edits. Pass explicit coordinate value changes "
                    "as the separate top-level cell_edits tool argument. For a fixed coordinate use "
                    "{element_id, value, value_type}. For an edit that must follow one row record after sorting, "
                    "use {record_target: {group_id, record_id, column}, value, value_type}; take record_id "
                    "from the current authorized Retriever result and group_id from the current repeat-row "
                    "mapping context. The server resolves its final row only after the current sort is applied. "
                    "Repeat-row mapping runs before explicit cell edits, so an explicitly requested edit may "
                    "replace that record's mapped value. Empty string means clear; do not substitute null, zero, "
                    "or false. "
                    "Use it only for a coordinate listed in the current TargetManifest and explicitly requested by the user. "
                    "Whenever the user explicitly asks to change or clear an existing coordinate, first call "
                    "office_save_mapping_preview with the exact cell_edits so the server can inspect the current file. "
                    "Do not issue an overwrite confirmation request from your own guess or a visual/text description; "
                    "only a tool result with status needs_confirmation authorizes you to ask the user to confirm. "
                    "Do not omit the requested cell_edits and return an unchanged result after the user confirms. "
                    "If office_save_mapping_preview returns status needs_confirmation, explain its risks, old/new values and exact operation_scope, ask the returned confirmation_question, and stop without writing. "
                    "Only after a new user message that is exactly 确认, repeat the identical operation and set force_override=true. If the user explicitly declines with 拒绝, 取消, or 不同意, repeat the identical pending operation so the server records status blocked; do not retry the write. "
                    "The server binds confirmation to this Thread, user, Session, Proposal revision, preview, current document bytes, targets and values; force_override by itself never authorizes a write. A stale confirmation returns needs_confirmation again and requires a fresh user reply. "
                    "After confirmation, the edit can replace the existing literal or formula at that exact coordinate, including a detected table header, without changing the cell's style or any other source mapping. "
                    "Normal field mappings remain restricted to writable data targets. If the same target also has a "
                    "stale model-generated unsupported-target clarification or skip, omit that stale no-op for the target. "
                    "Each mapping must use exactly one shape: direct "
                    "element_id/source_field/value_type; ordered fallback element_id/source_fields/value_type; "
                    "safe arithmetic formula element_id/formula/value_type, or a typed scalar value "
                    "element_id/literal_value/value_type when the user specifies a value or asks for a "
                    "deterministic calculation from retrieved data. To explicitly clear a target, "
                    "you may also use the compact shape element_id/value with value exactly an empty string. "
                    "Do not invent values or use a literal instead of a requested live field mapping. Use the exact IDs and field names "
                    "returned by Office Context. For repeated detail rows, pass the collection, worksheet, "
                    "first row and column-to-field choices in the separate repeat_rows argument; do not "
                    "enumerate repeated cells in proposal.mappings. The server derives row count and target "
                    "cells. For a selected record set, use repeat_rows for its row mapping and never put a "
                    "cell outside the current TargetManifest into mappings, clarifications, or skips. If the "
                    "server returns repeat_rows_required, refresh the exact missing source fields and resubmit "
                    "a complete repeat_rows mapping. If the row count requires structural insertion beyond the "
                    "template's existing row capacity, the server returns needs_confirmation without writing; "
                    "explain the exact added rows and formula impacts, wait for the user's exact 确认, then retry "
                    "the identical repeat_rows and Proposal with force_override=true. That confirmation is bound "
                    "to this user, Thread, Session, file bytes, revision, selected rows, columns and operation; it "
                    "cannot authorize a changed range. When the user explicitly requests an ordering, pass sort_by and sort_direction "
                    "together in repeat_rows; sort_by must be one of the selected collection's allowed_fields, "
                    "and direction is asc or desc. Empty values remain last. If no order is requested, retain "
                    "the relation's current order. Do not substitute keys such as field or type. Do not claim "
                    "an operation succeeded unless a tool returns status success. For a generated preview, require "
                    "operation_status=preview_ready and attachment_posted_to_thread=true; for a reused current preview, "
                    "require operation_status=unchanged. Answer questions from the current Session/tool history without changing "
                    "the Proposal. Never put a target absent from target_manifest into mappings, clarifications, "
                    "or skipped_targets. Use clear_targets or the compact empty-value mapping only when "
                    "the user explicitly asks to blank a cell; "
                    "for a whole detected table column, use clear_columns with its exact sheet and column letter; "
                    "the server expands it only to table_data cells, never the header. Use format_patches to change "
                    "Excel display formatting while preserving values; a whole table column uses sheet, column, "
                    "and number_format (for example 0.0). A value mapping and a format patch may target the same "
                    "cell because they change separate properties. "
                    "an omitted target is left unchanged. Template labels are not mandatory business requirements. "
                    "Explain unsupported user requests in normal text; submit valid supported "
                    "mappings independently when possible. Direct mappings, same-type ordered source fallbacks, "
                    "typed date/datetime values, bounded date offsets, and restricted same-sheet arithmetic formulas are supported. "
                    "When the user requests a date shift, do not refuse because the source is a date: use a typed "
                    "date/datetime literal if you have calculated the result from retrieved ISO values, or attach "
                    "transform={type:'date_offset',days:7} to a date/datetime source mapping. This is a bounded "
                    "server-side date operation, not Python or arbitrary expression execution. For repeat_rows, "
                    "the same transform may be attached to a date/datetime source column. Preserve date values as "
                    "typed Excel dates; do not convert them to display-only text. "
                    "Formula syntax allows only "
                    "cell references, numbers, parentheses and + - * /. Every repeat-row column object must "
                    "include its destination Excel column letter in `column` (for example "
                    "{'column':'C','source_field':'product_id.default_code'}); never omit `column`. "
                    "Then choose exactly one of source_field, fallback_fields, concat_fields, or formula. Use fallback_fields only for first-nonempty selection; use concat_fields to join multiple authorized string fields in order, with an optional separator (empty by default). In a formula template, {row} is the row number "
                    "and must appear inside cell references, for example =E{row}*D{row}*2 (not {row}*{row}*2). "
                    "Inspect "
                    "mapping_limits.template_formula_cells to understand which targets currently contain formulas. "
                    "A template formula stays unchanged unless the user explicitly maps or clears that target; "
                    "when explicitly selected in repeat_rows, the requested value or formula replaces it. Conditions, "
                    "arbitrary Excel functions, external/cross-sheet formulas and .docx mapping are unsupported. "
                    "Call office_finalize only after the user explicitly confirms. If asking for confirmation, "
                    "request the exact user reply '确认并生成正式文件'; this exact phrase is accepted by the "
                    "server-side authorization gate. When office_finalize returns status=finalized and "
                    "attachment_posted_to_thread=true, tell the user that the named file is attached in this "
                    "chat and can be downloaded from its attachment card. Do not construct a Markdown link, "
                    "web URL, or attachment:// URL from tool metadata. If the tool does not confirm that the "
                    "attachment was posted, do not claim that the file is available for download."
                ),
            }
            values["prepend_messages"] = [office_rules] + list(values.get("prepend_messages") or [])
        return values

    def _generate_assistant_response(self):
        """Use the native non-streaming handler for Office tool turns.

        llm_assistant chooses its handler from model metadata before calling
        _prepare_chat_kwargs, so changing only the returned ``stream`` flag is
        ineffective. The native non-streaming response keeps tool-call
        processing in llm_assistant's generate_messages loop and exposes the
        Provider's response.usage for the existing meter.
        """
        self.ensure_one()
        gpt5_office_tool_turn = (
            self.model_id.provider_id.service == "openai"
            and self.model_id.name.startswith("gpt-5")
            and any(tool.name in _OFFICE_TOOL_NAMES for tool in self.tool_ids)
        )
        if not self._office_is_active() and not gpt5_office_tool_turn:
            yield from super()._generate_assistant_response()
            return

        self.env.flush_all()
        history = self.get_llm_messages()
        chat_kwargs = self._prepare_chat_kwargs(history, use_streaming=False)
        if gpt5_office_tool_turn:
            # The configured gpt-5.6-luna Chat Completions endpoint rejected
            # function tools unless reasoning_effort is explicitly "none".
            chat_kwargs["reasoning_effort"] = "none"
        try:
            response = self.sudo().model_id.chat(**chat_kwargs)
            assistant_message = yield from self._handle_non_streaming_response(response)
        except Exception as exc:
            _logger.exception("Office Provider call failed in thread %s", self.id)
            error_message, event = self._post_error_message(exc, title=_("LLM API Error"))
            yield event
            return error_message
        return assistant_message

    def _office_message_store_payload(self, message):
        """Serialize a newly posted Office message together with its attachments.

        ``to_store_format()`` returns only the mail.message row. The Discuss
        Store payload also contains related ``ir.attachment`` rows, which the
        live chat needs to resolve the filename and MIME type for a download
        card without reloading the thread.
        """
        from odoo.addons.mail.tools.discuss import Store

        store = Store()
        message._to_store(store)
        payload = store.get_result()
        message_data = next(
            item for item in payload.get("mail.message", []) if item["id"] == message.id
        )
        return message_data, payload

    def _office_committed_message_store_payload(self, message_id, attachment_id):
        """Read a committed M1 delivery message in a fresh current-user cursor.

        M1 commits the final attachment and its mail.message on a separate
        cursor. The request cursor therefore cannot serialize that row into
        the live SSE Store until it is re-read from a fresh snapshot.
        """
        self.ensure_one()
        cursor = Registry(self.env.cr.dbname).cursor()
        try:
            env = api.Environment(cursor, self.env.uid, dict(self.env.context))
            message = env["mail.message"].browse(message_id).exists()
            if (
                not message
                or message.model != self._name
                or message.res_id != self.id
                or message.llm_role != "assistant"
                or attachment_id not in message.attachment_ids.ids
            ):
                raise UserError(_("The committed Office file is not attached to this chat message."))
            message.check_access("read")
            attachment = env["ir.attachment"].browse(attachment_id).exists()
            if not attachment:
                raise UserError(_("The committed Office attachment is unavailable."))
            attachment.check_access("read")
            return self._office_message_store_payload(message)
        finally:
            cursor.rollback()
            cursor.close()

    def _handle_non_streaming_response(self, response):
        """Meter native OpenAI response metadata without touching conversation content."""
        if self._office_is_active() and isinstance(response, dict):
            try:
                from ..services.usage_service import record_usage

                usage_result = record_usage(
                    self.env,
                    model=self.model_id,
                    usage=response.get("usage"),
                    elapsed_ms=None,
                    attempt_no=1,
                    outcome="success",
                    response_id=response.get("response_id"),
                    thread=self,
                )
                if not usage_result:
                    _logger.warning("M2 native Provider Usage was not recorded; thread_id=%s", self.id)
            except Exception as exc:
                _logger.warning(
                    "M2 native Provider Usage could not be recorded; thread_id=%s error_type=%s",
                    self.id,
                    type(exc).__name__,
                )
        return (yield from super()._handle_non_streaming_response(response))

    def _process_llm_body(self, body):
        """Normalize malformed Candidate download href whitespace in Office chats.

        The assistant can append a Markdown trailing space inside an Odoo
        ``/web/content/<id>?download=true`` link. Odoo's binary controller
        treats that value as invalid. Normalize only that exact internal
        download parameter after the normal HTML sanitizer has run; attachment
        ACL checks and the controller remain authoritative.
        """
        rendered = super()._process_llm_body(body)
        if not rendered:
            return rendered
        # This is a syntax correction for Odoo's boolean query parameter, not
        # an Office-session check; avoid attachment/session lookup while a
        # message is being rendered (including error/help messages).
        normalized = re.sub(
            r"(?P<prefix>\bhref=[\"']/web/content/[0-9]+\?download=true)(?:%20|[ \t\r\n])+(?P<quote>[\"'])",
            lambda match: match.group("prefix") + match.group("quote"),
            str(rendered),
            flags=re.IGNORECASE,
        )
        # ``super()`` returns sanitized Markup. ``re.sub`` downgrades it to a
        # plain str, which Odoo correctly escapes when rendering a chatter body.
        # Re-wrap only this already-sanitized HTML so the repaired anchor stays
        # clickable in the native UI.
        return Markup(normalized)

    def _execute_tool_call(self, tool_call, assistant_message):
        tool_name = (tool_call.get("function") or {}).get("name")
        if self._office_is_active():
            candidate_b_current = self._office_has_versioned_current()
            allowed_tool_names = {"office"} if candidate_b_current else _OFFICE_TOOL_NAMES
            if tool_name not in allowed_tool_names:
                error = self.env["mail.message"].create_tool_error_message(
                    tool_call,
                    _(
                        "This M1 mapping tool is unavailable because this Thread already has an accepted versioned workbook. "
                        "Use the office Candidate B facade for subsequent edits."
                        if candidate_b_current
                        else "This tool is not available during an Office mapping session."
                    ),
                    thread_model=self,
                )
                yield {"type": "message_create", "message": error.to_store_format()}
                return error

        tool_message = yield from super()._execute_tool_call(tool_call, assistant_message)
        if self._office_is_active() and tool_name in {
            "office_save_mapping_preview",
            "office_restore_proposal_revision",
        }:
            result = (tool_message.get_tool_data() or {}).get("result") or {}
            attachment_id = result.get("preview_attachment_id")
            is_preview_delivery = (
                tool_name == "office_save_mapping_preview"
                and result.get("status") == "success"
                and result.get("operation_status") in {"preview_ready", "unchanged"}
            ) or (
                tool_name == "office_restore_proposal_revision"
                and result.get("status") in {"preview_ready", "unchanged"}
            )
            if (
                is_preview_delivery
                and result.get("attachment_posted_to_thread") is True
                and type(attachment_id) is int
            ):
                delivery = result.get("attachment") or {}
                preview_message = self.env["mail.message"].browse(delivery.get("message_id", 0)).exists()
                if not preview_message or attachment_id not in preview_message.attachment_ids.ids:
                    preview_message = self.env["mail.message"].search(
                        [
                            ("model", "=", self._name),
                            ("res_id", "=", self.id),
                            ("llm_role", "=", "assistant"),
                            ("attachment_ids", "in", [attachment_id]),
                        ],
                        order="id desc",
                        limit=1,
                    )
                if preview_message:
                    message_data, store_data = self._office_message_store_payload(preview_message)
                    yield {
                        "type": "message_create",
                        "message": message_data,
                        "store_data": store_data,
                    }
                else:
                    _logger.warning(
                        "Office preview attachment %s is reported as posted but has no chat message; thread_id=%s",
                        attachment_id,
                        self.id,
                    )
        if tool_name == "office_finalize":
            result = (tool_message.get_tool_data() or {}).get("result") or {}
            attachment_id = result.get("attachment_id")
            message_id = result.get("delivery_message_id")
            if (
                result.get("status") == "finalized"
                and type(attachment_id) is int
                and type(message_id) is int
            ):
                try:
                    message_data, store_data = self._office_committed_message_store_payload(
                        message_id, attachment_id
                    )
                except Exception:
                    _logger.exception(
                        "Final Office output could not be added to the live chat Store; thread_id=%s attachment_id=%s",
                        self.id,
                        attachment_id,
                    )
                    tool_data = tool_message.get_tool_data() or {}
                    tool_data["status"] = "error"
                    tool_data["error"] = _(
                        "The file was generated, but the chat could not load its attachment card."
                    )
                    tool_data["result"] = {
                        **result,
                        "status": "failed",
                        "attachment_posted_to_thread": False,
                        "error_code": "final_attachment_not_visible",
                        "message": tool_data["error"],
                    }
                    tool_message.write({"body_json": tool_data})
                    yield {
                        "type": "message_update",
                        "message": tool_message.to_store_format(),
                    }
                else:
                    yield {
                        "type": "message_create",
                        "message": message_data,
                        "store_data": store_data,
                    }
        return tool_message


class LLMTool(models.Model):
    _inherit = "llm.tool"

    def get_input_schema(self):
        """Build Office tool schemas from Python signatures without FastMCP.

        The installed ``mcp`` package is v2, while the llm_tool helper imports
        the removed v1 FastMCP path. Office tools must still expose their real
        arguments to the Provider, so use llm_tool's existing Pydantic
        signature builder for this bounded tool set.
        """
        self.ensure_one()
        if self.name not in _OFFICE_TOOL_NAMES:
            return super().get_input_schema()
        method = self._get_implementation_method()
        if self.name == "office" and getattr(method, "_llm_tool_schema", None):
            return json.loads(json.dumps(method._llm_tool_schema))
        schema = self.get_pydantic_model_from_signature(method).model_json_schema()
        if self.name == "office_save_mapping_preview":
            schema["properties"].pop("header_edits", None)
            schema["properties"]["cell_edits"] = {
                "type": "array",
                "maxItems": 200,
                "description": "Optional explicit set_value operations. Use element_id for a fixed coordinate, or record_target to follow one authorized repeat-row record through the current final sort. The record_target must name a record in the bound collection and a column in its server-authorized repeat-row layout. Mapping runs first and this explicit edit runs afterward. Replacing an existing value/formula returns needs_confirmation with exact scope; no write occurs until the user replies exactly 确认 and the identical operation is retried with force_override=true. The flag alone grants no authority.",
                "items": {
                    "anyOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["element_id", "value", "value_type"],
                            "properties": {
                                "element_id": {"type": "string", "maxLength": 255},
                                "value": {"anyOf": [
                                    {"type": "string", "maxLength": 300},
                                    {"type": "number"}, {"type": "boolean"},
                                ]},
                                "value_type": {"type": "string", "enum": ["string", "number", "boolean", "date", "datetime"]},
                            },
                        },
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["record_target", "value", "value_type"],
                            "properties": {
                                "record_target": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["group_id", "record_id", "column"],
                                    "properties": {
                                        "group_id": {"type": "string", "maxLength": 64},
                                        "record_id": {"type": "integer", "minimum": 1},
                                        "column": {"type": "string", "pattern": "^[A-Z]{1,3}$"},
                                    },
                                },
                                "value": {"anyOf": [
                                    {"type": "string", "maxLength": 300},
                                    {"type": "number"}, {"type": "boolean"},
                                ]},
                                "value_type": {"type": "string", "enum": ["string", "number", "boolean", "date", "datetime"]},
                            },
                        },
                    ],
                },
            }
            schema["properties"]["force_override"] = {
                "type": "boolean",
                "default": False,
                "description": "Set true only when retrying the identical pending cell_edits or repeat_rows operation after the user has replied exactly 确认 in this Thread. This flag alone is not authorization and cannot expand its pending scope.",
            }
            schema["properties"]["repeat_rows"] = {
                "type": "array",
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["collection_field", "sheet", "start_row", "columns"],
                    "properties": {
                        "collection_field": {"type": "string"},
                        "sheet": {"type": "string"},
                        "start_row": {"type": "integer", "minimum": 1},
                        "sort_by": {
                            "type": "string",
                            "description": "Optional scalar field from the selected collection's allowed_fields; use only when the user requests ordering.",
                        },
                        "sort_direction": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Required together with sort_by. Empty values stay last.",
                        },
                        "columns": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 64,
                            "description": "Every item requires a destination Excel column and exactly one of source_field, fallback_fields, concat_fields, or formula. concat_fields joins authorized string fields in order using separator (empty by default). A date_offset transform may accompany a date/datetime source field.",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["column"],
                                "properties": {
                                    "column": {"type": "string", "pattern": "^[A-Z]{1,3}$", "description": "Required destination Excel column from the template's repeat-row layout."},
                                    "source_field": {"type": "string", "description": "One directly readable scalar field in the selected repeat-row collection."},
                                    "fallback_fields": {
                                        "type": "array",
                                        "minItems": 2,
                                        "maxItems": 8,
                                        "items": {"type": "string"},
                                    },
                                    "concat_fields": {
                                        "type": "array",
                                        "minItems": 2,
                                        "maxItems": 8,
                                        "items": {"type": "string"},
                                        "description": "Two to eight distinct fields, each authorized and typed string; all nonempty values are joined in this order.",
                                    },
                                    "separator": {
                                        "type": "string",
                                        "maxLength": 32,
                                        "description": "Text placed between nonempty concat_fields values; defaults to an empty string.",
                                    },
                                    "formula": {"type": "string", "maxLength": 512},
                                    "transform": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["type", "days"],
                                        "properties": {
                                            "type": {"const": "date_offset"},
                                            "days": {"type": "integer", "minimum": -365000, "maximum": 365000},
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            }
            schema["properties"]["proposal"] = {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "schema_version",
                    "mappings",
                    "clarifications",
                    "skipped_targets",
                ],
                "properties": {
                    "schema_version": {
                        "type": "string",
                        "enum": ["m2.mapping-proposal.v1"],
                    },
                    "mappings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["element_id"],
                            "properties": {
                                "element_id": {"type": "string"},
                                "value": {
                                    "type": "string",
                                    "enum": [""],
                                    "description": "Use only for an explicit clear; use literal_value for non-empty scalar values.",
                                },
                                "source_field": {"type": "string"},
                                "source_fields": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 8,
                                    "items": {"type": "string"},
                                },
                                "formula": {"type": "string", "maxLength": 512},
                                "transform": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["type", "days"],
                                    "properties": {
                                        "type": {"const": "date_offset"},
                                        "days": {"type": "integer", "minimum": -365000, "maximum": 365000},
                                    },
                                    "description": "Optional; allowed only with a date/datetime source mapping.",
                                },
                                "literal_value": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "boolean"},
                                        {"type": "string", "format": "date"},
                                        {"type": "string", "format": "date-time"},
                                    ],
                                    "description": "A user-specified or deterministically calculated scalar, including ISO date/date-time values; pair with value_type. Not an Excel formula.",
                                },
                                "value_type": {
                                    "type": "string",
                                    "enum": ["string", "number", "boolean", "date", "datetime", "formula"],
                                },
                            },
                        },
                    },
                    "clarifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["element_id", "reason_code", "question"],
                            "properties": {
                                "element_id": {"type": "string"},
                                "reason_code": {
                                    "type": "string",
                                    "enum": [
                                        "missing_source",
                                        "ambiguous_mapping",
                                        "unsupported_target",
                                        "conflicting_instruction",
                                    ],
                                },
                                "question": {"type": "string"},
                            },
                        },
                    },
                    "skipped_targets": {"type": "array", "items": {"type": "string"}},
                    "clear_targets": {
                        "type": "array",
                        "description": "Optional writable target IDs the user explicitly asked to clear; omitted targets remain unchanged.",
                        "items": {"type": "string"},
                    },
                    "clear_columns": {
                        "type": "array",
                        "description": "Clear only detected table_data cells in the named worksheet column; table headers and non-table cells are excluded.",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["sheet", "column"],
                            "properties": {
                                "sheet": {"type": "string"},
                                "column": {"type": "string", "pattern": "^[A-Z]{1,3}$"},
                            },
                        },
                    },
                    "format_patches": {
                        "type": "array",
                        "description": "Change display format without replacing cell values. A column patch applies only to detected table_data cells.",
                        "items": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["element_id", "number_format"],
                                    "properties": {
                                        "element_id": {"type": "string"},
                                        "number_format": {"type": "string", "maxLength": 128},
                                    },
                                },
                                {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["sheet", "column", "number_format"],
                                    "properties": {
                                        "sheet": {"type": "string"},
                                        "column": {"type": "string", "pattern": "^[A-Z]{1,3}$"},
                                        "number_format": {"type": "string", "maxLength": 128},
                                    },
                                },
                            ]
                        },
                    },
                },
            }
            # Keep the two document-only operations available at the same
            # top level accepted by native Provider tool calls. The tool
            # method explicitly merges them into the Proposal before strict
            # contract parsing; nested placement remains supported for older
            # clients.
            proposal_properties = schema["properties"]["proposal"]["properties"]
            schema["properties"]["clear_columns"] = proposal_properties["clear_columns"]
            schema["properties"]["format_patches"] = proposal_properties["format_patches"]
        return schema

    def odoo_record_retriever_execute(
        self,
        model,
        domain=None,
        fields=None,
        limit=100,
        offset=0,
        order="",
        include_pagination=False,
    ):
        """Delegate retrieval to the existing Odoo ORM-backed Retriever.

        Its ``search_read`` runs under this request's current ``env`` and
        therefore applies Odoo model ACLs, field access rights, and record
        rules. Office does not impose a second model/domain/provenance policy.
        """
        return super().odoo_record_retriever_execute(
            model,
            domain=domain or [],
            fields=fields or [],
            limit=limit,
            offset=offset,
            order=order,
            include_pagination=include_pagination,
        )
