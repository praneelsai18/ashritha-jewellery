"""Auth routes — /api/auth/*"""
import re
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import get_conn
from middleware.auth import make_token, login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
valid_email = lambda e: bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e))


def safe(row):
    d = dict(row); d.pop("password", None)
    d["is_admin"] = bool(d.get("is_admin", 0))
    return d


@bp.route("/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    fname = (d.get("fname") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    if not fname:                 return jsonify(error="First name required"), 400
    if not valid_email(email):    return jsonify(error="Invalid email"), 400
    if len(pw) < 6:               return jsonify(error="Password must be at least 6 characters"), 400
    conn = get_conn()
    if conn.execute("SELECT id FROM users WHERE email=%s", (email,)).fetchone():
        conn.close(); return jsonify(error="Account already exists"), 409
    cur = conn.execute(
        "INSERT INTO users (fname,lname,email,phone,password) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (fname, d.get("lname","").strip(), email,
         d.get("phone","").strip(), generate_password_hash(pw))
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
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    if not email or not pw: return jsonify(error="Email and password required"), 400
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email=%s", (email,)
    ).fetchone(); conn.close()
    if not row or not check_password_hash(row["password"], pw):
        return jsonify(error="Incorrect email or password"), 401
    return jsonify(token=make_token(row["id"], bool(row["is_admin"])), user=safe(row)), 200


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
        if len(d["new_password"]) < 6:
            conn.close(); return jsonify(error="Password too short"), 400
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
    if not fname or not valid_email(email) or len(pw) < 6:
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


@bp.route("/logout", methods=["POST"])
def logout():
    return jsonify(message="Logged out"), 200
