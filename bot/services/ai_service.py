"""Public compatibility facade for ai_service.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_ai_service_common = _importlib.import_module(".ai_service_common", __package__)
_ai_service_config = _importlib.import_module(".ai_service_config", __package__)
_ai_service_providers = _importlib.import_module(".ai_service_providers", __package__)
_ai_service_memory = _importlib.import_module(".ai_service_memory", __package__)
_ai_service_media = _importlib.import_module(".ai_service_media", __package__)
_ai_service_voice = _importlib.import_module(".ai_service_voice", __package__)
_ai_service_creative = _importlib.import_module(".ai_service_creative", __package__)
_ai_service_router = _importlib.import_module(".ai_service_router", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_ai_service_common,_ai_service_config,_ai_service_providers,_ai_service_memory,_ai_service_media,_ai_service_voice,_ai_service_creative,_ai_service_router]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_ai_service_registration = _importlib.import_module(".ai_service_registration", __package__)
_split_modules.append(_ai_service_registration)
for _k, _v in _ai_service_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
