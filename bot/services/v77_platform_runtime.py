"""v77_platform: runtime responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def self_healing_snapshot() -> dict[str,Any]:
    return {"circuits":{k:circuit_state(k) for k in _CIRCUITS},"failures":{k:len(v) for k,v in _FAILURES.items() if v},"policy":"bounded_retry_then_circuit"}

def admin_snapshot(root: str|Path=".") -> dict[str,Any]:
    return {"version":VERSION,"security":security_center(),"performance":performance_snapshot(),"providers":provider_snapshot(),"plugins":plugin_snapshot(),"self_healing":self_healing_snapshot(),"release_gate":release_gate(root)}

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
