"""Create synthetic Office fixtures for TV-OFFICE-ENGINE-M1.

All fixture content is synthetic and contains no business data.
"""
from __future__ import annotations

import base64
import random
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/"
    "lS8AAAAASUVORK5CYII="
)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def make_noise_png(path: Path, width: int = 1800, height: int = 1800) -> None:
    """Create a valid RGB PNG with deterministic high-entropy pixels (~9.7 MB)."""
    rng = random.Random(20261019)
    raw = b"".join(b"\x00" + rng.randbytes(width * 3) for _ in range(height))
    compressed = zlib.compress(raw, level=1)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def make_xls(path: Path) -> None:
    import xlwt

    book = xlwt.Workbook()
    sheet = book.add_sheet("Legacy Orders")
    heading = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour yellow")
    money = xlwt.easyxf(num_format_str="€#,##0.00")
    sheet.write_merge(0, 0, 0, 2, "Legacy invoice template", heading)
    sheet.write(1, 0, "Item", heading)
    sheet.write(1, 1, "Quantity", heading)
    sheet.write(1, 2, "Amount", heading)
    for row in range(2, 12):
        sheet.write(row, 0, f"Product-{row - 1}")
        sheet.write(row, 1, row - 1)
        sheet.write(row, 2, (row - 1) * 12.5, money)
    sheet.write(12, 1, "Total", heading)
    sheet.write(12, 2, xlwt.Formula("SUM(C3:C12)"), money)
    sheet.col(0).width = 5000
    sheet.col(2).width = 4000
    sheet.portrait = 0
    sheet.paper_size_code = 9
    book.save(str(path))


def make_xlsx(path: Path, image_path: Path | None = None, formula_cache: bool = True) -> None:
    from openpyxl import Workbook
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.workbook.external_link.external import ExternalBook, ExternalLink, ExternalSheetNames
    from openpyxl.packaging.relationship import Relationship

    book = Workbook()
    sheet = book.active
    sheet.title = "Modern Orders"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "Synthetic modern invoice"
    sheet["A1"].font = Font(bold=True)
    sheet["A1"].fill = PatternFill("solid", fgColor="FFF2CC")
    for row in range(2, 12):
        sheet.cell(row, 1, f"Product-{row - 1}")
        sheet.cell(row, 2, row - 1)
        sheet.cell(row, 3, (row - 1) * 12.5)
        sheet.cell(row, 3).number_format = '€#,##0.00'
    sheet["B12"] = "Total"
    sheet["C12"] = "=SUM(C2:C11)"
    sheet.conditional_formatting.add("C2:C11", CellIsRule(operator="greaterThan", formula=["50"], fill=PatternFill("solid", fgColor="FFC7CE")))
    sheet["D2"] = "Status"
    validation = DataValidation(type="list", formula1='"Draft,Confirmed"')
    sheet.add_data_validation(validation)
    validation.add("D3:D12")
    book.create_named_range("OrderTotal", sheet, "$C$12")
    sheet["F2"] = "='[source.xlsx]Source'!A1"
    external = ExternalLink(externalBook=ExternalBook(sheetNames=ExternalSheetNames(sheetName=["Source"]), id="rId1"))
    external.file_link = Relationship(
        Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/externalLinkPath",
        Target="../source.xlsx",
        TargetMode="External",
        Id="rId1",
    )
    book._external_links.append(external)
    sheet.freeze_panes = "A2"
    if image_path and image_path.exists():
        from openpyxl.drawing.image import Image

        image = Image(str(image_path))
        image.width = 24
        image.height = 24
        sheet.add_image(image, "E2")
    book.save(path)
    if formula_cache:
        inject_formula_cache(path, "C12", "687.5")


def inject_formula_cache(path: Path, cell_ref: str, value: str) -> None:
    """Insert a synthetic cached value in the first worksheet formula cell."""
    from xml.etree import ElementTree as ET

    tmp = path.with_suffix(".cachetmp.xlsx")
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path, "r") as source, ZipFile(tmp, "w", ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(data)
                cell = root.find(f".//m:c[@r='{cell_ref}']", ns)
                if cell is None:
                    raise RuntimeError(f"Fixture formula cell {cell_ref} not found")
                value_node = cell.find("m:v", ns)
                if value_node is None:
                    value_node = ET.SubElement(cell, f"{{{ns['m']}}}v")
                value_node.text = value
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            target.writestr(item, data)
    tmp.replace(path)


def _minimal_docx_parts(include_image: bool = True) -> dict[str, bytes]:
    import html

    drawing = ""
    image_rel = ""
    image_type = ""
    if include_image:
        image_rel = '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/pixel.png"/>'
        image_type = '<Default Extension="png" ContentType="image/png"/>'
        drawing = '''<w:p><w:r><w:drawing><wp:inline><wp:extent cx="9525" cy="9525"/><wp:docPr id="1" name="Synthetic image"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="pixel.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rId2"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="9525" cy="9525"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
    document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>
<w:p><w:r><w:t>Synthetic Chinese CMR 文档 — header/footer and VML text box test</w:t></w:r></w:p>
<w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/></w:tblGrid><w:tr><w:tc><w:p><w:r><w:t>Customer</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Example Customer</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:r><w:pict><v:shape id="TextBox1" style="width:120pt;height:40pt" stroked="f"><v:textbox><w:txbxContent><w:p><w:r><w:t>Textbox instruction: copy delivery address line by line</w:t></w:r></w:p></w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>
{drawing}<w:sectPr><w:headerReference w:type="default" r:id="rId3"/><w:footerReference w:type="default" r:id="rId4"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>
</w:body></w:document>'''
    rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>{image_rel}<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>'''
    content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>{image_type}<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>'''
    return {
        "[Content_Types].xml": content_types.encode(),
        "_rels/.rels": b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": document.encode(),
        "word/_rels/document.xml.rels": rels.encode(),
        "word/styles.xml": b'<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults/></w:styles>',
        "word/header1.xml": b'<?xml version="1.0" encoding="UTF-8"?><w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Header CMR</w:t></w:r></w:p></w:hdr>',
        "word/footer1.xml": b'<?xml version="1.0" encoding="UTF-8"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Page footer</w:t></w:r></w:p></w:ftr>',
    }


def make_docx(path: Path, image_path: Path | None = None, large: bool = False) -> None:
    parts = _minimal_docx_parts(include_image=image_path is not None)
    compression = ZIP_STORED if large else ZIP_DEFLATED
    with ZipFile(path, "w", compression) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
        if image_path is not None:
            archive.write(image_path, "word/media/pixel.png", compress_type=ZIP_STORED)
        if large and image_path is not None:
            # A valid, highly entropic image makes the DOCX package ~10 MB without
            # adding macros or executable content. The document references it at 1 px.
            archive.write(image_path, "word/media/large-photo.png", compress_type=ZIP_STORED)


def make_malformed_samples(root: Path) -> dict[str, Path]:
    samples = root / "malformed"
    samples.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    empty = samples / "empty.xlsx"
    empty.write_bytes(b"")
    result["empty"] = empty
    masquerade = samples / "script-disguised.xlsx"
    masquerade.write_text("#!/bin/sh\nprintf 'not an Office document'\n", encoding="utf-8")
    result["masquerade"] = masquerade
    truncated = samples / "truncated.xlsx"
    truncated.write_bytes(b"PK\x03\x04" + b"\x00" * 48)
    result["truncated_zip"] = truncated
    invalid_ooxml = samples / "invalid-ooxml.xlsx"
    with ZipFile(invalid_ooxml, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types>")
        archive.writestr("xl/workbook.xml", "<workbook><sheets></workbook>")
    result["invalid_ooxml"] = invalid_ooxml
    bomb = samples / "bounded-high-ratio.zip"
    with ZipFile(bomb, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("large.txt", b"A" * (16 * 1024 * 1024))
    result["high_ratio_zip"] = bomb
    return result
