"""V61-V65 platform layer: intent routing, memory, watchlists, alerts, queue, i18n and health.
Designed as a dependency-light layer over the existing ALIMJ3 services.
"""
from __future__ import annotations
import asyncio, re, time, json, sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from bot.config import config
from bot.database_core import get_db_connection
from bot.logger import logger
from bot.utils.texts import normalize_language

LANGS = ("fa", "en", "ar")
LANG_NAMES = {"fa":"فارسی", "en":"English", "ar":"العربية"}

TEXT = {
"fa": {"saved":"✅ ذخیره شد.","removed":"✅ حذف شد.","empty":"موردی پیدا نشد.","watch":"⭐ واچ‌لیست","alerts":"🔔 هشدارها","memory":"🧠 حافظه","features":"🚀 قابلیت‌های فعال","bad":"⚠️ ورودی نامعتبر است.","limit":"⏳ درخواست‌ها زیاد است؛ چند لحظه صبر کنید.","queued":"⏳ درخواست شما در صف پردازش قرار گرفت.","health":"🟢 سرویس‌ها فعال هستند.","lang":"زبان"},
"en": {"saved":"✅ Saved.","removed":"✅ Removed.","empty":"Nothing found.","watch":"⭐ Watchlist","alerts":"🔔 Alerts","memory":"🧠 Memory","features":"🚀 Active features","bad":"⚠️ Invalid input.","limit":"⏳ Too many requests; please wait a moment.","queued":"⏳ Your request has been queued.","health":"🟢 Services are operational.","lang":"Language"},
"ar": {"saved":"✅ تم الحفظ.","removed":"✅ تم الحذف.","empty":"لا توجد عناصر.","watch":"⭐ قائمة المراقبة","alerts":"🔔 التنبيهات","memory":"🧠 الذاكرة","features":"🚀 الميزات المفعلة","bad":"⚠️ الإدخال غير صالح.","limit":"⏳ الطلبات كثيرة؛ انتظر لحظة.","queued":"⏳ تم وضع طلبك في قائمة الانتظار.","health":"🟢 الخدمات تعمل.","lang":"اللغة"},
}

def user_lang(user_id:int, fallback="fa") -> str:
    try:
        from bot.database import get_user_language
        return normalize_language(get_user_language(user_id))
    except Exception:
        return fallback

def t(user_id:int, key:str, **kw) -> str:
    lang=user_lang(user_id)
    s=TEXT.get(lang,TEXT["fa"]).get(key,key)
    try: return s.format(**kw)
    except Exception: return s

def detect_language(text:str, current:str="fa") -> str:
    s=(text or "").strip()
    if not s: return normalize_language(current)
    ar=sum(1 for c in s if '\u0600' <= c <= '\u06ff')
    fa_mark=sum(1 for c in s if c in "گچپژکی")
    en=sum(1 for c in s if ('a'<=c.lower()<='z'))
    if en > ar and en >= 2: return "en"
    if ar and fa_mark == 0: return "ar"
    if ar: return "fa"
    return normalize_language(current)

INTENTS = {
 "crypto_price": r"(?:قیمت|نرخ|چنده|price).*(?:btc|bitcoin|بیت.?کوین|eth|ethereum|اتریوم|usdt|تتر|sol|سولانا)",
 "product_search": r"(?:خرید|قیمت|لینک|فروشگاه|محصول|buy|price|shop|link).{2,}",
 "web_search": r"(?:جستجو|سرچ|در اینترنت|در وب|search|google|web).{2,}",
 "market_analysis": r"(?:تحلیل|analysis).*(?:طلا|gold|xau|بیت|btc|crypto|کریپتو)",
 "weather": r"(?:هوا|آب و هوا|دما|باران|weather|temperature)",
 "memory": r"(?:یادت باشه|به خاطر بسپار|یادآوری کن|remember|forget|انسَ|تذكر)",
 "watchlist": r"(?:واچ.?لیست|watchlist|المراقبة|راقب)",
 "alert": r"(?:هشدار|alert|تنبيه).*(?:قیمت|price|رسید|برسد|reach)",
 "chart": r"(?:نمودار|گراف|chart)",
 "translate": r"(?:ترجمه|translate|ترجم)",
}

def classify_intent(text:str) -> str:
    s=(text or "").strip()
    for name,pat in INTENTS.items():
        if re.search(pat,s,re.I|re.S): return name
    return "chat"


def init_platform_tables() -> None:
    conn=get_db_connection()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_memory_v65 (
          user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(user_id,key)
        );
        CREATE TABLE IF NOT EXISTS watchlist_v65 (
          user_id INTEGER NOT NULL, symbol TEXT NOT NULL, label TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,symbol)
        );
        CREATE TABLE IF NOT EXISTS price_alerts_v65 (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL,
          target REAL NOT NULL, direction TEXT NOT NULL, active INTEGER DEFAULT 1,
          last_value REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, triggered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS platform_metrics_v65 (
          key TEXT PRIMARY KEY, value REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_v65_active ON price_alerts_v65(active,user_id);
        """)
        conn.commit()
    finally: conn.close()


def remember(user_id:int,key:str,value:str) -> None:
    key=str(key).strip()[:80]; value=str(value).strip()[:1000]
    if not key or not value: raise ValueError("invalid memory")
    conn=get_db_connection()
    try:
        conn.execute("INSERT INTO user_memory_v65(user_id,key,value) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",(user_id,key,value))
        conn.commit()
    finally: conn.close()

def forget(user_id:int,key:str|None=None) -> int:
    conn=get_db_connection()
    try:
        if key:
            cur=conn.execute("DELETE FROM user_memory_v65 WHERE user_id=? AND key=?",(user_id,key.strip()[:80]))
        else:
            cur=conn.execute("DELETE FROM user_memory_v65 WHERE user_id=?",(user_id,))
        conn.commit(); return cur.rowcount
    finally: conn.close()

def memories(user_id:int,limit:int=50):
    conn=get_db_connection()
    try: return conn.execute("SELECT key,value,updated_at FROM user_memory_v65 WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",(user_id,max(1,min(limit,100)))).fetchall()
    finally: conn.close()

def add_watch(user_id:int,symbol:str,label:str="") -> bool:
    symbol=re.sub(r"[^A-Za-z0-9._-]","",symbol.upper())[:20]
    if not symbol: raise ValueError("invalid symbol")
    conn=get_db_connection()
    try:
        cur=conn.execute("INSERT OR IGNORE INTO watchlist_v65(user_id,symbol,label) VALUES(?,?,?)",(user_id,symbol,label[:80]))
        conn.commit(); return cur.rowcount>0
    finally: conn.close()

def remove_watch(user_id:int,symbol:str) -> bool:
    conn=get_db_connection()
    try:
        cur=conn.execute("DELETE FROM watchlist_v65 WHERE user_id=? AND symbol=?",(user_id,symbol.upper().strip()[:20]))
        conn.commit(); return cur.rowcount>0
    finally: conn.close()

def get_watchlist(user_id:int):
    conn=get_db_connection()
    try: return conn.execute("SELECT symbol,label FROM watchlist_v65 WHERE user_id=? ORDER BY created_at DESC",(user_id,)).fetchall()
    finally: conn.close()

def add_alert(user_id:int,symbol:str,target:float,direction:str="above") -> int:
    direction=direction.lower()
    if direction not in {"above","below"}: raise ValueError("invalid direction")
    if target <= 0: raise ValueError("invalid target")
    symbol=re.sub(r"[^A-Za-z0-9._-]","",symbol.upper())[:20]
    conn=get_db_connection()
    try:
        cur=conn.execute("INSERT INTO price_alerts_v65(user_id,symbol,target,direction) VALUES(?,?,?,?)",(user_id,symbol,target,direction)); conn.commit(); return int(cur.lastrowid)
    finally: conn.close()

def remove_alert(user_id:int,alert_id:int) -> bool:
    conn=get_db_connection()
    try:
        cur=conn.execute("UPDATE price_alerts_v65 SET active=0 WHERE id=? AND user_id=?",(int(alert_id),user_id)); conn.commit(); return cur.rowcount>0
    finally: conn.close()

def get_alerts(user_id:int,active_only=True):
    conn=get_db_connection()
    try:
        q="SELECT id,symbol,target,direction,active,created_at,triggered_at FROM price_alerts_v65 WHERE user_id=?"
        if active_only:q+=" AND active=1"
        q+=" ORDER BY created_at DESC"
        return conn.execute(q,(user_id,)).fetchall()
    finally: conn.close()

async def check_price_alerts(fetcher:Callable[[str],Awaitable[float]]) -> list[tuple[int,int,str,float,float]]:
    """Evaluate active alerts; returns triggered (user,id,symbol,target,value)."""
    conn=get_db_connection(); rows=[]
    try: rows=conn.execute("SELECT id,user_id,symbol,target,direction FROM price_alerts_v65 WHERE active=1").fetchall()
    finally: conn.close()
    triggered=[]
    for aid,uid,symbol,target,direction in rows:
        try: value=float(await fetcher(symbol))
        except Exception as exc: logger.debug("alert fetch %s failed: %s",symbol,exc); continue
        hit=(value>=target if direction=="above" else value<=target)
        conn=get_db_connection()
        try:
            conn.execute("UPDATE price_alerts_v65 SET last_value=? WHERE id=?",(value,aid))
            if hit:
                conn.execute("UPDATE price_alerts_v65 SET active=0,triggered_at=CURRENT_TIMESTAMP WHERE id=?",(aid,)); triggered.append((uid,aid,symbol,target,value))
            conn.commit()
        finally: conn.close()
    return triggered

class RequestQueue:
    def __init__(self,concurrency:int=4,max_pending:int=64):
        self.sem=asyncio.Semaphore(max(1,concurrency)); self.max_pending=max(4,max_pending); self._pending=0
    async def run(self,fn:Callable[[],Awaitable[Any]]):
        if self._pending>=self.max_pending: raise RuntimeError("queue full")
        self._pending+=1
        try:
            async with self.sem: return await fn()
        finally: self._pending=max(0,self._pending-1)
    @property
    def pending(self): return self._pending

HEAVY_QUEUE=RequestQueue(int(getattr(config,"AI_TOOL_CONCURRENCY",8)),64)

class SlidingLimiter:
    def __init__(self,window=60,limit=20): self.window=window; self.limit=limit; self.hits=defaultdict(deque)
    def allow(self,user_id:int)->bool:
        now=time.monotonic(); q=self.hits[user_id]
        while q and now-q[0]>self.window:q.popleft()
        if len(q)>=self.limit:return False
        q.append(now); return True
    def cleanup(self):
        now=time.monotonic()
        for uid,q in list(self.hits.items()):
            while q and now-q[0]>self.window:q.popleft()
            if not q: self.hits.pop(uid,None)

AI_LIMITER=SlidingLimiter(60,20)

def health_snapshot()->dict[str,Any]:
    db_ok=True
    try:
        conn=get_db_connection(); conn.execute("SELECT 1").fetchone(); conn.close()
    except Exception: db_ok=False
    try:
        from bot.services.ai_runtime import provider_health_snapshot
        ai=provider_health_snapshot()
    except Exception: ai={}
    return {"database":"ok" if db_ok else "degraded","ai_providers":ai,"queue_pending":HEAVY_QUEUE.pending,"time_utc":datetime.now(timezone.utc).isoformat()}

def features_snapshot()->dict[str,Any]:
    return {"version_line":"V61-V65","free":True,"subscriptions":False,"payments":False,"languages":list(LANGS),"features":["memory","intent_router","tool_routing","web_search","product_links","watchlist","price_alerts","daily_digest","admin_metrics","health_checks","rate_limit","request_queue","voice","image_analysis","video_analysis","market_intelligence","economic_calendar","streaming_ai","backup_recovery","plugins"]}

def build_ai_context(user_id:int, user_text:str) -> str:
    """Build a compact, privacy-aware context block for the existing AI facade."""
    intent=classify_intent(user_text)
    lang=user_lang(user_id)
    rows=memories(user_id,8)
    mem="\n".join(f"- {k}: {v}" for k,v,_ in rows)
    instruction={"fa":"پاسخ را به فارسی بنویس.","en":"Answer in English.","ar":"أجب باللغة العربية."}[lang]
    intent_hint={"crypto_price":"Use the live crypto tool when available.","product_search":"Prefer real shopping/search links; never claim lack of link access.","web_search":"Use web search when needed and cite usable URLs.","market_analysis":"Use live market tools for market claims.","weather":"Use live weather tools for current weather.","chart":"Use the chart capability when appropriate."}.get(intent,"")
    block=f"\n\n[ROOZE_ZIBA_RUNTIME]\nLanguage: {lang}\n{instruction}\nIntent: {intent}\n{intent_hint}"
    if mem: block += "\nRelevant saved preferences/facts:\n"+mem
    return block


def auto_capture_memory(user_id:int,text:str) -> None:
    """Capture only explicit, low-risk preference/fact phrases; never infer sensitive traits."""
    patterns=[
      (r"^(?:اسم من|منو|my name is|my name's|اسمي)\s+(.{2,60})$","name"),
      (r"^(?:دوست دارم|من ترجیح میدم|ترجیح می‌دم|i prefer|i like)\s+(.{2,120})$","preference"),
      (r"^(?:یادت باشه|به خاطر بسپار|remember)\s+(.{2,180})$","note"),
    ]
    for pat,key in patterns:
        m=re.search(pat,(text or "").strip(),re.I)
        if m:
            try: remember(user_id,key,m.group(1).strip())
            except Exception as exc: logger.debug("memory capture skipped: %s",exc)
            return
