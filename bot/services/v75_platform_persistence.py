"""v75_platform: persistence responsibilities."""
from .v75_platform_common import *  # noqa: F401,F403
from . import v75_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def backup_integrity(path: str | Path) -> dict[str, Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            size+=len(block); h.update(block)
    return {"ok":size>0,"size":size,"sha256":h.hexdigest()}
