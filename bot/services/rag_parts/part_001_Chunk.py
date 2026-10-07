from dataclasses import dataclass

# Auto-split part 1: Chunk
@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    text: str
    tokens: tuple[str, ...]
