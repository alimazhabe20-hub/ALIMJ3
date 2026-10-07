# Auto-split part 11: _ensure_worker
def _ensure_worker() -> None:
    global _queue, _worker_task
    if _queue is None:
        _queue = asyncio.Queue(maxsize=256)
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker(), name="auto-reaction-worker")
