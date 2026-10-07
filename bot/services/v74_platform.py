"""Public compatibility facade for v74_platform.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_v74_platform_common = _importlib.import_module(".v74_platform_common", __package__)
_v74_platform_security = _importlib.import_module(".v74_platform_security", __package__)
_v74_platform_agent = _importlib.import_module(".v74_platform_agent", __package__)
_v74_platform_performance = _importlib.import_module(".v74_platform_performance", __package__)
_v74_platform_knowledge = _importlib.import_module(".v74_platform_knowledge", __package__)
_v74_platform_persistence = _importlib.import_module(".v74_platform_persistence", __package__)
_v74_platform_providers = _importlib.import_module(".v74_platform_providers", __package__)
_v74_platform_runtime = _importlib.import_module(".v74_platform_runtime", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_v74_platform_common,_v74_platform_security,_v74_platform_agent,_v74_platform_performance,_v74_platform_knowledge,_v74_platform_persistence,_v74_platform_providers,_v74_platform_runtime]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_v74_platform_registration = _importlib.import_module(".v74_platform_registration", __package__)
_split_modules.append(_v74_platform_registration)
for _k, _v in _v74_platform_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
