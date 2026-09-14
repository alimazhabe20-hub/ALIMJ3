from typing import Any

# Auto-split part 16: graph_neighbors
def graph_neighbors(node_id: str, relation: str|None=None, limit: int=30) -> list[dict[str,Any]]:
    c=_db(); q="SELECT e.source,e.relation,e.target,e.weight,n.label,n.kind,n.properties_json FROM v77_graph_edges e LEFT JOIN v77_graph_nodes n ON n.id=e.target WHERE e.source=?"; a=[node_id]
    if relation: q+=" AND e.relation=?"; a.append(relation)
    q+=" ORDER BY e.weight DESC LIMIT ?"; a.append(max(1,min(100,int(limit)))); rows=c.execute(q,a).fetchall(); c.close(); out=[]
    for r in rows:
        try:p=json.loads(r[6] or "{}")
        except Exception:p={}
        out.append({"source":r[0],"relation":r[1],"target":r[2],"weight":r[3],"label":r[4],"kind":r[5],"properties":p})
    return out
