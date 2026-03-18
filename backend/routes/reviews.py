"""Reviews routes — /api/reviews  &  /api/admin/reviews"""
from flask import Blueprint, request, jsonify, g
from config.database import get_conn
from middleware.auth import admin_required, optional_auth

bp = Blueprint("reviews", __name__)


def fmt(row):
    d = dict(row)
    d["stars"] = "★" * d["rating"] + "☆" * (5 - d["rating"])
    return d


# ── PUBLIC: reviews for a product ────────────────────────────────────
@bp.route("/api/products/<int:pid>/reviews", methods=["GET"])
def product_reviews(pid):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM reviews WHERE product_id=%s AND status='approved' ORDER BY created_at DESC",
        (pid,)
    ).fetchall()
    # Aggregate
    total = len(rows)
    avg   = round(sum(r["rating"] for r in rows) / total, 1) if total else 0
    dist  = {i: sum(1 for r in rows if r["rating"]==i) for i in range(1,6)}
    conn.close()
    return jsonify(
        reviews=[fmt(r) for r in rows],
        total=total, avg=avg, distribution=dist
    ), 200


# ── PUBLIC: submit review ─────────────────────────────────────────────
@bp.route("/api/products/<int:pid>/reviews", methods=["POST"])
@optional_auth
def submit_review(pid):
    conn = get_conn()
    if not conn.execute("SELECT id FROM products WHERE id=%s AND is_active=1", (pid,)).fetchone():
        conn.close(); return jsonify(error="Product not found"), 404

    d    = request.get_json(silent=True) or {}
    name = (d.get("author_name") or "").strip()
    text = (d.get("review_text") or "").strip()
    try:
        rating = int(d.get("rating", 0))
        assert 1 <= rating <= 5
    except Exception:
        conn.close(); return jsonify(error="Rating must be 1–5"), 400
    if not name:         conn.close(); return jsonify(error="Name required"), 400
    if len(text) < 10:   conn.close(); return jsonify(error="Review must be at least 10 characters"), 400

    cur = conn.execute(
        "INSERT INTO reviews (product_id,user_id,author_name,rating,review_text,status) VALUES (%s,%s,%s,%s,%s,'pending')",
        (pid, g.user_id, name, rating, text)
    )
    rid = cur.lastrowid; conn.commit()
    row = conn.execute("SELECT * FROM reviews WHERE id=%s", (rid,)).fetchone(); conn.close()
    return jsonify(review=fmt(row), message="Review submitted — pending approval"), 201


# ── ADMIN: list all reviews ───────────────────────────────────────────
@bp.route("/api/admin/reviews", methods=["GET"])
@admin_required
def admin_reviews():
    status = request.args.get("status","")
    sql, args = """
        SELECT r.*, p.name AS product_name
        FROM reviews r
        LEFT JOIN products p ON p.id = r.product_id
    """, []
    if status in ("pending","approved","rejected"):
        sql += " WHERE r.status=%s"; args.append(status)
    sql += " ORDER BY CASE r.status WHEN 'pending' THEN 0 ELSE 1 END, r.created_at DESC"
    conn = get_conn(); rows = conn.execute(sql,args).fetchall(); conn.close()
    pending = sum(1 for r in rows if r["status"]=="pending")
    return jsonify(reviews=[fmt(r) for r in rows], total=len(rows), pending=pending), 200


# ── ADMIN: approve review ─────────────────────────────────────────────
@bp.route("/api/admin/reviews/<int:rid>/approve", methods=["PUT"])
@admin_required
def approve_review(rid):
    conn = get_conn()
    if not conn.execute("SELECT id FROM reviews WHERE id=%s", (rid,)).fetchone():
        conn.close(); return jsonify(error="Review not found"), 404
    conn.execute("UPDATE reviews SET status='approved' WHERE id=%s", (rid,)); conn.commit(); conn.close()
    return jsonify(message="Review approved and published"), 200


# ── ADMIN: delete review ──────────────────────────────────────────────
@bp.route("/api/admin/reviews/<int:rid>", methods=["DELETE"])
@admin_required
def delete_review(rid):
    conn = get_conn()
    if not conn.execute("SELECT id FROM reviews WHERE id=%s", (rid,)).fetchone():
        conn.close(); return jsonify(error="Review not found"), 404
    conn.execute("DELETE FROM reviews WHERE id=%s", (rid,)); conn.commit(); conn.close()
    return jsonify(message="Review deleted"), 200
