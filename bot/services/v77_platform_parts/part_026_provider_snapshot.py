from typing import Any

# Auto-split part 26: provider_snapshot
def provider_snapshot() -> dict[str,Any]:
    return {k:{kk:(sorted(vv) if isinstance(vv,set) else vv) for kk,vv in v.items()} for k,v in _PROVIDERS.items()}
