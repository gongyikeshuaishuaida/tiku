#!/usr/bin/env python3
"""Extract PDF content using MinerU CLI (mineru-open-api).

Setup:
  npm install -g mineru-open-api
  mineru-open-api version                  # verify installation
  mineru-open-api auth                     # login (required for default precision mode)

Default (high-precision, extracts images):
  py -X utf8 scripts/mineru_extract.py "试卷/xxx.pdf"

Flash mode (free, no auth, no images):
  py -X utf8 scripts/mineru_extract.py "试卷/xxx.pdf" --flash
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_cli() -> str:
    """Find the mineru-open-api CLI executable."""
    # Check common npm global install locations
    candidates = [
        # Windows: npm global in AppData
        os.path.expandvars(r"%APPDATA%\npm\mineru-open-api.cmd"),
        os.path.expandvars(r"%APPDATA%\npm\mineru-open-api"),
        # POSIX: npm global
        "/usr/local/bin/mineru-open-api",
        "/usr/bin/mineru-open-api",
        # Fallback: just the name (relies on PATH)
        "mineru-open-api",
    ]
    for c in candidates:
        if os.path.exists(c) or c == "mineru-open-api":
            return c
    return "mineru-open-api"


def _get_cli() -> str:
    """Get CLI path, caching it for subsequent calls."""
    if not hasattr(_get_cli, "_cache"):
        cli = _find_cli()
        _get_cli._cache = cli
    return _get_cli._cache


def run_mineru(
    pdf_path: str,
    output_dir: str,
    flash: bool = False,
    formats: str = "md",
    token: str | None = None,
    table: bool = False,
) -> None:
    """Run mineru-open-api CLI and return the result directory."""
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.exists(pdf_path):
        sys.exit(f"PDF not found: {pdf_path}")

    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    cli = _get_cli()
    if flash:
        # Free flash mode (no auth, no images)
        cmd = [
            cli, "flash-extract",
            pdf_path,
            "-o", str(out_root),
        ]
        print(f"Extracting (flash mode): {pdf_path}")
    else:
        # Default: high-precision mode, tables kept as images
        cmd = [
            cli, "extract",
            pdf_path,
            "-o", str(out_root),
            "-f", formats,
            f"--table={str(table).lower()}",
        ]
        print(f"Extracting (high-precision, table={'on' if table else 'off'}): {pdf_path}")

    # Pass token from env var or explicit argument
    token = token or os.environ.get("MINERU_API_TOKEN", "")
    if token:
        cmd.extend(["--token", token])

    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except FileNotFoundError:
        sys.exit(
            f"mineru-open-api not found (tried: {cli}). Install with:\n"
            "  npm install -g mineru-open-api\n"
            "Verify with:\n"
            "  mineru-open-api version"
        )
    except subprocess.CalledProcessError as e:
        print(f"MinerU exited with code {e.returncode}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        if "auth" in (e.stderr or "").lower() or "login" in (e.stderr or "").lower():
            print("\nTip: Run 'mineru-open-api auth' to log in for high-precision mode.")
        sys.exit(1)


def find_and_summarize(output_dir: str) -> Path:
    """Find the result directory and print a summary."""
    root = Path(output_dir)

    # mineru-open-api typically creates output_dir/<pdf_name>/
    # or places files directly in output_dir/
    md_files = sorted(root.rglob("*.md"))
    if not md_files:
        print(f"No Markdown files found in {root}")
        return root

    # Find the result directory (closest parent of the first .md file)
    result_dir = md_files[0].parent

    img_dirs = [d for d in result_dir.rglob("images") if d.is_dir()]
    img_count = sum(len(list(d.iterdir())) for d in img_dirs)

    print(f"\n{'='*50}")
    print(f"Result directory: {result_dir}")
    print(f"Markdown files: {len(md_files)}")
    for m in md_files:
        size_kb = m.stat().st_size / 1024
        print(f"  {m.relative_to(result_dir)} ({size_kb:.1f} KB)")
    print(f"Images: {img_count}")
    for d in img_dirs:
        print(f"  {d.relative_to(result_dir)}/ ({len(list(d.iterdir()))} files)")

    # Check content_list.json
    for cl in result_dir.rglob("content_list.json"):
        try:
            data = json.loads(cl.read_text(encoding="utf-8"))
            if isinstance(data, list):
                print(f"Content items: {len(data)}")
        except Exception:
            pass

    # Print preview of first markdown
    if md_files:
        print(f"\n--- Preview of {md_files[0].name} ---")
        text = md_files[0].read_text(encoding="utf-8")
        preview = text[:2000]
        if len(text) > 2000:
            preview += "\n... (truncated)"
        print(preview)

    return result_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract PDF content using mineru-open-api CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument(
        "--output", "-o",
        default="_mineru_output",
        help="Output root directory (default: _mineru_output)",
    )
    parser.add_argument(
        "--flash",
        action="store_true",
        help="Use free flash-extract mode (no auth, fast, but no images)",
    )
    parser.add_argument(
        "--formats", "-f",
        default="md",
        help="Output formats (default: md). Other options: docx, html, latex",
    )
    parser.add_argument(
        "--token",
        help="MinerU API token (overrides MINERU_API_TOKEN env var). Get from https://mineru.net/ecosystem",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        default=False,
        help="Enable table recognition (OCR tables to HTML). Default: disabled, tables kept as images.",
    )
    args = parser.parse_args()

    run_mineru(args.pdf, args.output, args.flash, args.formats, args.token, args.table)
    result_dir = find_and_summarize(args.output)

    print(f"\nDone. MinerU output at: {result_dir}")


if __name__ == "__main__":
    main()
