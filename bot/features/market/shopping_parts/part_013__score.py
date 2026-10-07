from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.features.market.shopping import ProductResult

# Auto-split part 13: _score
def _score(result: ProductResult, query: str | list[str]) -> float:
    """امتیاز نرم؛ نتیجه مشابه را حذف نمی‌کند و بهترین query را ملاک می‌گیرد."""
    queries = query if isinstance(query, list) else _query_variants(query)
    if not queries:
        queries = [str(query or "")]

    text = f"{result.title} {result.match_hint}".lower()
    twords = {x.lower() for x in re.findall(r"[\wآ-ی]{2,}", text)}
    best = 0.0
    for q in queries:
        qwords = {x.lower() for x in re.findall(r"[\wآ-ی]{2,}", q)}
        if not qwords:
            continue
        overlap = len(qwords & twords) / max(1, len(qwords))
        # تطابق عبارت کامل امتیاز زیادی می‌گیرد، اما شرط نیست.
        phrase_bonus = 18 if q.lower() in text else 0
        best = max(best, overlap * 100 + phrase_bonus)

    score = best
    if result.price is not None:
        score += 12
    if result.seller:
        score += 3
    if result.source == "instagram":
        score += 4
    if result.source in ("torob", "digikala", "emalls"):
        score += 6
    return score
