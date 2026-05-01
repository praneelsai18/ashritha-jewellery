"""
Auth routes: /api/auth/register  POST
             /api/auth/login     POST
             /api/auth/me        GET   (login_required)
             /api/auth/profile   PUT   (login_required)
             /api/auth/logout    POST
"""
import re
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import get_conn
from middleware.auth import create_token, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


# ── REGISTER ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data  = request.get_json(silent=True) or {}
    fname = (data.get("fname") or "").strip()
    email = (data.get("email") or "").strip().lower()
    pw    = data.get("password") or ""

    if not fname:
        return jsonify({"error": "First name is required"}), 400
    if not _valid_email(email):
        return jsonify({"error": "Invalid email address"}), 400
    if len(pw) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "An account with this email already exists"}), 409

    cursor = conn.execute(
        "INSERT INTO users (fname, lname, email, phone, password) VALUES (?, ?, ?, ?, ?)",
        (fname, data.get("lname", "").strip(), email,
         data.get("phone", "").strip(), generate_password_hash(pw))
    )
    user_id = cursor.lastrowid
    conn.commit()

    user = conn.execute(
        "SELECT id, fname, lname, email, phone, address, is_admin FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    token = create_token(user_id, bool(user["is_admin"]))
    return jsonify({"token": token, "user": _safe_user(user)}), 201


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pw    = data.get("password") or ""

    if not email or not pw:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_conn()
    user = conn.execute(
        "SELECT id, fname, lname, email, phone, address, password, is_admin FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password"], pw):
        return jsonify({"error": "Incorrect email or password"}), 401

    token = create_token(user["id"], bool(user["is_admin"]))
    return jsonify({"token": token, "user": _safe_user(user)}), 200


# ── ME ────────────────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": g.user}), 200


# ── UPDATE PROFILE ────────────────────────────────────────────────────────────
@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    data    = request.get_json(silent=True) or {}
    fname   = (data.get("fname") or "").strip()
    lname   = (data.get("lname") or "").strip()
    phone   = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()

    if not fname:
        return jsonify({"error": "First name is required"}), 400

    conn = get_conn()
    conn.execute(
        "UPDATE users SET fname=?, lname=?, phone=?, address=?, updated_at=datetime('now') WHERE id=?",
        (fname, lname, phone, address, g.user_id)
    )

    # Optional password change
    new_pw = data.get("new_password")
    if new_pw:
        if len(new_pw) < 6:
            conn.close()
            return jsonify({"error": "New password must be at least 6 characters"}), 400
        conn.execute(
            "UPDATE users SET password=? WHERE id=?",
            (generate_password_hash(new_pw), g.user_id)
        )

    conn.commit()
    user = conn.execute(
        "SELECT id, fname, lname, email, phone, address, is_admin FROM users WHERE id = ?",
        (g.user_id,)
    ).fetchone()
    conn.close()
    return jsonify({"user": _safe_user(user)}), 200


# ── LOGOUT ────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
def logout():
    # JWT is stateless; client clears the token. We just confirm.
    return jsonify({"message": "Logged out successfully"}), 200


# ── HELPER ────────────────────────────────────────────────────────────────────
def _safe_user(user):
    """Return user dict without password."""
    d = dict(user)
    d.pop("password", None)
    d["is_admin"] = bool(d.get("is_admin", 0))
    return d
