from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

# Auto-split part 14: _save_history
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
