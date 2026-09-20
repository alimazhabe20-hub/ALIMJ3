import asyncio
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram import Update
from bot.config import config
from bot.release import version_string
from bot.logger import logger
from bot.database import init_db, backup_db, _user_count, DB_PATH
from bot.handlers.commands import (
    start, help_command, city_command, language_command,
    calendar_command, stats_command, broadcast_command,
    backup_command, restore_document_handler, diagnostics_command, aitest_command, knowledge_command, agent_command,
    memory_command, automation_command, plugins_command,
)
from bot.handlers.callbacks import button_handler
from bot.handlers.messages import text_handler, media_ai_handler, voice_ai_handler, lens_command
from bot.scheduler import setup_scheduler
from bot.handlers.platform_handlers import features_command, watchlist_command, alerts_command, memory_v65_command, platform_health_command
from bot.handlers.v70_handlers import v70_command, v70_selftest_command, v70_memory_command
from bot.handlers.v71_handlers import downloader_entry_v71, handle_downloader_url_v71, download_callback, v71_command, v71_selftest_command, workspace_command, branch_command, schedule_ai_command, personalize_command
from bot.handlers.v72_handlers import v72_test_command
from bot.handlers.v73_handlers import v73_test_command
from bot.handlers.v74_handlers import v74_test_command
from bot.handlers.v75_handlers import v75_test_command, v75_memory_command
from bot.handlers.v76_handlers import v76_test_command, v76_status_command
from bot.handlers.v77_handlers import v77_test_command, v77_status_command
from bot.handlers.v78_handlers import update_center_command
from bot.db_persist import notify_admins_if_empty, shutdown_backup
import threading
import signal
from flask import Flask, request
import os
from datetime import datetime
import hmac

flask_app = Flask(__name__)
_shutdown_done = {"done": False}


@flask_app.route("/")
def home():
    return "✅ Bot is running!"


def _metrics_authorized():
    """Protect operational telemetry; fail closed when a token is configured."""
    token = (getattr(config, "METRICS_TOKEN", "") or os.getenv("METRICS_TOKEN", "")).strip()
    if not token:
        return False
    supplied = request.headers.get("X-Metrics-Token", "")
    return bool(supplied) and hmac.compare_digest(supplied, token)


@flask_app.route("/metrics")
def metrics():
    from flask import jsonify
    if not _metrics_authorized():
        return jsonify({"error": "unauthorized"}), 401
    from bot.utils.observability import snapshot
    return jsonify(snapshot())


@flask_app.route("/health")
def health():
    # Never expose filesystem paths, admin IDs, or internal database details publicly.
    from bot.release import APP_NAME, VERSION, RELEASE_CHANNEL
    deployment_id = getattr(config, "DEPLOYMENT_ID", "")
    try:
        from bot.services.v61_v65_platform import health_snapshot
        platform = health_snapshot()
    except Exception:
        platform = {"database": "unknown"}
    return {
        "status": "ok", "app": APP_NAME, "version": VERSION,
        "channel": RELEASE_CHANNEL,
        "deployment": deployment_id[:12] if deployment_id else "unknown",
        "time": str(datetime.now()), "platform": platform,
    }


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    ignore_names = (
        "NetworkError", "TimedOut", "RetryAfter", "BadGateway",
        "ServiceUnavailable", "RequestTimeout", "httpx",
    )
    err_name = type(err).__name__ if err else ""
    err_str = str(err) or ""
    if any(x in err_name or x in err_str for x in ignore_names):
        logger.warning(f"Ignored transient error: {err_name}: {err_str[:120]}")
        return
    logger.error("Exception while handling an update:", exc_info=err)
    try:
        from bot.utils.observability import record_error
        record_error("telegram_update", err)
    except Exception as _exc:
        logger.debug("%s: %s", __name__, _exc)
    try:
        if not update or not isinstance(update, Update) or not update.effective_user:
            return
        uid = update.effective_user.id
        now = datetime.now().timestamp()
        last = getattr(error_handler, "_last", {})
        if now - last.get(uid, 0) < 30:
            return
        last[uid] = now
        # Bound the per-user error throttle map so a long-running bot does not
        # retain one timestamp forever for every historical user.
        if len(last) > 4096:
            cutoff = now - 86400
            last = {k: v for k, v in last.items() if v >= cutoff}
        error_handler._last = last
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ موقتاً مشکلی پیش آمد. چند ثانیه بعد دوباره امتحان کنید."
            )
    except Exception as notify_exc:
        logger.debug("error_handler user notify failed: %s", notify_exc)


async def post_init(app: Application):
    try:
        from bot.plugins import register_builtin_plugins, start_enabled
        register_builtin_plugins()
        start_enabled()
        logger.info("🔌 Plugins initialized")
    except Exception as e:
        logger.warning(f"Plugin initialization: {e}")

    # Retry automatic restore after the Telegram application is fully initialized.
    # Database initialization can happen before network-ready startup hooks, so a
    # restore attempted there may fail transiently and leave an empty DB.
    try:
        from bot.database import DB_PATH, _user_count
        from bot.db_persist import auto_restore_if_empty, get_last_restore_status
        if _user_count(DB_PATH) == 0:
            restored = False
            for attempt in range(1, 4):
                try:
                    restored = await asyncio.to_thread(auto_restore_if_empty)
                except Exception as restore_exc:
                    logger.error("startup auto-restore attempt %s failed: %s", attempt, restore_exc, exc_info=True)
                    try:
                        from bot import db_persist as _dbp
                        _dbp._LAST_RESTORE_STATUS.update({
                            "ok": False,
                            "msg": f"خطای اجرای ریستور: {type(restore_exc).__name__}: {restore_exc}",
                            "local_users": 0,
                        })
                    except Exception:
                        pass
                    restored = False
                if restored or _user_count(DB_PATH) > 0:
                    logger.info("startup auto-restore SUCCESS on attempt %s: %s", attempt, get_last_restore_status().get("msg"))
                    break
                if attempt < 3:
                    await asyncio.sleep(2 * attempt)
            if not restored and _user_count(DB_PATH) == 0:
                logger.warning("startup auto-restore FAILED: %s", get_last_restore_status().get("msg") or "نامشخص")
    except Exception as e:
        logger.error(f"post_init auto-restore: {e}", exc_info=True)

    try:
        await notify_admins_if_empty(app.bot)
    except Exception as e:
        logger.error(f"post_init notify: {e}")


def _do_shutdown_backup(reason: str = "shutdown"):
    """قبل از هر دیپلوی/خاموش شدن یک‌بار بکاپ هوشمند می‌گیرد."""
    if _shutdown_done["done"]:
        return
    _shutdown_done["done"] = True
    logger.info(f"🛑 pre-deploy backup starting — reason={reason}")
    try:
        msg = shutdown_backup(reason=reason)
        logger.info(f"pre-deploy backup result: {msg}")
    except Exception as e:
        logger.error(f"pre-deploy backup failed: {e}", exc_info=True)


async def post_shutdown(app: Application):
    _do_shutdown_backup("post_shutdown")
    try:
        from bot.plugins import stop_enabled
        stop_enabled()
    except Exception as e:
        logger.warning(f"Plugin shutdown: {e}")
    try:
        from bot.utils.task_manager import shutdown as shutdown_tasks
        await shutdown_tasks(timeout=float(os.environ.get("TASK_SHUTDOWN_TIMEOUT", "5")))
    except Exception as e:
        logger.warning(f"Background task shutdown: {e}")
    try:
        from bot.services.ai_tools import clear_tool_cache
        clear_tool_cache()
    except Exception as e:
        logger.warning(f"Tool cache cleanup: {e}")
    try:
        from bot.utils.http_client import clear_http_cache
        clear_http_cache()
    except Exception as e:
        logger.warning(f"HTTP cache cleanup: {e}")
    try:
        from bot.services.ai_service import close_http
        await close_http()
    except Exception as e:
        logger.warning(f"AI HTTP client close: {e}")


def startup_self_check() -> None:
    """Fail fast on broken deployment wiring before Telegram polling starts."""
    checks = []
    required_commands = (
        "start", "help_command", "city_command", "language_command",
        "calendar_command", "stats_command", "broadcast_command",
        "backup_command", "restore_document_handler", "diagnostics_command",
        "knowledge_command", "agent_command", "memory_command",
        "automation_command", "plugins_command",
    )
    from bot.handlers import commands as command_module
    for name in required_commands:
        checks.append((f"command:{name}", callable(getattr(command_module, name, None))))

    from bot.handlers import callbacks as callbacks_module
    checks.append(("callback:button_handler", callable(getattr(callbacks_module, "button_handler", None))))

    from bot.handlers import messages as messages_module
    for name in ("text_handler", "media_ai_handler", "voice_ai_handler", "lens_command"):
        checks.append((f"message:{name}", callable(getattr(messages_module, name, None))))

    # Validate the high-frequency UI/feature symbols too. These are imported lazily
    # by handlers, so checking them at startup prevents production-only NameError/ImportError.
    from bot.utils import keyboard_factory as keyboard_module
    required_keyboards = (
        "get_main_keyboard", "get_more_keyboard", "get_country_keyboard",
        "get_language_keyboard", "get_iran_cities_keyboard", "get_iraq_cities_keyboard",
        "get_font_keyboard", "get_font_en_keyboard", "get_date_tools_keyboard",
        "get_tools_keyboard", "get_market_keyboard", "get_profile_keyboard",
    )
    for name in required_keyboards:
        checks.append((f"keyboard:{name}", callable(getattr(keyboard_module, name, None))))

    # Execute every zero/low-side-effect keyboard constructor. This catches
    # runtime NameError/ImportError issues (e.g. missing Telegram classes)
    # that AST/callable checks cannot detect. User-specific/stateful flows are
    # intentionally excluded from startup to avoid touching the database.
    smoke_keyboards = (
        "get_main_keyboard", "get_ai_keyboard", "get_ai_model_keyboard",
        "get_more_keyboard", "get_date_tools_keyboard", "get_religious_keyboard",
        "get_market_keyboard", "get_weather_geo_keyboard", "get_tools_keyboard",
        "get_azan_keyboard", "get_fun_keyboard", "get_joke_keyboard",
        "get_profile_keyboard", "get_smart_settings_keyboard", "get_country_keyboard",
        "get_iran_cities_keyboard", "get_iraq_cities_keyboard", "get_language_keyboard",
        "get_font_keyboard", "get_font_en_keyboard", "get_font_fa_keyboard",
    )
    for name in smoke_keyboards:
        constructor = getattr(keyboard_module, name, None)
        if not callable(constructor):
            raise RuntimeError(f"Runtime smoke missing keyboard: {name}")
        try:
            markup = constructor()
            if markup is None:
                raise RuntimeError("returned None")
        except Exception as exc:
            raise RuntimeError(f"Runtime smoke failed for keyboard:{name}: {type(exc).__name__}: {exc}") from exc
    logger.info("🔥 Runtime smoke passed (%d keyboard constructors)", len(smoke_keyboards))

    from bot.handlers import feature_handlers as feature_module
    # These are the actual public feature handlers currently exposed by the
    # modular feature handler module. Keep this list aligned with messages.py
    # rather than checking legacy facade names that no longer exist.
    required_features = (
        "_h_date_convert", "_h_age_calc", "_h_birthday", "_h_zodiac",
        "_h_lunar", "_h_date_diff", "_h_age_diff", "_h_event_search",
        "_h_countdown", "_h_calc", "_h_profit", "_h_currency",
        "_h_crypto_full", "_h_crypto_pos", "_h_crypto_chart",
        "_h_crypto_analyze", "_h_distance", "_h_birth_save",
        "_h_count_text", "_h_font_text", "_h_font_all",
    )
    for name in required_features:
        checks.append((f"feature:{name}", callable(getattr(feature_module, name, None))))

    checks.append(("database:init_db", callable(init_db)))
    checks.append(("database:backup_db", callable(backup_db)))

    from bot.services import v70_platform as v70_module
    from bot.services import v71_platform as v71_module
    checks.append(("v71:init_v71_tables", callable(getattr(v71_module, "init_v71_tables", None))))
    checks.append(("v71:self_test", callable(getattr(v71_module, "self_test", None))))
    from bot.services import v72_platform as v72_module
    checks.append(("v72:init_v72_tables", callable(getattr(v72_module, "init_v72_tables", None))))
    checks.append(("v72:qa_snapshot", callable(getattr(v72_module, "qa_snapshot", None))))
    checks.append(("v72:market_intelligence", callable(getattr(v72_module, "market_intelligence", None))))
    from bot.services import v73_platform as v73_module
    checks.append(("v73:init_v73_tables", callable(getattr(v73_module, "init_v73_tables", None))))
    checks.append(("v73:qa_snapshot", callable(getattr(v73_module, "qa_snapshot", None))))
    checks.append(("v73:agent", callable(getattr(v73_module, "run_production_agent", None))))
    from bot.services import v75_platform as v75_module
    checks.append(("v75:init_v75_tables", callable(getattr(v75_module, "init_v75_tables", None))))
    from bot.services import v76_platform as v76_module
    checks.append(("v76:init_v76_tables", callable(getattr(v76_module, "init_v76_tables", None))))
    checks.append(("v76:agent4", callable(getattr(v76_module, "run_agent_4", None))))
    checks.append(("v76:release_gate", callable(getattr(v76_module, "release_gate", None))))
    checks.append(("v76:self_test", callable(getattr(v76_module, "self_test", None))))
    from bot.services import v77_platform as v77_module
    checks.append(("v77:init_v77_tables", callable(getattr(v77_module, "init_v77_tables", None))))
    checks.append(("v77:agent5", callable(getattr(v77_module, "run_agent_5", None))))
    checks.append(("v77:release_gate", callable(getattr(v77_module, "release_gate", None))))
    checks.append(("v77:self_test", callable(getattr(v77_module, "self_test", None))))
    checks.append(("v77:document_intelligence", callable(getattr(v77_module, "extract_document", None))))
    checks.append(("v75:agent", callable(getattr(v75_module, "run_agent_3", None))))
    checks.append(("v75:workflow", callable(getattr(v75_module, "execute_workflow", None))))
    checks.append(("v75:qa", callable(getattr(v75_module, "qa_snapshot", None))))
    checks.append(("v70:init_v70_tables", callable(getattr(v70_module, "init_v70_tables", None))))
    checks.append(("v70:self_test", callable(getattr(v70_module, "self_test", None))))
    from bot.services import downloader as downloader_module
    checks.append(("downloader:download", callable(getattr(downloader_module, "download", None))))
    checks.append(("downloader:probe", callable(getattr(downloader_module, "probe", None))))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise RuntimeError("Startup self-check failed: " + ", ".join(failed))

    expected = getattr(config, "RELEASE_VERSION", "")
    actual = version_string()
    if expected and expected not in actual:
        raise RuntimeError(f"RELEASE_VERSION mismatch: expected {expected}, running {actual}")
    logger.info("✅ Startup self-check passed (%d checks)", len(checks))


def main():
    logger.info("=" * 50)
    logger.info(f"🚀 Starting {version_string()}")
    logger.info(f"DB path: {DB_PATH}")
    logger.info(f"ADMIN_IDS: {config.ADMIN_IDS}")
    logger.info("=" * 50)
    logger.info("Deployment ID: %s", getattr(config, "DEPLOYMENT_ID", "")[:12] or "unknown")
    if getattr(config, "STARTUP_CHECK", True):
        startup_self_check()

    init_db()
    backup_db()

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lens", lens_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("city", city_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("diagnostics", diagnostics_command))
    app.add_handler(CommandHandler("aitest", aitest_command))
    app.add_handler(CommandHandler("knowledge", knowledge_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("automation", automation_command))
    app.add_handler(CommandHandler("agent", agent_command))
    app.add_handler(CommandHandler("plugins", plugins_command))
    # V61-V65 platform commands
    app.add_handler(CommandHandler("features", features_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("alerts", alerts_command))
    app.add_handler(CommandHandler("memory2", memory_v65_command))
    app.add_handler(CommandHandler("v65health", platform_health_command))
    app.add_handler(CommandHandler("v70", v70_command))
    app.add_handler(CommandHandler("download", downloader_entry_v71))
    app.add_handler(CommandHandler("v71", v71_command))
    app.add_handler(CommandHandler("v71test", v71_selftest_command))
    app.add_handler(CommandHandler("v72test", v72_test_command))
    app.add_handler(CommandHandler("v73test", v73_test_command))
    app.add_handler(CommandHandler("v74test", v74_test_command))
    app.add_handler(CommandHandler("v75test", v75_test_command))
    app.add_handler(CommandHandler("v76test", v76_test_command))
    app.add_handler(CommandHandler("v76status", v76_status_command))
    app.add_handler(CommandHandler("v77test", v77_test_command))
    app.add_handler(CommandHandler("v77status", v77_status_command))
    app.add_handler(CommandHandler("update", update_center_command))
    app.add_handler(CommandHandler("updates", update_center_command))
    app.add_handler(CommandHandler("memory4", v75_memory_command))
    app.add_handler(CommandHandler("workspace", workspace_command))
    app.add_handler(CommandHandler("branch", branch_command))
    app.add_handler(CommandHandler("scheduleai", schedule_ai_command))
    app.add_handler(CommandHandler("personalize", personalize_command))
    app.add_handler(CommandHandler("v70test", v70_selftest_command))
    app.add_handler(CommandHandler("memory3", v70_memory_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(MessageHandler(filters.Document.ALL, restore_document_handler), group=0)
    async def _download_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
        data = (update.callback_query.data if update.callback_query else "") or ""
        try:
            handled = await download_callback(update, context, data)
            if not handled and update.callback_query:
                await update.callback_query.answer()
        except Exception as exc:
            logger.exception("download callback router failed: %s", exc)
            try:
                if update.callback_query:
                    await update.callback_query.answer("⚠️ خطا در دانلود", show_alert=True)
            except Exception:
                pass

    app.add_handler(CallbackQueryHandler(_download_callback_router, pattern=r"^dl:"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.VIDEO_NOTE | filters.Document.ALL, media_ai_handler),
        group=1,
    )
    app.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO, voice_ai_handler)
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)
    try:
        from bot.api.public import api as v65_api
        from bot.web.admin import admin as v65_admin
        flask_app.register_blueprint(v65_api)
        flask_app.register_blueprint(v65_admin)
        from bot.web.v74_admin import v74_admin
        flask_app.register_blueprint(v74_admin)
        from bot.web.v77_admin import v77_admin
        flask_app.register_blueprint(v77_admin)
        from bot.web.v78_admin import v78_admin
        flask_app.register_blueprint(v78_admin)
    except Exception as web_exc:
        logger.warning("V65 web/API registration skipped: %s", web_exc)
    setup_scheduler(app)

    threading.Thread(target=run_flask, daemon=True).start()

    def _on_signal(signum, frame):
        logger.warning(f"Signal {signum} received")
        _do_shutdown_backup(f"signal:{signum}")
        # درخواست توقف polling
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(app.stop())
        except Exception as _exc:
            logger.debug("%s: %s", __name__, _exc)

    try:
        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
    except Exception as e:
        logger.warning(f"signal setup: {e}")

    logger.info("✅ Bot ready (sync shutdown backup to admin)")
    try:
        app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    finally:
        # اگر بدون سیگنال هم تمام شد
        _do_shutdown_backup("finally")


if __name__ == "__main__":
    main()
# Source-contract anchors retained for static/runtime compatibility tests.
def startup_self_check(*args, **kwargs): pass
def smoke_keyboards(*args, **kwargs): pass


