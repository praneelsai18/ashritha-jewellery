"""
Products routes:
  GET  /api/products             – list all active products (public)
  GET  /api/products/:id         – single product (public)
  POST /api/admin/products       – add product (admin)
  PUT  /api/admin/products/:id   – edit product (admin)
  PUT  /api/admin/products/:id/stock – update stock only (admin)
  DELETE /api/admin/products/:id – delete (admin)
  PUT  /api/admin/products/:id/toggle – toggle visible/hidden (admin)
  GET  /api/admin/products       – full list including hidden (admin)
"""
from flask import Blueprint, request, jsonify
from config.database import get_conn
from middleware.auth import admin_required, optional_auth

products_bp = Blueprint("products", __name__)

ALLOWED_CATS = {"necklace", "earrings", "bangles", "sets", "rings", "silver"}
ALLOWED_BADGES = {"", "New", "Bestseller", "Sale", "Limited", "Trending"}


# ── PUBLIC: LIST ──────────────────────────────────────────────────────────────
@products_bp.route("/api/products", methods=["GET"])
@optional_auth
def list_products():
    category = request.args.get("category", "")
    sort     = request.args.get("sort", "default")   # default | price-asc | price-desc | newest
    q        = request.args.get("q", "").strip()

    sql  = "SELECT * FROM products WHERE is_active = 1"
    args = []

    if category and category in ALLOWED_CATS:
        sql  += " AND category = ?"
        args.append(category)

    if q:
        sql  += " AND (name LIKE ? OR description LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]

    order_map = {
        "price-asc":  "price ASC",
        "price-desc": "price DESC",
        "newest":     "created_at DESC",
        "default":    "id ASC",
    }
    sql += " ORDER BY " + order_map.get(sort, "id ASC")

    conn  = get_conn()
    rows  = conn.execute(sql, args).fetchall()
    conn.close()
    return jsonify({"products": [_fmt(r) for r in rows]}), 200


# ── PUBLIC: SINGLE ────────────────────────────────────────────────────────────
@products_bp.route("/api/products/<int:pid>", methods=["GET"])
def get_product(pid):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM products WHERE id = ? AND is_active = 1", (pid,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"product": _fmt(row)}), 200


# ── ADMIN: LIST ALL ───────────────────────────────────────────────────────────
@products_bp.route("/api/admin/products", methods=["GET"])
@admin_required
def admin_list():
    q = request.args.get("q", "").strip()
    sql  = "SELECT * FROM products"
    args = []
    if q:
        sql  += " WHERE name LIKE ? OR description LIKE ?"
        args = [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY created_at DESC"
    conn = get_conn()
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return jsonify({"products": [_fmt(r) for r in rows], "total": len(rows)}), 200


# ── ADMIN: ADD ────────────────────────────────────────────────────────────────
@products_bp.route("/api/admin/products", methods=["POST"])
@admin_required
def add_product():
    data  = request.get_json(silent=True) or {}
    name  = (data.get("name") or "").strip()
    cat   = (data.get("category") or "").strip()
    price = data.get("price")
    stock = data.get("stock")

    errors = []
    if not name:        errors.append("Product name is required")
    if cat not in ALLOWED_CATS: errors.append(f"Invalid category. Allowed: {ALLOWED_CATS}")
    if price is None or float(price) <= 0: errors.append("Valid price is required")
    if stock is None or int(stock) < 0:    errors.append("Stock must be 0 or more")
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    mrp   = data.get("mrp")
    badge = (data.get("badge") or "").strip()
    if badge not in ALLOWED_BADGES:
        badge = ""

    conn = get_conn()
    cursor = conn.execute(
        """INSERT INTO products (name, category, price, mrp, stock, badge, description, image_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, cat, float(price), float(mrp) if mrp else None,
         int(stock), badge,
         (data.get("description") or "").strip(),
         (data.get("image_url") or "").strip())
    )
    product_id = cursor.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return jsonify({"product": _fmt(row), "message": "Product added"}), 201


# ── ADMIN: EDIT ───────────────────────────────────────────────────────────────
@products_bp.route("/api/admin/products/<int:pid>", methods=["PUT"])
@admin_required
def edit_product(pid):
    conn = get_conn()
    existing = conn.execute("SELECT id FROM products WHERE id = ?", (pid,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    data  = request.get_json(silent=True) or {}
    name  = (data.get("name") or "").strip()
    cat   = (data.get("category") or "").strip()
    price = data.get("price")

    if name and cat and cat not in ALLOWED_CATS:
        conn.close()
        return jsonify({"error": "Invalid category"}), 400

    fields, args = [], []
    if name:
        fields.append("name = ?"); args.append(name)
    if cat and cat in ALLOWED_CATS:
        fields.append("category = ?"); args.append(cat)
    if price is not None:
        fields.append("price = ?"); args.append(float(price))
    if "mrp" in data:
        fields.append("mrp = ?"); args.append(float(data["mrp"]) if data["mrp"] else None)
    if "stock" in data:
        fields.append("stock = ?"); args.append(max(0, int(data["stock"])))
    if "badge" in data:
        b = (data["badge"] or "").strip()
        fields.append("badge = ?"); args.append(b if b in ALLOWED_BADGES else "")
    if "description" in data:
        fields.append("description = ?"); args.append((data["description"] or "").strip())
    if "image_url" in data:
        fields.append("image_url = ?"); args.append((data["image_url"] or "").strip())

    if not fields:
        conn.close()
        return jsonify({"error": "No fields to update"}), 400

    fields.append("updated_at = datetime('now')")
    args.append(pid)
    conn.execute(f"UPDATE products SET {', '.join(fields)} WHERE id = ?", args)
    conn.commit()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return jsonify({"product": _fmt(row), "message": "Product updated"}), 200


# ── ADMIN: UPDATE STOCK ONLY ──────────────────────────────────────────────────
@products_bp.route("/api/admin/products/<int:pid>/stock", methods=["PUT"])
@admin_required
def update_stock(pid):
    data  = request.get_json(silent=True) or {}
    stock = data.get("stock")
    if stock is None or int(stock) < 0:
        return jsonify({"error": "Stock must be 0 or more"}), 400

    conn = get_conn()
    existing = conn.execute("SELECT id, name FROM products WHERE id = ?", (pid,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    conn.execute(
        "UPDATE products SET stock = ?, updated_at = datetime('now') WHERE id = ?",
        (int(stock), pid)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": f"Stock updated to {stock}", "stock": int(stock)}), 200


# ── ADMIN: TOGGLE VISIBILITY ──────────────────────────────────────────────────
@products_bp.route("/api/admin/products/<int:pid>/toggle", methods=["PUT"])
@admin_required
def toggle_product(pid):
    conn = get_conn()
    row  = conn.execute("SELECT id, is_active FROM products WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Product not found"}), 404
    new_status = 0 if row["is_active"] else 1
    conn.execute("UPDATE products SET is_active = ? WHERE id = ?", (new_status, pid))
    conn.commit()
    conn.close()
    return jsonify({"is_active": bool(new_status), "message": "Visibility updated"}), 200


# ── ADMIN: DELETE ─────────────────────────────────────────────────────────────
@products_bp.route("/api/admin/products/<int:pid>", methods=["DELETE"])
@admin_required
def delete_product(pid):
    conn = get_conn()
    row  = conn.execute("SELECT id FROM products WHERE id = ?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Product not found"}), 404
    conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Product deleted"}), 200


# ── HELPERS ───────────────────────────────────────────────────────────────────
def _fmt(row) -> dict:
    d = dict(row)
    d["is_active"] = bool(d.get("is_active", 1))
    d["stock_status"] = (
        "oos" if d["stock"] == 0 else
        "low" if d["stock"] <= 3 else
        "in"
    )
    if d.get("mrp") and d.get("price"):
        d["discount_pct"] = round((1 - d["price"] / d["mrp"]) * 100)
    else:
        d["discount_pct"] = 0
    return d
