"""finance_core: currency responsibilities."""
from .finance_core_common import *  # noqa: F401,F403
from . import finance_core_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def rial_toman(amount: float, to_toman: bool = True) -> str:
    if to_toman:
        return f"💵 {pn(f'{amount:,.0f}')} ریال = **{pn(f'{amount/10:,.0f}')} تومان**"
    return f"💵 {pn(f'{amount:,.0f}')} تومان = **{pn(f'{amount*10:,.0f}')} ریال**"

async def convert_currency(amount: float, from_cur: str, to_cur: str = "") -> str:
    """تبدیل ارز / کریپتو هوشمند — پشتیبانی گسترده + تبدیل دوطرفه"""
    from_cur = (from_cur or "").lower().strip().replace(" ", "").replace("‌", "")
    to_cur = (to_cur or "").lower().strip().replace(" ", "").replace("‌", "")

    from_cur = _FA_CURRENCY.get(from_cur, from_cur)
    to_cur = _FA_CURRENCY.get(to_cur, to_cur)

    # کریپتو → کریپتو یا کریپتو → فیات
    if from_cur in SYMBOL_TO_ID or re.match(r"^[a-zA-Z0-9]{2,15}$", from_cur):
        if to_cur and to_cur not in ("usd", "دلار", "toman", "تومان", "rial", "ریال", ""):
            id1 = await resolve_coin_id(from_cur)
            id2 = await resolve_coin_id(to_cur)
            if id1 and id2:
                prices = await _crypto_simple([id1, id2])
                p1 = prices.get(id1, {}).get("usd")
                p2 = prices.get(id2, {}).get("usd")
                if p1 and p2 and p2 > 0:
                    result = amount * p1 / p2
                    usd_rial = await _get_usd_rial() or 0
                    total_usd = amount * p1
                    total_toman = total_usd * (usd_rial / 10) if usd_rial else 0
                    return (
                        f"🔄 تبدیل کریپتو به کریپتو\n"
                        f"────────────────────\n"
                        f"{pn(amount)} {from_cur.upper()} = **{result:,.8f} {to_cur.upper()}**\n"
                        f"≈ ${total_usd:,.4f}\n"
                        + (f"≈ {pn(f'{total_toman:,.0f}')} تومان\n" if total_toman else "")
                        + f"────────────────────\n"
                        f"قیمت {from_cur.upper()}: ${p1:,.6f}\n"
                        f"قیمت {to_cur.upper()}: ${p2:,.6f}"
                    )
        return await convert_crypto(amount, from_cur)

    d = await _get_usd_rial()

    if from_cur in ("rial", "ریال", "irr") and to_cur in ("toman", "تومان", "tmn", ""):
        return rial_toman(amount, True)
    if from_cur in ("toman", "تومان", "tmn") and to_cur in ("rial", "ریال", "irr"):
        return rial_toman(amount, False)

    if d:
        if from_cur in ("usd",) and to_cur in ("rial", "toman", ""):
            rial = amount * d
            return (
                f"💵 تبدیل دلار\n"
                f"────────────────────\n"
                f"${amount:,.2f} = **{pn(f'{rial:,.0f}')} ریال**\n"
                f"≈ **{pn(f'{rial/10:,.0f}')} تومان**\n"
                f"نرخ: {pn(f'{d/10:,.0f}')} تومان"
            )
        if from_cur in ("toman",) and to_cur in ("usd", "دلار", ""):
            usd = amount * 10 / d
            return (
                f"🇮🇷 تبدیل تومان → دلار\n"
                f"────────────────────\n"
                f"{pn(f'{amount:,.0f}')} تومان = **${usd:,.4f}**\n"
                f"نرخ: {pn(f'{d/10:,.0f}')} تومان"
            )
        if from_cur in ("rial",) and to_cur in ("usd",):
            return f"{pn(f'{amount:,.0f}')} ریال = **${amount / d:,.4f}**"

    # اگر from کریپتو-like بود
    if re.match(r"^[a-zA-Z]{2,15}$", from_cur):
        return await convert_crypto(amount, from_cur)

    return (
        "❌ فرمت درست:\n"
        "• `100 دلار` یا `100 usd`\n"
        "• `50000 تومان دلار`\n"
        "• `20 ton` یا `1.5 btc` یا `100 pepe`\n"
        "• `1 btc eth` (تبدیل بین دو کریپتو)\n"
        "• `1000000 ریال تومان`\n"
        "• `50 تتر` یا `۲ بیتکوین`"
    )

def profit_loss(buy: float, sell: float, qty: float = 1.0) -> str:
    if buy <= 0:
        return "❌ قیمت خرید باید بزرگ‌تر از صفر باشد."
    gross = (sell - buy) * qty
    pct = (sell - buy) / buy * 100
    emoji = "📈" if gross >= 0 else "📉"
    status = "سود" if gross >= 0 else "ضرر"
    fee_est = (buy + sell) * qty * 0.005 / 2
    net = gross - fee_est
    return (
        f"{emoji} **محاسبه سود / ضرر**\n\n"
        f"قیمت خرید: {pn(f'{buy:,.0f}')}\n"
        f"قیمت فروش: {pn(f'{sell:,.0f}')}\n"
        f"تعداد / حجم: {pn(qty)}\n\n"
        f"**{status} ناخالص:** {pn(f'{abs(gross):,.0f}')}\n"
        f"**درصد:** {pct:+.2f}%\n"
        f"کارمزد تقریبی (۰.۵٪): {pn(f'{fee_est:,.0f}')}\n"
        f"**{status} تقریبی خالص:** {pn(f'{abs(net):,.0f}')}\n\n"
        f"{'✅ معامله در سود است.' if net >= 0 else '⚠️ معامله در ضرر است.'}"
    )

def parse_profit(text: str) -> tuple[float, float, float] | None:
    t = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    nums = re.findall(r"[\d]+(?:\.\d+)?", t)
    nums = [float(n) for n in nums]
    if len(nums) >= 2:
        return nums[0], nums[1], nums[2] if len(nums) > 2 else 1.0
    return None

def parse_currency_input(text: str) -> tuple[float, str, str] | None:
    """پارس هوشمند: عدد + ارز مبدا + ارز مقصد (فارسی/انگلیسی)"""
    if not text:
        return None
    t = text.strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    t = t.replace("،", "").replace(",", "")
    t_lower = t.lower().replace("‌", " ").replace("  ", " ").strip()

    # الگوهای رایج
    # 1) 20 ton / 1.5 btc usdt / 100 دلار تومان
    m = re.match(
        r"^([\d.]+)\s*([a-zA-Zآ-ی]+)?\s*(?:به|to|=|→|->)?\s*([a-zA-Zآ-ی]+)?\s*$",
        t_lower,
    )
    if m:
        amount = float(m.group(1))
        a = (m.group(2) or "").strip()
        b = (m.group(3) or "").strip()
        # نرمال‌سازی فارسی
        a = _FA_CURRENCY.get(a, a)
        b = _FA_CURRENCY.get(b, b)
        return amount, a, b

    # 2) فقط عدد و یک کلمه چسبیده: 100دلار
    m2 = re.match(r"^([\d.]+)\s*([a-zA-Zآ-ی]+)\s*$", t_lower)
    if m2:
        amount = float(m2.group(1))
        a = _FA_CURRENCY.get(m2.group(2).strip(), m2.group(2).strip())
        return amount, a, ""

    return None
