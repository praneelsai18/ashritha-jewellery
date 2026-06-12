"""
Ashritha Jewellers — Backend API
Run:  python app.py
Prod: gunicorn app:app
"""

import os
import sys
import gzip
import time
import threading
import uuid
from io import BytesIO
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from config.database import init_db, get_conn

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
STATIC_EXTENSIONS = {
    ".html", ".js", ".mjs", ".css", ".map",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".json", ".txt", ".pdf",
}
from routes.auth     import bp as auth_bp
from routes.products import bp as products_bp
from routes.orders   import bp as orders_bp
from routes.reviews  import bp as reviews_bp
from routes.rent     import bp as rent_bp
from routes.settings import bp as settings_bp

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ashritha_secret_CHANGE_IN_PROD")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024   # 20 MB
MAX_JSON_BYTES = int(os.environ.get("MAX_JSON_BYTES", 1024 * 1024))
MAX_MEDIA_JSON_BYTES = int(os.environ.get("MAX_MEDIA_JSON_BYTES", app.config["MAX_CONTENT_LENGTH"]))
LARGE_JSON_PATH_PREFIXES = (
    "/api/admin/products",
)
IS_PROD = os.environ.get("FLASK_ENV", "development") == "production"
if IS_PROD and app.config["SECRET_KEY"] == "ashritha_secret_CHANGE_IN_PROD":
    print("WARNING: SECRET_KEY must be set in production. Using insecure default.")


# ----------------------------------------------------
# FRONTEND + STATIC FILE SERVING
# Mirrors Vercel: /api/* -> Flask, everything else -> index.html / static assets.
# ----------------------------------------------------
@app.route("/")
def home():
    return send_from_directory(PROJECT_ROOT, "index.html")


@app.route("/<path:filename>")
def static_or_spa(filename):
    if filename.startswith("api/"):
        return jsonify(error="Endpoint not found"), 404

    # Block hidden files like .env, .git/*, etc.
    if any(part.startswith(".") for part in filename.split("/")):
        return jsonify(error="Forbidden"), 403

    ext = os.path.splitext(filename)[1].lower()
    full_path = os.path.join(PROJECT_ROOT, filename)
    if ext in STATIC_EXTENSIONS and os.path.isfile(full_path):
        return send_from_directory(PROJECT_ROOT, filename)

    # SPA fallback: anything else falls back to index.html
    return send_from_directory(PROJECT_ROOT, "index.html")


# ----------------------------------------------------
# CORS
# ----------------------------------------------------
DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

_front = [x.strip() for x in os.environ.get("FRONTEND_URL", "").split(",") if x.strip()]
_allow = [x.strip() for x in os.environ.get("ALLOWED_ORIGINS", "").split(",") if x.strip()]
ALLOWED_ORIGINS = set(DEFAULT_DEV_ORIGINS + _front + _allow)
if not _front and not _allow:
    # No explicit origin config means allow the calling origin for API routes.
    ALLOWED_ORIGINS = None

RATE_LOCK = threading.Lock()
RATE_BUCKETS = {}
RATE_RULES = {
    "auth": (10, 60),   # 10 requests / minute
    "order": (8, 60),   # 8 requests / minute
    "rent": (8, 60),
}

def _client_ip():
    xfwd = request.headers.get("X-Forwarded-For", "")
    if xfwd:
        return xfwd.split(",")[0].strip()
    return request.remote_addr or "unknown"

def _apply_rate_limit(bucket_name):
    rule = RATE_RULES.get(bucket_name)
    if not rule:
        return None
    limit, window = rule
    now = time.time()
    key = f"{bucket_name}:{_client_ip()}"
    with RATE_LOCK:
        bucket = [ts for ts in RATE_BUCKETS.get(key, []) if now - ts <= window]
        if len(bucket) >= limit:
            retry_after = int(window - (now - bucket[0])) if bucket else window
            return retry_after
        bucket.append(now)
        RATE_BUCKETS[key] = bucket
    return None

@app.after_request
def cors(resp):
    origin = request.headers.get("Origin", "")
    if origin and (ALLOWED_ORIGINS is None or origin in ALLOWED_ORIGINS):
        resp.headers["Access-Control-Allow-Origin"]      = origin
        resp.headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
        resp.headers["Access-Control-Allow-Credentials"] = "true"

    # Security headers for production hardening.
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if IS_PROD:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        # Default to no-store for sensitive responses, but let individual
        # routes opt into caching (e.g. public product listing) by setting
        # their own Cache-Control header.
        if "Cache-Control" not in resp.headers:
            resp.headers["Cache-Control"] = "no-store"
    return resp


GZIP_MIN_BYTES = 1024
# Only gzip text-ish payloads. Real image binaries (jpeg/png/webp) are
# already compressed — re-compressing just burns CPU for ~0 wire savings.
GZIP_TYPES = ("application/json", "text/", "application/javascript", "image/svg+xml")


@app.after_request
def gzip_response(resp):
    """Transparently gzip JSON/text responses so the product catalog payload
    (which can run several MB once base64 images are involved) ships in a
    fraction of the bytes."""
    accept = request.headers.get("Accept-Encoding", "")
    if "gzip" not in accept.lower():
        return resp
    if resp.status_code < 200 or resp.status_code >= 300:
        return resp
    if "Content-Encoding" in resp.headers:
        return resp
    if getattr(resp, "direct_passthrough", False):
        # Streamed responses (e.g. send_from_directory) can't be rewritten safely.
        return resp
    ct = resp.headers.get("Content-Type", "")
    if not any(ct.startswith(p) for p in GZIP_TYPES):
        return resp

    data = resp.get_data()
    if len(data) < GZIP_MIN_BYTES:
        return resp

    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as gz:
        gz.write(data)
    resp.set_data(buf.getvalue())
    resp.headers["Content-Encoding"] = "gzip"
    resp.headers["Content-Length"] = str(len(resp.get_data()))
    vary = [v.strip() for v in resp.headers.get("Vary", "").split(",") if v.strip()]
    if "Accept-Encoding" not in vary:
        vary.append("Accept-Encoding")
        resp.headers["Vary"] = ", ".join(vary)
    return resp


@app.before_request
def preflight():
    path_limit = MAX_MEDIA_JSON_BYTES if any(
        request.path.startswith(prefix) for prefix in LARGE_JSON_PATH_PREFIXES
    ) else MAX_JSON_BYTES

    if request.path.startswith("/api/") and request.content_length and request.content_length > path_limit:
        return jsonify(error="Request payload too large"), 413

    if request.path in ("/api/auth/login", "/api/auth/register", "/api/auth/forgot-password", "/api/auth/google"):
        retry_after = _apply_rate_limit("auth")
        if retry_after is not None:
            return jsonify(error="Too many requests. Please try again shortly."), 429
    elif request.path == "/api/orders" and request.method == "POST":
        retry_after = _apply_rate_limit("order")
        if retry_after is not None:
            return jsonify(error="Too many order attempts. Please try again shortly."), 429
    elif request.path == "/api/rent" and request.method == "POST":
        retry_after = _apply_rate_limit("rent")
        if retry_after is not None:
            return jsonify(error="Too many rent requests. Please try again shortly."), 429

    if request.method == "OPTIONS":
        from flask import make_response
        r = make_response()
        origin = request.headers.get("Origin", "")
        if origin and (ALLOWED_ORIGINS is None or origin in ALLOWED_ORIGINS):
            r.headers["Access-Control-Allow-Origin"] = origin
            r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return r, 204


# ----------------------------------------------------
# Blueprints
# ----------------------------------------------------
for bp in [auth_bp, products_bp, orders_bp, reviews_bp, rent_bp, settings_bp]:
    app.register_blueprint(bp)


def _warm_db_pool():
    """Open one connection at boot so the first real request doesn't
    have to pay the ~500ms Supabase TLS handshake."""
    try:
        c = get_conn()
        c.close()
    except Exception as e:
        print(f"[startup] DB pool warm-up skipped: {e}")


# Run in a background thread so Flask startup isn't blocked if the DB
# is briefly unreachable. Triggers for both `flask run` / `python app.py`
# and gunicorn worker boot (module import time).
threading.Thread(target=_warm_db_pool, daemon=True).start()


# ----------------------------------------------------
# Health Check
# ----------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify(
        status="ok",
        service="Ashritha Jewellers API",
        version="2.0.0"
    ), 200


# ----------------------------------------------------
# Error Handlers
# ----------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify(error="Endpoint not found"), 404

@app.errorhandler(405)
def bad_method(e):
    return jsonify(error="Method not allowed"), 405

@app.errorhandler(413)
def too_large(e):
    return jsonify(error="File too large"), 413

@app.errorhandler(500)
def server_err(e):
    req_id = str(uuid.uuid4())
    print(f"[ERROR] request_id={req_id} path={request.path} err={e}")
    return jsonify(error="Internal server error", request_id=req_id), 500


@app.errorhandler(Exception)
def unhandled(e):
    req_id = str(uuid.uuid4())
    print(f"[UNHANDLED] request_id={req_id} path={request.path} err={e}")
    return jsonify(error="Unexpected server error", request_id=req_id), 500


# ----------------------------------------------------
# Start Server
# ----------------------------------------------------
if __name__ == "__main__":

    init_db()

    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"

    print(f"""
╔══════════════════════════════════════════════════════╗
║   Ashritha Jewellers API  v2.0                       ║
║   http://localhost:{port}                            ║
║   Environment: {'development' if debug else 'production'}                     ║
╚══════════════════════════════════════════════════════╝
""")

    app.run(host="0.0.0.0", port=port, debug=debug)