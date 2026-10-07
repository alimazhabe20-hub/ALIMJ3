"""Public compatibility facade for utils_events.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_utils_events_common = _importlib.import_module(".utils_events_common", __package__)
_utils_events_calendar_data = _importlib.import_module(".utils_events_calendar_data", __package__)
_utils_events_conversion = _importlib.import_module(".utils_events_conversion", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_utils_events_common,_utils_events_calendar_data,_utils_events_conversion]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_utils_events_registration = _importlib.import_module(".utils_events_registration", __package__)
_split_modules.append(_utils_events_registration)
for _k, _v in _utils_events_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
