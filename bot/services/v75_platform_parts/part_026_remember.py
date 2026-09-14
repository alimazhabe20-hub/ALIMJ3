# Auto-split part 26: remember
def remember(user_id:int, category:str, key:str, value:str, confidence:float=1.0, source:str="user") -> None:
    conn=_db(); conn.execute("INSERT INTO v75_memory(id,user_id,category,key,value,confidence,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,category,key) DO UPDATE SET value=excluded.value,confidence=excluded.confidence,source=excluded.source,updated_at=CURRENT_TIMESTAMP",(uuid.uuid4().hex,user_id,category,key,redact(value,2000),max(0,min(1,float(confidence))),source)); conn.commit(); conn.close()
