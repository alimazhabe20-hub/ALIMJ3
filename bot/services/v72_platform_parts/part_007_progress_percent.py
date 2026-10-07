# Auto-split part 7: progress_percent
def progress_percent(done: int, total: int) -> float:
    if total <= 0: return 0.0
    return round(max(0.0, min(100.0, done * 100.0 / total)), 1)
