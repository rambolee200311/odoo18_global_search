"""Bounded, provider-independent classification of Office attachment headers."""

from dataclasses import dataclass
from pathlib import PurePosixPath


_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_SIGNATURE = b"PK\x03\x04"

_EXTENSION_FAMILIES = {
    ".xlsx": "spreadsheet",
    ".xlsm": "spreadsheet",
    ".xltx": "spreadsheet",
    ".xltm": "spreadsheet",
    ".xls": "spreadsheet",
    ".xlt": "spreadsheet",
    ".xla": "spreadsheet",
    ".docx": "word",
    ".docm": "word",
    ".dotx": "word",
    ".dotm": "word",
    ".doc": "word",
    ".dot": "word",
    ".pptx": "presentation",
    ".pptm": "presentation",
    ".potx": "presentation",
    ".potm": "presentation",
    ".ppsx": "presentation",
    ".ppsm": "presentation",
    ".ppt": "presentation",
    ".pot": "presentation",
    ".pps": "presentation",
}

_MIME_FAMILIES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "spreadsheet",
    "application/vnd.ms-excel": "spreadsheet",
    "application/vnd.ms-excel.sheet.macroenabled.12": "spreadsheet",
    "application/vnd.ms-excel.template.macroenabled.12": "spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.template": "spreadsheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "word",
    "application/msword": "word",
    "application/vnd.ms-word.document.macroenabled.12": "word",
    "application/vnd.ms-word.template.macroenabled.12": "word",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template": "word",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "presentation",
    "application/vnd.ms-powerpoint": "presentation",
    "application/vnd.ms-powerpoint.presentation.macroenabled.12": "presentation",
    "application/vnd.ms-powerpoint.slideshow.macroenabled.12": "presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.slideshow": "presentation",
    "application/vnd.openxmlformats-officedocument.presentationml.template": "presentation",
}

_LEGACY_MIMES = {
    "application/vnd.ms-excel",
    "application/msword",
    "application/vnd.ms-powerpoint",
}

_GENERIC_BINARY_MIMES = {"", "application/octet-stream", "application/zip"}


@dataclass(frozen=True)
class AttachmentIdentity:
    """Safe classification result; it deliberately contains no filename or data."""

    is_office_candidate: bool
    is_mismatch: bool
    reason_code: str


def _normalized_mime(value):
    return (value or "").split(";", 1)[0].strip().lower()


def inspect_attachment_identity(name, mimetype, header, file_size):
    """Classify an attachment using metadata and at most a caller-read 2 KiB header.

    The caller is responsible for permission checking and bounded I/O. This
    function never opens files, parses archives, or reads beyond ``header``.
    """
    name = name or ""
    extension = PurePosixPath(name.replace("\\", "/")).suffix.lower()
    extension_family = _EXTENSION_FAMILIES.get(extension)
    mime = _normalized_mime(mimetype)
    mime_family = _MIME_FAMILIES.get(mime)
    header = bytes(header or b"")[:2048]

    if header.startswith(_OLE_SIGNATURE):
        signature_family = "legacy"
    elif header.startswith(_ZIP_SIGNATURE):
        # A ZIP signature does not prove OOXML. It is still treated as an
        # Office candidate at the provider boundary and remains unsupported.
        signature_family = "ooxml-container"
    else:
        signature_family = None

    candidate = bool(extension_family or mime_family or signature_family)
    if not candidate:
        return AttachmentIdentity(False, False, "not_office")

    if not header or not file_size:
        return AttachmentIdentity(True, True, "empty_or_unreadable")

    declared_families = {family for family in (extension_family, mime_family) if family}
    if len(declared_families) > 1:
        return AttachmentIdentity(True, True, "declaration_conflict")

    declared_family = next(iter(declared_families), None)
    if declared_family and mime and not mime_family and mime not in _GENERIC_BINARY_MIMES:
        return AttachmentIdentity(True, True, "mime_conflict")

    legacy_extension = extension in {
        ".xls", ".xlt", ".xla", ".doc", ".dot", ".ppt", ".pot", ".pps"
    }
    expected_signature = (
        "legacy"
        if declared_family and (legacy_extension or mime in _LEGACY_MIMES)
        else "ooxml-container" if declared_family else None
    )
    if declared_family and expected_signature and signature_family != expected_signature:
        return AttachmentIdentity(True, True, "signature_mismatch")
    if signature_family == "legacy" and declared_family and extension_family and extension not in {
        ".xls", ".xlt", ".xla", ".doc", ".dot", ".ppt", ".pot", ".pps"
    }:
        return AttachmentIdentity(True, True, "signature_mismatch")
    if signature_family == "ooxml-container" and declared_family and extension in {
        ".xls", ".xlt", ".xla", ".doc", ".dot", ".ppt", ".pot", ".pps"
    }:
        return AttachmentIdentity(True, True, "signature_mismatch")
    if declared_family and not signature_family:
        return AttachmentIdentity(True, True, "signature_mismatch")

    return AttachmentIdentity(True, False, "office_candidate")
