from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.plugins.manager import PluginSpec

# Auto-split part 4: register
def register(spec: PluginSpec) -> PluginSpec:
    if not spec.name or not spec.name.replace("_", "").isalnum():
        raise ValueError("Invalid plugin name")
    disabled = _disabled_names()
    if spec.name.lower() in disabled:
        spec = PluginSpec(
            spec.name, spec.version, spec.description, spec.module,
            False, spec.tags, spec.dependencies,
        )
    _REGISTRY[spec.name] = spec
    _STATE.setdefault(spec.name, PluginState())
    return spec
