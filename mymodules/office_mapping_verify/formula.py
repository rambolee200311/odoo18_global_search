"""Parser for the deliberately small arithmetic subset accepted for XLSX formulas."""

from __future__ import annotations

import re


_TOKEN = re.compile(
    r"\s*(?:(\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)|((?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?)|([()+\-*/]))"
)


def formula_references(formula: object) -> tuple[str, ...]:
    """Return cell references if *formula* is safe arithmetic; else raise ValueError.

    The grammar intentionally excludes functions, ranges, sheet/external links,
    names, strings, and all command-capable Excel constructs.
    """
    if not isinstance(formula, str) or not formula.startswith("=") or len(formula) > 512:
        raise ValueError("invalid_formula")
    expression = formula[1:]
    if not expression.strip():
        raise ValueError("invalid_formula")
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(expression):
        match = _TOKEN.match(expression, position)
        if not match:
            raise ValueError("invalid_formula")
        reference, number, operator = match.groups()
        if reference:
            tokens.append(("reference", reference))
        elif number:
            tokens.append(("number", number))
        else:
            tokens.append(("operator", operator))
        position = match.end()
        if len(tokens) > 128:
            raise ValueError("invalid_formula")
    cursor = 0
    references: list[str] = []

    def peek(value: str | None = None) -> bool:
        if cursor >= len(tokens):
            return False
        return value is None or tokens[cursor] == ("operator", value)

    def consume() -> tuple[str, str]:
        nonlocal cursor
        if cursor >= len(tokens):
            raise ValueError("invalid_formula")
        token = tokens[cursor]
        cursor += 1
        return token

    def expression_rule() -> None:
        term_rule()
        while peek("+") or peek("-"):
            consume()
            term_rule()

    def term_rule() -> None:
        factor_rule()
        while peek("*") or peek("/"):
            consume()
            factor_rule()

    def factor_rule() -> None:
        if peek("+") or peek("-"):
            consume()
            factor_rule()
            return
        if peek("("):
            consume()
            expression_rule()
            if not peek(")"):
                raise ValueError("invalid_formula")
            consume()
            return
        kind, value = consume()
        if kind == "reference":
            references.append(value.replace("$", "").upper())
        elif kind != "number":
            raise ValueError("invalid_formula")

    expression_rule()
    if cursor != len(tokens):
        raise ValueError("invalid_formula")
    return tuple(references)
