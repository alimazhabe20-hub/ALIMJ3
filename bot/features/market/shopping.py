"""Public compatibility facade for shopping.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_shopping_common = _importlib.import_module(".shopping_common", __package__)
_shopping_models = _importlib.import_module(".shopping_models", __package__)
_shopping_parser = _importlib.import_module(".shopping_parser", __package__)
_shopping_search = _importlib.import_module(".shopping_search", __package__)
_shopping_filter = _importlib.import_module(".shopping_filter", __package__)
_shopping_public = _importlib.import_module(".shopping_public", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_shopping_common,_shopping_models,_shopping_parser,_shopping_search,_shopping_filter,_shopping_public]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_shopping_registration = _importlib.import_module(".shopping_registration", __package__)
_split_modules.append(_shopping_registration)
for _k, _v in _shopping_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
