from typing import Any

# Auto-split part 29: chunk_document
def chunk_document(text: str, *, source: str, chunk_chars: int = 1200, overlap: int = 180) -> list[dict[str, Any]]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean: return []
    step = max(1, chunk_chars-overlap); chunks=[]
    for i, start in enumerate(range(0, len(clean), step)):
        piece=clean[start:start+chunk_chars]
        if not piece: break
        chunks.append({"source": source, "chunk": i, "text": piece, "tokens": rag_tokens(piece), "chars": len(piece)})
        if start+chunk_chars >= len(clean): break
    return chunks
