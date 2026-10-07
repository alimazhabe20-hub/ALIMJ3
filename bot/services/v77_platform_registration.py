"""Late registration/compatibility actions for v77_platform."""
from .v77_platform_common import *  # noqa
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


if TYPE_CHECKING:
    from bot.services.v77_platform import AgentPlan

_POS={"bullish","positive","growth","rise","surge","increase","صعود","رشد","مثبت","افزایش","رکورد"}

_NEG={"bearish","negative","fall","drop","crash","decrease","کاهش","سقوط","منفی","ریزش"}

if TYPE_CHECKING:
    from bot.services.v77_platform import MAX_STATE_TURNS
