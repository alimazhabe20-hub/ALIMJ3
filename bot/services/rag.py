"""Bounded retrieval-augmented generation (RAG) index for project documentation.

This layer stays dependency-free and deterministic: documents are chunked once,
then ranked with a BM25-style lexical score plus phrase/coverage boosts. It is
safe for production use because only an explicit allow-list is indexed; user
memory and jokes_data.json are handled elsewhere and are never read here.
"""

# BEGIN MERGED LEGACY PART: rag_parts/part_001_Chunk.py
from dataclasses import dataclass

# Auto-split part 1: Chunk
@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    text: str
    tokens: tuple[str, ...]

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_002_ScoredChunk.py
from dataclasses import dataclass

# Auto-split part 2: ScoredChunk
@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float
    coverage: float

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_003__normalize.py
# Auto-split part 3: _normalize
def _normalize(text: str) -> str:
    text = (text or "").lower().replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[\u200c\u200d]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_004__tokens.py
# Auto-split part 4: _tokens
def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(_normalize(text)))

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_005__chunk_text.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_006__index.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_007_refresh_index.py
# Auto-split part 7: refresh_index
def refresh_index() -> None:
    """Invalidate the bounded in-process RAG index."""
    _index.cache_clear()

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_008_index_stats.py
# Auto-split part 8: index_stats
def index_stats() -> dict[str, int]:
    chunks = _index()
    return {"documents": len({c.source for c in chunks}), "chunks": len(chunks)}

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_009_search.py
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

# END MERGED LEGACY PART: 
# BEGIN MERGED LEGACY PART: rag_parts/part_010_build_context.py
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

# END MERGED LEGACY PART: 
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DOCUMENTS = ("README.md", "RELEASE.md", ".env.example", "render.yaml", "pyproject.toml")
MAX_FILE_CHARS = 80_000
CHUNK_CHARS = 1_200
CHUNK_OVERLAP = 180
MAX_RESULTS = 8
MAX_CONTEXT_CHARS = 4_000

_TOKEN_RE = re.compile(r"[\w\u0600-\u06ff]{2,}")


rag_parts/part_001_Chunk.py
rag_parts/part_002_ScoredChunk.py
rag_parts/part_003__normalize.py
rag_parts/part_004__tokens.py
rag_parts/part_005__chunk_text.py
rag_parts/part_006__index.py
rag_parts/part_007_refresh_index.py
rag_parts/part_008_index_stats.py
rag_parts/part_009_search.py
rag_parts/part_010_build_context.py
