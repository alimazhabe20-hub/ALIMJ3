from dataclasses import dataclass

# Auto-split part 2: PluginState
@dataclass
class PluginState:
    loaded: bool = False
    load_error: str = ""
    started: bool = False
    stopped: bool = False
    loaded_at: float = 0.0
    start_count: int = 0
    stop_count: int = 0
    last_hook: str = ""
    last_error: str = ""
    healthy: bool = True
