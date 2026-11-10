"""Test-only fixtures for workbook-version TransactionCase tests."""

import base64
import hashlib
from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook

from odoo.addons.office_engine_m2.services.mapping_service import create_session


XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def synthetic_xlsx(label):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet"
    sheet["A1"] = label
    sheet["B1"] = 10
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def attachment_values(name, content, *, company_id, res_model=False, res_id=False):
    return {
        "name": name,
        "type": "binary",
        "raw": content,
        "mimetype": XLSX_MIMETYPE,
        "company_id": company_id,
        "public": False,
        "res_model": res_model,
        "res_id": res_id,
    }


class WorkbookVersionFixtures:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.provider = cls.env["llm.provider"].create(
            {"name": "Workbook Version Test Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "Workbook Version Test Model " + uuid4().hex,
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )
        cls.owner = cls._make_user("owner", cls.env.company)
        cls.other_user = cls._make_user("other", cls.env.company)

    @classmethod
    def _make_user(cls, label, company):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Workbook Version " + label,
                "login": "workbook-version-" + label + "-" + uuid4().hex,
                "email": "workbook-version-" + uuid4().hex + "@example.invalid",
                "groups_id": [(6, 0, [cls.group_user.id])],
                "company_ids": [(6, 0, [company.id])],
                "company_id": company.id,
            }
        )

    def _session_fixture(self, user=None):
        user = user or self.owner
        company = user.company_id
        env = self.env(user=user.id, context={"allowed_company_ids": [company.id]})
        # The standard internal-user group may read its own partner but is not
        # granted Contact Creation. Reuse that test user's existing partner so
        # these version-service fixtures exercise the real user ACL instead of
        # depending on an unrelated contact-creation privilege.
        target = env["res.partner"].browse(user.partner_id.id)
        target.check_access("read")
        thread = env["llm.thread"].create(
            {
                "name": "Synthetic version thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        source_bytes = synthetic_xlsx("source-" + uuid4().hex)
        attachment = env["ir.attachment"].create(
            attachment_values(
                "synthetic-source-" + uuid4().hex + ".xlsx",
                source_bytes,
                company_id=company.id,
            )
        )
        message = thread.message_post(
            body="Synthetic workbook version test.",
            llm_role="user",
            attachment_ids=[attachment.id],
        )
        created = create_session(
            env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=attachment.id,
            target_model=target._name,
            target_record_id=target.id,
        )
        session = env["office.mapping.session"].browse(created["session_id"])
        return env, session, thread, message, attachment

    def _m1_request_fixture(self, env, session, output_bytes=None, *, include_proof=True):
        from odoo.addons.office_engine_odoo.models.office_document_request import _internal_mutation

        output_bytes = output_bytes or synthetic_xlsx("m1-output-" + uuid4().hex)
        request_model = env["office.document.request"]
        output_sha = hashlib.sha256(output_bytes).hexdigest()
        input_sha = hashlib.sha256(session.source_attachment_id.raw or b"").hexdigest()
        with _internal_mutation():
            request = request_model.create(
                {
                    "request_uuid": str(uuid4()),
                    "owner_id": env.uid,
                    "thread_id": session.thread_id.id,
                    "input_message_id": session.source_message_id.id,
                    "source_attachment_id": session.source_attachment_id.id,
                    "input_sha256": input_sha,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})
            output = env["ir.attachment"].create(
                attachment_values(
                    "synthetic-m1-output-" + uuid4().hex + ".xlsx",
                    output_bytes,
                    company_id=session.company_id.id,
                    res_model=request._name,
                    res_id=request.id,
                )
            )
            proof = {}
            if include_proof:
                from odoo.addons.office_engine_m2.services.workbook_version_service import (
                    M1_VALIDATOR_POLICY_VERSION,
                )

                report_digest = hashlib.sha256(
                    (input_sha + output_sha + "test-report").encode()
                ).hexdigest()
                proof = {
                    "m1_validation_status": "VERIFIED",
                    "m1_validator_policy_version": M1_VALIDATOR_POLICY_VERSION,
                    "m1_validation_report_id": report_digest,
                    "m1_validation_report_sha256": report_digest,
                    "m1_validation_input_sha256": input_sha,
                    "m1_validation_output_sha256": output_sha,
                    "m1_validation_completed_at": "2026-11-06 09:00:00",
                    "m1_version_session_id": session.id,
                    "m1_version_session_revision": session.revision,
                    "m1_version_proposal_revision": session.proposal_revision,
                }
            request.write(
                {
                    "state": "generated",
                    "output_attachment_id": output.id,
                    "output_sha256": output_sha,
                    **proof,
                }
            )
        return request, output

    def _versioned_session_fixture(self):
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_initial_v1

        env, session, thread, message, source = self._session_fixture()
        request, output = self._m1_request_fixture(env, session)
        version = register_initial_v1(env, session.id, request.id)
        session.invalidate_recordset()
        return env, session, thread, message, source, request, output, version

    def _register_candidate(self, env, session, **values):
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_candidate

        message_id = values.pop("intent_message_id", False)
        if not message_id:
            message = session.thread_id.message_post(
                body="Synthetic workbook edit Intent: " + values["idempotency_key"],
                llm_role="user",
                author_id=env.user.partner_id.id,
            )
            message_id = message.id
        return register_candidate(env, session.id, intent_message_id=message_id, **values)

    def _accept_candidate(self, env, candidate):
        from odoo.addons.office_engine_m2.services.workbook_version_service import (
            CandidateAcceptanceAuthorization,
            accept_verified_candidate,
        )

        if candidate.version_kind == "restore":
            return accept_verified_candidate(env, candidate.id)
        decision = candidate.thread_id.message_post(
            body="Accept synthetic workbook Candidate " + candidate.version_uuid,
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        authorization = CandidateAcceptanceAuthorization(
            authorization_kind="candidate_review",
            candidate_version_id=candidate.id,
            session_id=candidate.session_id.id,
            owner_id=env.uid,
            thread_id=candidate.thread_id.id,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=decision.id,
            parent_version_id=candidate.parent_version_id.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest or False,
        )
        return accept_verified_candidate(env, candidate.id, authorization)

    def _reject_candidate(self, env, candidate):
        from odoo.addons.office_engine_m2.services.workbook_version_service import (
            CandidateRejection,
            reject_verified_candidate,
        )

        decision = candidate.thread_id.message_post(
            body="Reject synthetic workbook Candidate " + candidate.version_uuid,
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        rejection = CandidateRejection(
            candidate_version_id=candidate.id,
            session_id=candidate.session_id.id,
            owner_id=env.uid,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=decision.id,
            parent_version_id=candidate.parent_version_id.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest or False,
        )
        return reject_verified_candidate(env, candidate.id, rejection)
