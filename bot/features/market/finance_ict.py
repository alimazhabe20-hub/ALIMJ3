"""Public compatibility facade for finance_ict.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_finance_ict_common = _importlib.import_module(".finance_ict_common", __package__)
_finance_ict_math = _importlib.import_module(".finance_ict_math", __package__)
_finance_ict_structure = _importlib.import_module(".finance_ict_structure", __package__)
_finance_ict_zones = _importlib.import_module(".finance_ict_zones", __package__)
_finance_ict_scenarios = _importlib.import_module(".finance_ict_scenarios", __package__)
_finance_ict_public = _importlib.import_module(".finance_ict_public", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_finance_ict_common,_finance_ict_math,_finance_ict_structure,_finance_ict_zones,_finance_ict_scenarios,_finance_ict_public]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_finance_ict_registration = _importlib.import_module(".finance_ict_registration", __package__)
_split_modules.append(_finance_ict_registration)
for _k, _v in _finance_ict_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
