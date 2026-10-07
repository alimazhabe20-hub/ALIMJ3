"""Protected V74 observability dashboard."""
from __future__ import annotations
import hmac, os
from flask import Blueprint, jsonify, Response, request

v74_admin = Blueprint("v74_admin", __name__, url_prefix="/admin/v74")


def _ok() -> bool:
    token=(os.getenv("ADMIN_PANEL_TOKEN") or os.getenv("METRICS_TOKEN") or "").strip()
    supplied=(request.headers.get("X-Admin-Token") or request.args.get("token") or "").strip()
    return bool(token and supplied) and hmac.compare_digest(supplied, token)


@v74_admin.get("")
def dashboard():
    if not _ok(): return jsonify({"error":"unauthorized"}), 401
    from bot.services.v74_platform import admin_dashboard_data
    data=admin_dashboard_data()
    return Response("<!doctype html><meta charset='utf-8'><title>ALIMJ3 V74</title><body><h1>ALIMJ3 V74</h1><pre>" + str(data) + "</pre></body>", mimetype="text/html")


@v74_admin.get("/json")
def dashboard_json():
    if not _ok(): return jsonify({"error":"unauthorized"}), 401
    from bot.services.v74_platform import admin_dashboard_data
    return jsonify(admin_dashboard_data())
