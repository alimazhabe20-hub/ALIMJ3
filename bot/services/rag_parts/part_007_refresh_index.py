# Auto-split part 7: refresh_index
def refresh_index() -> None:
    """Invalidate the bounded in-process RAG index."""
    _index.cache_clear()
