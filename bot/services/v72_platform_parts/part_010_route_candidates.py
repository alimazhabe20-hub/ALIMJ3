from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v72_platform import RouteCandidate

# Auto-split part 10: route_candidates
def route_candidates(prompt: str, providers: list[tuple[str, str]] | None = None) -> list[RouteCandidate]:
    """Deterministic route planner; it never calls a model or invents provider availability."""
    providers = providers or []
    mode = classify_ai_complexity(prompt)
    out = []
    for provider, model in providers[:40]:
        name = f"{provider}/{model}".lower()
        quality = .92 if any(x in name for x in ("pro", "opus", "sonnet", "70b", "120b")) else .82 if any(x in name for x in ("flash", "medium")) else .66
        speed = .92 if any(x in name for x in ("instant", "flash", "8b", "lite")) else .68
        score = quality if mode == "quality" else speed if mode == "fast" else (quality * .65 + speed * .35)
        out.append(RouteCandidate(provider, model, round(score, 4), f"{mode}:{'quality' if score > .8 else 'speed'}"))
    return sorted(out, key=lambda x: (-x.score, x.provider, x.model))
