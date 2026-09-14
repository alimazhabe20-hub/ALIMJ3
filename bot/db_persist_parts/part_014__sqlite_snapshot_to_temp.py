from pathlib import Path

# Auto-split part 14: _sqlite_snapshot_to_temp
def _sqlite_snapshot_to_temp() -> Path | None:
    """اسنپ‌شات امن SQLite (شامل WAL) به فایل موقت — برای آپلود/ارسال."""
    src_path = Path(DB_PATH)
    if not src_path.exists():
        return None
    tmp = src_path.with_suffix(f".db.snap.{secrets.token_hex(4)}")
    try:
        src = sqlite3.connect(str(src_path), timeout=30, check_same_thread=False)
        try:
            # ادغام WAL قبل از بکاپ تا چیزی جا نماند
            try:
                src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            dst = sqlite3.connect(str(tmp), timeout=30, check_same_thread=False)
            try:
                src.backup(dst)
                dst.commit()
            finally:
                dst.close()
        finally:
            src.close()
        if tmp.stat().st_size < 100:
            tmp.unlink(missing_ok=True)
            return None
        return tmp
    except Exception as exc:
        logger.error("sqlite snapshot failed: %s", exc)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return None
