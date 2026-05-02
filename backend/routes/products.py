"""Products routes — /api/products  &  /api/admin/products"""
from flask import Blueprint, request, jsonify
import psycopg2
from config.database import get_conn
from middleware.auth import admin_required, optional_auth

bp = Blueprint("products", __name__)

CATS   = {"necklace","earrings","bangles","sets","rings"}
BADGES = {"","New","Bestseller","Sale","Limited","Trending"}


def fmt(row):
    d = dict(row)
    d["is_active"]    = bool(d.get("is_active", 1))
    d["rent_enabled"] = bool(d.get("rent_enabled", 0))
    price, mrp = d.get("price",0), d.get("mrp")
    d["discount_pct"] = round((1 - price/mrp)*100) if mrp and mrp > price else 0
    d["stock_status"] = "oos" if d["stock"]==0 else "low" if d["stock"]<=3 else "in"
    return d


# ── PUBLIC: list ─────────────────────────────────────────────────────
@bp.route("/api/products", methods=["GET"])
@optional_auth
def list_products():
    cat   = request.args.get("category","")
    sort  = request.args.get("sort","default")
    q     = request.args.get("q","").strip()
    rent  = request.args.get("rent","")          # "1" = rent only

    sql, args = "SELECT * FROM products WHERE is_active=1", []
    if cat and cat in CATS:
        sql += " AND category=%s"; args.append(cat)
    if rent == "1":
        sql += " AND rent_enabled=1"
    if q:
        sql += " AND (name LIKE %s OR description LIKE %s)"; args += [f"%{q}%",f"%{q}%"]
    order = {"price-asc":"price ASC","price-desc":"price DESC",
             "newest":"created_at DESC"}.get(sort,"id ASC")
    sql += f" ORDER BY {order}"
    conn = get_conn(); rows = conn.execute(sql,args).fetchall(); conn.close()
    return jsonify(products=[fmt(r) for r in rows]), 200


# ── PUBLIC: single ────────────────────────────────────────────────────
@bp.route("/api/products/<int:pid>", methods=["GET"])
def get_product(pid):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM products WHERE id=%s AND is_active=1", (pid,)
    ).fetchone(); conn.close()
    if not row: return jsonify(error="Product not found"), 404
    return jsonify(product=fmt(row)), 200


# ── ADMIN: list all ───────────────────────────────────────────────────
@bp.route("/api/admin/products", methods=["GET"])
@admin_required
def admin_list():
    q = request.args.get("q","").strip()
    sql, args = "SELECT * FROM products", []
    if q: sql += " WHERE name LIKE %s OR description LIKE %s"; args=[f"%{q}%",f"%{q}%"]
    sql += " ORDER BY created_at DESC"
    conn = get_conn(); rows = conn.execute(sql,args).fetchall(); conn.close()
    return jsonify(products=[fmt(r) for r in rows], total=len(rows)), 200


# ── ADMIN: add ────────────────────────────────────────────────────────
@bp.route("/api/admin/products", methods=["POST"])
@admin_required
def add_product():
    d = request.get_json(silent=True) or {}
    name  = (d.get("name") or "").strip()
    cat   = (d.get("category") or "").strip()
    price = d.get("price")
    stock = d.get("stock")
    if not name:            return jsonify(error="Name required"), 400
    if cat not in CATS:     return jsonify(error=f"Category must be one of {CATS}"), 400
    if not price or float(price)<=0: return jsonify(error="Valid price required"), 400
    if stock is None or int(stock)<0: return jsonify(error="Stock required"), 400

    badge = (d.get("badge") or "").strip()
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO products
           (name,category,price,mrp,stock,badge,description,image_url,
            rent_enabled,rent_price,deposit,max_days)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (name, cat, float(price),
         float(d["mrp"]) if d.get("mrp") else None,
         int(stock), badge if badge in BADGES else "",
         (d.get("description") or "").strip(),
         (d.get("image_url") or "").strip(),
         1 if d.get("rent_enabled") else 0,
         float(d.get("rent_price") or 0),
         float(d.get("deposit") or 0),
         int(d.get("max_days") or 7))
    )
    res = cur.fetchone()
    if res and isinstance(res, dict):
        pid = res["id"]
    elif res:
        pid = res[0]
    else:
        pid = None
        
    conn.commit()
    row = conn.execute("SELECT * FROM products WHERE id=%s", (pid,)).fetchone(); conn.close()
    return jsonify(product=fmt(row), message="Product added"), 201


# ── ADMIN: edit ───────────────────────────────────────────────────────
@bp.route("/api/admin/products/<int:pid>", methods=["PUT"])
@admin_required
def edit_product(pid):
    conn = get_conn()
    if not conn.execute("SELECT id FROM products WHERE id=%s", (pid,)).fetchone():
        conn.close(); return jsonify(error="Not found"), 404
    d = request.get_json(silent=True) or {}
    fields, args = ["updated_at=CURRENT_TIMESTAMP"], []
    MAP = {
        "name":"name","category":"category","price":"price","mrp":"mrp",
        "stock":"stock","badge":"badge","description":"description",
        "image_url":"image_url","rent_enabled":"rent_enabled",
        "rent_price":"rent_price","deposit":"deposit","max_days":"max_days"
    }
    for k, col in MAP.items():
        if k in d:
            v = d[k]
            if k == "rent_enabled": v = 1 if v else 0
            elif k == "category" and v not in CATS: continue
            elif k == "badge" and v not in BADGES: v = ""
            fields.append(f"{col}=%s"); args.append(v)
    if len(fields)==1: conn.close(); return jsonify(error="Nothing to update"), 400
    args.append(pid)
    conn.execute(f"UPDATE products SET {','.join(fields)} WHERE id=%s", args)
    conn.commit()
    row = conn.execute("SELECT * FROM products WHERE id=%s", (pid,)).fetchone(); conn.close()
    return jsonify(product=fmt(row), message="Updated"), 200


# ── ADMIN: update stock only ─────────────────────────────────────────
@bp.route("/api/admin/products/<int:pid>/stock", methods=["PUT"])
@admin_required
def update_stock(pid):
    d = request.get_json(silent=True) or {}
    stock = d.get("stock")
    if stock is None or int(stock)<0: return jsonify(error="Stock >= 0 required"), 400
    conn = get_conn()
    if not conn.execute("SELECT id FROM products WHERE id=%s", (pid,)).fetchone():
        conn.close(); return jsonify(error="Not found"), 404
    conn.execute("UPDATE products SET stock=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s", (int(stock),pid))
    conn.commit(); conn.close()
    return jsonify(stock=int(stock), message=f"Stock updated to {stock}"), 200


# ── ADMIN: toggle visible/hidden ──────────────────────────────────────
@bp.route("/api/admin/products/<int:pid>/toggle", methods=["PUT"])
@admin_required
def toggle_product(pid):
    conn = get_conn()
    row = conn.execute("SELECT id,is_active FROM products WHERE id=%s", (pid,)).fetchone()
    if not row: conn.close(); return jsonify(error="Not found"), 404
    new = 0 if row["is_active"] else 1
    conn.execute("UPDATE products SET is_active=%s WHERE id=%s", (new,pid)); conn.commit(); conn.close()
    return jsonify(is_active=bool(new), message="Visibility updated"), 200


# ── ADMIN: delete ─────────────────────────────────────────────────────
@bp.route("/api/admin/products/<int:pid>", methods=["DELETE"])
@admin_required
def delete_product(pid):
    conn = get_conn()
    if not conn.execute("SELECT id FROM products WHERE id=%s", (pid,)).fetchone():
        conn.close(); return jsonify(error="Not found"), 404
    try:
        conn.execute("DELETE FROM products WHERE id=%s", (pid,))
        conn.commit()
        conn.close()
        return jsonify(message="Product deleted"), 200
    except psycopg2.IntegrityError:
        # Keep historical order/rental data intact and retire the product from storefront.
        conn._conn.rollback()
        conn.execute(
            "UPDATE products SET is_active=0,updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (pid,)
        )
        conn.commit()
        conn.close()
        return jsonify(
            message="Product archived because it is linked with existing orders/rentals",
            archived=True
        ), 200
