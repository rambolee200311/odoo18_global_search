#!/usr/bin/env python3
"""检查 skill 内 Odoo 工程准则与项目冻结来源是否同步。"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLE = SKILL_DIR / "references" / "Odoo_Engineering_Guidelines.md"
SOURCE_REL = Path("docs/context/cognition/Odoo_Engineering_Guidelines.md")
SOURCE_STATUS = "Odoo 版本无关; Frozen"
METADATA_RE = re.compile(rb"\A<!-- Skill bundle metadata\n(.*?)\n-->\n\n", re.S)


def find_repo_root(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())
    candidates.extend([Path.cwd().resolve(), *Path.cwd().resolve().parents])
    candidates.extend(SKILL_DIR.parents)
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / SOURCE_REL).is_file():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="比对内置 Odoo 工程准则与项目冻结来源；不一致时返回非零状态。"
    )
    parser.add_argument("--repo-root", help="项目仓库根目录；默认自动查找")
    args = parser.parse_args()
    repo_root = find_repo_root(args.repo_root)
    if repo_root is None:
        print(
            f"BLOCKED：找不到项目来源 {SOURCE_REL}；不得将内置副本视为已核对的权威版本。",
            file=sys.stderr,
        )
        return 2

    try:
        bundle_raw = BUNDLE.read_bytes()
        match = METADATA_RE.match(bundle_raw)
        if not match:
            raise ValueError("内置指南缺少来源元数据")
        metadata: dict[str, str] = {}
        for line in match.group(1).decode("utf-8").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        for field in ("Source path", "Source version/status", "Synced"):
            if field not in metadata:
                raise ValueError(f"内置指南元数据缺少字段：{field}")
        date.fromisoformat(metadata["Synced"])
        if metadata["Source path"] != SOURCE_REL.as_posix():
            raise ValueError(f"来源路径不匹配：{metadata['Source path']}")
        if metadata["Source version/status"] != SOURCE_STATUS:
            raise ValueError(
                f"记录的来源状态不匹配：{metadata['Source version/status']}；"
                f"预期 {SOURCE_STATUS}"
            )
        source = (repo_root / SOURCE_REL).read_bytes()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"BLOCKED：{exc}", file=sys.stderr)
        return 1

    header = source.decode("utf-8", errors="replace").splitlines()[:8]
    if "## Status: Frozen" not in header or "## Version Policy: Odoo 版本无关" not in header:
        print(
            "BLOCKED：来源头部的冻结状态或版本政策已变化；先审阅并同步 skill。",
            file=sys.stderr,
        )
        return 1

    bundled_body = bundle_raw[match.end() :]
    if bundled_body.removesuffix(b"\n") != source.removesuffix(b"\n"):
        print(
            "BLOCKED：内置指南正文与来源文件不同步；先审阅差异并更新副本及元数据。",
            file=sys.stderr,
        )
        return 1

    print("PASS：内置 Odoo 工程准则与冻结来源一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
