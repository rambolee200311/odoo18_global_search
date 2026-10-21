"""Fresh-shell postcheck and ORM cleanup for CC-OFFICE-M1-003."""
import json
import os
import uuid

from odoo import api, SUPERUSER_ID

TOKEN = os.environ.get("OFFICE_SPIKE_TOKEN")
USER_A_ID = 97
CONTROL_NAME = f"TEST_SPIKE_MARK_{TOKEN}_CTRL.bin"
ROLLBACK_NAME = f"TEST_SPIKE_MARK_{TOKEN}_ROLLBACK.bin"
ROLLBACK_FNAME = "34/34de6936a35011a07ecc06bc0521f9961ccb51f7"
if not TOKEN or not TOKEN.isalnum():
    raise RuntimeError("OFFICE_SPIKE_TOKEN must be alphanumeric")

bootstrap = env
assert bootstrap.uid == SUPERUSER_ID and bootstrap.su

def checked_path(root, relative):
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, relative))
    if os.path.commonpath([root, path]) != root:
        raise RuntimeError("Derived path escaped filestore root")
    return path

cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    if user_a.su or user_a.uid == SUPERUSER_ID:
        raise RuntimeError("User A context must be non-system and su=False")
    AttachmentA = user_a["ir.attachment"]
    controls = AttachmentA.search([("name", "=", CONTROL_NAME)])
    rollback_records = AttachmentA.search([("name", "=", ROLLBACK_NAME)])
    rollback_refs = AttachmentA.search([("store_fname", "=", ROLLBACK_FNAME)])
    if len(controls) != 1 or rollback_records or rollback_refs:
        raise AssertionError("Fresh-shell ORM state differs from expected commit/rollback results")
    control = controls
    control_fname = control.store_fname
    root = AttachmentA._filestore()
    rollback_object = os.path.exists(checked_path(root, ROLLBACK_FNAME))
    rollback_gc = os.path.exists(checked_path(root, "checklist/" + ROLLBACK_FNAME))
    control_object_before = os.path.exists(checked_path(root, control_fname))
    control_gc_before = os.path.exists(checked_path(root, "checklist/" + control_fname))
    if not rollback_object or not rollback_gc:
        raise AssertionError("Expected rolled-back object and Odoo GC marker were not both observable")
    before = {
        "fresh_shell_id": str(uuid.uuid4()),
        "user_a_su": user_a.su,
        "control_records_before_cleanup": len(controls),
        "rollback_name_records": len(rollback_records),
        "rollback_store_fname_references": len(rollback_refs),
        "rollback_filestore_object_exists": rollback_object,
        "rollback_gc_entry_exists": rollback_gc,
        "control_filestore_object_exists_before_cleanup": control_object_before,
        "control_gc_entry_exists_before_cleanup": control_gc_before,
        "status": "PASS",
    }
    print("OFFICE_SPIKE_FRESH_SHELL_POSTCHECK=" + json.dumps(before, sort_keys=True))
finally:
    cr.rollback()
    cr.close()
