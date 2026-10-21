"""Create/commit one synthetic control attachment and rollback one probe.

Run only inside the already-approved Odoo shell on odoo18ce. All attachment
operations use existing non-system internal user environments (su=False).
"""
import base64
import hashlib
import json
import os
import uuid

from odoo import api, SUPERUSER_ID


TOKEN = os.environ.get("OFFICE_SPIKE_TOKEN")
USER_A_ID = 97
USER_B_ID = 98
if not TOKEN or not TOKEN.isalnum():
    raise RuntimeError("OFFICE_SPIKE_TOKEN must be alphanumeric")

CONTROL_NAME = f"TEST_SPIKE_MARK_{TOKEN}_CTRL.bin"
ROLLBACK_NAME = f"TEST_SPIKE_MARK_{TOKEN}_ROLLBACK.bin"
CONTROL_PAYLOAD = f"attachment-spike-control:{TOKEN}:synthetic-v1".encode("ascii")
ROLLBACK_PAYLOAD = f"attachment-spike-rollback:{TOKEN}:synthetic-v1".encode("ascii")
control_sha = hashlib.sha1(CONTROL_PAYLOAD).hexdigest()
rollback_sha = hashlib.sha1(ROLLBACK_PAYLOAD).hexdigest()

def checked_path(root, relative):
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, relative))
    if os.path.commonpath([root, path]) != root:
        raise RuntimeError("Derived path escaped filestore root")
    return path

bootstrap = env
assert bootstrap.uid == SUPERUSER_ID and bootstrap.su
results = {"token": TOKEN, "tests": {}, "markers": {"control": CONTROL_NAME, "rollback": ROLLBACK_NAME}}

# Recheck both names and exact content-derived file paths immediately before
# any attachment write. These checks are under the non-system user context.
cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    user_b = api.Environment(cr, USER_B_ID, {}, su=False)
    if user_a.su or user_b.su or SUPERUSER_ID in (user_a.uid, user_b.uid):
        raise RuntimeError("Non-system su=False assertion failed")
    if not user_a.user.has_group("base.group_user") or user_a.user.has_group("base.group_system"):
        raise RuntimeError("User A is not a non-system internal user")
    if not user_b.user.has_group("base.group_user") or user_b.user.has_group("base.group_system"):
        raise RuntimeError("User B is not a non-system internal user")
    AttachmentA = user_a["ir.attachment"]
    if AttachmentA._storage() != "file":
        raise RuntimeError("Attachment storage changed from file")
    for name in (CONTROL_NAME, ROLLBACK_NAME):
        if AttachmentA.search_count([("name", "=", name)]):
            raise RuntimeError("Unique marker conflict; no write attempted")
    root = AttachmentA._filestore()
    for checksum in (control_sha, rollback_sha):
        fname = f"{checksum[:2]}/{checksum}"
        if os.path.exists(checked_path(root, fname)) or os.path.exists(checked_path(root, "checklist/" + fname)):
            raise RuntimeError("Checksum path conflict; no write attempted")
    results["tests"]["prewrite_recheck"] = "PASS"
finally:
    cr.rollback()
    cr.close()

# A committed personal attachment is the control and cleanup target.
cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    attachment = user_a["ir.attachment"].create({
        "name": CONTROL_NAME,
        "type": "binary",
        "mimetype": "application/octet-stream",
        "public": False,
        "datas": base64.b64encode(CONTROL_PAYLOAD).decode("ascii"),
    })
    control_id = attachment.id
    control_fname = attachment.store_fname
    control_file_before_commit = os.path.exists(checked_path(attachment._filestore(), control_fname))
    control_gc_before_commit = os.path.exists(checked_path(attachment._filestore(), "checklist/" + control_fname))
    cr.commit()
finally:
    cr.close()

# Re-read committed bytes in a fresh transaction; then verify B cannot access
# the unlinked private attachment either through search or direct ACL checking.
cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    control = user_a["ir.attachment"].browse(control_id).exists()
    if len(control) != 1 or control.name != CONTROL_NAME or control.create_uid.id != USER_A_ID:
        raise AssertionError("Committed control attachment identity/owner mismatch")
    readback = control.raw
    if isinstance(readback, str):
        readback = readback.encode("latin1")
    if hashlib.sha1(readback or b"").hexdigest() != control_sha:
        raise AssertionError("Committed attachment bytes differ from synthetic payload")
    results["tests"]["commit_readback"] = {
        "status": "PASS", "attachment_id": control_id,
        "sha1_matches": True, "owner_is_user_a": True,
        "filestore_object_exists": os.path.exists(checked_path(control._filestore(), control_fname)),
        "gc_entry_exists": os.path.exists(checked_path(control._filestore(), "checklist/" + control_fname)),
    }

    user_b = api.Environment(cr, USER_B_ID, {}, su=False)
    visible = user_b["ir.attachment"].search([("id", "=", control_id)])
    from odoo.exceptions import AccessError
    try:
        user_b["ir.attachment"].browse(control_id).check("read")
    except AccessError:
        denied = True
    else:
        denied = False
    if visible or not denied:
        raise AssertionError("User B unexpectedly accessed User A's private attachment")
    results["tests"]["cross_user_acl"] = {
        "status": "PASS", "search_visible": False,
        "direct_read_denied": True, "user_a_su": user_a.su,
        "user_b_su": user_b.su,
    }
finally:
    cr.rollback()
    cr.close()

# Create distinct bytes in an isolated cursor, observe only this probe's object
# and GC marker, then explicitly roll back. Do not query its DB visibility in
# this process; that check must be made by a separate fresh Odoo shell.
cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    rollback = user_a["ir.attachment"].create({
        "name": ROLLBACK_NAME,
        "type": "binary",
        "mimetype": "application/octet-stream",
        "public": False,
        "datas": base64.b64encode(ROLLBACK_PAYLOAD).decode("ascii"),
    })
    rollback_id = rollback.id
    rollback_fname = rollback.store_fname
    if rollback_fname != f"{rollback_sha[:2]}/{rollback_sha}":
        raise AssertionError("Odoo store_fname does not match expected unique probe checksum")
    rollback_file_in_tx = os.path.exists(checked_path(rollback._filestore(), rollback_fname))
    rollback_gc_in_tx = os.path.exists(checked_path(rollback._filestore(), "checklist/" + rollback_fname))
    cr.rollback()
finally:
    cr.close()

results["tests"]["rollback_probe"] = {
    "status": "PASS", "attachment_id_before_rollback": rollback_id,
    "store_fname": rollback_fname,
    "payload_sha1": rollback_sha,
    "object_exists_before_rollback": rollback_file_in_tx,
    "gc_entry_exists_before_rollback": rollback_gc_in_tx,
    "explicit_rollback_completed": True,
    "database_absence_check": "MUST RUN IN SEPARATE ODOO SHELL",
}
print("OFFICE_SPIKE_PROBE=" + json.dumps(results, sort_keys=True))
