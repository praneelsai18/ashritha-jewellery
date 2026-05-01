"""
JWT Authentication middleware for Ashritha Jewellers backend.
"""
import os
import jwt
from functools import wraps
from flask import request, jsonify, g
from config.database import get_conn

JWT_SECRET  = os.environ.get("JWT_SECRET", "ashritha_jwt_secret_change_in_prod_2025")
JWT_EXPIRES = 60 * 60 * 24 * 7   # 7 days in seconds


def create_token(user_id: int, is_admin: bool) -> str:
    import time
    payload = {
        "user_id":  user_id,
        "is_admin": is_admin,
        "iat":      int(time.time()),
        "exp":      int(time.time()) + JWT_EXPIRES,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


def _extract_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("aj_token")


def login_required(f):
    """Decorator — requires any valid token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired, please sign in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_conn()
        user = conn.execute(
            "SELECT id, fname, lname, email, phone, address, is_admin FROM users WHERE id = ?",
            (payload["user_id"],)
        ).fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "User not found"}), 401

        g.user    = dict(user)
        g.user_id = user["id"]
        g.is_admin = bool(user["is_admin"])
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator — requires admin token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            payload = decode_token(token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            return jsonify({"error": str(e)}), 401

        if not payload.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403

        conn = get_conn()
        user = conn.execute(
            "SELECT id, fname, email, is_admin FROM users WHERE id = ? AND is_admin = 1",
            (payload["user_id"],)
        ).fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "Admin not found"}), 403

        g.user    = dict(user)
        g.user_id = user["id"]
        g.is_admin = True
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """Decorator — attaches user to g if token present, continues regardless."""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user    = None
        g.user_id = None
        g.is_admin = False
        token = _extract_token()
        if token:
            try:
                payload = decode_token(token)
                conn = get_conn()
                user = conn.execute(
                    "SELECT id, fname, lname, email, phone, address, is_admin FROM users WHERE id = ?",
                    (payload["user_id"],)
                ).fetchone()
                conn.close()
                if user:
                    g.user    = dict(user)
                    g.user_id = user["id"]
                    g.is_admin = bool(user["is_admin"])
            except Exception:
                pass
        return f(*args, **kwargs)
    return decorated
