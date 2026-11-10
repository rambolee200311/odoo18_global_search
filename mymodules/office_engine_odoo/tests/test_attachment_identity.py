import base64
import hashlib
import io
import zipfile
from unittest.mock import patch
from uuid import uuid4

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase
from office_core import OfficeCoreError

from ..services import inspect_attachment_identity
from ..models.office_document_request import (
    _M1VersionBindingProof,
    _ensure_output_chat_message,
    _internal_mutation,
    OfficeDocumentRequest,
)


class TestAttachmentIdentity(TransactionCase):
    @staticmethod
    def _readback_proof(input_sha256, output_sha256):
        report = {
            "status": "PASS",
            "format": "xlsx",
            "input_sha256": input_sha256,
            "output_sha256": output_sha256,
            "checked_targets": 1,
            "checked_formulas": 0,
            "warnings": [],
        }
        return {"status": "PASS", "output_sha256": output_sha256, "office_verify": report}

    def test_rpc_style_write_cannot_forge_persisted_m1_validation_proof(self):
        thread = self._thread()
        source_bytes = self._minimal_xlsx()
        source = self._attachment(
            "proof-source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_bytes,
        )
        input_message = thread.message_post(
            body="Synthetic validation proof test.", llm_role="user", attachment_ids=[source.id]
        )
        request_uuid = str(uuid4())
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        with _internal_mutation():
            request = self.env["office.document.request"].create(
                {
                    "request_uuid": request_uuid,
                    "thread_id": thread.id,
                    "input_message_id": input_message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": source_digest,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})

        output_digest = hashlib.sha256(b"synthetic candidate bytes").hexdigest()
        proof = {
            "state": "generated",
            "m1_validation_status": "VERIFIED",
            "m1_validator_policy_version": "office_verify.m1.readback.v1",
            "m1_validation_report_id": "a" * 64,
            "m1_validation_report_sha256": "a" * 64,
            "m1_validation_input_sha256": source_digest,
            "m1_validation_output_sha256": output_digest,
            "m1_validation_completed_at": "2026-11-06 09:00:00",
            "m1_version_session_id": False,
            "m1_version_session_revision": False,
            "m1_version_proposal_revision": False,
        }
        with self.assertRaises(AccessError):
            request.write(proof)
        request.invalidate_recordset(["state", "m1_validation_status"])
        self.assertEqual(request.state, "processing")
        self.assertFalse(request.m1_validation_status)

    def test_final_output_message_is_linked_once_with_download_metadata(self):
        thread = self._thread()
        source = self._attachment(
            "source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            self._minimal_xlsx(),
        )
        input_message = thread.message_post(
            body="Fill this template",
            llm_role="user",
            attachment_ids=[source.id],
        )
        request_uuid = str(uuid4())
        with _internal_mutation():
            request = self.env["office.document.request"].create(
                {
                    "request_uuid": request_uuid,
                    "thread_id": thread.id,
                    "input_message_id": input_message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": "a" * 64,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})
            output = self.env["ir.attachment"].create(
                {
                    "name": "office-output-" + request_uuid + ".xlsx",
                    "type": "binary",
                    "raw": b"verified output bytes",
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "public": False,
                    "res_model": request._name,
                    "res_id": request.id,
                }
            )
            request.write(
                {
                    "output_attachment_id": output.id,
                    "output_sha256": "b" * 64,
                    "state": "generated",
                }
            )

        message_id, created = _ensure_output_chat_message(self.env, request)
        self.assertTrue(created)
        message = self.env["mail.message"].browse(message_id)
        self.assertEqual(message.model, thread._name)
        self.assertEqual(message.res_id, thread.id)
        self.assertEqual(message.llm_role, "assistant")
        self.assertIn(output, message.attachment_ids)

        duplicate_message_id, duplicate_created = _ensure_output_chat_message(self.env, request)
        self.assertEqual(duplicate_message_id, message_id)
        self.assertFalse(duplicate_created)
        self.assertEqual(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", thread._name),
                    ("res_id", "=", thread.id),
                    ("attachment_ids", "in", output.ids),
                ]
            ),
            1,
        )

        result = OfficeDocumentRequest._record_to_result(request)
        self.assertEqual(result["output_attachment_id"], output.id)
        self.assertEqual(result["filename"], output.name)
        self.assertEqual(result["mimetype"], output.mimetype)

    def test_publish_failure_rolls_back_output_and_retry_publishes_same_request(self):
        thread = self._thread()
        source_bytes = self._minimal_xlsx()
        source = self._attachment(
            "retry-source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_bytes,
        )
        input_message = thread.message_post(
            body="Retry file delivery",
            llm_role="user",
            attachment_ids=[source.id],
        )
        request_uuid = str(uuid4())
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        Request = self.env["office.document.request"]
        with _internal_mutation():
            request = Request.create(
                {
                    "request_uuid": request_uuid,
                    "owner_id": self.env.uid,
                    "thread_id": thread.id,
                    "input_message_id": input_message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": source_digest,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})
        # The real worker commits each state transition in its own cursor.
        # Persist the fixture's processing state before the simulated delivery
        # savepoint so rollback only undoes the output/publish attempt.
        request.flush_recordset(["state"])

        savepoint = "office_delivery_publish_failure"
        self.env.cr.execute(f"SAVEPOINT {savepoint}")
        binding = _M1VersionBindingProof(
            session_id=987654321,
            session_revision=1,
            proposal_revision=1,
            owner_id=self.env.uid,
            thread_id=thread.id,
            source_attachment_id=source.id,
            input_message_id=input_message.id,
        )

        class SavepointCursor:
            def commit(_self):
                self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint}")

            def rollback(_self):
                self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")

            def close(_self):
                return None

        with patch(
            "odoo.addons.office_engine_odoo.models.office_document_request._new_environment",
            return_value=(SavepointCursor(), self.env),
        ), patch(
            "odoo.addons.office_engine_odoo.models.office_document_request._ensure_output_chat_message",
            side_effect=UserError("synthetic attachment publication failure"),
        ):
            with self.assertRaisesRegex(UserError, "synthetic attachment publication failure"):
                Request._deliver_result(
                    self.env.cr.dbname,
                    self.env.uid,
                    dict(self.env.context),
                    request.id,
                    source.id,
                    thread.id,
                    input_message.id,
                    source_digest,
                    b"verified final workbook bytes",
                    hashlib.sha256(b"verified final workbook bytes").hexdigest(),
                    source.name,
                    "xlsx",
                    self._readback_proof(
                        source_digest, hashlib.sha256(b"verified final workbook bytes").hexdigest()
                    ),
                    binding,
                )

        request.invalidate_recordset(["state", "output_attachment_id"], flush=False)
        self.assertEqual(request.state, "processing")
        self.assertFalse(request.output_attachment_id)
        self.assertFalse(
            self.env["ir.attachment"].search_count(
                [("res_model", "=", request._name), ("res_id", "=", request.id)]
            )
        )

        with patch(
            "odoo.addons.office_engine_odoo.models.office_document_request._new_environment",
            return_value=(SavepointCursor(), self.env),
        ):
            retry = Request._deliver_result(
                self.env.cr.dbname,
                self.env.uid,
                dict(self.env.context),
                request.id,
                source.id,
                thread.id,
                input_message.id,
                source_digest,
                b"verified final workbook bytes",
                hashlib.sha256(b"verified final workbook bytes").hexdigest(),
                source.name,
                "xlsx",
                self._readback_proof(
                    source_digest, hashlib.sha256(b"verified final workbook bytes").hexdigest()
                ),
                binding,
            )
        request.invalidate_recordset(["state", "output_attachment_id"])
        self.assertEqual(retry["state"], "generated")
        self.assertEqual(retry["request_uuid"], request_uuid)
        self.assertTrue(retry["output_attachment_id"])
        self.assertTrue(retry["delivery_message_id"])
        self.assertEqual(request.state, "generated")
        posted = self.env["mail.message"].browse(retry["delivery_message_id"])
        self.assertEqual(posted.model, thread._name)
        self.assertEqual(posted.res_id, thread.id)
        self.assertIn(request.output_attachment_id, posted.attachment_ids)

    def test_m1_subcursor_delivery_uses_binding_validated_before_handoff(self):
        """The render transaction validates a pending Session before handing off to its worker cursor."""
        thread = self._thread()
        source_bytes = self._minimal_xlsx()
        source_digest = hashlib.sha256(source_bytes).hexdigest()
        source = self._attachment(
            "subcursor-source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_bytes,
        )
        input_message = thread.message_post(
            body="Synthetic render handoff.", llm_role="user", attachment_ids=[source.id]
        )
        request_uuid = str(uuid4())
        with _internal_mutation():
            request = self.env["office.document.request"].create(
                {
                    "request_uuid": request_uuid,
                    "owner_id": self.env.uid,
                    "thread_id": thread.id,
                    "input_message_id": input_message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": source_digest,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})

        class SavepointCursor:
            def commit(_self):
                self.env.cr.execute("RELEASE SAVEPOINT office_m1_subcursor_handoff")

            def rollback(_self):
                self.env.cr.execute("ROLLBACK TO SAVEPOINT office_m1_subcursor_handoff")

            def close(_self):
                return None

        self.env.cr.execute("SAVEPOINT office_m1_subcursor_handoff")
        candidate_bytes = source_bytes
        candidate_digest = hashlib.sha256(candidate_bytes).hexdigest()
        binding = _M1VersionBindingProof(
            session_id=987654321,
            session_revision=8,
            proposal_revision=2,
            owner_id=self.env.uid,
            thread_id=thread.id,
            source_attachment_id=source.id,
            input_message_id=input_message.id,
        )
        with patch(
            "odoo.addons.office_engine_odoo.models.office_document_request._new_environment",
            return_value=(SavepointCursor(), self.env),
        ), patch.object(
            OfficeDocumentRequest,
            "_check_m1_version_binding",
            side_effect=AccessError("the child cursor still sees the prior Session revision"),
        ):
            result = OfficeDocumentRequest._deliver_result(
                self.env["office.document.request"],
                self.env.cr.dbname,
                self.env.uid,
                dict(self.env.context),
                request.id,
                source.id,
                thread.id,
                input_message.id,
                source_digest,
                candidate_bytes,
                candidate_digest,
                source.name,
                "xlsx",
                self._readback_proof(source_digest, candidate_digest),
                binding,
            )

        request.invalidate_recordset()
        self.assertEqual(result["state"], "generated")
        self.assertEqual(request.m1_version_session_id, binding.session_id)
        self.assertEqual(request.m1_version_session_revision, binding.session_revision)
        self.assertEqual(request.m1_version_proposal_revision, binding.proposal_revision)

    def test_delivery_commit_recovery_returns_generated_state_without_false_publish(self):
        thread = self._thread()
        source_bytes = self._minimal_xlsx()
        source = self._attachment(
            "ambiguous-commit-source.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            source_bytes,
        )
        input_message = thread.message_post(
            body="Recover an ambiguous output commit",
            llm_role="user",
            attachment_ids=[source.id],
        )
        digest = hashlib.sha256(source_bytes).hexdigest()
        Request = self.env["office.document.request"]
        with _internal_mutation():
            request = Request.create(
                {
                    "request_uuid": str(uuid4()),
                    "owner_id": self.env.uid,
                    "thread_id": thread.id,
                    "input_message_id": input_message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": digest,
                }
            )
            output = self._attachment(
                "office-output-ambiguous.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"generated private output",
            )
            output.write({"res_model": request._name, "res_id": request.id, "public": False})
            request.write({"state": "validating"})
            request.write({"state": "processing"})
            request.write(
                {
                    "state": "generated",
                    "output_attachment_id": output.id,
                    "output_sha256": hashlib.sha256(output.raw).hexdigest(),
                }
            )

        class RollbackOnlyCursor:
            def rollback(_self):
                return None

            def close(_self):
                return None

        with patch(
            "odoo.addons.office_engine_odoo.models.office_document_request._new_environment",
            return_value=(RollbackOnlyCursor(), self.env),
        ), patch(
            "odoo.addons.office_engine_odoo.models.office_document_request._ensure_output_chat_message",
            side_effect=UserError("synthetic chat publish failure"),
        ):
            result = Request._fail_request(
                self.env.cr.dbname,
                self.env.uid,
                dict(self.env.context),
                request.id,
                "OFFICE_DELIVERY_FAILED",
                "delivery",
                "publication failed",
            )

        request.invalidate_recordset(["state", "output_attachment_id"])
        self.assertEqual(result["state"], "generated")
        self.assertEqual(result["output_attachment_id"], output.id)
        self.assertFalse(result["delivery_message_id"])
        self.assertEqual(result["error_code"], "OFFICE_DELIVERY_FAILED")
        self.assertEqual(result["failed_stage"], "delivery")
        self.assertEqual(request.state, "generated")
        self.assertEqual(request.output_attachment_id, output)

    def test_identity_matrix(self):
        cases = [
            (
                "spoofed.xlsx",
                "text/plain",
                b"plain text pretending to be a workbook",
                True,
                True,
            ),
            (
                "valid.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"PK\x03\x04synthetic zip header",
                True,
                False,
            ),
            ("notes.txt", "text/plain; charset=utf-8", b"hello", False, False),
            ("picture.png", "image/png", b"\x89PNG\r\n\x1a\n", False, False),
            (
                "report.docx",
                "application/vnd.ms-excel",
                b"PK\x03\x04synthetic zip header",
                True,
                True,
            ),
            (
                "truncated.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"PK",
                True,
                True,
            ),
            (
                "legacy.doc",
                "application/msword",
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1synthetic OLE header",
                True,
                False,
            ),
            (
                "wrong-family.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1synthetic OLE header",
                True,
                True,
            ),
            (
                "wrong-family.xls",
                "application/vnd.ms-excel",
                b"PK\x03\x04synthetic zip header",
                True,
                True,
            ),
            ("plain.txt", "text/plain", b"PK\x03\x04zip payload", False, False),
        ]
        for name, mime, header, candidate, mismatch in cases:
            with self.subTest(name=name, mime=mime):
                result = inspect_attachment_identity(name, mime, header, len(header))
                self.assertEqual(result.is_office_candidate, candidate)
                self.assertEqual(result.is_mismatch, mismatch)

    def test_header_input_is_clamped_to_2048_bytes(self):
        result = inspect_attachment_identity(
            "notes.txt", "text/plain", b"x" * 10_000, 10_000
        )
        self.assertFalse(result.is_office_candidate)

    def _minimal_xlsx(self):
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.active.title = "Sheet1"
        workbook.active["A1"] = "客户名称"
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return output.getvalue()

    def test_valid_upload_preserves_instruction_without_office_binary(self):
        thread = self._thread()
        mimetype = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        valid_package = self._minimal_xlsx()
        with zipfile.ZipFile(io.BytesIO(valid_package), "r") as archive:
            self.assertIn("[Content_Types].xml", archive.namelist())
            self.assertIn("xl/workbook.xml", archive.namelist())

        valid_attachment = self._attachment(
            "minimal.xlsx", mimetype, valid_package
        )
        valid_header = thread._office_engine_attachment_header(valid_attachment)
        valid_identity = inspect_attachment_identity(
            valid_attachment.name,
            valid_attachment.mimetype,
            valid_header,
            valid_attachment.file_size,
        )
        self.assertTrue(valid_identity.is_office_candidate)
        self.assertFalse(valid_identity.is_mismatch)

        office_user_message = thread.message_post(
            body="请读取这个 Excel",
            llm_role="user",
            attachment_ids=[valid_attachment.id],
        )
        prepared = thread._prepare_chat_kwargs(office_user_message, False)
        serialized = thread.provider_id._dispatch(
            "format_messages", prepared["messages"], model=thread.model_id
        )
        self.assertEqual(serialized[0]["content"], "请读取这个 Excel")
        self.assertNotIn("base64", str(serialized))
        self.assertFalse(office_user_message.is_error)
        self.assertIn(valid_attachment.id, thread.get_llm_messages().mapped("attachment_ids").ids)

        damaged_package = bytearray(valid_package)
        central_directory = damaged_package.find(b"PK\x01\x02")
        self.assertGreaterEqual(central_directory, 0)
        damaged_package[central_directory : central_directory + 4] = b"XX\x01\x02"
        with self.assertRaises(zipfile.BadZipFile):
            with zipfile.ZipFile(io.BytesIO(damaged_package), "r") as archive:
                archive.namelist()

        damaged_attachment = self._attachment(
            "damaged-central-directory.xlsx", mimetype, bytes(damaged_package)
        )
        damaged_header = thread._office_engine_attachment_header(damaged_attachment)
        damaged_identity = inspect_attachment_identity(
            damaged_attachment.name,
            damaged_attachment.mimetype,
            damaged_header,
            damaged_attachment.file_size,
        )
        self.assertTrue(damaged_identity.is_office_candidate)
        damaged_message = thread.message_post(
            body="damaged package",
            llm_role="user",
            attachment_ids=[damaged_attachment.id],
        )
        prepared = thread._prepare_chat_kwargs(damaged_message, False)
        serialized = thread.provider_id._dispatch(
            "format_messages", prepared["messages"], model=thread.model_id
        )
        self.assertEqual(serialized[0]["content"], "damaged package")
        self.assertNotIn("base64", str(serialized))
        with self.assertRaises(OfficeCoreError):
            self.env["office.document.request"]._inspect_chat_attachment_document(
                damaged_attachment, thread, damaged_message
            )

    def test_ordinary_attachments_reach_real_openai_message_serializer(self):
        thread = self._thread()
        text_bytes = b"ordinary serialized text payload"
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lXcAAAAASUVORK5CYII="
        )
        text_attachment = self._attachment(
            "notes.txt", "text/plain", text_bytes
        )
        image_attachment = self._attachment(
            "pixel.png", "image/png", png_bytes
        )
        message = thread.message_post(
            body="ordinary chat message",
            llm_role="user",
            attachment_ids=[text_attachment.id, image_attachment.id],
        )

        self.assertEqual(thread._check_unsupported_attachments(message), [])
        self.assertFalse(message.is_error)
        serialized = thread.provider_id._dispatch(
            "format_messages", message, model=thread.model_id
        )

        self.assertEqual(len(serialized), 1)
        self.assertEqual(serialized[0]["role"], "user")
        self.assertEqual(
            serialized[0]["content"][0],
            {
                "type": "text",
                "text": "ordinary chat message\n\n--- notes.txt ---\n"
                "ordinary serialized text payload",
            },
        )
        self.assertEqual(
            serialized[0]["content"][1],
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,"
                    + base64.b64encode(png_bytes).decode("ascii")
                },
            },
        )

    def _thread(self):
        provider = self.env["llm.provider"].create(
            {"name": "Office gate test " + uuid4().hex, "service": "openai"}
        )
        model = self.env["llm.model"].create(
            {
                "name": "Office gate model " + uuid4().hex,
                "provider_id": provider.id,
                "model_use": "multimodal",
            }
        )
        return self.env["llm.thread"].create(
            {
                "name": "Office gate test thread " + uuid4().hex,
                "provider_id": provider.id,
                "model_id": model.id,
            }
        )

    def _attachment(self, name, mimetype, content):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "mimetype": mimetype,
                "datas": base64.b64encode(content),
            }
        )

    def test_spoofed_office_posts_error_message_and_stays_out_of_next_round(self):
        thread = self._thread()
        secret_body = "SPOOFED_ATTACHMENT_BODY_" + uuid4().hex
        attachment = self._attachment(
            "spoofed.xlsx", "text/plain", secret_body.encode("utf-8")
        )
        dispatched_histories = []

        def provider_stub(model, messages, **kwargs):
            dispatched_histories.append(messages)
            return iter([{"content": "local stub response"}])

        with patch.object(type(thread.model_id), "chat", provider_stub):
            rejected_events = list(thread.generate(
                user_message_body=secret_body,
                attachment_ids=[attachment.id],
            ))
        self.assertEqual(dispatched_histories, [])
        self.assertEqual([event["type"] for event in rejected_events], ["message_create"])
        error_id = rejected_events[0]["message"]["id"]
        error_message = self.env["mail.message"].browse(error_id)
        self.assertTrue(rejected_events[0]["message"]["is_error"])
        self.assertTrue(error_message.is_error)
        self.assertNotIn(secret_body, error_message.body)
        next_text = "NEXT_ROUND_TEXT_" + uuid4().hex

        with patch.object(type(thread.model_id), "chat", provider_stub):
            list(thread.generate(user_message_body=next_text))

        self.assertEqual(len(dispatched_histories), 1)
        history = dispatched_histories[0]
        self.assertNotIn(error_message.id, history.ids)
        self.assertIn(next_text, "\n".join(history.mapped("body")))
        self.assertNotIn(secret_body, "\n".join(history.mapped("body")))
        self.assertNotIn(attachment.id, history.mapped("attachment_ids").ids)

    def test_provider_preparation_excludes_office_attachment_in_history(self):
        thread = self._thread()
        attachment = self._attachment(
            "report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            self._minimal_xlsx(),
        )
        message = thread.message_post(
            body="historical attachment",
            llm_role="user",
            attachment_ids=[attachment.id],
        )
        prepared = thread._prepare_chat_kwargs(message, False)
        self.assertEqual(prepared["messages"], message)
        serialized = thread.provider_id._dispatch(
            "format_messages", prepared["messages"], model=thread.model_id
        )
        self.assertEqual(serialized[0]["role"], "user")
        self.assertIn("historical attachment", serialized[0]["content"])
        self.assertNotIn("base64", str(serialized))
        self.assertFalse(message.is_error)

    def test_office_only_upload_remains_visible_to_provider_without_binary(self):
        thread = self._thread()
        workbook = self._minimal_xlsx()
        attachment = self._attachment(
            "template-only.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            workbook,
        )
        message = thread.message_post(
            body="",
            llm_role="user",
            attachment_ids=[attachment.id],
        )

        serialized = thread.provider_id._dispatch(
            "format_messages", message, model=thread.model_id
        )

        self.assertEqual(len(serialized), 1)
        self.assertEqual(serialized[0]["role"], "user")
        self.assertIn("template-only.xlsx", serialized[0]["content"])
        self.assertIn("office_prepare_context", serialized[0]["content"])
        self.assertNotIn("base64", str(serialized))
        self.assertNotIn(base64.b64encode(workbook).decode("ascii"), str(serialized))

        provider_payloads = []

        def provider_stub(model, messages, **kwargs):
            provider_payloads.append(
                thread.provider_id._dispatch("format_messages", messages, model=model)
            )
            return iter([{"content": "I received the attached Office file."}])

        with patch.object(type(thread.model_id), "chat", provider_stub):
            events = list(thread.generate(attachment_ids=[attachment.id]))

        self.assertEqual(len(provider_payloads), 1)
        user_turns = [item for item in provider_payloads[0] if item.get("role") == "user"]
        upload_turns = [item for item in user_turns if "template-only.xlsx" in item["content"]]
        self.assertTrue(upload_turns)
        self.assertNotIn("base64", str(provider_payloads[0]))
        assistant_messages = self.env["mail.message"].search(
            [
                ("model", "=", thread._name),
                ("res_id", "=", thread.id),
                ("llm_role", "=", "assistant"),
                ("is_error", "=", False),
            ],
            order="id desc",
        )
        self.assertIn("I received the attached Office file.", assistant_messages[0].body)
        self.assertTrue(events)

    def test_malformed_office_candidate_is_rejected_before_provider(self):
        thread = self._thread()
        samples = [
            (
                "truncated.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"PK",
            ),
            (
                "damaged.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"PK\x03\x04not a complete zip package",
            ),
            (
                "legacy.doc",
                "application/msword",
                b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1synthetic OLE header",
            ),
        ]
        for name, mimetype, content in samples:
            attachment = self._attachment(name, mimetype, content)
            with patch.object(
                type(thread.model_id), "chat", side_effect=AssertionError("malformed Office must not reach Provider")
            ):
                events = list(thread.generate(user_message_body="broken", attachment_ids=[attachment.id]))
            self.assertTrue(events)
            self.assertTrue(self.env["mail.message"].browse(events[-1]["message"]["id"]).is_error)

    def test_ordinary_text_and_png_are_preserved_in_provider_stub_history(self):
        thread = self._thread()
        text = self._attachment("notes.txt", "text/plain", b"ordinary text payload")
        image = self._attachment("picture.png", "image/png", b"\x89PNG\r\n\x1a\nsynthetic png")
        dispatched_histories = []

        def provider_stub(model, messages, **kwargs):
            dispatched_histories.append(messages)
            return iter([{"content": "local stub response"}])

        with patch.object(type(thread.model_id), "chat", provider_stub):
            list(
                thread.generate(
                    user_message_body="Keep these ordinary attachments available",
                    attachment_ids=[text.id, image.id],
                )
            )

        self.assertEqual(len(dispatched_histories), 1)
        history = dispatched_histories[0]
        attachment_ids = history.mapped("attachment_ids").ids
        self.assertIn(text.id, attachment_ids)
        self.assertIn(image.id, attachment_ids)

    def test_ordinary_text_and_png_are_not_rejected_by_gate(self):
        thread = self._thread()
        text = self._attachment("notes.txt", "text/plain", b"ordinary text")
        image = self._attachment("picture.png", "image/png", b"\x89PNG\r\n\x1a\nbytes")
        message = thread.message_post(
            body="normal files",
            llm_role="user",
            attachment_ids=[text.id, image.id],
        )

        self.assertEqual(thread._check_unsupported_attachments(message), [])
        self.assertFalse(message.is_error)

    def test_filestore_header_read_returns_at_most_2048_bytes(self):
        thread = self._thread()
        content = b"PK\x03\x04" + b"x" * (5 * 1024 * 1024 - 4)
        attachment = self._attachment(
            "large.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content,
        )
        header = thread._office_engine_attachment_header(attachment)
        self.assertEqual(len(header), 2048)
        self.assertEqual(header, content[:2048])

        message = thread.message_post(
            body="synthetic large Office attachment",
            llm_role="user",
            attachment_ids=[attachment.id],
        )
        with patch(
            "zipfile.ZipFile",
            side_effect=AssertionError("provider preparation must not parse Office packages"),
        ) as zip_open:
            prepared = thread._prepare_chat_kwargs(message, False)
        self.assertEqual(prepared["messages"], message)
        self.assertIn("synthetic large Office attachment", str(prepared["messages"].mapped("body")))
        serialized = thread.provider_id._dispatch(
            "format_messages", prepared["messages"], model=thread.model_id
        )
        self.assertEqual(serialized[0]["content"], "synthetic large Office attachment")
        self.assertNotIn("base64", str(serialized))
        zip_open.assert_not_called()

    def test_header_read_uses_current_user_attachment_access(self):
        thread = self._thread()
        portal_user = self.env["res.users"].create(
            {
                "name": "Office gate portal " + uuid4().hex,
                "login": "office-gate-portal-" + uuid4().hex,
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        attachment = self._attachment("private.xlsx", "text/plain", b"not office")
        with self.assertRaises(AccessError):
            thread.with_user(portal_user)._office_engine_attachment_header(
                attachment.with_user(portal_user)
            )
