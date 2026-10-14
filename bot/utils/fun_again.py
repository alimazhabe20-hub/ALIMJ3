"""دکمه «یکی دیگه» برای انگیزشی / دانستنی / جوک."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def fun_again_keyboard(kind: str) -> InlineKeyboardMarkup:
    """kind: motivation | fact | joke"""
    kind = (kind or "motivation").strip().lower()
    if kind not in ("motivation", "fact", "joke"):
        kind = "motivation"
    labels = {
        "motivation": "💖 یکی دیگه",
        "fact": "🧠 یکی دیگه",
        "joke": "😂 یکی دیگه",
    }
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(labels[kind], callback_data=f"fun:again:{kind}")]]
    )
