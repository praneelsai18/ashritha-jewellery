"""Products routes — /api/products  &  /api/admin/products"""
import os
import re
import json
import base64
import time as _time
import threading

from flask import Blueprint, request, jsonify, make_response, redirect
from flask import json as flask_json
import psycopg2
from config.database import get_conn
from middleware.auth import admin_required

bp = Blueprint("products", __name__)

CATS   = {"necklace","earrings","bangles","sets","rings","combo","longchains","blackbeads"}
BADGES = {"","New","Bestseller","Sale","Limited","Trending"}
DEFAULT_BANGLE_SIZES = ["2.2", "2.4", "2.6", "2.8", "2.10"]

# ── In-process TTL cache for the public product listing ──────────────
# Product cards only need the first image; ditto for filters/sort. We
# memoize the fully-serialized JSON payload keyed by request args so
# repeat visitors skip both the DB roundtrip and the JSON build.
_LIST_CACHE_TTL = float(os.environ.get("PRODUCT_LIST_CACHE_TTL", "20"))
_LIST_CACHE = {}
_LIST_CACHE_LOCK = threading.Lock()


def _cache_bust():
    with _LIST_CACHE_LOCK:
        _LIST_CACHE.clear()


DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[\w.+\-]+);base64,(?P<data>.+)$", re.DOTALL)


def _parse_image_list(image_url):
    """Normalize the messy `image_url` column into a Python list of strings."""
    if not image_url:
        return []
    if isinstance(image_url, list):
        return [str(x) for x in image_url if x]
    if not isinstance(image_url, str):
        return []
    s = image_url.strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x) for x in arr if x]
        except Exception:
            pass
    return [s]


def _norm_bangle_sizes(value):
    if value is None:
        return list(DEFAULT_BANGLE_SIZES)
    if isinstance(value, list):
        vals = value
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return list(DEFAULT_BANGLE_SIZES)
        try:
            parsed = json.loads(s)
            vals = parsed if isinstance(parsed, list) else s.split(",")
        except Exception:
            vals = s.split(",")
    else:
        return list(DEFAULT_BANGLE_SIZES)
    cleaned = []
    seen = set()
    for raw in vals:
        item = str(raw).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned or list(DEFAULT_BANGLE_SIZES)


def fmt(row):
    d = dict(row)
    d["is_active"]    = bool(d.get("is_active", 1))
    d["rent_enabled"] = bool(d.get("rent_enabled", 0))
    price, mrp = d.get("price",0), d.get("mrp")
    d["discount_pct"] = round((1 - price/mrp)*100) if mrp and mrp > price else 0
    d["stock_status"] = "oos" if d["stock"]==0 else "low" if d["stock"]<=3 else "in"
    if d.get("category") == "bangles":
        d["bangle_sizes"] = _norm_bangle_sizes(d.get("bangle_sizes"))
    else:
        d["bangle_sizes"] = []
    return d


# ── PUBLIC: list ─────────────────────────────────────────────────────
@bp.route("/api/products", methods=["GET"])
def list_products():
    cat   = request.args.get("category","")
    sort  = request.args.get("sort","default")
    q     = request.args.get("q","").strip()
    rent  = request.args.get("rent","")          # "1" = rent only

    cache_key = (cat, sort, q.lower(), rent)
    now = _time.time()
    with _LIST_CACHE_LOCK:
        cached = _LIST_CACHE.get(cache_key)
        payload = cached["payload"] if cached and now - cached["ts"] < _LIST_CACHE_TTL else None

    if payload is None:
        t0 = _time.perf_counter()
        # `image_url` is excluded from SELECT so we don't ship multi-MB
        # base64 blobs back from the DB just to throw them away.
        sql, args = "SELECT id,name,category,price,mrp,stock,badge,description,is_active,rent_enabled,rent_price,deposit,max_days,bangle_sizes,created_at,updated_at, (CASE WHEN image_url IS NULL OR image_url='' OR image_url='[]' THEN 0 ELSE 1 END) AS has_image FROM products WHERE is_active=1", []
        if cat and cat in CATS:
            sql += " AND category=%s"; args.append(cat)
        if rent == "1":
            sql += " AND rent_enabled=1"
        if q:
            sql += " AND (name ILIKE %s OR description ILIKE %s)"; args += [f"%{q}%",f"%{q}%"]
        order = {"price-asc":"price ASC","price-desc":"price DESC",
                 "newest":"created_at DESC"}.get(sort,"id ASC")
        sql += f" ORDER BY {order}"

        conn = get_conn()
        try:
            rows = conn.execute(sql, args).fetchall()
        finally:
            conn.close()
        t_db = _time.perf_counter()

        items = []
        for r in rows:
            row = dict(r)
            pid = row.get("id")
            has_image = bool(row.pop("has_image", 0))
            row["image_url"] = (
                json.dumps([f"/api/products/{pid}/image/0"]) if has_image else ""
            )
            items.append(fmt(row))
        payload = flask_json.dumps({"products": items})
        t_end = _time.perf_counter()

        print(
            f"[/api/products] {len(items)} items  db={int((t_db-t0)*1000)}ms  "
            f"serialize={int((t_end-t_db)*1000)}ms  payload={len(payload)//1024}KB"
        )

        with _LIST_CACHE_LOCK:
            _LIST_CACHE[cache_key] = {"ts": now, "payload": payload}

    resp = make_response(payload, 200)
    resp.headers["Content-Type"] = "application/json"
    # Browsers may keep the catalog for a short window. Always revalidate
    # so admin edits surface quickly. Overrides the global `no-store`
    # set by the production after_request hook.
    resp.headers["Cache-Control"] = "public, max-age=30, must-revalidate"
    return resp


# ── PUBLIC: single ────────────────────────────────────────────────────
@bp.route("/api/products/<int:pid>", methods=["GET"])
def get_product(pid):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM products WHERE id=%s AND is_active=1", (pid,)
    ).fetchone(); conn.close()
    if not row: return jsonify(error="Product not found"), 404
    return jsonify(product=fmt(row)), 200


# ── PUBLIC: image binary ─────────────────────────────────────────────
# Pulls a single product image out of the JSON envelope and serves it as
# real binary with aggressive Cache-Control + ETag. The first hit decodes
# the base64; everything after is a 304 from the browser.
@bp.route("/api/products/<int:pid>/image/<int:idx>", methods=["GET"])
def product_image(pid, idx):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT image_url, updated_at FROM products WHERE id=%s AND is_active=1",
            (pid,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify(error="Not found"), 404

    images = _parse_image_list(row.get("image_url"))
    if idx < 0 or idx >= len(images):
        return jsonify(error="Image not found"), 404

    img = images[idx]

    # Already a remote URL → just bounce the browser there.
    if img.startswith(("http://", "https://", "//")):
        return redirect(img, code=302)

    m = DATA_URL_RE.match(img)
    if m:
        mime = m.group("mime")
        try:
            raw = base64.b64decode(m.group("data"), validate=False)
        except Exception:
            return jsonify(error="Invalid image data"), 500
    else:
        # Bare base64 with no data-URL prefix — best effort as JPEG.
        try:
            raw = base64.b64decode(img, validate=False)
            mime = "image/jpeg"
        except Exception:
            return jsonify(error="Invalid image data"), 500

    etag = 'W/"p%d-i%d-%s"' % (pid, idx, row.get("updated_at"))
    if request.headers.get("If-None-Match") == etag:
        resp = make_response("", 304)
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"
        return resp

    resp = make_response(raw, 200)
    resp.headers["Content-Type"] = mime
    resp.headers["Content-Length"] = str(len(raw))
    resp.headers["ETag"] = etag
    # 1 day cache; ETag handles invalidation when the product is edited
    # (updated_at changes ⇒ ETag changes ⇒ browser re-downloads).
    resp.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"
    return resp


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
            rent_enabled,rent_price,deposit,max_days,bangle_sizes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (name, cat, float(price),
         float(d["mrp"]) if d.get("mrp") else None,
         int(stock), badge if badge in BADGES else "",
         (d.get("description") or "").strip(),
         (d.get("image_url") or "").strip(),
         1 if d.get("rent_enabled") else 0,
         float(d.get("rent_price") or 0),
         float(d.get("deposit") or 0),
         int(d.get("max_days") or 7),
         json.dumps(_norm_bangle_sizes(d.get("bangle_sizes")) if cat == "bangles" else []))
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
    _cache_bust()
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
        "rent_price":"rent_price","deposit":"deposit","max_days":"max_days",
        "bangle_sizes":"bangle_sizes",
    }
    for k, col in MAP.items():
        if k in d:
            v = d[k]
            if k == "rent_enabled": v = 1 if v else 0
            elif k == "category" and v not in CATS: continue
            elif k == "badge" and v not in BADGES: v = ""
            elif k == "bangle_sizes":
                v = json.dumps(_norm_bangle_sizes(v))
            fields.append(f"{col}=%s"); args.append(v)
    if len(fields)==1: conn.close(); return jsonify(error="Nothing to update"), 400
    args.append(pid)
    conn.execute(f"UPDATE products SET {','.join(fields)} WHERE id=%s", args)
    conn.commit()
    row = conn.execute("SELECT * FROM products WHERE id=%s", (pid,)).fetchone(); conn.close()
    _cache_bust()
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
    _cache_bust()
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
    _cache_bust()
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
        _cache_bust()
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
        _cache_bust()
        return jsonify(
            message="Product archived because it is linked with existing orders/rentals",
            archived=True
        ), 200
