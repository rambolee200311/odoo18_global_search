"""Shared, reauthorized Odoo data helpers for native Office tools and rendering."""

from __future__ import annotations

import re
import json

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError

from .mapping_service import _load_mapping_data

_VALUE_TYPES = {
    "char": "string", "text": "string", "html": "string", "selection": "string",
    "integer": "number", "float": "number", "monetary": "number", "boolean": "boolean",
    # Odoo serializes date and datetime values as ISO-like text through the
    # native Retriever; they remain scalar values that Office can write.
    "date": "string", "datetime": "string",
}

def _authorized_scalar_field_type(target, field_name):
    """Return the type of an ACL-readable scalar field via at most two M2O hops."""
    if (
        not isinstance(field_name, str)
        or not field_name
        or field_name.count(".") > 2
    ):
        return None
    try:
        segments = field_name.split(".")
        if any(not segment or segment in {"id", "__last_update", "create_uid", "write_uid"} for segment in segments):
            return None
        current = target
        for index, segment in enumerate(segments):
            model = current.env[current._name]
            model.check_access("read")
            model.check_field_access_rights("read", [segment])
            field = model._fields.get(segment)
            if not field:
                return None
            if index == len(segments) - 1:
                return _VALUE_TYPES.get(field.type)
            if field.type != "many2one":
                return None
            related_model = current.env[field.comodel_name]
            related_model.check_access("read")
            current = current[segment]
            if current:
                current.check_access("read")
            else:
                current = related_model
        return None
    except (AccessError, UserError):
        # Field discovery examines many relations, some of which expose
        # permanently restricted fields (for example res.users.totp_secret),
        # or whose model-specific access check is not configured. Skip that
        # candidate; an unverifiable field must never abort the whole mapping
        # request or be sent to the local Provider.
        return None


def _approved_field_types(env, session, allowed_fields):
    """Recheck configured fields using the active Odoo user's ORM permissions."""
    _rules, _manifest, configured_fields, _groups = _load_mapping_data(session)

    target_model = env[session.target_model]
    target_model.check_access("read")
    target = target_model.browse(session.target_record_id).exists()
    if not target:
        raise AccessError(_("The target record is unavailable."))
    target.check_access("read")
    permitted = {}
    for field_name in sorted(configured_fields):
        if not isinstance(field_name, str):
            continue
        value_type = _authorized_scalar_field_type(target, field_name)
        if value_type and configured_fields[field_name] == value_type:
            permitted[field_name] = value_type
    if not permitted:
        raise UserError(_("No readable mapping fields are available for this record."))
    return target, permitted


def _retrieve_record(env, session, fields):
    """Use Retriever for the record and resolve only reauthorized M2O paths."""
    tool = env["llm.tool"].search(
        [("implementation", "=", "odoo_record_retriever"), ("active", "=", True)],
        limit=1,
    )
    if not tool:
        raise UserError(_("The authorized Odoo record retrieval service is unavailable."))
    tool.check_access("read")
    requested = list(fields)
    direct_fields = [name for name in requested if "." not in name]
    relation_fields = {name.split(".", 1)[0] for name in requested if "." in name}
    retriever_fields = sorted(set(direct_fields) | relation_fields)
    try:
        result = tool.execute(
            {
                "model": session.target_model,
                "domain": [["id", "=", session.target_record_id]],
                "fields": retriever_fields,
                "limit": 1,
            }
        )
    except (AccessError, UserError, ValidationError):
        raise
    except Exception as exc:
        # Do not leak Retriever internals, and never continue to the Provider
        # when the authorized data source timed out or failed.
        raise UserError(_("The target record could not be retrieved.")) from exc
    if (
        not isinstance(result, list)
        or len(result) != 1
        or not isinstance(result[0], dict)
        or result[0].get("id") != session.target_record_id
    ):
        raise UserError(_("The target record could not be retrieved unambiguously."))
    values = dict(result[0])
    target = env[session.target_model].browse(session.target_record_id).exists()
    if not target:
        raise AccessError(_("The target record is unavailable."))
    target.check_access("read")
    for field_name in requested:
        if "." not in field_name:
            continue
        value_type = _authorized_scalar_field_type(target, field_name)
        if not value_type:
            raise AccessError(_("A mapped field is no longer available."))
        values[field_name] = _resolve_related_scalar(target, field_name, value_type)
    return values


def _resolve_related_scalar(record, field_name, value_type):
    """Read a server-authorized many2one path without sudo or caller IDs."""
    current = record
    segments = field_name.split(".")
    for index, segment in enumerate(segments):
        model = current.env[current._name]
        model.check_access("read")
        model.check_field_access_rights("read", [segment])
        field = model._fields.get(segment)
        if not field:
            raise AccessError(_("A mapped field is no longer available."))
        if index == len(segments) - 1:
            if field.type not in _VALUE_TYPES:
                raise AccessError(_("A mapped field is no longer available."))
            if current:
                current.check_access("read")
                current.check_field_access_rights("read", [segment])
                return current[segment]
            return False if value_type == "string" else None
        if field.type != "many2one":
            raise AccessError(_("A mapped relation is no longer available."))
        related_model = current.env[field.comodel_name]
        related_model.check_access("read")
        current = current[segment]
        if current:
            current.check_access("read")
        else:
            current = related_model
    raise AccessError(_("A mapped field is no longer available."))


def _approved_collection_field_types(env, session, group):
    """Reauthorize a configured one2many/many2many and its scalar fields."""
    relation_model = group.get("relation_model")
    if relation_model not in env.registry.models:
        raise AccessError(_("The mapping session is unavailable."))
    target_model = env[session.target_model]
    target_model.check_access("read")
    if group.get("collection_field") == "selected_records":
        try:
            context = json.loads(session.context_json or "{}")
            selected_ids = context.get("selected_record_ids") or [session.target_record_id]
        except (TypeError, json.JSONDecodeError) as exc:
            raise AccessError(_("The mapping session is unavailable.")) from exc
        if (
            relation_model != session.target_model
            or group.get("record_ids") != selected_ids
            or group.get("row_count") != len(selected_ids)
        ):
            raise AccessError(_("The selected-record mapping no longer matches its Session."))
        records_by_id = {
            record.id: record for record in target_model.browse(selected_ids).exists()
        }
        if set(records_by_id) != set(selected_ids):
            raise AccessError(_("One or more selected records are unavailable."))
        records = target_model.browse(selected_ids)
        records.check_access("read")
        configured = group.get("allowed_fields", {})
        permitted = {}
        for name in sorted(configured):
            kinds = [_authorized_scalar_field_type(records_by_id[item], name) for item in selected_ids]
            if kinds and kinds[0] and all(kind == kinds[0] for kind in kinds) and configured[name] == kinds[0]:
                permitted[name] = kinds[0]
        if not permitted:
            raise UserError(_("No readable fields are available in the selected records."))
        direct_names = [name for name in permitted if "." not in name]
        if direct_names:
            records.check_field_access_rights("read", direct_names)
        return permitted

    target = target_model.browse(session.target_record_id).exists()
    if not target:
        raise AccessError(_("The target record is unavailable."))
    target.check_access("read")
    relation = target_model._fields.get(group.get("collection_field"))
    if (
        not relation
        or relation.type not in {"one2many", "many2many"}
        or relation.comodel_name != relation_model
    ):
        raise AccessError(_("The mapping session is unavailable."))
    target.check_field_access_rights("read", [relation.name])
    records = target[group["collection_field"]]
    records.check_access("read")
    if len(records) != group.get("row_count"):
        raise UserError(_("The authorized collection size no longer matches the mapping rows."))
    configured = group.get("allowed_fields", {})
    permitted = {}
    for name in sorted(configured):
        kind = _authorized_scalar_field_type(records, name)
        if kind and configured[name] == kind and name not in {"id", "create_uid", "write_uid"}:
            permitted[name] = kind
    if not permitted:
        raise UserError(_("No readable fields are available in this collection."))
    direct_names = [name for name in permitted if "." not in name]
    if direct_names:
        records.check_field_access_rights("read", direct_names)
    return permitted


def _retrieve_collection(env, session, group, fields):
    """Retrieve exactly the relation recordset, preserving its authorized order."""
    selected_records = group.get("collection_field") == "selected_records"
    if selected_records:
        try:
            context = json.loads(session.context_json or "{}")
            ids = context.get("selected_record_ids") or [session.target_record_id]
        except (TypeError, json.JSONDecodeError) as exc:
            raise AccessError(_("The mapping session is unavailable.")) from exc
        if group.get("record_ids") != ids or group.get("relation_model") != session.target_model:
            raise AccessError(_("The selected-record mapping no longer matches its Session."))
        collection_model = session.target_model
        collection_records = env[collection_model].browse(ids).exists()
        if set(collection_records.ids) != set(ids):
            raise AccessError(_("One or more selected records are unavailable."))
        collection_records.check_access("read")
        for record in collection_records:
            record.check_access("read")
        domain = [["id", "in", ids]]
    else:
        target = env[session.target_model].browse(session.target_record_id).exists()
        if not target:
            raise AccessError(_("The target record is unavailable."))
        target.check_access("read")
        relation = env[session.target_model]._fields.get(group["collection_field"])
        if not relation or relation.type not in {"one2many", "many2many"}:
            raise AccessError(_("The mapping session is unavailable."))
        target.check_field_access_rights("read", [group["collection_field"]])
        relation_records = target[group["collection_field"]]
        relation_records.check_access("read")
        ids = relation_records.ids
        collection_model = group["relation_model"]
        domain = [[relation.inverse_name, "=", session.target_record_id]] if relation.type == "one2many" else [["id", "in", ids]]
    if len(ids) != group["row_count"]:
        raise UserError(_("The authorized collection size no longer matches the mapping rows."))
    if not ids:
        return []
    tool = env["llm.tool"].search(
        [("implementation", "=", "odoo_record_retriever"), ("active", "=", True)], limit=1
    )
    if not tool:
        raise UserError(_("The authorized Odoo record retrieval service is unavailable."))
    tool.check_access("read")
    requested = list(fields)
    tool_field_set = {name.split(".", 1)[0] for name in requested}
    if selected_records:
        tool_field_set.add("id")
    tool_fields = sorted(tool_field_set)
    try:
        result = tool.execute(
            {
                "model": collection_model,
                "domain": domain,
                "fields": tool_fields,
                "limit": len(ids),
            }
        )
    except (AccessError, UserError, ValidationError):
        raise
    except Exception as exc:
        raise UserError(_("The authorized collection could not be retrieved.")) from exc
    if (
        not isinstance(result, list)
        or any(not isinstance(item, dict) or type(item.get("id")) is not int for item in result)
        or {item["id"] for item in result} != set(ids)
    ):
        raise UserError(_("The authorized collection response is incomplete or inconsistent."))
    rows_by_id = {item["id"]: item for item in result}
    rows = []
    for record_id in ids:
        row = dict(rows_by_id[record_id])
        line = env[collection_model].browse(record_id).exists()
        if not line:
            raise AccessError(_("An authorized collection row is no longer available."))
        line.check_access("read")
        for field_name in requested:
            if "." not in field_name:
                continue
            value_type = _authorized_scalar_field_type(line, field_name)
            if not value_type:
                raise AccessError(_("A mapped collection field is no longer available."))
            row[field_name] = _resolve_related_scalar(line, field_name, value_type)
        rows.append(row)
    sort_by = group.get("sort_by")
    if sort_by is not None:
        direction = group.get("sort_direction")
        if sort_by not in fields or direction not in {"asc", "desc"}:
            raise AccessError(_("The repeat-row ordering is no longer authorized."))

        def sort_key(row):
            value = row.get(sort_by)
            if value is None or value is False or value == "":
                return None
            if isinstance(value, str):
                return (0, value.casefold())
            if isinstance(value, bool):
                return (2, int(value))
            if isinstance(value, (int, float)):
                return (1, float(value))
            raise ValidationError(_("The repeat-row ordering field is not a sortable scalar."))

        populated = []
        empty = []
        for row in rows:
            key = sort_key(row)
            (empty if key is None else populated).append((key, row))
        populated.sort(key=lambda item: item[0], reverse=direction == "desc")
        # Python's sort is stable, so duplicate values preserve the related
        # record order. Empty values remain last in both directions.
        rows = [row for _key, row in populated] + [row for _key, row in empty]
    return rows


def _mapping_field_types(root_fields, groups, group_fields):
    result = dict(root_fields)
    for group in groups:
        for name, value_type in group_fields.get(group["group_id"], {}).items():
            result[f"{group['group_id']}::{name}"] = value_type
    return result


def _target_label_context(manifest, template_elements):
    """Associate writable cells with nearby template labels for semantic mapping."""
    cells = {}
    for item in template_elements:
        element_id = item.get("element_id", "")
        match = re.fullmatch(r"xlsx:([^!]+)!([A-Z]+)([1-9][0-9]*)", element_id)
        text = item.get("text")
        if match and isinstance(text, str) and text.strip():
            sheet, column_text, row_text = match.groups()
            column = 0
            for char in column_text:
                column = column * 26 + ord(char) - ord("A") + 1
            cells[element_id] = (sheet, column, int(row_text), text.strip()[:160])

    result = []
    for target in manifest:
        match = re.fullmatch(r"xlsx:([^!]+)!([A-Z]+)([1-9][0-9]*)", target["element_id"])
        if not match:
            continue
        sheet, column_text, row_text = match.groups()
        column = 0
        for char in column_text:
            column = column * 26 + ord(char) - ord("A") + 1
        row = int(row_text)
        nearby = []
        for label in target.get("visual_labels", []):
            if (
                isinstance(label, dict)
                and isinstance(label.get("element_id"), str)
                and isinstance(label.get("text"), str)
                and isinstance(label.get("relation"), str)
            ):
                nearby.append((0, 0, label["element_id"], label["text"], label["relation"]))
        for element_id, (label_sheet, label_column, label_row, text) in cells.items():
            if label_sheet != sheet:
                continue
            if label_row == row and 0 < column - label_column <= 3:
                nearby.append((column - label_column, 0, element_id, text, "same_row_left"))
            elif label_column == column and 0 < row - label_row <= 3:
                nearby.append((row - label_row, 1, element_id, text, "same_column_above"))
        nearby.sort(key=lambda item: (item[0], item[1]))
        if nearby or target.get("merge_range"):
            entry = {
                "element_id": target["element_id"],
                "write_target": target.get("write_target", target["element_id"]),
                "nearby_labels": [
                    {"element_id": element_id, "text": text, "relation": relation}
                    for _distance, _orientation, element_id, text, relation in nearby[:3]
                ],
            }
            if target.get("merge_range"):
                entry["merge_range"] = target["merge_range"]
            result.append(entry)
    return result
