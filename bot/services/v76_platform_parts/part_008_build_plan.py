from typing import Iterable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v76_platform import Plan

# Auto-split part 8: build_plan
def build_plan(goal: str, tools: Iterable[str] = ()) -> Plan:
    g = redact(goal, 6000).strip(); scan = security_scan(g)
    if not g or scan["risk"] == "high": return Plan(uuid.uuid4().hex, g, [], 30000, 2)
    available = set(tools); i = intent(g); mapping = {"market":"get_market_prices", "news":"hybrid_retrieve", "calendar":"get_economic_calendar", "web":"hybrid_retrieve", "download":"download_file", "document":"search_knowledge_base", "report":"generate_report"}
    steps=[]
    for kind in i["candidates"]:
        tool=mapping.get(kind)
        if tool and tool in available and tool not in [x["tool"] for x in steps]: steps.append({"tool":tool,"arguments":{"query":g},"verify":True})
    return Plan(uuid.uuid4().hex,g,steps[:MAX_STEPS])
