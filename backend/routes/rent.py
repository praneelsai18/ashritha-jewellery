"""Rent routes — /api/rent  &  /api/admin/rent"""
from datetime import datetime
import re
from flask import Blueprint, request, jsonify, g
from config.database import get_conn
from middleware.auth import admin_required, optional_auth, login_required

bp = Blueprint("rent", __name__)

STATUSES = {"pending","confirmed","active","returned","cancelled"}
PHONE_DIGITS = re.compile(r"\D")


# ── Submit rent request ───────────────────────────────────────────────
@bp.route("/api/rent", methods=["POST"])
@optional_auth
def submit_rent():
    d = request.get_json(silent=True) or {}
    required = ["product_id","customer_name","customer_phone","address","start_date","end_date"]
    missing = [f for f in required if not d.get(f)]
    if missing: return jsonify(error=f"Missing: {', '.join(missing)}"), 400

    pid = int(d["product_id"])
    customer_phone = PHONE_DIGITS.sub("", d.get("customer_phone", ""))
    if len(customer_phone) < 10:
        return jsonify(error="Enter a valid mobile number"), 400

    conn = get_conn()
    p = conn.execute(
        "SELECT * FROM products WHERE id=%s AND is_active=1 AND rent_enabled=1", (pid,)
    ).fetchone()
    if not p: conn.close(); return jsonify(error="Product not available for rent"), 404

    try:
        start = datetime.strptime(d["start_date"], "%Y-%m-%d")
        end   = datetime.strptime(d["end_date"],   "%Y-%m-%d")
        days  = (end - start).days
        assert days > 0
    except Exception:
        conn.close(); return jsonify(error="Invalid dates — end must be after start"), 400

    if days > p["max_days"]:
        conn.close()
        return jsonify(error=f"Max rental period is {p['max_days']} days"), 400

    rent_total = days * p["rent_price"]
    deposit    = p["deposit"]
    grand      = rent_total + deposit

    cur = conn.execute(
        """INSERT INTO rent_requests
           (product_id,user_id,customer_name,customer_phone,address,
            start_date,end_date,days,rent_total,deposit,grand_total)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (pid, g.user_id,
         d["customer_name"].strip(), customer_phone,
         d["address"].strip(), d["start_date"], d["end_date"],
         days, rent_total, deposit, grand)
    )
    res = cur.fetchone()
    rid = res["id"] if (res and isinstance(res, dict)) else (res[0] if res else None)
    conn.commit()
    row = conn.execute("SELECT * FROM rent_requests WHERE id=%s", (rid,)).fetchone()
    conn.close()
    return jsonify(
        rent_request=dict(row),
        summary={
            "product": p["name"],
            "days": days, "rent_total": rent_total,
            "deposit": deposit, "grand_total": grand
        },
        message="Rental request submitted"
    ), 201


# ── My rent requests ──────────────────────────────────────────────────
@bp.route("/api/rent/my", methods=["GET"])
@login_required
def my_rent():
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.*, p.name AS product_name, p.image_url
           FROM rent_requests r LEFT JOIN products p ON p.id=r.product_id
           WHERE r.user_id=%s ORDER BY r.created_at DESC""",
        (g.user_id,)
    ).fetchall(); conn.close()
    return jsonify(rent_requests=[dict(r) for r in rows]), 200


# ── ADMIN: list all ───────────────────────────────────────────────────
@bp.route("/api/admin/rent", methods=["GET"])
@admin_required
def admin_rent():
    status = request.args.get("status","")
    sql = """SELECT r.*, p.name AS product_name
             FROM rent_requests r LEFT JOIN products p ON p.id=r.product_id"""
    args = []
    if status and status in STATUSES:
        sql += " WHERE r.status=%s"; args.append(status)
    sql += " ORDER BY r.created_at DESC"
    conn = get_conn(); rows = conn.execute(sql,args).fetchall(); conn.close()
    return jsonify(rent_requests=[dict(r) for r in rows], total=len(rows)), 200


# ── ADMIN: update status ──────────────────────────────────────────────
@bp.route("/api/admin/rent/<int:rid>/status", methods=["PUT"])
@admin_required
def update_rent_status(rid):
    d = request.get_json(silent=True) or {}
    status = (d.get("status") or "").strip()
    if status not in STATUSES: return jsonify(error=f"Must be one of {STATUSES}"), 400
    conn = get_conn()
    if not conn.execute("SELECT id FROM rent_requests WHERE id=%s", (rid,)).fetchone():
        conn.close(); return jsonify(error="Not found"), 404
    conn.execute("UPDATE rent_requests SET status=%s WHERE id=%s", (status,rid))
    conn.commit(); conn.close()
    return jsonify(status=status, message=f"Rent request → {status}"), 200
