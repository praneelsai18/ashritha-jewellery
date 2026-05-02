"""JWT auth middleware — Ashritha Jewellers"""
import os, time, jwt
from functools import wraps
from flask import request, jsonify, g
from config.database import get_conn

SECRET  = os.environ.get("JWT_SECRET", "ashritha_jwt_secret_CHANGE_IN_PROD_2025")
EXPIRES = 60 * 60 * 24 * 7   # 7 days
IS_PROD = os.environ.get("FLASK_ENV", "development") == "production"

if IS_PROD and SECRET == "ashritha_jwt_secret_CHANGE_IN_PROD_2025":
    raise RuntimeError("JWT_SECRET must be set in production")


def make_token(user_id, is_admin):
    return jwt.encode(
        {"user_id": user_id, "is_admin": is_admin,
         "iat": int(time.time()), "exp": int(time.time()) + EXPIRES},
        SECRET, algorithm="HS256"
    )


def _token():
    h = request.headers.get("Authorization", "")
    return h[7:] if h.startswith("Bearer ") else request.cookies.get("aj_token")


def _load_user(payload):
    conn = get_conn()
    row = conn.execute(
        "SELECT id,fname,lname,email,phone,address,is_admin FROM users WHERE id=%s",
        (payload["user_id"],)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        tok = _token()
        if not tok:
            return jsonify(error="Authentication required"), 401
        try:
            payload = jwt.decode(tok, SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify(error="Session expired — please sign in again"), 401
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid token"), 401
        user = _load_user(payload)
        if not user:
            return jsonify(error="User not found"), 401
        g.user = user; g.user_id = user["id"]; g.is_admin = bool(user["is_admin"])
        return f(*a, **kw)
    return wrap


def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        tok = _token()
        if not tok:
            return jsonify(error="Authentication required"), 401
        try:
            payload = jwt.decode(tok, SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify(error="Session expired — please sign in again"), 401
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid token"), 401
        if not payload.get("is_admin"):
            return jsonify(error="Admin access required"), 403
        conn = get_conn()
        row = conn.execute(
            "SELECT id,fname,email,is_admin FROM users WHERE id=%s AND is_admin=1",
            (payload["user_id"],)
        ).fetchone()
        conn.close()
        if not row:
            return jsonify(error="Admin not found"), 403
        g.user = dict(row); g.user_id = row["id"]; g.is_admin = True
        return f(*a, **kw)
    return wrap


def optional_auth(f):
    @wraps(f)
    def wrap(*a, **kw):
        g.user = None; g.user_id = None; g.is_admin = False
        tok = _token()
        if tok:
            try:
                payload = jwt.decode(tok, SECRET, algorithms=["HS256"])
                user = _load_user(payload)
                if user:
                    g.user = user; g.user_id = user["id"]
                    g.is_admin = bool(user["is_admin"])
            except Exception:
                pass
        return f(*a, **kw)
    return wrap
