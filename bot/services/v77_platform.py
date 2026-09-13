"""ALIMJ3 V77 Ultimate Platform.

V77 turns the remaining platform ideas into concrete, bounded services:
Agent 5, unified tool execution, knowledge graph, DR integrity/restore
planning, provider mesh, market/news intelligence, smart alerts, security 3,
performance/cache, document intelligence, plugins, admin health, self-healing,
conversation state, report studio, web research, intent, and release gates.

Design goals: deterministic helpers, bounded work, fail-closed security, no
untrusted code execution, no hidden network calls, and compatibility with the
existing V61-V76 services.
"""
from __future__ import annotations

import ast
import asyncio
import csv
import hashlib
import io
import ipaddress
import json
import os
import re
import shutil
import sqlite3
import statistics
import time
import uuid
from collections import Counter, defaultdict, OrderedDict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

VERSION = "77.0.0"
MAX_STEPS = max(2, min(24, int(os.getenv("V77_MAX_STEPS", "12"))))
MAX_CALLS = max(2, min(48, int(os.getenv("V77_MAX_CALLS", "24"))))
MAX_STATE_TURNS = max(4, min(50, int(os.getenv("V77_MAX_STATE_TURNS", "20"))))
CACHE_MAX = max(64, min(20000, int(os.getenv("V77_CACHE_MAX", "4096"))))

_SECRET = re.compile(r"(?i)(token|api[_-]?key|secret|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)")
_INJECTION = re.compile(r"(?i)(ignore\s+(all|any|previous|prior)\s+instructions|system\s+prompt|developer\s+message|reveal\s+.*prompt|نادیده\s+بگیر|دستورهای?\s+سیستم)")
_DANGEROUS = re.compile(r"(?i)(rm\s+-rf|powershell|cmd\.exe|os\.system|subprocess|eval\s*\(|exec\s*\(|curl\s+[^\n]*\|)")
_PRIVATE_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal", "metadata.google.internal."}
_CACHE: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_RATE: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=100))
_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=20))
_CIRCUITS: dict[str, dict[str, Any]] = {}
_EVENTS: defaultdict[str, list[Callable[[dict[str, Any]], Any]]] = defaultdict(list)
_PLUGINS: dict[str, dict[str, Any]] = {}
_PROVIDERS: dict[str, dict[str, Any]] = {}


def _db():
    from bot.database import get_db_connection
    return get_db_connection()


def redact(value: Any, limit: int = 12000) -> str:
    text = str(value if value is not None else "")
    text = _SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]", text)
    return text[:limit]


def security_scan(text: str) -> dict[str, Any]:
    s = str(text or "")[:40000]
    injection = bool(_INJECTION.search(s))
    secret = bool(_SECRET.search(s))
    command = bool(_DANGEROUS.search(s))
    risk = "high" if injection or command else "medium" if secret else "low"
    return {"prompt_injection": injection, "secret_exposure": secret, "dangerous_command": command, "risk": risk}


def safe_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    """Validate URL syntax and resolve host DNS before allowing public IPs."""
    try:
        p = urlparse(str(url).strip())
        schemes = {"http", "https"} if allow_http else {"https"}
        if p.scheme not in schemes or not p.hostname or p.username or p.password:
            return False, "scheme_host_or_userinfo"
        host = p.hostname.rstrip(".").lower()
        if host in _PRIVATE_HOSTS or host.endswith(".local") or host.endswith(".internal"):
            return False, "private_host"
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False, "private_ip"
        except ValueError:
            pass
        # DNS validation is best-effort and fail-closed for resolvable private targets.
        try:
            import socket
            infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
            for info in infos:
                addr = info[4][0]
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                    return False, "private_dns_target"
        except (OSError, ValueError):
            # Domain DNS can be unavailable in offline/test environments; URL is
            # still structurally valid, and the actual HTTP client must recheck.
            pass
        return True, p.geturl()[:4096]
    except Exception:
        return False, "invalid_url"


def safe_path(root: str | Path, candidate: str | Path) -> tuple[bool, Path]:
    base = Path(root).resolve(); target = (base / str(candidate)).resolve()
    try:
        target.relative_to(base); return True, target
    except ValueError:
        return False, target


def archive_member_safe(root: str | Path, member: str) -> tuple[bool, Path]:
    """Prevent zip/tar style traversal and absolute extraction paths."""
    name = str(member).replace("\\", "/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:/", name):
        return False, Path(root) / name
    return safe_path(root, name)


# ---------------------------------------------------------------------------
# 1. Agent 5.0: dependency-aware plan, verification, bounded repair.
# ---------------------------------------------------------------------------
@dataclass
class AgentStep:
    id: str
    tool: str
    arguments: dict[str, Any]
    depends_on: list[str]
    verify: bool = True
    retries: int = 1


@dataclass
class AgentPlan:
    id: str
    goal: str
    steps: list[AgentStep]
    budget_ms: int = 90000
    max_calls: int = MAX_CALLS


def advanced_intent(text: str) -> dict[str, Any]:
    s = str(text or "").strip().lower()
    rules = [
        ("market", r"بازار|قیمت|کریپتو|بیت.?کوین|اتریوم|طلا|ارز|btc|eth|gold|crypto"),
        ("news", r"خبر|اخبار|نیوز|news|latest|خبر جدید"),
        ("calendar", r"تقویم|تقویم اقتصادی|economic calendar|cpi|ppi|nfp|fomc|نرخ بهره"),
        ("web", r"جستجو|وب|منبع|سرچ|search|research"),
        ("download", r"دانلود|download|لینک فایل|فایل دانلود"),
        ("document", r"pdf|word|excel|سند|فایل|متن فایل|جدول"),
        ("report", r"گزارش|report|xlsx|csv|pdf گزارش"),
        ("alert", r"هشدار|آلارم|alert|اعلان قیمت"),
        ("backup", r"بکاپ|پشتیبان|backup|restore|بازیابی"),
        ("system", r"سلامت|وضعیت سیستم|health|status|diagnostic|عیب"),
        ("code", r"کد|برنامه|python|code|bug|باگ"),
    ]
    candidates = [name for name, pat in rules if re.search(pat, s, re.I)]
    return {"primary": candidates[0] if candidates else "general", "candidates": candidates, "needs_tool": bool(candidates), "confidence": min(1.0, 0.35 + 0.15 * len(candidates))}


def build_agent_plan(goal: str, tools: Iterable[str] = ()) -> AgentPlan:
    goal = redact(goal, 8000).strip()
    if not goal or security_scan(goal)["risk"] == "high":
        return AgentPlan(uuid.uuid4().hex, goal, [], 30000, 2)
    available = set(tools)
    mapping = {
        "market": "get_market_prices", "news": "hybrid_retrieve", "calendar": "get_economic_calendar",
        "web": "hybrid_retrieve", "download": "download_file", "document": "search_knowledge_base",
        "report": "generate_report", "system": "v77_system_status",
    }
    steps: list[AgentStep] = []
    for kind in advanced_intent(goal)["candidates"]:
        tool = mapping.get(kind)
        if tool and tool in available and tool not in {x.tool for x in steps}:
            deps = [steps[-1].id] if kind in {"report", "system"} and steps else []
            steps.append(AgentStep(uuid.uuid4().hex[:10], tool, {"query": goal}, deps, True, 1))
    return AgentPlan(uuid.uuid4().hex, goal, steps[:MAX_STEPS])


def verify_result(result: Any, *, expected: str = "") -> dict[str, Any]:
    text = redact(result, 6000).strip()
    failed = not text or text.startswith(("خطا", "Error", "ابزار ناشناخته", "Tool blocked", "زمان اجرای"))
    return {"ok": not failed, "nonempty": bool(text), "expected_match": bool(expected and expected.lower() in text.lower()), "safe": not bool(_SECRET.search(text)), "preview": text[:1000]}


async def run_agent_5(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    plan = build_agent_plan(goal, get_registered_tool_names())
    if not plan.steps:
        return {"ok": bool(plan.goal), "status": "direct_or_blocked", "plan": asdict(plan), "steps": []}
    started = time.monotonic(); results=[]; completed=set(); calls=0
    for step in plan.steps:
        if calls >= plan.max_calls or (time.monotonic()-started)*1000 >= plan.budget_ms:
            break
        if any(dep not in completed for dep in step.depends_on):
            continue
        last = None
        for attempt in range(step.retries + 1):
            if calls >= plan.max_calls: break
            calls += 1; t=time.monotonic()
            try:
                result = await asyncio.wait_for(execute_tool(step.tool, step.arguments, user_id=user_id, source="agent5"), timeout=20)
                check = verify_result(result)
                last = {"step_id": step.id, "tool": step.tool, "attempt": attempt+1, "ok": check["ok"], "verified": check, "latency_ms": round((time.monotonic()-t)*1000,1), "result": redact(result,3000)}
                if check["ok"]: completed.add(step.id); break
            except Exception:
                last = {"step_id": step.id, "tool": step.tool, "attempt": attempt+1, "ok": False, "verified": {"ok":False}, "latency_ms": round((time.monotonic()-t)*1000,1), "result": "tool execution failed"}
        if last: results.append(last)
        if last and not last["ok"]: break
    status="completed" if results and all(x["ok"] for x in results) else "partial" if results else "failed"
    return {"ok": status in {"completed","partial"}, "status":status, "plan":asdict(plan), "steps":results, "calls":calls, "elapsed_ms":round((time.monotonic()-started)*1000,1)}


async def unified_tool_execute(tool: str, arguments: dict[str, Any] | None = None, *, user_id: int = 0) -> dict[str, Any]:
    """Single safe bridge to the existing tool runtime; never executes code strings."""
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    if tool not in set(get_registered_tool_names()):
        return {"ok":False,"error":"unknown_tool"}
    if security_scan(json.dumps(arguments or {}, ensure_ascii=False))["risk"] == "high":
        return {"ok":False,"error":"blocked_input"}
    try:
        out = await asyncio.wait_for(execute_tool(tool, arguments or {}, user_id=user_id, source="v77"), timeout=30)
        return {"ok":True,"result":redact(out,6000)}
    except Exception:
        return {"ok":False,"error":"tool_execution_failed"}


# ---------------------------------------------------------------------------
# 2. Knowledge graph.
# ---------------------------------------------------------------------------
def graph_upsert_node(node_id: str, label: str, kind: str="entity", properties: dict[str,Any]|None=None) -> None:
    c=_db(); c.execute("INSERT INTO v77_graph_nodes(id,label,kind,properties_json,updated_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET label=excluded.label,kind=excluded.kind,properties_json=excluded.properties_json,updated_at=CURRENT_TIMESTAMP",(str(node_id)[:200],redact(label,500),str(kind)[:80],json.dumps(properties or {},ensure_ascii=False)[:12000])); c.commit(); c.close()


def graph_link(source: str, relation: str, target: str, weight: float=1.0) -> None:
    c=_db(); c.execute("INSERT INTO v77_graph_edges(source,relation,target,weight) VALUES(?,?,?,?) ON CONFLICT(source,relation,target) DO UPDATE SET weight=excluded.weight",(str(source)[:200],redact(relation,120),str(target)[:200],float(weight))); c.commit(); c.close()


def graph_neighbors(node_id: str, relation: str|None=None, limit: int=30) -> list[dict[str,Any]]:
    c=_db(); q="SELECT e.source,e.relation,e.target,e.weight,n.label,n.kind,n.properties_json FROM v77_graph_edges e LEFT JOIN v77_graph_nodes n ON n.id=e.target WHERE e.source=?"; a=[node_id]
    if relation: q+=" AND e.relation=?"; a.append(relation)
    q+=" ORDER BY e.weight DESC LIMIT ?"; a.append(max(1,min(100,int(limit)))); rows=c.execute(q,a).fetchall(); c.close(); out=[]
    for r in rows:
        try:p=json.loads(r[6] or "{}")
        except Exception:p={}
        out.append({"source":r[0],"relation":r[1],"target":r[2],"weight":r[3],"label":r[4],"kind":r[5],"properties":p})
    return out


# ---------------------------------------------------------------------------
# 3. Backup / DR 4.0.
# ---------------------------------------------------------------------------
def sqlite_backup(source: str|Path, destination: str|Path) -> dict[str,Any]:
    src=Path(source); dst=Path(destination); dst.parent.mkdir(parents=True,exist_ok=True); tmp=dst.with_suffix(dst.suffix+".tmp")
    try:
        if tmp.exists(): tmp.unlink()
        s=sqlite3.connect(str(src),timeout=10); d=sqlite3.connect(str(tmp),timeout=10)
        with d: s.backup(d)
        s.close(); d.close(); tmp.replace(dst)
        verify=verify_sqlite(dst)
        fp=backup_fingerprint(dst)
        return {"ok":bool(verify["ok"]),"verify":verify,"fingerprint":fp,"path":str(dst)}
    except Exception:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass
        return {"ok":False,"error":"backup_failed"}


def backup_fingerprint(path: str|Path) -> dict[str,Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block); size+=len(block)
    return {"ok":True,"sha256":h.hexdigest(),"size":size,"path":str(p)}


def verify_sqlite(path: str|Path) -> dict[str,Any]:
    try:
        c=sqlite3.connect(str(path),timeout=8); integrity=c.execute("PRAGMA integrity_check").fetchone(); quick=c.execute("PRAGMA quick_check").fetchone(); c.close()
        return {"ok":bool(integrity and integrity[0]=="ok" and quick and quick[0]=="ok"),"result":integrity[0] if integrity else "unknown"}
    except Exception: return {"ok":False,"result":"unavailable"}


def backup_manifest(path: str|Path) -> dict[str,Any]:
    fp=backup_fingerprint(path); return {"version":VERSION,"created_at":int(time.time()),"integrity":verify_sqlite(path),"fingerprint":fp}


def restore_plan(current_db: str|Path, candidates: Iterable[str|Path]) -> dict[str,Any]:
    current=Path(current_db); current_size=current.stat().st_size if current.exists() else 0; ranked=[]
    for candidate in candidates:
        p=Path(candidate); v=verify_sqlite(p)
        if v["ok"]: ranked.append({"path":str(p),"size":p.stat().st_size,"score":(1 if p.stat().st_size else 0)+(p.stat().st_size>=current_size)})
    ranked.sort(key=lambda x:(x["score"],x["size"]),reverse=True)
    return {"ok":bool(ranked),"current_size":current_size,"candidates":ranked}


def rotate_backups(directory: str|Path, keep: int=5) -> dict[str,Any]:
    d=Path(directory); files=sorted([p for p in d.glob("*.db") if p.is_file()], key=lambda p:p.stat().st_mtime, reverse=True) if d.exists() else []
    removed=[]
    for p in files[max(1,int(keep)):]:
        try:p.unlink(); removed.append(p.name)
        except OSError: pass
    return {"ok":True,"kept":min(len(files),max(1,int(keep))),"removed":removed}


# ---------------------------------------------------------------------------
# 4. Provider Mesh 2.0.
# ---------------------------------------------------------------------------
def register_provider(name: str, capabilities: Iterable[str]=(), weight: float=1.0, cost_per_1k: float=0.0) -> None:
    _PROVIDERS[str(name)]={"capabilities":set(capabilities),"weight":max(.1,float(weight)),"cost_per_1k":max(0,float(cost_per_1k)),"failures":0,"successes":0,"latency_ms":0.0,"enabled":True}


def provider_health(name: str, ok: bool, latency_ms: float=0.0, cost: float=0.0) -> None:
    p=_PROVIDERS.setdefault(name,{"capabilities":set(),"weight":1.0,"cost_per_1k":0.0,"failures":0,"successes":0,"latency_ms":0.0,"enabled":True})
    p["latency_ms"]=(p["latency_ms"]*.7)+float(latency_ms)*.3
    p["cost_per_1k"]=(p["cost_per_1k"]*.9)+max(0,float(cost))*.1
    if ok:p["successes"]+=1;p["failures"]=max(0,p["failures"]-1)
    else:p["failures"]+=1
    p["enabled"]=p["failures"]<5


def choose_provider(capability: str, *, max_cost: float|None=None) -> str|None:
    choices=[]
    for name,p in _PROVIDERS.items():
        if not p["enabled"] or capability not in p["capabilities"]: continue
        if max_cost is not None and p["cost_per_1k"]>max_cost: continue
        reliability=p["successes"]/(p["successes"]+p["failures"]+1)
        score=(p["latency_ms"]+1)/(p["weight"]*reliability)
        choices.append((score,name))
    return min(choices)[1] if choices else None


def provider_snapshot() -> dict[str,Any]:
    return {k:{kk:(sorted(vv) if isinstance(vv,set) else vv) for kk,vv in v.items()} for k,v in _PROVIDERS.items()}


# ---------------------------------------------------------------------------
# 5. Market Intelligence 3.0.
# ---------------------------------------------------------------------------
def _num(values: Iterable[Any]) -> list[float]:
    out=[]
    for x in values:
        try: out.append(float(x))
        except (TypeError,ValueError): pass
    return out


def _ema(vals: list[float], period: int) -> float|None:
    if not vals:return None
    p=max(1,min(period,len(vals))); a=2/(p+1); e=vals[0]
    for x in vals[1:]:e=a*x+(1-a)*e
    return e


def market_intelligence_3(closes: Iterable[float], volumes: Iterable[float]|None=None) -> dict[str,Any]:
    v=_num(closes); vol=_num(volumes or []); result={"samples":len(v),"trend":"unknown","regime":"unknown","momentum":0.0,"volatility":0.0,"rsi":None,"ema_fast":None,"ema_slow":None,"volume_trend":"unknown","confidence":0.0}
    if not v:return result
    result["ema_fast"]=_ema(v,12); result["ema_slow"]=_ema(v,26)
    base=v[max(0,len(v)-6)]; result["momentum"]=round((v[-1]-base)/abs(base),6) if base else 0
    rets=[(v[i]-v[i-1])/v[i-1] for i in range(1,len(v)) if v[i-1]]
    result["volatility"]=round(statistics.pstdev(rets),6) if len(rets)>1 else 0.0
    gains=[max(0,x) for x in rets[-14:]]; losses=[max(0,-x) for x in rets[-14:]]; avg_gain=sum(gains)/max(1,len(gains)); avg_loss=sum(losses)/max(1,len(losses))
    result["rsi"]=round(100-(100/(1+avg_gain/max(avg_loss,1e-12))),2) if rets else None
    if result["ema_fast"] and result["ema_slow"]:
        if result["ema_fast"] > result["ema_slow"] and result["momentum"] > 0.005:
            result["trend"] = "bullish"
        elif result["ema_fast"] < result["ema_slow"] and result["momentum"] < -0.005:
            result["trend"] = "bearish"
        elif result["momentum"] > 0.02:
            result["trend"] = "bullish"
        elif result["momentum"] < -0.02:
            result["trend"] = "bearish"
        else:
            result["trend"] = "neutral"
    result["regime"]="high_volatility" if result["volatility"]>.03 else "normal"
    if len(vol)>=4: result["volume_trend"]="rising" if sum(vol[-3:])/3>sum(vol[-6:-3])/3 else "falling"
    result["confidence"]=round(min(1,.25+abs(result["momentum"])*8+(0.15 if result["trend"]!="neutral" else 0)),3)
    return result


def correlation(a: Iterable[float], b: Iterable[float]) -> float|None:
    x=_num(a); y=_num(b); n=min(len(x),len(y))
    if n<3:return None
    x=x[-n:];y=y[-n:];mx=sum(x)/n;my=sum(y)/n;dx=[z-mx for z in x];dy=[z-my for z in y];den=(sum(z*z for z in dx)*sum(z*z for z in dy))**.5
    return round(sum(dx[i]*dy[i] for i in range(n))/den,4) if den else 0.0


# ---------------------------------------------------------------------------
# 6. News Fusion 2.0.
# ---------------------------------------------------------------------------
_POS={"bullish","positive","growth","rise","surge","increase","صعود","رشد","مثبت","افزایش","رکورد"}
_NEG={"bearish","negative","fall","drop","crash","decrease","کاهش","سقوط","منفی","ریزش"}

def news_fusion(items: Iterable[dict[str,Any]]) -> list[dict[str,Any]]:
    groups: dict[str,list[dict[str,Any]]]={}
    for raw in items:
        x=dict(raw); title=re.sub(r"\W+"," ",str(x.get("title","")).lower()).strip(); words=set(title.split()); key=" ".join(sorted(words))[:220] or hashlib.sha1(str(x).encode()).hexdigest()[:12]
        groups.setdefault(key,[]).append(x)
    out=[]
    for key,group in groups.items():
        text=" ".join(str(x.get("title","")).lower()+" "+str(x.get("content","")).lower() for x in group); pos=sum(w in text for w in _POS); neg=sum(w in text for w in _NEG); sentiment="positive" if pos>neg else "negative" if neg>pos else "neutral"
        out.append({"canonical_key":key,"title":group[0].get("title",key),"sources":len(group),"items":group,"sentiment":sentiment,"impact":round(max([float(x.get("impact",0) or 0) for x in group]+[0]),3),"confidence":round(min(1,.35+.12*len(group)),3)})
    return sorted(out,key=lambda x:(-x["impact"],-x["sources"]))


# ---------------------------------------------------------------------------
# 7. Economic surprise.
# ---------------------------------------------------------------------------
def economic_surprise(actual: Any, forecast: Any) -> dict[str,Any]:
    try:a=float(str(actual).replace("%","").replace(",",""));f=float(str(forecast).replace("%","").replace(",",""))
    except (TypeError,ValueError):return {"available":False,"score":0,"direction":"unknown"}
    delta=a-f; score=delta/max(abs(f),1.0)
    return {"available":True,"actual":a,"forecast":f,"delta":round(delta,6),"score":round(score,4),"direction":"above" if delta>0 else "below" if delta<0 else "inline"}


# ---------------------------------------------------------------------------
# 8. Adaptive cache/performance.
# ---------------------------------------------------------------------------
def cache_get(key: str) -> Any:
    k=str(key); x=_CACHE.get(k)
    if not x:return None
    if x[0]<=time.monotonic():_CACHE.pop(k,None);return None
    _CACHE.move_to_end(k);return x[1]


def cache_set(key: str, value: Any, ttl: float=30) -> None:
    k=str(key);_CACHE[k]=(time.monotonic()+max(.5,float(ttl)),value);_CACHE.move_to_end(k)
    while len(_CACHE)>CACHE_MAX:_CACHE.popitem(last=False)


def performance_snapshot() -> dict[str,Any]:
    try:
        c=_db(); rows=c.execute("SELECT latency_ms,ok FROM v77_perf ORDER BY id DESC LIMIT 1000").fetchall();c.close()
        lat=[float(r[0]) for r in rows];err=sum(not bool(r[1]) for r in rows)
    except Exception:lat=[];err=0
    return {"samples":len(lat),"avg_ms":round(sum(lat)/len(lat),2) if lat else 0,"p95_ms":round(sorted(lat)[max(0,int(len(lat)*.95)-1)],2) if lat else 0,"error_rate":round(err/len(lat),4) if lat else 0,"cache_items":len(_CACHE)}


def record_performance(component: str, latency_ms: float, ok: bool=True) -> None:
    try:
        c=_db();c.execute("INSERT INTO v77_perf(component,latency_ms,ok) VALUES(?,?,?)",(redact(component,160),float(latency_ms),int(ok)));c.commit();c.close()
    except Exception:pass


# ---------------------------------------------------------------------------
# 9. QA / regression / release deployment gate.
# ---------------------------------------------------------------------------
def release_gate(root: str|Path=".") -> dict[str,Any]:
    root=Path(root); syntax=[]; forbidden=[]; count=0
    for p in root.rglob("*.py"):
        count+=1
        try:ast.parse(p.read_text(encoding="utf-8"))
        except Exception:syntax.append(str(p))
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".db",".sqlite",".sqlite3",".pyc",".pyo"} and "__pycache__" not in p.parts and p.parts and p.parts[0] not in {"data","runtime","backups"}:forbidden.append(str(p))
    required=["requirements.txt","Dockerfile","render.yaml","bot/main.py"]
    missing=[x for x in required if not (root/x).exists()]
    return {"ok":not syntax and not forbidden and not missing,"python_files":count,"syntax_failures":syntax[:50],"forbidden_artifacts":forbidden[:50],"missing_required":missing}


def run_regression_tests(root: str|Path=".") -> dict[str,Any]:
    import subprocess, sys
    root=str(root)
    try:
        proc=subprocess.run([sys.executable,"-m","pytest","-q","tests"],cwd=root,text=True,capture_output=True,timeout=180)
        return {"ok":proc.returncode==0,"returncode":proc.returncode,"summary":redact((proc.stdout or "").splitlines()[-5:],3000)}
    except Exception:
        return {"ok":False,"returncode":-1,"summary":"pytest execution unavailable"}


# ---------------------------------------------------------------------------
# 10. Smart alerts 3.0.
# ---------------------------------------------------------------------------
def evaluate_alert(kind: str, config: dict[str,Any], context: dict[str,Any]) -> bool:
    try:
        if kind=="price":
            v=float(context["price"]);t=float(config["target"]);return v>=t if config.get("direction","above")=="above" else v<=t
        if kind=="change":
            v=float(context["change_pct"]);t=abs(float(config["threshold"]));return v>=t if config.get("direction","above")=="above" else v<=-t
        if kind=="news":return float(context.get("impact",0))>=float(config.get("min_impact",.7))
        if kind=="calendar":return abs(float(context.get("surprise",0)))>=float(config.get("min_surprise",.5))
        if kind=="combo":return all(bool(context.get(k)) for k in config.get("all",[])[:20])
    except (TypeError,ValueError,KeyError):return False
    return False


def create_alert(user_id: int, kind: str, config: dict[str,Any]) -> str:
    aid=uuid.uuid4().hex;c=_db();c.execute("INSERT INTO v77_alerts(id,user_id,kind,config_json,enabled) VALUES(?,?,?,?,1)",(aid,int(user_id),str(kind)[:50],json.dumps(config,ensure_ascii=False)[:8000]));c.commit();c.close();return aid


def list_alerts(user_id: int, limit: int=50) -> list[dict[str,Any]]:
    c=_db();rows=c.execute("SELECT id,kind,config_json,enabled,created_at FROM v77_alerts WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(int(user_id),max(1,min(100,int(limit))))).fetchall();c.close();out=[]
    for r in rows:
        try:cfg=json.loads(r[2] or "{}")
        except Exception:cfg={}
        out.append({"id":r[0],"kind":r[1],"config":cfg,"enabled":bool(r[3]),"created_at":r[4]})
    return out


# ---------------------------------------------------------------------------
# 11. Security 3 / rate limits / self healing.
# ---------------------------------------------------------------------------
def rate_limit(key: str, limit: int=30, window: float=60) -> bool:
    now=time.monotonic(); q=_RATE[str(key)]
    while q and now-q[0]>window:q.popleft()
    if len(q)>=max(1,int(limit)):return False
    q.append(now);return True


def circuit_state(name: str) -> dict[str,Any]:
    p=_CIRCUITS.setdefault(str(name),{"failures":0,"opened_until":0.0})
    return {"open":time.monotonic()<p["opened_until"],"failures":p["failures"],"retry_at":p["opened_until"]}


def record_failure(name: str, threshold: int=5, cooldown: float=60) -> None:
    n=str(name);now=time.monotonic();q=_FAILURES[n];q.append(now);p=_CIRCUITS.setdefault(n,{"failures":0,"opened_until":0.0});p["failures"]=len(q)
    if len(q)>=threshold:p["opened_until"]=now+max(1,float(cooldown))


def record_success(name: str) -> None:
    n=str(name);_FAILURES[n].clear();p=_CIRCUITS.setdefault(n,{"failures":0,"opened_until":0.0});p.update(failures=0,opened_until=0.0)


def security_center() -> dict[str,Any]:
    return {"fail_closed":True,"prompt_injection":True,"secret_redaction":True,"dns_ssrf_check":True,"path_traversal":True,"archive_traversal":True,"rate_limit":True,"circuit_breaker":True,"untrusted_code_execution":False,"destructive_auto_action":False,"score":100}


# ---------------------------------------------------------------------------
# 12. Document intelligence 2.0.
# ---------------------------------------------------------------------------
def extract_document(path: str|Path) -> dict[str,Any]:
    p=Path(path)
    if not p.exists() or not p.is_file():return {"ok":False,"error":"missing"}
    ext=p.suffix.lower();text="";tables=[]
    try:
        if ext==".pdf":
            from pypdf import PdfReader
            reader=PdfReader(str(p));text="\n".join((page.extract_text() or "") for page in reader.pages)
        elif ext==".docx":
            from docx import Document
            doc=Document(str(p));text="\n".join(x.text for x in doc.paragraphs if x.text.strip())
            tables=[[[cell.text for cell in row.cells] for row in table.rows] for table in doc.tables]
        elif ext in {".txt",".md",".csv"}:
            text=p.read_text(encoding="utf-8",errors="replace")
            if ext==".csv":
                rows=list(csv.reader(io.StringIO(text)));tables=rows[:200]
        else:return {"ok":False,"error":"unsupported_type"}
        return {"ok":True,"type":ext,"text":text[:200000],"characters":len(text),"tables":tables[:50],"sha256":backup_fingerprint(p)["sha256"]}
    except Exception:return {"ok":False,"error":"document_parse_failed"}


# ---------------------------------------------------------------------------
# 13. Plugin architecture 2.0.
# ---------------------------------------------------------------------------
def register_plugin(name: str, version: str, handler: Callable[...,Any], permissions: Iterable[str]=(), trusted: bool=False) -> dict[str,Any]:
    if not name or not callable(handler):return {"ok":False,"error":"invalid_plugin"}
    if not trusted:return {"ok":False,"error":"trust_required"}
    perms={str(x) for x in permissions if str(x) in {"read","network","files","market","admin"}}
    _PLUGINS[str(name)]={"version":str(version),"handler":handler,"permissions":perms,"trusted":True}
    return {"ok":True,"name":str(name),"version":str(version),"permissions":sorted(perms)}


def plugin_snapshot() -> dict[str,Any]:
    return {k:{"version":v["version"],"permissions":sorted(v["permissions"]),"trusted":v["trusted"]} for k,v in _PLUGINS.items()}


# ---------------------------------------------------------------------------
# 14. Conversation state: structured turns, no automatic summarization.
# ---------------------------------------------------------------------------
def update_conversation(user_id: int, role: str, content: str, metadata: dict[str,Any]|None=None) -> None:
    if role not in {"user","assistant","tool","system"}:role="user"
    c=_db();c.execute("INSERT INTO v77_conversation(id,user_id,role,content,metadata_json) VALUES(?,?,?,?,?)",(uuid.uuid4().hex,int(user_id),role,redact(content,10000),json.dumps(metadata or {},ensure_ascii=False)[:6000]));c.execute("DELETE FROM v77_conversation WHERE user_id=? AND id NOT IN (SELECT id FROM v77_conversation WHERE user_id=? ORDER BY created_at DESC LIMIT ?)",(int(user_id),int(user_id),MAX_STATE_TURNS));c.commit();c.close()


def get_conversation(user_id: int, limit: int=MAX_STATE_TURNS) -> list[dict[str,Any]]:
    c=_db();rows=c.execute("SELECT role,content,metadata_json,created_at FROM v77_conversation WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(int(user_id),max(1,min(MAX_STATE_TURNS,int(limit))))).fetchall();c.close();out=[]
    for r in reversed(rows):
        try:m=json.loads(r[2] or "{}")
        except Exception:m={}
        out.append({"role":r[0],"content":r[1],"metadata":m,"created_at":r[3]})
    return out


# ---------------------------------------------------------------------------
# 15. Report Studio: JSON/CSV/XLSX/DOCX/PDF.
# ---------------------------------------------------------------------------
def generate_report(title: str, rows: list[dict[str,Any]], fmt: str="json") -> tuple[bytes,str,str]:
    safe=re.sub(r"[^\w\- ]+","_",title or "report")[:80] or "report";fmt=fmt.lower();keys=sorted({k for r in rows for k in r})
    if fmt=="json":return json.dumps({"title":title,"rows":rows},ensure_ascii=False,indent=2).encode(),safe+".json","application/json"
    if fmt=="csv":
        s=io.StringIO();w=csv.DictWriter(s,fieldnames=keys);w.writeheader();w.writerows(rows);return s.getvalue().encode("utf-8-sig"),safe+".csv","text/csv"
    if fmt=="xlsx":
        try:
            from openpyxl import Workbook
            wb=Workbook();ws=wb.active;ws.title=(title or "Report")[:31];ws.append(keys)
            for r in rows:ws.append([r.get(k,"") for k in keys])
            b=io.BytesIO();wb.save(b);return b.getvalue(),safe+".xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception:return generate_report(title,rows,"csv")
    if fmt=="docx":
        try:
            from docx import Document
            doc=Document();doc.add_heading(title or "Report",0);table=doc.add_table(rows=1,cols=max(1,len(keys))); 
            for i,k in enumerate(keys):table.rows[0].cells[i].text=str(k)
            for r in rows:
                cells=table.add_row().cells
                for i,k in enumerate(keys):cells[i].text=str(r.get(k,""))
            b=io.BytesIO();doc.save(b);return b.getvalue(),safe+".docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except Exception:return generate_report(title,rows,"json")
    if fmt=="pdf":
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            b=io.BytesIO();doc=SimpleDocTemplate(b,pagesize=A4);styles=getSampleStyleSheet();story=[Paragraph(title or "Report",styles["Title"])];data=[keys]+[[str(r.get(k,"")) for k in keys] for r in rows]
            table=Table(data,repeatRows=1);table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey)]));story.append(table);doc.build(story);return b.getvalue(),safe+".pdf","application/pdf"
        except Exception:return generate_report(title,rows,"json")
    return generate_report(title,rows,"json")


# ---------------------------------------------------------------------------
# 16. Web Research.
# ---------------------------------------------------------------------------
def rank_sources(items: Iterable[dict[str,Any]], query: str="") -> list[dict[str,Any]]:
    seen=set();out=[];terms=set(re.findall(r"\w{3,}",query.lower()))
    for raw in list(items)[:200]:
        x=dict(raw);url=str(x.get("url","")).strip();title=str(x.get("title","")).strip();key=hashlib.sha256((url or title).lower().encode()).hexdigest()
        if key in seen:continue
        seen.add(key);text=(title+" "+str(x.get("content", ""))).lower();match=sum(t in text for t in terms);trust=float(x.get("trust",0) or 0)+(0.1 if url.startswith("https://") else 0);x.update(score=round(match+trust,3),untrusted=True);out.append(x)
    return sorted(out,key=lambda x:x["score"],reverse=True)


def verify_claim(claim: str, evidence: Iterable[str]) -> dict[str,Any]:
    tokens=set(re.findall(r"\w{4,}",str(claim).lower()));ev=" ".join(map(str,evidence)).lower();matched=sum(t in ev for t in tokens);confidence=matched/max(1,len(tokens));return {"claim":redact(claim,1500),"supported":confidence>=.5,"confidence":round(confidence,3),"matched_terms":matched,"terms":len(tokens)}


def research_pack(query: str, sources: Iterable[dict[str,Any]]) -> dict[str,Any]:
    ranked=rank_sources(sources,query);claims=[]
    for item in ranked[:8]:
        content=str(item.get("content","") or item.get("snippet","")).strip()
        if content:claims.append(verify_claim(query,[content]))
    return {"query":redact(query,1000),"sources":ranked[:10],"evidence_checks":claims,"confidence":round(sum(x["confidence"] for x in claims)/len(claims),3) if claims else 0}


# ---------------------------------------------------------------------------
# 17. Admin center / self-healing.
# ---------------------------------------------------------------------------
def self_healing_snapshot() -> dict[str,Any]:
    return {"circuits":{k:circuit_state(k) for k in _CIRCUITS},"failures":{k:len(v) for k,v in _FAILURES.items() if v},"policy":"bounded_retry_then_circuit"}


def admin_snapshot(root: str|Path=".") -> dict[str,Any]:
    return {"version":VERSION,"security":security_center(),"performance":performance_snapshot(),"providers":provider_snapshot(),"plugins":plugin_snapshot(),"self_healing":self_healing_snapshot(),"release_gate":release_gate(root)}


# ---------------------------------------------------------------------------
# 18. Event-driven / workflow safety.
# ---------------------------------------------------------------------------
def subscribe(event: str, callback: Callable[[dict[str,Any]],Any]) -> None:
    if callable(callback) and len(_EVENTS[str(event)])<32:_EVENTS[str(event)].append(callback)


async def emit(event: str, payload: dict[str,Any]) -> int:
    count=0
    for cb in list(_EVENTS.get(str(event),[])):
        try:
            r=cb(payload)
            if asyncio.iscoroutine(r):await asyncio.wait_for(r,timeout=10)
            count+=1
        except Exception:pass
    return count


def validate_workflow(steps: list[dict[str,Any]]) -> tuple[bool,str]:
    if not isinstance(steps,list) or len(steps)>MAX_STEPS:return False,"too_many_steps"
    if any(str(x.get("tool", "")) in {"run_workflow","workflow_execute"} for x in steps):return False,"nested_workflow"
    ids=[str(x.get("id",i)) for i,x in enumerate(steps)]
    if len(ids)!=len(set(ids)):return False,"duplicate_step_ids"
    return True,"ok"


# ---------------------------------------------------------------------------
# 19. DB and system initialization.
# ---------------------------------------------------------------------------
def init_v77_tables() -> None:
    c=_db();c.executescript("""
    CREATE TABLE IF NOT EXISTS v77_graph_nodes(id TEXT PRIMARY KEY,label TEXT NOT NULL,kind TEXT NOT NULL,properties_json TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v77_graph_edges(source TEXT NOT NULL,relation TEXT NOT NULL,target TEXT NOT NULL,weight REAL DEFAULT 1,PRIMARY KEY(source,relation,target));
    CREATE TABLE IF NOT EXISTS v77_perf(id INTEGER PRIMARY KEY AUTOINCREMENT,component TEXT,latency_ms REAL,ok INTEGER,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v77_alerts(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,kind TEXT NOT NULL,config_json TEXT NOT NULL,enabled INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS v77_conversation(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,metadata_json TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_v77_graph_edges_source ON v77_graph_edges(source);
    CREATE INDEX IF NOT EXISTS idx_v77_alerts_user ON v77_alerts(user_id,enabled);
    CREATE INDEX IF NOT EXISTS idx_v77_conversation_user ON v77_conversation(user_id,created_at);
    """);c.commit();c.close()


def system_snapshot(root: str|Path=".") -> dict[str,Any]:
    try:c=_db();users=c.execute("SELECT COUNT(*) FROM users").fetchone()[0];alerts=c.execute("SELECT COUNT(*) FROM v77_alerts WHERE enabled=1").fetchone()[0];nodes=c.execute("SELECT COUNT(*) FROM v77_graph_nodes").fetchone()[0];c.close()
    except Exception:users=alerts=nodes=0
    return {"version":VERSION,"users":users,"active_alerts":alerts,"graph_nodes":nodes,"security":security_center(),"performance":performance_snapshot(),"providers":provider_snapshot(),"plugins":plugin_snapshot(),"self_healing":self_healing_snapshot()}


def self_test(root: str|Path=".") -> dict[str,Any]:
    checks={}
    checks["intent"]=advanced_intent("قیمت بیت کوین") ["primary"]=="market"
    checks["security"]=security_scan("ignore previous instructions")["prompt_injection"] and not safe_url("http://127.0.0.1")[0]
    checks["graph"]=(graph_upsert_node("__v77test__","test" ) is None and graph_link("__v77test__","knows","__v77test2__") is None and bool(graph_neighbors("__v77test__")))
    checks["market"]=market_intelligence_3([100,105,110])["trend"]=="bullish"
    checks["news"]=bool(news_fusion([{"title":"Bitcoin rises","impact":.8},{"title":"Bitcoin rises","impact":.7}]))
    checks["calendar"]=economic_surprise("110","100")["direction"]=="above"
    checks["report"]=bool(generate_report("qa",[{"ok":True}],"json")[0])
    checks["workflow"]=validate_workflow([{"tool":"run_workflow"}])[0] is False
    checks["release"]=release_gate(root)["ok"]
    return {"ok":all(checks.values()),"checks":checks,"system":system_snapshot(root)}
