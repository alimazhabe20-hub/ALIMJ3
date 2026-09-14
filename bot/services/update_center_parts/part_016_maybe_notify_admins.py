from typing import Any

# Auto-split part 16: maybe_notify_admins
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
