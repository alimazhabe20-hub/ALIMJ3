"""v77_platform: graph responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
