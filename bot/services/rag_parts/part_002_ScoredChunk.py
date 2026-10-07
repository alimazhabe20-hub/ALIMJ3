from dataclasses import dataclass

# Auto-split part 2: ScoredChunk
@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float
    coverage: float
