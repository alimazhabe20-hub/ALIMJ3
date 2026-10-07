"""Late registration/compatibility actions for finance_ta."""
from .finance_ta_common import *  # noqa
from . import finance_ta_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

