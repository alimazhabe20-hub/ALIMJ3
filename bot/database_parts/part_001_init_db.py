# Auto-split part 1: init_db
def init_db() -> None:
    logger.info(f"Initializing database at {DB_PATH} ...")
    restore_from_backup_if_needed()
    # ریستور خودکار از GitHub (اگر DB خالی و تنظیمات موجود باشد)
    try:
        from bot.db_persist import auto_restore_if_empty
        auto_restore_if_empty()
    except Exception as e:
        logger.error(f"auto_restore_if_empty: {e}")

    conn = get_db_connection()
    c = conn.cursor()
    # فقط CREATE IF NOT EXISTS — هیچ‌وقت جدول users را DROP نمی‌کنیم
    c.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "user_id INTEGER PRIMARY KEY,"
        "first_name TEXT,"
        "city TEXT DEFAULT 'قم',"
        "country TEXT DEFAULT 'Iran',"
        "language TEXT DEFAULT 'fa',"
        "subscribed INTEGER DEFAULT 1,"
        "register_date TEXT,"
        "last_active TEXT,"
        "notification_enabled INTEGER DEFAULT 0,"
        "notify_fajr INTEGER DEFAULT 0,"
        "notify_dhuhr INTEGER DEFAULT 0,"
        "notify_asr INTEGER DEFAULT 0,"
        "notify_maghrib INTEGER DEFAULT 0,"
        "notify_isha INTEGER DEFAULT 0"
        ")"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS stats ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "date TEXT,"
        "total_users INTEGER,"
        "active_users INTEGER"
        ")"
    )
    for col, default in (
        ("last_main_msg_id", "INTEGER"),
        ("notification_enabled", "INTEGER DEFAULT 0"),
        ("notify_fajr", "INTEGER DEFAULT 0"),
        ("notify_dhuhr", "INTEGER DEFAULT 0"),
        ("notify_asr", "INTEGER DEFAULT 0"),
        ("notify_maghrib", "INTEGER DEFAULT 0"),
        ("notify_isha", "INTEGER DEFAULT 0"),
        ("birth_date", "TEXT"),
    ):
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {default}")
        except sqlite3.OperationalError:
            # Column already exists — expected on upgraded databases
            pass
        except Exception as mig_exc:
            logger.debug("users migration %s failed: %s", col, mig_exc)
    conn.commit()
    conn.close()
    init_extra_tables()
    # V61-V65 platform tables: memory, watchlist, price alerts, metrics.
    try:
        from bot.services.v61_v65_platform import init_platform_tables
        init_platform_tables()
    except Exception as platform_exc:
        logger.error("platform table initialization failed: %s", platform_exc)
    try:
        from bot.services.v70_platform import init_v70_tables
        init_v70_tables()
        from bot.services.v71_platform import init_v71_tables
        init_v71_tables()
        from bot.services.v73_platform import init_v73_tables
        init_v73_tables()
        from bot.services.v74_platform import init_v74_tables
        init_v74_tables()
        from bot.services.v75_platform import init_v75_tables
        init_v75_tables()
        from bot.services.v76_platform import init_v76_tables
        init_v76_tables()
        from bot.services.v77_platform import init_v77_tables
        init_v77_tables()
    except Exception as v70_exc:
        logger.error("V70/V71/V73 table initialization failed: %s", v70_exc)
    # V36: ثبت و کنترل نسخه schema؛ هیچ داده‌ای حذف یا بازنویسی نمی‌شود.
    conn = get_db_connection()
    try:
        ensure_schema_version(conn, DB_PATH)
    finally:
        conn.close()
    # یک‌بار: اذان‌ها پیش‌فرض خاموش (مگر کاربر خودش روشن کرده باشد بعد از این)
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("SELECT value FROM meta WHERE key = 'azan_off_by_default_v2'")
        row = c.fetchone()
        if not row:
            c.execute(
                "UPDATE users SET notification_enabled = 0, "
                "notify_fajr = 0, notify_dhuhr = 0, notify_asr = 0, "
                "notify_maghrib = 0, notify_isha = 0"
            )
            c.execute(
                "INSERT INTO meta (key, value) VALUES ('azan_off_by_default_v2', '1')"
            )
            conn.commit()
            logger.info("Migration: all azan notifications set to OFF by default")
        conn.close()
    except Exception as e:
        logger.error(f"azan migration: {e}")
    n = _user_count(DB_PATH)
    logger.info(f"Database ready — {n} users")
