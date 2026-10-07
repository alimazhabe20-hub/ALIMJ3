"""ai_tools: agents responsibilities."""
from .ai_tools_common import *  # noqa: F401,F403
from . import ai_tools_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _register_builtin_tools() -> None:
    register_builtin_tools()

def _run_workflow_tool(steps, user_id=0):
    # Kept as a sync-compatible wrapper; the actual engine is async.
    raise RuntimeError("workflow tool must be invoked through its async handler")

async def _run_workflow_async(steps, user_id=0):
    from bot.services.workflow_engine import run_workflow
    return await run_workflow(steps, user_id=user_id)

async def _run_agent(goal: str = "", user_id: int = 0) -> str:
    from bot.services.agent_engine import run_agent
    return await run_agent(goal, user_id=user_id)

def _provider_health() -> str:
    from bot.services.ai_runtime import provider_health_snapshot

    snapshot = provider_health_snapshot()
    if not snapshot:
        return "هنوز داده‌ای از سلامت Providerها ثبت نشده است."
    lines = ["وضعیت سلامت Providerهای AI (بر اساس اجرای واقعی اخیر):"]
    for name, item in snapshot.items():
        status = item["status"]
        if status == "healthy":
            label = "سالم"
        elif status == "cooldown":
            label = f"در cooldown ({item['cooldown_remaining_sec']}s)"
        else:
            label = "بدون داده کافی"
        rate = item["success_rate"]
        rate_text = f"{round(rate * 100)}%" if isinstance(rate, (int, float)) else "—"
        latency = f"{item['avg_latency_ms']}ms" if item["avg_latency_ms"] is not None else "—"
        lines.append(
            f"- {name}: {label} | موفقیت {rate_text} | latency میانگین {latency} | "
            f"ok={item['ok']} fail={item['fail']}"
        )
    return "\n".join(lines)[:4500]

def _knowledge_search(query: str = "", limit: int = 5) -> str:
    from bot.services.knowledge_base import format_knowledge_results
    return format_knowledge_results(query, limit)

async def _hybrid_retrieve(query: str = "", include_web: bool = False, user_id: int = 0) -> str:
    from bot.services.retrieval import hybrid_search
    return await hybrid_search(user_id, query, include_web=bool(include_web))

class _ToolDefsProxy(list):
    def __iter__(self):
        return iter(get_tool_definitions())
    def __len__(self):
        return len(get_tool_definitions())
    def __getitem__(self, i):
        return get_tool_definitions()[i]

async def _run_agent_v73(goal: str = "", user_id: int = 0) -> str:
    from bot.services.v73_platform import run_production_agent
    return await run_production_agent(goal, user_id=user_id)

def _v73_health() -> str:
    from bot.services.v73_platform import health_snapshot, performance_snapshot
    return json.dumps({"health": health_snapshot(), "performance": performance_snapshot()}, ensure_ascii=False)[:4500]

async def _run_agent_v74(goal: str = "", user_id: int = 0) -> str:
    from bot.services.v74_platform import run_agent_2
    return await run_agent_2(goal, user_id=user_id)

def _v74_system_status() -> str:
    from bot.services.v74_platform import observability_snapshot
    import json
    return json.dumps(observability_snapshot(), ensure_ascii=False)[:12000]

async def _run_agent_v75(goal: str = "", user_id: int = 0) -> str:
    from bot.services.v75_platform import run_agent_3
    return json.dumps(await run_agent_3(goal, user_id=user_id), ensure_ascii=False)[:12000]

async def _multi_agent_v75(goal: str = "", user_id: int = 0) -> str:
    from bot.services.v75_platform import run_multi_agent
    return json.dumps(await run_multi_agent(goal, user_id=user_id), ensure_ascii=False)[:12000]

def _v75_status() -> str:
    from bot.services.v75_platform import dashboard
    return json.dumps(dashboard(), ensure_ascii=False)[:12000]

def _v75_security(text: str = "") -> str:
    from bot.services.v75_platform import security_scan
    return json.dumps(security_scan(text), ensure_ascii=False)

def _v75_news_score(title: str = "", content: str = "") -> str:
    from bot.services.v75_platform import score_news
    return json.dumps(score_news(title, content), ensure_ascii=False)

async def _run_agent_v76(goal: str = "", user_id: int = 0) -> str:
    from bot.services.v76_platform import run_agent_4
    return json.dumps(await run_agent_4(goal,user_id=user_id),ensure_ascii=False)[:12000]

def _v76_status() -> str:
    from bot.services.v76_platform import system_snapshot
    return json.dumps(system_snapshot(),ensure_ascii=False)[:12000]

async def _run_agent_v77(goal: str = "", user_id: int = 0) -> str:
    from bot.services.v77_platform import run_agent_5
    result = await run_agent_5(str(goal or ""), user_id=int(user_id or 0))
    return json.dumps(result, ensure_ascii=False)[:12000]

def _v77_status() -> str:
    from bot.services.v77_platform import system_snapshot
    return json.dumps(system_snapshot("."), ensure_ascii=False)[:12000]

def _v77_market(closes: list[float] | None = None) -> str:
    from bot.services.v77_platform import market_intelligence_3
    return json.dumps(market_intelligence_3(closes or []), ensure_ascii=False)

def _v77_security(text: str = "") -> str:
    from bot.services.v77_platform import security_scan
    return json.dumps(security_scan(text), ensure_ascii=False)
