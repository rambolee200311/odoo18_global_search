"""Current-user Odoo persistence wrapper for the Office Engine services."""

from __future__ import annotations

import contextvars
import hashlib
import importlib
import json
import logging
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

from odoo import _, api, conf, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules.registry import Registry


def _load_trusted_python_package(package_name):
    """Load a pure-Python package from this adapter's configured addon root.

    Odoo's dynamic ``odoo.addons.*`` module name cannot be re-imported by a
    fresh multiprocessing ``spawn`` interpreter. Keep a single stable,
    ordinary Python package identity for the parent and worker.
    """
    addon_root = Path(__file__).resolve().parents[2]
    configured_roots = {
        Path(path).resolve()
        for path in getattr(conf, "addons_paths", [])
        if path
    }
    if addon_root not in configured_roots:
        raise ImportError("Office engine package root is not a configured Odoo addon path")
    root_string = str(addon_root)
    if root_string not in sys.path:
        sys.path.insert(0, root_string)
    package = importlib.import_module(package_name)
    expected_init = (addon_root / package_name / "__init__.py").resolve()
    if Path(package.__file__).resolve() != expected_init:
        raise ImportError("Office engine package resolved outside its configured addon path")
    return package


_office_core = _load_trusted_python_package("office_core")
_office_verify = _load_trusted_python_package("office_verify")
OfficeCoreError = _office_core.OfficeCoreError
ResourceBudget = _office_core.ResourceBudget
inspect_document = _office_core.inspect_document
render_candidate = _office_core.render_candidate
OfficeVerifyError = _office_verify.OfficeVerifyError
VerificationBudget = _office_verify.VerificationBudget
VerificationPolicy = _office_verify.VerificationPolicy
verify_output = _office_verify.verify_output


_logger = logging.getLogger(__name__)
_INTERNAL_MUTATION = contextvars.ContextVar("office_document_request_internal_mutation", default=False)

_MIME_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MAX_MAPPING_BYTES = 1 * 1024 * 1024
_MAX_FILE_SIZE = 32 * 1024 * 1024
_MAX_EXPANDED_SIZE = 100 * 1024 * 1024
_MAX_ZIP_ENTRIES = 512
_MAX_ENTRY_SIZE = 20 * 1024 * 1024
_MAX_XML_ELEMENTS = 1_000_000
_MAX_CELLS = 500_000
_MAX_PARAGRAPHS = 100_000
_MAX_MEMORY_BYTES = 4 * 1024 * 1024 * 1024
_TIMEOUT_SECONDS = 15.0
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


class _RequestFailure(Exception):
    def __init__(self, code, stage, message):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message


@contextmanager
def _internal_mutation():
    token = _INTERNAL_MUTATION.set(True)
    try:
        yield
    finally:
        _INTERNAL_MUTATION.reset(token)


def _resource_budget():
    return ResourceBudget(
        max_file_size=_MAX_FILE_SIZE,
        max_expanded_size=_MAX_EXPANDED_SIZE,
        max_zip_entries=_MAX_ZIP_ENTRIES,
        max_entry_size=_MAX_ENTRY_SIZE,
        max_xml_elements=_MAX_XML_ELEMENTS,
        max_cells=_MAX_CELLS,
        max_paragraphs=_MAX_PARAGRAPHS,
        max_memory_bytes=_MAX_MEMORY_BYTES,
        timeout_seconds=_TIMEOUT_SECONDS,
    )


def _verification_budget():
    return VerificationBudget(
        max_file_size=_MAX_FILE_SIZE,
        max_expanded_size=_MAX_EXPANDED_SIZE,
        max_zip_entries=_MAX_ZIP_ENTRIES,
        max_entry_size=_MAX_ENTRY_SIZE,
        max_xml_elements=_MAX_XML_ELEMENTS,
        max_cells=_MAX_CELLS,
        max_paragraphs=_MAX_PARAGRAPHS,
        max_mapping_bytes=_MAX_MAPPING_BYTES,
        max_memory_bytes=_MAX_MEMORY_BYTES,
        timeout_seconds=_TIMEOUT_SECONDS,
    )


def _new_environment(dbname, uid, context):
    cursor = Registry(dbname).cursor()
    return cursor, api.Environment(cursor, uid, context)


def _now_utc():
    return fields.Datetime.to_string(datetime.now(timezone.utc).replace(tzinfo=None))


class OfficeDocumentRequest(models.Model):
    _name = "office.document.request"
    _description = "Office Document Processing Request"
    _order = "id desc"

    request_uuid = fields.Char(required=True, readonly=True, copy=False)
    owner_id = fields.Many2one("res.users", required=True, readonly=True, copy=False, ondelete="restrict")
    thread_id = fields.Many2one("llm.thread", readonly=True, copy=False, ondelete="set null")
    input_message_id = fields.Many2one("mail.message", readonly=True, copy=False, ondelete="set null")
    source_attachment_id = fields.Many2one("ir.attachment", readonly=True, copy=False, ondelete="set null")
    output_attachment_id = fields.Many2one("ir.attachment", readonly=True, copy=False, ondelete="restrict")
    state = fields.Selection(
        [
            ("accepted", "Accepted"),
            ("validating", "Validating"),
            ("processing", "Processing"),
            ("generated", "Generated"),
            ("failed", "Failed"),
        ],
        required=True,
        readonly=True,
        default="accepted",
        copy=False,
    )
    error_code = fields.Char(readonly=True, copy=False)
    failed_stage = fields.Char(readonly=True, copy=False)
    input_sha256 = fields.Char(readonly=True, copy=False, size=64)
    output_sha256 = fields.Char(readonly=True, copy=False, size=64)
    started_at = fields.Datetime(required=True, readonly=True, copy=False)
    finished_at = fields.Datetime(readonly=True, copy=False)

    _sql_constraints = [
        ("request_uuid_unique", "unique(request_uuid)", "The request UUID must be unique."),
    ]

    @api.model
    def _inspect_chat_attachment(self, source, thread, input_message):
        """Inspect a supported chat upload under the current user's access."""
        source.ensure_one()
        thread.ensure_one()
        input_message.ensure_one()
        source.check("read")
        if source.type != "binary" or source.url:
            raise UserError(_("Only a binary Office attachment can be inspected."))
        self._validate_input_context(self.env, self.env.uid, source, thread.id, input_message.id)
        filename = source.name or ""
        mimetype = (source.mimetype or "").lower().split(";", 1)[0].strip()
        extension = os.path.splitext(filename)[1].lower()
        fmt = {".xlsx": "xlsx", ".docx": "docx"}.get(extension)
        if not fmt or mimetype not in {_MIME_TYPES[fmt], "application/octet-stream"}:
            raise UserError(_("The Office extension and content type do not match a supported format."))
        if source.file_size <= 0 or source.file_size > _MAX_FILE_SIZE:
            raise UserError(_("The Office attachment is empty or exceeds the file size limit."))
        content = source.raw or b""
        if not content or len(content) != source.file_size or len(content) > _MAX_FILE_SIZE:
            raise UserError(_("The Office attachment could not be read within the configured limit."))
        inspection = inspect_document(content, filename, mimetype, _resource_budget())
        if inspection.format != fmt:
            raise UserError(_("The attachment contents do not match the declared Office format."))
        sheet_names = sorted(
            {
                item.element_id.split(":", 1)[1].rsplit("!", 1)[0]
                for item in inspection.elements
                if item.element_id.startswith("xlsx:") and "!" in item.element_id
            }
        )
        formula_count = sum(item.kind == "formula" for item in inspection.elements)
        return {
            "format": inspection.format,
            "element_count": len(inspection.elements),
            "formula_count": formula_count,
            "sheet_names": sheet_names,
            "template_sha256": inspection.template_sha256,
        }

    @api.model_create_multi
    def create(self, vals_list):
        if not _INTERNAL_MUTATION.get():
            raise AccessError(_("Office requests can only be created by the internal Office service."))
        normalized = []
        allowed = {
            "request_uuid",
            "owner_id",
            "thread_id",
            "input_message_id",
            "source_attachment_id",
            "input_sha256",
            "started_at",
        }
        for incoming in vals_list:
            if set(incoming) - allowed:
                raise ValidationError(_("The Office request contains unsupported fields."))
            request_uuid = incoming.get("request_uuid")
            if not isinstance(request_uuid, str) or not _UUID_PATTERN.fullmatch(request_uuid):
                raise ValidationError(_("A valid caller-generated request UUID is required."))
            try:
                if str(uuid.UUID(request_uuid)) != request_uuid.lower():
                    raise ValueError
            except (ValueError, AttributeError) as exc:
                raise ValidationError(_("A valid caller-generated request UUID is required.")) from exc
            values = dict(incoming)
            values["owner_id"] = self.env.uid
            values["state"] = "accepted"
            values["started_at"] = values.get("started_at") or _now_utc()
            normalized.append(values)
        return super().create(normalized)

    def write(self, vals):
        if not _INTERNAL_MUTATION.get():
            raise AccessError(_("Office request state and result fields are managed by the internal Office service."))
        allowed = {
            "state",
            "output_attachment_id",
            "error_code",
            "failed_stage",
            "input_sha256",
            "output_sha256",
            "finished_at",
        }
        if set(vals) - allowed:
            raise ValidationError(_("The Office request update contains unsupported fields."))
        transitions = {
            "accepted": {"validating", "failed"},
            "validating": {"processing", "failed"},
            "processing": {"generated", "failed"},
            "generated": set(),
            "failed": set(),
        }
        next_state = vals.get("state")
        if next_state:
            for request in self:
                if next_state not in transitions[request.state]:
                    raise ValidationError(_("The Office request state transition is not allowed."))
        return super().write(vals)

    @api.constrains("state", "output_attachment_id")
    def _check_output_consistency(self):
        for request in self:
            output = request.output_attachment_id
            if request.state == "generated" and not output:
                raise ValidationError(_("A generated request must have an output attachment."))
            if request.state != "generated" and output:
                raise ValidationError(_("Only a generated request can have an output attachment."))
            if output and (
                output.res_model != request._name
                or output.res_id != request.id
                or output.public
            ):
                raise ValidationError(_("The output attachment must be private and bound to this request."))

    @api.constrains("request_uuid")
    def _check_request_uuid(self):
        for request in self:
            if not _UUID_PATTERN.fullmatch(request.request_uuid or ""):
                raise ValidationError(_("A valid caller-generated request UUID is required."))

    @api.model
    def _render_request_sync(
        self,
        request_uuid,
        source_attachment_id,
        mapping_plan,
        thread_id=None,
        input_message_id=None,
    ):
        """Synchronously render a private result using only the current user context."""
        if not isinstance(mapping_plan, dict):
            raise UserError(_("A valid explicit Mapping Plan is required."))
        try:
            mapping_size = len(json.dumps(mapping_plan, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise UserError(_("The Mapping Plan must be JSON serializable.")) from exc
        if mapping_size > _MAX_MAPPING_BYTES:
            raise UserError(_("The Mapping Plan exceeds the allowed size."))

        dbname, uid, context = self.env.cr.dbname, self.env.uid, dict(self.env.context)
        request_id, content, filename, mimetype, input_sha256, already_exists, preflight_error = self._begin_request(
            dbname, uid, context, request_uuid, source_attachment_id, thread_id, input_message_id
        )
        if already_exists:
            return self._existing_result(dbname, uid, context, request_id)
        if preflight_error:
            return self._fail_request(
                dbname, uid, context, request_id, *preflight_error
            )

        try:
            self._set_request_state(dbname, uid, context, request_id, "validating")
            ext = os.path.splitext(filename)[1].lower()
            fmt = {".xlsx": "xlsx", ".docx": "docx"}.get(ext)
            if not fmt:
                raise _RequestFailure(
                    "OFFICE_UNSUPPORTED_FEATURE", "format", "当前仅开放已验证的 .xlsx 与 .docx 基础结构。"
                )
            if mimetype != _MIME_TYPES[fmt]:
                raise _RequestFailure(
                    "OFFICE_INVALID_OR_MISMATCHED", "format", "文件扩展名与内容类型不一致。"
                )

            budget = _resource_budget()
            verify_budget = _verification_budget()
            inspection = inspect_document(content, filename, mimetype, budget)
            if inspection.format != fmt or inspection.template_sha256 != input_sha256:
                raise _RequestFailure(
                    "OFFICE_INVALID_OR_MISMATCHED", "inspection", "输入文件格式或内容身份检查失败。"
                )
            self._set_request_state(dbname, uid, context, request_id, "processing")
            candidate = render_candidate(content, filename, mimetype, mapping_plan, budget)
            verification = verify_output(
                content,
                candidate.content,
                filename,
                mimetype,
                mapping_plan,
                VerificationPolicy(enabled_formats=("xlsx", "docx"), require_styles=True),
                verify_budget,
            )
            if verification.status != "PASS":
                raise _RequestFailure(
                    "OFFICE_INTEGRITY_FAILED", "verify", "生成文件未通过完整性回读检查。"
                )
            if verification.output_sha256 != candidate.candidate_sha256:
                raise _RequestFailure(
                    "OFFICE_INTEGRITY_FAILED", "verify", "生成文件摘要与回读结果不一致。"
                )
            try:
                return self._deliver_result(
                    dbname,
                    uid,
                    context,
                    request_id,
                    source_attachment_id,
                    thread_id,
                    input_message_id,
                    input_sha256,
                    candidate.content,
                    candidate.candidate_sha256,
                    filename,
                    fmt,
                    verification.as_dict(),
                )
            except Exception as exc:
                raise _RequestFailure(
                    "OFFICE_DELIVERY_FAILED", "delivery", "结果附件未能安全提交，未提供下载结果。"
                ) from exc
        except _RequestFailure as exc:
            return self._fail_request(dbname, uid, context, request_id, exc.code, exc.stage, exc.message)
        except (OfficeCoreError, OfficeVerifyError) as exc:
            return self._fail_request(dbname, uid, context, request_id, exc.code, exc.stage, exc.message)
        except (AccessError, UserError):
            return self._fail_request(
                dbname, uid, context, request_id, "OFFICE_DELIVERY_FAILED", "authorization", "请求授权或交付检查失败。"
            )
        except Exception:
            _logger.error("Office request failed; request_uuid=%s stage=internal", request_uuid)
            return self._fail_request(
                dbname, uid, context, request_id, "OFFICE_ENGINE_FAILED", "internal", "Office 文件处理失败。"
            )

    def _begin_request(self, dbname, uid, context, request_uuid, source_attachment_id, thread_id, input_message_id):
        if not isinstance(request_uuid, str) or not _UUID_PATTERN.fullmatch(request_uuid):
            raise UserError(_("A valid caller-generated request UUID is required."))
        request_uuid = str(uuid.UUID(request_uuid))
        if isinstance(source_attachment_id, bool) or not isinstance(source_attachment_id, int) or source_attachment_id <= 0:
            raise UserError(_("A valid authorized source attachment is required."))
        for value, label in ((thread_id, "thread"), (input_message_id, "message")):
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                raise UserError(_("A valid %(label)s reference is required.", label=label))
        if bool(thread_id) != bool(input_message_id):
            raise UserError(_("Thread and input message context must be supplied together."))

        duplicate = False
        duplicate_id = False
        content = b""
        filename = ""
        mimetype = ""
        input_sha256 = ""
        preflight_error = False
        cursor, env = _new_environment(dbname, uid, context)
        try:
            Request = env["office.document.request"]
            Request.check_access("create")
            Attachment = env["ir.attachment"]
            source = Attachment.browse(source_attachment_id).exists()
            if not source:
                raise AccessError(_("The source attachment is unavailable."))
            # ir.attachment has an additional linked-record access check that
            # is implemented by check(), beyond generic model ACL/rules.
            source.check("read")
            if source.type != "binary" or source.url:
                raise UserError(_("Only an authorized binary Office attachment can be processed."))
            filename = source.name or ""
            mimetype = source.mimetype or ""
            self._validate_input_context(env, uid, source, thread_id, input_message_id)
            existing = Request.search([("request_uuid", "=", request_uuid)], limit=1)
            if existing:
                if (
                    existing.source_attachment_id.id != source.id
                    or existing.thread_id.id != (thread_id or False)
                    or existing.input_message_id.id != (input_message_id or False)
                ):
                    raise UserError(_("This request UUID is already bound to a different input."))
                if source.file_size and source.file_size > _MAX_FILE_SIZE:
                    duplicate_id = existing.id
                    duplicate = True
                    preflight_error = ("OFFICE_RESOURCE_LIMIT", "input_snapshot", "源文件超过服务端大小限制。")
                else:
                    content = source.raw or b""
                    input_sha256 = hashlib.sha256(content).hexdigest()
                    if existing.input_sha256 and existing.input_sha256 != input_sha256:
                        raise UserError(_("The source attachment content changed for this request UUID."))
                    duplicate_id = existing.id
                    duplicate = True
            else:
                if source.file_size and source.file_size > _MAX_FILE_SIZE:
                    content = b""
                    preflight_error = ("OFFICE_RESOURCE_LIMIT", "input_snapshot", "源文件超过服务端大小限制。")
                else:
                    content = source.raw or b""
                    if len(content) > _MAX_FILE_SIZE:
                        content = b""
                        preflight_error = ("OFFICE_RESOURCE_LIMIT", "input_snapshot", "源文件超过服务端大小限制。")
                    else:
                        input_sha256 = hashlib.sha256(content).hexdigest()
                with _internal_mutation():
                    request = Request.create(
                        {
                            "request_uuid": request_uuid,
                            "owner_id": uid,
                            "thread_id": thread_id or False,
                            "input_message_id": input_message_id or False,
                            "source_attachment_id": source.id,
                            "input_sha256": input_sha256 or False,
                        }
                    )
                duplicate_id = request.id
                cursor.commit()
        except psycopg2.IntegrityError as exc:
            cursor.rollback()
            if "request_uuid" not in (getattr(getattr(exc, "diag", None), "constraint_name", "") or ""):
                cursor.close()
                raise
            duplicate = True
        except Exception:
            cursor.rollback()
            cursor.close()
            raise
        cursor.close()

        if duplicate and not duplicate_id:
            cursor, env = _new_environment(dbname, uid, context)
            try:
                existing = env["office.document.request"].search([("request_uuid", "=", request_uuid)], limit=1)
                if not existing:
                    raise AccessError(_("The request is unavailable."))
                duplicate_id = existing.id
                source = env["ir.attachment"].browse(source_attachment_id).exists()
                if not source:
                    raise AccessError(_("The source attachment is unavailable."))
                source.check("read")
                self._validate_input_context(env, uid, source, thread_id, input_message_id)
                if (
                    existing.source_attachment_id.id != source.id
                    or existing.thread_id.id != (thread_id or False)
                    or existing.input_message_id.id != (input_message_id or False)
                ):
                    raise UserError(_("This request UUID is already bound to a different input."))
                if source.file_size and source.file_size > _MAX_FILE_SIZE:
                    raise UserError(_("The source file exceeds the configured size limit."))
                content = source.raw or b""
                input_sha256 = hashlib.sha256(content).hexdigest()
                if existing.input_sha256 and existing.input_sha256 != input_sha256:
                    raise UserError(_("The source attachment content changed for this request UUID."))
            finally:
                cursor.rollback()
                cursor.close()
        elif duplicate:
            cursor, env = _new_environment(dbname, uid, context)
            try:
                existing = env["office.document.request"].browse(duplicate_id).exists()
                if not existing:
                    raise AccessError(_("The request is unavailable."))
            finally:
                cursor.rollback()
                cursor.close()

        if duplicate:
            return duplicate_id, content, filename, mimetype, input_sha256, True, preflight_error
        return duplicate_id, content, filename, mimetype, input_sha256, False, preflight_error

    def _set_request_state(self, dbname, uid, context, request_id, state, extra=None):
        cursor, env = _new_environment(dbname, uid, context)
        try:
            request = env["office.document.request"].browse(request_id).exists()
            if not request:
                raise AccessError(_("The request is unavailable."))
            request.check_access("write")
            values = {"state": state}
            values.update(extra or {})
            if state == "generated":
                values.setdefault("finished_at", _now_utc())
            with _internal_mutation():
                request.write(values)
            cursor.commit()
        except Exception:
            cursor.rollback()
            raise
        finally:
            cursor.close()

    def _validate_request_input(self, env, request, source_attachment_id, thread_id, input_message_id, input_sha256):
        request.check_access("write")
        if request.owner_id.id != env.uid:
            raise AccessError(_("The request is unavailable."))
        source = env["ir.attachment"].browse(source_attachment_id).exists()
        if not source:
            raise AccessError(_("The source attachment is unavailable."))
        source.check_access("read")
        current = hashlib.sha256(source.raw or b"").hexdigest()
        if current != input_sha256 or (request.input_sha256 and request.input_sha256 != current):
            raise AccessError(_("The source attachment changed during processing."))
        self._validate_input_context(env, env.uid, source, thread_id, input_message_id)
        return source

    @staticmethod
    def _validate_input_context(env, uid, source, thread_id, input_message_id):
        if bool(thread_id) != bool(input_message_id):
            raise AccessError(_("The request context is unavailable."))
        if thread_id:
            thread = env["llm.thread"].browse(thread_id).exists()
            message = env["mail.message"].browse(input_message_id).exists()
            if not thread or not message:
                raise AccessError(_("The request context is unavailable."))
            thread.check_access("read")
            message.check_access("read")
            if thread.user_id.id != uid or message.model != "llm.thread" or message.res_id != thread.id:
                raise AccessError(_("The request context is unavailable."))
            if source not in message.attachment_ids:
                raise AccessError(_("The source attachment is not part of the input message."))
        elif source.res_model == "mail.message":
            raise AccessError(_("Message attachments require a validated message context."))

    def _deliver_result(
        self,
        dbname,
        uid,
        context,
        request_id,
        source_attachment_id,
        thread_id,
        input_message_id,
        input_sha256,
        candidate_bytes,
        candidate_sha256,
        filename,
        fmt,
        verification,
    ):
        cursor, env = _new_environment(dbname, uid, context)
        try:
            request = env["office.document.request"].browse(request_id).exists()
            if not request:
                raise AccessError(_("The request is unavailable."))
            self._validate_request_input(
                env, request, source_attachment_id, thread_id, input_message_id, input_sha256
            )
            clean_name = "office-output-" + request.request_uuid + "." + fmt
            request_uuid = request.request_uuid
            create_started_at = _now_utc()
            started = time.monotonic()
            with _internal_mutation():
                output = env["ir.attachment"].create(
                    {
                        "name": clean_name,
                        "type": "binary",
                        "raw": candidate_bytes,
                        "mimetype": _MIME_TYPES[fmt],
                        "public": False,
                        "res_model": request._name,
                        "res_id": request.id,
                    }
                )
                request.write(
                    {
                        "output_attachment_id": output.id,
                        "output_sha256": candidate_sha256,
                        "state": "generated",
                        "error_code": False,
                        "failed_stage": False,
                        "finished_at": _now_utc(),
                    }
                )
            output.check("read")
            output_id = output.id
            output_hash = candidate_sha256
            cursor.commit()
            commit_completed_at = _now_utc()
            elapsed_ms = round((time.monotonic() - started) * 1000, 3)
            _logger.info(
                "Office attachment create-to-commit timing request_uuid=%s db=%s uid=%s create_started_at=%s commit_completed_at=%s elapsed_ms=%s",
                request_uuid,
                dbname,
                uid,
                create_started_at,
                commit_completed_at,
                elapsed_ms,
            )
            if elapsed_ms > 1000:
                _logger.warning(
                    "Warning — TDD §6.1 long transaction risk request_uuid=%s elapsed_ms=%s",
                    request_uuid,
                    elapsed_ms,
                )
            return {
                "request_uuid": request_uuid,
                "state": "generated",
                "error_code": False,
                "failed_stage": False,
                "output_attachment_id": output_id,
                "output_sha256": output_hash,
                "readback": verification,
            }
        except Exception:
            cursor.rollback()
            raise
        finally:
            cursor.close()

    def _fail_request(self, dbname, uid, context, request_id, code, stage, message):
        # A commit exception can be ambiguous; honor a committed generated result if it exists.
        cursor, env = _new_environment(dbname, uid, context)
        try:
            request = env["office.document.request"].browse(request_id).exists()
            if request and request.state == "generated" and request.output_attachment_id:
                request.output_attachment_id.check("read")
                result = self._record_to_result(request)
                cursor.rollback()
                return result
        except AccessError:
            pass
        finally:
            cursor.rollback()
            cursor.close()

        cursor, env = _new_environment(dbname, uid, context)
        try:
            request = env["office.document.request"].browse(request_id).exists()
            response = {
                "request_uuid": request.request_uuid if request else False,
                "state": request.state if request else "failed",
                "error_code": request.error_code if request and request.state == "failed" else code,
                "failed_stage": request.failed_stage if request and request.state == "failed" else stage,
                "message": message,
                "output_attachment_id": False,
            }
            if request and request.state not in ("generated", "failed"):
                request.check_access("write")
                with _internal_mutation():
                    request.write(
                        {
                            "state": "failed",
                            "output_attachment_id": False,
                            "error_code": code,
                            "failed_stage": stage,
                            "finished_at": _now_utc(),
                        }
                    )
                response.update(
                    {
                        "state": "failed",
                        "error_code": code,
                        "failed_stage": stage,
                    }
                )
                cursor.commit()
            elif request:
                cursor.rollback()
            return response
        except Exception:
            cursor.rollback()
            _logger.error("Office failure state could not be persisted; request_id=%s", request_id)
            return {
                "request_uuid": False,
                "state": "failed",
                "error_code": "OFFICE_DELIVERY_FAILED",
                "failed_stage": "failure_persistence",
                "message": "Office 请求失败，且失败状态暂未持久化。",
                "output_attachment_id": False,
            }
        finally:
            cursor.close()

    def _existing_result(self, dbname, uid, context, request_id):
        cursor, env = _new_environment(dbname, uid, context)
        try:
            request = env["office.document.request"].browse(request_id).exists()
            if not request:
                raise AccessError(_("The request is unavailable."))
            request.check_access("read")
            if request.output_attachment_id:
                request.output_attachment_id.check_access("read")
            return self._record_to_result(request)
        finally:
            cursor.rollback()
            cursor.close()

    @staticmethod
    def _record_to_result(request):
        return {
            "request_uuid": request.request_uuid,
            "state": request.state,
            "error_code": request.error_code or False,
            "failed_stage": request.failed_stage or False,
            "output_attachment_id": request.output_attachment_id.id or False,
            "output_sha256": request.output_sha256 or False,
        }
