import json

from .errors import error


class ConfigurationError(Exception):
    def __init__(self, code="CONFIGURATION_ERROR"):
        super().__init__(code)
        self.code = code


def published_snapshot(env, domain_key):
    # Published configuration is control-plane metadata. It is not business
    # data and ordinary users must not receive direct model ACLs for it.
    config_env = env["wd.gs.config.domain"].sudo()
    domain = config_env.search(
        [("key", "=", domain_key), ("active", "=", True)], limit=1
    )
    version = config_env.env["wd.gs.config.version"].search(
        [("domain_id", "=", domain.id), ("state", "=", "published")],
        order="version desc, id desc",
        limit=1,
    )
    if not version or not version.snapshot_json or not version.checksum:
        raise ConfigurationError()
    try:
        snapshot = json.loads(version.snapshot_json)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ConfigurationError() from exc
    if not isinstance(snapshot, dict) or snapshot.get("version") != version.version:
        raise ConfigurationError()
    return {
        "domain_key": domain.key,
        "version_id": version.id,
        "checksum": version.checksum,
        "snapshot": snapshot,
    }
