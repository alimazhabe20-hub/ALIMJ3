"""Late registration/compatibility actions for ai_media."""
from .ai_media_common import *  # noqa
from bot.services import ai_service as _ai
from . import ai_media_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_LOCAL_PIPELINE = None

_LOCAL_PIPELINE_MODEL = None

_LOCAL_BACKEND_CACHE = None

TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-DilaraNeural")

TTS_VOICE = _ai.TTS_VOICE
