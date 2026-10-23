#!/usr/bin/env python3
"""Run the bounded, standalone M1 Office engine technical probes.

This runner uses synthetic fixtures only. It does not import Odoo or access a DB.
Run with: venv/bin/python scripts/tv_m1/run_tv_m1.py
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import psutil

from fixture_factory import make_docx, make_malformed_samples, make_noise_png, make_xls, make_xlsx


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / "docs/verification/evidence/TV_Office_Engine_M1"
TIMEOUT = 90
RSS_LIMIT = 1024 * 1024 * 1024
EVIDENCE_ROOT: Path | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def soffice_path() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def process_rows() -> list[dict[str, Any]]:
    rows = []
    try:
        iterator = psutil.process_iter(["pid", "ppid", "name", "cmdline", "status", "create_time"])
        for process in iterator:
            try:
                name = (process.info.get("name") or "").lower()
                cmdline = " ".join(process.info.get("cmdline") or [])
                if "soffice" in name or "soffice" in cmdline.lower():
                    rows.append({
                        "pid": process.info.get("pid"),
                        "ppid": process.info.get("ppid"),
                        "name": process.info.get("name"),
                        "status": process.info.get("status"),
                        "cmdline": cmdline[:1000],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (PermissionError, psutil.AccessDenied) as exc:
        return [{"enumeration_status": "DENIED_BY_RUNTIME_SANDBOX", "error": str(exc)}]
    return rows


def run_process(
    args: list[str],
    *,
    timeout: int = TIMEOUT,
    rss_limit: int = RSS_LIMIT,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run a child with timeout and sampled process-tree RSS kill boundary."""
    start = time.monotonic()
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            args,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd=str(cwd) if cwd else None,
            env=env,
            start_new_session=True,
        )
        root = psutil.Process(process.pid)
        try:
            peak_rss = root.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            peak_rss = 0
        reason = None
        while process.poll() is None:
            try:
                # macOS sandbox denies global PID enumeration, which psutil.children()
                # needs. Sample only the PID launched by this harness and report that
                # process-tree RSS is not observable in this environment.
                rss = root.memory_info().rss if root.is_running() else 0
                peak_rss = max(peak_rss, rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            elapsed = time.monotonic() - start
            if elapsed > timeout:
                reason = "timeout"
            elif peak_rss > rss_limit:
                reason = "rss_limit"
            if reason:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                break
            time.sleep(0.02)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode("utf-8", "replace")
        stderr = stderr_file.read().decode("utf-8", "replace")
    return {
        "args": args,
        "pid": process.pid,
        "returncode": process.returncode,
        "elapsed_seconds": round(time.monotonic() - start, 4),
        "peak_rss_bytes": peak_rss,
        "peak_rss_scope": "launched PID only; descendants cannot be enumerated under this runtime sandbox",
        "termination_reason": reason,
        "stdout": stdout,
        "stderr": stderr,
    }


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def save_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if not fieldnames:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_log(out: Path, label: str, result: dict[str, Any]) -> None:
    (out / "logs" / f"{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lo_convert(soffice: str, source: Path, target_format: str, outdir: Path, profile: Path, label: str) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    profile.mkdir(parents=True, exist_ok=True)
    cache_dir = profile / "xdg-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    child_env = os.environ.copy()
    child_env["XDG_CACHE_HOME"] = str(cache_dir)
    args = [
        soffice,
        "--headless",
        f"-env:UserInstallation={profile.as_uri()}",
        "--convert-to",
        target_format,
        "--outdir",
        str(outdir),
        str(source),
    ]
    result = run_process(args, timeout=120, rss_limit=RSS_LIMIT, env=child_env)
    result["output_files"] = [str(path) for path in outdir.glob(f"*.{target_format.split(':')[0]}")]
    write_log(EVIDENCE_ROOT or outdir.parent, label, result)
    return result


def preserve_pdf_and_render(pdf: Path, artifacts: Path, label: str) -> dict[str, Any]:
    artifacts.mkdir(parents=True, exist_ok=True)
    saved_pdf = artifacts / f"{label}.pdf"
    shutil.copy2(pdf, saved_pdf)
    renderer = shutil.which("pdftoppm")
    if not renderer:
        return {"pdf": str(saved_pdf), "render_status": "NOT_RUN_RENDERER_MISSING"}
    prefix = artifacts / f"{label}-page"
    rendered = run_process([renderer, "-png", "-f", "1", "-l", "1", "-r", "100", str(saved_pdf), str(prefix)], timeout=30, rss_limit=512 * 1024 * 1024)
    images = sorted(artifacts.glob(f"{label}-page-*.png"))
    return {"pdf": str(saved_pdf), "render_status": "OK" if images and rendered["returncode"] == 0 else "FAILED", "images": [str(path) for path in images], "renderer_returncode": rendered["returncode"], "renderer_stderr": rendered["stderr"][:400]}


def compare_images(before: Path, after: Path) -> dict[str, Any]:
    from PIL import Image, ImageChops

    left = Image.open(before).convert("RGB")
    right = Image.open(after).convert("RGB")
    result: dict[str, Any] = {"before_size": left.size, "after_size": right.size}
    if left.size != right.size:
        result.update({"status": "DIMENSION_MISMATCH", "different_pixel_ratio": 1.0})
        return result
    diff = ImageChops.difference(left, right).convert("L")
    histogram = diff.histogram()
    changed = sum(histogram[1:])
    total = left.width * left.height
    result.update({"status": "COMPARED", "different_pixel_ratio": changed / total if total else 0.0, "different_pixels": changed, "total_pixels": total})
    return result


def xlsx_structure(path: Path) -> dict[str, Any]:
    from openpyxl import load_workbook

    book = load_workbook(path, data_only=False, keep_links=True)
    sheet = book[book.sheetnames[0]]
    formulas = {}
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                formulas[cell.coordinate] = cell.value
    names = getattr(book.defined_names, "keys", None)
    defined_names = sorted(names()) if callable(names) else sorted(item.name for item in getattr(book.defined_names, "definedName", []))
    return {
        "sheetnames": book.sheetnames,
        "formula_cells": formulas,
        "merged_ranges": sorted(str(item) for item in sheet.merged_cells.ranges),
        "conditional_formatting_count": len(sheet.conditional_formatting),
        "data_validation_count": len(sheet.data_validations.dataValidation),
        "image_count": len(sheet._images),
        "defined_names": defined_names,
        "external_link_count": len(book._external_links),
        "styles": {cell.coordinate: {"style_id": cell.style_id, "number_format": cell.number_format} for row in sheet.iter_rows() for cell in row if cell.has_style},
    }


def formula_caches(path: Path, cell_ref: str) -> dict[str, Any]:
    from openpyxl import load_workbook

    formula_book = load_workbook(path, data_only=False, keep_links=True)
    cache_book = load_workbook(path, data_only=True, keep_links=True)
    formula_sheet = formula_book[formula_book.sheetnames[0]]
    cache_sheet = cache_book[cache_book.sheetnames[0]]
    return {"formula": formula_sheet[cell_ref].value, "cached_value": cache_sheet[cell_ref].value}


def xlrd_style_signature(book: Any, sheet: Any, coordinate: str) -> dict[str, Any]:
    letters = "".join(char for char in coordinate if char.isalpha()).upper()
    digits = "".join(char for char in coordinate if char.isdigit())
    column = 0
    for char in letters:
        column = column * 26 + ord(char) - ord("A") + 1
    row, column = int(digits) - 1, column - 1
    cell = sheet.cell(row, column)
    xf = book.xf_list[cell.xf_index]
    font = book.font_list[xf.font_index]
    fmt = book.format_map.get(xf.format_key)
    return {
        "xf_index": cell.xf_index,
        "font_name": font.name,
        "bold": bool(font.bold),
        "italic": bool(font.italic),
        "number_format": fmt.format_str if fmt else None,
        "fill_pattern": xf.background.fill_pattern,
        "fill_colour_index": xf.background.pattern_colour_index,
        "horizontal_alignment": xf.alignment.hor_align,
        "vertical_alignment": xf.alignment.vert_align,
    }


def xlsx_style_signature(path: Path, coordinate: str) -> dict[str, Any]:
    from openpyxl import load_workbook

    book = load_workbook(path, data_only=False, keep_links=True)
    cell = book.active[coordinate]
    colour = cell.fill.fgColor
    return {
        "style_id": cell.style_id,
        "font_name": cell.font.name,
        "bold": bool(cell.font.bold),
        "italic": bool(cell.font.italic),
        "number_format": cell.number_format,
        "fill_pattern": cell.fill.fill_type,
        "fill_colour_index": colour.indexed if colour.type == "indexed" else colour.rgb,
        "horizontal_alignment": cell.alignment.horizontal,
        "vertical_alignment": cell.alignment.vertical,
    }


def normalized_number_format(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\\€", "€")
    return value


def style_comparison_rows(case: str, coordinate: str, before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key in ["font_name", "bold", "italic", "number_format", "fill_pattern", "fill_colour_index", "horizontal_alignment", "vertical_alignment"]:
        left, right = before.get(key), after.get(key)
        if key == "number_format":
            left, right = normalized_number_format(left), normalized_number_format(right)
        rows.append({"case": case, "cell": coordinate, "attribute": key, "before": left, "after": right, "status": "PRESERVED" if left == right else "CHANGED"})
    return rows


def inspect_docx(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        document = ET.fromstring(package.read("word/document.xml"))
        text_nodes = [node.text or "" for node in document.iter() if node.tag.endswith("}t")]
        return {
            "entries": len(names),
            "paragraphs": len([node for node in document.iter() if node.tag.endswith("}p")]),
            "tables": len([node for node in document.iter() if node.tag.endswith("}tbl")]),
            "vml_shapes": len([node for node in document.iter() if node.tag.endswith("}shape")]),
            "drawings": len([node for node in document.iter() if node.tag.endswith("}drawing")]),
            "document_text": "".join(text_nodes),
            "header_present": "word/header1.xml" in names,
            "footer_present": "word/footer1.xml" in names,
            "media": sorted(name for name in names if name.startswith("word/media/")),
        }


def child_python(code: str, *args: str) -> list[str]:
    return [sys.executable, "-c", code, *args]


def main() -> int:
    global EVIDENCE_ROOT
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUT
    output.mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(exist_ok=True)
    artifacts = output / "artifacts"
    artifacts.mkdir(exist_ok=True)
    EVIDENCE_ROOT = output
    env: dict[str, Any] = {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "memory_total_bytes": psutil.virtual_memory().total,
        "packages": {name: package_version(name) for name in ["openpyxl", "python-docx", "xlrd", "xlwt", "psutil", "Pillow"]},
        "soffice_path": soffice_path(),
        "baseline_soffice_processes": process_rows(),
    }
    if env["soffice_path"]:
        version_result = run_process([env["soffice_path"], "--version"], timeout=40, rss_limit=RSS_LIMIT)
        env["soffice_version"] = version_result["stdout"].strip()
        env["soffice_version_stderr"] = version_result["stderr"].strip()
        env["soffice_version_result"] = {k: version_result[k] for k in ["returncode", "elapsed_seconds", "peak_rss_bytes", "termination_reason"]}
    for command, args in [("fc-list", ["fc-list", ":", "family"]), ("pdftoppm", ["pdftoppm", "-v"])]:
        path = shutil.which(command)
        env[command] = {"path": path}
        if path:
            result = run_process(args, timeout=15, rss_limit=256 * 1024 * 1024)
            if command == "fc-list":
                wanted = [line for line in result["stdout"].splitlines() if any(term in line.lower() for term in ["cjk", "heiti", "songti", "simhei", "simsun", "noto sans sc", "source han"])]
                env[command].update({"matching_families": sorted(set(wanted)), "stderr": result["stderr"][:2000], "returncode": result["returncode"]})
            else:
                env[command].update({"stdout": result["stdout"][:500], "stderr": result["stderr"][:500], "returncode": result["returncode"]})
    # Record only non-secret Odoo runtime budgets, never the full configuration.
    config = REPO / "odoo.conf"
    safe_keys = {"workers", "limit_time_cpu", "limit_time_real", "limit_memory_soft", "limit_memory_hard"}
    selected_config = {}
    if config.exists():
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
                continue
            key, value = (part.strip() for part in stripped.split("=", 1))
            if key in safe_keys:
                selected_config[key] = value
    env["odoo_runtime_budget_keys"] = selected_config or "NOT_FOUND_OR_NOT_CONFIGURED"
    (output / "TV_Office_Engine_M1_Environment.txt").write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not env["soffice_path"]:
        print("ERROR: soffice unavailable; only non-LO probes can run", file=sys.stderr)
    with tempfile.TemporaryDirectory(prefix="tv-office-m1-") as temp_name:
        work = Path(temp_name)
        image = work / "pixel.png"
        make_noise_png(image, 8, 8)
        xls = work / "legacy.xls"
        xlsx = work / "modern.xlsx"
        docx = work / "modern.docx"
        make_xls(xls)
        make_xlsx(xlsx, image)
        make_docx(docx, image)
        large_xlsx = work / "large-50000-rows.xlsx"
        from openpyxl import Workbook

        large_book = Workbook(write_only=True)
        large_sheet = large_book.create_sheet("Rows")
        for row in range(1, 50001):
            large_sheet.append([row, f"synthetic-row-{row}", row * 1.25])
        large_book.save(large_xlsx)
        large_png = work / "large-image.png"
        make_noise_png(large_png)
        large_docx = work / "large-10mb.docx"
        make_docx(large_docx, large_png)
        malformed = make_malformed_samples(work)

        manifest = []
        for sample_id, path, features in [
            ("XLS-SYN-01", xls, "formula; merged; styles; print setup"),
            ("XLSX-SYN-01", xlsx, "formula with injected cached value; merged; conditional formatting; image; external link; named range; validation"),
            ("DOCX-SYN-01", docx, "table; header/footer; VML textbox; DrawingML image; Chinese text"),
            ("XLSX-LARGE-50K", large_xlsx, "50000 rows; 3 columns"),
            ("DOCX-LARGE-10MB", large_docx, "synthetic document with high-entropy embedded PNG"),
        ]:
            manifest.append({"sample_id": sample_id, "format": path.suffix, "bytes": path.stat().st_size, "sha256": sha256(path), "source": "synthetic; temporary only", "features": features})
        for case_name, path in malformed.items():
            manifest.append({"sample_id": f"MAL-{case_name}", "format": path.suffix, "bytes": path.stat().st_size, "sha256": sha256(path), "source": "synthetic; temporary only", "features": case_name})
        save_csv(output / "TV_Office_Engine_M1_Sample_Manifest.csv", manifest)

        legacy_rows: list[dict[str, Any]] = []
        style_rows: list[dict[str, Any]] = []
        visual_rows: list[dict[str, Any]] = []
        direct_code = "import openpyxl,sys; openpyxl.load_workbook(sys.argv[1]); print('opened')"
        direct = run_process(child_python(direct_code, str(xls)), timeout=20, rss_limit=RSS_LIMIT)
        write_log(output, "legacy_openpyxl_direct_xls", direct)
        legacy_rows.append({"case": "openpyxl-direct-xls", "status": "OPENED" if direct["returncode"] == 0 else "FAILED_AS_EXPECTED_CANDIDATE", "returncode": direct["returncode"], "elapsed_seconds": direct["elapsed_seconds"], "error": (direct["stderr"] or direct["stdout"])[:500]})
        import xlrd

        book = xlrd.open_workbook(str(xls), formatting_info=True)
        sheet = book.sheet_by_index(0)
        legacy_rows.append({"case": "xlrd-read-xls", "status": "OPENED", "returncode": 0, "elapsed_seconds": None, "sheets": book.sheet_names(), "rows": sheet.nrows, "cols": sheet.ncols, "merged_regions": sheet.merged_cells, "xf_count": len(book.xf_list), "formula_cache_cell_C13": sheet.cell_value(12, 2)})
        if env["soffice_path"]:
            legacy_xlsx_dir = work / "legacy-converted"
            converted = lo_convert(env["soffice_path"], xls, "xlsx", legacy_xlsx_dir, work / "profiles/xls-to-xlsx", "lo_xls_to_xlsx")
            converted_xlsx = legacy_xlsx_dir / "legacy.xlsx"
            legacy_rows.append({"case": "lo-xls-to-xlsx", "status": "OK" if converted["returncode"] == 0 and converted_xlsx.exists() else "FAILED", "returncode": converted["returncode"], "elapsed_seconds": converted["elapsed_seconds"], "peak_rss_bytes": converted["peak_rss_bytes"], "stderr": converted["stderr"][:700]})
            if converted_xlsx.exists():
                before = {"merged_ranges": xlrd.open_workbook(str(xls), formatting_info=True).sheet_by_index(0).merged_cells, "source_xf_count": len(xlrd.open_workbook(str(xls), formatting_info=True).xf_list)}
                after = xlsx_structure(converted_xlsx)
                before_formula = xlrd.open_workbook(str(xls), formatting_info=True).sheet_by_index(0).cell_value(12, 2)
                legacy_rows.append({"case": "lo-xls-to-xlsx-structure", "source": before, "converted": after, "source_formula_cached_result": before_formula})
                style_rows.append({"case": "xls-to-xlsx", "attribute": "merged_region_count", "before": len(before["merged_ranges"]), "after": len(after["merged_ranges"]), "status": "PRESERVED" if len(before["merged_ranges"]) == len(after["merged_ranges"]) else "CHANGED"})
                source_for_style = xlrd.open_workbook(str(xls), formatting_info=True)
                source_sheet = source_for_style.sheet_by_index(0)
                for coordinate in ["A1", "A2", "C3", "C13"]:
                    style_rows.extend(style_comparison_rows("xls-to-xlsx", coordinate, xlrd_style_signature(source_for_style, source_sheet, coordinate), xlsx_style_signature(converted_xlsx, coordinate)))
                style_rows.append({"case": "xls-to-xlsx", "attribute": "source_XF_records_vs_target_cell_style_ids", "before": before["source_xf_count"], "after": len({v["style_id"] for v in after["styles"].values()}), "status": "NON_EQUIVALENT_COUNTS_DIAGNOSTIC_ONLY"})
                back_dir = work / "legacy-roundtrip-xls"
                back = lo_convert(env["soffice_path"], converted_xlsx, "xls", back_dir, work / "profiles/xlsx-to-xls", "lo_xlsx_to_xls")
                back_xls = back_dir / "legacy.xls"
                if back_xls.exists():
                    rb = xlrd.open_workbook(str(back_xls), formatting_info=True)
                    legacy_rows.append({"case": "lo-xlsx-to-xls-roundtrip", "status": "OK", "returncode": back["returncode"], "elapsed_seconds": back["elapsed_seconds"], "merged_regions": rb.sheet_by_index(0).merged_cells, "xf_count": len(rb.xf_list), "formula_result": rb.sheet_by_index(0).cell_value(12, 2)})
                    style_rows.append({"case": "xls-roundtrip", "attribute": "merged_region_count", "before": len(sheet.merged_cells), "after": len(rb.sheet_by_index(0).merged_cells), "status": "PRESERVED" if sheet.merged_cells == rb.sheet_by_index(0).merged_cells else "CHANGED"})
                    style_rows.append({"case": "xls-roundtrip", "attribute": "XF_record_count", "before": len(book.xf_list), "after": len(rb.xf_list), "status": "COUNT_CHANGED_REQUIRES_PROPERTY_COMPARISON"})
                    for coordinate in ["A1", "A2", "C3", "C13"]:
                        style_rows.extend(style_comparison_rows("xls-roundtrip", coordinate, xlrd_style_signature(book, sheet, coordinate), xlrd_style_signature(rb, rb.sheet_by_index(0), coordinate)))
                    src_pdf_dir = work / "source-xls-pdf"
                    back_pdf_dir = work / "roundtrip-xls-pdf"
                    src_pdf = lo_convert(env["soffice_path"], xls, "pdf", src_pdf_dir, work / "profiles/source-xls-pdf", "lo_source_xls_pdf")
                    back_pdf = lo_convert(env["soffice_path"], back_xls, "pdf", back_pdf_dir, work / "profiles/roundtrip-xls-pdf", "lo_roundtrip_xls_pdf")
                    src_pdf_path = next(src_pdf_dir.glob("*.pdf"), None)
                    back_pdf_path = next(back_pdf_dir.glob("*.pdf"), None)
                    if src_pdf_path and back_pdf_path:
                        before_render = preserve_pdf_and_render(src_pdf_path, artifacts, "xls-before-roundtrip")
                        after_render = preserve_pdf_and_render(back_pdf_path, artifacts, "xls-after-roundtrip")
                        if before_render.get("images") and after_render.get("images"):
                            visual_rows.append({"case": "xls-roundtrip", **compare_images(Path(before_render["images"][0]), Path(after_render["images"][0]))})
                else:
                    legacy_rows.append({"case": "lo-xlsx-to-xls-roundtrip", "status": "FAILED", "returncode": back["returncode"], "elapsed_seconds": back["elapsed_seconds"], "stderr": back["stderr"][:700]})
        save_csv(output / "TV_Office_Engine_M1_Conversion_Matrix.csv", legacy_rows)

        formula_before = formula_caches(xlsx, "C12")
        from openpyxl import load_workbook

        modified = work / "modern-modified.xlsx"
        modern_book = load_workbook(xlsx, data_only=False, keep_links=True)
        modern_book["Modern Orders"]["A2"] = "Updated Product"
        modern_book.save(modified)
        formula_after = formula_caches(modified, "C12")
        structure_before = xlsx_structure(xlsx)
        structure_after = xlsx_structure(modified)
        formula_check = {
            "sample_id": "XLSX-SYN-01",
            "cell": "C12",
            "before_save": formula_before,
            "after_openpyxl_save": formula_after,
            "formula_text_preserved": formula_before["formula"] == formula_after["formula"],
            "cache_preserved": formula_before["cached_value"] == formula_after["cached_value"],
            "structure_before": structure_before,
            "structure_after": structure_after,
        }
        if env["soffice_path"]:
            recalc_dir = work / "recalculated"
            recalc = lo_convert(env["soffice_path"], modified, "xlsx", recalc_dir, work / "profiles/recalc", "lo_xlsx_recalc")
            recalc_file = recalc_dir / "modern-modified.xlsx"
            formula_check["libreoffice_recalc"] = {
                "returncode": recalc["returncode"],
                "elapsed_seconds": recalc["elapsed_seconds"],
                "peak_rss_bytes": recalc["peak_rss_bytes"],
                "output_exists": recalc_file.exists(),
                "formula_cache_after": formula_caches(recalc_file, "C12") if recalc_file.exists() else None,
                "structure_after": xlsx_structure(recalc_file) if recalc_file.exists() else None,
                "stderr": recalc["stderr"][:1000],
            }
        else:
            formula_check["libreoffice_recalc"] = "NOT RUN: soffice unavailable"
        save_json(output / "TV_Office_Engine_M1_Formula_Check.json", formula_check)
        structure_rows = []
        for key in ["sheetnames", "formula_cells", "merged_ranges", "conditional_formatting_count", "data_validation_count", "image_count", "defined_names", "external_link_count"]:
            structure_rows.append({"object_type": key, "before": json.dumps(structure_before.get(key), ensure_ascii=False, sort_keys=True), "after": json.dumps(structure_after.get(key), ensure_ascii=False, sort_keys=True), "preserved": structure_before.get(key) == structure_after.get(key)})
        save_csv(output / "TV_Office_Engine_M1_Structure_Diff.csv", structure_rows)

        docx_before = inspect_docx(docx)
        word_results: list[dict[str, Any]] = []
        if package_version("python-docx") == "NOT_INSTALLED":
            word_results.append({"case": "python-docx-read-write", "status": "INCONCLUSIVE", "reason": "python-docx is not installed in the specified venv; no dependency installation was performed"})
        else:
            code = "from docx import Document; import sys; d=Document(sys.argv[1]); d.paragraphs[0].text += ' edited'; d.save(sys.argv[2])"
            edited = work / "python-docx-edited.docx"
            result = run_process(child_python(code, str(docx), str(edited)), timeout=30)
            word_results.append({"case": "python-docx-read-write", "status": "OK" if result["returncode"] == 0 else "FAILED", "returncode": result["returncode"], "elapsed_seconds": result["elapsed_seconds"], "peak_rss_bytes": result["peak_rss_bytes"], "stderr": result["stderr"][:800]})
            if edited.exists():
                word_results.append({"case": "python-docx-structure", "before": docx_before, "after": inspect_docx(edited)})
        word_results.append({"case": "handcrafted-docx-structure-baseline", "status": "PARSED", "structure": docx_before})
        if env["soffice_path"]:
            old_doc_dir = work / "legacy-doc"
            doc_result = lo_convert(env["soffice_path"], docx, "doc", old_doc_dir, work / "profiles/docx-to-doc", "lo_docx_to_doc")
            old_doc = old_doc_dir / "modern.doc"
            word_results.append({"case": "lo-docx-to-doc", "status": "OK" if old_doc.exists() else "FAILED", "returncode": doc_result["returncode"], "elapsed_seconds": doc_result["elapsed_seconds"], "peak_rss_bytes": doc_result["peak_rss_bytes"], "stderr": doc_result["stderr"][:800]})
            returned_docx = None
            if old_doc.exists():
                return_dir = work / "legacy-docx-return"
                return_result = lo_convert(env["soffice_path"], old_doc, "docx", return_dir, work / "profiles/doc-to-docx", "lo_doc_to_docx")
                returned_docx = return_dir / "modern.docx"
                word_results.append({"case": "lo-doc-to-docx-roundtrip", "status": "OK" if returned_docx.exists() else "FAILED", "returncode": return_result["returncode"], "elapsed_seconds": return_result["elapsed_seconds"], "structure": inspect_docx(returned_docx) if returned_docx.exists() else None, "stderr": return_result["stderr"][:800]})
            src_pdf_dir = work / "docx-pdf"
            pdf_result = lo_convert(env["soffice_path"], docx, "pdf", src_pdf_dir, work / "profiles/docx-pdf", "lo_docx_to_pdf")
            src_pdf = next(src_pdf_dir.glob("*.pdf"), None)
            word_results.append({"case": "lo-docx-to-pdf", "status": "OK" if src_pdf else "FAILED", "returncode": pdf_result["returncode"], "elapsed_seconds": pdf_result["elapsed_seconds"], "stderr": pdf_result["stderr"][:800]})
            before_render = preserve_pdf_and_render(src_pdf, artifacts, "docx-before-oldformat") if src_pdf else None
            if returned_docx and returned_docx.exists():
                after_pdf_dir = work / "docx-roundtrip-pdf"
                after_pdf = lo_convert(env["soffice_path"], returned_docx, "pdf", after_pdf_dir, work / "profiles/docx-roundtrip-pdf", "lo_docx_roundtrip_to_pdf")
                after_pdf_path = next(after_pdf_dir.glob("*.pdf"), None)
                after_render = preserve_pdf_and_render(after_pdf_path, artifacts, "docx-after-oldformat") if after_pdf_path else None
                if before_render and after_render and before_render.get("images") and after_render.get("images"):
                    visual_rows.append({"case": "docx-to-doc-to-docx", **compare_images(Path(before_render["images"][0]), Path(after_render["images"][0]))})
                before_structure, after_structure = docx_before, inspect_docx(returned_docx)
                for metric in ["paragraphs", "tables", "vml_shapes", "drawings", "header_present", "footer_present"]:
                    style_rows.append({"case": "docx-to-doc-to-docx", "attribute": metric, "before": before_structure.get(metric), "after": after_structure.get(metric), "status": "PRESERVED" if before_structure.get(metric) == after_structure.get(metric) else "CHANGED"})
                style_rows.append({"case": "docx-to-doc-to-docx", "attribute": "textbox_instruction_text_present", "before": "Textbox instruction" in before_structure["document_text"], "after": "Textbox instruction" in after_structure["document_text"], "status": "PRESERVED_AS_TEXT" if "Textbox instruction" in after_structure["document_text"] else "LOST"})
                word_results.append({"case": "lo-docx-roundtrip-pdf", "status": "OK" if after_pdf_path else "FAILED", "returncode": after_pdf["returncode"], "elapsed_seconds": after_pdf["elapsed_seconds"], "stderr": after_pdf["stderr"][:500]})
        save_json(output / "TV_Office_Engine_M1_Word_Check.json", word_results)
        save_csv(output / "TV_Office_Engine_M1_Style_Diff.csv", style_rows)
        save_csv(output / "TV_Office_Engine_M1_Visual_Diff.csv", visual_rows)

        # Large-file performance: each trial is a fresh, bounded child process.
        perf_rows: list[dict[str, Any]] = []
        bench_xlsx = """import json,sys,time; from openpyxl import load_workbook; src,out=sys.argv[1:3]; t=time.perf_counter(); w=load_workbook(src,read_only=False,data_only=False); parsed=time.perf_counter(); s=w.active; s['D1']='tv'; w.save(out); saved=time.perf_counter(); w2=load_workbook(out,read_only=True,data_only=False); checked=w2.active.max_row; w2.close(); print(json.dumps({'parse_seconds':parsed-t,'save_seconds':saved-parsed,'readback_seconds':time.perf_counter()-saved,'rows':checked}))"""
        for trial in range(1, 11):
            target = work / f"large-50k-out-{trial}.xlsx"
            result = run_process(child_python(bench_xlsx, str(large_xlsx), str(target)), timeout=60, rss_limit=RSS_LIMIT)
            try:
                details = json.loads(result["stdout"].splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                details = {}
            perf_rows.append({"sample": "XLSX-LARGE-50K", "trial": trial, "file_bytes": large_xlsx.stat().st_size, "status": "OK" if result["returncode"] == 0 and target.exists() else "FAILED", "wall_seconds": result["elapsed_seconds"], "peak_rss_bytes": result["peak_rss_bytes"], **details, "returncode": result["returncode"], "termination_reason": result["termination_reason"], "stderr": result["stderr"][:300]})
        large_docx_before = inspect_docx(large_docx)
        docx_bench = """import json,sys,time,zipfile,xml.etree.ElementTree as ET; p=sys.argv[1]; t=time.perf_counter(); z=zipfile.ZipFile(p); b=z.read('word/document.xml'); d=ET.fromstring(b); parsed=time.perf_counter(); media=sum(i.file_size for i in z.infolist() if i.filename.startswith('word/media/')); print(json.dumps({'zip_xml_parse_seconds':parsed-t,'document_xml_bytes':len(b),'media_bytes':media,'entries':len(z.infolist())}))"""
        for trial in range(1, 4):
            result = run_process(child_python(docx_bench, str(large_docx)), timeout=60, rss_limit=RSS_LIMIT)
            try:
                details = json.loads(result["stdout"].splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                details = {}
            perf_rows.append({"sample": "DOCX-LARGE-10MB", "trial": trial, "file_bytes": large_docx.stat().st_size, "status": "OK" if result["returncode"] == 0 else "FAILED", "wall_seconds": result["elapsed_seconds"], "peak_rss_bytes": result["peak_rss_bytes"], **details, "returncode": result["returncode"], "termination_reason": result["termination_reason"], "stderr": result["stderr"][:300]})
        if env["soffice_path"]:
            pdf_large = work / "large-docx-pdf"
            result = lo_convert(env["soffice_path"], large_docx, "pdf", pdf_large, work / "profiles/large-docx-pdf", "lo_large_docx_to_pdf")
            pdf_path = next(pdf_large.glob("*.pdf"), None)
            perf_rows.append({"sample": "DOCX-LARGE-10MB", "trial": "LibreOffice PDF convert", "file_bytes": large_docx.stat().st_size, "status": "OK" if pdf_path else "FAILED", "wall_seconds": result["elapsed_seconds"], "peak_rss_bytes": result["peak_rss_bytes"], "returncode": result["returncode"], "termination_reason": result["termination_reason"], "stderr": result["stderr"][:500]})
            if pdf_path:
                preserve_pdf_and_render(pdf_path, artifacts, "large-docx-pdf")
        save_csv(output / "TV_Office_Engine_M1_Performance.csv", perf_rows)

        security_rows: list[dict[str, Any]] = []
        safe_zip_code = """import json,sys,zipfile
p=sys.argv[1]
max_total=1024*1024
total=0
z=zipfile.ZipFile(p)
result=[]
for item in z.infolist():
    if item.file_size > max_total-total:
        result.append({'name':item.filename,'declared':item.file_size,'status':'REJECTED_SIZE_LIMIT'})
        break
    with z.open(item) as stream:
        while True:
            block=stream.read(min(65536,max_total-total+1))
            if not block:
                break
            total += len(block)
            if total > max_total:
                result.append({'name':item.filename,'status':'REJECTED_READ_LIMIT'})
                break
    if result:
        break
print(json.dumps({'total_read_bytes':total,'entries':result}))"""
        for case, path in malformed.items():
            code = "import json,sys,openpyxl\ntry:\n openpyxl.load_workbook(sys.argv[1]); print(json.dumps({'result':'OPENED'}))\nexcept Exception as e:\n print(json.dumps({'result':'CAUGHT_EXCEPTION','exception_type':type(e).__module__+'.'+type(e).__name__,'message':str(e)[:500]}))"
            result = run_process(child_python(code, str(path)), timeout=20, rss_limit=512 * 1024 * 1024)
            try:
                parser_result = json.loads(result["stdout"].splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                parser_result = {}
            security_rows.append({"case": case, "tool": "openpyxl subprocess", "status": parser_result.get("result", "PROCESS_FAILURE"), "exception_type": parser_result.get("exception_type"), "message": parser_result.get("message"), "returncode": result["returncode"], "termination_reason": result["termination_reason"], "elapsed_seconds": result["elapsed_seconds"], "peak_rss_bytes": result["peak_rss_bytes"], "stderr": result["stderr"][:700]})
            if case == "high_ratio_zip":
                safe = run_process(child_python(safe_zip_code, str(path)), timeout=20, rss_limit=128 * 1024 * 1024)
                security_rows.append({"case": case, "tool": "bounded zip reader", "status": "OK" if safe["returncode"] == 0 and "REJECTED_SIZE_LIMIT" in safe["stdout"] else "FAILED", "returncode": safe["returncode"], "termination_reason": safe["termination_reason"], "elapsed_seconds": safe["elapsed_seconds"], "peak_rss_bytes": safe["peak_rss_bytes"], "stdout": safe["stdout"][:1000], "stderr": safe["stderr"][:300]})
            if env["soffice_path"]:
                lo_dir = work / f"malformed-lo-{case}"
                lo_result = lo_convert(env["soffice_path"], path, "pdf", lo_dir, work / f"profiles/malformed-{case}", f"lo_malformed_{case}")
                pdf_output = next(lo_dir.glob("*.pdf"), None)
                security_rows.append({"case": case, "tool": "LibreOffice isolated conversion", "status": "OUTPUT_CREATED_UNVERIFIED_MUST_REJECT_BY_PREVALIDATION" if pdf_output else ("REJECTED_OR_ERROR" if lo_result["returncode"] != 0 else "NO_OUTPUT"), "returncode": lo_result["returncode"], "termination_reason": lo_result["termination_reason"], "elapsed_seconds": lo_result["elapsed_seconds"], "peak_rss_bytes": lo_result["peak_rss_bytes"], "stderr": lo_result["stderr"][:500]})
        # Encrypted OOXML fixture generation is not assumed available; record explicitly.
        security_rows.append({"case": "encrypted-office", "tool": "fixture availability", "status": "NOT RUN", "reason": "No encryption fixture generator was configured; malformed/masquerade probes do not substitute for encryption testing"})
        save_csv(output / "TV_Office_Engine_M1_Security_Matrix.csv", security_rows)

        concurrency_rows: list[dict[str, Any]] = []
        baseline_pids = {int(item["pid"]) for item in env["baseline_soffice_processes"] if item.get("pid")}
        if env["soffice_path"]:
            for count in [1, 2, 4]:
                for trial in range(1, 4):
                    jobs = []
                    for worker in range(count):
                        outdir = work / f"parallel-{count}-{trial}-{worker}"
                        profile = work / f"profiles/parallel-{count}-{trial}-{worker}"
                        outdir.mkdir(parents=True, exist_ok=True)
                        profile.mkdir(parents=True, exist_ok=True)
                        cache_dir = profile / "xdg-cache"
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        args = [env["soffice_path"], "--headless", f"-env:UserInstallation={profile.as_uri()}", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)]
                        jobs.append((worker, args, outdir))
                    # Run each concurrency wave simultaneously; each process has an isolated profile/output.
                    procs = []
                    for worker, args, outdir in jobs:
                        outlog = work / f"parallel-out-{count}-{trial}-{worker}.log"
                        errlog = work / f"parallel-err-{count}-{trial}-{worker}.log"
                        outstream, errstream = outlog.open("wb"), errlog.open("wb")
                        child_env = os.environ.copy()
                        child_env["XDG_CACHE_HOME"] = str(cache_dir)
                        proc = subprocess.Popen(args, stdout=outstream, stderr=errstream, env=child_env, start_new_session=True)
                        procs.append((worker, proc, outdir, outstream, errstream, time.monotonic()))
                    peak_by_worker = {worker: 0 for worker, *_ in procs}
                    for worker, proc, *_ in procs:
                        try:
                            peak_by_worker[worker] = psutil.Process(proc.pid).memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    timed_out_workers: set[int] = set()
                    while any(proc.poll() is None for _, proc, *_ in procs):
                        now = time.monotonic()
                        for worker, proc, outdir, outstream, errstream, started in procs:
                            if proc.poll() is not None:
                                continue
                            try:
                                root_proc = psutil.Process(proc.pid)
                                rss = root_proc.memory_info().rss if root_proc.is_running() else 0
                                peak_by_worker[worker] = max(peak_by_worker[worker], rss)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                            if now - started > 120:
                                timed_out_workers.add(worker)
                                try:
                                    os.killpg(proc.pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                        time.sleep(0.02)
                    for worker, proc, outdir, outstream, errstream, started in procs:
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                        outstream.close()
                        errstream.close()
                        stderr_file = work / f"parallel-err-{count}-{trial}-{worker}.log"
                        stderr = stderr_file.read_text(errors="replace") if stderr_file.exists() else ""
                        generated = list(outdir.glob("*.pdf"))
                        profile = work / f"profiles/parallel-{count}-{trial}-{worker}"
                        lock_files = list(profile.rglob("*.lock"))
                        timed_out = worker in timed_out_workers
                        concurrency_rows.append({"parallelism": count, "trial": trial, "worker": worker, "status": "OK" if generated and not timed_out and proc.returncode == 0 else "FAILED", "elapsed_seconds": round(time.monotonic() - started, 4), "peak_rss_bytes": peak_by_worker[worker], "peak_rss_scope": "launcher PID only; child enumeration denied", "returncode": proc.returncode, "timed_out": timed_out, "profile_lock_files_remaining": json.dumps([str(item.relative_to(profile)) for item in lock_files]), "profile": str(profile), "output_count": len(generated), "stderr": stderr[:500]})
                    current = process_rows()
                    new_processes = [item for item in current if item.get("pid") and int(item["pid"]) not in baseline_pids]
                    snapshot_denied = any(item.get("enumeration_status") == "DENIED_BY_RUNTIME_SANDBOX" for item in current)
                    snapshot_status = "PROCESS_SNAPSHOT_DENIED_BY_RUNTIME_SANDBOX" if snapshot_denied else ("RESIDUAL_PROCESSES" if new_processes else "CLEAN")
                    concurrency_rows.append({"parallelism": count, "trial": trial, "worker": "post-wave-process-snapshot", "status": snapshot_status, "residual_soffice_processes": json.dumps(new_processes or current, ensure_ascii=False)})
                    time.sleep(0.5)
        else:
            concurrency_rows.append({"parallelism": "NOT RUN", "status": "INCONCLUSIVE", "reason": "LibreOffice unavailable"})
        save_csv(output / "TV_Office_Engine_M1_Concurrency.csv", concurrency_rows)

        # Store an explicit case-level status register, not an inferred overall pass.
        results = {
            "plan_baseline": "TV Office Engine M1 Plan 1.0.0 Frozen",
            "overall_status": "PARTIAL_NOT_CLOSED",
            "execution_date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "environment": {"platform": env["platform"], "python": env["python"], "soffice": env.get("soffice_version"), "docx_library": env["packages"]["python-docx"]},
            "cases": {
                "legacy_xls_direct_and_conversion": "EXECUTED_WITH_PER_CASE_RESULTS",
                "legacy_doc_conversion": "EXECUTED_WITH_PER_CASE_RESULTS",
                "modern_xlsx_formula_and_ooxml": "EXECUTED_WITH_PER_CASE_RESULTS",
                "openpyxl_formula_cache_behavior": "CONFIRMED_CACHE_CLEARED_ON_SAVE_FOR_SYNTHETIC_FIXTURE",
                "libreoffice_formula_recalc": "SYNTHETIC_FIXTURE_CACHE_RESTORED; VERIFY_STABLE_RELEASE_AND_REAL_FILES",
                "external_links_openpyxl_roundtrip": "EXECUTED_WITH_SYNTHETIC_LINK",
                "python_docx_write_preservation": "INCONCLUSIVE_DEPENDENCY_MISSING" if env["packages"]["python-docx"] == "NOT_INSTALLED" else "EXECUTED_WITH_PER_CASE_RESULTS",
                "performance_xlsx_50k": "EXECUTED_WITH_PER_TRIAL_RESULTS",
                "performance_docx_10mb": "EXECUTED_WITH_PER_TRIAL_RESULTS",
                "security_encrypted_office": "NOT_RUN_FIXTURE_MISSING",
                "security_macro_legacy_xls": "NOT_RUN_FIXTURE_MISSING",
            "concurrency_global_process_snapshot": "INCONCLUSIVE_RUNTIME_SANDBOX_DENIED_PROCESS_ENUMERATION" if any(item.get("enumeration_status") == "DENIED_BY_RUNTIME_SANDBOX" for item in env["baseline_soffice_processes"]) else "EXECUTED",
            "authorized_real_business_samples": "NOT_AVAILABLE; SYNTHETIC_FIXTURES_ONLY",
            "odoo_sync_async_decision": "INCONCLUSIVE; EXPLICIT_RUNTIME_BUDGETS_NOT_FOUND",
            },
            "synthetic_fixtures_are_removed_after_run": True,
        }
        save_json(output / "TV_Office_Engine_M1_Results.json", results)
        post = process_rows()
        save_json(output / "TV_Office_Engine_M1_PostRun_Soffice_Processes.json", {"processes": post, "baseline": env["baseline_soffice_processes"]})
    print(f"TV probes completed. Evidence: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
