"""One-shot synthetic race runner for the owner-approved CB-02 amendment.

Run as a direct Odoo ORM process, without starting/stopping the HTTP service:
    ./venv/bin/python docs/implementation/evidence/CB-M2-CB-02/run-concurrency-acceptance-shell.py

The script commits a uniquely tagged synthetic version lineage because its
version rows and bound attachments are intentionally immutable. It refuses to
run twice with the same tag. No provider call or business record mutation is
performed.
"""

import hashlib
import json
import threading
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mymodules"))
import odoo
from odoo.tools import config

# Initialize the configured Odoo environment, then use Registry/cursors
# directly. This deliberately avoids `odoo-bin shell` server.start(), which
# is unnecessary for ORM work and can attempt process-wide shutdown handling.
config.parse_config(["-c", "odoo.conf", "-d", "odoo18ce"])
from odoo import api
from odoo.modules.registry import Registry

from odoo.addons.office_engine_m2.tests.integration.test_workbook_version_race import (
    race_accept_two_candidates,
)
from odoo.addons.office_engine_m2.tests.support import (
    XLSX_MIMETYPE,
    WorkbookVersionFixtures,
    attachment_values,
    synthetic_xlsx,
)
from odoo.addons.office_engine_m2.tests.support.validator_stub import verified_receipt
from odoo.addons.office_engine_m2.services.workbook_version_service import (
    CandidateAcceptanceAuthorization,
    accept_verified_candidate,
    record_validation_receipt,
    register_candidate,
    register_initial_v1,
)
from odoo.addons.office_engine_m2.services.mapping_service import create_session
from odoo.exceptions import ValidationError


TAG = "CB02-AMEND-ACCEPT-RACE-20261108-01"
PREFIX = TAG + "-"


def run(shell_env):
    # `odoo-bin shell` starts as Odoo's shell identity. Use the ordinary
    # Administrator user for all created business/session/version records so
    # the service still enforces its normal current-user ORM checks.
    admin = shell_env.ref("base.user_admin")
    company = admin.company_id
    ctx = {"allowed_company_ids": [company.id]}
    user_env = api.Environment(shell_env.cr, admin.id, ctx)

    if user_env["llm.thread"].search_count([("name", "=", TAG)]):
        raise RuntimeError(f"Refusing duplicate execution for synthetic tag {TAG}")

    provider = shell_env["llm.provider"].search([("service", "=", "openai")], limit=1)
    if not provider:
        raise RuntimeError("No existing OpenAI Provider record is available for a no-call synthetic Thread")
    model = shell_env["llm.model"].search(
        [("provider_id", "=", provider.id), ("model_use", "in", ["chat", "multimodal"])],
        limit=1,
    )
    if not model:
        raise RuntimeError("No existing chat-capable model record is available for the synthetic Thread")

    target = user_env["res.partner"].browse(admin.partner_id.id).exists()
    target.check_access("read")
    thread = user_env["llm.thread"].create(
        {"name": TAG, "provider_id": provider.id, "model_id": model.id}
    )
    source_bytes = synthetic_xlsx(PREFIX + "source")
    source = user_env["ir.attachment"].create(
        attachment_values(
            PREFIX + "source.xlsx",
            source_bytes,
            company_id=company.id,
        )
    )
    message = thread.message_post(
        body="Synthetic CB-02 concurrency acceptance fixture.",
        llm_role="user",
        attachment_ids=[source.id],
    )
    context = create_session(
        user_env,
        thread_id=thread.id,
        source_message_id=message.id,
        source_attachment_id=source.id,
        target_model=target._name,
        target_record_id=target.id,
    )
    session = user_env["office.mapping.session"].browse(context["session_id"])

    request, _m1_output = WorkbookVersionFixtures()._m1_request_fixture(user_env, session)
    v1 = register_initial_v1(user_env, session.id, request.id)
    session.invalidate_recordset()
    if session.current_version_id != v1 or session.document_revision != 1:
        raise AssertionError("Synthetic V1 did not become current at document revision 1")

    candidates = []
    review_message_ids = {}
    for label in ("a", "b"):
        payload = synthetic_xlsx(PREFIX + "candidate-" + label)
        digest = hashlib.sha256((PREFIX + "request-" + label).encode()).hexdigest()
        intent = thread.message_post(
            body="Synthetic edit Intent " + PREFIX + label,
            llm_role="user",
            author_id=admin.partner_id.id,
        )
        candidate = register_candidate(
            user_env,
            session.id,
            parent_version_id=v1.id,
            expected_document_revision=1,
            candidate_bytes=payload,
            filename=PREFIX + "candidate-" + label + ".xlsx",
            mimetype=XLSX_MIMETYPE,
            idempotency_key=PREFIX + "candidate-" + label,
            request_digest=digest,
            intent_effect_digest=hashlib.sha256((PREFIX + "effect-" + label).encode()).hexdigest(),
            intent_message_id=intent.id,
        )
        record_validation_receipt(user_env, candidate.id, verified_receipt(candidate))
        candidates.append(candidate)
        review = thread.message_post(
            body="Accept synthetic Candidate " + label,
            llm_role="user",
            author_id=admin.partner_id.id,
        )
        review_message_ids[candidate.id] = review.id

    # Make only this uniquely tagged synthetic fixture visible to independent
    # racing transactions. The approved amendment permits retaining it because
    # version history and bound attachments are immutable.
    user_env.cr.commit()
    print(json.dumps({
        "phase": "fixture_committed",
        "tag": TAG,
        "owner_uid": admin.id,
        "company_id": company.id,
        "thread_id": thread.id,
        "session_id": session.id,
        "v1_id": v1.id,
        "candidate_ids": [item.id for item in candidates],
        "document_revision": 1,
        "provider_calls": 0,
        "synthetic_only": True,
    }, sort_keys=True), flush=True)

    def accept_with_review(env, candidate_id):
        candidate = env["office.workbook.version"].browse(candidate_id).exists()
        authorization = CandidateAcceptanceAuthorization(
            authorization_kind="candidate_review",
            candidate_version_id=candidate.id,
            session_id=candidate.session_id.id,
            owner_id=env.uid,
            thread_id=candidate.thread_id.id,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=review_message_ids[candidate.id],
            parent_version_id=candidate.parent_version_id.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest or False,
        )
        return accept_verified_candidate(env, candidate.id, authorization)

    outcomes = race_accept_two_candidates(
        shell_env.registry,
        admin.id,
        ctx,
        accept_with_review,
        [item.id for item in candidates],
    )
    if len({item[2] for item in outcomes}) != 2 or any(not item[2] for item in outcomes):
        raise AssertionError(f"The race did not use two distinct database backends: {outcomes!r}")

    user_env.invalidate_all()
    session = user_env["office.mapping.session"].browse(context["session_id"])
    versions = user_env["office.workbook.version"].browse([item.id for item in candidates]).exists()
    accepted = versions.filtered(lambda item: item.state == "accepted_current")
    pending = versions - accepted
    if len(accepted) != 1 or len(pending) != 1:
        raise AssertionError(f"Expected exactly one accepted candidate, got states={versions.mapped('state')!r}")
    winner = accepted
    loser = pending
    if (
        session.current_version_id != winner
        or session.last_valid_version_id != winner
        or session.document_revision != 2
        or winner.accepted_document_revision != 2
        or winner.parent_version_id != v1
        or loser.parent_version_id != v1
        or v1.state != "superseded"
    ):
        raise AssertionError("Current/last-valid/revision or parent-chain state is inconsistent after the race")

    for version in versions:
        attachment = version.output_attachment_id
        attachment.check_access("read")
        actual_sha = hashlib.sha256(attachment.raw or b"").hexdigest()
        if (
            attachment.res_model != version._name
            or attachment.res_id != version.id
            or actual_sha != version.output_sha256
            or version.validation_result != "VERIFIED"
        ):
            raise AssertionError(f"Candidate attachment/proof binding mismatch for version {version.id}")

    try:
        accept_with_review(user_env, loser.id)
    except ValidationError as exc:
        if "WORKBOOK_VERSION_STALE" not in str(exc):
            raise AssertionError(f"The losing candidate did not fail stale revalidation: {exc}") from exc
        loser_retry = "WORKBOOK_VERSION_STALE"
    else:
        raise AssertionError("The losing candidate was accepted on a later attempt")

    print(json.dumps({
        "phase": "race_verified",
        "tag": TAG,
        "outcomes": outcomes,
        "backend_pids": sorted(item[2] for item in outcomes),
        "winner_version_id": winner.id,
        "loser_version_id": loser.id,
        "winner_state": winner.state,
        "loser_state": loser.state,
        "current_version_id": session.current_version_id.id,
        "last_valid_version_id": session.last_valid_version_id.id,
        "document_revision": session.document_revision,
        "loser_retry": loser_retry,
        "attachment_sha_checks": "PASS",
        "retained_synthetic_lineage": TAG,
    }, sort_keys=True), flush=True)
    user_env.cr.rollback()


database = config["db_name"]
threading.current_thread().dbname = database
registry = Registry(database)
with registry.cursor() as cursor:
    shell_env = api.Environment(cursor, odoo.SUPERUSER_ID, {})
    run(shell_env)
    cursor.rollback()
