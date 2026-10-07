"""Shopping Engine v3 - live, multi-source, cached, ranked and alert-ready.

Rules:
- Iran is the default market.
- Foreign/global sources are opt-in only.
- AI is never required for shopping results.
- Never invent a price, stock state, seller or URL.
- Prefer direct live catalogs, then search engines as fallback.
"""
from __future__ import annotations

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
