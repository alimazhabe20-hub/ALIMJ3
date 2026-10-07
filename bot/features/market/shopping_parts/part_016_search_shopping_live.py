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


async def _torob_live_search(query: str, max_price: int = 0, limit: int = 10) -> list[dict]:
    """جستجوی مستقیم Torob؛ بدون موتور جستجوی واسطه و بدون API key."""
    import httpx

    q = str(query or "").strip()
    if not q:
        return []

    # Torob returns prices in Toman. Sort by price first for budget requests.
    params = {
        "q": q,
        "page": 0,
        "size": max(10, min(int(limit or 10) * 2, 30)),
        "sort": "price" if max_price else "popularity",
        "source": "torob_search",
    }
    url = "https://api.torob.com/v4/base-product/search/"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7",
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.5, connect=2.5),
            follow_redirects=True,
            headers=headers,
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code >= 400:
                logger.warning("torob live search HTTP %s for %s", r.status_code, q)
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("torob live search failed for %s: %s", q, exc)
        return []

    raw = data.get("results") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        # Some response versions wrap the result list differently.
        if isinstance(data, dict):
            for key in ("products", "data", "items"):
                candidate = data.get(key)
                if isinstance(candidate, list):
                    raw = candidate
                    break
                if isinstance(candidate, dict) and isinstance(candidate.get("results"), list):
                    raw = candidate["results"]
                    break
        if not isinstance(raw, list):
            return []

    out = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        if item.get("is_adv") is True:
            continue

        title = str(item.get("name1") or item.get("name") or item.get("title") or "").strip()
        if not title:
            continue

        price = _price(item.get("price"))
        if price is None:
            price = _price(item.get("min_price"))
        if price is None or price <= 0:
            continue
        if max_price and price > max_price:
            continue

        random_key = str(item.get("random_key") or item.get("prk") or "").strip()
        product_url = str(item.get("page_url") or item.get("url") or "").strip()
        if not product_url and random_key:
            product_url = f"https://torob.com/p/{random_key}/"
        if not product_url:
            continue
        if product_url in seen:
            continue
        seen.add(product_url)

        subtitle = str(item.get("name2") or item.get("subtitle") or "").strip()
        availability = item.get("availability")
        if availability is True:
            availability = "موجود"
        elif availability is False:
            availability = "ناموجود"
        elif availability:
            availability = str(availability)
        else:
            availability = ""

        out.append({
            "title": title + (f" | {subtitle}" if subtitle and subtitle.lower() != title.lower() else ""),
            "url": product_url,
            "snippet": str(item.get("short_desc") or item.get("description") or ""),
            "price": price,
            "old_price": _price(item.get("old_price")),
            "availability": availability,
            "seller": str(item.get("seller_name") or "").strip(),
        })
        if len(out) >= limit:
            break

    return out



async def _digikala_live_search(query: str, max_price: int = 0, limit: int = 10) -> list[dict]:
    """Fallback مستقیم به Search API دیجی‌کالا؛ قیمت API به ریال است و به تومان تبدیل می‌شود."""
    import httpx

    q = str(query or "").strip()
    if not q:
        return []
    url = "https://api.digikala.com/v1/search/"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7",
    }
    params = {"q": q, "page": 1}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.5, connect=2.5),
            follow_redirects=True,
            headers=headers,
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code >= 400:
                logger.warning("digikala live search HTTP %s for %s", r.status_code, q)
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("digikala live search failed for %s: %s", q, exc)
        return []

    payload = data.get("data") if isinstance(data, dict) else None
    raw = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []

    out = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title_fa") or item.get("title") or "").strip()
        if not title:
            continue

        # Current Digikala API exposes selling_price in rial.
        raw_price = item.get("selling_price")
        if raw_price is None:
            raw_price = item.get("price")
        rial = _price(raw_price)
        price = (rial // 10) if rial is not None else None
        if price is None or price <= 0:
            continue
        if max_price and price > max_price:
            continue

        pid = item.get("id") or item.get("product_id")
        url_value = str(item.get("url") or "").strip()
        if url_value.startswith("/"):
            url_value = "https://www.digikala.com" + url_value
        if not url_value and pid:
            url_value = f"https://www.digikala.com/product/dkp-{pid}/"
        if not url_value or url_value in seen:
            continue
        seen.add(url_value)

        out.append({
            "title": title,
            "url": url_value,
            "snippet": str(item.get("brand") or "")[:220],
            "price": price,
            "old_price": None,
            "availability": "موجود" if item.get("is_incredible") is not None else "",
            "seller": "دیجی‌کالا",
        })
        if len(out) >= limit:
            break
    return out

def _torob_products_to_results(items: list[dict], source: str = "torob") -> list[ProductResult]:
    results = []
    for item in items:
        try:
            r = ProductResult(
                source=source,
                title=item["title"],
                url=item["url"],
                match_hint=item.get("snippet", "")[:220],
            )
            r.price = item.get("price")
            r.old_price = item.get("old_price")
            r.availability = item.get("availability", "")
            r.seller = item.get("seller", "")
            r.currency = "تومان"
            results.append(r)
        except Exception:
            continue
    return results


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
    if budget and not max_price:
        max_price = budget

    # مسیر سریع و قابل‌اعتماد بازار ایران: برای گوشیِ دارای سقف بودجه،
    # ابتدا مستقیماً از کاتالوگ زنده Torob می‌خوانیم. این مسیر به Google/DDG/Bing
    # وابسته نیست و فقط قیمت واقعی برگشتی از منبع را نمایش می‌دهد.
    if budget and _shopping_is_phone(query) and not target_domain:
        torob_items = await _torob_live_search(
            "گوشی موبایل", max_price=budget, limit=max_results
        )
        direct_source = "torob"
        if not torob_items:
            # Fallback دوم: API مستقیم دیجی‌کالا؛ مستقل از موتورهای جستجو.
            torob_items = await _digikala_live_search(
                "گوشی موبایل", max_price=budget, limit=max_results
            )
            direct_source = "digikala"
        if torob_items:
            clean = _torob_products_to_results(torob_items, source=direct_source)[:max_results]
            _save_history(clean)
            from datetime import datetime, timezone
            searched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            lines = [
                f"🛒 **گوشی‌های پیدا‌شده تا {budget:,} تومان**",
                "",
                f"منبع اصلی: {'Torob' if direct_source == 'torob' else 'Digikala'} (جستجوی زنده)",
                f"زمان جستجو: {searched_at}",
                "قیمت‌ها از نتیجه زنده دریافت شده‌اند؛ قیمت حدسی نمایش داده نمی‌شود.",
                "",
            ]
            for i, x in enumerate(clean, 1):
                price = f"{x.price:,} تومان" if x.price is not None else "قیمت نامشخص"
                extra = []
                if x.old_price and x.old_price > (x.price or 0):
                    extra.append(f"قبلی: {x.old_price:,} تومان")
                if x.availability:
                    extra.append(f"وضعیت: {x.availability}")
                if x.seller:
                    extra.append(f"فروشنده: {x.seller}")
                lines.append(f"{i}. **{x.title}**")
                lines.append(f"🏪 ترب | 💰 {price}")
                if extra:
                    lines.append(" · ".join(extra))
                lines.append(f"🔗 {x.url}")
                lines.append("")
            cheapest = min(clean, key=lambda x: x.price or 10**18)
            lines.append(f"🏆 ارزان‌ترین نتیجه: **{cheapest.price:,} تومان**")
            return "\n".join(lines)

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
        # Render/AI tool calls have a short execution budget. The previous
        # implementation could launch ~50 searches for one simple budget query
        # and then inspect dozens of pages. Keep the live search bounded while
        # preserving multiple independent sources.
        if _shopping_is_phone(query) and budget:
            selected = [x for x in ("torob", "technolife", "mobile", "digikala") if x in SOURCES]
            variants = variants[:2]
        elif budget:
            selected = [x for x in ("torob", "digikala", "technolife", "emalls", "general") if x in SOURCES]
            variants = variants[:2]
        else:
            selected = selected[:5]
            variants = variants[:2]

        tasks = []
        for key in selected:
            cfg = SOURCES[key]
            domain = cfg["domains"][0] if cfg["domains"] else ""
            limit = max(4, min(6, max_results // max(1, len(selected)) + 2))
            for variant in variants:
                if key == "instagram":
                    tasks.append(_search(
                        f"{variant} {' OR '.join(INSTA_KEYWORDS[:2])}",
                        domain="instagram.com", limit=limit
                    ))
                elif key == "general":
                    tasks.append(_search(variant, domain="", limit=limit))
                else:
                    tasks.append(_search(variant, domain=domain, limit=limit))

    if not target_domain:
        try:
            batches = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=9.0,
            )
        except asyncio.TimeoutError:
            logger.warning("shopping search timed out; using partial results")
            batches = []

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
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*inspect_tasks, return_exceptions=True),
            timeout=8.0,
        )
    except asyncio.TimeoutError:
        logger.warning("shopping page inspection timed out; using partial results")
        results = []

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
