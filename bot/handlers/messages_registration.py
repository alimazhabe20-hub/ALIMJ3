"""Late registration/compatibility actions for messages."""
from .messages_common import *  # noqa
from . import messages_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_legacy_text_handler = text_handler

_legacy_media_ai_handler = media_ai_handler

_legacy_voice_ai_handler = voice_ai_handler

_legacy_lens_command = lens_command
