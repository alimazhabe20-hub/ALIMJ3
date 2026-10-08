"""shopping: filter responsibilities."""
from .shopping_common import *  # noqa: F401,F403
from . import shopping_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _score(result: ProductResult, query: str | list[str]) -> float:
    """امتیاز نرم؛ نتیجه مشابه را حذف نمی‌کند و بهترین query را ملاک می‌گیرد."""
    queries = query if isinstance(query, list) else _query_variants(query)
    if not queries:
        queries = [str(query or "")]

    text = f"{result.title} {result.match_hint}".lower()
    twords = {x.lower() for x in re.findall(r"[\wآ-ی]{2,}", text)}
    best = 0.0
    for q in queries:
        qwords = {x.lower() for x in re.findall(r"[\wآ-ی]{2,}", q)}
        if not qwords:
            continue
        overlap = len(qwords & twords) / max(1, len(qwords))
        # تطابق عبارت کامل امتیاز زیادی می‌گیرد، اما شرط نیست.
        phrase_bonus = 18 if q.lower() in text else 0
        best = max(best, overlap * 100 + phrase_bonus)

    score = best
    if result.price is not None:
        score += 12
    if result.seller:
        score += 3
    if result.source == "instagram":
        score += 4
    if result.source in ("torob", "digikala", "emalls"):
        score += 6
    return score

def _shopping_digits(text: str) -> str:
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return str(text or "").translate(table)

def _shopping_budget(text: str) -> int:
    import re
    t = _shopping_digits(text).replace(",", "").replace("٬", "")
    patterns = [
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d+(?:\.\d+)?)\s*(?:میلیون|م)\b",
        r"(\d+(?:\.\d+)?)\s*(?:میلیون|م)\s*(?:تومان|تومن)?",
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d{5,})\s*(?:تومان|تومن)?",
    ]
    for pat in patterns:
        m = re.search(pat, t, re.I)
        if not m: continue
        try:
            n=float(m.group(1))
            if "میلیون" in m.group(0) or re.search(r"\d+(?:\.\d+)?\s*م\b",m.group(0)): n*=1_000_000
            if n>=100_000: return int(n)
        except Exception: pass
    return 0

def _shopping_is_phone(text: str) -> bool:
    import re
    return bool(re.search(r"گوشی|موبایل|اسمارت\s*فون|smart\s*phone|iphone|آیفون|سامسونگ|شیائومی|پوکو|honor|oneplus|pixel", str(text or ""), re.I))

def _shopping_wants_foreign(text: str) -> bool:
    import re
    q = str(text or "").strip().lower()
    patterns = (
        r"سایت[‌ ]*ها?ی?\s*(?:خارجی|بین.?المللی|جهانی)",
        r"منابع[‌ ]*(?:خارجی|بین.?المللی|جهانی)",
        r"بازار[‌ ]*(?:خارجی|جهانی|بین.?المللی)",
        r"(?:خارجی|بین.?المللی|جهانی)\s*(?:هم|نیز)?\s*(?:بگرد|جستجو|بررسی|چک|پیدا)",
        r"(?:amazon|آمازون|ebay|ایبی|aliexpress|علی.?اکسپرس|walmart|best\s*buy|etsy|newegg|noon|temu|shein)",
        r"(?:سایت|فروشگاه)\s+(?:خارج|جهان|بین.?الملل)",
    )
    return any(re.search(pat, q, re.I) for pat in patterns)

def _shopping_iran_only_query(query: str) -> str:
    return f"{str(query or '').strip()} ایران تومان خرید فروشگاه"

def _save_history(results: list[ProductResult]) -> None:
    if not results:
        return
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT,
                title TEXT,
                source TEXT,
                url TEXT,
                price INTEGER,
                captured_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        for x in results:
            if x.price is None:
                continue
            key = hashlib.sha1(
                re.sub(r"\s+", " ", x.title.lower()).encode("utf-8", "ignore")
            ).hexdigest()[:24]
            c.execute(
                "INSERT INTO shopping_price_history(product_key,title,source,url,price) VALUES(?,?,?,?,?)",
                (key, x.title[:220], x.source, x.url[:1000], int(x.price)),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.debug("shopping history save failed: %s", exc)

def shopping_price_history(query: str = "", days: int = 30, user_id: int = 0) -> str:
    query = (query or "").strip()
    if not query:
        return "نام محصول برای تاریخچه قیمت مشخص نیست."
    try:
        from bot.database import get_db_connection

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shopping_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_key TEXT,
                title TEXT,
                source TEXT,
                url TEXT,
                price INTEGER,
                captured_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        words = [w for w in re.findall(r"[\wآ-ی]{3,}", query.lower())][:8]
        rows = c.execute(
            "SELECT title,source,price,captured_at,url FROM shopping_price_history ORDER BY id DESC LIMIT 1200"
        ).fetchall()
        conn.close()
        matched = []
        for row in rows:
            title = str(row[0] or "").lower()
            if not words or sum(w in title for w in words) >= max(1, len(words) // 2):
                matched.append(row)
        if not matched:
            return "برای این محصول هنوز تاریخچه قیمتی از جستجوهای قبلی ربات ثبت نشده است."
        prices = [int(r[2]) for r in matched if r[2] is not None]
        lines = [
            f"📈 تاریخچه مشاهده‌شده قیمت برای «{query}»",
            f"تعداد مشاهدات: {len(prices)}",
        ]
        if prices:
            lines.append(
                f"کمترین: {min(prices):,} تومان | بیشترین: {max(prices):,} تومان | میانگین: {sum(prices)/len(prices):,.0f} تومان"
            )
        for r in matched[:12]:
            src = SOURCES.get(r[1], SOURCES["general"])["label"]
            lines.append(f"• {r[3]} | {src} | {int(r[2]):,} تومان")
        return "\n".join(lines)
    except Exception as exc:
        return f"تاریخچه قیمت در دسترس نیست: {exc}"
