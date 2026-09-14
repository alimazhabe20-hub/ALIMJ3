# Auto-split part 11: personalize
def personalize(user_id:int, language:str|None=None, response_style:str|None=None, ai_mode:str|None=None, notifications:bool|None=None)->dict:
    current={"language":"fa","response_style":"balanced","ai_mode":"balanced","notifications":1}
    conn=get_db_connection(); row=conn.execute("SELECT language,response_style,ai_mode,notifications FROM v71_user_settings WHERE user_id=?",(user_id,)).fetchone(); conn.close()
    if row: current=dict(zip(current,row))
    updates={"language":language if language in SUPPORTED_LANGS else current["language"],"response_style":response_style or current["response_style"],"ai_mode":ai_mode or current["ai_mode"],"notifications":int(current["notifications"] if notifications is None else notifications)}
    _execute_write("INSERT INTO v71_user_settings(user_id,language,response_style,ai_mode,notifications) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET language=excluded.language,response_style=excluded.response_style,ai_mode=excluded.ai_mode,notifications=excluded.notifications",(user_id,updates["language"],updates["response_style"],updates["ai_mode"],updates["notifications"]))
    return updates
