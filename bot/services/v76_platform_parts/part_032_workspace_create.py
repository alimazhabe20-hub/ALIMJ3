# Auto-split part 32: workspace_create
def workspace_create(user_id:int,name:str)->str:
    wid=uuid.uuid4().hex;c=_db();c.execute("INSERT INTO v76_workspaces(id,user_id,name) VALUES(?,?,?)",(wid,user_id,redact(name,120)));c.commit();c.close();return wid
