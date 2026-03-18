"""
Ashritha Jewellery — Backend API
Run:  python app.py
Prod: gunicorn app:app
"""

import os, sys
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


# ----------------------------------------------------
# NEW HOME ROUTE (ADDED)
# ----------------------------------------------------
@app.route("/")
def home():
    return jsonify(
        status="Ashritha Jewelleries API running",
        message="Backend deployed successfully"
    ), 200


# ----------------------------------------------------
# CORS
# ----------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    os.environ.get("FRONTEND_URL", ""),
]

@app.after_request
def cors(resp):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS or os.environ.get("FLASK_ENV") == "development":
        resp.headers["Access-Control-Allow-Origin"]      = origin or "*"
        resp.headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp


@app.before_request
def preflight():
    if request.method == "OPTIONS":
        from flask import make_response
        r = make_response()
        origin = request.headers.get("Origin", "")
        r.headers["Access-Control-Allow-Origin"]  = origin or "*"
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
        service="Ashritha Jewellery API",
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
    return jsonify(error="Internal server error", detail=str(e)), 500


# ----------------------------------------------------
# Start Server
# ----------------------------------------------------
if __name__ == "__main__":

    init_db()

    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"

    print(f"""
╔══════════════════════════════════════════════════════╗
║   Ashritha Jewellery API  v2.0                       ║
║   http://localhost:{port}                            ║
║   Admin: admin@ashritha.com / admin123               ║
╚══════════════════════════════════════════════════════╝
""")

    app.run(host="0.0.0.0", port=port, debug=debug)