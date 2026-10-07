"""messages: media responsibilities."""
from .messages_common import *  # noqa: F401,F403
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def media_ai_handler(*args, **kwargs): return await _legacy_media_ai_handler(*args, **kwargs)

async def lens_command(*args, **kwargs): return await _legacy_lens_command(*args, **kwargs)

async def voice_ai_handler(*args, **kwargs): return await _legacy_voice_ai_handler(*args, **kwargs)
