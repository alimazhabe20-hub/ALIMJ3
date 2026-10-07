"""Late registration/compatibility actions for database."""
from .database_common import *  # noqa
from . import database_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


AZAN_FIELDS = {
    "fajr": ("notify_fajr", "اذان صبح"),
    "dhuhr": ("notify_dhuhr", "اذان ظهر"),
    "asr": ("notify_asr", "اذان عصر"),
    "maghrib": ("notify_maghrib", "اذان مغرب"),
    "isha": ("notify_isha", "اذان عشاء"),
}
