"""ماشین‌حساب گرافیکی تلگرام — صفحه کلید اینلاین."""
from __future__ import annotations

import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

try:
    from bot.features.tools.features_tools_app_tools import calculator as _eval_expr
except Exception:  # pragma: no cover
    def _eval_expr(expr: str) -> str:
        return f"❌ موتور محاسبه در دسترس نیست.\n`{expr}`"

try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    class _L:
        def debug(self, *a, **k): pass
        def error(self, *a, **k): pass
    logger = _L()

# کلیدهای callback: gcalc:<token>
# token: رقم/عملگر یا فرمان‌های خاص: eq clr bs pm pct sqrt pow

_BTN = InlineKeyboardButton


def _kb() -> InlineKeyboardMarkup:
    """چینش شبیه ماشین‌حساب واقعی."""
    rows = [
        [
            _BTN("C", callback_data="gcalc:clr"),
            _BTN("⌫", callback_data="gcalc:bs"),
            _BTN("(", callback_data="gcalc:("),
            _BTN(")", callback_data="gcalc:)"),
        ],
        [
            _BTN("√", callback_data="gcalc:sqrt"),
            _BTN("^", callback_data="gcalc:^"),
            _BTN("%", callback_data="gcalc:%"),
            _BTN("÷", callback_data="gcalc:/"),
        ],
        [
            _BTN("7", callback_data="gcalc:7"),
            _BTN("8", callback_data="gcalc:8"),
            _BTN("9", callback_data="gcalc:9"),
            _BTN("×", callback_data="gcalc:*"),
        ],
        [
            _BTN("4", callback_data="gcalc:4"),
            _BTN("5", callback_data="gcalc:5"),
            _BTN("6", callback_data="gcalc:6"),
            _BTN("−", callback_data="gcalc:-"),
        ],
        [
            _BTN("1", callback_data="gcalc:1"),
            _BTN("2", callback_data="gcalc:2"),
            _BTN("3", callback_data="gcalc:3"),
            _BTN("+", callback_data="gcalc:+"),
        ],
        [
            _BTN("±", callback_data="gcalc:pm"),
            _BTN("0", callback_data="gcalc:0"),
            _BTN(".", callback_data="gcalc:."),
            _BTN("=", callback_data="gcalc:eq"),
        ],
        [
            _BTN("π", callback_data="gcalc:pi"),
            _BTN("e", callback_data="gcalc:e"),
            _BTN("کپی نتیجه", callback_data="gcalc:copy"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def _display(expr: str, result: str | None = None, error: str | None = None) -> str:
    expr = expr or "0"
    lines = [
        "🔢 **ماشین‌حساب گرافیکی**",
        "────────────────────",
        f"`{expr}`",
    ]
    if error:
        lines.append("")
        lines.append(f"⚠️ {error}")
    elif result is not None:
        lines.append("")
        lines.append(f"📤 **= {result}**")
    lines.append("────────────────────")
    lines.append("از دکمه‌ها استفاده کنید.")
    return "\n".join(lines)


def _get_expr(context: ContextTypes.DEFAULT_TYPE) -> str:
    return str(context.user_data.get("gcalc_expr") or "")


def _set_expr(context: ContextTypes.DEFAULT_TYPE, expr: str) -> None:
    context.user_data["gcalc_expr"] = expr


def _extract_result_number(text: str) -> str | None:
    """از خروجی تابع calculator عدد را جدا می‌کند."""
    if not text:
        return None
    # خروجی پیشرفته: **۱۲** یا نتیجه: ۱۲
    m = re.search(r"خروجی:\s*\*\*([^*]+)\*\*", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"نتیجه:\s*([^\n]+)", text)
    if m:
        return m.group(1).strip()
    # اگر فقط عدد
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if re.fullmatch(r"[0-9۰-۹.,+\-eE]+", ln.replace(",", "").replace("،", "")):
            return ln
    return None


def _to_english_digits(s: str) -> str:
    return s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


async def start_graphical_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع ماشین‌حساب گرافیکی (از منوی ابزارها)."""
    _set_expr(context, "")
    context.user_data.pop("gcalc_last_result", None)
    text = _display("0")
    msg = update.effective_message
    if msg:
        await msg.reply_text(text, reply_markup=_kb(), parse_mode="Markdown")


async def graphical_calc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دکمه‌های gcalc:…"""
    query = update.callback_query
    if not query or not query.data:
        return
    data = query.data
    if not data.startswith("gcalc:"):
        return

    token = data.split(":", 1)[1]
    expr = _get_expr(context)
    result_show: str | None = None
    error: str | None = None

    try:
        if token == "clr":
            expr = ""
            context.user_data.pop("gcalc_last_result", None)
        elif token == "bs":
            expr = expr[:-1]
        elif token == "eq":
            if not expr.strip():
                error = "عبارتی وارد نشده."
            else:
                out = _eval_expr(expr)
                if out.startswith("❌"):
                    # پیام خطای موتور
                    error = out.split("\n", 1)[0].replace("❌", "").strip() or "خطا در محاسبه"
                else:
                    num = _extract_result_number(out)
                    if num is None:
                        # کل خروجی را نشان بده فشرده
                        result_show = out.replace("\n", " · ")[:120]
                    else:
                        result_show = num
                        context.user_data["gcalc_last_result"] = _to_english_digits(
                            num.replace(",", "").replace("،", "").replace(" ", "")
                        )
                        # برای ادامه محاسبه، نتیجه را به‌عنوان عبارت نگه دار
                        eng = context.user_data["gcalc_last_result"]
                        # ارقام فارسی را انگلیسی کن برای ادامه
                        expr = eng
        elif token == "pm":
            # تغییر علامت کل عبارت یا آخرین عدد
            if not expr:
                expr = "-"
            elif expr.startswith("-") and not any(c in expr[1:] for c in "+-*/^"):
                expr = expr[1:]
            else:
                # آخرین عدد را منفی/مثبت کن
                m = re.search(r"([+\-*/^()]*)([0-9.]+)$", expr)
                if m:
                    prefix, num = m.group(1), m.group(2)
                    if prefix.endswith("-") and (len(prefix) == 1 or prefix[-2] in "+-*/(^"):
                        expr = expr[: -len(num) - 1] + num
                    else:
                        expr = expr[: -len(num)] + "(-" + num + ")"
                else:
                    expr = f"-({expr})"
        elif token == "sqrt":
            expr = f"sqrt({expr})" if expr else "sqrt("
        elif token == "pi":
            expr += "pi"
        elif token == "e":
            expr += "e"
        elif token == "%":
            expr += "%"
        elif token == "copy":
            last = context.user_data.get("gcalc_last_result") or expr
            await query.answer(f"نتیجه: {last}", show_alert=True)
            return
        elif token in set("0123456789.+-*/^()"):
            expr += token
        else:
            await query.answer("دکمه نامعتبر", show_alert=False)
            return
    except Exception as e:
        logger.error("gcalc: %s", e)
        error = "خطای داخلی"

    if len(expr) > 80:
        error = "عبارت خیلی طولانی است — C را بزنید."
        expr = expr[:80]

    _set_expr(context, expr)
    text = _display(expr or "0", result=result_show, error=error)

    try:
        await query.answer()
    except Exception:
        pass
    try:
        await query.edit_message_text(text, reply_markup=_kb(), parse_mode="Markdown")
    except Exception as e:
        # اگر متن یکی باشد تلگرام خطا می‌دهد
        logger.debug("gcalc edit: %s", e)


# سازگاری با نام‌های کوتاه
async def gcalc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await graphical_calc_callback(update, context)
