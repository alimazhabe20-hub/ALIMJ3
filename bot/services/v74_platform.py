"""V74 Reliability & Intelligence Core.

Twelve bounded production subsystems are implemented here:
1) Agent 2.0, 2) Tool System 2.0, 3) Security 2.0, 4) Self-Healing 2.0,
5) Performance 2.0, 6) QA 2.0, 7) Observability, 8) Web Intelligence 2.0,
9) RAG 2.0, 10) Persistence 2.0, 11) Provider Reliability, 12) Runtime/API Reliability.

Design rules: bounded work, fail closed, no secret exposure, no destructive autonomous
actions, deterministic fallbacks, and compatibility with the existing V70-V73 stack.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
import sqlite3
import time
import urllib.parse
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from bot.logger import logger

VERSION = "74.0.0"
MAX_AGENT_STEPS = max(1, min(10, int(os.getenv("V74_AGENT_MAX_STEPS", "6"))))
MAX_AGENT_CALLS = max(2, min(24, int(os.getenv("V74_AGENT_MAX_CALLS", "12"))))
MAX_AGENT_REPAIRS = max(0, min(3, int(os.getenv("V74_AGENT_MAX_REPAIRS", "2"))))
AGENT_BUDGET_MS = max(5000, min(120000, int(os.getenv("V74_AGENT_BUDGET_MS", "45000"))))
TOOL_RETRIES = max(0, min(3, int(os.getenv("V74_TOOL_RETRIES", "1"))))
CACHE_TTL = max(2, int(os.getenv("V74_CACHE_TTL", "20")))
CACHE_MAX = max(64, int(os.getenv("V74_CACHE_MAX", "2048")))

# ---------------------------------------------------------------------------
# 3) Security 2.0
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = (
    re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)(sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,})"),
)
_PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+(?:(?:all|any)\s+)?(?:previous|prior)\s+instructions",
    r"نادیده\s+بگیر\s+(همه|تمام|دستورهای|دستورات)",
    r"دستورهای\s+سیستم\s+را\s+نادیده",
    r"system\s+prompt|developer\s+message",
    r"reveal\s+(the\s+)?(system|developer)\s+prompt",
    r"افشای?\s+(پرامپت|دستور)\s+(سیستم|سازنده)",
)


def redact_secrets(value: Any) -> str:
    text = str(value if value is not None else "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(
            lambda m: (m.group(1) + "=[REDACTED]") if m.lastindex == 2 else "[REDACTED]",
            text,
        )
    return text[:5000]


def detect_prompt_injection(text: str) -> dict[str, Any]:
    sample = (text or "")[:12000]
    hits = [p for p in _PROMPT_INJECTION_PATTERNS if re.search(p, sample, re.I)]
    return {"detected": bool(hits), "count": len(hits), "severity": "high" if len(hits) >= 2 else "medium" if hits else "none"}


def safe_public_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    raw = (url or "").strip()
    if not raw or len(raw) > 2048:
        return False, "invalid_url"
    try:
        p = urllib.parse.urlsplit(raw)
    except Exception:
        return False, "invalid_url"
    allowed = {"https", "http"} if allow_http else {"https"}
    if p.scheme.lower() not in allowed or not p.hostname or p.username or p.password:
        return False, "unsafe_scheme_or_credentials"
    host = p.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        return False, "private_host"
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        return False, "dns_failed"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False, "private_host"
    return True, "ok"


def safe_archive_member(name: str) -> bool:
    n = (name or "").replace("\\", "/")
    if not n or n.startswith("/") or re.match(r"^[A-Za-z]:", n):
        return False
    return ".." not in [p for p in n.split("/") if p]


def safe_path(path: str | Path, root: str | Path) -> bool:
    try:
        p, r = Path(path).resolve(), Path(root).resolve()
        return p == r or r in p.parents
    except Exception:
        return False


def sanitize_untrusted_text(text: str, max_chars: int = 12000) -> str:
    """Keep external text bounded and explicitly mark it as untrusted context."""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(text or ""))
    return "[UNTRUSTED_EXTERNAL_CONTENT]\n" + redact_secrets(clean)[:max_chars]

# ---------------------------------------------------------------------------
# 2) Tool System 2.0
# ---------------------------------------------------------------------------
@dataclass
class ToolPolicy:
    name: str
    version: str = "1.0"
    risk: str = "read"
    network: bool = False
    timeout: float = 25.0
    retries: int = TOOL_RETRIES
    cache_ttl: int = 0
    dependencies: tuple[str, ...] = ()
    enabled: bool = True
    schema_validated: bool = True
    owner: str = "core"

_TOOL_POLICIES: dict[str, ToolPolicy] = {}
_TOOL_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=30))
_TOOL_DISABLED_UNTIL: dict[str, float] = {}


def register_tool_policy(name: str, **kwargs: Any) -> ToolPolicy:
    policy = ToolPolicy(name=name, **{k: v for k, v in kwargs.items() if k in ToolPolicy.__dataclass_fields__})
    _TOOL_POLICIES[name] = policy
    return policy


def tool_policy_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {
        name: {
            "version": p.version, "risk": p.risk, "network": p.network,
            "timeout": p.timeout, "retries": p.retries, "cache_ttl": p.cache_ttl,
            "dependencies": list(p.dependencies), "enabled": p.enabled,
            "cooldown": round(max(0.0, _TOOL_DISABLED_UNTIL.get(name, 0) - now), 1),
        }
        for name, p in sorted(_TOOL_POLICIES.items())
    }


def tool_allowed(name: str, *, source: str = "system", approved: bool = False) -> tuple[bool, str]:
    p = _TOOL_POLICIES.get(name)
    if p and not p.enabled:
        return False, "disabled"
    if p and time.monotonic() < _TOOL_DISABLED_UNTIL.get(name, 0):
        return False, "cooldown"
    if p and p.risk in {"write", "admin"} and source in {"agent", "agent_repair"} and not approved:
        return False, "approval_required"
    return True, "ok"


def note_tool_failure(name: str) -> bool:
    now = time.monotonic()
    q = _TOOL_FAILURES[name]
    q.append(now)
    recent = sum(1 for x in q if now - x <= 120)
    if recent >= max(3, int(os.getenv("V74_TOOL_FAILURE_THRESHOLD", "4"))):
        _TOOL_DISABLED_UNTIL[name] = now + max(10, int(os.getenv("V74_TOOL_COOLDOWN", "45")))
        return True
    return False


def recover_tool(name: str) -> dict[str, Any]:
    _TOOL_DISABLED_UNTIL[name] = time.monotonic() + 3
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache()
    except Exception:
        pass
    return {"tool": name, "recovered": True, "action": "cache_clear_and_short_cooldown"}

# ---------------------------------------------------------------------------
# 1) Agent 2.0
# ---------------------------------------------------------------------------
@dataclass
class AgentStep:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


def _agent_intents(goal: str, available: set[str]) -> list[AgentStep]:
    q = (goal or "").lower()
    patterns: list[tuple[str, str, str, dict[str, Any], int]] = [
        (r"هوا|آب\s*و\s*هوا|دما|باران|weather", "get_weather", "weather", {}, 4),
        (r"آلودگی|کیفیت\s*هوا|aqi|air", "get_air_quality", "air_quality", {}, 4),
        (r"قیمت|بازار|کریپتو|بیت.?کوین|طلا|دلار|ارز|market|price", "get_market_prices", "market", {}, 5),
        (r"تقویم\s*اقتصادی|economic\s*calendar|اخبار\s*اقتصادی", "get_economic_calendar", "calendar", {}, 5),
        (r"مستندات|راهنما|قابلیت.*ربات|knowledge|documentation", "search_knowledge_base", "knowledge", {"query": goal}, 4),
        (r"اینترنت|وب|جستجو|خبر|اخبار|latest|news|search", "hybrid_retrieve", "web", {"query": goal, "include_web": True}, 5),
        (r"خرید|بخر|فروشگاه|shopping|قیمت.*محصول", "search_shopping", "shopping", {"query": goal, "source": "all", "max_results": 8}, 4),
    ]
    found: list[tuple[int, AgentStep]] = []
    for pattern, tool, reason, args, score in patterns:
        if tool in available and re.search(pattern, q, re.I):
            found.append((score, AgentStep(tool, dict(args), reason)))
    found.sort(key=lambda x: (-x[0], x[1].tool))
    return [x[1] for x in found[:MAX_AGENT_STEPS]]


def _should_stop(goal: str, step: AgentStep, result: str) -> bool:
    low = (goal + " " + result).lower()
    if any(x in low for x in ("فقط", "تنها", "just", "only")) and step.reason in {"market", "weather", "air_quality", "calendar"}:
        return True
    return bool(result) and not str(result).startswith(("خطا", "ابزار ناشناخته", "ابزار مسدود", "زمان اجرای")) and step.reason in {"weather", "air_quality"}


async def run_agent_2(goal: str, *, user_id: int = 0) -> str:
    goal = (goal or "").strip()[:6000]
    if not goal:
        return "هدف خالی است."
    injection = detect_prompt_injection(goal)
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names
    available = get_registered_tool_names()
    plan = _agent_intents(goal, available)
    if not plan:
        return "برای این درخواست ابزار مطمئنی لازم نیست؛ پاسخ مستقیم مناسب‌تر است."
    started = time.monotonic()
    trace: list[dict[str, Any]] = []
    used: set[str] = set()
    calls = repairs = 0
    for idx, step in enumerate(plan, 1):
        if calls >= MAX_AGENT_CALLS or (time.monotonic() - started) * 1000 >= AGENT_BUDGET_MS or step.tool in used:
            break
        allowed, reason = tool_allowed(step.tool, source="agent")
        if not allowed:
            trace.append({"step": idx, "tool": step.tool, "ok": False, "blocked": reason})
            continue
        used.add(step.tool); calls += 1
        t0 = time.monotonic()
        try:
            result = await execute_tool(step.tool, step.arguments, user_id=user_id, source="agent")
            ok = not str(result).startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته", "ابزار مسدود", "ابزار موقتاً"))
            trace.append({"step": idx, "tool": step.tool, "reason": step.reason, "ok": ok,
                          "elapsed_ms": round((time.monotonic()-t0)*1000, 1), "result": redact_secrets(result)[:2500]})
            if not ok and repairs < MAX_AGENT_REPAIRS and "hybrid_retrieve" in available and "hybrid_retrieve" not in used:
                repairs += 1; calls += 1; used.add("hybrid_retrieve")
                repaired = await execute_tool("hybrid_retrieve", {"query": goal, "include_web": True}, user_id=user_id, source="agent_repair")
                trace.append({"step": idx, "tool": "hybrid_retrieve", "repair": True,
                              "ok": not str(repaired).startswith("خطا"), "result": redact_secrets(repaired)[:2500]})
            if ok and _should_stop(goal, step, str(result)):
                break
        except Exception:
            logger.warning("V74 agent step failed", exc_info=True)
            trace.append({"step": idx, "tool": step.tool, "ok": False, "error": "internal_failure"})
            if repairs < MAX_AGENT_REPAIRS:
                repairs += 1
    return json.dumps({"ok": bool(trace), "goal": goal[:500], "steps": trace, "calls": calls,
                       "repairs": repairs, "budget_ms": AGENT_BUDGET_MS,
                       "prompt_injection": injection}, ensure_ascii=False)[:12000]

# ---------------------------------------------------------------------------
# 5) Performance 2.0
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, Any]] = {}
_INFLIGHT: dict[str, asyncio.Task] = {}
_PERF: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})
_SLOW: Counter[str] = Counter()


def cache_get(key: str) -> Any | None:
    item = _CACHE.get(key)
    if not item:
        return None
    if item[0] <= time.monotonic():
        _CACHE.pop(key, None); return None
    return item[1]


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    now = time.monotonic()
    _CACHE[key] = (now + max(1, ttl), value)
    if len(_CACHE) > CACHE_MAX:
        stale = [k for k, (exp, _) in _CACHE.items() if exp <= now]
        for k in stale[: max(1, len(stale)//2)]: _CACHE.pop(k, None)
        if len(_CACHE) > CACHE_MAX:
            for k in list(_CACHE)[: len(_CACHE)-CACHE_MAX]: _CACHE.pop(k, None)


def clear_performance_cache() -> None:
    _CACHE.clear()


def record_performance(component: str, elapsed_ms: float, ok: bool = True) -> None:
    p = _PERF[component]
    p["calls"] += 1; p["total_ms"] += max(0.0, elapsed_ms); p["max_ms"] = max(p["max_ms"], elapsed_ms)
    if not ok: p["errors"] += 1
    if elapsed_ms >= float(os.getenv("V74_SLOW_MS", "3000")): _SLOW[component] += 1


def performance_snapshot() -> dict[str, Any]:
    return {k: {"calls": int(v["calls"]), "errors": int(v["errors"]),
                 "avg_ms": round(v["total_ms"]/max(1, v["calls"]), 2),
                 "max_ms": round(v["max_ms"], 2), "slow_count": _SLOW[k]}
            for k, v in sorted(_PERF.items())}

# ---------------------------------------------------------------------------
# 4) Self-Healing 2.0
# ---------------------------------------------------------------------------
_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=50))
_RECOVERY_LOG: deque[dict[str, Any]] = deque(maxlen=100)


def note_failure(component: str, error: str = "") -> bool:
    now = time.monotonic(); q = _FAILURES[component]; q.append(now)
    threshold = max(3, int(os.getenv("V74_FAILURE_THRESHOLD", "4")))
    tripped = sum(1 for x in q if now-x <= 120) >= threshold
    if tripped:
        _RECOVERY_LOG.append({"component": component, "action": "cooldown", "error": redact_secrets(error)[:500], "at": time.time()})
    return tripped


def recover_component(component: str) -> dict[str, Any]:
    actions: list[str] = []
    try:
        clear_performance_cache(); actions.append("performance_cache_cleared")
    except Exception: pass
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache(); actions.append("tool_cache_cleared")
    except Exception: pass
    _RECOVERY_LOG.append({"component": component, "action": "recovered", "at": time.time()})
    return {"component": component, "recovered": True, "actions": actions}


def healing_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {k: {"failures_120s": sum(1 for x in q if now-x <= 120)} for k, q in _FAILURES.items()}

# ---------------------------------------------------------------------------
# 8) Web Intelligence 2.0
# ---------------------------------------------------------------------------
_SOURCE_WEIGHTS = {"wikipedia.org": .75, "reuters.com": .95, "bbc.com": .90, "gov": .98, "edu": .95}


def source_score(url: str, text: str = "", base: float = .4) -> float:
    try: host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except Exception: host = ""
    score = base + (.05 if url.lower().startswith("https://") else 0)
    for domain, weight in _SOURCE_WEIGHTS.items():
        if host.endswith(domain): score = max(score, weight)
    if len(text) > 1500: score += .05
    return round(min(1.0, score), 4)


def dedupe_sources(sources: Iterable[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    seen: set[str] = set(); out: list[dict[str, Any]] = []
    for item in sources:
        url = str(item.get("url") or "").strip()
        ok, _ = safe_public_url(url)
        if not ok or url in seen: continue
        seen.add(url)
        text = sanitize_untrusted_text(str(item.get("text") or ""), 16000)
        out.append({**item, "url": url, "text": text, "score": source_score(url, text, float(item.get("score") or .4))})
    return sorted(out, key=lambda x: (-x["score"], x["url"]))[:max(1, min(limit, 50))]


def verify_claims(claims: Iterable[str], sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    srcs = dedupe_sources(list(sources), 30); results=[]
    for claim in list(claims)[:30]:
        tokens = [t.lower() for t in re.findall(r"[\w\u0600-\u06ff]{4,}", str(claim))][:14]
        evidence=[]
        for src in srcs:
            text = str(src.get("text") or "").lower()
            matched = sum(t in text for t in tokens)
            if matched >= max(2, len(tokens)//3): evidence.append({"url": src["url"], "matches": matched, "score": src["score"]})
        results.append({"claim": str(claim)[:600], "status": "supported_by_sources" if evidence else "needs_independent_source",
                        "evidence": sorted(evidence, key=lambda x: (-x["matches"], -x["score"]))[:5]})
    return results

# ---------------------------------------------------------------------------
# 9) RAG 2.0
# ---------------------------------------------------------------------------
_STOP = set("the and for with that this from are was is به برای و از که این آن را در با است یک های هایو".split())


def rag_tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[\w\u0600-\u06ff]{3,}", str(text or "")) if t.lower() not in _STOP]


def chunk_document(text: str, *, source: str, chunk_chars: int = 1200, overlap: int = 180) -> list[dict[str, Any]]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean: return []
    step = max(1, chunk_chars-overlap); chunks=[]
    for i, start in enumerate(range(0, len(clean), step)):
        piece=clean[start:start+chunk_chars]
        if not piece: break
        chunks.append({"source": source, "chunk": i, "text": piece, "tokens": rag_tokens(piece), "chars": len(piece)})
        if start+chunk_chars >= len(clean): break
    return chunks


def rag_rank(query: str, chunks: Iterable[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    q=Counter(rag_tokens(query)); scored=[]
    for c in chunks:
        toks=Counter(c.get("tokens") or rag_tokens(c.get("text", "")))
        overlap=sum(min(q[t], toks[t]) for t in q)
        if not overlap: continue
        coverage=overlap/max(1,sum(q.values())); density=overlap/max(1,len(toks))
        score=coverage*0.7+density*0.2+min(0.1, len(c.get("text", ""))/12000)
        scored.append((score, coverage, c))
    scored.sort(key=lambda x:(-x[0],-x[1],x[2].get("source", ""),x[2].get("chunk",0)))
    return [{**c, "score": round(s,5), "coverage": round(cov,5)} for s,cov,c in scored[:max(1,min(limit,20))]]


def rag_context(query: str, chunks: Iterable[dict[str, Any]], limit: int = 6, max_chars: int = 9000) -> str:
    blocks=[]; used=0
    for c in rag_rank(query,chunks,limit):
        block=f"[{c['source']}#{c['chunk']} score={c['score']}]\n{sanitize_untrusted_text(c['text'], 2500)}"
        if used+len(block)+2>max_chars: break
        blocks.append(block); used+=len(block)+2
    return "\n\n".join(blocks)

# ---------------------------------------------------------------------------
# 10) Persistence 2.0
# ---------------------------------------------------------------------------
def db_integrity(path: str | Path) -> dict[str, Any]:
    p=Path(path)
    if not p.exists(): return {"ok": False, "reason": "missing", "path": str(p)}
    try:
        conn=sqlite3.connect(str(p), timeout=10)
        row=conn.execute("PRAGMA integrity_check").fetchone(); count=0
        try: count=int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        except sqlite3.Error: pass
        conn.close(); ok=bool(row and row[0]=="ok")
        return {"ok": ok, "integrity": row[0] if row else "unknown", "users": count, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__, "path": str(p)}


def verify_backup(path: str | Path) -> dict[str, Any]:
    result=db_integrity(path); result["backup"] = True; return result


def persistence_snapshot() -> dict[str, Any]:
    try:
        from bot.config import config
        current=db_integrity(config.DB_PATH)
        backup_dir=Path(config.BACKUP_DIR)
        candidates=sorted(backup_dir.glob("bot_*.db"), key=lambda p:p.stat().st_mtime, reverse=True)[:5] if backup_dir.exists() else []
        backups=[verify_backup(p) | {"name": p.name} for p in candidates]
        return {"current": {k:v for k,v in current.items() if k != "path"}, "backups": backups,
                "verified_backups": sum(1 for x in backups if x.get("ok"))}
    except Exception as exc:
        return {"current": {"ok": False, "reason": type(exc).__name__}, "backups": []}

# ---------------------------------------------------------------------------
# 11) Provider Reliability + 12) Runtime/API Reliability
# ---------------------------------------------------------------------------
_PROVIDER: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls":0,"errors":0,"total_ms":0.0,"cooldown_until":0.0})
_RUNTIME: dict[str, Any] = {"started_at": time.time(), "readiness": {}, "last_errors": deque(maxlen=50)}


def provider_event(provider: str, *, ok: bool, elapsed_ms: float) -> None:
    p=_PROVIDER[provider]; p["calls"]+=1; p["total_ms"]+=elapsed_ms
    if not ok: p["errors"]+=1
    if p["errors"] >= 4 and p["errors"] > p["calls"]*.5: p["cooldown_until"]=time.monotonic()+30


def provider_available(provider: str) -> bool:
    return time.monotonic() >= float(_PROVIDER[provider].get("cooldown_until",0))


def provider_snapshot() -> dict[str, Any]:
    return {k:{"calls":int(v["calls"]),"errors":int(v["errors"]),"avg_ms":round(v["total_ms"]/max(1,v["calls"]),2),
               "available":provider_available(k)} for k,v in sorted(_PROVIDER.items())}


def set_readiness(name: str, ok: bool, detail: str = "") -> None:
    _RUNTIME["readiness"][name]={"ok":bool(ok),"detail":redact_secrets(detail)[:300],"updated_at":time.time()}


def runtime_snapshot() -> dict[str, Any]:
    return {"uptime_s":round(max(0,time.time()-_RUNTIME["started_at"]),1), "readiness":dict(_RUNTIME["readiness"]),
            "last_errors":list(_RUNTIME["last_errors"])}

# ---------------------------------------------------------------------------
# 6) QA 2.0
# ---------------------------------------------------------------------------
def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root=Path(root); py=list(root.rglob("*.py")); syntax=[]; unsafe=[]
    for p in py:
        try: ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception as exc: syntax.append(f"{p}: {type(exc).__name__}")
        try:
            text=p.read_text(encoding="utf-8")
            if re.search(r"(?i)eval\s*\(|exec\s*\(|subprocess\.Popen\s*\(",text): unsafe.append(str(p))
        except Exception: pass
    return {"python_files":len(py),"syntax_ok":not syntax,"syntax_errors":syntax[:50],
            "unsafe_pattern_files":unsafe[:50],"security_checks":"enabled","agent_limits":
            {"steps":MAX_AGENT_STEPS,"calls":MAX_AGENT_CALLS,"repairs":MAX_AGENT_REPAIRS,"budget_ms":AGENT_BUDGET_MS}}

# ---------------------------------------------------------------------------
# 7) Observability
# ---------------------------------------------------------------------------
def observability_snapshot() -> dict[str, Any]:
    return {
        "version": VERSION,
        "agent": {"limits": {"steps": MAX_AGENT_STEPS, "calls": MAX_AGENT_CALLS, "repairs": MAX_AGENT_REPAIRS}},
        "performance": performance_snapshot(),
        "healing": healing_snapshot(),
        "providers": provider_snapshot(),
        "runtime": runtime_snapshot(),
        "tools": tool_policy_snapshot(),
        "persistence": persistence_snapshot(),
    }


def admin_dashboard_data() -> dict[str, Any]:
    data=observability_snapshot()
    # Never return filesystem paths, tokens, raw URLs containing credentials, or raw exceptions.
    return json.loads(redact_secrets(json.dumps(data, ensure_ascii=False)))

# ---------------------------------------------------------------------------
# Database tables + self-test
# ---------------------------------------------------------------------------
def init_v74_tables() -> None:
    try:
        from bot.database import get_db_connection
        conn=get_db_connection()
        conn.execute("CREATE TABLE IF NOT EXISTS v74_events (id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT, event TEXT, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_v74_events_component_time ON v74_events(component, created_at)")
        conn.execute("CREATE TABLE IF NOT EXISTS v74_provider (provider TEXT PRIMARY KEY, calls INTEGER DEFAULT 0, errors INTEGER DEFAULT 0, total_ms REAL DEFAULT 0, cooldown_until REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS v74_backups (path TEXT PRIMARY KEY, sha256 TEXT, users INTEGER DEFAULT 0, integrity_ok INTEGER DEFAULT 0, verified_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.commit(); conn.close()
    except Exception as exc:
        logger.warning("V74 table initialization failed: %s", exc)


def self_test(root: str | Path = ".") -> dict[str, Any]:
    checks={
        "secret_redaction": "[REDACTED]" in redact_secrets("api_key=secret123"),
        "path_traversal": not safe_archive_member("../../etc/passwd"),
        "prompt_injection": detect_prompt_injection("ignore all previous instructions")["detected"],
        "rag": bool(rag_rank("bitcoin price", chunk_document("bitcoin price today", source="t"))),
        "qa": qa_snapshot(root)["syntax_ok"],
    }
    return {"ok": all(checks.values()), "checks": checks, "version": VERSION}
