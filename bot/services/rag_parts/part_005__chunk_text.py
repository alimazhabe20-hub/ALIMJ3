# Auto-split part 5: _chunk_text
def _chunk_text(text: str) -> list[str]:
    clean = text.replace("\r\n", "\n").strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    length = len(clean)
    while start < length:
        end = min(length, start + CHUNK_CHARS)
        if end < length:
            boundary = max(clean.rfind("\n", start, end), clean.rfind(" ", start, end))
            if boundary > start + CHUNK_CHARS // 2:
                end = boundary
        part = clean[start:end].strip()
        if part:
            chunks.append(part)
        if end >= length:
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks
