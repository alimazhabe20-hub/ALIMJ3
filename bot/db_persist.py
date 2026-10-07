"""Public compatibility facade for db_persist.

Semantically split into focused modules; historical imports remain stable.
"""
import importlib as _importlib

_db_persist_common = _importlib.import_module(".db_persist_common", __package__)
_db_persist_telegram = _importlib.import_module(".db_persist_telegram", __package__)
_db_persist_github = _importlib.import_module(".db_persist_github", __package__)
_db_persist_backup = _importlib.import_module(".db_persist_backup", __package__)

# Wire all split modules into one compatible namespace so legacy cross-function
# references keep resolving without duplicating implementation.
_split_modules = [_db_persist_common,_db_persist_telegram,_db_persist_github,_db_persist_backup]
for _m in _split_modules:
    for _o in _split_modules:
        if _m is not _o:
            for _k, _v in _o.__dict__.items():
                if not _k.startswith("__"):
                    _m.__dict__.setdefault(_k, _v)

# Execute late registrations/aliases only after every implementation module is loaded.
_db_persist_registration = _importlib.import_module(".db_persist_registration", __package__)
_split_modules.append(_db_persist_registration)
for _k, _v in _db_persist_registration.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

# Export every historical symbol, including private helpers used by sibling modules.
for _m in _split_modules:
    for _k, _v in _m.__dict__.items():
        if not _k.startswith("__") and _k not in {"_m","_o","_k","_v"}:
            globals()[_k] = _v


# Compatibility wrappers: keep the public facade's monkey-patchable dependency
# surface identical to the pre-refactor module.
def auto_restore_if_empty(*args, **kwargs):
    for _name in (
        "telegram_backup_enabled", "telegram_download_pinned_db",
        "github_enabled", "github_download_db", "_user_count", "DB_PATH",
    ):
        if _name in globals():
            setattr(_db_persist_backup, _name, globals()[_name])
    return _db_persist_backup.auto_restore_if_empty(*args, **kwargs)


def get_last_restore_status(*args, **kwargs):
    return _db_persist_backup.get_last_restore_status(*args, **kwargs)
