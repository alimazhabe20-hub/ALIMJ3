from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.rag import Chunk
if TYPE_CHECKING:
    from bot.services.rag import lru_cache

# Auto-split part 6: _index
@lru_cache(maxsize=1)
def _index() -> tuple[Chunk, ...]:
    result: list[Chunk] = []
    for name in ALLOWED_DOCUMENTS:
        path = ROOT / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
        except OSError:
            continue
        for idx, part in enumerate(_chunk_text(text)):
            toks = _tokens(part)
            if toks:
                result.append(Chunk(name, idx, part, toks))
    return tuple(result)
