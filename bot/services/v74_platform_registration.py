"""Late registration/compatibility actions for v74_platform."""
from .v74_platform_common import *  # noqa
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_TOOL_POLICIES: dict[str, ToolPolicy] = {}

_TOOL_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=30))

_TOOL_DISABLED_UNTIL: dict[str, float] = {}

if TYPE_CHECKING:
    from bot.services.v74_platform import ToolPolicy

if TYPE_CHECKING:
    from bot.services.v74_platform import AgentStep

if TYPE_CHECKING:
    from bot.services.v74_platform import AgentStep

_CACHE: dict[str, tuple[float, Any]] = {}

_INFLIGHT: dict[str, asyncio.Task] = {}

_PERF: dict[str, dict[str, float]] = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})

_SLOW: Counter[str] = Counter()

if TYPE_CHECKING:
    from bot.services.v74_platform import CACHE_TTL

_FAILURES: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=50))

_RECOVERY_LOG: deque[dict[str, Any]] = deque(maxlen=100)

_SOURCE_WEIGHTS = {"wikipedia.org": .75, "reuters.com": .95, "bbc.com": .90, "gov": .98, "edu": .95}

_STOP = set("the and for with that this from are was is به برای و از که این آن را در با است یک های هایو".split())

_PROVIDER: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls":0,"errors":0,"total_ms":0.0,"cooldown_until":0.0})

_RUNTIME: dict[str, Any] = {"started_at": time.time(), "readiness": {}, "last_errors": deque(maxlen=50)}
