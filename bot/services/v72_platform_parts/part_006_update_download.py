# Auto-split part 6: update_download
def update_download(job_id: int, *, status: str | None = None, progress: float | None = None, error_code: str = "") -> None:
    fields, vals = [], []
    if status is not None: fields.append("status=?"); vals.append(status[:30])
    if progress is not None: fields.append("progress=?"); vals.append(max(0.0, min(100.0, float(progress))))
    if error_code: fields.append("error_code=?"); vals.append(error_code[:80])
    if not fields: return
    fields.append("updated_at=CURRENT_TIMESTAMP")
    vals.append(int(job_id))
    _execute_write(f"UPDATE v72_download_jobs SET {','.join(fields)} WHERE id=?", tuple(vals))
