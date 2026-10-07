"""Public compatibility facade for database.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_database_common = _importlib.import_module(".database_common", __package__)
_database_core = _importlib.import_module(".database_core", __package__)
_database_users = _importlib.import_module(".database_users", __package__)
_database_notifications = _importlib.import_module(".database_notifications", __package__)
_database_reminders = _importlib.import_module(".database_reminders", __package__)
_database_ai = _importlib.import_module(".database_ai", __package__)
_database_calendar = _importlib.import_module(".database_calendar", __package__)
_database_stats = _importlib.import_module(".database_stats", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_database_common,_database_core,_database_users,_database_notifications,_database_reminders,_database_ai,_database_calendar,_database_stats]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_database_registration = _importlib.import_module(".database_registration", __package__)
_split_modules.append(_database_registration)
for _k, _v in _database_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v
