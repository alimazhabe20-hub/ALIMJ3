from typing import Any

# Auto-split part 24: create_alert
def create_alert(user_id:int, kind:str, config:dict[str,Any]) -> str:
    conn=_db(); count=conn.execute("SELECT COUNT(*) FROM v75_alerts WHERE user_id=?",(user_id,)).fetchone()[0]
    if count>=MAX_ALERTS_PER_USER: conn.close(); raise ValueError("alert_limit")
    aid=uuid.uuid4().hex; conn.execute("INSERT INTO v75_alerts(id,user_id,kind,config_json) VALUES(?,?,?,?)",(aid,user_id,kind,json.dumps(config,ensure_ascii=False))); conn.commit(); conn.close(); return aid
