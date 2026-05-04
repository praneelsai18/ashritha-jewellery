import os
import sys
import traceback
from pathlib import Path
from flask import Flask, jsonify

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
backend_dir = PROJECT_ROOT / "backend"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from app import app
    from config.database import init_db

    try:
        init_db()
    except Exception as e:
        print("Database initialization failed:", e)

except Exception:
    err_trace = traceback.format_exc()
    print("FATAL BOOT ERROR:", err_trace)
    app = Flask(__name__)

    @app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    @app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    def catch_all(path):
        return jsonify(error="Vercel App Crash", details=err_trace), 500

application = app
handler = app
