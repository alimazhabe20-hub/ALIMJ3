# Auto-split part 5: record_download
def record_download(user_id: int, url: str, mode: str, status: str = "queued", progress: float = 0.0, error_code: str = "") -> int:
    conn = get_db_connection(); cur = conn.execute(
        "INSERT INTO v72_download_jobs(user_id,url,mode,status,progress,error_code) VALUES(?,?,?,?,?,?)",
        (int(user_id), str(url)[:4000], normalize_download_mode(mode), status[:30], max(0.0, min(100.0, float(progress))), error_code[:80]),
    ); conn.commit(); jid = int(cur.lastrowid); conn.close(); return jid
