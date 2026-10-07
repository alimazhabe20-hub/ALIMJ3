"""Public compatibility facade for messages.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_messages_common = _importlib.import_module(".messages_common", __package__)
_messages_ai = _importlib.import_module(".messages_ai", __package__)
_messages_routing = _importlib.import_module(".messages_routing", __package__)
_messages_media = _importlib.import_module(".messages_media", __package__)
_messages_main = _importlib.import_module(".messages_main", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_messages_common,_messages_ai,_messages_routing,_messages_media,_messages_main]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_messages_registration = _importlib.import_module(".messages_registration", __package__)
_split_modules.append(_messages_registration)
for _k, _v in _messages_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
