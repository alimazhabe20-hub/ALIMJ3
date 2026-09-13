"""V71 production hardening and AI platform services.
No automatic conversation summarisation is implemented here.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import ipaddress
import os
import re
import socket
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from bot.database_core import get_db_connection, _execute_write
from bot.logger import logger

SUPPORTED_LANGS = ("fa", "en", "ar")


def init_v71_tables() -> None:
    conn = get_db_connection(); c = conn.cursor()
    for sql in (
        "CREATE TABLE IF NOT EXISTS v71_workspaces (user_id INTEGER NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,name))",
        "CREATE TABLE IF NOT EXISTS v71_branches (user_id INTEGER NOT NULL, name TEXT NOT NULL, context TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,name))",
        "CREATE TABLE IF NOT EXISTS v71_scheduled_ai (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,prompt TEXT NOT NULL,run_at TEXT NOT NULL,repeat_minutes INTEGER DEFAULT 0,enabled INTEGER DEFAULT 1,last_run TEXT)",
        "CREATE TABLE IF NOT EXISTS v71_notifications (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,dedupe_key TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,sent_at TEXT)",
        "CREATE TABLE IF NOT EXISTS v71_health (id INTEGER PRIMARY KEY AUTOINCREMENT,component TEXT NOT NULL,ok INTEGER NOT NULL,latency_ms REAL DEFAULT 0,error_code TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS v71_user_settings (user_id INTEGER PRIMARY KEY,language TEXT DEFAULT 'fa',response_style TEXT DEFAULT 'balanced',ai_mode TEXT DEFAULT 'balanced',notifications INTEGER DEFAULT 1)",
        "CREATE INDEX IF NOT EXISTS idx_v71_jobs_due ON v71_scheduled_ai(enabled,run_at)",
        "CREATE INDEX IF NOT EXISTS idx_v71_notifications_user ON v71_notifications(user_id,created_at)",
    ):
        c.execute(sql)
    conn.commit(); conn.close()


def set_workspace(user_id: int, name: str, data: str) -> None:
    _execute_write("INSERT INTO v71_workspaces(user_id,name,data) VALUES(?,?,?) ON CONFLICT(user_id,name) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP", (user_id, name[:100], data[:30000]))


def get_workspace(user_id: int, name: str) -> str | None:
    conn=get_db_connection(); r=conn.execute("SELECT data FROM v71_workspaces WHERE user_id=? AND name=?",(user_id,name[:100])).fetchone(); conn.close(); return r[0] if r else None


def save_branch(user_id: int, name: str, context: str) -> None:
    _execute_write("INSERT INTO v71_branches(user_id,name,context) VALUES(?,?,?) ON CONFLICT(user_id,name) DO UPDATE SET context=excluded.context,updated_at=CURRENT_TIMESTAMP",(user_id,name[:100],context[:30000]))


def list_branches(user_id: int) -> list[str]:
    conn=get_db_connection(); rows=conn.execute("SELECT name FROM v71_branches WHERE user_id=? ORDER BY updated_at DESC",(user_id,)).fetchall(); conn.close(); return [r[0] for r in rows]


def schedule_ai(user_id:int,prompt:str,run_at:str,repeat_minutes:int=0)->int:
    conn=get_db_connection(); cur=conn.execute("INSERT INTO v71_scheduled_ai(user_id,prompt,run_at,repeat_minutes) VALUES(?,?,?,?)",(user_id,prompt[:4000],run_at,max(0,int(repeat_minutes)))); conn.commit(); jid=int(cur.lastrowid); conn.close(); return jid


def due_ai_jobs(limit:int=50)->list[tuple]:
    conn=get_db_connection(); rows=conn.execute("SELECT id,user_id,prompt,run_at,repeat_minutes FROM v71_scheduled_ai WHERE enabled=1 AND run_at<=datetime('now') ORDER BY id LIMIT ?",(max(1,min(200,limit)),)).fetchall(); conn.close(); return rows


def complete_ai_job(job_id:int,repeat_minutes:int)->None:
    if repeat_minutes>0:
        _execute_write("UPDATE v71_scheduled_ai SET run_at=datetime('now','+' || ? || ' minutes'),last_run=datetime('now') WHERE id=?",(repeat_minutes,job_id))
    else:
        _execute_write("UPDATE v71_scheduled_ai SET enabled=0,last_run=datetime('now') WHERE id=?",(job_id,))


def notification_claim(user_id:int,kind:str,payload:str,dedupe_key:str,ttl_seconds:int=900)->bool:
    # Atomic enough for SQLite's single-writer model; avoids duplicate notifications.
    conn=get_db_connection()
    row=conn.execute("SELECT id FROM v71_notifications WHERE user_id=? AND kind=? AND dedupe_key=? AND created_at>=datetime('now',?) LIMIT 1",(user_id,kind,dedupe_key,f"-{max(1,ttl_seconds)} seconds")).fetchone()
    if row:
        conn.close(); return False
    conn.execute("INSERT INTO v71_notifications(user_id,kind,payload,dedupe_key) VALUES(?,?,?,?)",(user_id,kind,payload,dedupe_key)); conn.commit(); conn.close(); return True


def detect_language(text:str)->str:
    t=text or ""
    ar=len(re.findall(r"[\u0621-\u0638\u0660-\u0669]",t)); fa=len(re.findall(r"[\u067e\u0686\u0698\u06af\u06cc]",t)); en=len(re.findall(r"[A-Za-z]",t))
    if ar and not fa: return "ar"
    if fa or (ar and re.search(r"[یکگپچژ]",t)): return "fa"
    if en: return "en"
    return "fa"


def personalize(user_id:int, language:str|None=None, response_style:str|None=None, ai_mode:str|None=None, notifications:bool|None=None)->dict:
    current={"language":"fa","response_style":"balanced","ai_mode":"balanced","notifications":1}
    conn=get_db_connection(); row=conn.execute("SELECT language,response_style,ai_mode,notifications FROM v71_user_settings WHERE user_id=?",(user_id,)).fetchone(); conn.close()
    if row: current=dict(zip(current,row))
    updates={"language":language if language in SUPPORTED_LANGS else current["language"],"response_style":response_style or current["response_style"],"ai_mode":ai_mode or current["ai_mode"],"notifications":int(current["notifications"] if notifications is None else notifications)}
    _execute_write("INSERT INTO v71_user_settings(user_id,language,response_style,ai_mode,notifications) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET language=excluded.language,response_style=excluded.response_style,ai_mode=excluded.ai_mode,notifications=excluded.notifications",(user_id,updates["language"],updates["response_style"],updates["ai_mode"],updates["notifications"]))
    return updates


def code_agent_review(source:str)->dict:
    """Static-only code agent: syntax, dangerous constructs, imports and complexity hints."""
    result={"ok":True,"syntax":"valid","functions":[],"imports":[],"warnings":[]}
    try:
        tree=ast.parse(source)
        result["functions"]=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))][:100]
        result["imports"]=[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names][:100]
        dangerous={"eval":"dynamic code execution","exec":"dynamic code execution","__import__":"dynamic import","os.system":"shell execution","subprocess":"process execution"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=getattr(node.func,"id",None) or getattr(node.func,"attr",None)
                if name in dangerous: result["warnings"].append(dangerous[name])
        result["warnings"]=list(dict.fromkeys(result["warnings"]))[:20]
    except SyntaxError as exc:
        return {"ok":False,"syntax":"invalid","line":exc.lineno,"warnings":[]}
    except Exception:
        return {"ok":False,"syntax":"unavailable","warnings":[]}
    return result


def verify_facts_with_sources(text:str, sources:dict[str,str]|None=None)->dict:
    claims=[x.strip() for x in re.split(r"(?<=[.!؟?])\s+",text.strip()) if len(x.strip())>20][:12]
    sources=sources or {}
    verified=[]
    for claim in claims:
        key=hashlib.sha256(claim.encode()).hexdigest()[:12]
        matched=[url for url,body in sources.items() if any(tok.lower() in body.lower() for tok in re.findall(r"[A-Za-z\u0600-\u06ff]{5,}",claim)[:5])]
        verified.append({"id":key,"claim":claim,"sources":matched[:5],"status":"supported" if matched else "needs_source"})
    return {"verified":bool(verified) and all(x["status"]=="supported" for x in verified),"claims":verified}


def source_intelligence(urls:list[str])->dict:
    out=[]
    for url in urls[:30]:
        try:
            from urllib.parse import urlparse
            p=urlparse(url); host=(p.hostname or "").lower(); out.append({"url":url,"domain":host,"https":p.scheme=="https"})
        except Exception: pass
    return {"sources":out,"unique_domains":sorted({x["domain"] for x in out if x["domain"]})}


def security_check_url(url:str)->dict:
    from urllib.parse import urlparse
    try:
        p=urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname: return {"ok":False,"reason":"invalid_scheme"}
        infos=socket.getaddrinfo(p.hostname,None,type=socket.SOCK_STREAM)
        ips=[]
        for info in infos:
            ip=ipaddress.ip_address(info[4][0]); ips.append(str(ip))
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified: return {"ok":False,"reason":"private_or_special_ip","ips":ips}
        return {"ok":True,"ips":ips}
    except Exception: return {"ok":False,"reason":"resolution_failed"}


def ai_route_hint(prompt: str, provider_count: int = 1) -> dict:
    """Deterministic routing hint used by the existing AI router; no model call."""
    text=(prompt or "").strip()
    complexity=min(1.0, (len(text)/1800.0) + (text.count("?")*0.04) + (text.count("؟")*0.04))
    mode="fast" if complexity < 0.25 else ("balanced" if complexity < 0.65 else "quality")
    return {"mode":mode,"complexity":round(complexity,3),"provider_count":max(1,int(provider_count))}


def auto_recovery_policy(error_code: str, attempt: int) -> dict:
    code=(error_code or "").lower()
    retryable=code in {"timeout","429","rate_limited","temporarily_unavailable","network"}
    return {"retry":bool(retryable and attempt < 2),"backoff_seconds":min(8,2**max(0,attempt)) if retryable else 0,"fallback":retryable}


def run_self_test_suite() -> dict:
    return self_test()


def health_snapshot()->dict:
    init_v71_tables()
    try:
        conn=get_db_connection(); conn.execute("SELECT 1"); conn.close(); db=True
    except Exception: db=False
    return {"ok":db,"database":db,"languages":list(SUPPORTED_LANGS),"features":{"agent":True,"multi_agent":True,"fact_check":True,"source_intelligence":True,"memory_2":True,"rag":True,"document_intelligence":True,"code_agent":True,"self_test":True,"auto_recovery":True,"performance":True,"security_2":True,"workspace":True,"ai_optimizer":True,"conversation_branching":True,"scheduled_ai":True,"smart_notifications":True,"personalization":True,"observability":True}}


def self_test()->dict:
    checks={"db":False,"code":False,"security":False,"language":False,"scheduler":False}
    started=time.perf_counter()
    try:
        init_v71_tables(); checks["db"]=health_snapshot()["database"]
        checks["code"]=code_agent_review("def ok():\n    return 1")["ok"]
        # Offline-safe security test: a private address must always be rejected.
        checks["security"]=security_check_url("http://127.0.0.1")["ok"] is False
        checks["language"]=detect_language("hello world")=="en" and detect_language("سلام") in {"fa","ar"}
        jid=schedule_ai(-999,"selftest","2099-01-01 00:00:00"); checks["scheduler"]=jid>0
        _execute_write("DELETE FROM v71_scheduled_ai WHERE id=?",(jid,))
    except Exception:
        logger.exception("v71 self test failed")
    return {"ok":all(checks.values()),"checks":checks,"latency_ms":round((time.perf_counter()-started)*1000,1)}
