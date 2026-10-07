# Auto-split part 4: _scope_allows
def _scope_allows(chat_type: str | None) -> bool:
    allowed = getattr(config, "AUTO_REACTIONS_SCOPE", "private,group,supergroup")
    return (chat_type or "private").lower() in {x.strip().lower() for x in str(allowed).split(",") if x.strip()}
