from typing import Any

# Auto-split part 14: graph_upsert_node
def graph_upsert_node(node_id: str, label: str, kind: str="entity", properties: dict[str,Any]|None=None) -> None:
    c=_db(); c.execute("INSERT INTO v77_graph_nodes(id,label,kind,properties_json,updated_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET label=excluded.label,kind=excluded.kind,properties_json=excluded.properties_json,updated_at=CURRENT_TIMESTAMP",(str(node_id)[:200],redact(label,500),str(kind)[:80],json.dumps(properties or {},ensure_ascii=False)[:12000])); c.commit(); c.close()
