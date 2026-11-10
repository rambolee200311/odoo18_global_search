"""Read-only ORM and XLSX verification for the approved synthetic race lineage."""

import hashlib
import json
import sys
import threading
import zipfile
from io import BytesIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "mymodules"))

import odoo
from odoo import api
from odoo.modules.registry import Registry
from odoo.tools import config

config.parse_config(["-c", "odoo.conf", "-d", "odoo18ce"])

TAG = "CB02-CONCURRENCY-APPROVED-20261107-01"
database = config["db_name"]
threading.current_thread().dbname = database
registry = Registry(database)

with registry.cursor() as cursor:
    root_env = api.Environment(cursor, odoo.SUPERUSER_ID, {})
    admin = root_env.ref("base.user_admin")
    env = api.Environment(cursor, admin.id, {"allowed_company_ids": [admin.company_id.id]})

    threads = env["llm.thread"].search([("name", "=", TAG)])
    assert len(threads) == 1, f"expected one tagged synthetic Thread, got {len(threads)}"
    thread = threads
    sessions = env["office.mapping.session"].search([("thread_id", "=", thread.id)])
    assert len(sessions) == 1, f"expected one Session, got {len(sessions)}"
    session = sessions
    versions = env["office.workbook.version"].search(
        [("session_id", "=", session.id)], order="version_no, id"
    )
    assert len(versions) == 3, f"expected exactly V1 and two candidates, got {len(versions)}"
    v1, candidate_a, candidate_b = versions
    winner = versions.filtered(lambda item: item.state == "accepted_current")
    loser = versions.filtered(lambda item: item.version_kind == "edit" and item.state == "verified")
    assert len(winner) == len(loser) == 1
    assert (v1.version_no, candidate_a.version_no, candidate_b.version_no) == (1, 2, 3)
    assert v1.state == "superseded"
    assert session.current_version_id == session.last_valid_version_id == winner
    assert session.document_revision == winner.accepted_document_revision == 2
    assert session.owner_id == admin and session.thread_id == thread

    expected_version_attachments = set(versions.mapped("output_attachment_id").ids)
    bound_attachments = env["ir.attachment"].search(
        [
            ("res_model", "=", "office.workbook.version"),
            ("res_id", "in", versions.ids),
        ]
    )
    assert set(bound_attachments.ids) == expected_version_attachments, (
        "version-owned attachment set differs from the exact output attachments"
    )

    file_checks = []
    for version in versions:
        assert version.session_id == session
        assert version.owner_id == admin
        assert version.company_id == session.company_id
        assert version.thread_id == thread
        if version == v1:
            assert version.input_attachment_id == session.source_attachment_id
            assert not version.parent_version_id
        else:
            assert version.parent_version_id == v1
            assert version.input_attachment_id == v1.output_attachment_id
        attachment = version.output_attachment_id
        attachment.check_access("read")
        raw = attachment.raw or b""
        digest = hashlib.sha256(raw).hexdigest()
        assert attachment.public is False
        assert attachment.res_model == version._name and attachment.res_id == version.id
        assert digest == version.output_sha256
        with zipfile.ZipFile(BytesIO(raw)) as package:
            assert package.testzip() is None
        from openpyxl import load_workbook

        workbook = load_workbook(BytesIO(raw), data_only=False, read_only=True)
        assert workbook.sheetnames == ["Sheet"]
        file_checks.append({
            "version_id": version.id,
            "state": version.state,
            "output_attachment_id": attachment.id,
            "sha256": digest,
            "size": len(raw),
            "xlsx_zip": "PASS",
            "openpyxl_readback": "PASS",
        })
        workbook.close()

    print(json.dumps({
        "status": "PASS",
        "tag": TAG,
        "thread_id": thread.id,
        "session_id": session.id,
        "version_ids": versions.ids,
        "version_count": len(versions),
        "version_attachment_count": len(bound_attachments),
        "winner_id": winner.id,
        "loser_id": loser.id,
        "current_id": session.current_version_id.id,
        "last_valid_id": session.last_valid_version_id.id,
        "document_revision": session.document_revision,
        "files": file_checks,
        "business_records_modified": False,
    }, sort_keys=True), flush=True)
    cursor.rollback()
