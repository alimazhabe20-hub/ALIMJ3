"""هوش خرید بازار: جستجوی گسترده چندفروشگاهی + اینستاگرام + کل وب.

این ماژول به API خصوصی فروشگاه‌ها وابسته نیست. از موتور جستجو (DuckDuckGo)
برای فروشگاه‌های هدف، اینستاگرام و کل اینترنت استفاده می‌کند و سپس صفحه را
برای داده‌های ساختاریافته (JSON-LD Product/Offer) و الگوهای قیمت فارسی می‌خواند.
"""

# BEGIN MERGED LEGACY PART: shopping_parts/part_001_ProductResult.py
from dataclasses import dataclass

# Auto-split part 1: ProductResult
@dataclass
class ProductResult:
    source: str
    title: str
    url: str
    price: int | None = None
    old_price: int | None = None
    currency: str = "تومان"
    seller: str = ""
    availability: str = ""
    image: str = ""
    match_hint: str = ""

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_002__norm_digits.py
# Auto-split part 2: _norm_digits
def _norm_digits(s: str) -> str:
    return str(s).translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_003__price.py
from typing import Any

# Auto-split part 3: _price
def _price(value: Any) -> int | None:
    if value is None:
        return None
    s = _norm_digits(str(value)).replace("٬", "").replace(",", "").replace(" ", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        n = float(m.group())
    except Exception:
        return None
    return int(n)

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_004__currency_and_price.py
from typing import Any

# Auto-split part 4: _currency_and_price
def _currency_and_price(raw: Any, currency: str = "") -> tuple[int | None, str]:
    p = _price(raw)
    cur = (currency or "").lower()
    if p is not None and ("rial" in cur or "ریال" in cur):
        p = p // 10
        return p, "تومان"
    if p is not None:
        return p, "تومان"
    return None, "تومان"

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_005__domain.py
# Auto-split part 5: _domain
def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_006__source_for_url.py
# Auto-split part 6: _source_for_url
def _source_for_url(url: str) -> str:
    d = _domain(url)
    for key, cfg in SOURCES.items():
        if any(x in d for x in cfg["domains"]):
            return key
    return "general"

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_007__clean_title.py
# Auto-split part 7: _clean_title
def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    return title[:240]

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_008__search.py
# Auto-split part 8: _search
async def _search(query: str, domain: str = "", limit: int = 8, extra: str = "") -> list[dict[str, str]]:
    """جستجوی سریع چندموتوره؛ اولین منبع معتبر برگردانده می‌شود تا Shopping روی Render timeout نشود."""
    import asyncio
    from urllib.parse import quote_plus

    parts = []
    if domain:
        parts.append(f"site:{domain}")
    parts.append(query)
    if extra:
        parts.append(extra)
    q = " ".join(parts).strip()

    key = f"search:v4:{q}:{limit}"
    now = time.time()
    cached = CACHE.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        try:
            return json.loads(cached[1])
        except Exception:
            pass

    headers = {"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8"}

    def _google_links(soup):
        out = []
        for a in soup.select("a"):
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            if not href.startswith("http") or not title:
                continue
            low = href.lower()
            if any(x in low for x in ("google.com", "googleusercontent.com", "gstatic.com")):
                continue
            out.append({"url": href, "title": title, "snippet": ""})
            if len(out) >= limit:
                break
        return out

    def _bing_links(soup):
        out = []
        for item in soup.select("li.b_algo")[:limit]:
            a = item.select_one("h2 a")
            if not a:
                continue
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            sn = item.select_one(".b_caption p")
            snippet = sn.get_text(" ", strip=True) if sn else ""
            if href and title:
                out.append({"url": href, "title": title, "snippet": snippet})
        return out

    def _brave_links(soup):
        out = []
        for a in soup.select("a"):
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            if not href.startswith("http") or not title:
                continue
            if "search.brave.com" in href.lower():
                continue
            out.append({"url": href, "title": title, "snippet": ""})
            if len(out) >= limit:
                break
        return out

    async def _one(client, name, method, url, parser, data=None):
        try:
            if method == "post":
                r = await asyncio.wait_for(client.post(url, data=data), timeout=5.5)
            else:
                r = await asyncio.wait_for(client.get(url), timeout=5.5)
            if r.status_code >= 400:
                return name, []
            return name, parser(BeautifulSoup(r.text, "html.parser"))
        except Exception as exc:
            logger.debug("shopping %s failed for %s: %s", name, q, exc)
            return name, []

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            engines = [
                ("ddg", "post", SEARCH_URL, lambda soup: [
                    {"url": a.get("href") or "", "title": _clean_title(a.get_text(" ", strip=True)),
                     "snippet": (a.find_parent("div", class_="result").select_one(".result__snippet").get_text(" ", strip=True)
                                 if a.find_parent("div", class_="result") and a.find_parent("div", class_="result").select_one(".result__snippet") else "")}
                    for a in soup.select("a.result__a")[:limit]
                    if a.get("href") and a.get_text(" ", strip=True)
                ], {"q": q}),
                ("google", "get", f"https://www.google.com/search?hl=en&q={quote_plus(q)}", _google_links, None),
                ("bing", "get", f"https://www.bing.com/search?q={quote_plus(q)}", _bing_links, None),
                ("brave", "get", f"https://search.brave.com/search?q={quote_plus(q)}", _brave_links, None),
            ]
            tasks = [asyncio.create_task(_one(client, *e)) for e in engines]
            pending = set(tasks)
            out = []
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        name, candidate = task.result()
                    except Exception:
                        continue
                    if candidate:
                        out = candidate[:limit]
                        logger.info("shopping search engine=%s query=%s results=%d", name, q, len(out))
                        for other in pending:
                            other.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        CACHE[key] = (now, json.dumps(out, ensure_ascii=False))
                        return out
            CACHE[key] = (now, json.dumps([], ensure_ascii=False))
            return []
    except Exception as exc:
        logger.debug("shopping search failed for %s: %s", q, exc)
        return []

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_009__extract_jsonld.py
from bs4 import BeautifulSoup
from typing import Any

# Auto-split part 9: _extract_jsonld
def _extract_jsonld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(tag.string or tag.get_text())
        except Exception:
            continue
        objs = obj if isinstance(obj, list) else [obj]
        for x in objs:
            if isinstance(x, dict):
                if x.get("@type") == "@graph" and isinstance(x.get("@graph"), list):
                    found.extend(y for y in x["@graph"] if isinstance(y, dict))
                else:
                    found.append(x)
    return found

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_010__from_product.py
from typing import Any

# Auto-split part 10: _from_product
def _from_product(obj: dict[str, Any]) -> tuple[int | None, int | None, str, str, str, str]:
    offers = obj.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    price, cur = _currency_and_price(
        offers.get("price") or offers.get("lowPrice"),
        offers.get("priceCurrency", ""),
    )
    old = _price(offers.get("highPrice") or offers.get("price"))
    seller = offers.get("seller")
    if isinstance(seller, dict):
        seller = seller.get("name") or ""
    availability = str(offers.get("availability") or "").split("/")[-1]
    image = obj.get("image") or ""
    if isinstance(image, list):
        image = image[0] if image else ""
    return price, old, str(seller or ""), availability, str(image or ""), cur

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_011__inspect.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

# Auto-split part 11: _inspect
async def _inspect(url: str, title: str, snippet: str) -> ProductResult:
    result = ProductResult(
        source=_source_for_url(url),
        title=title,
        url=url,
        match_hint=snippet[:220],
    )
    # برای اینستاگرام معمولاً قیمت مستقیم در صفحه عمومی نیست؛ فقط لینک و عنوان نگه می‌داریم
    if result.source == "instagram":
        result.seller = "صفحه اینستاگرامی"
        return result

    try:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return result
        soup = BeautifulSoup(r.text, "html.parser")

        # JSON-LD اول
        for obj in _extract_jsonld(soup):
            typ = obj.get("@type")
            if typ == "Product" or (isinstance(typ, list) and "Product" in typ):
                p, old, seller, avail, image, cur = _from_product(obj)
                if p is not None:
                    result.price = p
                if old is not None and (result.price is None or old > result.price):
                    result.old_price = old
                result.seller = seller or result.seller
                result.availability = avail
                result.image = image
                result.currency = cur
                if result.price is not None:
                    break

        # Meta tags
        if result.price is None:
            meta = soup.select_one(
                'meta[property="product:price:amount"], meta[itemprop="price"], '
                'meta[property="og:price:amount"]'
            )
            if meta:
                result.price, result.currency = _currency_and_price(
                    meta.get("content") or meta.get("value"),
                    meta.get("contentCurrency", "") or "تومان",
                )

        # الگوهای متنی فارسی
        if result.price is None:
            text = soup.get_text(" ", strip=True)
            patterns = [
                r"([0-9۰-۹][0-9۰-۹,٬\.]{2,})\s*(?:تومان|تومن|ت\.?م)",
                r"(?:قیمت|Price|قیمت نهایی|قیمت فروش)\s*[:：]?\s*([0-9۰-۹][0-9۰-۹,٬\.]{2,})",
                r"([0-9۰-۹]{1,3}(?:[٬,][0-9۰-۹]{3})+)\s*(?:تومان|تومن)",
            ]
            for pat in patterns:
                m = re.search(pat, text, re.I)
                if m:
                    result.price, result.currency = _currency_and_price(m.group(1), "تومان")
                    break

        # عنوان بهتر از og:title
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title and og_title.get("content"):
            clean = _clean_title(og_title["content"])
            if len(clean) > 8:
                result.title = clean

    except Exception as exc:
        logger.debug("shopping inspect failed %s: %s", url, exc)
    return result

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_012__query_variants.py
# Auto-split part 12: _query_variants
def _query_variants(query: str) -> list[str]:
    """ساخت چند جستجوی کوتاه‌تر تا نتیجه به تطابق لفظ‌به‌لفظ وابسته نباشد."""
    q = re.sub(r"\s+", " ", (query or "").strip())
    if not q:
        return []

    variants: list[str] = [q]
    # کلمات کم‌ارزش در توصیف‌های بینایی را حذف می‌کنیم.
    stop = {
        "یک", "عدد", "نوع", "مدل", "شکل", "طرح", "دارای", "با", "و", "از",
        "برای", "در", "روی", "رنگ", "مناسب", "دکوری", "دکوراتیو", "خاص",
        "برجستگی", "برجسته", "تصویر", "عکس",
    }
    words = [w for w in re.findall(r"[\wآ-ی]{2,}", q.lower()) if w not in stop]
    if words:
        variants.append(" ".join(words))
    if len(words) >= 4:
        # دو نسخه کوتاه برای موتور جستجو؛ یکی ابتدای توصیف و یکی انتهای آن.
        variants.append(" ".join(words[:4]))
        variants.append(" ".join(words[-4:]))
    # چند جایگزین رایج برای توصیف‌های فارسی/بازاری.
    synonym_groups = [
        ("چوب پنبه ای", "چوب پنبه"),
        ("چوب‌پنبه‌ای", "چوب پنبه"),
        ("چوبی", "درب چوبی"),
        ("شیشه ای", "شیشه"),
        ("شیشه‌ای", "شیشه"),
    ]
    for a, b in synonym_groups:
        if a in q.lower():
            variants.append(q.lower().replace(a, b))

    out: list[str] = []
    seen: set[str] = set()
    for v in variants:
        v = re.sub(r"\s+", " ", v).strip()
        if len(v) >= 4 and v not in seen:
            seen.add(v)
            out.append(v)
    return out[:6]

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_013__score.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

# Auto-split part 13: _score
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_014__save_history.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_015_shopping_price_history.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: shopping_parts/part_016_search_shopping.py
try:
    import logging as _shopping_logging
    logger = _shopping_logging.getLogger('rooze_ziba')
except Exception:
    logger = None

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

def _shopping_query_variants(query: str, budget: int = 0) -> list[str]:
    q = str(query or "").strip()
    out = [q]
    if budget:
        b = f"{budget:,}"
        # Generic budget requests must stay generic.  The old implementation
        # accidentally converted every budget query into a phone search.
        if _shopping_is_phone(q):
            out += [
                f"بهترین گوشی تا {b} تومان",
                f"گوشی موبایل تا {b} تومان",
                f"گوشی خوب تا {b} تومان قیمت خرید",
                f"گوشی تا {b} تومان ترب",
                f"گوشی تا {b} تومان دیجی کالا",
                f"سامسونگ تا {b} تومان گوشی",
                f"شیائومی تا {b} تومان گوشی",
                f"پوکو تا {b} تومان گوشی",
                f"آنر تا {b} تومان گوشی",
                f"آیفون تا {b} تومان گوشی",
            ]
        else:
            out += [
                f"وسایل کاربردی تا {b} تومان برای خرید",
                f"محصولات کاربردی تا {b} تومان",
                f"بهترین وسیله کاربردی تا {b} تومان",
                f"لوازم کاربردی تا {b} تومان خرید",
                f"پیشنهاد خرید تا {b} تومان",
                f"محصول پرفروش تا {b} تومان",
                f"لوازم دیجیتال کاربردی تا {b} تومان",
                f"لوازم خانه کاربردی تا {b} تومان",
            ]
    seen = set()
    result = []
    for x in out:
        x = " ".join(x.split())
        if x and x not in seen:
            seen.add(x)
            result.append(x)
    return result


# سایت‌های شناخته‌شده برای جستجوی مستقیم؛ در صورت گفتن «برو سایت X»
# فقط همان دامنه هدف می‌شود. برای سایت‌های ناشناخته نیز از دامنه استخراج‌شده از متن استفاده می‌کنیم.
_SITE_ALIASES = {
    "دیجی کالا": "digikala.com", "دیجی‌کالا": "digikala.com", "digikala": "digikala.com",
    "ترب": "torob.com", "torob": "torob.com",
    "ایمالز": "emalls.ir", "emalls": "emalls.ir",
    "تکنولایف": "technolife.ir", "technolایف": "technolife.ir", "technolife": "technolife.ir",
    "اسنپ شاپ": "snapp.shop", "اسنپ‌شاپ": "snapp.shop", "snappshop": "snapp.shop",
    "باسلام": "basalam.com", "basalam": "basalam.com",
    "دیجی استایل": "digistyle.com", "دیجی‌استایل": "digistyle.com", "digistyle": "digistyle.com",
    "موبایل دات آی آر": "mobile.ir", "mobile.ir": "mobile.ir",
    "آمازون": "amazon.com", "amazon": "amazon.com",
    "ebay": "ebay.com", "ایبی": "ebay.com",
    "علی اکسپرس": "aliexpress.com", "علی‌اکسپرس": "aliexpress.com", "aliexpress": "aliexpress.com",
    "walmart": "walmart.com", "وال مارت": "walmart.com",
    "bestbuy": "bestbuy.com", "best buy": "bestbuy.com",
    "etsy": "etsy.com", "اتسی": "etsy.com",
    "newegg": "newegg.com",
    "noon": "noon.com", "نون": "noon.com",
    "temu": "temu.com", "تیمو": "temu.com",
    "shein": "shein.com", "شین": "shein.com",
    "nike": "nike.com", "نایکی": "nike.com",
    "adidas": "adidas.com", "آدیداس": "adidas.com",
}

def _explicit_shopping_site(text: str) -> str:
    import re
    q = str(text or "").strip().lower()
    # نام‌های متداول را اول بررسی کن.
    for alias, domain in sorted(_SITE_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in q:
            return domain
    # مثال: «برو سایت example.com و ...» یا URL مستقیم
    m = re.search(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})(?:/[^\s]*)?", q)
    if m:
        return m.group(1).lower().rstrip('.')
    return ""

def _strip_site_command(text: str) -> str:
    import re
    q = str(text or "").strip()
    q = re.sub(r"(?:برو|برو تو|برو داخل|وارد شو به|داخل|در|توی|تو)\s+(?:سایت\s+)?(?:دیجی کالا|دیجی‌کالا|ترب|ایمالز|تکنولایف|اسنپ شاپ|اسنپ‌شاپ|باسلام|آمازون|amazon|ebay|ایبی|علی اکسپرس|علی‌اکسپرس|walmart|best ?buy|etsy|newegg|noon|temu|shein)\s*", "", q, flags=re.I)
    q = re.sub(r"(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?", "", q, flags=re.I)
    q = re.sub(r"(?:ببین|بررسی کن|پیدا کن|جستجو کن|داره|موجوده|موجود هست|هست؟)", "", q, flags=re.I)
    return " ".join(q.split()).strip(" ؟?!،,") or str(text or "").strip()


async def search_shopping(
    query: str = "",
    source: str = "all",
    max_results: int = 10,
    min_price: int = 0,
    max_price: int = 0,
    user_id: int = 0,
) -> str:
    """جستجوی هوشمند و گسترده قیمت محصول در فروشگاه‌های ایرانی + اینستاگرام + کل وب."""
    query = (query or "").strip()
    if not query:
        return "عبارت محصول برای جستجو مشخص نیست."

    max_results = max(4, min(int(max_results or 10), 22))
    source = (source or "all").lower().strip()
    target_domain = _explicit_shopping_site(query)
    target_query = _strip_site_command(query) if target_domain else query
    budget = _shopping_budget(query)
    foreign_requested = _shopping_wants_foreign(query)
    if budget and not max_price:
        max_price = budget

    # اگر کاربر سایت مشخصی گفته باشد، جستجو فقط روی همان سایت انجام می‌شود.
    if target_domain:
        selected = []
        variants = _shopping_query_variants(target_query, budget) or [target_query]
        tasks = [_search(v, domain=target_domain, limit=max(8, max_results + 2)) for v in variants[:8]]
        batches = await asyncio.gather(*tasks, return_exceptions=True)
    # انتخاب منابع
    elif source in ("all", "همه", "تمام", "everywhere", "web"):
        preferred = ["torob", "digikala", "snappshop", "technolife", "mobile", "emalls", "basalam", "digistyle", "modiseh", "instagram", "general"]
        selected = [s for s in preferred if s in SOURCES]
    else:
        selected = [s for s in source.replace(",", " ").split() if s in SOURCES]
        if not selected:
            selected = list(SOURCES.keys())
    if not target_domain:
        if "general" not in selected:
            selected.append("general")
        if "instagram" not in selected:
            selected.append("instagram")

    # چند query مستقل می‌سازیم؛ تطابق دقیق دیگر شرط موفقیت نیست.
    if not target_domain:
        variants = _shopping_query_variants(query, budget) or [query]
        tasks = []
        for key in selected:
            cfg = SOURCES[key]
            domain = cfg["domains"][0] if cfg["domains"] else ""
            limit = max(5, max_results // max(1, len(selected)) + 3)

            # برای هر منبع فقط چند query قوی‌تر را اجرا می‌کنیم تا روی Render فشار ایجاد نشود.
            local_variants = variants[:2] if key not in ("general", "instagram") else variants[:3]
            for variant in local_variants:
                if key == "instagram":
                    tasks.append(
                        _search(f"{variant} {' OR '.join(INSTA_KEYWORDS[:3])}",
                                domain="instagram.com", limit=limit + 1)
                    )
                elif key == "general":
                    tasks.append(_search(variant if foreign_requested else _shopping_iran_only_query(variant), domain="", limit=limit + 2))
                else:
                    tasks.append(_search(variant, domain=domain, limit=limit))
    if not target_domain:
        batches = await asyncio.gather(*tasks, return_exceptions=True)

    # جمع‌آوری لینک‌های یکتا
    links: dict[str, dict[str, str]] = {}
    for batch in batches:
        if isinstance(batch, Exception):
            continue
        for item in batch:
            url = (item.get("url") or "").strip()
            if not url or url in links:
                continue
            # فیلتر لینک‌های بی‌ربط رایج
            low = url.lower()
            if any(
                x in low
                for x in (
                    "twitter.com",
                    "x.com",
                    "facebook.com",
                    "t.me/",
                    "telegram.",
                    "wikipedia.org",
                    "aparat.com",
                )
            ):
                continue
            links[url] = item

    # بازرسی صفحات (حداکثر ۲۶ تا برای سرعت)
    to_inspect = list(links.values())[:12]
    inspect_tasks = [
        _inspect(x["url"], x["title"], x.get("snippet", "")) for x in to_inspect
    ]
    results = await asyncio.gather(*inspect_tasks, return_exceptions=True)

    clean: list[ProductResult] = []
    for x in results:
        if not isinstance(x, ProductResult):
            continue
        if min_price and (x.price is None or x.price < min_price):
            continue
        if max_price and x.price is not None and x.price > max_price:
            continue
        clean.append(x)

    clean.sort(key=lambda x: (-_score(x, variants), x.price is None, x.price or 10**18))
    clean = clean[:max_results]
    _save_history(clean)

    if not clean:
        # fallback به لینک‌های خام
        fallback = list(links.values())[:max_results]
        if not fallback:
            if budget and _shopping_is_phone(query):
                return f"برای بودجه حدود {budget:,} تومان جستجوی گوشی انجام شد، اما نتیجه قابل‌تأیید از منابع زنده برنگشت؛ قیمت حدسی ارائه نمی‌کنم."
            return f"برای «{query}» نتیجه‌ای در فروشگاه‌ها، اینستاگرام و وب پیدا نشد."
        lines = [
            f"🔎 نتایج جستجو برای «{query}» (قیمت مستقیم استخراج نشد):",
            "لینک‌های مرتبط از فروشگاه‌ها و اینستاگرام:",
        ]
        for i, x in enumerate(fallback, 1):
            src = _source_for_url(x["url"])
            label = SOURCES.get(src, SOURCES["general"])["label"]
            lines.append(f"\n{i}. {x['title']}\n🏪 {label}\n🔗 {x['url']}")
        return "\n".join(lines)

    # ساخت خروجی نهایی
    from datetime import datetime, timezone
    searched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"🛒 **نتیجه جستجوی گسترده برای «{query}»**",
        "",
        "جستجو در فروشگاه‌های ایرانی + اینستاگرام + کل وب انجام شد.",
        f"زمان جستجو: {searched_at}",
        "قیمت فقط وقتی نمایش داده می‌شود که از صفحه نتیجه استخراج شده باشد؛ قیمت حدسی ارائه نمی‌شود.",
        "قبل از خرید، موجودی و قیمت نهایی همان صفحه را دوباره بررسی کنید.",
        "",
    ]

    for i, x in enumerate(clean, 1):
        source_label = SOURCES.get(x.source, SOURCES["general"])["label"]
        if x.price is not None:
            price = f"{x.price:,} تومان"
        else:
            price = "قیمت در صفحه مشخص نشد" if x.source != "instagram" else "قیمت در اینستا (معمولاً در پست/دایرکت)"

        extra = []
        if x.old_price and x.old_price > (x.price or 0):
            extra.append(f"قبلی: {x.old_price:,}")
        if x.seller:
            extra.append(f"فروشنده: {x.seller}")
        if x.availability:
            extra.append(f"وضعیت: {x.availability}")

        lines.append(f"{i}. **{x.title}**")
        lines.append(f"🏪 {source_label} | 💰 {price}")
        if extra:
            lines.append(" · ".join(extra))
        lines.append(f"🔗 {x.url}")
        lines.append("")

    # ارزان‌ترین (فقط بین آن‌هایی که قیمت دارند)
    priced = [x for x in clean if x.price is not None]
    if priced:
        cheapest = min(priced, key=lambda x: x.price or 10**18)
        lines.append(
            f"🏆 ارزان‌ترین نتیجه پیدا‌شده: **{cheapest.price:,} تومان** — "
            f"{SOURCES.get(cheapest.source, SOURCES['general'])['label']}"
        )

    # آمار منابع
    sources_count: dict[str, int] = {}
    for x in clean:
        sources_count[x.source] = sources_count.get(x.source, 0) + 1
    if sources_count:
        src_summary = " · ".join(
            f"{SOURCES.get(k, SOURCES['general'])['label']}: {v}"
            for k, v in sorted(sources_count.items(), key=lambda i: -i[1])
        )
        lines.append(f"\n📊 منابع: {src_summary}")

    return "\n".join(lines)

# BEGIN MERGED LEGACY PART: shopping_parts/part_016_search_shopping_live.py
"""Shopping Engine v3 - live, multi-source, cached, ranked and alert-ready.

Rules:
- Iran is the default market.
- Foreign/global sources are opt-in only.
- AI is never required for shopping results.
- Never invent a price, stock state, seller or URL.
- Prefer direct live catalogs, then search engines as fallback.
"""

import asyncio
import hashlib
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("rooze_ziba")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36 RoozeZiba/5.0"
CACHE_TTL = 180
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_STATS = {"searches": 0, "cache_hits": 0, "direct_ok": 0, "web_ok": 0, "empty": 0, "errors": 0}
_SEARCH_SEM = asyncio.Semaphore(8)

IRAN_SITES = {
    "torob.com": "ترب", "digikala.com": "دیجی‌کالا", "technolife.ir": "تکنولایف",
    "snappshop.ir": "اسنپ‌شاپ", "emalls.ir": "ایمالز", "mobile.ir": "موبایل.ir",
    "basalam.com": "باسلام", "digistyle.com": "دیجی‌استایل", "modiseh.com": "مدیسه",
}
FOREIGN_ALIASES = {
    "amazon": "amazon.com", "آمازون": "amazon.com", "ebay": "ebay.com", "ایبی": "ebay.com",
    "aliexpress": "aliexpress.com", "علی اکسپرس": "aliexpress.com", "علی‌اکسپرس": "aliexpress.com",
    "walmart": "walmart.com", "وال مارت": "walmart.com", "bestbuy": "bestbuy.com", "best buy": "bestbuy.com",
    "etsy": "etsy.com", "اتسی": "etsy.com", "newegg": "newegg.com", "noon": "noon.com", "نون": "noon.com",
    "temu": "temu.com", "تیمو": "temu.com", "shein": "shein.com", "شین": "shein.com",
}
IRAN_ALIASES = {
    "دیجی کالا": "digikala.com", "دیجی‌کالا": "digikala.com", "digikala": "digikala.com",
    "ترب": "torob.com", "torob": "torob.com", "تکنولایف": "technolife.ir", "technolife": "technolife.ir",
    "اسنپ شاپ": "snappshop.ir", "اسنپ‌شاپ": "snappshop.ir", "snappshop": "snappshop.ir",
    "ایمالز": "emalls.ir", "emalls": "emalls.ir", "موبایل دات آی آر": "mobile.ir", "mobile.ir": "mobile.ir",
    "باسلام": "basalam.com", "basalam": "basalam.com", "دیجی استایل": "digistyle.com", "دیجی‌استایل": "digistyle.com",
}
TRUST = {"ترب": 100, "دیجی‌کالا": 98, "تکنولایف": 94, "ایمالز": 92, "اسنپ‌شاپ": 91, "باسلام": 86, "دیجی‌استایل": 88, "مدیسه": 85, "موبایل.ir": 84, "وب": 60}


def _digits(text: str) -> str:
    return str(text or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


def _budget(text: str) -> int:
    t = _digits(text).replace(",", "").replace("٬", "")
    patterns = (
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)*(\d+(?:\.\d+)?)\s*(?:میلیون|م)\b",
        r"(\d+(?:\.\d+)?)\s*(?:میلیون|م)\s*(?:تومان|تومن)?",
        r"(?:بودجه|تا|زیر|حداکثر|حدود|حد)\s*(\d{5,})\s*(?:تومان|تومن)?",
    )
    for pat in patterns:
        m = re.search(pat, t, re.I)
        if m:
            try:
                n = float(m.group(1))
                if "میلیون" in m.group(0) or re.search(r"\d+(?:\.\d+)?\s*م\b", m.group(0)):
                    n *= 1_000_000
                if n >= 100_000:
                    return int(n)
            except Exception:
                pass
    return 0


def _foreign_requested(text: str) -> bool:
    q = str(text or "").lower()
    markers = ("سایت خارجی", "سایت‌های خارجی", "سایت های خارجی", "بازار جهانی", "منابع خارجی", "بین‌المللی", "بین المللی", "خارجی", "amazon", "آمازون", "ebay", "ایبی", "aliexpress", "علی اکسپرس", "walmart", "best buy", "etsy", "newegg", "noon", "temu", "shein")
    return any(x in q for x in markers)


def _explicit_domain(text: str) -> str:
    q = str(text or "").lower()
    for alias, domain in sorted({**IRAN_ALIASES, **FOREIGN_ALIASES}.items(), key=lambda x: -len(x[0])):
        if alias in q:
            return domain
    m = re.search(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9.-]+\.[a-z]{2,})(?:/[^\s]*)?", q)
    return m.group(1).lower().rstrip(".") if m else ""


def _clean_query(text: str) -> str:
    q = str(text or "").strip().replace("ي", "ی").replace("ك", "ک")
    q = re.sub(r"[\u200c\u200f\u200e]", " ", q)
    q = re.sub(r"(?:لطفاً|لطفا|میشه|میخوام|می\s*خوام|برام|برای\s*من|ببین|پیدا\s*کن|پیدا کن|جستجو کن|جستجو|بگرد|خرید|بخر|بخرم|قیمت|نرخ|چنده|چقدر|فروشگاه|فروشنده|لینک|مقایسه|ارزان(?:ترین)?|بهترین|پیشنهاد|موجودی|موجود|چی\s*بخرم|چه\s*بخرم)", " ", q, flags=re.I)
    q = re.sub(r"(?:سایت|فروشگاه)\s+(?:خارجی|های خارجی|های ایرانی|ایرانی)", " ", q, flags=re.I)
    q = re.sub(r"https?://\S+", " ", q)
    q = re.sub(r"\s+", " ", q).strip(" ؟?!،,")
    return q or str(text or "").strip()


def _query_variants(query: str, budget: int) -> list[str]:
    q = _clean_query(query)
    variants = [q]
    if budget:
        variants += [f"{q} تا {budget:,} تومان", f"{q} قیمت خرید", f"{q} فروشگاه"]
    else:
        variants += [f"{q} قیمت", f"{q} خرید", f"{q} فروشگاه"]
    # Keep variants product-specific; never replace a generic product with "وسایل کاربردی".
    out, seen = [], set()
    for x in variants:
        x = " ".join(x.split())
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out[:4]


def _parse_price(value) -> int | None:
    if value is None: return None
    s = _digits(str(value)).replace(",", "").replace("٬", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m: return None
    try:
        n = float(m.group(0)); return int(n) if n > 0 else None
    except Exception: return None


def _price_from_text(text: str) -> int | None:
    patterns = (
        r"([0-9۰-۹]{1,3}(?:[,٬][0-9۰-۹]{3}){1,4})\s*(?:تومان|تومن|ت)\b",
        r"([0-9۰-۹]{5,})\s*(?:تومان|تومن|ت)\b",
        r"(?:قیمت|price|قیمت فروش|قیمت نهایی)\s*[:：]?\s*([0-9۰-۹]{5,})",
    )
    for pat in patterns:
        m = re.search(pat, text or "", re.I)
        if m:
            p = _parse_price(m.group(1))
            if p: return p
    return None


def _tokens(text: str) -> set[str]:
    stop = {"برای", "من", "یک", "یه", "تا", "تومان", "قیمت", "خرید", "مردانه", "زنانه", "مناسب", "بهترین", "ارزان"}
    return {x for x in re.findall(r"[\wآ-ی]{2,}", str(text or "").lower()) if x not in stop}


def _relevance(title: str, query: str) -> float:
    qt = _tokens(query); tt = _tokens(title)
    if not qt: return 0.0
    overlap = len(qt & tt) / len(qt)
    phrase = 25.0 if _clean_query(query).lower() in title.lower() else 0.0
    return overlap * 100 + phrase


def _cache_key(query: str, source: str, max_price: int, foreign: bool) -> str:
    raw = f"{query}|{source}|{max_price}|{foreign}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()


async def _bing_search(query: str, domain: str = "", limit: int = 8) -> list[dict]:
    q = f"site:{domain} {query}" if domain else query
    url = f"https://www.bing.com/search?q={quote_plus(q)}&setlang=fa-IR"
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"}) as client:
                r = await client.get(url)
        if r.status_code >= 400: return []
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for item in soup.select("li.b_algo")[:limit]:
            a = item.select_one("h2 a")
            if not a: continue
            href = (a.get("href") or "").strip(); title = a.get_text(" ", strip=True)
            cap = item.select_one(".b_caption p"); snippet = cap.get_text(" ", strip=True) if cap else ""
            if href.startswith("http") and title: out.append({"url": href, "title": title, "snippet": snippet})
        if out: _STATS["web_ok"] += 1
        return out
    except Exception as exc:
        _STATS["errors"] += 1; logger.debug("shopping bing failed: %s", exc)
        return []


async def _ddg_search(query: str, domain: str = "", limit: int = 8) -> list[dict]:
    q = f"site:{domain} {query}" if domain else query
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7"}) as client:
                r = await client.get("https://html.duckduckgo.com/html/", params={"q": q})
        if r.status_code >= 400: return []
        soup = BeautifulSoup(r.text, "html.parser"); out=[]
        for item in soup.select(".result")[:limit]:
            a=item.select_one(".result__a")
            if not a: continue
            href=(a.get("href") or "").strip(); title=a.get_text(" ",strip=True)
            s=item.select_one(".result__snippet"); snippet=s.get_text(" ",strip=True) if s else ""
            if href.startswith("http") and title: out.append({"url":href,"title":title,"snippet":snippet})
        return out
    except Exception as exc:
        _STATS["errors"] += 1; logger.debug("shopping ddg failed: %s", exc); return []


async def _direct_torob(query: str, max_price: int, limit: int) -> list[dict]:
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(timeout=httpx.Timeout(11.0, connect=5.0), follow_redirects=True, headers={"User-Agent": UA, "Accept":"application/json", "Accept-Language":"fa-IR,fa;q=0.9"}) as client:
                r=await client.get("https://api.torob.com/v4/base-product/search/",params={"q":query,"page":0,"size":min(max(12,limit*2),40),"sort":"price","source":"torob_search"})
        if r.status_code >= 400: return []
        data=r.json(); raw=data.get("results") if isinstance(data,dict) else None
        if not isinstance(raw,list): return []
        out=[]; seen=set()
        for item in raw:
            if not isinstance(item,dict) or item.get("is_adv") is True: continue
            title=str(item.get("name1") or item.get("name") or item.get("title") or "").strip()
            price=_parse_price(item.get("price")) or _parse_price(item.get("min_price"))
            key=str(item.get("random_key") or item.get("prk") or "").strip()
            link=str(item.get("page_url") or item.get("url") or "").strip() or (f"https://torob.com/p/{key}/" if key else "")
            if not title or not price or not link or link in seen or (max_price and price>max_price): continue
            seen.add(link); out.append({"title":title,"url":link,"price":price,"seller":str(item.get("seller_name") or "").strip(),"source":"ترب","availability":str(item.get("availability") or "").strip()})
            if len(out)>=limit: break
        if out: _STATS["direct_ok"] += 1
        return out
    except Exception as exc:
        _STATS["errors"] += 1; logger.debug("torob direct failed: %s", exc); return []


async def _direct_digikala(query: str, max_price: int, limit: int) -> list[dict]:
    try:
        async with _SEARCH_SEM:
            async with httpx.AsyncClient(timeout=httpx.Timeout(11.0, connect=5.0), follow_redirects=True, headers={"User-Agent": UA, "Accept":"application/json", "Accept-Language":"fa-IR,fa;q=0.9"}) as client:
                r=await client.get("https://api.digikala.com/v1/search/",params={"q":query,"page":1})
        if r.status_code>=400: return []
        data=r.json(); raw=((data.get("data") or {}).get("products") if isinstance(data,dict) else None)
        if not isinstance(raw,list): return []
        out=[]
        for item in raw:
            if not isinstance(item,dict): continue
            title=str(item.get("title_fa") or item.get("title") or "").strip()
            rial=_parse_price(item.get("selling_price")) or _parse_price(item.get("price")); price=(rial//10) if rial else None
            pid=item.get("id") or item.get("product_id"); link=str(item.get("url") or "").strip()
            if link.startswith("/"): link="https://www.digikala.com"+link
            if not link and pid: link=f"https://www.digikala.com/product/dkp-{pid}/"
            if not title or not price or not link or (max_price and price>max_price): continue
            out.append({"title":title,"url":link,"price":price,"seller":"دیجی‌کالا","source":"دیجی‌کالا","availability":""})
            if len(out)>=limit: break
        if out: _STATS["direct_ok"] += 1
        return out
    except Exception as exc:
        _STATS["errors"] += 1; logger.debug("digikala direct failed: %s", exc); return []


async def _fetch_source(query: str, domain: str, limit: int, foreign: bool) -> list[dict]:
    batches = await asyncio.gather(_bing_search(query, domain=domain, limit=limit), _ddg_search(query, domain=domain, limit=limit), return_exceptions=True)
    out=[]
    for b in batches:
        if isinstance(b,list):
            for x in b:
                host=urlparse(x.get("url","")).netloc.lower().replace("www.","")
                x["source"]=IRAN_SITES.get(host, host if foreign else "وب")
                x["price"]=_price_from_text((x.get("title") or "")+" "+(x.get("snippet") or ""))
                out.append(x)
    return out


def _save_history_rows(rows: list[dict]) -> None:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); c=conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS shopping_price_history (id INTEGER PRIMARY KEY AUTOINCREMENT, product_key TEXT, title TEXT, source TEXT, url TEXT, price INTEGER, captured_at TEXT DEFAULT (datetime('now')))""")
        for x in rows:
            if not x.get("price"): continue
            key=hashlib.sha1(re.sub(r"\s+"," ",str(x.get("title") or "").lower()).encode("utf-8","ignore")).hexdigest()[:24]
            c.execute("INSERT INTO shopping_price_history(product_key,title,source,url,price) VALUES(?,?,?,?,?)",(key,str(x.get("title") or "")[:220],str(x.get("source") or "")[:80],str(x.get("url") or "")[:1000],int(x["price"])))
        conn.commit(); conn.close()
    except Exception as exc: logger.debug("shopping history save failed: %s", exc)


def _rank(rows: list[dict], query: str, max_price: int) -> list[dict]:
    seen=set(); out=[]
    for x in rows:
        url=str(x.get("url") or "").strip()
        if not url or url in seen: continue
        seen.add(url)
        title=str(x.get("title") or ""); price=x.get("price")
        rel=_relevance(title, query)
        if rel < 15 and _tokens(query): continue
        trust=TRUST.get(str(x.get("source") or "وب"), 60)
        price_bonus=0
        if price:
            price_bonus=18 if max_price and price<=max_price else 5
        x["_score"]=rel+trust*0.18+price_bonus
        out.append(x)
    out.sort(key=lambda x:(-x["_score"], x.get("price") or 10**30))
    return out


def _history_summary(query: str, days: int = 30) -> tuple[str, dict]:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); rows=conn.execute("SELECT title,source,price,captured_at,url FROM shopping_price_history WHERE captured_at >= datetime('now', ?) ORDER BY id DESC LIMIT 3000",(f"-{max(1,int(days))} days",)).fetchall(); conn.close()
        qt=_tokens(query); matched=[r for r in rows if len(qt & _tokens(r[0])) >= max(1, len(qt)//2)] if qt else []
        prices=[int(r[2]) for r in matched if r[2]]
        if not prices: return "", {}
        stats={"min":min(prices),"max":max(prices),"avg":int(sum(prices)/len(prices)),"count":len(prices)}
        return f"📈 تاریخچه مشاهده‌شده: کمینه {stats['min']:,} | بیشینه {stats['max']:,} | میانگین {stats['avg']:,} تومان در {days} روز اخیر", stats
    except Exception: return "", {}


def _create_alert(user_id: int, query: str, target: int, direction: str = "below") -> str:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); c=conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS shopping_price_alerts (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,query TEXT NOT NULL,target INTEGER NOT NULL,direction TEXT NOT NULL DEFAULT 'below',active INTEGER NOT NULL DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP,last_price INTEGER,last_checked TEXT,triggered_at TEXT)""")
        cur=c.execute("INSERT INTO shopping_price_alerts(user_id,query,target,direction) VALUES(?,?,?,?)",(int(user_id),query[:300],int(target),direction)); conn.commit(); aid=cur.lastrowid; conn.close()
        return f"🔔 هشدار قیمت #{aid} ثبت شد.\nاگر «{query}» به {target:,} تومان یا کمتر برسد، بهت پیام می‌دهم."
    except Exception as exc: return f"ثبت هشدار ناموفق بود: {exc}"


def create_shopping_price_alert(user_id: int, query: str, target: int) -> str:
    if not user_id or not query or int(target or 0) <= 0: return "نام محصول، کاربر و قیمت هدف لازم است."
    return _create_alert(user_id, _clean_query(query), int(target), "below")


def list_shopping_price_alerts(user_id: int) -> str:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); rows=conn.execute("SELECT id,query,target,active,created_at,last_price FROM shopping_price_alerts WHERE user_id=? ORDER BY id DESC",(int(user_id),)).fetchall(); conn.close()
        if not rows: return "🔔 هشدار خرید فعالی نداری."
        lines=["🔔 هشدارهای قیمت خرید:"]
        for r in rows: lines.append(f"#{r[0]} | {'فعال' if r[3] else 'غیرفعال'} | {r[1]} | هدف {int(r[2]):,} تومان")
        return "\n".join(lines)
    except Exception as exc: return f"هشدارها در دسترس نیستند: {exc}"


def cancel_shopping_price_alert(user_id: int, alert_id: int) -> str:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); cur=conn.execute("UPDATE shopping_price_alerts SET active=0 WHERE id=? AND user_id=?",(int(alert_id),int(user_id))); conn.commit(); conn.close()
        return "✅ هشدار غیرفعال شد." if cur.rowcount else "هشدار پیدا نشد."
    except Exception as exc: return f"لغو هشدار ناموفق بود: {exc}"


def shopping_engine_status() -> str:
    return "🛒 Shopping Engine v3\n" + " | ".join(f"{k}={v}" for k,v in _STATS.items()) + f" | cache={len(_CACHE)}"


async def search_shopping(query: str = "", source: str = "all", max_results: int = 10, min_price: int = 0, max_price: int = 0, user_id: int = 0) -> str:
    raw=" ".join(str(query or "").split()).strip()
    if not raw: return "عبارت محصول برای جستجو مشخص نیست."
    _STATS["searches"] += 1
    max_results=max(3,min(int(max_results or 10),12)); budget=_budget(raw)
    if budget and not max_price: max_price=budget
    foreign=_foreign_requested(raw); domain=_explicit_domain(raw)
    if domain and domain not in IRAN_SITES: foreign=True
    clean=_clean_query(raw)
    if not clean or len(clean)<2: clean=raw
    key=_cache_key(clean,domain or source,max_price,foreign); cached=_CACHE.get(key)
    if cached and time.time()-cached[0] < CACHE_TTL:
        _STATS["cache_hits"] += 1; rows=[dict(x) for x in cached[1]]
    else:
        rows=[]
        variants=_query_variants(clean,budget)
        # Direct catalog search is the primary path for Iran, for ALL product categories.
        if not foreign and not domain:
            direct_queries=variants[:2]
            batches=await asyncio.gather(*[_direct_torob(v,max_price,max_results) for v in direct_queries] + [_direct_digikala(v,max_price,max_results) for v in direct_queries], return_exceptions=True)
            for b in batches:
                if isinstance(b,list): rows.extend(b)
        if not rows or foreign or domain:
            domains=[]
            if domain: domains=[domain]
            elif foreign: domains=["amazon.com","ebay.com","walmart.com","aliexpress.com",""]
            else: domains=["torob.com","digikala.com","emalls.ir","technolife.ir",""]
            tasks=[]
            for v in variants[:2]:
                for d in domains[:5]: tasks.append(_fetch_source(v,d,max_results,foreign))
            batches=await asyncio.gather(*tasks,return_exceptions=True)
            for b in batches:
                if isinstance(b,list): rows.extend(b)
        rows=_rank(rows,clean,max_price)
        rows=rows[:max_results]
        _CACHE[key]=(time.time(),[dict(x) for x in rows])
        if rows: _save_history_rows(rows)
    if not rows:
        _STATS["empty"] += 1
        return f"⚠️ برای «{clean}» در منابع زنده نتیجه قابل‌تأییدی پیدا نشد؛ قیمت حدسی ارائه نمی‌کنم."
    priced=[x for x in rows if x.get("price")]
    market="بازار جهانی" if foreign else "بازار ایران"
    now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines=[f"🛒 **نتایج خرید — {clean}**",f"🌍 {market} | 🕒 {now}","ℹ️ قیمت‌ها فقط از داده زنده/کش کوتاه‌مدت استخراج شده‌اند.",""]
    for i,x in enumerate(rows,1):
        price=x.get("price"); src=x.get("source") or "وب"
        lines.append(f"**{i}. {x.get('title') or 'محصول'}**")
        lines.append(f"🏪 {src} | 💰 {price:,} تومان" if price and not foreign else (f"🏪 {src} | 💰 {price:,}" if price else f"🏪 {src} | 💰 قیمت در نتیجه مشخص نشد"))
        if x.get("seller"): lines.append(f"👤 {x['seller']}")
        if x.get("availability"): lines.append(f"📦 {x['availability']}")
        lines.append(f"🔗 {x['url']}"); lines.append("")
    if priced:
        cheapest=min(priced,key=lambda x:x["price"]); lines.append(f"🏆 ارزان‌ترین: **{cheapest['price']:,} تومان**")
        if max_price:
            within=[x for x in priced if x["price"]<=max_price]
            lines.append(f"🎯 {len(within)} نتیجه داخل بودجه {max_price:,} تومان پیدا شد.")
    hist,_=_history_summary(clean,30)
    if hist: lines.extend(["",hist])
    lines += ["", "⚠️ قیمت و موجودی ممکن است تغییر کند؛ قبل از خرید صفحه فروشنده را دوباره بررسی کن."]
    return "\n".join(lines)


async def check_shopping_price_alerts(context) -> None:
    """Low-frequency background check for user shopping alerts."""
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); rows=conn.execute("SELECT id,user_id,query,target,direction FROM shopping_price_alerts WHERE active=1 ORDER BY id LIMIT 25").fetchall(); conn.close()
        for aid,uid,q,target,direction in rows:
            try:
                result=await search_shopping(q,max_results=3,user_id=int(uid))
                prices=[int(x) for x in re.findall(r"(?:💰\s*|🏆[^\n]*?\*\*)\s*([0-9,]+)",result) if x]
                if not prices: continue
                value=min(prices)
                conn=get_db_connection(); conn.execute("UPDATE shopping_price_alerts SET last_price=?,last_checked=CURRENT_TIMESTAMP WHERE id=?",(value,aid)); conn.commit(); conn.close()
                hit=(value<=int(target)) if direction=="below" else (value>=int(target))
                if hit:
                    conn=get_db_connection(); conn.execute("UPDATE shopping_price_alerts SET active=0,triggered_at=CURRENT_TIMESTAMP WHERE id=?",(aid,)); conn.commit(); conn.close()
                    await context.bot.send_message(chat_id=int(uid),text=f"🔔 هشدار قیمت\n\n«{q}»\nقیمت مشاهده‌شده: {value:,} تومان\nهدف: {int(target):,} تومان\n\nبرای بررسی دوباره، جستجوی خرید را اجرا کن.")
            except Exception as exc: logger.debug("shopping alert %s failed: %s",aid,exc)
    except Exception as exc: logger.debug("shopping alerts job failed: %s",exc)


# Rich price-history facade replaces the old simple formatter while preserving the public API.
def shopping_price_history(query: str = "", days: int = 30, user_id: int = 0) -> str:
    query=str(query or "").strip()
    if not query: return "نام محصول برای تاریخچه قیمت مشخص نیست."
    try:
        from bot.database import get_db_connection
        conn=get_db_connection(); rows=conn.execute("SELECT title,source,price,captured_at,url FROM shopping_price_history WHERE captured_at >= datetime('now', ?) ORDER BY id DESC LIMIT 3000",(f"-{max(1,int(days))} days",)).fetchall(); conn.close()
        qt=_tokens(query); matched=[r for r in rows if len(qt & _tokens(r[0]))>=max(1,len(qt)//2)] if qt else []
        if not matched: return f"برای «{query}» هنوز تاریخچه قیمت کافی ثبت نشده است."
        prices=[int(r[2]) for r in matched if r[2]]
        lines=[f"📈 **تاریخچه قیمت — {query}**",f"🗓 بازه: {days} روز | مشاهدات: {len(prices)}"]
        if prices:
            lines.append(f"💰 کمینه: {min(prices):,} | بیشینه: {max(prices):,} | میانگین: {sum(prices)//len(prices):,} تومان")
            if len(prices)>=2:
                change=prices[0]-prices[-1]; pct=(change/prices[-1]*100) if prices[-1] else 0
                lines.append(f"📊 تغییر مشاهده‌شده: {change:+,} تومان ({pct:+.1f}%)")
        for r in matched[:10]: lines.append(f"• {r[3]} | {r[1]} | {int(r[2]):,} تومان")
        return "\n".join(lines)
    except Exception as exc: return f"تاریخچه قیمت در دسترس نیست: {exc}"

# END MERGED LEGACY PART: 
import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from bot.logger import logger

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
SEARCH_URL = "https://html.duckduckgo.com/html/"
CACHE: dict[str, tuple[float, str]] = {}
CACHE_TTL = 150

# لیست گسترده فروشگاه‌ها و منابع ایرانی + بین‌المللی مرتبط
SOURCES = {
    # مقایسه قیمت و مارکت‌پلیس‌های اصلی
    "torob": {"label": "ترب", "domains": ["torob.com"]},
    "digikala": {"label": "دیجی‌کالا", "domains": ["digikala.com"]},
    "snappshop": {"label": "اسنپ‌شاپ", "domains": ["snappshop.ir"]},
    "emalls": {"label": "ایمالز", "domains": ["emalls.ir"]},
    "basalam": {"label": "باسلام", "domains": ["basalam.com"]},
    # تخصصی تکنولوژی و موبایل
    "technolife": {"label": "تکنولایف", "domains": ["technolife.ir"]},
    "momtaz": {"label": "مقداد آی‌تی", "domains": ["meghdadit.com"]},
    "kalaoma": {"label": "کالاوما", "domains": ["kalaoma.com"]},
    "19kala": {"label": "۱۹کالا", "domains": ["19kala.com"]},
    "mobile": {"label": "موبایل‌دات‌آی‌آر", "domains": ["mobile.ir"]},
    "digistyle": {"label": "دیجی‌استایل", "domains": ["digistyle.com"]},
    # مد و پوشاک و زیبایی
    "modiseh": {"label": "مدیسه", "domains": ["modiseh.com"]},
    "zanbil": {"label": "زنبیل", "domains": ["zanbil.ir"]},
    "goldiran": {"label": "گلدیران", "domains": ["goldiran.com"]},
    # مارکت‌پلیس و عمومی
    "alibaba": {"label": "علی‌بابا", "domains": ["alibaba.ir"]},
    "sheypoor": {"label": "شیپور", "domains": ["sheypoor.com"]},
    "divar": {"label": "دیوار", "domains": ["divar.ir"]},
    "okala": {"label": "اکالا", "domains": ["okala.com"]},
    "takhfifan": {"label": "تخفیفان", "domains": ["takhfifan.com"]},
    # اینستاگرام و شبکه‌های اجتماعی
    "instagram": {"label": "اینستاگرام", "domains": ["instagram.com"]},
    # جستجوی عمومی وب (همه‌جا)
    "general": {"label": "وب / سایر", "domains": []},
}

# کلمات کلیدی برای تقویت جستجوی اینستاگرام و فروشگاه‌های آنلاین
INSTA_KEYWORDS = [
    "فروشگاه", "شاپ", "خرید", "قیمت", "فروش آنلاین", "online shop",
    "فروشگاه اینترنتی", "خرید آنلاین",
]


# Shopping Engine v3 must be the final public implementation.
