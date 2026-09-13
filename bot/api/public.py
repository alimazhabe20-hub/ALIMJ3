"""Read-only public API for V65. No secrets, payments or subscriptions."""
from __future__ import annotations
import hmac, os
from flask import Blueprint, jsonify, request
from bot.release import APP_NAME, VERSION
from bot.services.v61_v65_platform import features_snapshot, health_snapshot, get_watchlist, get_alerts

api = Blueprint("v65_api", __name__, url_prefix="/api/v1")

def _auth():
    token=(os.getenv("PUBLIC_API_TOKEN","") or "").strip()
    if not token:return True
    supplied=(request.headers.get("X-API-Key","") or "").strip()
    if not supplied:
        auth=request.headers.get("Authorization","")
        supplied=auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    return bool(supplied) and hmac.compare_digest(supplied,token)

def _guard():
    if not _auth(): return jsonify({"error":"unauthorized"}),401
    return None

@api.get("/health")
def health():
    g=_guard()
    if g:return g
    return jsonify({"status":"ok","app":APP_NAME,"version":VERSION,"platform":health_snapshot()})

@api.get("/features")
def features():
    g=_guard()
    if g:return g
    return jsonify(features_snapshot())

@api.get("/stats")
def stats():
    g=_guard()
    if g:return g
    try:
        from bot.database import get_db_connection
        conn=get_db_connection()
        total=conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active=conn.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')").fetchone()[0]
        conn.close()
    except Exception: total=active=None
    return jsonify({"total_users":total,"active_today":active,"free":True,"payments":False})

@api.get("/watchlist")
def watchlist():
    g=_guard()
    if g:return g
    uid=int(request.args.get("user_id","0") or 0)
    if not uid:return jsonify({"error":"user_id required"}),400
    return jsonify({"items":[{"symbol":s,"label":l} for s,l in get_watchlist(uid)]})

@api.get("/alerts")
def alerts():
    g=_guard()
    if g:return g
    uid=int(request.args.get("user_id","0") or 0)
    if not uid:return jsonify({"error":"user_id required"}),400
    return jsonify({"items":[{"id":r[0],"symbol":r[1],"target":r[2],"direction":r[3],"active":bool(r[4])} for r in get_alerts(uid,False)]})
