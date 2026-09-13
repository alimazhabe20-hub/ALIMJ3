"""Protected V77 Ultimate operator dashboard."""
from __future__ import annotations
import hmac, os
from flask import Blueprint, jsonify, Response, request

v77_admin = Blueprint("v77_admin", __name__, url_prefix="/admin/v77")

def _ok() -> bool:
    token=(os.getenv("ADMIN_PANEL_TOKEN") or os.getenv("METRICS_TOKEN") or "").strip()
    supplied=(request.headers.get("X-Admin-Token") or request.args.get("token") or "").strip()
    return bool(token and supplied) and hmac.compare_digest(supplied, token)

@v77_admin.get("")
def dashboard():
    if not _ok(): return jsonify({"error":"unauthorized"}), 401
    from bot.services.v77_platform import admin_snapshot
    data=admin_snapshot(".")
    return Response("<!doctype html><meta charset='utf-8'><title>ALIMJ3 V77</title><body><h1>ALIMJ3 V77 Ultimate</h1><pre>" + str(data) + "</pre></body>", mimetype="text/html")

@v77_admin.get("/json")
def dashboard_json():
    if not _ok(): return jsonify({"error":"unauthorized"}), 401
    from bot.services.v77_platform import admin_snapshot
    return jsonify(admin_snapshot("."))
