import json
from pathlib import Path


DOMAIN_KEY = "global_search_baseline"
RESULT_PATH = (
    Path.cwd()
    / "mymodules/wd_tv_global_search/tv_07_final_acceptance_dataset/results/configuration_result.json"
)


def _published(domain):
    return domain.version_ids.filtered(lambda version: version.state == "published").sorted(
        key=lambda version: (version.version, version.id), reverse=True
    )[:1]


def _next_version(domain):
    versions = domain.version_ids
    return max(versions.mapped("version") or [0]) + 1


def configure(env):
    domain = env["wd.gs.config.domain"].search(
        [("key", "=", DOMAIN_KEY), ("active", "=", True)], limit=1
    )
    if not domain:
        raise RuntimeError(f"Missing configuration domain: {DOMAIN_KEY}")
    existing = domain.version_ids.filtered(
        lambda version: version.version >= 2 and version.state == "draft"
    ).sorted(key=lambda version: (version.version, version.id), reverse=True)[:1]
    source = _published(domain)
    version = existing or env["wd.gs.config.version"].create(
        {
            "domain_id": domain.id,
            "version": _next_version(domain),
            "schema_version": source.schema_version,
            "state": "draft",
        }
    )
    if not version.resource_ids:
        for source_resource in source.resource_ids:
            resource = source_resource.copy({"version_id": version.id})
            for source_mapping in source_resource.model_mapping_ids:
                mapping = source_mapping.copy({"resource_id": resource.id})
                for source_field in source_mapping.searchable_field_ids:
                    source_field.copy({"mapping_id": mapping.id})
            for source_path in source_resource.relation_path_ids:
                source_path.copy({"resource_id": resource.id})
            for source_date in source_resource.business_date_ids:
                source_date.copy({"resource_id": resource.id})
            for source_state in source_resource.state_mapping_ids:
                source_state.copy({"resource_id": resource.id})
            for source_snapshot in source_resource.snapshot_field_ids:
                source_snapshot.copy({"resource_id": resource.id})
        for source_entry in source.vocabulary_ids:
            source_entry.copy({"version_id": version.id})
        for source_entry in source.scoring_ids:
            source_entry.copy({"version_id": version.id})
        for source_entry in source.performance_ids:
            source_entry.copy({"version_id": version.id})
        version.invalidate_recordset()

    resources = {resource.key: resource for resource in version.resource_ids}
    paths = {
        "purchase_order": ("partner_id", "order_line.product_id"),
        "sale_order": ("partner_id", "order_line.product_id"),
        "stock_picking": ("partner_id", "purchase_id", "sale_id"),
    }
    snapshot_fields = {
        "purchase_order": (("partner_id", "Vendor", "text"),),
        "sale_order": (("partner_id", "Customer", "text"),),
        "stock_picking": (("origin", "Source Document", "text"),),
    }
    for key, path_values in paths.items():
        resource = resources.get(key)
        if not resource:
            continue
        existing_paths = set(resource.relation_path_ids.mapped("path"))
        for path in path_values:
            if path not in existing_paths:
                env["wd.gs.relation.path"].create(
                    {"resource_id": resource.id, "path": path, "max_depth": len(path.split("."))}
                )
    for key, fields in snapshot_fields.items():
        resource = resources.get(key)
        if not resource:
            continue
        existing_fields = set(resource.snapshot_field_ids.mapped("field_name"))
        for field_name, label, format_type in fields:
            if field_name not in existing_fields:
                env["wd.gs.snapshot.field"].create(
                    {
                        "resource_id": resource.id,
                        "field_name": field_name,
                        "label": label,
                        "format_type": format_type,
                        "allow_empty": True,
                    }
                )

    version.action_validate()
    if version.state != "rejected":
        version.action_publish()
    result = {
        "domain": domain.key,
        "version": version.version,
        "state": version.state,
        "checksum": version.checksum,
        "relation_paths": {
            key: list(paths_for_resource)
            for key, paths_for_resource in paths.items()
            if key in resources
        },
        "note": "Relation paths are validated and used for authorized related-identifier search.",
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


result = configure(env)
env.cr.commit()
print(json.dumps(result, ensure_ascii=False, indent=2))
