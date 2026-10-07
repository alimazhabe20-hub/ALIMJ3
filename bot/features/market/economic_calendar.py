"""Public compatibility facade for economic_calendar.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_economic_calendar_common = _importlib.import_module(".economic_calendar_common", __package__)
_economic_calendar_parsing = _importlib.import_module(".economic_calendar_parsing", __package__)
_economic_calendar_providers = _importlib.import_module(".economic_calendar_providers", __package__)
_economic_calendar_formatting = _importlib.import_module(".economic_calendar_formatting", __package__)
_economic_calendar_navigation = _importlib.import_module(".economic_calendar_navigation", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_economic_calendar_common,_economic_calendar_parsing,_economic_calendar_providers,_economic_calendar_formatting,_economic_calendar_navigation]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_economic_calendar_registration = _importlib.import_module(".economic_calendar_registration", __package__)
_split_modules.append(_economic_calendar_registration)
for _k, _v in _economic_calendar_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
