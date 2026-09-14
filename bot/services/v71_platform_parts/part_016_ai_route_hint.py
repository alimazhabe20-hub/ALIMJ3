# Auto-split part 16: ai_route_hint
def ai_route_hint(prompt: str, provider_count: int = 1) -> dict:
    """Deterministic routing hint used by the existing AI router; no model call."""
    text=(prompt or "").strip()
    complexity=min(1.0, (len(text)/1800.0) + (text.count("?")*0.04) + (text.count("؟")*0.04))
    mode="fast" if complexity < 0.25 else ("balanced" if complexity < 0.65 else "quality")
    return {"mode":mode,"complexity":round(complexity,3),"provider_count":max(1,int(provider_count))}
