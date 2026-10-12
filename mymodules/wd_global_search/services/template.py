import re
from dataclasses import dataclass

from odoo import _
from odoo.exceptions import AccessError
from odoo.tools.misc import format_date, format_datetime, formatLang


MAX_TEMPLATE_BYTES = 8 * 1024
MAX_VARIABLES = 50
MAX_LOOP_BLOCKS = 5
MAX_LOOP_DEPTH = 2
MAX_LOOP_BODY_CODEPOINTS = 1000
_FIELD_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_FIELD_PATH = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z")
_FORMATS = {
    "char": {"text"},
    "text": {"text"},
    "html": {"text"},
    "integer": {"integer", "text"},
    "float": {"float", "text"},
    "date": {"date", "text"},
    "datetime": {"datetime", "text"},
    "boolean": {"boolean", "text"},
    "selection": {"selection", "text"},
    "many2one": {"many2one", "text"},
    "monetary": {"monetary", "float", "text"},
}
_PATH_TERMINALS = {
    "char",
    "text",
    "integer",
    "float",
    "date",
    "datetime",
    "boolean",
    "selection",
    "monetary",
}
_UNAUTHORIZED = object()


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class TemplatePart:
    text: str = ""
    field_name: str = ""
    format_key: str = ""

    @property
    def is_variable(self):
        return bool(self.field_name)

    @property
    def is_loop(self):
        return False

    @property
    def root_field_name(self):
        return self.field_name.split(".", 1)[0]


@dataclass(frozen=True)
class LoopPart:
    field_name: str
    body: tuple
    source_length: int

    @property
    def is_variable(self):
        return False

    @property
    def is_loop(self):
        return True


def _matching_loop_close(template, start, field_name):
    depth = 1
    index = start
    while index < len(template):
        if template.startswith("{{", index) or template.startswith("}}", index):
            index += 2
            continue
        if template[index] != "{":
            index += 1
            continue
        end = template.find("}", index + 1)
        if end < 0:
            return None
        token = template[index + 1 : end]
        if token == field_name:
            depth += 1
        elif token == "/" + field_name:
            depth -= 1
            if depth == 0:
                return index
        index = end + 1
    return None


def parse_template(template):
    if not isinstance(template, str) or not template.strip():
        raise TemplateError(_("Card template must not be empty."))
    try:
        template_size = len(template.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise TemplateError(_("Card template must be valid UTF-8 text.")) from exc
    if template_size > MAX_TEMPLATE_BYTES:
        raise TemplateError(_("Card template exceeds the 8 KiB limit."))

    variable_count = 0
    loop_count = 0

    def parse_scope(index, expected_close=None, depth=0):
        nonlocal variable_count, loop_count
        parts = []
        literal = []

        def flush_literal():
            if literal:
                parts.append(TemplatePart(text="".join(literal)))
                literal.clear()

        while index < len(template):
            char = template[index]
            if char == "\\" and index + 1 < len(template):
                escaped = template[index + 1]
                if escaped in ("n", "t"):
                    literal.append("\n" if escaped == "n" else "\t")
                    index += 2
                    continue
            if template.startswith("{{", index):
                literal.append("{")
                index += 2
                continue
            if template.startswith("}}", index):
                literal.append("}")
                index += 2
                continue
            if char == "{":
                end = template.find("}", index + 1)
                if end < 0 or "{" in template[index + 1 : end]:
                    raise TemplateError(_("Card template contains an unclosed variable."))
                token = template[index + 1 : end]
                if token.startswith("/"):
                    closing_name = token[1:]
                    if expected_close == closing_name:
                        flush_literal()
                        return tuple(parts), end + 1, index
                    raise TemplateError(_("Card template contains an unmatched loop end tag."))

                field_name, separator, format_key = token.partition(":")
                if (
                    not separator
                    and _FIELD_NAME.fullmatch(field_name)
                    and _matching_loop_close(template, end + 1, field_name) is not None
                ):
                    if depth >= MAX_LOOP_DEPTH:
                        raise TemplateError(_("Card template exceeds the two-level loop limit."))
                    flush_literal()
                    loop_count += 1
                    if loop_count > MAX_LOOP_BLOCKS:
                        raise TemplateError(_("Card template exceeds the five-loop limit."))
                    body_start = end + 1
                    body, next_index, close_start = parse_scope(
                        body_start, expected_close=field_name, depth=depth + 1
                    )
                    source_length = close_start - body_start
                    if source_length > MAX_LOOP_BODY_CODEPOINTS:
                        raise TemplateError(
                            _("Card template loop body exceeds 1000 characters.")
                        )
                    parts.append(
                        LoopPart(
                            field_name=field_name,
                            body=body,
                            source_length=source_length,
                        )
                    )
                    index = next_index
                    continue

                if not _FIELD_PATH.fullmatch(field_name):
                    raise TemplateError(_("Card template contains an invalid field variable."))
                if separator and not format_key:
                    raise TemplateError(_("Card template contains an empty format key."))
                if separator and format_key not in {
                    item for formats in _FORMATS.values() for item in formats
                }:
                    raise TemplateError(_("Card template contains an unsupported format key."))
                flush_literal()
                parts.append(TemplatePart(field_name=field_name, format_key=format_key))
                variable_count += 1
                if variable_count > MAX_VARIABLES:
                    raise TemplateError(_("Card template exceeds the 50 variable limit."))
                index = end + 1
                continue
            if char == "}":
                raise TemplateError(_("Card template contains an unmatched closing brace."))
            literal.append(char)
            index += 1

        if expected_close:
            raise TemplateError(_("Card template contains an unclosed loop block."))
        flush_literal()
        return tuple(parts), index, None

    parts = parse_scope(0)[0]
    return parts


def validate_template(
    template,
    models,
    check_permissions=True,
    many2many_separator=", ",
):
    parts = parse_template(template)
    if not models:
        raise TemplateError(_("Card template requires at least one mapped model."))
    validate_many2many_separator(many2many_separator)

    for model in models:
        if check_permissions:
            try:
                model.check_access_rights("read")
            except AccessError as exc:
                raise TemplateError(_("Card template model is not readable.")) from exc
        _validate_scope(parts, model, check_permissions)
    return parts


def validate_many2many_separator(separator):
    if separator is None:
        return ", "
    if not isinstance(separator, str):
        raise TemplateError(_("Many2many separator must be plain text."))
    try:
        separator.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise TemplateError(_("Many2many separator must be valid UTF-8 text.")) from exc
    return separator


def _validate_scope(parts, model, check_permissions):
    for part in parts:
        if part.is_loop:
            field = _field(model, part.field_name)
            if field.type != "one2many":
                raise TemplateError(
                    _("Loop field %(field)s must be a direct One2many field.")
                    % {"field": part.field_name}
                )
            _validate_relation_field(model, part.field_name, field, check_permissions)
            related_model = _related_model(model, field, check_permissions)
            _validate_scope(part.body, related_model, check_permissions)
        elif part.is_variable:
            _validate_path(model, part, check_permissions)


def _field(model, name):
    field = model._fields.get(name)
    if field is None:
        raise TemplateError(
            _("Field %(field)s is missing on %(model)s.")
            % {"field": name, "model": model._name}
        )
    return field


def _validate_relation_field(model, name, field, check_permissions):
    if not field.store or field.related:
        raise TemplateError(_("Relation field %(field)s is not supported.") % {"field": name})
    _check_field_permission(model, name, check_permissions)


def _related_model(model, field, check_permissions):
    model_name = field.comodel_name
    if not model_name or model_name not in model.env:
        raise TemplateError(_("Relation field has an unavailable target model."))
    related_model = model.env[model_name]
    if check_permissions:
        try:
            related_model.check_access_rights("read")
        except AccessError as exc:
            raise TemplateError(_("Related model is not readable.")) from exc
    return related_model


def _check_field_permission(model, name, check_permissions):
    if check_permissions:
        try:
            model.check_field_access_rights("read", [name])
        except AccessError as exc:
            raise TemplateError(_("Card template fields are not readable.")) from exc


def _terminal_path_field(model, path):
    current_model = model
    for name in path[:-1]:
        field = _field(current_model, name)
        if field.type not in {"many2one", "many2many"}:
            raise TemplateError(
                _("Relation path contains an unsupported field type.")
            )
        current_model = _related_model(current_model, field, False)
    return current_model, _field(current_model, path[-1])


def _expand_related_path(
    model, path, allow_terminal_related, seen=frozenset(), allow_single_related=False
):
    if len(path) > 16 or len(seen) > 16:
        raise TemplateError(_("Related field path exceeds its safe expansion limit."))

    current_model = model
    expanded = []
    for index, name in enumerate(path):
        field = _field(current_model, name)
        if field.related:
            is_terminal = index == len(path) - 1
            if (
                not allow_terminal_related
                or not is_terminal
                or (index == 0 and not allow_single_related)
            ):
                raise TemplateError(
                    _("Related field %(field)s is not supported.")
                    % {"field": name}
                )
            key = (current_model._name, name)
            if key in seen:
                raise TemplateError(_("Related field path contains a cycle."))
            related_path = tuple(str(field.related).split("."))
            if not related_path or any(not _FIELD_NAME.fullmatch(item) for item in related_path):
                raise TemplateError(_("Related field path is invalid."))
            expanded.extend(
                _expand_related_path(
                    current_model,
                    related_path,
                    True,
                    seen | {key},
                    True,
                )
            )
            break

        expanded.append(name)
        if index < len(path) - 1:
            if field.type not in {"many2one", "many2many"}:
                raise TemplateError(
                    _("Relation path contains an unsupported field type.")
                )
            current_model = _related_model(current_model, field, False)
    return expanded


def _validate_path(model, part, check_permissions):
    original_path = part.field_name.split(".")
    if len(original_path) > 1:
        alias_model, alias_field = _terminal_path_field(model, original_path)
        if alias_field.related:
            _check_field_permission(
                alias_model, original_path[-1], check_permissions
            )
    path = _expand_related_path(
        model, original_path, allow_terminal_related=len(original_path) > 1
    )
    current_model = model
    fields = []
    for name in path:
        field = _field(current_model, name)
        if not field.store or field.related:
            raise TemplateError(_("Field %(field)s is not supported.") % {"field": name})
        _check_field_permission(current_model, name, check_permissions)
        fields.append((current_model, field))
        if len(fields) < len(path):
            if field.type not in {"many2one", "many2many"}:
                raise TemplateError(
                    _("Relation path %(path)s contains an unsupported field type.")
                    % {"path": part.field_name}
                )
            if field.type == "many2many" and len(fields) != 1:
                raise TemplateError(
                    _("Many2many is only supported as the first relation in a path.")
                )
            current_model = _related_model(current_model, field, check_permissions)

    root_field = fields[0][1]
    terminal_model, terminal_field = fields[-1]
    if len(path) == 1:
        if terminal_field.type in {"one2many", "many2many"}:
            raise TemplateError(
                _("Relation field %(field)s must use a supported path or loop.")
                % {"field": part.field_name}
            )
        if terminal_field.type not in _FORMATS:
            raise TemplateError(
                _("Field %(field)s has an unsupported type.")
                % {"field": part.field_name}
            )
    else:
        if root_field.type not in {"many2one", "many2many"}:
            raise TemplateError(
                _("Relation path %(path)s must start with Many2one or Many2many.")
                % {"path": part.field_name}
            )
        if terminal_field.type not in _PATH_TERMINALS:
            raise TemplateError(
                _("Relation path %(path)s must end in a supported ordinary field.")
                % {"path": part.field_name}
            )
        relation_hops = len(path) - 1
        max_hops = 3 if root_field.type == "many2one" else 2
        if relation_hops > max_hops:
            raise TemplateError(
                _("Relation path %(path)s exceeds its maximum depth.")
                % {"path": part.field_name}
            )

    allowed_formats = _FORMATS.get(terminal_field.type, set())
    selected_format = part.format_key or _default_format(terminal_field.type)
    if selected_format not in allowed_formats:
        raise TemplateError(
            _("Format %(format)s is incompatible with field %(field)s.")
            % {"format": selected_format, "field": part.field_name}
        )
    if terminal_field.type == "monetary":
        currency_field_name = terminal_field.get_currency_field(terminal_model)
        currency_field = terminal_model._fields.get(currency_field_name)
        if (
            currency_field is None
            or currency_field.type != "many2one"
            or currency_field.comodel_name != "res.currency"
        ):
            raise TemplateError(_("Monetary fields require a res.currency field."))
        _check_field_permission(
            terminal_model, currency_field_name, check_permissions
        )


def template_field_names(template):
    names = []
    for part in parse_template(template):
        if part.is_variable:
            names.append(part.root_field_name)
        elif part.is_loop:
            names.append(part.field_name)
    return tuple(dict.fromkeys(names))


def template_direct_field_names(template):
    return tuple(
        dict.fromkeys(
            part.field_name
            for part in parse_template(template)
            if part.is_variable and "." not in part.field_name
        )
    )


def template_read_field_names(model, template):
    names = list(template_field_names(template))
    for name in tuple(names):
        field = model._fields.get(name)
        if not field:
            continue
        if field.type == "monetary":
            currency_name = field.get_currency_field(model)
            if currency_name:
                names.append(currency_name)
    return tuple(dict.fromkeys(names))


def render_template(
    env,
    model_name,
    values,
    readable_fields,
    template,
    unauthorized_placeholder="",
    many2many_separator=", ",
):
    model = env[model_name]
    parts = parse_template(template)
    root_record = values.get("_record") if isinstance(values, dict) else None
    return _render_scope(
        env,
        model,
        parts,
        values,
        set(readable_fields or ()),
        root_record,
        True,
        unauthorized_placeholder,
        validate_many2many_separator(many2many_separator),
    )


def _render_scope(
    env,
    model,
    parts,
    values,
    readable_fields,
    record,
    is_root,
    unauthorized_placeholder,
    separator,
):
    rendered = []
    for part in parts:
        if not part.is_variable and not part.is_loop:
            rendered.append(part.text)
            continue
        if part.is_loop:
            if record:
                children = _visible_relation_records(record, part.field_name, "one2many")
                if children is _UNAUTHORIZED:
                    rendered.append(unauthorized_placeholder)
                    continue
                for child in children:
                    rendered.append(
                        _render_scope(
                            env,
                            child.env[child._name],
                            part.body,
                            {},
                            set(),
                            child,
                            False,
                            unauthorized_placeholder,
                            separator,
                        )
                    )
            else:
                field = model._fields.get(part.field_name)
                if not field or not _synthetic_field_accessible(model, part.field_name):
                    rendered.append(
                        unauthorized_placeholder
                        if field
                        else ""
                    )
                    continue
                related_model = env[field.comodel_name]
                rendered.append(
                    _render_scope(
                        env,
                        related_model,
                        part.body,
                        {},
                        set(),
                        None,
                        False,
                        unauthorized_placeholder,
                        separator,
                    )
                )
            continue

        if record is None:
            result = _render_synthetic_variable(
                env,
                model,
                part,
                values,
                readable_fields,
                is_root,
                separator,
            )
        elif is_root and "." not in part.field_name:
            result = _render_root_variable(
                env, model, part, values, readable_fields
            )
        else:
            if is_root and part.root_field_name not in readable_fields:
                result = _UNAUTHORIZED
            else:
                result = _resolve_path(
                    record, part.field_name.split("."), part.format_key, separator
                )
        rendered.append(
            unauthorized_placeholder if result is _UNAUTHORIZED else result
        )
    return "".join(rendered)


def _render_root_variable(env, model, part, values, readable_fields):
    name = part.field_name
    field = model._fields.get(name)
    if not field:
        return ""
    if name not in readable_fields or name not in values:
        return _UNAUTHORIZED
    if field.type in {"one2many", "many2many"}:
        raise TemplateError(_("Relation fields cannot be rendered as scalar variables."))
    value = values[name]
    if _is_empty(value, field.type):
        return "—"
    if field.type == "monetary" and not values.get("_currency_%s" % field.name):
        return "—"
    format_key = part.format_key or _default_format(field.type)
    return _format_value(env, model, field, value, format_key, values)


def _render_synthetic_variable(
    env, model, part, values, readable_fields, is_root, separator
):
    if is_root and part.root_field_name not in readable_fields:
        return _UNAUTHORIZED if part.root_field_name in model._fields else ""
    if "." not in part.field_name:
        if part.field_name in values:
            return _render_root_variable(env, model, part, values, readable_fields)
        field = model._fields.get(part.field_name)
        if not field:
            return ""
        if not _synthetic_field_accessible(model, part.field_name):
            return _UNAUTHORIZED
        value = _sample_value(env, model, field)
        return _format_sample(env, model, field, value, part.format_key)

    original_fields = part.field_name.split(".")
    alias_model, alias_field = _terminal_path_field(model, original_fields)
    if alias_field.related and not _synthetic_field_accessible(
        alias_model, original_fields[-1]
    ):
        return _UNAUTHORIZED
    current_model = model
    fields = _expand_related_path(
        model, original_fields, allow_terminal_related=True
    )
    for index, name in enumerate(fields):
        field = current_model._fields.get(name)
        if not field or not _synthetic_field_accessible(current_model, name):
            return _UNAUTHORIZED if field else ""
        if index < len(fields) - 1:
            if field.type not in {"many2one", "many2many"}:
                return ""
            current_model = env[field.comodel_name]
            continue
        if field.type not in _PATH_TERMINALS:
            return ""
        value = _sample_value(env, current_model, field)
        formatted = _format_sample(env, current_model, field, value, part.format_key)
        if model._fields[fields[0]].type == "many2many":
            return separator.join((formatted, formatted))
        return formatted

    return "—"


def _sample_value(env, model, field):
    if field.type in {"char", "text", "html", "many2one"}:
        return "Example"
    if field.type in {"integer", "float", "monetary"}:
        return 1234
    if field.type == "boolean":
        return True
    if field.type == "date":
        return "2026-10-10"
    if field.type == "datetime":
        return "2026-10-10 09:30:00"
    if field.type == "selection":
        selection = model.fields_get([field.name])[field.name].get("selection", [])
        return selection[0][0] if selection else False
    return False


def _format_sample(env, model, field, value, format_key):
    if field.type == "monetary":
        values = {"_currency_%s" % field.name: env.company.currency_id}
    else:
        values = {}
    if _is_empty(value, field.type):
        return "—"
    return _format_value(
        env,
        model,
        field,
        value,
        format_key or _default_format(field.type),
        values,
    )


def _synthetic_field_accessible(model, name):
    try:
        model.check_field_access_rights("read", [name])
        field = model._fields[name]
        if field.type in {"many2one", "many2many", "one2many"}:
            model.env[field.comodel_name].check_access_rights("read")
    except AccessError:
        return False
    return True


def _visible_relation_records(record, name, expected_type=None):
    model = record.env[record._name]
    field = model._fields.get(name)
    if not field or (expected_type and field.type != expected_type):
        return _UNAUTHORIZED
    try:
        model.check_field_access_rights("read", [name])
        related_model = record.env[field.comodel_name]
        related_model.check_access_rights("read")
        linked_ids = record[name].ids
        if not linked_ids:
            return related_model.browse()
        order_parts = [
            item.strip()
            for item in (related_model._order or "").split(",")
            if item.strip() and item.strip().split()[0] != "id"
        ]
        order = ", ".join(order_parts + ["id asc"])
        records = related_model.search(
            [("id", "in", linked_ids)], order=order, limit=len(linked_ids)
        )
        if field.type == "many2one" and not records:
            return _UNAUTHORIZED
        return records
    except AccessError:
        return _UNAUTHORIZED


def _resolve_path(record, path, format_key, separator):
    model = record.env[record._name]
    original_path = list(path)
    if len(original_path) > 1:
        alias_model, alias_field = _terminal_path_field(model, original_path)
        if alias_field.related:
            try:
                alias_model.check_field_access_rights(
                    "read", [original_path[-1]]
                )
            except AccessError:
                return _UNAUTHORIZED
    expanded_path = _expand_related_path(
        model, original_path, allow_terminal_related=len(original_path) > 1
    )
    return _resolve_expanded_path(record, expanded_path, format_key, separator)


def _resolve_expanded_path(record, path, format_key, separator):
    model = record.env[record._name]
    field_name = path[0]
    field = model._fields.get(field_name)
    if not field:
        return ""
    if len(path) == 1:
        try:
            model.check_field_access_rights("read", [field_name])
        except AccessError:
            return _UNAUTHORIZED
        if field.type in {"many2one", "many2many", "one2many"}:
            if field.type == "many2one":
                related = _visible_relation_records(record, field_name, "many2one")
                if related is _UNAUTHORIZED:
                    return _UNAUTHORIZED
                return "—" if not related else str(related.display_name)
            return _UNAUTHORIZED
        value = record[field_name]
        if _is_empty(value, field.type):
            return "—"
        return _format_record_value(record, field, value, format_key)

    if field.type == "many2many":
        related = _visible_relation_records(record, field_name, "many2many")
        if related is _UNAUTHORIZED:
            return _UNAUTHORIZED
        if not related:
            return "—"
        rendered = [
            _resolve_expanded_path(item, path[1:], format_key, separator)
            for item in related
        ]
        visible = [value for value in rendered if value is not _UNAUTHORIZED]
        if not visible:
            return _UNAUTHORIZED if rendered else "—"
        return separator.join(visible)
    if field.type != "many2one":
        return _UNAUTHORIZED
    related = _visible_relation_records(record, field_name, "many2one")
    if related is _UNAUTHORIZED:
        return _UNAUTHORIZED
    if not related:
        return "—"
    return _resolve_expanded_path(related[0], path[1:], format_key, separator)


def _format_record_value(record, field, value, format_key):
    model = record.env[record._name]
    currency_values = {}
    if field.type == "monetary":
        currency_name = field.get_currency_field(model)
        currency = _visible_relation_records(record, currency_name, "many2one")
        if currency is _UNAUTHORIZED:
            return _UNAUTHORIZED
        if not currency:
            return "—"
        currency_values["_currency_%s" % field.name] = currency
    return _format_value(
        record.env,
        model,
        field,
        value,
        format_key or _default_format(field.type),
        currency_values,
    )


def _default_format(field_type):
    return {
        "char": "text",
        "text": "text",
        "html": "text",
        "integer": "integer",
        "float": "float",
        "date": "date",
        "datetime": "datetime",
        "boolean": "boolean",
        "selection": "selection",
        "many2one": "many2one",
        "monetary": "monetary",
    }[field_type]


def _is_empty(value, field_type):
    return value is None or value == "" or (value is False and field_type != "boolean")


def _format_value(env, model, field, value, format_key, values):
    if format_key == "boolean":
        return _("Yes") if value else _("No")
    if format_key == "integer":
        return formatLang(env, int(value), digits=0)
    if format_key == "float":
        return formatLang(env, value)
    if format_key == "date":
        return format_date(env, value)
    if format_key == "datetime":
        return format_datetime(env, value)
    if format_key == "selection":
        selection = model.fields_get([field.name])[field.name].get("selection", [])
        return dict(selection).get(value, "")
    if format_key == "many2one":
        if isinstance(value, (tuple, list)):
            return value[1] if len(value) > 1 else ""
        return str(value)
    if format_key == "monetary":
        currency = values.get("_currency_%s" % field.name)
        if not currency:
            raise TemplateError(_("Monetary field currency is not readable."))
        return formatLang(env, value, currency_obj=currency)
    if field.type == "html":
        from odoo.tools import html2plaintext

        return html2plaintext(value)
    if isinstance(value, (tuple, list)):
        return value[1] if len(value) > 1 else (value[0] if value else "")
    return str(value)
