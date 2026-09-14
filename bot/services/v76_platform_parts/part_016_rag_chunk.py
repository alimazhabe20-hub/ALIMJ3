# Auto-split part 16: rag_chunk
def rag_chunk(text: str, chunk_size: int=900, overlap: int=120) -> list[str]:
    chunk_size=max(100,min(4000,int(chunk_size))); overlap=max(0,min(chunk_size-1,int(overlap))); s=str(text or ""); out=[]; i=0
    while i<len(s) and len(out)<2000:
        out.append(s[i:i+chunk_size]); i += chunk_size-overlap
    return out
