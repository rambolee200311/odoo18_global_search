#!/usr/bin/env python3
"""Fail-closed 检查 skill 内模板与项目权威来源是否同步。"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "references" / "templates"

TEMPLATES = {
    "business-requirements": (
        "Designing/Business_Requirements_Guide.md",
        "docs/context/cognition/template/Designing/Business_Requirements_Guide.md",
    ),
    "srs": (
        "Designing/SRS模板.md",
        "docs/context/cognition/template/Designing/SRS模板.md",
    ),
    "ddd": (
        "Designing/DDD模板.md",
        "docs/context/cognition/template/Designing/DDD模板.md",
    ),
    "technical-verification": (
        "Designing/Technical_Verification_Guide.md",
        "docs/context/cognition/template/Designing/Technical_Verification_Guide.md",
    ),
    "tdd": (
        "Designing/TDD模板.md",
        "docs/context/cognition/template/Designing/TDD模板.md",
    ),
    "cc": (
        "Coding/Coding_Contract模板.md",
        "docs/context/cognition/template/Coding/Coding_Contract模板.md",
    ),
    "ihr": (
        "Coding/IHR模板.md",
        "docs/context/cognition/template/Coding/IHR模板.md",
    ),
    "atr": (
        "Coding/ATR模板.md",
        "docs/context/cognition/template/Coding/ATR模板.md",
    ),
    "hvr": (
        "Coding/HVR模板.md",
        "docs/context/cognition/template/Coding/HVR模板.md",
    ),
    "fr": (
        "Coding/FR模板.md",
        "docs/context/cognition/template/Coding/FR模板.md",
    ),
    "pvr": (
        "Closoure/PVR模板.md",
        "docs/context/cognition/template/Closoure/PVR模板.md",
    ),
    "pcr": (
        "Closoure/PCR模板.md",
        "docs/context/cognition/template/Closoure/PCR模板.md",
    ),
}
PLAN_TEMPLATE = "Planning/IMPLEMENTATION_PLAN_TEMPLATE.md"
PROJECT_WORKFLOW = "docs/context/cognition/Project_Workflow.md"
PROJECT_WORKFLOW_SHA256 = "8075c91bbd5fd76e50c9ee7f50bd606418e6dc97bda4f57c2f44618f6546d44f"
METADATA_RE = re.compile(rb"\A<!-- Skill bundle metadata\n(.*?)\n-->\n\n", re.S)


def find_repo_root(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())
    candidates.extend(Path.cwd().resolve().parents)
    candidates.append(Path.cwd().resolve())
    candidates.extend(SKILL_DIR.parents)
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "docs/context/cognition/template").is_dir():
            return candidate
    return None


def parse_metadata(bundle: Path) -> tuple[bytes, dict[str, str]]:
    raw = bundle.read_bytes()
    match = METADATA_RE.match(raw)
    if not match:
        raise ValueError(f"缺少模板头部元数据：{bundle}")
    metadata: dict[str, str] = {}
    for line in match.group(1).decode("utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    required = {"Source path", "Source version/status", "Synced"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"模板元数据缺少字段 {', '.join(sorted(missing))}：{bundle}")
    date.fromisoformat(metadata["Synced"])
    body = raw[match.end() :]
    return body, metadata


def check_header_metadata(source: bytes, version_status: str, label: str) -> list[str]:
    errors: list[str] = []
    head = source.decode("utf-8", errors="replace").splitlines()[:20]
    head_text = "\n".join(head)
    expected_versions = re.findall(r"\bv\d+(?:\.\d+){1,2}\b", version_status)
    actual_versions = re.findall(r"\bv\d+(?:\.\d+){1,2}\b", head_text, flags=re.I)
    expected_statuses = re.findall(r"\b(Frozen|Draft|RC)\b", version_status, flags=re.I)
    actual_statuses = re.findall(r"\b(Frozen|Draft|RC)\b", head_text, flags=re.I)
    if expected_versions and not set(expected_versions).issubset(set(actual_versions)):
        errors.append(
            f"{label}: 元数据版本 {expected_versions} 与来源头部版本 {actual_versions} 不一致"
        )
    if expected_statuses and not {
        value.lower() for value in expected_statuses
    }.issubset({value.lower() for value in actual_statuses}):
        errors.append(
            f"{label}: 元数据状态 {expected_statuses} 与来源头部状态 {actual_statuses} 不一致"
        )
    return errors


def check_closure_status_conflict(repo_root: Path, key: str) -> list[str]:
    if key not in {"pvr", "pcr"}:
        return []
    workflow = repo_root / "docs/context/cognition/Project_Workflow.md"
    if not workflow.exists():
        return [f"{key}: 找不到 Project_Workflow.md，无法核对 Closure 模板状态"]
    text = workflow.read_text(encoding="utf-8")
    template_name = "PVR模板.md" if key == "pvr" else "PCR模板.md"
    has_draft_placeholder = any(
        template_name in line and "Draft（占位）" in line for line in text.splitlines()
    )
    bundled_path, source_rel = TEMPLATES[key]
    source = (repo_root / source_rel).read_text(encoding="utf-8")
    has_frozen_header = "Frozen" in "\n".join(source.splitlines()[:10])
    if has_draft_placeholder and has_frozen_header:
        return [
            f"{key}: 来源状态冲突：Project_Workflow.md §0.3 / §11 将 {template_name} "
            "标为 Draft（占位），但对应模板头部标为 Frozen；请文档负责人统一 "
            "Draft / Frozen 描述，skill 不自行裁定"
        ]
    return []


def check_one(key: str, repo_root: Path) -> list[str]:
    if key == "implementation-plan":
        bundle = TEMPLATE_DIR / PLAN_TEMPLATE
        try:
            _, metadata = parse_metadata(bundle)
        except (OSError, ValueError) as exc:
            return [str(exc)]
        if not metadata["Source path"].startswith("Skill-authored"):
            return [f"Implementation Plan 模板来源元数据异常：{metadata['Source path']}"]
        return []

    if key not in TEMPLATES:
        return [f"未知模板名：{key}"]
    bundle_rel, source_rel = TEMPLATES[key]
    bundle = TEMPLATE_DIR / bundle_rel
    source_path = repo_root / source_rel
    label = f"{key} ({bundle_rel})"
    try:
        body, metadata = parse_metadata(bundle)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    if metadata["Source path"] != source_rel:
        return [f"{label}: 来源路径不匹配，记录为 {metadata['Source path']}，应为 {source_rel}"]
    if not source_path.is_file():
        return [f"{label}: 找不到来源文件 {source_path}"]
    source = source_path.read_bytes()
    errors = check_header_metadata(source, metadata["Source version/status"], label)
    if body != source:
        errors.append(f"{label}: 模板正文与来源文件不同步；请核对版本 / 状态并同步副本")
    errors.extend(check_closure_status_conflict(repo_root, key))
    return errors


def check_workflow_baseline(repo_root: Path) -> list[str]:
    workflow = repo_root / PROJECT_WORKFLOW
    if not workflow.is_file():
        return [f"找不到 {PROJECT_WORKFLOW}，无法核对工作流来源"]
    digest = hashlib.sha256(workflow.read_bytes()).hexdigest()
    if digest != PROJECT_WORKFLOW_SHA256:
        return [
            f"{PROJECT_WORKFLOW} 已变化（SHA-256 {digest}）；"
            "先评估并同步 skill，再使用其模板或门禁"
        ]
    return []


def main() -> int:
    choices = [*TEMPLATES, "implementation-plan"]
    parser = argparse.ArgumentParser(
        description="比对 skill 内模板与项目来源；任何差异均返回非零状态。"
    )
    parser.add_argument("--repo-root", help="项目仓库根目录；默认自动查找")
    parser.add_argument("--template", choices=choices, help="只核对当前要使用的模板")
    args = parser.parse_args()
    repo_root = find_repo_root(args.repo_root)
    if repo_root is None:
        print("BLOCKED：找不到项目模板来源。请在项目仓库内运行或传入 --repo-root。")
        return 2

    workflow_errors = check_workflow_baseline(repo_root)
    if workflow_errors:
        print("BLOCKED：Project_Workflow 来源已变化，先审查并同步 skill：", file=sys.stderr)
        for error in workflow_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    keys = [args.template] if args.template else choices
    failures: list[str] = []
    for key in keys:
        errors = check_one(key, repo_root)
        if errors:
            failures.extend(errors)
        else:
            print(f"PASS：{key}")
    if failures:
        print("BLOCKED：模板来源核对失败，停止使用相关模板：", file=sys.stderr)
        for error in failures:
            print(f"- {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
