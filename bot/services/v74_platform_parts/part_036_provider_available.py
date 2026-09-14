# Auto-split part 36: provider_available
def provider_available(provider: str) -> bool:
    return time.monotonic() >= float(_PROVIDER[provider].get("cooldown_until",0))
