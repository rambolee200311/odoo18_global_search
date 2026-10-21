"""Read-only preflight for the CC-OFFICE-M1-003 attachment spike.

Execute inside the approved Odoo shell. The shell bootstrap env is used only to
select identities and inspect runtime metadata; attachment searches use an
explicit non-system internal user environment with su=False.
"""
import hashlib
import json
import os
import uuid

from odoo import api, SUPERUSER_ID, release


TOKEN = os.environ.get("OFFICE_SPIKE_TOKEN")
if not TOKEN or not TOKEN.isalnum():
    raise RuntimeError("OFFICE_SPIKE_TOKEN must be an alphanumeric unique marker")

bootstrap = env
assert bootstrap.uid == SUPERUSER_ID and bootstrap.su

internal_group = bootstrap.ref("base.group_user")
system_group = bootstrap.ref("base.group_system")
candidate_users = bootstrap["res.users"].search([
    ("id", "in", [97, 98, 99, 102, 103, 6]),
    ("active", "=", True),
    ("share", "=", False),
    ("groups_id", "in", internal_group.id),
    ("groups_id", "not in", system_group.id),
])
if len(candidate_users) < 2:
    raise RuntimeError("Need two existing active non-system internal users")
user_a_id, user_b_id = candidate_users[:2].ids

names = [
    f"TEST_SPIKE_MARK_{TOKEN}_CTRL.bin",
    f"TEST_SPIKE_MARK_{TOKEN}_ROLLBACK.bin",
]
payloads = [
    f"attachment-spike-control:{TOKEN}:synthetic-v1".encode("ascii"),
    f"attachment-spike-rollback:{TOKEN}:synthetic-v1".encode("ascii"),
]
checksums = [hashlib.sha1(payload).hexdigest() for payload in payloads]

cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, user_a_id, {}, su=False)
    user_b = api.Environment(cr, user_b_id, {}, su=False)
    if user_a.su or user_b.su or user_a.uid == SUPERUSER_ID or user_b.uid == SUPERUSER_ID:
        raise RuntimeError("Non-system user context assertion failed")
    if not user_a.user.has_group("base.group_user") or user_a.user.has_group("base.group_system"):
        raise RuntimeError("User A is not a non-system internal user")
    if not user_b.user.has_group("base.group_user") or user_b.user.has_group("base.group_system"):
        raise RuntimeError("User B is not a non-system internal user")

    AttachmentA = user_a["ir.attachment"]
    if AttachmentA._storage() != "file":
        raise RuntimeError("Attachment storage is not file; do not change configuration")
    for name in names:
        if AttachmentA.search_count([("name", "=", name)]):
            raise RuntimeError("Unique marker already exists; stop without mutation")

    root = os.path.realpath(AttachmentA._filestore())
    path_status = []
    for checksum in checksums:
        fname = f"{checksum[:2]}/{checksum}"
        full_path = os.path.realpath(os.path.join(root, fname))
        gc_path = os.path.realpath(os.path.join(root, "checklist", fname))
        if os.path.commonpath([root, full_path]) != root or os.path.commonpath([root, gc_path]) != root:
            raise RuntimeError("Derived filestore path escaped root")
        if os.path.exists(full_path) or os.path.exists(gc_path):
            raise RuntimeError("Candidate checksum path already exists; stop without mutation")
        path_status.append({"expected_store_fname": fname, "object_exists": False, "gc_entry_exists": False})

    result = {
        "preflight_id": str(uuid.uuid4()),
        "token": TOKEN,
        "runtime": {
            "odoo_version": release.version,
            "python_version": __import__("sys").version.split()[0],
            "database": cr.dbname,
            "postgresql_version": cr._cnx.server_version,
            "storage_mode": AttachmentA._storage(),
        },
        "users": {"user_a_id": user_a_id, "user_b_id": user_b_id,
                  "user_a_su": user_a.su, "user_b_su": user_b.su},
        "markers_absent": True,
        "payload_checksums": checksums,
        "candidate_paths": path_status,
    }
    print("OFFICE_SPIKE_PREFLIGHT=" + json.dumps(result, sort_keys=True))
finally:
    cr.rollback()
    cr.close()
