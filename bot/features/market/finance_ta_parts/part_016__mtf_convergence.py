# Auto-split part 16: _mtf_convergence
def _mtf_convergence(mtf: dict) -> tuple:
    """(متن همگرایی، قدرت 1-10)"""
    dirs = mtf.get("dirs") or {}
    scores = mtf.get("scores") or {}
    vals = [dirs.get(k) for k in ("1H", "4H", "1D")]
    bull = sum(1 for d in vals if d == "صعودی")
    bear = sum(1 for d in vals if d == "نزولی")
    avg_sc = [scores.get(k) for k in ("1H", "4H", "1D") if scores.get(k)]
    avg = sum(avg_sc) / len(avg_sc) if avg_sc else 5
    if bull == 3:
        return "همگرایی کامل صعودی ۳/۳", min(10, int(avg + 2))
    if bear == 3:
        return "همگرایی کامل نزولی ۳/۳", min(10, int(avg + 2))
    if bull == 2 and bear == 0:
        return "همگرایی جزئی صعودی ۲/۳", int(avg)
    if bear == 2 and bull == 0:
        return "همگرایی جزئی نزولی ۲/۳", int(avg)
    if bull and bear:
        return "عدم همگرایی — تضاد تایم‌فریم‌ها", max(1, int(avg - 2))
    return "همگرایی ضعیف / رنج", max(1, int(avg - 1))
