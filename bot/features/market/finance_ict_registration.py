"""Late registration/compatibility actions for finance_ict."""
from .finance_ict_common import *  # noqa
from . import finance_ict_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})

