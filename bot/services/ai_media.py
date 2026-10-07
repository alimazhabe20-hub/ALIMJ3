"""Public compatibility facade for ai_media.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_ai_media_common = _importlib.import_module(".ai_media_common", __package__)
_ai_media_image = _importlib.import_module(".ai_media_image", __package__)
_ai_media_voice = _importlib.import_module(".ai_media_voice", __package__)
_ai_media_creative = _importlib.import_module(".ai_media_creative", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_ai_media_common,_ai_media_image,_ai_media_voice,_ai_media_creative]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_ai_media_registration = _importlib.import_module(".ai_media_registration", __package__)
_split_modules.append(_ai_media_registration)
for _k, _v in _ai_media_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
