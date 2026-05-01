"""
Orders routes:
  POST /api/orders               – place order (optional auth — guest or logged in)
  GET  /api/orders/my            – my orders (login_required)
  GET  /api/admin/orders         – all orders (admin)
  GET  /api/admin/orders/:id     – order detail (admin)
  PUT  /api/admin/orders/:id/status – update status (admin)
"""
import time
from flask import Blueprint, request, jsonify, g
from config.database import get_conn
from middleware.auth import login_required, admin_required, optional_auth

orders_bp = Blueprint("orders", __name__)

VALID_STATUSES = {"pending", "confirmed", "shipped", "delivered", "cancelled"}


# ── PLACE ORDER ───────────────────────────────────────────────────────────────
@orders_bp.route("/api/orders", methods=["POST"])
@optional_auth
def place_order():
    data = request.get_json(silent=True) or {}

    # Validate required fields
    required = ["customer_name", "customer_phone", "address", "city", "pin_code", "items"]
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    items = data["items"]
    if not items or not isinstance(items, list):
        return jsonify({"error": "Order must contain at least one item"}), 400

    conn = get_conn()

    # Validate items and compute totals
    order_items, subtotal = [], 0.0
    for item in items:
        pid = item.get("product_id")
        qty = int(item.get("qty", 1))
        if not pid or qty < 1:
            conn.close()
            return jsonify({"error": "Invalid item in order"}), 400

        product = conn.execute(
            "SELECT id, name, price, stock, is_active FROM products WHERE id = ?", (pid,)
        ).fetchone()

        if not product:
            conn.close()
            return jsonify({"error": f"Product #{pid} not found"}), 404
        if not product["is_active"]:
            conn.close()
            return jsonify({"error": f"'{product['name']}' is no longer available"}), 400
        if product["stock"] < qty:
            conn.close()
            return jsonify({
                "error": f"Only {product['stock']} units of '{product['name']}' available",
                "available": product["stock"]
            }), 400

        order_items.append({
            "product_id":   product["id"],
            "product_name": product["name"],
            "price":        product["price"],
            "qty":          qty,
        })
        subtotal += product["price"] * qty

    # Settings
    settings_rows = conn.execute("SELECT key, value FROM settings WHERE key IN ('free_shipping','shipping_charge')").fetchall()
    settings = {r["key"]: float(r["value"]) for r in settings_rows}
    free_min = settings.get("free_shipping", 499)
    ship_fee = 0.0 if subtotal >= free_min else settings.get("shipping_charge", 50)
    total    = subtotal + ship_fee

    # Generate order ref
    order_ref = "AJ" + str(int(time.time()))[-6:]

    # Insert order
    user_id = g.user_id  # None for guests
    cursor = conn.execute(
        """INSERT INTO orders
           (order_ref, user_id, customer_name, customer_phone, address, city, state, pin_code, notes, subtotal, shipping, total)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (order_ref, user_id,
         data["customer_name"].strip(), data["customer_phone"].strip(),
         data["address"].strip(), data["city"].strip(),
         data.get("state", "").strip(), data["pin_code"].strip(),
         data.get("notes", "").strip(),
         subtotal, ship_fee, total)
    )
    order_id = cursor.lastrowid

    # Insert order items + reduce stock
    for item in order_items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price, qty) VALUES (?,?,?,?,?)",
            (order_id, item["product_id"], item["product_name"], item["price"], item["qty"])
        )
        conn.execute(
            "UPDATE products SET stock = MAX(0, stock - ?), updated_at = datetime('now') WHERE id = ?",
            (item["qty"], item["product_id"])
        )

    conn.commit()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()

    return jsonify({
        "message":   "Order placed successfully",
        "order_ref": order_ref,
        "order":     _fmt_order(order),
        "items":     order_items,
    }), 201


# ── MY ORDERS ─────────────────────────────────────────────────────────────────
@orders_bp.route("/api/orders/my", methods=["GET"])
@login_required
def my_orders():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (g.user_id,)
    ).fetchall()

    result = []
    for order in rows:
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order["id"],)
        ).fetchall()
        o = _fmt_order(order)
        o["items"] = [dict(i) for i in items]
        result.append(o)

    conn.close()
    return jsonify({"orders": result}), 200


# ── ADMIN: ALL ORDERS ─────────────────────────────────────────────────────────
@orders_bp.route("/api/admin/orders", methods=["GET"])
@admin_required
def admin_orders():
    status = request.args.get("status", "")
    sql  = "SELECT * FROM orders"
    args = []
    if status and status in VALID_STATUSES:
        sql  += " WHERE status = ?"
        args.append(status)
    sql += " ORDER BY created_at DESC"

    conn = get_conn()
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return jsonify({"orders": [_fmt_order(r) for r in rows], "total": len(rows)}), 200


# ── ADMIN: ORDER DETAIL ───────────────────────────────────────────────────────
@orders_bp.route("/api/admin/orders/<int:oid>", methods=["GET"])
@admin_required
def admin_order_detail(oid):
    conn = get_conn()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (oid,)
    ).fetchall()
    conn.close()
    o = _fmt_order(order)
    o["items"] = [dict(i) for i in items]
    return jsonify({"order": o}), 200


# ── ADMIN: UPDATE STATUS ──────────────────────────────────────────────────────
@orders_bp.route("/api/admin/orders/<int:oid>/status", methods=["PUT"])
@admin_required
def update_order_status(oid):
    data   = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Allowed: {VALID_STATUSES}"}), 400

    conn = get_conn()
    row  = conn.execute("SELECT id FROM orders WHERE id = ?", (oid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Order not found"}), 404

    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, oid))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Order status updated to '{status}'", "status": status}), 200


# ── HELPERS ───────────────────────────────────────────────────────────────────
def _fmt_order(row) -> dict:
    d = dict(row)
    return d
