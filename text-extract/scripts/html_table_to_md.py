"""Convert simple HTML <table> blocks in Markdown to Markdown tables.

Usage:
    py -X utf8 html_table_to_md.py file.md          # in-place
    py -X utf8 html_table_to_md.py file.md --stdout  # print to stdout
"""

import re
import sys
from pathlib import Path


def html_table_to_md(html: str) -> str:
    """Convert a single HTML <table> to a Markdown table string.
       Returns the original HTML if it contains colspan/rowspan or nested tables.
    """
    # Reject complex tables
    if re.search(r'(?:colspan|rowspan)\s*=', html, re.IGNORECASE):
        return html
    if html.count("<table") > 1:
        return html

    rows: list[list[str]] = []
    for tr_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE):
        cells: list[str] = []
        for td_match in re.finditer(r"<t[dh][^>]*>(.*?)</t[dh]>", tr_match.group(1), re.DOTALL | re.IGNORECASE):
            cell = td_match.group(1).strip()
            # Replace pipe chars inside cells to avoid table breakage
            cell = cell.replace("|", r"\|")
            cell = cell.replace("\n", " ")
            # Collapse whitespace
            cell = re.sub(r"\s+", " ", cell).strip()
            cells.append(cell)
        if cells:
            rows.append(cells)

    if len(rows) < 2:
        return html

    # Ensure consistent column count
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")

    lines: list[str] = []
    # Header row
    lines.append("| " + " | ".join(rows[0]) + " |")
    # Separator
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    # Data rows
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")

    return "\n".join(lines)


def convert_file(path: str | Path) -> str:
    """Convert all simple HTML tables in a Markdown file. Returns the new content."""
    text = Path(path).read_text(encoding="utf-8")

    def replace_table(m: re.Match) -> str:
        html = m.group(0)
        return html_table_to_md(html)

    return re.sub(r"<table[^>]*>.*?</table>", replace_table, text, flags=re.DOTALL | re.IGNORECASE)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: py -X utf8 html_table_to_md.py <file.md> [--stdout]")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    new_content = convert_file(path)

    if "--stdout" in sys.argv:
        print(new_content)
    else:
        path.write_text(new_content, encoding="utf-8")
        print(f"Converted tables in: {path}")


if __name__ == "__main__":
    main()
