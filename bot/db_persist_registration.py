"""Late registration/compatibility actions for db_persist."""
from .db_persist_common import *  # noqa
from . import db_persist_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


_LAST_RESTORE_STATUS: dict[str, str | bool | int] = {
    "ok": False,
    "msg": "",
    "local_users": 0,
    "remote_users": -1,
}
