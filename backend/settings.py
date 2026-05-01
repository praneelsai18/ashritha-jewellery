"""
Settings routes:
  GET /api/admin/settings        – get all settings (admin)
  PUT /api/admin/settings        – update settings (admin)
  GET /api/settings/public       – get public settings (store uses these)
"""
from flask import Blueprint, request, jsonify
from config.database import get_conn
from middleware.auth import admin_required

settings_bp = Blueprint("settings", __name__)

PUBLIC_KEYS = {"ann_text", "free_shipping", "shipping_charge", "store_name"}


# ── PUBLIC SETTINGS ───────────────────────────────────────────────────────────
@settings_bp.route("/api/settings/public", methods=["GET"])
def public_settings():
    conn = get_conn()
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key IN ('ann_text','free_shipping','shipping_charge','store_name','wa_number')"
    ).fetchall()
    conn.close()
    return jsonify({"settings": {r["key"]: r["value"] for r in rows}}), 200


# ── ADMIN: GET ALL ────────────────────────────────────────────────────────────
@settings_bp.route("/api/admin/settings", methods=["GET"])
@admin_required
def get_settings():
    conn  = get_conn()
    rows  = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return jsonify({"settings": {r["key"]: r["value"] for r in rows}}), 200


# ── ADMIN: UPDATE ─────────────────────────────────────────────────────────────
@settings_bp.route("/api/admin/settings", methods=["PUT"])
@admin_required
def update_settings():
    data = request.get_json(silent=True) or {}

    ALLOWED_KEYS = {
        "wa_number", "upi_id", "ann_text",
        "free_shipping", "shipping_charge", "store_name"
    }

    updates = {}
    for key, val in data.items():
        if key in ALLOWED_KEYS:
            updates[key] = str(val).strip()

    if not updates:
        return jsonify({"error": "No valid settings provided"}), 400

    conn = get_conn()
    for key, val in updates.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, val)
        )
    conn.commit()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()

    return jsonify({
        "message":  "Settings saved",
        "settings": {r["key"]: r["value"] for r in rows}
    }), 200
