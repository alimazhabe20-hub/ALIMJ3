"""Public compatibility facade for finance.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_finance_common = _importlib.import_module(".finance_common", __package__)
_finance_chart = _importlib.import_module(".finance_chart", __package__)
_finance_context = _importlib.import_module(".finance_context", __package__)
_finance_analysis = _importlib.import_module(".finance_analysis", __package__)
_finance_signals = _importlib.import_module(".finance_signals", __package__)
_finance_tools = _importlib.import_module(".market_finance_tools", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_finance_common,_finance_chart,_finance_context,_finance_analysis,_finance_signals,_finance_tools]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_finance_registration = _importlib.import_module(".finance_registration", __package__)
_split_modules.append(_finance_registration)
for _k, _v in _finance_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
