# Auto-split part 15: shopping_price_history
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
