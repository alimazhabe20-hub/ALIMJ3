"""Late registration/compatibility actions for v75_platform."""
from .v75_platform_common import *  # noqa
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


if TYPE_CHECKING:
    from bot.services.v75_platform import AgentTask

_PERF=defaultdict(lambda: deque(maxlen=100))
