"""Public compatibility facade for downloader.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_downloader_common = _importlib.import_module(".downloader_common", __package__)
_downloader_validation = _importlib.import_module(".downloader_validation", __package__)
_downloader_providers = _importlib.import_module(".downloader_providers", __package__)
_downloader_cache = _importlib.import_module(".downloader_cache", __package__)
_downloader_public = _importlib.import_module(".downloader_public", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_downloader_common,_downloader_validation,_downloader_providers,_downloader_cache,_downloader_public]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_downloader_registration = _importlib.import_module(".downloader_registration", __package__)
_split_modules.append(_downloader_registration)
for _k, _v in _downloader_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
