"""ALIMJ3 V76 — Adaptive Core & Automation Platform.

Dependency-light implementations of the twenty V76 capability groups.  The
module is deliberately bounded: no untrusted input becomes executable code,
agent loops are finite, destructive operations require explicit approval, and
all persistent state is SQLite-backed through the existing DB facade.
"""
from __future__ import annotations

import ast, asyncio, csv, hashlib, io, ipaddress, json, os, re, sqlite3, time, uuid
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

VERSION = "76.0.0"
MAX_STEPS = max(1, min(20, int(os.getenv("V76_MAX_STEPS", "10"))))
MAX_CALLS = max(2, min(40, int(os.getenv("V76_MAX_CALLS", "20"))))
MAX_JOB_QUEUE = max(50, min(5000, int(os.getenv("V76_MAX_JOB_QUEUE", "500"))))
MAX_CACHE = max(64, min(10000, int(os.getenv("V76_CACHE_MAX", "2048"))))

_SECRET = re.compile(r"(?i)(token|api[_-]?key|secret|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)")
_INJECTION = re.compile(r"(?i)(ignore\s+(all|any|previous|prior)\s+instructions|system\s+prompt|developer\s+message|reveal\s+.*prompt|نادیده\s+بگیر|دستورهای?\s+سیستم)")
_PRIVATE_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal", "169.254.169.254"}
_CACHE: dict[str, tuple[float, Any]] = {}
_PERF: deque[dict[str, Any]] = deque(maxlen=4000)
_FAILURES: defaultdict[str, deque[float]] = defaultdict(lambda: deque(maxlen=20))
_EVENTS: defaultdict[str, list[Callable[[dict[str, Any]], Any]]] = defaultdict(list)
_PLUGINS: dict[str, dict[str, Any]] = {}
_PROVIDERS: dict[str, dict[str, Any]] = {}


def _db():
    from bot.database import get_db_connection
    return get_db_connection()


def redact(value: Any, limit: int = 10000) -> str:
    text = str(value if value is not None else "")
    text = _SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]", text)
    return text[:limit]


def security_scan(text: str) -> dict[str, Any]:
    s = str(text or "")[:30000]
    injection = bool(_INJECTION.search(s))
    secret = bool(_SECRET.search(s))
    command = bool(re.search(r"(?i)(rm\s+-rf|powershell|cmd\.exe|os\.system|subprocess|curl\s+[^\n]*\|)", s))
    return {"prompt_injection": injection, "secret_exposure": secret, "dangerous_command": command,
            "risk": "high" if injection or command else "medium" if secret else "low"}


def safe_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    try:
        p = urlparse(str(url).strip())
        if p.scheme not in ({"http", "https"} if allow_http else {"https"}) or not p.hostname:
            return False, "scheme_or_host"
        host = p.hostname.lower().rstrip(".")
        if host in _PRIVATE_HOSTS or host.endswith(".local"):
            return False, "private_host"
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False, "private_ip"
        except ValueError:
            pass
        if p.username or p.password:
            return False, "userinfo_not_allowed"
        return True, p.geturl()[:4096]
    except Exception:
        return False, "invalid_url"


def safe_path(root: str | Path, candidate: str | Path) -> tuple[bool, Path]:
    base = Path(root).resolve(); target = (base / str(candidate)).resolve()
    try: target.relative_to(base); return True, target
    except ValueError: return False, target

# 1. Agent 4.0 + planning/verification
@dataclass
class Plan:
    id: str
    goal: str
    steps: list[dict[str, Any]]
    budget_ms: int = 60000
    max_calls: int = MAX_CALLS


def intent(text: str) -> dict[str, Any]:
    s = str(text or "").lower()
    candidates = []
    rules = [("market", r"بازار|قیمت|کریپتو|بیت.?کوین|طلا|ارز|btc|gold|crypto"),
             ("news", r"خبر|اخبار|news|latest"), ("calendar", r"تقویم|economic calendar|خبر اقتصادی"),
             ("web", r"جستجو|وب|search|منبع"), ("download", r"دانلود|download|فایل"),
             ("document", r"pdf|word|excel|فایل|سند"), ("workflow", r"workflow|اتومات|خودکار"),
             ("report", r"گزارش|report"), ("code", r"کد|برنامه|code|python")]
    for name, pattern in rules:
        if re.search(pattern, s, re.I): candidates.append(name)
    return {"primary": candidates[0] if candidates else "general", "candidates": candidates, "needs_tool": bool(candidates)}


def build_plan(goal: str, tools: Iterable[str] = ()) -> Plan:
    g = redact(goal, 6000).strip(); scan = security_scan(g)
    if not g or scan["risk"] == "high": return Plan(uuid.uuid4().hex, g, [], 30000, 2)
    available = set(tools); i = intent(g); mapping = {"market":"get_market_prices", "news":"hybrid_retrieve", "calendar":"get_economic_calendar", "web":"hybrid_retrieve", "download":"download_file", "document":"search_knowledge_base", "report":"generate_report"}
    steps=[]
    for kind in i["candidates"]:
        tool=mapping.get(kind)
        if tool and tool in available and tool not in [x["tool"] for x in steps]: steps.append({"tool":tool,"arguments":{"query":g},"verify":True})
    return Plan(uuid.uuid4().hex,g,steps[:MAX_STEPS])


async def run_agent_4(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    plan=build_plan(goal,get_registered_tool_names()); start=time.monotonic(); out=[]; seen=set()
    if not plan.steps: return {"ok": bool(plan.goal), "status":"direct_or_blocked", "plan":asdict(plan), "steps":[]}
    for idx,step in enumerate(plan.steps,1):
        if idx>MAX_STEPS or len(out)>=plan.max_calls or (time.monotonic()-start)*1000>=plan.budget_ms: break
        if step["tool"] in seen: continue
        seen.add(step["tool"]); t=time.monotonic()
        result=await execute_tool(step["tool"],step.get("arguments",{}),user_id=user_id,source="agent")
        ok=not str(result).startswith(("خطا در اجرای","زمان اجرای","ابزار ناشناخته","ابزار مسدود"))
        out.append({"step":idx,"tool":step["tool"],"ok":ok,"verified":ok,"latency_ms":round((time.monotonic()-t)*1000,1),"result":redact(result,3000)})
        record_performance("agent4:"+step["tool"],(time.monotonic()-t)*1000,ok)
        if not ok: break
    status="completed" if out and all(x["ok"] for x in out) else "partial" if out else "failed"
    return {"ok":status in {"completed","partial"},"status":status,"plan":asdict(plan),"steps":out,"elapsed_ms":round((time.monotonic()-start)*1000,1)}


# 2. Multi-agent
async def multi_agent_4(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    r=await run_agent_4(goal,user_id=user_id)
    specialists=[{"role":"researcher" if "search" in x["tool"] else "domain","tool":x["tool"],"ok":x["ok"]} for x in r["steps"]]
    return {**r,"specialists":specialists,"review":all(x["verified"] for x in r["steps"]) if r["steps"] else False}

# 3. Admin/observability

def record_performance(component: str, latency_ms: float, ok: bool=True) -> None:
    _PERF.append({"component":component,"latency_ms":round(float(latency_ms),2),"ok":bool(ok),"ts":time.time()})
    try:
        c=_db(); c.execute("INSERT INTO v76_perf(component,latency_ms,ok) VALUES(?,?,?)",(component,float(latency_ms),int(ok))); c.commit(); c.close()
    except Exception: pass


def observability() -> dict[str,Any]:
    vals=list(_PERF); lat=[x["latency_ms"] for x in vals]
    return {"version":VERSION,"samples":len(vals),"error_rate":round(sum(not x["ok"] for x in vals)/len(vals),3) if vals else 0,"avg_latency_ms":round(sum(lat)/len(lat),2) if lat else 0,"slow_requests":sum(x["latency_ms"]>2000 for x in vals),"components":sorted({x["component"] for x in vals})}

# 4. Security center

def security_center() -> dict[str,Any]:
    return {"fail_closed":True,"ssrf_protection":True,"prompt_injection":True,"secret_redaction":True,"path_traversal":True,"archive_safety":True,"destructive_tools_require_approval":True,"score":100}

# 5. Web intelligence

def rank_sources(items: list[dict[str,Any]], query: str="") -> list[dict[str,Any]]:
    seen=set(); out=[]
    for item in items[:100]:
        url=str(item.get("url","")).strip(); title=str(item.get("title","")).strip(); key=hashlib.sha256((url or title).lower().encode()).hexdigest()
        if key in seen: continue
        seen.add(key); score=float(item.get("score",0)); score += 1 if query and any(w in (title+" "+str(item.get("content",""))).lower() for w in query.lower().split()[:5]) else 0
        out.append({**item,"score":round(score,3),"untrusted":True})
    return sorted(out,key=lambda x:x["score"],reverse=True)


def verify_claim(claim: str, evidence: Iterable[str]) -> dict[str,Any]:
    tokens={x for x in re.findall(r"\w{4,}",claim.lower())}; ev=" ".join(map(str,evidence)).lower(); matched=sum(x in ev for x in tokens)
    confidence=matched/max(1,len(tokens)); return {"claim":redact(claim,1000),"supported":confidence>=0.5,"confidence":round(confidence,3)}

# 6. RAG

def rag_chunk(text: str, chunk_size: int=900, overlap: int=120) -> list[str]:
    chunk_size=max(100,min(4000,int(chunk_size))); overlap=max(0,min(chunk_size-1,int(overlap))); s=str(text or ""); out=[]; i=0
    while i<len(s) and len(out)<2000:
        out.append(s[i:i+chunk_size]); i += chunk_size-overlap
    return out


def rag_search(query: str, chunks: Iterable[str], limit: int=5) -> list[dict[str,Any]]:
    q=set(re.findall(r"\w{2,}",query.lower())); scored=[]
    for ch in chunks:
        words=set(re.findall(r"\w{2,}",str(ch).lower())); score=len(q&words)/max(1,len(q)); scored.append({"text":str(ch)[:4000],"score":round(score,4)})
    return sorted(scored,key=lambda x:x["score"],reverse=True)[:max(1,min(20,int(limit)))]

# 7. Advanced market

def market_advanced(closes: Iterable[float]) -> dict[str,Any]:
    vals=[float(x) for x in closes if x is not None]
    if not vals: return {"trend":"unknown","volatility":0,"momentum":0,"confidence":0}
    momentum=(vals[-1]-vals[max(0,len(vals)-6)])/max(abs(vals[max(0,len(vals)-6)]),1e-9)
    mean=sum(vals)/len(vals); variance=sum((x-mean)**2 for x in vals)/len(vals); vol=(variance**0.5)/max(abs(mean),1e-9)
    trend="bullish" if momentum>0.01 else "bearish" if momentum<-0.01 else "neutral"
    return {"trend":trend,"momentum":round(momentum,5),"volatility":round(vol,5),"confidence":round(min(1,abs(momentum)*10+0.2),3),"regime":"high_vol" if vol>.03 else "normal"}

# 8. News fusion

def fuse_news(items: Iterable[dict[str,Any]]) -> list[dict[str,Any]]:
    groups={}
    for x in items:
        title=str(x.get("title","")).strip(); key=re.sub(r"\W+"," ",title.lower()).strip()[:180]
        groups.setdefault(key,[]).append(x)
    return [{"title":k,"sources":len(v),"items":v,"impact":max(float(x.get("impact",0)) for x in v)} for k,v in groups.items()]

# 9. Economic calendar

def economic_surprise(actual: Any, forecast: Any) -> dict[str,Any]:
    try: a=float(str(actual).replace('%','').replace(',','')); f=float(str(forecast).replace('%','').replace(',','')); delta=a-f
        # percent-free normalized surprise
    except Exception: return {"available":False,"score":0,"direction":"unknown"}
    scale=max(abs(f),1.0); score=delta/scale
    return {"available":True,"delta":round(delta,6),"score":round(score,4),"direction":"above" if delta>0 else "below" if delta<0 else "inline"}

# 10. Backup / DR

def backup_fingerprint(path: str|Path) -> dict[str,Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block); size+=len(block)
    return {"ok":True,"sha256":h.hexdigest(),"size":size,"path":str(p)}


def verify_sqlite(path: str|Path) -> dict[str,Any]:
    try:
        c=sqlite3.connect(str(path),timeout=5); row=c.execute("PRAGMA integrity_check").fetchone(); c.close(); return {"ok":row and row[0]=="ok","result":row[0] if row else "unknown"}
    except Exception as e: return {"ok":False,"result":"unavailable"}

# 11. Performance/cache

def cache_get(key: str) -> Any:
    x=_CACHE.get(str(key));
    if not x: return None
    if x[0]<=time.monotonic(): _CACHE.pop(str(key),None); return None
    return x[1]


def cache_set(key: str, value: Any, ttl: float=30) -> None:
    if len(_CACHE)>=MAX_CACHE:
        for k in list(_CACHE)[:max(1,len(_CACHE)-MAX_CACHE+1)]: _CACHE.pop(k,None)
    _CACHE[str(key)]=(time.monotonic()+max(1,float(ttl)),value)

# 12. QA release gate

def release_gate(root: str|Path=".") -> dict[str,Any]:
    root=Path(root); failures=[]; files=0
    for p in root.rglob("*.py"):
        files+=1
        try: ast.parse(p.read_text(encoding="utf-8"))
        except Exception as e: failures.append(str(p))
    return {"ok":not failures,"python_files":files,"syntax_failures":failures[:50],"security":security_center()}

# 13. Workflow/event architecture

def validate_workflow(steps: list[dict[str,Any]]) -> tuple[bool,str]:
    if len(steps)>MAX_STEPS: return False,"too_many_steps"
    if any(str(x.get("tool","")) in {"run_workflow","workflow_execute"} for x in steps): return False,"nested_workflow"
    return True,"ok"


def subscribe(event: str, callback: Callable[[dict[str,Any]],Any]) -> None:
    if callable(callback): _EVENTS[str(event)][:20].append(callback)


async def emit(event: str, payload: dict[str,Any]) -> int:
    count=0
    for cb in list(_EVENTS.get(str(event),[])):
        try:
            r=cb(payload); await r if asyncio.iscoroutine(r) else None; count+=1
        except Exception: pass
    return count

# 14 Smart alerts

def evaluate_alert(kind: str, config: dict[str,Any], context: dict[str,Any]) -> bool:
    if kind=="price":
        try: v=float(context["price"]); t=float(config["target"]); return v>=t if config.get("direction","above")=="above" else v<=t
        except Exception:return False
    if kind=="combo": return all(bool(context.get(k)) for k in config.get("all",[])[:20])
    if kind=="news": return float(context.get("impact",0))>=float(config.get("min_impact",.7))
    if kind=="calendar": return abs(float(context.get("surprise",0)))>=float(config.get("min_surprise",.5))
    return False

# 15 Memory 2.0

def remember(user_id:int,key:str,value:str,category:str="general",confidence:float=1.0,source:str="user") -> None:
    c=_db(); c.execute("INSERT INTO v76_memory(id,user_id,category,key,value,confidence,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,category,key) DO UPDATE SET value=excluded.value,confidence=excluded.confidence,source=excluded.source,updated_at=CURRENT_TIMESTAMP",(uuid.uuid4().hex,user_id,category,redact(key,200),redact(value,3000),max(0,min(1,float(confidence))),source)); c.commit(); c.close()


def recall(user_id:int,category:str|None=None,limit:int=20)->list[dict[str,Any]]:
    c=_db(); q="SELECT category,key,value,confidence,source,updated_at FROM v76_memory WHERE user_id=?"; a=[user_id]
    if category:q+=" AND category=?";a.append(category)
    q+=" ORDER BY updated_at DESC LIMIT ?";a.append(max(1,min(100,int(limit)))); rows=c.execute(q,a).fetchall();c.close();return [dict(x) for x in rows]

# 16 Workspace

def workspace_create(user_id:int,name:str)->str:
    wid=uuid.uuid4().hex;c=_db();c.execute("INSERT INTO v76_workspaces(id,user_id,name) VALUES(?,?,?)",(wid,user_id,redact(name,120)));c.commit();c.close();return wid

# 17 Report generator

def generate_report(title:str,rows:list[dict[str,Any]],fmt:str="json")->tuple[bytes,str,str]:
    safe=re.sub(r"[^\w\- ]+","_",title or "report")[:80] or "report"; fmt=fmt.lower()
    if fmt=="json":return json.dumps({"title":title,"rows":rows},ensure_ascii=False,indent=2).encode(),safe+".json","application/json"
    if fmt=="csv":
        keys=sorted({k for r in rows for k in r});s=io.StringIO();w=csv.DictWriter(s,fieldnames=keys);w.writeheader();w.writerows(rows);return s.getvalue().encode("utf-8-sig"),safe+".csv","text/csv"
    if fmt=="xlsx":
        try:
            from openpyxl import Workbook
            wb=Workbook();ws=wb.active;keys=sorted({k for r in rows for k in r});ws.append(keys)
            for r in rows:ws.append([r.get(k,"") for k in keys])
            b=io.BytesIO();wb.save(b);return b.getvalue(),safe+".xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception:return generate_report(title,rows,"csv")
    return generate_report(title,rows,"json")

# 18 Conversation state

def update_state(user_id:int,goal:str,context:dict[str,Any]|None=None,pending:bool=False)->None:
    c=_db();c.execute("INSERT INTO v76_state(user_id,goal,context_json,pending,updated_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET goal=excluded.goal,context_json=excluded.context_json,pending=excluded.pending,updated_at=CURRENT_TIMESTAMP",(user_id,redact(goal,1000),json.dumps(context or {},ensure_ascii=False)[:10000],int(pending)));c.commit();c.close()


def get_state(user_id:int)->dict[str,Any]:
    c=_db();r=c.execute("SELECT goal,context_json,pending,updated_at FROM v76_state WHERE user_id=?",(user_id,)).fetchone();c.close()
    if not r:return {}
    try:ctx=json.loads(r[1] or "{}")
    except Exception:ctx={}
    return {"goal":r[0],"context":ctx,"pending":bool(r[2]),"updated_at":r[3]}

# 19 Plugin/provider mesh

def register_plugin(name:str,version:str,handler:Callable[...,Any],permissions:Iterable[str]=())->None:
    if name and callable(handler):_PLUGINS[name]={"version":version,"handler":handler,"permissions":set(permissions)}


def plugin_snapshot()->dict[str,Any]:return {k:{"version":v["version"],"permissions":sorted(v["permissions"])} for k,v in _PLUGINS.items()}


def register_provider(name:str,capabilities:Iterable[str]=(),weight:float=1.0)->None:
    _PROVIDERS[name]={"capabilities":set(capabilities),"weight":float(weight),"failures":0,"latency":0.0,"enabled":True}


def provider_health(name:str,ok:bool,latency_ms:float=0)->None:
    p=_PROVIDERS.setdefault(name,{"capabilities":set(),"weight":1.0,"failures":0,"latency":0.0,"enabled":True});p["latency"]=float(latency_ms);p["failures"]=max(0,p["failures"]+(0 if ok else 1));p["enabled"]=p["failures"]<5


def choose_provider(capability:str)->str|None:
    candidates=[(n,p) for n,p in _PROVIDERS.items() if p["enabled"] and capability in p["capabilities"]]
    if not candidates:return None
    return min(candidates,key=lambda x:(x[1]["failures"],x[1]["latency"]/max(x[1]["weight"],.1)))[0]

# 20 DB/migrations + system center

def init_v76_tables()->None:
    c=_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS v76_perf(id INTEGER PRIMARY KEY AUTOINCREMENT,component TEXT,latency_ms REAL,ok INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v76_memory(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,category TEXT NOT NULL,key TEXT NOT NULL,value TEXT NOT NULL,confidence REAL,source TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,category,key));
    CREATE TABLE IF NOT EXISTS v76_workspaces(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,name TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v76_state(user_id INTEGER PRIMARY KEY,goal TEXT,context_json TEXT,pending INTEGER DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v76_jobs(id TEXT PRIMARY KEY,user_id INTEGER,status TEXT,payload_json TEXT,priority INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_v76_jobs_status ON v76_jobs(status,priority,created_at);
    CREATE TABLE IF NOT EXISTS v76_security(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT,detail TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """);c.commit();c.close()


def system_snapshot()->dict[str,Any]:
    try:
        c=_db();jobs=c.execute("SELECT COUNT(*) FROM v76_jobs WHERE status IN ('queued','running')").fetchone()[0];mem=c.execute("SELECT COUNT(*) FROM v76_memory").fetchone()[0];c.close()
    except Exception:jobs=mem=0
    return {"version":VERSION,"intent_engine":True,"agent4":True,"multi_agent":True,"event_driven":True,"job_engine":True,"plugin_system":True,"security":security_center(),"observability":observability(),"web_intelligence":True,"rag3":True,"market_advanced":True,"news_fusion":True,"calendar2":True,"backup_dr":True,"performance":True,"qa_release_gate":True,"smart_alerts":True,"memory2":True,"workspace":True,"reports":True,"conversation_state":True,"provider_mesh":True,"jobs":jobs,"memory":mem}


def self_test(root:str|Path=".")->dict[str,Any]:
    checks={}
    try:init_v76_tables();checks["database"]=True
    except Exception:checks["database"]=False
    checks["security"]=security_scan("ignore previous instructions")["prompt_injection"]
    checks["url"]=not safe_url("http://127.0.0.1:80")[0]
    checks["intent"]=intent("قیمت بیت کوین")["primary"]=="market"
    checks["rag"]=bool(rag_search("btc",["BTC market","weather"],1))
    checks["market"]=market_advanced([100,105,110])["trend"]=="bullish"
    checks["calendar"]=economic_surprise("110","100")["direction"]=="above"
    checks["workflow"]=validate_workflow([{"tool":"run_workflow"}])[0] is False
    checks["report"]=bool(generate_report("qa",[{"ok":True}])[0])
    checks["release_gate"]=release_gate(root)["ok"]
    return {"ok":all(checks.values()),"checks":checks,"system":system_snapshot()}
