"""Telegram-friendly table rendering utilities.

Telegram does not provide a native spreadsheet/table message primitive, so this
module renders compact Unicode box tables that stay readable on mobile.  It
also converts ordinary Markdown tables produced by AI into the same format.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Sequence


def _cell_width(value: object) -> int:
    text = str(value if value is not None else "")
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in {"W", "F"}:
            width += 2
        elif unicodedata.category(ch) in {"Cf", "Mn"}:
            continue
        else:
            width += 1
    return max(width, 1)


def _truncate(value: object, max_width: int) -> str:
    text = str(value if value is not None else "").replace("\n", " ").strip()
    if _cell_width(text) <= max_width:
        return text
    if max_width <= 1:
        return "…"
    out = ""
    used = 0
    for ch in text:
        cw = 2 if unicodedata.east_asian_width(ch) in {"W", "F"} else 1
        if used + cw > max_width - 1:
            break
        out += ch
        used += cw
    return out + "…"


def render_table(
    headers: Sequence[object],
    rows: Iterable[Sequence[object]],
    *,
    title: str = "",
    max_width: int = 58,
    max_rows: int = 30,
) -> str:
    """Render a compact Unicode table suitable for Telegram mobile clients."""
    heads = [str(x if x is not None else "") for x in headers]
    if not heads:
        return title.strip() if title else ""

    data = []
    for row in list(rows)[:max_rows]:
        vals = list(row)
        vals += [""] * max(0, len(heads) - len(vals))
        data.append([str(v if v is not None else "") for v in vals[: len(heads)]])

    # Keep the whole table reasonably narrow on phones. Long columns share the
    # available width instead of creating a huge horizontal block.
    n = len(heads)
    widths = [max(_cell_width(heads[i]), *( [_cell_width(r[i]) for r in data] or [1] )) for i in range(n)]
    total = sum(widths) + 3 * n + 1
    if total > max_width:
        target = max(6, (max_width - (3 * n + 1)) // n)
        widths = [min(w, target) for w in widths]

    def row_text(values: Sequence[object]) -> str:
        cells = []
        for i, value in enumerate(values):
            txt = _truncate(value, widths[i])
            pad = widths[i] - _cell_width(txt)
            cells.append(f" {txt}{' ' * max(0, pad)} ")
        return "│" + "│".join(cells) + "│"

    top_border = "┬".join("─" * (w + 2) for w in widths)
    mid_border = "┼".join("─" * (w + 2) for w in widths)
    bottom_border = "┴".join("─" * (w + 2) for w in widths)
    top = "┌" + top_border + "┐"
    mid = "├" + mid_border + "┤"
    bottom = "└" + bottom_border + "┘"
    lines = []
    if title.strip():
        lines.append(title.strip())
    lines.extend([top, row_text(heads), mid])
    lines.extend(row_text(row) for row in data)
    lines.append(bottom)
    return "\n".join(lines)


_MD_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _split_md_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [part.strip() for part in text.split("|")]


def markdown_tables_to_unicode(text: str) -> str:
    """Convert Markdown pipe tables to compact Telegram Unicode tables."""
    if not text or "|" not in text:
        return text or ""

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if not in_fence and i + 1 < len(lines) and "|" in line and _MD_SEPARATOR.match(lines[i + 1]):
            headers = _split_md_row(line)
            rows: list[list[str]] = []
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                row = _split_md_row(lines[j])
                if len(row) == len(headers):
                    rows.append(row)
                    j += 1
                else:
                    break
            if rows or headers:
                out.append(render_table(headers, rows))
                i = j
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


def prepare_ai_output(text: str) -> str:
    """Normalize AI-generated Markdown tables for Telegram."""
    return markdown_tables_to_unicode(text)
