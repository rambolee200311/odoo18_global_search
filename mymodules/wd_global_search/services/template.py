import re
from dataclasses import dataclass

from odoo import _
from odoo.exceptions import AccessError
from odoo.tools.misc import format_date, format_datetime, formatLang


MAX_TEMPLATE_BYTES = 8 * 1024
MAX_VARIABLES = 50
_FIELD_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
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


def parse_template(template):
    if not isinstance(template, str) or not template.strip():
        raise TemplateError(_("Card template must not be empty."))
    try:
        template_size = len(template.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise TemplateError(_("Card template must be valid UTF-8 text.")) from exc
    if template_size > MAX_TEMPLATE_BYTES:
        raise TemplateError(_("Card template exceeds the 8 KiB limit."))

    parts = []
    literal = []
    index = 0

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
            flush_literal()
            end = template.find("}", index + 1)
            if end < 0 or "{" in template[index + 1 : end]:
                raise TemplateError(_("Card template contains an unclosed variable."))
            token = template[index + 1 : end]
            field_name, separator, format_key = token.partition(":")
            if not _FIELD_NAME.fullmatch(field_name):
                raise TemplateError(_("Card template contains an invalid field variable."))
            if separator and not format_key:
                raise TemplateError(_("Card template contains an empty format key."))
            if separator and format_key not in {
                item for formats in _FORMATS.values() for item in formats
            }:
                raise TemplateError(_("Card template contains an unsupported format key."))
            parts.append(
                TemplatePart(field_name=field_name, format_key=format_key)
            )
            if sum(part.is_variable for part in parts) > MAX_VARIABLES:
                raise TemplateError(_("Card template exceeds the 50 variable limit."))
            index = end + 1
            continue
        if char == "}":
            raise TemplateError(_("Card template contains an unmatched closing brace."))
        literal.append(char)
        index += 1

    flush_literal()
    return tuple(parts)


def validate_template(template, models, check_permissions=True):
    parts = parse_template(template)
    variables = [part for part in parts if part.is_variable]
    if not models:
        raise TemplateError(_("Card template requires at least one mapped model."))

    for model in models:
        field_names = list(dict.fromkeys(part.field_name for part in variables))
        if check_permissions:
            try:
                model.check_access_rights("read")
                if field_names:
                    model.check_field_access_rights("read", field_names)
            except AccessError as exc:
                raise TemplateError(_("Card template fields are not readable.")) from exc
        for part in variables:
            field = model._fields.get(part.field_name)
            if (
                field is None
                or field.type not in _FORMATS
                or not field.store
                or field.related
            ):
                raise TemplateError(
                    _("Field %(field)s is missing or unsupported on %(model)s.")
                    % {"field": part.field_name, "model": model._name}
                )
            allowed_formats = _FORMATS[field.type]
            selected_format = part.format_key or _default_format(field.type)
            if selected_format not in allowed_formats:
                raise TemplateError(
                    _("Format %(format)s is incompatible with field %(field)s.")
                    % {"format": selected_format, "field": part.field_name}
                )
            if field.type == "monetary":
                currency_field = model._fields.get(
                    getattr(field, "currency_field", "")
                )
                if (
                    currency_field is None
                    or currency_field.type != "many2one"
                    or currency_field.comodel_name != "res.currency"
                ):
                    raise TemplateError(
                        _("Monetary fields require a res.currency field.")
                    )
                if check_permissions:
                    try:
                        model.check_field_access_rights(
                            "read", [field.currency_field]
                        )
                    except AccessError as exc:
                        raise TemplateError(
                            _("Monetary currency fields are not readable.")
                        ) from exc
    return parts


def template_field_names(template):
    return tuple(
        dict.fromkeys(
            part.field_name for part in parse_template(template) if part.is_variable
        )
    )


def template_read_field_names(model, template):
    names = list(template_field_names(template))
    for name in tuple(names):
        field = model._fields[name]
        if field.type == "monetary" and field.currency_field:
            names.append(field.currency_field)
    return tuple(dict.fromkeys(names))


def render_template(
    env, model_name, values, readable_fields, template, unauthorized_placeholder=""
):
    model = env[model_name]
    parts = parse_template(template)
    rendered = []
    for part in parts:
        if not part.is_variable:
            rendered.append(part.text)
            continue
        if part.field_name not in readable_fields or part.field_name not in values:
            rendered.append(
                unauthorized_placeholder
                if part.field_name in model._fields
                else ""
            )
            continue
        field = model._fields[part.field_name]
        value = values[part.field_name]
        if _is_empty(value, field.type):
            rendered.append("—")
            continue
        format_key = part.format_key or _default_format(field.type)
        rendered.append(_format_value(env, model, field, value, format_key, values))
    return "".join(rendered)


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
