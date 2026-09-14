# Auto-split part 19: health_snapshot
def health_snapshot()->dict:
    init_v71_tables()
    try:
        conn=get_db_connection(); conn.execute("SELECT 1"); conn.close(); db=True
    except Exception: db=False
    return {"ok":db,"database":db,"languages":list(SUPPORTED_LANGS),"features":{"agent":True,"multi_agent":True,"fact_check":True,"source_intelligence":True,"memory_2":True,"rag":True,"document_intelligence":True,"code_agent":True,"self_test":True,"auto_recovery":True,"performance":True,"security_2":True,"workspace":True,"ai_optimizer":True,"conversation_branching":True,"scheduled_ai":True,"smart_notifications":True,"personalization":True,"observability":True}}
