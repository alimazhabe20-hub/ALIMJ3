# Auto-split part 13: rag_chunk
def rag_chunk(text: str, *, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    chunk_size = max(200, min(3000, int(chunk_size))); overlap = max(0, min(chunk_size//2, int(overlap)))
    chunks=[]; start=0
    while start < len(text):
        end=min(len(text), start+chunk_size); chunks.append(text[start:end])
        if end == len(text): break
        start=max(start+1, end-overlap)
    return chunks
