"""Bind Office tools to native Odoo-LLM chat without replacing its loop."""

import json
import logging

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.modules.registry import Registry


_logger = logging.getLogger(__name__)


_OFFICE_TOOL_NAMES = {
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
            values["tools"] = self.tool_ids.filtered(lambda tool: tool.name in _OFFICE_TOOL_NAMES)
            office_rules = {
                "role": "system",
                "content": (
                    "For an initial Office mapping request, use odoo_record_retriever to identify the exact "
                    "business record from the user's request, then call office_prepare_context. Use only the "
                    "returned target_manifest and allowed_fields. "
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
                    "clarifications, skipped_targets, with optional clear_targets. Each mapping must use exactly one shape: direct "
                    "element_id/source_field/value_type; ordered fallback element_id/source_fields/value_type; "
                    "safe arithmetic formula element_id/formula/value_type, or a typed scalar value "
                    "element_id/literal_value/value_type when the user specifies a value or asks for a "
                    "deterministic calculation from retrieved data. To explicitly clear a target, "
                    "you may also use the compact shape element_id/value with value exactly an empty string. "
                    "Do not invent values or use a literal instead of a requested live field mapping. Use the exact IDs and field names "
                    "returned by Office Context. For repeated detail rows, pass the collection, worksheet, "
                    "first row and column-to-field choices in the separate repeat_rows argument; do not "
                    "enumerate repeated cells in proposal.mappings. The server derives row count and target "
                    "cells. When the user explicitly requests an ordering, pass sort_by and sort_direction "
                    "together in repeat_rows; sort_by must be one of the selected collection's allowed_fields, "
                    "and direction is asc or desc. Empty values remain last. If no order is requested, retain "
                    "the relation's current order. Do not substitute keys such as field or type. Do not claim "
                    "a preview exists unless that tool returns "
                    "preview_ready. Answer questions from the current Session/tool history without changing "
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
                    "and restricted same-sheet arithmetic formulas are supported. Formula syntax allows only "
                    "cell references, numbers, parentheses and + - * /. Every repeat-row column object must "
                    "include its destination Excel column letter in `column` (for example "
                    "{'column':'C','source_field':'product_id.default_code'}); never omit `column`. "
                    "Then choose exactly one of source_field, fallback_fields, or formula. In a formula template, {row} is the row number "
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

    def _execute_tool_call(self, tool_call, assistant_message):
        tool_name = (tool_call.get("function") or {}).get("name")
        if self._office_is_active():
            if tool_name not in _OFFICE_TOOL_NAMES:
                error = self.env["mail.message"].create_tool_error_message(
                    tool_call,
                    _("This tool is not available during an Office mapping session."),
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
            if (
                result.get("status") in {"preview_ready", "unchanged"}
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
        schema = self.get_pydantic_model_from_signature(method).model_json_schema()
        if self.name == "office_save_mapping_preview":
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
                            "description": "Every item requires the destination Excel column letter plus exactly one source_field, fallback_fields, or formula. Example: {\"column\":\"C\",\"source_field\":\"product_id.default_code\"}.",
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
                                    "formula": {"type": "string", "maxLength": 512},
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
                                "literal_value": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "boolean"},
                                    ],
                                    "description": "A user-specified or deterministically calculated scalar value; pair with value_type. Not an Excel formula.",
                                },
                                "value_type": {
                                    "type": "string",
                                    "enum": ["string", "number", "boolean", "formula"],
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
