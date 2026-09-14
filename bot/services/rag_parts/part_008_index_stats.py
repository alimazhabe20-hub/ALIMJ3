# Auto-split part 8: index_stats
def index_stats() -> dict[str, int]:
    chunks = _index()
    return {"documents": len({c.source for c in chunks}), "chunks": len(chunks)}
