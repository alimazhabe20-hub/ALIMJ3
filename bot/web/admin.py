"""Minimal operator dashboard; protected by ADMIN_PANEL_TOKEN/METRICS_TOKEN."""
from __future__ import annotations
import hmac, os
from flask import Blueprint, jsonify, request, Response
from bot.services.v61_v65_platform import health_snapshot, features_snapshot
from bot.release import APP_NAME, VERSION

admin=Blueprint("v65_admin",__name__,url_prefix="/admin")

def _ok():
 token=(os.getenv("ADMIN_PANEL_TOKEN") or os.getenv("METRICS_TOKEN") or "").strip()
 if not token:return False
 supplied=(request.headers.get("X-Admin-Token") or request.args.get("token") or "").strip()
 return bool(supplied) and hmac.compare_digest(supplied,token)

@admin.get("")
def home():
 if not _ok(): return jsonify({"error":"unauthorized"}),401
 h=health_snapshot()
 html=f"""<!doctype html><html lang='en'><meta charset='utf-8'><title>{APP_NAME} {VERSION}</title><body><h1>{APP_NAME} v{VERSION}</h1><pre>{h}</pre><p>Free platform · Persian / English / Arabic</p></body></html>"""
 return Response(html,mimetype="text/html")

@admin.get("/health")
def health():
 if not _ok(): return jsonify({"error":"unauthorized"}),401
 return jsonify(health_snapshot())

@admin.get("/features")
def features():
 if not _ok(): return jsonify({"error":"unauthorized"}),401
 return jsonify(features_snapshot())
