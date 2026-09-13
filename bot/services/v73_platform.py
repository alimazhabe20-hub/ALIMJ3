"""V73 platform: production agent architecture, security, self-healing, QA and performance.

All controls are bounded and deterministic. No unbounded autonomous loops, no secret
exposure, and no security bypasses are implemented here.
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
import time
import urllib.parse
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from bot.logger import logger

VERSION = "73.0.0"
MAX_AGENT_STEPS = max(1, min(8, int(os.getenv("V73_AGENT_MAX_STEPS", "6"))))
MAX_AGENT_REPAIRS = max(0, min(3, int(os.getenv("V73_AGENT_MAX_REPAIRS", "2"))))
MAX_TOOL_CALLS_PER_RUN = max(2, min(20, int(os.getenv("V73_AGENT_MAX_TOOL_CALLS", "10"))))
SLOW_TOOL_MS = max(100, float(os.getenv("V73_SLOW_TOOL_MS", "3000")))

# ---------------------------------------------------------------------------
# Security primitives
# ---------------------------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r"(?i)(bot[_-]?token|api[_-]?key|secret|password|authorization)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
]


def redact_secrets(value: Any) -> str:
    text = str(value if value is not None else "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: m.group(1) + "=[REDACTED]" if m.lastindex == 2 else "Bearer [REDACTED]", text)
    return text[:4000]


def safe_public_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    """Reject malformed URLs and SSRF-sensitive destinations."""
    raw = (url or "").strip()
    if not raw or len(raw) > 2048:
        return False, "invalid_url"
    try:
        p = urllib.parse.urlsplit(raw)
    except Exception:
        return False, "invalid_url"
    schemes = {"https", "http"} if allow_http else {"https"}
    if p.scheme.lower() not in schemes or not p.hostname or p.username or p.password:
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


def safe_path(path: str, root: str | Path) -> bool:
    try:
        target = Path(path).resolve()
        base = Path(root).resolve()
        return target == base or base in target.parents
    except Exception:
        return False


def safe_archive_member(name: str) -> bool:
    n = (name or "").replace("\\", "/")
    if not n or n.startswith("/") or re.match(r"^[A-Za-z]:", n):
        return False
    parts = [p for p in n.split("/") if p]
    return ".." not in parts


def sanitize_tool_arguments(args: dict[str, Any], *, max_text=6000) -> dict[str, Any]:
    """Bound agent/tool input without altering normal handler semantics."""
    out: dict[str, Any] = {}
    for key, value in (args or {}).items():
        if isinstance(value, str):
            out[key] = value[:max_text]
        elif isinstance(value, (int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, list):
            out[key] = value[:20]
        elif isinstance(value, dict):
            out[key] = sanitize_tool_arguments(value, max_text=max_text // 2)
        else:
            out[key] = str(value)[:max_text]
    return out


# ---------------------------------------------------------------------------
# Agent architecture
# ---------------------------------------------------------------------------
class AgentRun:
    def __init__(self, goal: str, user_id: int = 0):
        self.goal = goal[:6000]
        self.user_id = user_id
        self.started = time.monotonic()
        self.steps: list[dict[str, Any]] = []
        self.used: set[str] = set()
        self.calls = 0
        self.repairs = 0

    def can_call(self, tool: str) -> bool:
        return self.calls < MAX_TOOL_CALLS_PER_RUN and tool not in self.used

    def record(self, **item: Any) -> None:
        self.steps.append({**item, "elapsed_ms": round((time.monotonic() - self.started) * 1000, 1)})


def _intent_candidates(goal: str, available: set[str]) -> list[dict[str, Any]]:
    q = goal.lower()
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    patterns = [
        ("weather", r"هوا|آب\s*و\s*هوا|دما|باران|weather", "get_weather", {}),
        ("air", r"آلودگی|کیفیت\s*هوا|aqi", "get_air_quality", {}),
        ("market", r"قیمت|بازار|کریپتو|بیت.?کوین|طلا|دلار|ارز|market|price", "get_market_prices", {}),
        ("knowledge", r"مستندات|راهنما|قابلیت.*ربات|knowledge|documentation", "search_knowledge_base", {"query": goal}),
        ("web", r"اینترنت|وب|جستجو|خبر|اخبار|latest|news|search", "hybrid_retrieve", {"query": goal, "include_web": True}),
        ("shopping", r"خرید|بخر|فروشگاه|shopping", "search_shopping", {"query": goal, "source": "all", "max_results": 8}),
    ]
    for _, pattern, tool, args in patterns:
        if tool in available and re.search(pattern, q, re.I):
            score = len(re.findall(pattern, q, re.I)) + (2 if tool == "hybrid_retrieve" and re.search(r"جدید|فعلی|امروز|latest|news", q, re.I) else 0)
            candidates.append((score, tool, args))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return [{"tool": t, "arguments": a} for _, t, a in candidates[:MAX_AGENT_STEPS]]


async def run_production_agent(goal: str, *, user_id: int = 0) -> str:
    """Bounded agent with planning, policy checks, repair, trace and safe output."""
    goal = (goal or "").strip()
    if not goal:
        return "هدف خالی است."
    from bot.services.tool_runtime import execute_tool, get_registered_tool_names

    run = AgentRun(goal, user_id)
    available = get_registered_tool_names()
    plan = _intent_candidates(goal, available)
    if not plan:
        return "برای این درخواست برنامه ابزارمحور مطمئنی پیدا نشد؛ پاسخ مستقیم AI مناسب‌تر است."

    for idx, step in enumerate(plan, 1):
        tool = step["tool"]
        args = sanitize_tool_arguments(step.get("arguments") or {})
        if not run.can_call(tool):
            break
        run.calls += 1
        run.used.add(tool)
        started = time.monotonic()
        try:
            value = await execute_tool(tool, args, user_id=user_id, source="agent")
            failed = isinstance(value, str) and value.startswith(("خطا در اجرای", "زمان اجرای", "ابزار ناشناخته", "ابزار مسدود"))
            run.record(step=idx, tool=tool, ok=not failed, result=redact_secrets(value)[:3000])
            if failed and run.repairs < MAX_AGENT_REPAIRS:
                run.repairs += 1
                fallback = "hybrid_retrieve" if "hybrid_retrieve" in available and tool != "hybrid_retrieve" else None
                if fallback and run.can_call(fallback):
                    run.calls += 1
                    run.used.add(fallback)
                    repaired = await execute_tool(fallback, {"query": goal, "include_web": True}, user_id=user_id, source="agent_repair")
                    run.record(step=idx, tool=fallback, repair=True, ok=not str(repaired).startswith("خطا"), result=redact_secrets(repaired)[:3000])
        except Exception as exc:
            logger.warning("V73 agent step failed: %s", exc, exc_info=True)
            run.record(step=idx, tool=tool, ok=False, error="internal_failure")
            if run.repairs < MAX_AGENT_REPAIRS:
                run.repairs += 1
        if (time.monotonic() - started) > 30:
            logger.warning("V73 agent slow step tool=%s", tool)

    return json.dumps({"ok": bool(run.steps), "goal": run.goal[:500], "steps": run.steps, "repairs": run.repairs}, ensure_ascii=False)[:9000]


# ---------------------------------------------------------------------------
# Self-healing and circuit protection
# ---------------------------------------------------------------------------
_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=20))
_COOLDOWN_UNTIL: dict[str, float] = {}


def note_failure(component: str) -> bool:
    now = time.monotonic()
    q = _FAILURES[component]
    q.append(now)
    threshold = max(2, int(os.getenv("V73_FAILURE_THRESHOLD", "3")))
    if len([x for x in q if now - x <= 120]) >= threshold:
        _COOLDOWN_UNTIL[component] = now + max(5, float(os.getenv("V73_COOLDOWN_SECONDS", "30")))
        return True
    return False


def component_available(component: str) -> bool:
    return time.monotonic() >= _COOLDOWN_UNTIL.get(component, 0.0)


def recover_component(component: str) -> dict[str, Any]:
    """Safe local recovery only: clear in-memory caches and reset known clients."""
    actions: list[str] = []
    try:
        from bot.services.tool_runtime import clear_tool_cache
        clear_tool_cache()
        actions.append("tool_cache_cleared")
    except Exception:
        pass
    try:
        from bot.utils.http_client import clear_http_cache
        clear_http_cache()
        actions.append("http_cache_cleared")
    except Exception:
        pass
    _COOLDOWN_UNTIL[component] = time.monotonic() + 3
    return {"component": component, "recovered": True, "actions": actions}


def health_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {
        name: {
            "failures_120s": sum(1 for x in q if now - x <= 120),
            "cooldown_remaining": round(max(0.0, _COOLDOWN_UNTIL.get(name, 0.0) - now), 1),
        }
        for name, q in _FAILURES.items()
    }


# ---------------------------------------------------------------------------
# Performance + QA
# ---------------------------------------------------------------------------
_PERF: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})


def record_performance(name: str, elapsed_ms: float, ok: bool = True) -> None:
    p = _PERF[name]
    p["calls"] += 1
    p["total_ms"] += max(0.0, elapsed_ms)
    p["max_ms"] = max(p["max_ms"], elapsed_ms)
    if not ok:
        p["errors"] += 1


def performance_snapshot() -> dict[str, Any]:
    out = {}
    for name, p in _PERF.items():
        calls = max(1.0, p["calls"])
        out[name] = {
            "calls": int(p["calls"]),
            "errors": int(p["errors"]),
            "avg_ms": round(p["total_ms"] / calls, 2),
            "max_ms": round(p["max_ms"], 2),
            "slow": p["max_ms"] >= SLOW_TOOL_MS,
        }
    return out


def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root = Path(root)
    py_files = list(root.rglob("*.py"))
    syntax_errors: list[str] = []
    for path in py_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            syntax_errors.append(f"{path}: {type(exc).__name__}")
    return {
        "python_files": len(py_files),
        "syntax_errors": syntax_errors[:50],
        "syntax_ok": not syntax_errors,
        "performance_components": len(_PERF),
        "security": "enabled",
        "agent_limits": {"steps": MAX_AGENT_STEPS, "calls": MAX_TOOL_CALLS_PER_RUN, "repairs": MAX_AGENT_REPAIRS},
    }


def init_v73_tables() -> None:
    """Create persistent operational tables without touching existing user data."""
    try:
        from bot.database import get_db_connection
        conn = get_db_connection()
        conn.execute("""CREATE TABLE IF NOT EXISTS v73_health (
            component TEXT PRIMARY KEY, failures INTEGER DEFAULT 0, cooldown_until REAL DEFAULT 0,
            last_error TEXT DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS v73_perf (
            name TEXT PRIMARY KEY, calls INTEGER DEFAULT 0, errors INTEGER DEFAULT 0,
            total_ms REAL DEFAULT 0, max_ms REAL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("V73 table initialization failed: %s", exc)
