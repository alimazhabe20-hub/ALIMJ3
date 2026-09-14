# Auto-split part 13: maybe_auto_react
async def maybe_auto_react(update, context=None) -> bool:
    """Backward-compatible async entry point; it only queues work."""
    return enqueue_auto_reaction(update)
