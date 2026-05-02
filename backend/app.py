"""
Ashritha Jewellers — Backend API
Run:  python app.py
Prod: gunicorn app:app
"""

import os
import sys
import time
import threading
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
from config.database import init_db
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
IS_PROD = os.environ.get("FLASK_ENV", "development") == "production"
if IS_PROD and app.config["SECRET_KEY"] == "ashritha_secret_CHANGE_IN_PROD":
    raise RuntimeError("SECRET_KEY must be set in production")


# ----------------------------------------------------
# NEW HOME ROUTE (ADDED)
# ----------------------------------------------------
@app.route("/")
def home():
    return jsonify(
        status="Ashritha Jewellers API running",
        message="Backend deployed successfully"
    ), 200


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
    if origin and origin in ALLOWED_ORIGINS:
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
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.before_request
def preflight():
    if request.path.startswith("/api/") and request.content_length and request.content_length > MAX_JSON_BYTES:
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
        if origin and origin in ALLOWED_ORIGINS:
            r.headers["Access-Control-Allow-Origin"] = origin
            r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return r, 204


# ----------------------------------------------------
# Blueprints
# ----------------------------------------------------
for bp in [auth_bp, products_bp, orders_bp, reviews_bp, rent_bp, settings_bp]:
    app.register_blueprint(bp)


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