"""Public compatibility facade for finance_core.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_finance_core_common = _importlib.import_module(".finance_core_common", __package__)
_finance_core_pricing = _importlib.import_module(".finance_core_pricing", __package__)
_finance_core_crypto = _importlib.import_module(".finance_core_crypto", __package__)
_finance_core_currency = _importlib.import_module(".finance_core_currency", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_finance_core_common,_finance_core_pricing,_finance_core_crypto,_finance_core_currency]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_finance_core_registration = _importlib.import_module(".finance_core_registration", __package__)
_split_modules.append(_finance_core_registration)
for _k, _v in _finance_core_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
