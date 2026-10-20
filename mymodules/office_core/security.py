"""Bounded validation for OOXML ZIP containers and secure XML preflight."""

from __future__ import annotations

import posixpath
import re
import zipfile
import zlib
from dataclasses import dataclass
from io import BytesIO

from lxml import etree

from .errors import OfficeCoreError
from .models import ResourceBudget

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
MIME_BY_EXT = {
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".doc": {"application/msword", "application/octet-stream"},
}


@dataclass(frozen=True)
class Package:
    kind: str
    entries: tuple[str, ...]
    xml_roots: dict[str, etree._Element]


def _invalid(stage: str, message: str = "文件格式无效或与声明不一致。") -> OfficeCoreError:
    return OfficeCoreError("OFFICE_INVALID_OR_MISMATCHED", stage, message)


def _unsupported(stage: str, message: str = "文件包含当前未启用的 Office 结构。") -> OfficeCoreError:
    return OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", stage, message)


def _resource(stage: str, message: str = "文件超过已配置的处理资源限制。") -> OfficeCoreError:
    return OfficeCoreError("OFFICE_RESOURCE_LIMIT", stage, message)


def _safe_member_name(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/") or "\x00" in name:
        return False
    normalized = posixpath.normpath(name)
    return normalized == name.rstrip("/") and normalized not in (".", "..") and not normalized.startswith("../")


def _parse_xml(name: str, data: bytes, budget: ResourceBudget) -> etree._Element:
    if len(data) > budget.max_entry_size:
        raise _resource("container", "Office XML 部件超过大小限制。")
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        recover=False,
        remove_comments=False,
    )
    try:
        tree = etree.parse(BytesIO(data), parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise _invalid("xml", "Office 文件中的 XML 结构无效。") from exc
    if tree.docinfo.doctype:
        raise _unsupported("xml", "不支持包含 DTD 的 Office XML。")
    root = tree.getroot()
    for node in root.iter():
        if isinstance(node, etree._Entity):
            raise _unsupported("xml", "不支持包含实体引用的 Office XML。")
    if sum(1 for _ in root.iter()) > budget.max_xml_elements:
        raise _resource("xml", "Office XML 结构数量超过限制。")
    return root


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


def _check_relationships(name: str, root: etree._Element, all_names: set[str]) -> None:
    ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    if root.tag != ns + "Relationships":
        raise _invalid("relationships")
    source = "" if name == "_rels/.rels" else name.rsplit("/_rels/", 1)[0] + "/" + name.rsplit("/_rels/", 1)[1][:-5]
    for rel in root.findall(ns + "Relationship"):
        if rel.get("TargetMode", "Internal") == "External":
            raise _unsupported("relationships", "不支持包含外部链接的 Office 文件。")
        target = rel.get("Target", "")
        if not target or target.startswith("//") or "\\" in target or "\x00" in target:
            raise _invalid("relationships")
        if target.startswith("/"):
            resolved = posixpath.normpath(target.lstrip("/"))
        else:
            base = posixpath.dirname(source)
            resolved = posixpath.normpath(posixpath.join(base, target)) if base else posixpath.normpath(target)
        if resolved.startswith("../") or resolved == ".." or resolved not in all_names:
            raise _invalid("relationships")


def inspect_package(data: bytes, filename: str, mime_type: str, budget: ResourceBudget) -> Package:
    budget.validate()
    if not isinstance(data, bytes) or not data:
        raise _invalid("input", "文件为空或内容类型无效。")
    if len(data) > budget.max_file_size:
        raise _resource("input", "文件超过输入大小限制。")
    if not isinstance(filename, str) or not isinstance(mime_type, str):
        raise _invalid("input")
    ext = posixpath.splitext(filename.lower())[1]
    if ext not in MIME_BY_EXT or mime_type.lower().split(";", 1)[0].strip() not in MIME_BY_EXT[ext]:
        raise _invalid("input")
    if data.startswith(OLE_MAGIC):
        if ext in {".xls", ".doc"}:
            raise _unsupported("format", "旧版 Office 文件当前未启用内容处理能力。")
        raise _invalid("signature")
    if not data.startswith(ZIP_MAGIC):
        raise _invalid("signature")
    kind = "xlsx" if ext == ".xlsx" else "docx" if ext == ".docx" else "disabled"
    if kind == "disabled":
        raise _unsupported("format", "该 Office 格式当前未启用内容处理能力。")
    try:
        archive = zipfile.ZipFile(BytesIO(data), "r")
        infos = archive.infolist()
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise _invalid("container") from exc
    if len(infos) > budget.max_zip_entries:
        raise _resource("container", "Office 容器条目数量超过限制。")
    names: set[str] = set()
    declared_total = 0
    for info in infos:
        if not _safe_member_name(info.filename) or info.filename in names:
            raise _invalid("container")
        names.add(info.filename)
        if info.flag_bits & 0x1:
            raise _unsupported("container", "不支持加密的 Office 文件。")
        if info.file_size > budget.max_entry_size:
            raise _resource("container", "Office 容器单个部件超过大小限制。")
        declared_total += info.file_size
        if declared_total > budget.max_expanded_size:
            raise _resource("container", "Office 容器展开大小超过限制。")
        unix_mode = (info.external_attr >> 16) & 0xF000
        if unix_mode == 0xA000:
            raise _unsupported("container", "不支持包含链接对象的 Office 容器。")
        if not _allowed_part(kind, info.filename):
            raise _unsupported("container", "文件包含当前未启用的 Office 部件。")
    required = {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml" if kind == "xlsx" else "word/document.xml"}
    if not required.issubset(names):
        raise _invalid("container")
    actual_total = 0
    total_xml_elements = 0
    xml_roots: dict[str, etree._Element] = {}
    try:
        for info in infos:
            if info.is_dir():
                continue
            with archive.open(info, "r") as member:
                chunks: list[bytes] = []
                member_size = 0
                while True:
                    chunk = member.read(64 * 1024)
                    if not chunk:
                        break
                    member_size += len(chunk)
                    actual_total += len(chunk)
                    if member_size > budget.max_entry_size or actual_total > budget.max_expanded_size:
                        raise _resource("container")
                    chunks.append(chunk)
                raw = b"".join(chunks)
            if member_size != info.file_size:
                raise _invalid("container")
            if info.filename.endswith(".xml") or info.filename.endswith(".rels"):
                root = _parse_xml(info.filename, raw, budget)
                total_xml_elements += sum(1 for _ in root.iter())
                if total_xml_elements > budget.max_xml_elements:
                    raise _resource("xml", "Office XML 总结构数量超过限制。")
                xml_roots[info.filename] = root
    except (zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise _invalid("container") from exc
    for name in names:
        if name.endswith(".rels"):
            _check_relationships(name, xml_roots[name], names)
    # Entire package must be testable without extraction; this also verifies CRCs.
    try:
        bad = archive.testzip()
    except (zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
        raise _invalid("container") from exc
    if bad:
        raise _invalid("container")
    return Package(kind=kind, entries=tuple(sorted(names)), xml_roots=xml_roots)


def reject_unsupported_ooxml_nodes(package: Package) -> None:
    blocked_local_names = {
        "extLst", "AlternateContent", "oleObject", "control", "externalLink",
        "txbxContent", "pict", "altChunk", "fldSimple", "instrText", "del",
        "ins", "sdt", "customXml", "commentRangeStart", "commentRangeEnd",
    }
    for root in package.xml_roots.values():
        for node in root.iter():
            local = etree.QName(node).localname if isinstance(node.tag, str) else ""
            if local in blocked_local_names:
                raise _unsupported("structure", "文件包含当前未启用的高级或活动 Office 对象。")
            if package.kind == "docx" and local in {"drawing", "hyperlink", "bookmarkStart", "bookmarkEnd"}:
                raise _unsupported("structure", "Word 文件包含当前未启用的图形、链接或书签结构。")
