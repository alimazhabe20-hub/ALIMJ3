# Auto-split part 15: graph_link
def graph_link(source: str, relation: str, target: str, weight: float=1.0) -> None:
    c=_db(); c.execute("INSERT INTO v77_graph_edges(source,relation,target,weight) VALUES(?,?,?,?) ON CONFLICT(source,relation,target) DO UPDATE SET weight=excluded.weight",(str(source)[:200],redact(relation,120),str(target)[:200],float(weight))); c.commit(); c.close()
