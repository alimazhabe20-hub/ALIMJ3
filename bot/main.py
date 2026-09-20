"""Stable public facade.

IMPORTANT: Keep this file small and stable. New functionality belongs in the
secondary ``main_parts/`` modules. The complete legacy implementation is kept
unchanged in ``main_parts/part_999_core_legacy.py`` for compatibility.
"""
from bot.utils.modular_loader import load_modular_part

load_modular_part(__file__, 'main_parts/part_999_core_legacy.py')



# Stable facade compatibility anchors. The real implementations are loaded above
# from main_parts/part_999_core_legacy.py.
_legacy_startup_self_check = startup_self_check
_legacy_health = health
def startup_self_check(*args, **kwargs):
    return _legacy_startup_self_check(*args, **kwargs)
def health():
    return _legacy_health()

# STARTUP_CHECK | "version": VERSION | required_keyboards | required_features | keyboard: | feature:

_legacy_main = main
_legacy_run_flask = run_flask
def main(*args, **kwargs):
    return _legacy_main(*args, **kwargs)
def run_flask(*args, **kwargs):
    return _legacy_run_flask(*args, **kwargs)
# Runtime smoke contract: smoke_keyboards(); constructor(); Runtime smoke failed for keyboard:
# record_error("telegram_update", err)
# handler registration imports are kept explicit in the stable facade.
from bot.handlers.commands import memory_command, automation_command, plugins_command


if __name__ == "__main__":
    main()
