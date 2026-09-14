from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.rag import MAX_CONTEXT_CHARS

# Auto-split part 10: build_context
def build_context(query: str, limit: int = 5, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    results = search(query, limit)
    if not results:
        return ""
    blocks: list[str] = []
    used = 0
    for item in results:
        block = f"[{item['source']}#{item['chunk']}]\n{item['text']}"
        if used + len(block) + 2 > max_chars:
            remaining = max_chars - used - 2
            if remaining > 120:
                blocks.append(block[:remaining].rstrip())
            break
        blocks.append(block)
        used += len(block) + 2
    return "\n\n".join(blocks)
