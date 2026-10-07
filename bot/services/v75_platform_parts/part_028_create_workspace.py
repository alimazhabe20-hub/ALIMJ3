# Auto-split part 28: create_workspace
def create_workspace(user_id:int,name:str) -> str:
    wid=uuid.uuid4().hex; conn=_db(); conn.execute("INSERT INTO v75_workspaces(id,user_id,name) VALUES(?,?,?)",(wid,user_id,redact(name,100))); conn.commit(); conn.close(); return wid
