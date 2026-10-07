from dataclasses import dataclass

# Auto-split part 7: ToolPolicy
@dataclass
class ToolPolicy:
    name: str
    version: str = "1.0"
    risk: str = "read"
    network: bool = False
    timeout: float = 25.0
    retries: int = TOOL_RETRIES
    cache_ttl: int = 0
    dependencies: tuple[str, ...] = ()
    enabled: bool = True
    schema_validated: bool = True
    owner: str = "core"
