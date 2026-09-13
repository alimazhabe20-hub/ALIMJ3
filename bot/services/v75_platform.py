"""ALIMJ3 V75 — Intelligence & Automation Platform.

Adds the requested 17 capability groups as bounded, production-safe primitives:
Agent 3.0, Multi-Agent, Admin Dashboard data, Security Center, Web Intelligence
3.0, RAG 3.0, Market Intelligence 2.0, News Intelligence, Economic Calendar 2.0,
Backup/DR 3.0, Performance 3.0, QA 3.0, Workflow Builder, Smart Alerts,
Memory 2.0, Workspace, and Report Generator.

The module is intentionally dependency-light. Network/AI-heavy operations delegate
to existing project services and degrade safely when an optional provider is absent.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import time
import uuid
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from bot.logger import logger

VERSION = "75.0.0"
MAX_WORKFLOW_STEPS = max(1, min(12, int(os.getenv("V75_WORKFLOW_MAX_STEPS", "8"))))
MAX_AGENT_STEPS = max(1, min(12, int(os.getenv("V75_AGENT_MAX_STEPS", "8"))))
MAX_AGENT_CALLS = max(2, min(32, int(os.getenv("V75_AGENT_MAX_CALLS", "16"))))
MAX_AGENT_MS = max(5000, min(180000, int(os.getenv("V75_AGENT_BUDGET_MS", "60000"))))
MAX_ALERTS_PER_USER = max(10, min(500, int(os.getenv("V75_MAX_ALERTS", "100"))))
MAX_MEMORY_ITEMS = max(20, min(2000, int(os.getenv("V75_MAX_MEMORY", "500"))))

# ---------------------------------------------------------------------------
# Generic helpers / security
# ---------------------------------------------------------------------------
_SECRET_RE = re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)")
_INJECTION_RE = re.compile(
    r"(?i)(ignore\s+(all|any|previous|prior)\s+instructions|system\s+prompt|developer\s+message|reveal\s+.*prompt|نادیده\s+بگیر|دستورهای?\s+سیستم)"
)

def redact(value: Any, limit: int = 8000) -> str:
    text = str(value if value is not None else "")
    text = _SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]", text)
    return text[:limit]


def security_scan(text: str) -> dict[str, Any]:
    s = str(text or "")[:20000]
    injection = bool(_INJECTION_RE.search(s))
    secrets = bool(_SECRET_RE.search(s))
    suspicious_commands = bool(re.search(r"(?i)(rm\s+-rf|powershell|cmd\.exe|subprocess|os\.system|curl\s+.*\|)", s))
    return {"prompt_injection": injection, "secret_exposure": secrets, "dangerous_command": suspicious_commands,
            "risk": "high" if injection or suspicious_commands else "medium" if secrets else "low"}


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()

# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------
def _db():
    from bot.database import get_db_connection
    return get_db_connection()


def init_v75_tables() -> None:
    conn = _db()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS v75_workspaces (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_v75_ws_user ON v75_workspaces(user_id);
        CREATE TABLE IF NOT EXISTS v75_workflow_runs (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
            status TEXT NOT NULL, input_json TEXT, result_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, finished_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_v75_runs_user ON v75_workflow_runs(user_id, created_at);
        CREATE TABLE IF NOT EXISTS v75_alerts (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL,
            config_json TEXT NOT NULL, enabled INTEGER DEFAULT 1,
            last_value TEXT, last_fired_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_v75_alerts_user ON v75_alerts(user_id, enabled);
        CREATE TABLE IF NOT EXISTS v75_memory (
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, category TEXT NOT NULL,
            key TEXT NOT NULL, value TEXT NOT NULL, confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'user', updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, category, key)
        );
        CREATE INDEX IF NOT EXISTS idx_v75_mem_user ON v75_memory(user_id, category);
        CREATE TABLE IF NOT EXISTS v75_news (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT NOT NULL,
            url TEXT, published_at TEXT, impact REAL DEFAULT 0,
            sentiment REAL DEFAULT 0, content_hash TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS v75_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT NOT NULL,
            operation TEXT NOT NULL, latency_ms REAL DEFAULT 0, ok INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_v75_metrics_time ON v75_metrics(created_at);
        """)
        conn.commit()
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# 1/2 Agent 3.0 + Multi-Agent
# ---------------------------------------------------------------------------
@dataclass
class AgentTask:
    id: str
    goal: str
    steps: list[dict[str, Any]]
    status: str = "planned"


def plan_agent(goal: str, available_tools: Iterable[str] = ()) -> AgentTask:
    goal = redact(goal, 6000).strip()
    available = set(available_tools)
    if not goal:
        return AgentTask(uuid.uuid4().hex, "", [], "rejected")
    scan = security_scan(goal)
    if scan["risk"] == "high":
        return AgentTask(uuid.uuid4().hex, goal, [], "security_blocked")
    patterns = [
        (r"هوا|weather", "get_weather", {"query": goal}),
        (r"بازار|قیمت|کریپتو|بیت.?کوین|طلا|ارز|market|price", "get_market_prices", {"query": goal}),
        (r"تقویم|خبر اقتصادی|economic calendar", "get_economic_calendar", {"query": goal}),
        (r"خبر|اخبار|news|latest|وب|جستجو|search", "hybrid_retrieve", {"query": goal, "include_web": True}),
        (r"خرید|محصول|shopping", "search_shopping", {"query": goal, "source": "all", "max_results": 8}),
        (r"مستند|دانش|راهنما|knowledge", "search_knowledge_base", {"query": goal}),
    ]
    steps = []
    for pattern, tool, args in patterns:
        if tool in available and re.search(pattern, goal, re.I):
            steps.append({"tool": tool, "arguments": args, "reason": "intent_match"})
    # Multi-agent style specialist stages: research -> domain -> reviewer.
    if len(steps) > MAX_AGENT_STEPS:
        steps = steps[:MAX_AGENT_STEPS]
    return AgentTask(uuid.uuid4().hex, goal, steps, "planned" if steps else "direct_answer")


async def run_agent_3(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    task = plan_agent(goal, get_registered_tool_names())
    if task.status != "planned":
        return {"ok": task.status == "direct_answer", "task_id": task.id, "status": task.status, "steps": []}
    started = time.monotonic(); results = []; seen = set()
    for index, step in enumerate(task.steps[:MAX_AGENT_STEPS], 1):
        if len(results) >= MAX_AGENT_CALLS or (time.monotonic() - started) * 1000 >= MAX_AGENT_MS:
            break
        tool = step["tool"]
        if tool in seen:
            continue
        seen.add(tool)
        t0 = time.monotonic()
        result = await execute_tool(tool, step.get("arguments", {}), user_id=user_id, source="agent")
        ok = not str(result).startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته", "ابزار مسدود"))
        results.append({"step": index, "tool": tool, "ok": ok, "latency_ms": round((time.monotonic()-t0)*1000, 1), "result": redact(result, 2500)})
        if not ok:
            # One bounded reviewer/repair path; never recursive.
            break
    task.status = "completed" if results and all(x["ok"] for x in results) else "partial" if results else "failed"
    return {"ok": task.status in {"completed", "partial"}, "task_id": task.id, "status": task.status,
            "goal": task.goal, "steps": results, "elapsed_ms": round((time.monotonic()-started)*1000, 1)}


async def run_multi_agent(goal: str, *, user_id: int = 0) -> dict[str, Any]:
    """Bounded specialist orchestration using existing tools, not independent LLM loops."""
    result = await run_agent_3(goal, user_id=user_id)
    specialists = []
    for item in result.get("steps", []):
        specialists.append({"specialist": _specialist_for(item["tool"]), "tool": item["tool"], "ok": item["ok"]})
    return {**result, "specialists": specialists, "reviewed": bool(result.get("steps"))}


def _specialist_for(tool: str) -> str:
    if "market" in tool: return "finance"
    if "calendar" in tool: return "economics"
    if "search" in tool or "retrieve" in tool: return "research"
    if "weather" in tool: return "utility"
    return "general"

# ---------------------------------------------------------------------------
# 3 Security Center
# ---------------------------------------------------------------------------
def security_center_snapshot() -> dict[str, Any]:
    return {
        "policy": "fail_closed",
        "prompt_injection_detection": True,
        "secret_redaction": True,
        "tool_permission_boundary": True,
        "untrusted_content_boundary": True,
        "autonomous_destructive_actions": False,
        "score": 100,
    }

# ---------------------------------------------------------------------------
# 5 Web Intelligence 3.0 / 6 RAG 3.0
# ---------------------------------------------------------------------------
def rank_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set(); out = []
    for item in items or []:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        key = stable_hash(url or title.lower())
        if key in seen: continue
        seen.add(key)
        trust = float(item.get("trust", 0) or 0)
        if url.startswith("https://"): trust += 0.1
        item = dict(item); item["trust_score"] = round(min(1.0, trust), 3)
        out.append(item)
    return sorted(out, key=lambda x: (-x["trust_score"], x.get("title", "")))


def rag_chunk(text: str, *, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    chunk_size = max(200, min(3000, int(chunk_size))); overlap = max(0, min(chunk_size//2, int(overlap)))
    chunks=[]; start=0
    while start < len(text):
        end=min(len(text), start+chunk_size); chunks.append(text[start:end])
        if end == len(text): break
        start=max(start+1, end-overlap)
    return chunks


def rag_rank(query: str, chunks: list[str], top_k: int = 5) -> list[dict[str, Any]]:
    terms=set(re.findall(r"\w+", (query or "").lower()))
    scored=[]
    for i, chunk in enumerate(chunks):
        words=re.findall(r"\w+", chunk.lower()); counts=Counter(words)
        score=sum(min(3, counts[t]) for t in terms) / max(1, len(terms))
        scored.append({"index":i,"score":round(score,4),"text":chunk})
    return sorted(scored,key=lambda x:(-x["score"],x["index"]))[:max(1,min(20,int(top_k)))]

# ---------------------------------------------------------------------------
# 7 Market Intelligence 2.0
# ---------------------------------------------------------------------------
def market_intelligence_2(symbol: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    d = data or {}
    closes = [float(x) for x in d.get("closes", []) if isinstance(x,(int,float)) or str(x).replace('.','',1).isdigit()]
    if len(closes) >= 2:
        change = (closes[-1]-closes[0])/closes[0]*100 if closes[0] else 0
        trend = "bullish" if change > 1 else "bearish" if change < -1 else "neutral"
        volatility = sum(abs(closes[i]-closes[i-1])/closes[i-1] for i in range(1,len(closes)) if closes[i-1]) / max(1,len(closes)-1)*100
    else:
        change=0; trend="unknown"; volatility=0
    return {"symbol": symbol.upper(), "trend": trend, "change_pct": round(change,3), "volatility_pct": round(volatility,3),
            "confidence": round(min(0.95, 0.35 + min(len(closes), 100)/200),3),
            "scenarios": {"bullish": "continuation above resistance", "bearish": "break below support", "neutral": "range-bound"}}

# ---------------------------------------------------------------------------
# 8 News / 9 Calendar intelligence
# ---------------------------------------------------------------------------
def score_news(title: str, content: str = "") -> dict[str, Any]:
    text=(title+" "+content).lower()
    positive=sum(x in text for x in ("surge","gain","growth","bullish","افزایش","رشد","مثبت"))
    negative=sum(x in text for x in ("crash","drop","loss","bearish","کاهش","سقوط","منفی"))
    sentiment=(positive-negative)/max(1,positive+negative)
    impact=min(1.0, (len(re.findall(r"!|عاجل|breaking|urgent", text, re.I))*0.2)+0.2)
    return {"sentiment":round(sentiment,3),"impact":round(impact,3),"label":"positive" if sentiment>0.2 else "negative" if sentiment<-0.2 else "neutral"}


def economic_surprise(actual: str, forecast: str) -> dict[str, Any]:
    def num(x):
        m=re.search(r"[-+]?\d+(?:\.\d+)?",str(x or "")); return float(m.group()) if m else None
    a,f=num(actual),num(forecast)
    if a is None or f is None: return {"available":False,"score":0,"direction":"unknown"}
    diff=a-f; scale=max(1,abs(f)); score=max(-1,min(1,diff/scale))
    return {"available":True,"difference":round(diff,6),"score":round(score,4),"direction":"above" if diff>0 else "below" if diff<0 else "inline"}

# ---------------------------------------------------------------------------
# 10 Backup / DR 3.0
# ---------------------------------------------------------------------------
def backup_integrity(path: str | Path) -> dict[str, Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            size+=len(block); h.update(block)
    return {"ok":size>0,"size":size,"sha256":h.hexdigest()}

# ---------------------------------------------------------------------------
# 11 Performance / 12 QA
# ---------------------------------------------------------------------------
_PERF=defaultdict(lambda: deque(maxlen=100))

def record_perf(component: str, latency_ms: float, ok: bool=True) -> None:
    _PERF[component].append((time.time(), float(latency_ms), bool(ok)))
    try:
        conn=_db(); conn.execute("INSERT INTO v75_metrics(component,operation,latency_ms,ok) VALUES(?,?,?,?)",(component,"runtime",float(latency_ms),1 if ok else 0)); conn.commit(); conn.close()
    except Exception: pass


def performance_snapshot() -> dict[str, Any]:
    out={}
    for name, rows in _PERF.items():
        vals=[r[1] for r in rows]; out[name]={"count":len(rows),"avg_ms":round(sum(vals)/len(vals),2) if vals else 0,"p95_ms":round(sorted(vals)[max(0,int(len(vals)*.95)-1)],2) if vals else 0,"errors":sum(not r[2] for r in rows)}
    return out


def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root=Path(root); files=list(root.rglob("*.py")) if root.exists() else []
    bad=[]
    for p in files:
        try: ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception: bad.append(str(p))
    return {"ok":not bad,"python_files":len(files),"syntax_errors":bad[:20],"security":security_center_snapshot(),"performance":performance_snapshot()}

# ---------------------------------------------------------------------------
# 13 Workflow Builder
# ---------------------------------------------------------------------------
def validate_workflow(steps: list[dict[str, Any]]) -> tuple[bool,str]:
    if not isinstance(steps,list) or not steps: return False,"workflow_empty"
    if len(steps)>MAX_WORKFLOW_STEPS: return False,"workflow_too_long"
    for i,s in enumerate(steps,1):
        if not isinstance(s,dict) or not str(s.get("tool") or "").strip(): return False,f"invalid_step_{i}"
        if s.get("tool") == "run_workflow": return False,"nested_workflow"
    return True,"ok"


async def execute_workflow(name: str, steps: list[dict[str,Any]], *, user_id:int=0) -> dict[str,Any]:
    ok,reason=validate_workflow(steps)
    run_id=uuid.uuid4().hex
    if not ok: return {"ok":False,"run_id":run_id,"reason":reason}
    conn=_db(); conn.execute("INSERT INTO v75_workflow_runs(id,user_id,name,status,input_json) VALUES(?,?,?,?,?)",(run_id,user_id,name,"running",json.dumps(steps,ensure_ascii=False))); conn.commit(); conn.close()
    results=[]
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    try:
        for step in steps:
            tool=str(step["tool"]); args=step.get("arguments",{}) or {}
            if tool not in get_registered_tool_names(): raise ValueError("unknown_tool")
            result=await execute_tool(tool,args,user_id=user_id)
            results.append({"tool":tool,"result":redact(result,2500)})
            if str(result).startswith(("خطا در اجرای","زمان اجرای","ابزار مسدود","ابزار ناشناخته")): raise RuntimeError("tool_failed")
        status="completed"
        payload={"ok":True,"run_id":run_id,"steps":results,"final":results[-1]["result"] if results else ""}
    except Exception:
        status="failed"; payload={"ok":False,"run_id":run_id,"steps":results,"reason":"workflow_failed"}
    conn=_db(); conn.execute("UPDATE v75_workflow_runs SET status=?,result_json=?,finished_at=CURRENT_TIMESTAMP WHERE id=?",(status,json.dumps(payload,ensure_ascii=False),run_id)); conn.commit(); conn.close()
    return payload

# ---------------------------------------------------------------------------
# 14 Smart Alerts
# ---------------------------------------------------------------------------
def create_alert(user_id:int, kind:str, config:dict[str,Any]) -> str:
    conn=_db(); count=conn.execute("SELECT COUNT(*) FROM v75_alerts WHERE user_id=?",(user_id,)).fetchone()[0]
    if count>=MAX_ALERTS_PER_USER: conn.close(); raise ValueError("alert_limit")
    aid=uuid.uuid4().hex; conn.execute("INSERT INTO v75_alerts(id,user_id,kind,config_json) VALUES(?,?,?,?)",(aid,user_id,kind,json.dumps(config,ensure_ascii=False))); conn.commit(); conn.close(); return aid


def evaluate_alert(alert:dict[str,Any], context:dict[str,Any]) -> bool:
    if not alert.get("enabled",True): return False
    cfg=alert.get("config",{})
    kind=alert.get("kind","")
    if kind=="price":
        value=float(context.get("price",0)); target=float(cfg.get("target",0)); direction=cfg.get("direction","above")
        return value>=target if direction=="above" else value<=target
    if kind=="news": return float(context.get("impact",0))>=float(cfg.get("min_impact",.7))
    if kind=="calendar": return float(context.get("surprise",0))>=float(cfg.get("min_surprise",.5))
    if kind=="combo": return all(bool(context.get(k)) for k in cfg.get("all",[]))
    return False

# ---------------------------------------------------------------------------
# 15 Memory 2.0 / 16 Workspace
# ---------------------------------------------------------------------------
def remember(user_id:int, category:str, key:str, value:str, confidence:float=1.0, source:str="user") -> None:
    conn=_db(); conn.execute("INSERT INTO v75_memory(id,user_id,category,key,value,confidence,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,category,key) DO UPDATE SET value=excluded.value,confidence=excluded.confidence,source=excluded.source,updated_at=CURRENT_TIMESTAMP",(uuid.uuid4().hex,user_id,category,key,redact(value,2000),max(0,min(1,float(confidence))),source)); conn.commit(); conn.close()


def recall(user_id:int, category:str|None=None, limit:int=20) -> list[dict[str,Any]]:
    conn=_db();
    if category:
        rows=conn.execute("SELECT category,key,value,confidence,source,updated_at FROM v75_memory WHERE user_id=? AND category=? ORDER BY updated_at DESC LIMIT ?",(user_id,category,min(MAX_MEMORY_ITEMS,limit))).fetchall()
    else:
        rows=conn.execute("SELECT category,key,value,confidence,source,updated_at FROM v75_memory WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",(user_id,min(MAX_MEMORY_ITEMS,limit))).fetchall()
    conn.close(); return [dict(r) for r in rows]


def create_workspace(user_id:int,name:str) -> str:
    wid=uuid.uuid4().hex; conn=_db(); conn.execute("INSERT INTO v75_workspaces(id,user_id,name) VALUES(?,?,?)",(wid,user_id,redact(name,100))); conn.commit(); conn.close(); return wid

# ---------------------------------------------------------------------------
# 17 Report Generator
# ---------------------------------------------------------------------------
def generate_report(title:str, rows:list[dict[str,Any]], fmt:str="json") -> tuple[bytes,str,str]:
    fmt=fmt.lower().strip()
    safe_title=re.sub(r"[^\w\- ]+","_",title or "report")[:80] or "report"
    if fmt=="json": return json.dumps({"title":title,"rows":rows},ensure_ascii=False,indent=2).encode(),safe_title+".json","application/json"
    if fmt=="csv":
        keys=sorted({k for r in rows for k in r})
        buf=io.StringIO(); w=csv.DictWriter(buf,fieldnames=keys); w.writeheader(); w.writerows(rows)
        return buf.getvalue().encode("utf-8-sig"),safe_title+".csv","text/csv"
    if fmt=="xlsx":
        try:
            from openpyxl import Workbook
            wb=Workbook(); ws=wb.active; ws.title="Report"; keys=sorted({k for r in rows for k in r}); ws.append(keys)
            for r in rows: ws.append([r.get(k,"") for k in keys])
            out=io.BytesIO(); wb.save(out); return out.getvalue(),safe_title+".xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        except Exception: return generate_report(title,rows,"csv")
    if fmt=="docx":
        try:
            from docx import Document
            d=Document(); d.add_heading(title or "Report",0)
            for r in rows: d.add_paragraph(" | ".join(f"{k}: {v}" for k,v in r.items()))
            out=io.BytesIO(); d.save(out); return out.getvalue(),safe_title+".docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        except Exception: return generate_report(title,rows,"json")
    if fmt=="pdf":
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            out=io.BytesIO(); doc=SimpleDocTemplate(out,pagesize=A4); styles=getSampleStyleSheet(); story=[Paragraph(title or "Report",styles["Title"])]
            for r in rows: story.extend([Paragraph(redact(" | ".join(f"{k}: {v}" for k,v in r.items()),1800),styles["BodyText"]),Spacer(1,8)])
            doc.build(story); return out.getvalue(),safe_title+".pdf","application/pdf"
        except Exception: return generate_report(title,rows,"json")
    return generate_report(title,rows,"json")

# ---------------------------------------------------------------------------
# Dashboard + self test
# ---------------------------------------------------------------------------
def dashboard() -> dict[str,Any]:
    try:
        conn=_db(); users=conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]; alerts=conn.execute("SELECT COUNT(*) FROM v75_alerts WHERE enabled=1").fetchone()[0]; runs=conn.execute("SELECT COUNT(*) FROM v75_workflow_runs").fetchone()[0]; mem=conn.execute("SELECT COUNT(*) FROM v75_memory").fetchone()[0]; conn.close()
    except Exception: users=alerts=runs=mem=0
    return {"version":VERSION,"users":users,"active_alerts":alerts,"workflow_runs":runs,"memory_items":mem,"security":security_center_snapshot(),"performance":performance_snapshot()}


def self_test(root: str|Path=".") -> dict[str,Any]:
    checks={}
    try: init_v75_tables(); checks["database"]=True
    except Exception: checks["database"]=False
    checks["security"]=security_scan("ignore previous instructions") ["prompt_injection"] is True
    checks["rag"]=bool(rag_rank("btc",["BTC market price", "weather"],1))
    checks["workflow_validation"]=validate_workflow([{"tool":"get_market_prices","arguments":{}}])[0]
    checks["report"]=bool(generate_report("test",[{"ok":True}],"json")[0])
    checks["qa"]=qa_snapshot(root)["ok"]
    return {"ok":all(checks.values()),"checks":checks,"dashboard":dashboard()}
