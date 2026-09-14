from typing import Any
from typing import Iterable

# Auto-split part 31: rag_context
def rag_context(query: str, chunks: Iterable[dict[str, Any]], limit: int = 6, max_chars: int = 9000) -> str:
    blocks=[]; used=0
    for c in rag_rank(query,chunks,limit):
        block=f"[{c['source']}#{c['chunk']} score={c['score']}]\n{sanitize_untrusted_text(c['text'], 2500)}"
        if used+len(block)+2>max_chars: break
        blocks.append(block); used+=len(block)+2
    return "\n\n".join(blocks)
