"""ORM-only cleanup of the single committed CC-003 control attachment."""
import json
import os
import uuid

from odoo import api, SUPERUSER_ID

TOKEN = os.environ.get("OFFICE_SPIKE_TOKEN")
USER_A_ID = 97
CONTROL_NAME = f"TEST_SPIKE_MARK_{TOKEN}_CTRL.bin"
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
        raise RuntimeError("Cleanup must use non-system user A with su=False")
    controls = user_a["ir.attachment"].search([("name", "=", CONTROL_NAME)])
    if len(controls) != 1 or controls.create_uid.id != USER_A_ID:
        raise RuntimeError("Expected exactly one owned synthetic control attachment")
    fname = controls.store_fname
    root = user_a["ir.attachment"]._filestore()
    controls.unlink()
    cr.commit()
finally:
    cr.close()

# Verify with a new transaction and repeat only the exact-name ORM cleanup.
cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    AttachmentA = user_a["ir.attachment"]
    remaining = AttachmentA.search([("name", "=", CONTROL_NAME)])
    if remaining:
        raise AssertionError("Control attachment remains after ORM unlink")
    repeated = AttachmentA.search([("name", "=", CONTROL_NAME)])
    repeated.unlink()
    cr.commit()
finally:
    cr.close()

# Final read-only observation: ORM record must remain absent; the only checked
# object is the control's original store_fname under the configured filestore.
cr = bootstrap.registry.cursor()
try:
    user_a = api.Environment(cr, USER_A_ID, {}, su=False)
    AttachmentA = user_a["ir.attachment"]
    count = AttachmentA.search_count([("name", "=", CONTROL_NAME)])
    if count:
        raise AssertionError("Exact synthetic control marker reappeared")
    root = AttachmentA._filestore()
    result = {
        "cleanup_id": str(uuid.uuid4()),
        "user_a_su": user_a.su,
        "exact_name_record_count_after_cleanup": count,
        "repeated_orm_cleanup": "PASS_NOOP",
        "control_filestore_object_exists_after_unlink": os.path.exists(checked_path(root, fname)),
        "control_gc_entry_exists_after_unlink": os.path.exists(checked_path(root, "checklist/" + fname)),
        "direct_filestore_delete": False,
        "global_gc_executed": False,
        "status": "PASS",
    }
    print("OFFICE_SPIKE_ORM_CLEANUP=" + json.dumps(result, sort_keys=True))
finally:
    cr.rollback()
    cr.close()
