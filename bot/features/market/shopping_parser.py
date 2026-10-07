"""shopping: parser responsibilities."""
from .shopping_common import *  # noqa: F401,F403
from . import shopping_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _norm_digits(s: str) -> str:
    return str(s).translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )

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

def _currency_and_price(raw: Any, currency: str = "") -> tuple[int | None, str]:
    p = _price(raw)
    cur = (currency or "").lower()
    if p is not None and ("rial" in cur or "ریال" in cur):
        p = p // 10
        return p, "تومان"
    if p is not None:
        return p, "تومان"
    return None, "تومان"

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""

def _source_for_url(url: str) -> str:
    d = _domain(url)
    for key, cfg in SOURCES.items():
        if any(x in d for x in cfg["domains"]):
            return key
    return "general"

def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    return title[:240]

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
