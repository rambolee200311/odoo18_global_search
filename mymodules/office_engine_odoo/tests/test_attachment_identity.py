import base64
import io
import zipfile
from unittest.mock import patch
from uuid import uuid4

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase

from ..services import inspect_attachment_identity


class TestAttachmentIdentity(TransactionCase):
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

    def test_valid_minimal_ooxml_and_damaged_central_directory_fail_closed(self):
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

        with patch.object(
            type(thread.model_id), "chat", side_effect=AssertionError("Office files must not reach Provider")
        ):
            events = list(
                thread.generate(
                    user_message_body="请读取这个 Excel",
                    attachment_ids=[valid_attachment.id],
                )
            )
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "message_create")
        self.assertEqual(events[1]["type"], "message_create")
        office_user_message = self.env["mail.message"].browse(events[0]["message"]["id"])
        self.assertFalse(office_user_message.is_error)
        response_message = self.env["mail.message"].browse(events[1]["message"]["id"])
        self.assertFalse(response_message.is_error)
        self.assertIn("文件已接收并完成安全结构检查", response_message.body)
        self.assertNotIn(valid_attachment.id, thread.get_llm_messages().mapped("attachment_ids").ids)

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
        # Valid OOXML enters the internal parser; a corrupt central directory
        # is rejected before any Provider call and rendered as an error event.
        with patch.object(
            type(thread.model_id), "chat", side_effect=AssertionError("invalid Office must not reach Provider")
        ):
            events = list(
                thread.generate(
                    user_message_body="damaged package",
                    attachment_ids=[damaged_attachment.id],
                )
            )
        self.assertEqual(len(events), 2)
        rejected = self.env["mail.message"].browse(events[0]["message"]["id"])
        self.assertTrue(rejected.is_error)
        error = self.env["mail.message"].browse(events[1]["message"]["id"])
        self.assertTrue(error.is_error)

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
        self.assertFalse(prepared["messages"])
        self.assertFalse(message.is_error)

    def test_malformed_office_candidates_fail_closed_without_archive_parsing(self):
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
        self.assertFalse(prepared["messages"])
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
