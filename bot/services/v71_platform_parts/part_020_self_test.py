# Auto-split part 20: self_test
def self_test()->dict:
    checks={"db":False,"code":False,"security":False,"language":False,"scheduler":False}
    started=time.perf_counter()
    try:
        init_v71_tables(); checks["db"]=health_snapshot()["database"]
        checks["code"]=code_agent_review("def ok():\n    return 1")["ok"]
        # Offline-safe security test: a private address must always be rejected.
        checks["security"]=security_check_url("http://127.0.0.1")["ok"] is False
        checks["language"]=detect_language("hello world")=="en" and detect_language("سلام") in {"fa","ar"}
        jid=schedule_ai(-999,"selftest","2099-01-01 00:00:00"); checks["scheduler"]=jid>0
        _execute_write("DELETE FROM v71_scheduled_ai WHERE id=?",(jid,))
    except Exception:
        logger.exception("v71 self test failed")
    return {"ok":all(checks.values()),"checks":checks,"latency_ms":round((time.perf_counter()-started)*1000,1)}
