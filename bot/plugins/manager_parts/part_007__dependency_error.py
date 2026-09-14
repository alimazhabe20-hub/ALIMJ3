from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.plugins.manager import PluginSpec

# Auto-split part 7: _dependency_error
def _dependency_error(spec: PluginSpec) -> str:
    missing = [dep for dep in spec.dependencies if dep not in _REGISTRY]
    disabled = [dep for dep in spec.dependencies if dep in _REGISTRY and not _REGISTRY[dep].enabled]
    failed = [dep for dep in spec.dependencies if dep in _STATE and _STATE[dep].load_error]
    if missing:
        return "missing dependency: " + ", ".join(missing)
    if disabled:
        return "disabled dependency: " + ", ".join(disabled)
    if failed:
        return "failed dependency: " + ", ".join(failed)
    return ""
