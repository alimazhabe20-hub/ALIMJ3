from pathlib import Path

# Auto-split part 8: _validate_sqlite_backup
def _validate_sqlite_backup(path: Path) -> tuple[bool, str]:
    """Validate a candidate DB before it can replace the live database."""
    try:
        if path.stat().st_size < 100:
            return False, "فایل خیلی کوچک است"
        max_bytes = max(1024 * 1024, int(getattr(config, "RESTORE_MAX_BYTES", 256 * 1024 * 1024)))
        if path.stat().st_size > max_bytes:
            return False, "حجم فایل بیش از حد مجاز است"
        uri = f"file:{path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or str(integrity[0]).lower() != "ok":
                return False, "integrity_check ناموفق بود"
            conn.execute("PRAGMA foreign_key_check").fetchall()
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"users", "stats"}
            if not required.issubset(tables):
                return False, "ساختار دیتابیس با نسخه فعلی سازگار نیست"
            user_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
            required_user_cols = {
                "user_id", "first_name", "city", "country", "language", "subscribed",
                "register_date", "last_active", "notification_enabled", "notify_fajr",
                "notify_dhuhr", "notify_asr", "notify_maghrib", "notify_isha", "birth_date",
            }
            if not required_user_cols.issubset(user_cols):
                return False, "ستون‌های دیتابیس با نسخه فعلی سازگار نیست"
            stats_cols = {r[1] for r in conn.execute("PRAGMA table_info(stats)")}
            if not {"id", "date", "total_users", "active_users"}.issubset(stats_cols):
                return False, "ساختار جدول stats ناسازگار است"
            meta_exists = "schema_meta" in tables
            if meta_exists:
                row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                if row is not None:
                    try:
                        version = int(row[0])
                    except (TypeError, ValueError):
                        return False, "schema_version نامعتبر است"
                    if version > SCHEMA_VERSION:
                        return False, "نسخه schema این بکاپ جدیدتر از نسخه فعلی است"
            users = int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0)
            return True, str(users)
        finally:
            conn.close()
    except Exception:
        return False, "فایل SQLite معتبر نیست"
