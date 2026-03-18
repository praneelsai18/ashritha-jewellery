"""Settings routes"""
from flask import Blueprint, request, jsonify
from config.database import get_conn
from middleware.auth import admin_required

bp = Blueprint("settings", __name__)

ALLOWED = {"wa_number","upi_id","ann_text","free_shipping","shipping_charge","store_name"}


@bp.route("/api/settings/public", methods=["GET"])
def public_settings():
    conn = get_conn()
    rows = conn.execute("SELECT key,value FROM settings").fetchall()
    conn.close()
    return jsonify(settings={r["key"]: r["value"] for r in rows}), 200


@bp.route("/api/admin/settings", methods=["GET"])
@admin_required
def get_settings():
    conn = get_conn(); rows = conn.execute("SELECT key,value FROM settings").fetchall(); conn.close()
    return jsonify(settings={r["key"]: r["value"] for r in rows}), 200


@bp.route("/api/admin/settings", methods=["PUT"])
@admin_required
def update_settings():
    d = request.get_json(silent=True) or {}
    updates = {k: str(v).strip() for k, v in d.items() if k in ALLOWED}
    if not updates: return jsonify(error="No valid keys"), 400
    conn = get_conn()
    for k, v in updates.items():
        conn.execute(
            "INSERT INTO settings (key,value) VALUES (%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, v)
        )
    conn.commit()
    rows = conn.execute("SELECT key,value FROM settings").fetchall(); conn.close()
    return jsonify(settings={r["key"]: r["value"] for r in rows}, message="Settings saved"), 200
