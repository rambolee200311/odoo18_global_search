"""Odoo ACL, Record Rule, and linked attachment access tests."""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures
from ..services.mapping_service import get_workbook_version_summary, list_workbook_version_summaries


class TestWorkbookVersionAccess(WorkbookVersionFixtures, TransactionCase):
    def test_authorized_read_summaries_are_bounded_and_private(self):
        env, session, _thread, _message, _source, _request, _output, version = self._versioned_session_fixture()
        summary = get_workbook_version_summary(env, session.id, version.id)
        self.assertEqual(summary["output_sha256"], version.output_sha256)
        self.assertNotIn("content", summary)
        self.assertEqual(list_workbook_version_summaries(env, session.id)[0]["version_id"], version.id)
        with self.assertRaises(ValidationError):
            list_workbook_version_summaries(env, session.id, limit=True)

        other_env = self.env(
            user=self.other_user.id,
            context={"allowed_company_ids": [self.other_user.company_id.id]},
        )
        with self.assertRaises(AccessError):
            get_workbook_version_summary(other_env, session.id, version.id)
        with self.assertRaises(AccessError):
            list_workbook_version_summaries(other_env, session.id)

    def test_owner_only_version_and_attachment_access(self):
        env, session, _thread, _message, _source, _request, _output, version = self._versioned_session_fixture()
        other_env = self.env(
            user=self.other_user.id,
            context={"allowed_company_ids": [self.other_user.company_id.id]},
        )
        self.assertFalse(other_env["office.workbook.version"].search([("id", "=", version.id)]))
        with self.assertRaises(AccessError):
            version.with_env(other_env).check_access("read")
        with self.assertRaises(AccessError):
            version.output_attachment_id.with_env(other_env).check("read")
        with self.assertRaises(AccessError):
            version.with_env(other_env).write({"state": "accepted_current"})
        self.assertEqual(session.current_version_id, version)

    def test_cross_company_user_cannot_read_version_or_private_attachment(self):
        env, session, _thread, _message, _source, _request, _output, version = self._versioned_session_fixture()
        # Reuse an existing company: this access test does not need to create
        # business setup records, and the host database may require additional
        # company-specific fields on res.company.
        other_company = self.env.companies.filtered(lambda company: company != self.env.company)[:1]
        self.assertTrue(other_company, "The access test requires a second configured company.")
        other_company = other_company.ensure_one()
        other_company_user = self._make_user("other-company", other_company)
        other_env = self.env(
            user=other_company_user.id,
            context={"allowed_company_ids": [other_company.id]},
        )
        with self.assertRaises(AccessError):
            version.with_env(other_env).check_access("read")
        with self.assertRaises(AccessError):
            version.output_attachment_id.with_env(other_env).check("read")

    def test_same_owner_cannot_rebind_version_to_another_session(self):
        env, session, _thread, _message, _source, _request, _output, version = self._versioned_session_fixture()
        _other_env, other_session, _other_thread, _other_message, _other_source = self._session_fixture()
        with self.assertRaises(AccessError):
            get_workbook_version_summary(env, other_session.id, version.id)
