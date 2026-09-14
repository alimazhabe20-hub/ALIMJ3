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
            timeout=14, follow_redirects=True, headers={"User-Agent": UA}
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
