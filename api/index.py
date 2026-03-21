import os
import sys

backend_dir = os.path.join(os.getcwd(), 'backend')
if not os.path.exists(backend_dir):
    backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from config.database import init_db

try:
    init_db()
except Exception as e:
    print("Database initialization failed:", e)

handler = app
