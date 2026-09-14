# Auto-split part 3: _disabled_names
def _disabled_names() -> set[str]:
    raw = os.getenv("PLUGINS_DISABLED", "")
    return {x.strip().lower() for x in raw.split(",") if x.strip()}
