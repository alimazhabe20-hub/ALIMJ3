"""Pretty table image renderer for Telegram (Pillow).

Produces clean PNG tables similar to professional market channels:
light cells, subtle borders, green/red change colors, RTL-friendly layout.
"""
from __future__ import annotations

import io
import re
from typing import Iterable, Sequence


def _parse_change(value: object) -> tuple[str, str | None]:
    """Return (display_text, color_hex or None)."""
    text = str(value if value is not None else "").strip()
    if not text or text in {"—", "-", "–"}:
        return text or "—", None
    # detect + / - percentages or numbers
    m = re.search(r"([+\-−]?\s*\d+[.,]?\d*)\s*%?", text)
    color = None
    if m:
        raw = m.group(1).replace("−", "-").replace(" ", "").replace(",", ".")
        try:
            num = float(raw)
            if num > 0:
                color = "#16a34a"  # green
            elif num < 0:
                color = "#dc2626"  # red
        except ValueError:
            pass
    if "🟢" in text or "▲" in text or text.startswith("+"):
        color = color or "#16a34a"
    if "🔴" in text or "▼" in text or text.startswith("-") or text.startswith("−"):
        color = color or "#dc2626"
    # clean emoji for image
    clean = text.replace("🟢", "").replace("🔴", "").replace("▲", "").replace("▼", "").strip()
    return clean or text, color


def render_table_image(
    headers: Sequence[object],
    rows: Iterable[Sequence[object]],
    *,
    title: str = "",
    max_rows: int = 25,
    col_align: Sequence[str] | None = None,
) -> bytes:
    """Render a clean channel-style table as PNG bytes."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise RuntimeError("Pillow نصب نیست") from e

    heads = [str(h if h is not None else "") for h in headers]
    data = [list(r) for r in rows][:max_rows]
    if not heads:
        heads = [f"ستون{i+1}" for i in range(len(data[0]) if data else 1)]

    n_cols = len(heads)
    # normalize row lengths
    norm_rows: list[list[str]] = []
    change_colors: list[list[str | None]] = []
    for row in data:
        cells = []
        colors = []
        for i in range(n_cols):
            val = row[i] if i < len(row) else ""
            txt, col = _parse_change(val)
            cells.append(txt)
            colors.append(col)
        norm_rows.append(cells)
        change_colors.append(colors)

    # fonts — try common system fonts, fallback to default
    def _font(size: int, bold: bool = False):
        candidates = []
        if bold:
            candidates += [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ]
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    font_title = _font(22, bold=True)
    font_head = _font(15, bold=True)
    font_cell = _font(14)
    font_small = _font(12)

    # measure
    padding_x = 14
    padding_y = 10
    row_h = 36
    header_h = 40
    title_h = 48 if title.strip() else 12
    footer_h = 16

    def text_w(font, text: str) -> int:
        try:
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0]
        except Exception:
            return len(text) * 8

    # column widths
    col_ws = []
    for i in range(n_cols):
        w = text_w(font_head, heads[i]) + padding_x * 2
        for row in norm_rows:
            w = max(w, text_w(font_cell, row[i]) + padding_x * 2)
        col_ws.append(min(max(w, 70), 220))

    table_w = sum(col_ws) + 2
    img_w = table_w + 24
    img_h = title_h + header_h + row_h * len(norm_rows) + footer_h + 12

    # colors matching channel style
    BG = (245, 247, 250)
    HEADER_BG = (230, 235, 242)
    ROW_BG = (255, 255, 255)
    ROW_ALT = (248, 250, 252)
    BORDER = (200, 208, 220)
    TEXT = (30, 35, 45)
    TITLE_COLOR = (20, 25, 35)

    img = Image.new("RGB", (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)

    # title
    y = 10
    if title.strip():
        tw = text_w(font_title, title.strip())
        draw.text(((img_w - tw) // 2, y), title.strip(), font=font_title, fill=TITLE_COLOR)
        y = title_h

    # table origin
    x0 = (img_w - table_w) // 2
    y0 = y

    # header background
    draw.rectangle([x0, y0, x0 + table_w, y0 + header_h], fill=HEADER_BG, outline=BORDER)

    # header text (RTL-ish: rightmost column first visually if Persian, but we keep given order)
    cx = x0
    for i, h in enumerate(heads):
        tw = text_w(font_head, h)
        tx = cx + (col_ws[i] - tw) // 2
        draw.text((tx, y0 + (header_h - 18) // 2), h, font=font_head, fill=TEXT)
        cx += col_ws[i]

    # rows
    for r_idx, row in enumerate(norm_rows):
        ry = y0 + header_h + r_idx * row_h
        bg = ROW_ALT if r_idx % 2 else ROW_BG
        draw.rectangle([x0, ry, x0 + table_w, ry + row_h], fill=bg, outline=BORDER)
        cx = x0
        for i, cell in enumerate(row):
            color = change_colors[r_idx][i]
            fill = tuple(int(color.lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) if color else TEXT
            tw = text_w(font_cell, cell)
            # center numbers/changes, right-align labels slightly
            align = (col_align[i] if col_align and i < len(col_align) else "center")
            if align == "right":
                tx = cx + col_ws[i] - tw - padding_x
            elif align == "left":
                tx = cx + padding_x
            else:
                tx = cx + (col_ws[i] - tw) // 2
            draw.text((tx, ry + (row_h - 16) // 2), cell, font=font_cell, fill=fill)
            cx += col_ws[i]

    # outer border
    draw.rectangle([x0, y0, x0 + table_w, y0 + header_h + row_h * len(norm_rows)], outline=BORDER, width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


def render_table_image_or_text(
    headers: Sequence[object],
    rows: Iterable[Sequence[object]],
    *,
    title: str = "",
    max_rows: int = 25,
) -> tuple[bytes | None, str]:
    """Try image first; fall back to unicode text table."""
    rows_list = list(rows)
    try:
        png = render_table_image(headers, rows_list, title=title, max_rows=max_rows)
        return png, title or ""
    except Exception:
        from bot.utils.table_renderer import render_table
        return None, render_table(headers, rows_list, title=title, max_rows=max_rows)
