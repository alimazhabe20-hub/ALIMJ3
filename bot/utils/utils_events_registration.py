"""Late registration/compatibility actions for utils_events."""
from .utils_events_common import *  # noqa
from .utils_events_calendar_data import merge_international_shamsi_events
from . import utils_events_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


shamsi_events = merge_international_shamsi_events(1405)
