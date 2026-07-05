#!/usr/bin/env python3
"""Validate local Obsidian question-bank notes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_FIELDS = [
    "id",
    "题型",
    "来源",
    "试卷",
    "题号",
    "难度",
    "知识点",
    "完成次数",
    "正确率",
    "状态",
    "错题原因",
    "创建日期",
    "图片核验",
    "tags",
]

STALE_TERMS = ["正确次数", "下次复习", "上次练习", "待补充"]


def read_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    frontmatter = text[4:end].splitlines()
    data: dict[str, str] = {}
    for line in frontmatter:
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def section_text(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^## |\n---\n", text[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def iter_notes(root: Path, prefix: str | None) -> list[Path]:
    files = sorted(root.rglob("*.md"))
    if prefix:
        files = [path for path in files if path.name.startswith(prefix)]
    return [
        path
        for path in files
        if not any(part in {".obsidian", ".codex-skills", "scripts"} for part in path.parts)
    ]


def validate_note(root: Path, path: Path) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(root)
    text = path.read_text(encoding="utf-8")
    meta = read_frontmatter(text)

    if not meta:
        return [f"{rel}: missing frontmatter"]

    for field in REQUIRED_FIELDS:
        if field not in meta:
            errors.append(f"{rel}: missing field {field}")

    note_id = meta.get("id")
    if note_id and note_id != path.stem:
        errors.append(f"{rel}: id does not match filename ({note_id})")

    for term in STALE_TERMS:
        if term in text:
            errors.append(f"{rel}: contains stale/placeholder term {term}")

    answer = section_text(text, "答案")
    analysis = section_text(text, "解析")
    if not answer:
        errors.append(f"{rel}: empty or missing ## 答案")
    if not analysis:
        errors.append(f"{rel}: empty or missing ## 解析")

    embeds = re.findall(r"!\[\[attachments/([^\]]+)\]\]", text)
    image_status = meta.get("图片核验", "")
    if embeds and image_status == "无图片":
        errors.append(f"{rel}: has image embeds but 图片核验 is 无图片")
    if not embeds and image_status != "无图片":
        errors.append(f"{rel}: no image embeds but 图片核验 is {image_status}")
    for embed in embeds:
        attachment = root / "attachments" / embed
        if not attachment.exists():
            errors.append(f"{rel}: missing attachment {attachment.relative_to(root)}")

    # Check for Markdown tables in question body (not in 答案/解析 sections)
    # Tables in exam content should be images per --table=false policy
    body = text
    ans_match = re.search(r"^## 答案\s*$", text, flags=re.MULTILINE)
    if ans_match:
        body = text[:ans_match.start()]
    if re.search(r"^\|.+\|.*\n\|[\s\-:]+\|", body, re.MULTILINE):
        errors.append(f"{rel}: contains Markdown table in question body — replace with image")

    # Check for duplicate frontmatter keys
    fm_lines = text[4:text.find("\n---", 4)].splitlines() if text.startswith("---\n") else []
    seen_keys: set[str] = set()
    for line in fm_lines:
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key = line.split(":", 1)[0].strip()
            if key in seen_keys:
                errors.append(f"{rel}: duplicate frontmatter key '{key}'")
            seen_keys.add(key)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prefix", help="Only validate note filenames with this prefix.")
    args = parser.parse_args()

    root = args.root.resolve()
    errors: list[str] = []
    notes = iter_notes(root, args.prefix)
    for path in notes:
        errors.extend(validate_note(root, path))

    for error in errors:
        print(f"ERROR: {error}")
    print(f"checked {len(notes)} note(s), errors {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
