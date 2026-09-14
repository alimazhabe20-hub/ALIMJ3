from dataclasses import dataclass

# Auto-split part 1: PluginSpec
@dataclass(frozen=True)
class PluginSpec:
    name: str
    version: str
    description: str
    module: str = ""
    enabled: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
