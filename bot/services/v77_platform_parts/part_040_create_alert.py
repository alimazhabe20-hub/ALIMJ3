from typing import Any

# Auto-split part 40: create_alert
def create_alert(user_id: int, kind: str, config: dict[str,Any]) -> str:
    aid=uuid.uuid4().hex;c=_db();c.execute("INSERT INTO v77_alerts(id,user_id,kind,config_json,enabled) VALUES(?,?,?,?,1)",(aid,int(user_id),str(kind)[:50],json.dumps(config,ensure_ascii=False)[:8000]));c.commit();c.close();return aid
