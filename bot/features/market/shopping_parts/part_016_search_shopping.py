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
            local_variants = variants[:5] if key not in ("general", "instagram") else variants[:8]
            for variant in local_variants:
                if key == "instagram":
                    tasks.append(
                        _search(f"{variant} {' OR '.join(INSTA_KEYWORDS[:3])}",
                                domain="instagram.com", limit=limit + 1)
                    )
                elif key == "general":
                    tasks.append(_search(variant, domain="", limit=limit + 2))
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
    to_inspect = list(links.values())[:36]
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
