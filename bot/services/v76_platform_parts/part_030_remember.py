# Auto-split part 30: remember
def remember(user_id:int,key:str,value:str,category:str="general",confidence:float=1.0,source:str="user") -> None:
    c=_db(); c.execute("INSERT INTO v76_memory(id,user_id,category,key,value,confidence,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,category,key) DO UPDATE SET value=excluded.value,confidence=excluded.confidence,source=excluded.source,updated_at=CURRENT_TIMESTAMP",(uuid.uuid4().hex,user_id,category,redact(key,200),redact(value,3000),max(0,min(1,float(confidence))),source)); c.commit(); c.close()
