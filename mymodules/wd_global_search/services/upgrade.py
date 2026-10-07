"""Upgrade preflight and post-migration checks for Global Search."""

import hashlib
import json

from odoo.exceptions import ValidationError


def _snapshot_checksum(snapshot_json):
    return hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()


def validate_published_versions(env):
    """Validate every Published snapshot without changing business data."""
    versions = env["wd.gs.config.version"].search([("state", "=", "published")])
    failures = []
    for version in versions:
        if not version.snapshot_json or not version.checksum:
            failures.append(f"{version.id}:missing_snapshot")
            continue
        try:
            snapshot = json.loads(version.snapshot_json)
        except (TypeError, ValueError):
            failures.append(f"{version.id}:invalid_json")
            continue
        if not isinstance(snapshot, dict) or snapshot.get("version") != version.version:
            failures.append(f"{version.id}:version_mismatch")
            continue
        if _snapshot_checksum(version.snapshot_json) != version.checksum:
            failures.append(f"{version.id}:checksum_mismatch")
    if failures:
        raise ValidationError("Published configuration validation failed: %s" % ", ".join(failures))
    return {"published_count": len(versions)}


def run_post_migration(env):
    """Run the non-destructive migration gate and record an audit event."""
    result = validate_published_versions(env)
    env["wd.gs.audit.event"].create(
        {
            "action": "upgrade",
            "message": "Published configuration preflight passed.",
        }
    )
    return result
