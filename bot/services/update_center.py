"""ALIMJ3 Update Center.

Safe, read-only release discovery. The bot never replaces its own files from a
remote URL automatically. An operator publishes a small JSON manifest at
UPDATE_MANIFEST_URL; Update Center validates it, compares semantic versions,
checks local runtime/dependencies/schema, caches the result, and reports a
clear green/yellow/red status.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import re
import sqlite3
import time
import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from bot.config import config
from bot.logger import logger
from bot.release import APP_NAME, RELEASE_CHANNEL, VERSION
from bot.database import DB_PATH

CACHE_TTL = max(60, int(os.getenv("UPDATE_CHECK_TTL", "1800")))
TIMEOUT = max(3.0, min(30.0, float(os.getenv("UPDATE_CHECK_TIMEOUT", "10"))))
MAX_MANIFEST_BYTES = 512 * 1024
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _version_tuple(value: str) -> tuple[int, int, int]:
    m = _VERSION_RE.match(str(value or "").strip())
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())


def _is_public_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)
    except ValueError:
        return True


def _valid_manifest_url(url: str) -> bool:
    try:
        p = urlparse(url)
        host = p.hostname
        if p.scheme != "https" or not host or p.username or p.password or p.port not in (None, 443):
            return False
        if not _is_public_ip(host):
            return False
        # Resolve hostnames before connecting to reject private/link-local DNS answers.
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return bool(infos) and all(_is_public_ip(item[4][0]) for item in infos)
    except Exception:
        return False


def _manifest_url() -> str:
    return (os.getenv("UPDATE_MANIFEST_URL", "") or "").strip()


def _cache_path() -> Path:
    return Path(getattr(config, "BACKUP_DIR", "data/backups")) / "update_center.json"


def _load_cache() -> dict[str, Any] | None:
    path = _cache_path()
    try:
        if not path.exists() or time.time() - path.stat().st_mtime > CACHE_TTL:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _save_cache(data: dict[str, Any]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.debug("update center cache write failed: %s", exc)


def _read_manifest() -> tuple[dict[str, Any] | None, str | None]:
    url = _manifest_url()
    if not url:
        return None, "manifest_not_configured"
    if not _valid_manifest_url(url):
        return None, "manifest_url_invalid"
    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"Accept": "application/json", "User-Agent": "ALIMJ3-UpdateCenter/1.0"},
            allow_redirects=False,
        )
        if response.status_code != 200:
            return None, f"manifest_http_{response.status_code}"
        raw = response.content
        if len(raw) > MAX_MANIFEST_BYTES:
            return None, "manifest_too_large"
        data = response.json()
        if not isinstance(data, dict):
            return None, "manifest_invalid_json"
        version = str(data.get("version", ""))
        if not _VERSION_RE.match(version):
            return None, "manifest_version_invalid"
        data["version"] = version.lstrip("v")
        return data, None
    except requests.RequestException:
        return None, "manifest_network_error"
    except (ValueError, TypeError):
        return None, "manifest_invalid_json"
    except Exception:
        return None, "manifest_error"


def _dependency_check() -> dict[str, Any]:
    required = {
        "telegram": "python-telegram-bot",
        "requests": "requests",
        "httpx": "httpx",
        "flask": "Flask",
        "pypdf": "pypdf",
        "openpyxl": "openpyxl",
        "reportlab": "reportlab",
        "docx": "python-docx",
        "yt_dlp": "yt-dlp",
    }
    missing = [label for module, label in required.items() if importlib.util.find_spec(module) is None]
    return {"ok": not missing, "missing": missing}


def _schema_check() -> dict[str, Any]:
    try:
        if not Path(DB_PATH).exists():
            return {"ok": True, "status": "database_not_created_yet"}
        from bot.database_migrations import schema_status
        conn = sqlite3.connect(DB_PATH)
        try:
            status = schema_status(conn)
        finally:
            conn.close()
        return {"ok": int(status["version"]) <= int(status["supported_version"]), "status": status}
    except Exception:
        return {"ok": False, "status": "schema_check_failed"}


def _local_checks() -> dict[str, Any]:
    py_ok = tuple(int(x) for x in platform.python_version_tuple()[:3]) >= (3, 10, 0)
    dep = _dependency_check()
    schema = _schema_check()
    return {
        "python": {"ok": py_ok, "version": platform.python_version()},
        "dependencies": dep,
        "database": schema,
        "release": {"version": VERSION, "channel": RELEASE_CHANNEL, "app": APP_NAME},
        "ok": bool(py_ok and dep["ok"] and schema["ok"]),
    }


def _status_for(current: str, manifest: dict[str, Any] | None, error: str | None) -> str:
    if error:
        return "unknown"
    latest = _version_tuple(str(manifest.get("version", "0.0.0"))) if manifest else _version_tuple(current)
    cur = _version_tuple(current)
    if latest > cur:
        return "update_required" if str(manifest.get("severity", "")).lower() in {"critical", "required", "security"} else "update_available"
    return "up_to_date"


def _safe_manifest_view(manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    if not manifest:
        return None
    allowed = ("version", "severity", "release_date", "title", "notes", "min_supported_version", "package_url", "sha256", "changelog_url")
    out = {k: manifest[k] for k in allowed if k in manifest}
    if "package_url" in out and not _valid_manifest_url(str(out["package_url"])):
        out.pop("package_url", None)
    if "changelog_url" in out and not _valid_manifest_url(str(out["changelog_url"])):
        out.pop("changelog_url", None)
    return out


def check_for_updates(*, force: bool = False) -> dict[str, Any]:
    """Return a safe update report. No remote code is executed or installed."""
    if not force:
        cached = _load_cache()
        if cached:
            cached["cached"] = True
            return cached

    manifest, error = _read_manifest()
    local = _local_checks()
    current = VERSION
    latest = str(manifest.get("version")) if manifest else current
    status = _status_for(current, manifest, error)
    result: dict[str, Any] = {
        "ok": bool(local["ok"] and status != "unknown"),
        "status": status,
        "current_version": current,
        "latest_version": latest,
        "channel": RELEASE_CHANNEL,
        "manifest_configured": bool(_manifest_url()),
        "manifest_error": error,
        "local_checks": local,
        "release": _safe_manifest_view(manifest),
        "checked_at": int(time.time()),
        "cached": False,
    }
    if manifest:
        min_supported = str(manifest.get("min_supported_version", "0.0.0"))
        if _version_tuple(current) < _version_tuple(min_supported):
            result["status"] = "update_required"
            result["ok"] = False
            result["reason"] = "current_version_below_min_supported"
    _save_cache(result)
    return result


def update_summary(result: dict[str, Any], lang: str = "fa") -> str:
    status = result.get("status")
    current = result.get("current_version", VERSION)
    latest = result.get("latest_version", current)
    release = result.get("release") or {}
    notes = str(release.get("notes", "")).strip()
    severity = str(release.get("severity", "")).lower()
    if lang == "en":
        if status == "up_to_date": head = "🟢 Your bot is up to date."
        elif status == "update_available": head = f"🟡 Update available: v{latest} (current v{current})"
        elif status == "update_required": head = f"🔴 Update required: v{latest} (current v{current})"
        else: head = "⚪ Update status is unavailable. Configure UPDATE_MANIFEST_URL."
        lines = ["🔄 Update Center", head, f"Runtime: {'✅ healthy' if result.get('local_checks', {}).get('ok') else '⚠️ needs attention'}"]
        if severity: lines.append(f"Severity: {severity}")
        if notes: lines.append(f"Notes: {notes[:900]}")
        return "\n".join(lines)
    if lang == "ar":
        if status == "up_to_date": head = "🟢 البوت محدث إلى آخر إصدار."
        elif status == "update_available": head = f"🟡 يوجد تحديث: v{latest} (الحالي v{current})"
        elif status == "update_required": head = f"🔴 التحديث مطلوب: v{latest} (الحالي v{current})"
        else: head = "⚪ حالة التحديث غير متاحة. اضبط UPDATE_MANIFEST_URL."
        lines = ["🔄 مركز التحديث", head, f"حالة التشغيل: {'✅ سليمة' if result.get('local_checks', {}).get('ok') else '⚠️ تحتاج إلى مراجعة'}"]
        if severity: lines.append(f"الأهمية: {severity}")
        if notes: lines.append(f"ملاحظات: {notes[:900]}")
        return "\n".join(lines)
    if status == "up_to_date": head = "🟢 ربات شما به‌روز است."
    elif status == "update_available": head = f"🟡 بروزرسانی موجود است: v{latest} (نسخه فعلی v{current})"
    elif status == "update_required": head = f"🔴 بروزرسانی ضروری است: v{latest} (نسخه فعلی v{current})"
    else: head = "⚪ وضعیت بروزرسانی قابل دریافت نیست؛ UPDATE_MANIFEST_URL را تنظیم کنید."
    lines = ["🔄 مرکز بروزرسانی", head, f"سلامت اجرا: {'✅ سالم' if result.get('local_checks', {}).get('ok') else '⚠️ نیازمند بررسی'}"]
    if severity: lines.append(f"اهمیت: {severity}")
    if notes: lines.append(f"توضیحات: {notes[:900]}")
    return "\n".join(lines)


def maybe_notify_admins(result: dict[str, Any], send_message) -> int:
    """Notify admins once per newly discovered release; never sends user data."""
    if result.get("status") not in {"update_available", "update_required"}:
        return 0
    latest = str(result.get("latest_version", ""))
    if not latest:
        return 0
    state_path = _cache_path().with_name("update_center_notify.json")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except Exception:
        state = {}
    if state.get("last_notified_version") == latest:
        return 0
    sent = 0
    for admin_id in getattr(config, "ADMIN_IDS", []) or []:
        try:
            send_message(admin_id, update_summary(result, "fa"))
            sent += 1
        except Exception as exc:
            logger.warning("update admin notification failed: %s", exc)
    if sent:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"last_notified_version": latest, "notified_at": int(time.time())}), encoding="utf-8")
        except Exception:
            pass
    return sent


def self_test() -> dict[str, Any]:
    local = _local_checks()
    url = _manifest_url()
    url_ok = (not url) or _valid_manifest_url(url)
    return {"ok": bool(local["ok"] and url_ok), "checks": {"local_runtime": local["ok"], "manifest_url": url_ok, "version": bool(_VERSION_RE.match(VERSION))}}
