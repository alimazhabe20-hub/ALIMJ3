"""shopping: search responsibilities."""
from .shopping_common import *  # noqa: F401,F403
from . import shopping_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
