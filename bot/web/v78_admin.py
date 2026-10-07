"""Protected V78 Update Center operator endpoints.

Authentication is deliberately token-only. Telegram ADMIN_IDS cannot be used as
HTTP authentication because an HTTP request does not prove Telegram identity.
"""
from flask import Blueprint, Response, request
import hmac
import os

v78_admin = Blueprint("v78_admin", __name__, url_prefix="/admin/v78")

def _authorized() -> bool:
    expected = (os.getenv("ADMIN_PANEL_TOKEN") or os.getenv("METRICS_TOKEN") or "").strip()
    supplied = (request.headers.get("X-Admin-Token") or request.headers.get("X-Metrics-Token") or "").strip()
    return bool(expected and supplied and hmac.compare_digest(supplied, expected))

@v78_admin.get("/updates")
def updates():
    if not _authorized():
        return {"error": "unauthorized"}, 401
    from bot.services.update_center import check_for_updates
    return check_for_updates(force=True)

@v78_admin.get("/updates/json")
def updates_json():
    if not _authorized():
        return {"error": "unauthorized"}, 401
    from bot.services.update_center import check_for_updates
    import json
    return Response(json.dumps(check_for_updates(force=True), ensure_ascii=False, indent=2), mimetype="application/json")
