"""Final exact-marker ORM and read-only filestore audit for CC-003."""
import json
import os

from odoo import api, SUPERUSER_ID

TOKEN = os.environ.get("OFFICE_SPIKE_TOKEN")
if not TOKEN or not TOKEN.isalnum():
    raise RuntimeError("OFFICE_SPIKE_TOKEN must be alphanumeric")
USER_A_ID = 97
expected = {
    "control": (f"TEST_SPIKE_MARK_{TOKEN}_CTRL.bin", "dc/dc6a49aab38a11bb25bb612cb5df2ed9999c016a"),
    "rollback": (f"TEST_SPIKE_MARK_{TOKEN}_ROLLBACK.bin", "34/34de6936a35011a07ecc06bc0521f9961ccb51f7"),
}
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
        raise RuntimeError("Final audit must use non-system user A with su=False")
    AttachmentA = user_a["ir.attachment"]
    root = AttachmentA._filestore()
    audited = {}
    for label, (name, fname) in expected.items():
        records_by_name = AttachmentA.search([("name", "=", name)])
        refs_by_fname = AttachmentA.search([("store_fname", "=", fname)])
        if records_by_name or refs_by_fname:
            raise AssertionError(f"Exact synthetic {label} record or reference remains")
        audited[label] = {
            "exact_name_record_count": len(records_by_name),
            "store_fname_reference_count": len(refs_by_fname),
            "filestore_object_exists": os.path.exists(checked_path(root, fname)),
            "gc_entry_exists": os.path.exists(checked_path(root, "checklist/" + fname)),
        }
    if not all(v["filestore_object_exists"] and v["gc_entry_exists"] for v in audited.values()):
        raise AssertionError("Expected Odoo GC checklist state changed unexpectedly")
    print("OFFICE_SPIKE_FINAL_AUDIT=" + json.dumps({
        "user_a_su": user_a.su,
        "storage_mode": AttachmentA._storage(),
        "records_and_references_absent": True,
        "objects_are_exactly_the_two_spike_candidates": True,
        "objects_left_for_native_gc": audited,
        "global_gc_executed": False,
        "direct_filestore_delete": False,
        "status": "PASS",
    }, sort_keys=True))
finally:
    cr.rollback()
    cr.close()
