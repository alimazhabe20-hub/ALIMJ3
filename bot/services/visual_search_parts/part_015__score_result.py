from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.visual_search import SearchResult

# Auto-split part 15: _score_result
def _score_result(result: SearchResult, query_terms: list[str], all_terms: list[str]) -> float:
    hay = _normalize(f"{result.title} {result.snippet} {result.url}")
    tokens = set(_tokens(hay))
    if not tokens:
        return 0.0

    q_overlap = len(set(query_terms) & tokens) / max(1, len(set(query_terms)))
    global_overlap = len(set(all_terms) & tokens) / max(1, len(set(all_terms)))

    # Domain/product signals help but never make the result mandatory.
    bonus = 0.0
    if any(x in hay for x in ("product", "محصول", "بطری", "shop", "store", "فروشگاه", "digikala", "basalam")):
        bonus += 0.03
    if any(x in result.url.lower() for x in ("instagram.com", "digikala.com", "basalam.com")):
        bonus += 0.04

    score = 0.62 * q_overlap + 0.35 * global_overlap + bonus
    return max(0.0, min(1.0, score))
