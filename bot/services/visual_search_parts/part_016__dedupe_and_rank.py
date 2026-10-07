from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.visual_search import SearchResult

# Auto-split part 16: _dedupe_and_rank
def _dedupe_and_rank(results: list[SearchResult], description: str, ocr: str, caption: str) -> list[SearchResult]:
    terms = _tokens(" ".join(x for x in (description, ocr, caption) if x))
    best_by_url: dict[str, SearchResult] = {}
    for r in results:
        key = _strip_ddg_url(r.url).split("#", 1)[0].rstrip("/").lower()
        if not key:
            continue
        q_terms = _tokens(r.matched_query)
        r.score = _score_result(r, q_terms, terms)
        old = best_by_url.get(key)
        if old is None or r.score > old.score:
            best_by_url[key] = r
    ranked = sorted(best_by_url.values(), key=lambda x: x.score, reverse=True)
    return ranked[:15]
