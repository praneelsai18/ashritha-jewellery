"""Orders routes — /api/orders  &  /api/admin/orders"""
import time
from flask import Blueprint, request, jsonify, g
from config.database import get_conn
from middleware.auth import login_required, admin_required, optional_auth

bp = Blueprint("orders", __name__)
STATUSES = {"pending","confirmed","shipped","delivered","cancelled"}


def calc_shipping(subtotal, conn):
    rows = {r["key"]: r["value"] for r in conn.execute(
        "SELECT key,value FROM settings WHERE key IN ('free_shipping','shipping_charge')"
    ).fetchall()}
    free = float(rows.get("free_shipping", 499))
    charge = float(rows.get("shipping_charge", 50))
    return 0.0 if subtotal >= free else charge


# ── Place order ───────────────────────────────────────────────────────
@bp.route("/api/orders", methods=["POST"])
@optional_auth
def place_order():
    d = request.get_json(silent=True) or {}
    required = ["customer_name","customer_phone","address","city","pin_code","items"]
    missing  = [f for f in required if not d.get(f)]
    if missing: return jsonify(error=f"Missing: {', '.join(missing)}"), 400

    items = d["items"]
    if not items: return jsonify(error="Order needs at least one item"), 400

    conn = get_conn()
    order_items, subtotal = [], 0.0

    for item in items:
        pid = item.get("product_id")
        qty = max(1, int(item.get("qty", 1)))
        p = conn.execute(
            "SELECT id,name,price,stock,is_active FROM products WHERE id=%s", (pid,)
        ).fetchone()
        if not p:           conn.close(); return jsonify(error=f"Product #{pid} not found"), 404
        if not p["is_active"]: conn.close(); return jsonify(error=f"'{p['name']}' unavailable"), 400
        if p["stock"] < qty:
            conn.close()
            return jsonify(error=f"Only {p['stock']} of '{p['name']}' available", available=p["stock"]), 400
        order_items.append(dict(p) | {"qty": qty})
        subtotal += p["price"] * qty

    ship  = calc_shipping(subtotal, conn)
    total = subtotal + ship
    ref   = "AJ" + str(int(time.time()))[-6:]

    cur = conn.execute(
        """INSERT INTO orders
           (order_ref,user_id,customer_name,customer_phone,address,city,state,pin_code,notes,subtotal,shipping,total)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (ref, g.user_id,
         d["customer_name"].strip(), d["customer_phone"].strip(),
         d["address"].strip(), d["city"].strip(),
         d.get("state","").strip(), d["pin_code"].strip(),
         d.get("notes","").strip(), subtotal, ship, total)
    )
    res = cur.fetchone()
    oid = res["id"] if (res and isinstance(res, dict)) else (res[0] if res else None)
    for item in order_items:
        conn.execute(
            "INSERT INTO order_items (order_id,product_id,product_name,price,qty) VALUES (%s,%s,%s,%s,%s)",
            (oid, item["id"], item["name"], item["price"], item["qty"])
        )
        conn.execute(
            "UPDATE products SET stock=GREATEST(0,stock-%s),updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (item["qty"], item["id"])
        )
    conn.commit()
    order = conn.execute("SELECT * FROM orders WHERE id=%s", (oid,)).fetchone()
    conn.close()
    return jsonify(order_ref=ref, order=dict(order), items=order_items,
                   message="Order placed"), 201


# ── My orders ─────────────────────────────────────────────────────────
@bp.route("/api/orders/my", methods=["GET"])
@login_required
def my_orders():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC", (g.user_id,)
    ).fetchall()
    result = []
    for o in rows:
        items = conn.execute("SELECT * FROM order_items WHERE order_id=%s", (o["id"],)).fetchall()
        result.append(dict(o) | {"items": [dict(i) for i in items]})
    conn.close()
    return jsonify(orders=result), 200


# ── ADMIN: list all ───────────────────────────────────────────────────
@bp.route("/api/admin/orders", methods=["GET"])
@admin_required
def admin_orders():
    status = request.args.get("status","")
    sql, args = "SELECT * FROM orders", []
    if status and status in STATUSES:
        sql += " WHERE status=%s"; args.append(status)
    sql += " ORDER BY created_at DESC"
    conn = get_conn(); rows = conn.execute(sql,args).fetchall(); conn.close()
    return jsonify(orders=[dict(r) for r in rows], total=len(rows)), 200


# ── ADMIN: detail ─────────────────────────────────────────────────────
@bp.route("/api/admin/orders/<int:oid>", methods=["GET"])
@admin_required
def admin_order_detail(oid):
    conn = get_conn()
    o = conn.execute("SELECT * FROM orders WHERE id=%s", (oid,)).fetchone()
    if not o: conn.close(); return jsonify(error="Not found"), 404
    items = conn.execute("SELECT * FROM order_items WHERE order_id=%s", (oid,)).fetchall()
    conn.close()
    return jsonify(order=dict(o) | {"items": [dict(i) for i in items]}), 200


# ── ADMIN: update status ──────────────────────────────────────────────
@bp.route("/api/admin/orders/<int:oid>/status", methods=["PUT"])
@admin_required
def update_status(oid):
    d = request.get_json(silent=True) or {}
    status = (d.get("status") or "").strip()
    if status not in STATUSES: return jsonify(error=f"Status must be one of {STATUSES}"), 400
    conn = get_conn()
    if not conn.execute("SELECT id FROM orders WHERE id=%s", (oid,)).fetchone():
        conn.close(); return jsonify(error="Not found"), 404
    conn.execute("UPDATE orders SET status=%s WHERE id=%s", (status, oid)); conn.commit(); conn.close()
    return jsonify(status=status, message=f"Order status → {status}"), 200
