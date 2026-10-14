"""مبدل فونت — انگلیسی + بهترین استایل‌های یونیکد سازگار با فارسی و عربی"""
from .styles import STYLES, FONT_NAMES, PERSIAN_COMPATIBLE
import random
import re

# فونت‌های مناسب انگلیسی (unicode fancy)
EN_STYLES = [
    "bold", "italic", "bold_italic", "script", "bold_script", "fraktur", "bold_fraktur",
    "double", "monospace", "sans", "sans_bold", "sans_italic", "sans_bold_italic",
    "fullwidth", "circled", "small_caps", "superscript", "subscript", "upside_down",
    "strikethrough", "underline", "spaced", "reverse",
]

# بهترین استایل‌های سازگار با فارسی و عربی
FA_STYLES = list(PERSIAN_COMPATIBLE)


def _apply(text: str, style_key: str) -> str:
    style = STYLES.get(style_key)
    if style is None:
        return text
    if callable(style):
        return style(text)
    if isinstance(style, dict) and style and all(isinstance(k, int) for k in style.keys()):
        return text.translate(style)
    return "".join(style.get(ch, ch) for ch in text)


def list_fonts() -> str:
    en_lines = []
    for k in EN_STYLES:
        if k in FONT_NAMES:
            sample = _apply("Abc", k)
            en_lines.append(f"• {FONT_NAMES[k]}  →  {sample}")
    fa_lines = []
    for k in FA_STYLES:
        if k in FONT_NAMES:
            sample = _apply("نمونه", k)
            fa_lines.append(f"• {FONT_NAMES[k]}  →  {sample}")
    parts = [
        "🎨  **استودیوی فونت**",
        "・ ・ ・ ・ ・",
        "",
        "🇬🇧  **انگلیسی**",
        *en_lines,
        "",
        "🇮🇷  **فارسی / عربی**",
        *fa_lines,
        "",
        "・ ・ ・ ・ ・",
        "📌 از منو یک فونت انتخاب کن، بعد متنت را بفرست.",
    ]
    return "\n".join(parts)


def get_font_preview(style_key: str = None) -> str:
    sample_en = "Hello World 123"
    sample_fa = "سلام دنیا"
    if style_key and style_key in STYLES:
        en = _apply(sample_en, style_key)
        fa = _apply(sample_fa, style_key)
        name = FONT_NAMES.get(style_key, style_key)
        return "\n".join([
            "🎨  **پیش‌نمایش فونت**",
            f"✨  `{name}`",
            "・ ・ ・ ・ ・",
            "",
            "🇬🇧  انگلیسی",
            en,
            "",
            "🇮🇷  فارسی",
            fa,
            "",
            "・ ・ ・ ・ ・",
            "📝 حالا متن خودت را بفرست.",
        ])
    keys = list(STYLES.keys())
    random.shuffle(keys)
    lines = [
        "🎨  **نمونه‌های تصادفی**",
        "・ ・ ・ ・ ・",
        "",
    ]
    for k in keys[:6]:
        lines.append(f"**{FONT_NAMES.get(k, k)}**")
        lines.append(_apply(sample_en, k))
        lines.append("")
    lines.append("・ ・ ・ ・ ・")
    return "\n".join(lines)


def apply_font(text: str, style_key: str) -> str:
    if not text or not text.strip():
        return "\n".join([
            "🎨  **استودیوی فونت**",
            "・ ・ ・ ・ ・",
            "❌ متن خالی است.",
            "یک کلمه یا جمله بفرست.",
        ])
    if style_key not in STYLES:
        return f"❌ فونت «{style_key}» پیدا نشد."
    text = text.strip()
    if len(text) > 500:
        text = text[:500]
    converted = _apply(text, style_key)
    name = FONT_NAMES.get(style_key, style_key)
    return "\n".join([
        "🎨  **نتیجهٔ فونت**",
        f"✨  `{name}`",
        "・ ・ ・ ・ ・",
        "",
        converted,
        "",
        "・ ・ ・ ・ ・",
        f"📥  اصل: {text}",
        "",
        "💡 دوباره متن بفرست یا فونت دیگری انتخاب کن.",
    ])


def _is_mostly_persian(text: str) -> bool:
    fa = len(re.findall(r"[\u0600-\u06FF]", text))
    en = len(re.findall(r"[A-Za-z]", text))
    return fa >= en


def apply_all_fonts(text: str) -> str:
    """اعمال همه فونت‌های مرتبط (هوشمند فارسی/عربی یا انگلیسی)"""
    if not text or not text.strip():
        return "\n".join([
            "🌈  **گالری فونت**",
            "・ ・ ・ ・ ・",
            "❌ متن خالی است.",
            "یک کلمه یا جمله کوتاه بفرست.",
        ])
    text = text.strip()
    if len(text) > 80:
        text = text[:80]
    keys = FA_STYLES if _is_mostly_persian(text) else EN_STYLES
    lang = "فارسی / عربی" if keys is FA_STYLES else "انگلیسی"
    lines = [
        "🌈  **گالری فونت**",
        f"📝  `{text}`",
        f"🌍  مجموعه: {lang}",
        "・ ・ ・ ・ ・",
        "",
    ]
    n = 0
    for k in keys:
        if k not in STYLES:
            continue
        try:
            conv_t = _apply(text, k)
            name = FONT_NAMES.get(k, k)
            n += 1
            lines.append(f"**{n}. {name}**")
            lines.append(conv_t)
            lines.append("")
        except Exception:
            continue
    lines.append("・ ・ ・ ・ ・")
    lines.append(f"✨  {n} استایل آماده شد")
    lines.append("💡 برای یک فونت خاص، از منوی انگلیسی/فارسی انتخاب کن.")
    return "\n".join(lines)
