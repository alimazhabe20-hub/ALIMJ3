from typing import Any

# Auto-split part 9: search
def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    query = (query or "").strip()
    qtokens = _tokens(query)
    if not qtokens:
        return []
    qset = set(qtokens)
    chunks = _index()
    if not chunks:
        return []

    doc_freq: dict[str, int] = {}
    for chunk in chunks:
        for token in set(chunk.tokens):
            doc_freq[token] = doc_freq.get(token, 0) + 1
    avgdl = sum(len(c.tokens) for c in chunks) / max(1, len(chunks))
    k1, b = 1.35, 0.72
    phrase = _normalize(query)
    scored: list[ScoredChunk] = []

    for chunk in chunks:
        tf: dict[str, int] = {}
        for token in chunk.tokens:
            tf[token] = tf.get(token, 0) + 1
        dl = len(chunk.tokens)
        score = 0.0
        matched = 0
        for token in qset:
            freq = tf.get(token, 0)
            if not freq:
                continue
            matched += 1
            df = doc_freq.get(token, 0)
            idf = math.log(1.0 + (len(chunks) - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1.0 - b + b * dl / max(1.0, avgdl))
            score += idf * (freq * (k1 + 1.0)) / denom
        coverage = matched / max(1, len(qset))
        norm_text = _normalize(chunk.text)
        if phrase and len(phrase) >= 4 and phrase in norm_text:
            score += 2.5
        score += coverage * 1.8
        if score > 0:
            scored.append(ScoredChunk(chunk, score, coverage))

    scored.sort(key=lambda item: (-item.score, -item.coverage, item.chunk.source, item.chunk.index))
    cap = max(1, min(int(limit), MAX_RESULTS))
    return [
        {
            "source": item.chunk.source,
            "chunk": item.chunk.index,
            "score": round(item.score, 4),
            "coverage": round(item.coverage, 4),
            "text": item.chunk.text,
        }
        for item in scored[:cap]
    ]
