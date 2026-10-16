"""قالب یکسان UI: عنوان ضخیم + محتوای نقل‌قولی (blockquote تلگرام)."""
from __future__ import annotations

import html as _html
from typing import Optional


def esc(s) -> str:
    return _html.escape(str(s if s is not None else ""), quote=False)


def bold(s: str) -> str:
    return f"<b>{esc(s)}</b>"


def quote(body: str) -> str:
    body = (body or "").strip()
    if not body:
        return ""
    return f"<blockquote>{esc(body)}</blockquote>"


def section(title: str, body: str) -> str:
    """عنوان ضخیم + بدنه نقل‌قول."""
    body = (body or "").strip()
    if not body:
        return bold(title)
    return f"{bold(title)}\n{quote(body)}"


def sections(*pairs: tuple[str, str], footer: str = "") -> str:
    """چند بخش پشت‌سرهم + فوتر اختیاری."""
    parts = []
    for title, body in pairs:
        if not (body or "").strip() and not (title or "").strip():
            continue
        parts.append(section(title, body))
    if footer:
        parts.append(esc(footer) if "<" not in footer else footer)
    return "\n".join(p for p in parts if p)


def ensure_html_parse_mode(kwargs: dict) -> dict:
    kwargs = dict(kwargs or {})
    kwargs.setdefault("parse_mode", "HTML")
    return kwargs
