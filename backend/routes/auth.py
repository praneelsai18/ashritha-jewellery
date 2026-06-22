"""Auth routes — /api/auth/*"""
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import get_conn
from middleware.auth import make_token, login_required
from services.email import send_password_reset_email

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
valid_email = lambda e: bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e))
PHONE_DIGITS = re.compile(r"\D")
PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")
LOGIN_ATTEMPTS = {}
RESET_REQUESTS = {}
MAX_FAILS = 7
LOCK_SECS = 10 * 60
RESET_TOKEN_MINS = 15
RESET_MAX_PER_EMAIL = 3
RESET_WINDOW_SECS = 60 * 60


def safe(row):
    d = dict(row); d.pop("password", None)
    d["is_admin"] = bool(d.get("is_admin", 0))
    return d


def _valid_password(pw):
    return bool(PASSWORD_RE.match(pw or ""))


def _ip():
    xfwd = request.headers.get("X-Forwarded-For", "")
    return xfwd.split(",")[0].strip() if xfwd else (request.remote_addr or "unknown")


def _attempt_key(identifier):
    key = (identifier or "").strip().lower()
    if not valid_email(key):
        digits = PHONE_DIGITS.sub("", key)
        key = digits[-10:] if len(digits) >= 10 else digits
    return f"{key}::{_ip()}"


def _find_user_by_login(identifier):
    identifier = (identifier or "").strip()
    conn = get_conn()
    if valid_email(identifier):
        row = conn.execute(
            "SELECT * FROM users WHERE email=%s", (identifier.lower(),)
        ).fetchone()
    else:
        phone = PHONE_DIGITS.sub("", identifier)
        if len(phone) < 10:
            conn.close()
            return None
        row = conn.execute(
            "SELECT * FROM users WHERE phone=%s OR RIGHT(phone, 10)=%s",
            (phone, phone[-10:]),
        ).fetchone()
    conn.close()
    return row


@bp.route("/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    fname = (d.get("fname") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    if not fname:                 return jsonify(error="First name required"), 400
    if not valid_email(email):    return jsonify(error="Invalid email"), 400
    if not _valid_password(pw):
        return jsonify(error="Password must be 8+ chars and include letters + numbers"), 400
    phone = PHONE_DIGITS.sub("", d.get("phone",""))
    if phone and len(phone) < 10:
        return jsonify(error="Enter a valid phone number"), 400
    conn = get_conn()
    if conn.execute("SELECT id FROM users WHERE email=%s", (email,)).fetchone():
        conn.close(); return jsonify(error="Account already exists"), 409
    cur = conn.execute(
        "INSERT INTO users (fname,lname,email,phone,password) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (fname, d.get("lname","").strip(), email,
         phone, generate_password_hash(pw))
    )
    res = cur.fetchone()
    uid = res["id"] if (res and isinstance(res, dict)) else (res[0] if res else None)
    conn.commit()
    row = conn.execute(
        "SELECT id,fname,lname,email,phone,address,is_admin FROM users WHERE id=%s", (uid,)
    ).fetchone(); conn.close()
    return jsonify(token=make_token(uid, False), user=safe(row)), 201


@bp.route("/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    identifier = (d.get("email") or "").strip()
    pw    = d.get("password") or ""
    if not identifier or not pw:
        return jsonify(error="Email/phone and password required"), 400
    if not valid_email(identifier) and len(PHONE_DIGITS.sub("", identifier)) < 10:
        return jsonify(error="Enter a valid email or phone number"), 400
    key = _attempt_key(identifier)
    now = int(time.time())
    hist = LOGIN_ATTEMPTS.get(key, {"count": 0, "lock_until": 0})
    if hist.get("lock_until", 0) > now:
        return jsonify(error="Too many failed attempts. Try again later."), 429

    row = _find_user_by_login(identifier)
    if not row or not check_password_hash(row["password"], pw):
        hist["count"] = hist.get("count", 0) + 1
        if hist["count"] >= MAX_FAILS:
            hist["lock_until"] = now + LOCK_SECS
            hist["count"] = 0
        LOGIN_ATTEMPTS[key] = hist
        return jsonify(error="Incorrect email/phone or password"), 401
    LOGIN_ATTEMPTS.pop(key, None)
    return jsonify(token=make_token(row["id"], bool(row["is_admin"])), user=safe(row)), 200


@bp.route("/google", methods=["POST"])
def google_login():
    d = request.get_json(silent=True) or {}
    id_token = (d.get("id_token") or "").strip()
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not id_token:
        return jsonify(error="Google token is required"), 400
    if not client_id:
        return jsonify(error="Google login is not configured on server"), 503
    try:
        from google.oauth2 import id_token as gid_token
        from google.auth.transport import requests as grequests
    except Exception:
        return jsonify(error="Google auth dependency missing on server"), 500

    try:
        payload = gid_token.verify_oauth2_token(id_token, grequests.Request(), client_id)
    except Exception:
        return jsonify(error="Invalid Google token"), 401

    email = (payload.get("email") or "").strip().lower()
    full_name = (payload.get("name") or "").strip()
    given_name = (payload.get("given_name") or "").strip()
    family_name = (payload.get("family_name") or "").strip()
    if not email:
        return jsonify(error="Google account email not available"), 400

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=%s", (email,)).fetchone()
    if not row:
        fname = given_name or (full_name.split(" ")[0] if full_name else "Google User")
        lname = family_name or (" ".join(full_name.split(" ")[1:]) if full_name else "")
        cur = conn.execute(
            "INSERT INTO users (fname,lname,email,password,phone) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (fname, lname, email, generate_password_hash(secrets.token_urlsafe(24)), "")
        )
        res = cur.fetchone()
        uid = res["id"] if (res and isinstance(res, dict)) else (res[0] if res else None)
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id=%s", (uid,)).fetchone()
    conn.close()
    return jsonify(token=make_token(row["id"], bool(row["is_admin"])), user=safe(row)), 200


def _utcnow():
    return datetime.now(timezone.utc)


def _reset_link_base():
    base = (os.environ.get("FRONTEND_URL", "") or "").strip().rstrip("/")
    if not base:
        base = request.host_url.rstrip("/")
    return base


def _can_request_reset(email):
    now = int(time.time())
    key = email.lower()
    hist = [ts for ts in RESET_REQUESTS.get(key, []) if now - ts <= RESET_WINDOW_SECS]
    RESET_REQUESTS[key] = hist
    return len(hist) < RESET_MAX_PER_EMAIL


def _record_reset_request(email):
    key = email.lower()
    RESET_REQUESTS.setdefault(key, []).append(int(time.time()))


@bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    if not valid_email(email):
        return jsonify(error="Enter a valid email"), 400

    generic = {"message": "If an account exists for that email, we sent a password reset link."}

    if not _can_request_reset(email):
        return jsonify(generic), 200

    conn = get_conn()
    row = conn.execute("SELECT id FROM users WHERE email=%s", (email,)).fetchone()
    if not row:
        conn.close()
        return jsonify(generic), 200

    raw_token = secrets.token_urlsafe(32)
    token_hash = generate_password_hash(raw_token)
    expires_at = _utcnow() + timedelta(minutes=RESET_TOKEN_MINS)

    conn.execute(
        "UPDATE password_reset_tokens SET used=1 WHERE user_id=%s AND used=0",
        (row["id"],),
    )
    conn.execute(
        """INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
           VALUES (%s, %s, %s)""",
        (row["id"], token_hash, expires_at),
    )
    conn.commit()
    conn.close()

    reset_url = f"{_reset_link_base()}/?reset_token={raw_token}"
    ok, err = send_password_reset_email(email, reset_url)
    if ok:
        _record_reset_request(email)
    elif os.environ.get("FLASK_ENV", "development") != "production":
        print(f"[dev] Password reset link for {email}: {reset_url}")
        if err:
            print(f"[dev] Brevo email failed: {err}")
        _record_reset_request(email)
    elif err:
        print(f"[password-reset] Email not sent for {email}: {err}")

    return jsonify(generic), 200


@bp.route("/reset-password", methods=["POST"])
def reset_password():
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    new_pw = d.get("new_password") or ""
    if not token:
        return jsonify(error="Reset link is invalid or expired"), 400
    if not _valid_password(new_pw):
        return jsonify(error="Password must be 8+ chars and include letters + numbers"), 400

    conn = get_conn()
    rows = conn.execute(
        """SELECT prt.id, prt.user_id, prt.token_hash, prt.expires_at, prt.used
           FROM password_reset_tokens prt
           WHERE prt.used=0
           ORDER BY prt.created_at DESC
           LIMIT 50"""
    ).fetchall()

    match = None
    for row in rows:
        expires = row["expires_at"]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < _utcnow():
            continue
        if check_password_hash(row["token_hash"], token):
            match = row
            break

    if not match:
        conn.close()
        return jsonify(error="Reset link is invalid or expired"), 400

    conn.execute(
        "UPDATE users SET password=%s WHERE id=%s",
        (generate_password_hash(new_pw), match["user_id"]),
    )
    conn.execute(
        "UPDATE password_reset_tokens SET used=1 WHERE id=%s",
        (match["id"],),
    )
    conn.commit()
    conn.close()
    return jsonify(message="Password reset successful. Please sign in."), 200


@bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify(user=g.user), 200


@bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    d = request.get_json(silent=True) or {}
    fname = (d.get("fname") or "").strip()
    if not fname: return jsonify(error="First name required"), 400
    conn = get_conn()
    
    new_email = (d.get("email") or "").strip().lower()
    if new_email and new_email != g.user["email"]:
        if not valid_email(new_email):
            conn.close(); return jsonify(error="Invalid email"), 400
        if conn.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (new_email, g.user_id)).fetchone():
            conn.close(); return jsonify(error="Email already exists"), 409
        conn.execute("UPDATE users SET email=%s WHERE id=%s", (new_email, g.user_id))

    conn.execute(
        "UPDATE users SET fname=%s,lname=%s,phone=%s,address=%s WHERE id=%s",
        (fname, d.get("lname","").strip(), d.get("phone","").strip(),
         d.get("address","").strip(), g.user_id)
    )
    if d.get("new_password"):
        if not _valid_password(d["new_password"]):
            conn.close(); return jsonify(error="Password must be 8+ chars and include letters + numbers"), 400
        conn.execute("UPDATE users SET password=%s WHERE id=%s",
                     (generate_password_hash(d["new_password"]), g.user_id))
    conn.commit()
    row = conn.execute(
        "SELECT id,fname,lname,email,phone,address,is_admin FROM users WHERE id=%s",
        (g.user_id,)
    ).fetchone(); conn.close()
    return jsonify(user=safe(row)), 200

@bp.route("/admins", methods=["GET"])
@login_required
def get_admins():
    if not g.user["is_admin"]: return jsonify(error="Forbidden"), 403
    conn = get_conn()
    rows = conn.execute("SELECT id,fname,lname,email,phone,address,is_admin FROM users WHERE is_admin=1").fetchall()
    conn.close()
    return jsonify(admins=[safe(r) for r in rows]), 200

@bp.route("/admin", methods=["POST"])
@login_required
def create_admin():
    if not g.user["is_admin"]: return jsonify(error="Forbidden"), 403
    d = request.get_json(silent=True) or {}
    fname = (d.get("fname") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw = d.get("password") or ""
    if not fname or not valid_email(email) or not _valid_password(pw):
        return jsonify(error="Invalid data"), 400
    conn = get_conn()
    if conn.execute("SELECT id FROM users WHERE email=%s", (email,)).fetchone():
        conn.close(); return jsonify(error="Email already exists"), 409
    conn.execute(
        "INSERT INTO users (fname,email,password,is_admin) VALUES (%s,%s,%s,1)",
        (fname, email, generate_password_hash(pw))
    )
    conn.commit(); conn.close()
    return jsonify(message="Admin created"), 201

@bp.route("/admin/<email>", methods=["DELETE"])
@login_required
def delete_admin(email):
    if not g.user["is_admin"]: return jsonify(error="Forbidden"), 403
    email = email.lower()
    if email == g.user["email"]: return jsonify(error="Cannot delete yourself"), 400
    if email == "admin@ashrithajewellery.com": return jsonify(error="Cannot delete primary admin"), 400
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE email=%s AND is_admin=1", (email,))
    conn.commit(); conn.close()
    return jsonify(message="Admin deleted"), 200


@bp.route("/cart", methods=["GET"])
@login_required
def get_cart():
    conn = get_conn()
    row = conn.execute("SELECT cart_data FROM users WHERE id=%s", (g.user_id,)).fetchone()
    conn.close()
    return jsonify(cart=row["cart_data"] if row and row.get("cart_data") else "[]"), 200

@bp.route("/cart", methods=["PUT"])
@login_required
def update_cart():
    d = request.get_json(silent=True) or {}
    cart_data = d.get("cart_data", "[]")
    conn = get_conn()
    conn.execute("UPDATE users SET cart_data=%s WHERE id=%s", (cart_data, g.user_id))
    conn.commit()
    conn.close()
    return jsonify(message="Cart updated"), 200

@bp.route("/logout", methods=["POST"])
def logout():
    return jsonify(message="Logged out"), 200
