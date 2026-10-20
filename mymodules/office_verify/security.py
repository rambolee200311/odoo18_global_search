"""Bounded ZIP/XML reader independent from office_core."""

from __future__ import annotations

import posixpath
import re
import zipfile
import zlib
from dataclasses import dataclass
from io import BytesIO

from lxml import etree

from .errors import OfficeVerifyError
from .models import VerificationBudget

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
MIME_BY_EXT = {
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
}
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"


@dataclass(frozen=True)
class Package:
    kind: str
    entries: tuple[str, ...]
    raw_parts: dict[str, bytes]
    roots: dict[str, etree._Element]
    relationships: dict[str, tuple[tuple[str, str, str], ...]]


def _invalid(stage: str) -> OfficeVerifyError:
    return OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", stage, "Office 文件无效或与声明格式不一致。")


def _unsupported(stage: str) -> OfficeVerifyError:
    return OfficeVerifyError("OFFICE_UNSUPPORTED_FEATURE", stage, "文件包含当前未启用或不安全的 Office 结构。")


def _resource(stage: str) -> OfficeVerifyError:
    return OfficeVerifyError("OFFICE_RESOURCE_LIMIT", stage, "Office 文件超过回读资源限制。")


def _safe_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        return False
    normalized = posixpath.normpath(name)
    return normalized == name.rstrip("/") and normalized not in {".", ".."} and not normalized.startswith("../")


def _allowed_part(kind: str, name: str) -> bool:
    if name in {"[Content_Types].xml", "_rels/.rels", "docProps/app.xml", "docProps/core.xml"}:
        return True
    if kind == "xlsx":
        return bool(
            re.fullmatch(r"xl/workbook\.xml", name)
            or re.fullmatch(r"xl/_rels/workbook\.xml\.rels", name)
            or re.fullmatch(r"xl/styles\.xml", name)
            or re.fullmatch(r"xl/theme/theme\d+\.xml", name)
            or re.fullmatch(r"xl/sharedStrings\.xml", name)
            or re.fullmatch(r"xl/calcChain\.xml", name)
            or re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
            or re.fullmatch(r"xl/worksheets/_rels/sheet\d+\.xml\.rels", name)
        )
    return bool(
        re.fullmatch(r"word/document\.xml", name)
        or re.fullmatch(r"word/styles\.xml", name)
        or re.fullmatch(r"word/settings\.xml", name)
        or re.fullmatch(r"word/numbering\.xml", name)
        or re.fullmatch(r"word/fontTable\.xml", name)
        or re.fullmatch(r"word/webSettings\.xml", name)
        or re.fullmatch(r"word/theme/theme\d+\.xml", name)
        or re.fullmatch(r"word/_rels/document\.xml\.rels", name)
        or re.fullmatch(r"word/_rels/(styles|settings|numbering|fontTable|webSettings)\.xml\.rels", name)
    )


def _parse_xml(data: bytes, budget: VerificationBudget) -> etree._Element:
    if len(data) > budget.max_entry_size:
        raise _resource("xml")
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
        recover=False,
        remove_comments=False,
    )
    try:
        tree = etree.parse(BytesIO(data), parser)
    except (etree.XMLSyntaxError, ValueError, OSError) as exc:
        raise _invalid("xml") from exc
    if tree.docinfo.doctype:
        raise _unsupported("xml")
    root = tree.getroot()
    nodes = 0
    for node in root.iter():
        nodes += 1
        if nodes > budget.max_xml_elements:
            raise _resource("xml")
        if isinstance(node, etree._Entity):
            raise _unsupported("xml")
    return root


def _relationship_source(rel_name: str) -> str:
    if rel_name == "_rels/.rels":
        return ""
    match = re.fullmatch(r"(.+)/_rels/([^/]+)\.rels", rel_name)
    if not match:
        raise _invalid("relationships")
    return f"{match.group(1)}/{match.group(2)}"


def _resolve_target(source: str, target: str) -> str:
    if not target or "\\" in target or "\x00" in target or target.startswith("//"):
        raise _invalid("relationships")
    if target.startswith("/"):
        resolved = posixpath.normpath(target.lstrip("/"))
    else:
        base = posixpath.dirname(source)
        resolved = posixpath.normpath(posixpath.join(base, target)) if base else posixpath.normpath(target)
    if resolved in {".", ".."} or resolved.startswith("../"):
        raise _invalid("relationships")
    return resolved


def _read_relationships(rel_name: str, root: etree._Element, names: set[str]) -> tuple[tuple[str, str, str], ...]:
    if root.tag != REL_NS + "Relationships":
        raise _invalid("relationships")
    source = _relationship_source(rel_name)
    seen_ids: set[str] = set()
    result: list[tuple[str, str, str]] = []
    for rel in root.findall(REL_NS + "Relationship"):
        rel_id = rel.get("Id", "")
        target = rel.get("Target", "")
        rel_type = rel.get("Type", "")
        if not rel_id or rel_id in seen_ids or not rel_type:
            raise _invalid("relationships")
        seen_ids.add(rel_id)
        if rel.get("TargetMode", "Internal") == "External":
            raise _unsupported("relationships")
        resolved = _resolve_target(source, target)
        if resolved not in names:
            raise _invalid("relationships")
        result.append((rel_id, rel_type, resolved))
    return tuple(sorted(result))


def _validate_content_types(root: etree._Element, names: set[str]) -> None:
    if root.tag != CT_NS + "Types":
        raise _invalid("content_types")
    defaults: set[str] = set()
    overrides: set[str] = set()
    for node in root:
        if node.tag == CT_NS + "Default":
            extension = node.get("Extension", "").lower()
            content_type = node.get("ContentType", "")
            if not extension or extension in defaults or extension not in {"xml", "rels"} or not content_type:
                raise _unsupported("content_types")
            defaults.add(extension)
        elif node.tag == CT_NS + "Override":
            part_name = node.get("PartName", "")
            content_type = node.get("ContentType", "")
            normalized = part_name.lstrip("/")
            if not part_name.startswith("/") or not normalized or normalized in overrides or normalized not in names or not content_type:
                raise _invalid("content_types")
            if any(marker in content_type.lower() for marker in ("macroenabled", "vbaproject", "oleobject", "externallink")):
                raise _unsupported("content_types")
            overrides.add(normalized)
        else:
            raise _unsupported("content_types")


def read_package(data: bytes, filename: str, mime_type: str, budget: VerificationBudget) -> Package:
    budget.validate()
    if not isinstance(data, bytes) or not data or not isinstance(filename, str) or not isinstance(mime_type, str):
        raise _invalid("input")
    if len(data) > budget.max_file_size:
        raise _resource("input")
    ext = posixpath.splitext(filename.lower())[1]
    normalized_mime = mime_type.lower().split(";", 1)[0].strip()
    if ext not in MIME_BY_EXT or normalized_mime not in MIME_BY_EXT[ext]:
        raise _invalid("input")
    if data.startswith(OLE_MAGIC):
        raise _unsupported("format")
    if not data.startswith(ZIP_MAGIC):
        raise _invalid("signature")
    kind = "xlsx" if ext == ".xlsx" else "docx"
    try:
        archive = zipfile.ZipFile(BytesIO(data), "r")
        infos = archive.infolist()
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise _invalid("container") from exc
    if len(infos) > budget.max_zip_entries:
        raise _resource("container")
    names: set[str] = set()
    declared_total = 0
    for info in infos:
        if not _safe_name(info.filename) or info.filename in names:
            raise _invalid("container")
        if info.is_dir():
            raise _unsupported("container")
        names.add(info.filename)
        if info.flag_bits & 0x1:
            raise _unsupported("container")
        if info.file_size > budget.max_entry_size:
            raise _resource("container")
        declared_total += info.file_size
        if declared_total > budget.max_expanded_size:
            raise _resource("container")
        if ((info.external_attr >> 16) & 0xF000) == 0xA000:
            raise _unsupported("container")
        if not _allowed_part(kind, info.filename):
            raise _unsupported("container")
    document_part = "xl/workbook.xml" if kind == "xlsx" else "word/document.xml"
    required = {"[Content_Types].xml", "_rels/.rels", document_part}
    if not required.issubset(names):
        raise _invalid("container")

    roots: dict[str, etree._Element] = {}
    raw_parts: dict[str, bytes] = {}
    actual_total = 0
    total_xml_nodes = 0
    try:
        for info in infos:
            if info.is_dir():
                continue
            chunks: list[bytes] = []
            member_size = 0
            with archive.open(info, "r") as member:
                while True:
                    chunk = member.read(64 * 1024)
                    if not chunk:
                        break
                    member_size += len(chunk)
                    actual_total += len(chunk)
                    if member_size > budget.max_entry_size or actual_total > budget.max_expanded_size:
                        raise _resource("container")
                    chunks.append(chunk)
            if member_size != info.file_size:
                raise _invalid("container")
            raw = b"".join(chunks)
            raw_parts[info.filename] = raw
            if info.filename.endswith(".xml") or info.filename.endswith(".rels"):
                root = _parse_xml(raw, budget)
                total_xml_nodes += sum(1 for _ in root.iter())
                if total_xml_nodes > budget.max_xml_elements:
                    raise _resource("xml")
                roots[info.filename] = root
    except (zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise _invalid("container") from exc
    relationships: dict[str, tuple[tuple[str, str, str], ...]] = {}
    _validate_content_types(roots["[Content_Types].xml"], names)
    for part_name, root in roots.items():
        if part_name.endswith(".rels"):
            relationships[part_name] = _read_relationships(part_name, root, names)
    try:
        bad_name = archive.testzip()
    except (zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise _invalid("container") from exc
    if bad_name:
        raise _invalid("container")
    return Package(kind, tuple(sorted(names)), raw_parts, roots, relationships)


BLOCKED_LOCAL_NAMES = {
    "extLst", "AlternateContent", "oleObject", "control", "externalLink", "txbxContent",
    "pict", "altChunk", "fldSimple", "instrText", "del", "ins", "sdt", "customXml",
    "commentRangeStart", "commentRangeEnd", "drawing", "hyperlink", "hyperlinks", "bookmarkStart", "bookmarkEnd",
    "dataValidations", "conditionalFormatting", "phoneticPr", "legacyDrawing", "gridSpan", "vMerge",
}


def reject_unsupported_nodes(package: Package) -> None:
    for root in package.roots.values():
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            if etree.QName(node).localname in BLOCKED_LOCAL_NAMES:
                raise _unsupported("structure")
