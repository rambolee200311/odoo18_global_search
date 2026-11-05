"""Small server-side helpers shared by native Office tools and rendering."""

from __future__ import annotations

import re

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError

from .ai_orchestrator import _authorized_scalar_field_type, _scalar_field_path_status


_MAX_TEMPLATE_TEXT_ITEMS = 160
_MAX_TEMPLATE_TEXT_CHARS = 300
_MAX_TEMPLATE_TARGETS = 2_000
_MAX_FIELD_CANDIDATES = 500
_NESTED_FIELD_CANDIDATE_RESERVE = 125
_MAX_REPEAT_FIELDS = 160
_MAX_NESTED_FIELD_CHECKS = 20_000
_MAX_SELECTED_RECORDS = 100
_MAX_REQUESTED_COLLECTIONS = 40
_MAX_REQUESTED_COLLECTION_FIELDS = 64
SELECTED_RECORDS_COLLECTION = "selected_records"
_SCALAR_ODOO_FIELD_TYPES = frozenset(
    {"char", "text", "html", "selection", "integer", "float", "monetary", "boolean", "date", "datetime"}
)
_RELATED_FIELD_PRIORITY = (
    # Prefer a single ORM-computed full address over a display name. This is
    # still discovered dynamically and only included after every relation
    # segment passes the current user's ACL and field-access checks.
    "contact_address",
    "name",
    "display_name",
    "complete_name",
    "street",
    "street2",
    "city",
    "zip",
    "ref",
    "barcode",
    "default_code",
    "weight",
    "net_weight",
    "gross_weight",
    "volume",
)
_REPEAT_ROW_FIELD_PRIORITY = tuple(dict.fromkeys((
    # Keep common line-item identifiers and measures in the bounded schema.
    # These are priorities only: candidates still come from _field_candidates,
    # which checks the current user's read and field-access rights.
    "default_code",
    "barcode",
    "weight",
    "net_weight",
    "gross_weight",
    "product_uom_qty",
    "quantity",
    *_RELATED_FIELD_PRIORITY,
)))


def _field_candidates(env, target, _policy=None):
    """Discover scalar fields the current Odoo user can read on this record."""
    target.check_access("read")
    result = {}
    for field_name in sorted(target._fields):
        if len(result) >= _MAX_FIELD_CANDIDATES:
            break
        value_type = _authorized_scalar_field_type(target, field_name)
        if value_type:
            result[field_name] = value_type

    # Offer safe scalar fields one many2one hop away without letting the first
    # large relation (for example a user or company model) consume the entire
    # candidate budget. Each relation gets a fair turn; common display/address
    # fields are only prioritized, not whitelisted, and all other readable
    # scalar fields remain eligible while capacity remains.
    relation_candidates = []
    nested_candidates = []
    nested_routes = []
    for relation_name, relation_field in sorted(target._fields.items()):
        if getattr(relation_field, "type", None) != "many2one":
            continue
        related_model = env[relation_field.comodel_name]
        candidates = []
        for leaf_name in sorted(related_model._fields):
            field_name = f"{relation_name}.{leaf_name}"
            value_type = _authorized_scalar_field_type(target, field_name)
            if value_type:
                candidates.append((field_name, value_type, leaf_name))
        priority = {name: index for index, name in enumerate(_REPEAT_ROW_FIELD_PRIORITY)}
        candidates.sort(
            key=lambda item: (
                item[2] not in priority,
                priority.get(item[2], len(priority)),
                item[2],
            )
        )
        if candidates:
            relation_candidates.append(candidates)
        # Include a second many2one hop for common business paths such as
        # order.warehouse_id.partner_id.street. Every segment is rechecked by
        # _authorized_scalar_field_type against the current user's ORM rights.
        # Discover leaf names first, then check paths round-robin across all
        # relation routes. Iterating every leaf of the first large relation
        # used to consume the inspection budget before later paths such as
        # warehouse_id.partner_id.contact_address were reached.
        for nested_name, nested_field in sorted(related_model._fields.items()):
            if getattr(nested_field, "type", None) != "many2one":
                continue
            nested_model = env[nested_field.comodel_name]
            leaf_names = [
                leaf_name
                for leaf_name, leaf_field in nested_model._fields.items()
                if getattr(leaf_field, "type", None) in _SCALAR_ODOO_FIELD_TYPES
            ]
            leaf_priority = {name: index for index, name in enumerate(_RELATED_FIELD_PRIORITY)}
            leaf_names.sort(
                key=lambda name: (
                    name not in leaf_priority,
                    leaf_priority.get(name, len(leaf_priority)),
                    name,
                )
            )
            if leaf_names:
                nested_routes.append((relation_name, nested_name, leaf_names))

    nested_checks = 0
    max_leaf_count = max((len(route[2]) for route in nested_routes), default=0)
    for leaf_index in range(max_leaf_count):
        if nested_checks >= _MAX_NESTED_FIELD_CHECKS:
            break
        for relation_name, nested_name, leaf_names in nested_routes:
            if nested_checks >= _MAX_NESTED_FIELD_CHECKS:
                break
            if leaf_index >= len(leaf_names):
                continue
            leaf_name = leaf_names[leaf_index]
            nested_checks += 1
            field_name = f"{relation_name}.{nested_name}.{leaf_name}"
            value_type = _authorized_scalar_field_type(target, field_name)
            if value_type:
                nested_candidates.append((field_name, value_type, leaf_name))

    nested_priority = {name: index for index, name in enumerate(_RELATED_FIELD_PRIORITY)}
    nested_candidates.sort(
        key=lambda item: (
            item[2] not in nested_priority,
            nested_priority.get(item[2], len(nested_priority)),
            item[0],
        )
    )

    def add_relation_candidates(limit):
        """Add one-hop candidates fairly, leaving reserved room for nested paths."""
        nonlocal relation_candidates
        starting_count = len(result)
        while relation_candidates and len(result) < _MAX_FIELD_CANDIDATES:
            remaining = []
            for candidates in relation_candidates:
                if len(result) >= _MAX_FIELD_CANDIDATES or len(result) - starting_count >= limit:
                    remaining.append(candidates)
                    continue
                field_name, value_type, _leaf_name = candidates.pop(0)
                result.setdefault(field_name, value_type)
                if candidates:
                    remaining.append(candidates)
            relation_candidates = remaining
            if len(result) - starting_count >= limit:
                break

    nested_reserve = min(len(nested_candidates), _NESTED_FIELD_CANDIDATE_RESERVE)
    add_relation_candidates(max(0, _MAX_FIELD_CANDIDATES - len(result) - nested_reserve))

    nested_added = 0
    for field_name, value_type, _leaf_name in nested_candidates:
        if len(result) >= _MAX_FIELD_CANDIDATES or nested_added >= nested_reserve:
            break
        if field_name not in result:
            result[field_name] = value_type
            nested_added += 1

    # If duplicate root/one-hop paths used some of the reserved capacity,
    # backfill it with remaining one-hop candidates without exceeding the cap.
    add_relation_candidates(_MAX_FIELD_CANDIDATES - len(result))
    if not result:
        raise UserError(_("No readable, supported scalar fields are available for this record."))
    return result


def _selected_record_context(env, model_name, record_ids, requested_fields=None):
    """Reauthorize records and intersect discovered plus explicitly requested scalar paths.

    ``requested_fields`` is only a discovery hint (for example fields the
    native Retriever just read). Each path is independently checked against
    the current user's model, field, related-record and company permissions on
    every selected record before it is returned.
    """
    if (
        not isinstance(model_name, str)
        or model_name not in env.registry.models
        or not isinstance(record_ids, list)
        or not record_ids
        or len(record_ids) > _MAX_SELECTED_RECORDS
        or any(type(record_id) is not int or record_id < 1 for record_id in record_ids)
        or len(set(record_ids)) != len(record_ids)
    ):
        raise ValidationError(_("The selected record set is invalid or exceeds the supported batch size."))
    model = env[model_name]
    model.check_access("read")
    records_by_id = {record.id: record for record in model.browse(record_ids).exists()}
    if set(records_by_id) != set(record_ids):
        raise AccessError(_("One or more selected records are unavailable."))
    records = model.browse(record_ids)
    records.check_access("read")
    for record in records:
        record.check_access("read")

    candidate_maps = [_field_candidates(env, records_by_id[record_id]) for record_id in record_ids]
    common_names = set(candidate_maps[0])
    for fields in candidate_maps[1:]:
        common_names.intersection_update(fields)
    common = {
        name: candidate_maps[0][name]
        for name in sorted(common_names)
        if all(fields[name] == candidate_maps[0][name] for fields in candidate_maps)
    }
    if requested_fields is None:
        requested_fields = []
    if (
        not isinstance(requested_fields, list)
        or len(requested_fields) > 64
        or any(not isinstance(name, str) or not name.strip() or len(name) > 255 for name in requested_fields)
        or len(set(requested_fields)) != len(requested_fields)
    ):
        raise ValidationError(_("The explicitly requested field list is invalid."))
    records_by_id = {record.id: record for record in records}
    for name in requested_fields:
        kinds = [
            _authorized_scalar_field_type(records_by_id[record_id], name)
            for record_id in record_ids
        ]
        if kinds and kinds[0] and all(kind == kinds[0] for kind in kinds):
            common[name] = kinds[0]
    return records, common


def _field_metadata(env, model_name, fields):
    """Describe already-authorized field paths for model selection.

    This is presentation metadata only. Permission and type checks continue to
    use the compact ``field -> type`` map and are repeated before every read.
    """
    result = {}
    if model_name not in env.registry.models or not isinstance(fields, dict):
        return result
    for path, value_type in fields.items():
        if not isinstance(path, str) or not path:
            continue
        current_model = env[model_name]
        field = None
        segments = path.split(".")
        for index, segment in enumerate(segments):
            field = current_model._fields.get(segment)
            if not field:
                break
            if index < len(segments) - 1:
                if field.type != "many2one" or field.comodel_name not in env.registry.models:
                    field = None
                    break
                current_model = env[field.comodel_name]
        if not field:
            continue
        descriptor = {
            "type": value_type,
            "label": str(field.string or segments[-1])[:200],
        }
        help_text = field.help
        if isinstance(help_text, str) and help_text.strip():
            descriptor["help"] = help_text.strip()[:500]
        result[path] = descriptor
    return result


def _normalize_requested_collection_fields(requested_fields_by_collection):
    """Validate a bounded, collection-scoped field discovery hint."""
    if requested_fields_by_collection is None:
        return {}
    if (
        not isinstance(requested_fields_by_collection, dict)
        or len(requested_fields_by_collection) > _MAX_REQUESTED_COLLECTIONS
    ):
        raise ValidationError(_("The explicitly requested collection fields are invalid."))
    normalized = {}
    total_fields = 0
    for collection_field, field_paths in requested_fields_by_collection.items():
        if (
            not isinstance(collection_field, str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", collection_field)
            or not isinstance(field_paths, list)
            or len(field_paths) > _MAX_REQUESTED_COLLECTION_FIELDS
            or any(
                not isinstance(path, str) or not path.strip() or len(path) > 255
                for path in field_paths
            )
            or len(set(field_paths)) != len(field_paths)
        ):
            raise ValidationError(_("The explicitly requested collection fields are invalid."))
        total_fields += len(field_paths)
        if total_fields > _MAX_REQUESTED_COLLECTION_FIELDS:
            raise ValidationError(_("Too many explicitly requested collection fields."))
        normalized[collection_field] = list(field_paths)
    return normalized


def _repeat_row_collection_candidates(env, target, requested_fields_by_collection=None):
    """Expose readable one2many collections as repeat-row input candidates.

    Values are intentionally omitted here. The native Retriever must fetch
    values on demand, and it separately constrains the query to records linked
    to this exact Office Session target.
    """
    requested_fields_by_collection = _normalize_requested_collection_fields(
        requested_fields_by_collection
    )
    target.check_access("read")
    candidates = []
    for field_name, relation in sorted(target._fields.items()):
        if relation.type != "one2many":
            continue
        try:
            target.check_field_access_rights("read", [field_name])
            records = target[field_name]
            records.check_access("read")
            if not records:
                continue
            fields = _field_candidates(env, records)
        except (AccessError, UserError):
            continue
        requested_paths = requested_fields_by_collection.get(field_name, [])
        explicitly_authorized = {}
        unavailable_requested_fields = []
        unavailable_requested_field_reasons = {}
        for path in requested_paths:
            path_results = [_scalar_field_path_status(record, path) for record in records]
            row_types = {value_type for value_type, _reason in path_results}
            if len(row_types) == 1 and None not in row_types:
                explicitly_authorized[path] = row_types.pop()
            else:
                unavailable_requested_fields.append(path)
                reasons = sorted({reason for value_type, reason in path_results if not value_type and reason})
                unavailable_requested_field_reasons[path] = reasons or ["inconsistent_type_across_rows"]
        priority = {name: index for index, name in enumerate(_REPEAT_ROW_FIELD_PRIORITY)}

        def field_rank(name):
            leaf = name.rsplit(".", 1)[-1]
            if leaf in priority:
                semantic_rank = priority[leaf]
            elif re.search(r"(?:qty|quantity)", leaf, re.IGNORECASE):
                semantic_rank = len(priority)
            else:
                semantic_rank = len(priority) + 1
            return semantic_rank, name.count(".") + 1, name

        # Explicitly requested, authorized paths are reserved before filling
        # the bounded discovery schema. Fill the remaining capacity by semantic
        # rank while alternating direct and related candidates, so a large
        # group cannot crowd out the other. Avoid slicing a ranked list: the
        # selected set and the reason an item is retained remain explicit.
        allowed_fields = dict(explicitly_authorized)
        direct_fields = sorted(
            (name for name in fields if "." not in name and name not in allowed_fields),
            key=field_rank,
        )
        related_fields = sorted(
            (name for name in fields if "." in name and name not in allowed_fields),
            key=field_rank,
        )
        buckets = {"direct": direct_fields, "related": related_fields}
        positions = {"direct": 0, "related": 0}
        selected_counts = {
            "direct": sum("." not in name for name in allowed_fields),
            "related": sum("." in name for name in allowed_fields),
        }
        while len(allowed_fields) < _MAX_REPEAT_FIELDS:
            available = [
                group
                for group in ("direct", "related")
                if positions[group] < len(buckets[group])
            ]
            if not available:
                break
            # Prefer the group currently represented by fewer fields. Direct
            # wins ties for deterministic output; field_rank orders each group.
            group = min(available, key=lambda item: (selected_counts[item], item != "direct"))
            candidate_name = buckets[group][positions[group]]
            positions[group] += 1
            allowed_fields[candidate_name] = fields[candidate_name]
            selected_counts[group] += 1
        candidates.append(
            {
                "collection_field": field_name,
                "relation_model": relation.comodel_name,
                "inverse_field": relation.inverse_name,
                "row_count": len(records),
                "allowed_fields": allowed_fields,
                "unavailable_requested_fields": unavailable_requested_fields,
                "unavailable_requested_field_reasons": unavailable_requested_field_reasons,
            }
        )
        if len(candidates) >= 40:
            break
    return candidates


def _cell_coordinates(element_id):
    if not isinstance(element_id, str) or not element_id.startswith("xlsx:") or "!" not in element_id:
        return None
    sheet, coordinate = element_id[5:].rsplit("!", 1)
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", coordinate)
    if not match:
        return None
    column = 0
    for char in match.group(1):
        column = column * 26 + ord(char) - ord("A") + 1
    return sheet, column, int(match.group(2)), coordinate


def _template_context(inspection):
    """Build bounded writable targets and visible labels for supported Office files."""
    inspection_format = getattr(inspection, "format", "xlsx")
    if inspection_format == "docx":
        # The current M1 Word adapter can replace a simple, single-run text
        # paragraph. It cannot add paragraphs or rows, or preserve a rich-text
        # run structure while replacing just part of a paragraph. Keep those
        # unsupported paragraphs visible as context, but never authorize them
        # as write targets.
        paragraphs = [item for item in inspection.elements if item.kind == "paragraph"]
        targets = [
            {
                "element_id": item.element_id,
                "required": False,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": True,
            }
            for item in paragraphs
            if item.writable
        ]
        visible_text = [
            {"element_id": item.element_id, "text": item.value[:_MAX_TEMPLATE_TEXT_CHARS]}
            for item in paragraphs[:_MAX_TEMPLATE_TEXT_ITEMS]
            if isinstance(item.value, str) and item.value.strip()
        ]
        if not targets or len(targets) > _MAX_TEMPLATE_TARGETS:
            raise UserError(_("The Word template has no supported writable paragraphs or exceeds the mapping limit."))
        return targets, visible_text

    if inspection_format != "xlsx":
        raise UserError(_("This Office format has no supported mapping targets."))
    items = [item for item in inspection.elements if item.kind in {"cell", "formula"}]
    values = {}
    coordinates = {}
    merged_ranges = {}
    for item in items:
        location = _cell_coordinates(item.element_id)
        if not location:
            continue
        coordinates[item.element_id] = location
        if isinstance(getattr(item, "merged_range", None), str):
            merged_ranges[item.element_id] = item.merged_range
        if item.kind == "formula" and isinstance(item.value, dict):
            formula = item.value.get("formula")
            if isinstance(formula, str) and formula.strip():
                values[item.element_id] = formula.strip()[:_MAX_TEMPLATE_TEXT_CHARS]
        elif isinstance(item.value, str) and item.value.strip():
            values[item.element_id] = item.value.strip()[:_MAX_TEMPLATE_TEXT_CHARS]

    targets = []
    for item in items:
        location = coordinates.get(item.element_id)
        # Existing cells and formulas are user-selectable targets. Nothing is
        # changed unless the Proposal explicitly writes or clears that cell.
        if not location or item.kind not in {"cell", "formula"}:
            continue
        sheet, column, row, _coordinate = location
        visual_labels = []
        merged = merged_ranges.get(item.element_id)
        merged_bounds = None
        if merged:
            parts = merged.split(":", 1)
            if len(parts) == 2:
                first = _cell_coordinates(f"xlsx:{sheet}!{parts[0]}")
                last = _cell_coordinates(f"xlsx:{sheet}!{parts[1]}")
                if first and last:
                    merged_bounds = (
                        min(first[1], last[1]), min(first[2], last[2]),
                        max(first[1], last[1]), max(first[2], last[2]),
                    )
        for element_id, text in values.items():
            other = coordinates.get(element_id)
            if not other or other[0] != sheet:
                continue
            _other_sheet, other_column, other_row, _other_coordinate = other
            # Keep the visual label relation explicit when a label is just
            # above a merged destination, even if it is not in the anchor
            # column. The actual writable target remains the merged anchor.
            if other_row == row and 0 < column - other_column <= 3:
                visual_labels.append((0, column - other_column, element_id, text, "same_row_left"))
            elif other_column == column and 0 < row - other_row <= 3:
                visual_labels.append((1, row - other_row, element_id, text, "same_column_above"))
            elif merged_bounds and other_row == merged_bounds[1] - 1 and merged_bounds[0] <= other_column <= merged_bounds[2]:
                visual_labels.append((2, abs(other_column - merged_bounds[0]), element_id, text, "above_merged_region"))
        visual_labels.sort(key=lambda value: (value[0], value[1]))
        target = {
            "element_id": item.element_id,
            # Template labels describe a destination but do not make it a
            # mandatory business field. The Proposal explicitly decides what
            # to write or clear; omitted cells remain untouched.
            "required": False,
            "writable": getattr(item, "table_role", None) != "table_header",
            "allowed_value_types": ["string", "number", "boolean", "date", "datetime", "formula"],
            "approved_to_skip": True,
        }
        table_role = getattr(item, "table_role", None)
        table_header = getattr(item, "table_header", None)
        if table_role in {"table_header", "table_data"}:
            target["table_role"] = table_role
        if isinstance(table_header, str) and table_header:
            target["table_header"] = table_header[:_MAX_TEMPLATE_TEXT_CHARS]
        if merged:
            target["merge_range"] = merged
            target["write_target"] = item.element_id
        if visual_labels:
            target["visual_labels"] = [
                {"element_id": element_id, "text": text, "relation": relation}
                for _rank, _distance, element_id, text, relation in visual_labels[:3]
            ]
        targets.append(target)
    if not targets or len(targets) > _MAX_TEMPLATE_TARGETS:
        raise UserError(_("The template has no supported writable targets or exceeds the mapping limit."))

    visible_text = [
        {"element_id": element_id, "text": text}
        for element_id, text in list(values.items())[:_MAX_TEMPLATE_TEXT_ITEMS]
    ]
    return targets, visible_text
