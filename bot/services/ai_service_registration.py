"""Late registration/compatibility actions for ai_service."""
from .ai_service_common import *  # noqa
from . import ai_service_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_KEY_COOLDOWN: Dict[str, float] = {}

_KEY_RR: Dict[str, int] = defaultdict(int)

_PROVIDER_PRETTY = {
    "gemini": "Gemini",
    "groq": "Groq",
    "cerebras": "Cerebras",
    "cloudflare": "Cloudflare",
    "openrouter": "OpenRouter",
}

IMAGE_GEN_MODEL = os.getenv(
    "GEMINI_IMAGE_MODEL",
    "gemini-3.1-flash-image",
)

TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-DilaraNeural")

TTS_VOICE = os.getenv("TTS_VOICE", "fa-IR-DilaraNeural")
