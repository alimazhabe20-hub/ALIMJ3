from dataclasses import dataclass

# Auto-split part 1: SearchResult
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    score: float = 0.0
    matched_query: str = ""
