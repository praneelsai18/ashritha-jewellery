import os
import sys

backend_dir = os.path.join(os.getcwd(), 'backend')
if not os.path.exists(backend_dir):
    backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app import app
    from config.database import init_db

    try:
        init_db()
    except Exception as e:
        print("Database initialization failed:", e)

except Exception as boot_error:
    import traceback
    from flask import Flask, jsonify
    app = Flask(__name__)
    err_trace = traceback.format_exc()
    print("FATAL BOOT ERROR:", err_trace)
    
    @app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    @app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    def catch_all(path):
        return jsonify(error="Vercel App Crash", details=err_trace), 500
