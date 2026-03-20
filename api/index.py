import os
import sys

# Add the backend directory to sys.path so Python can find app.py and its modules
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app

# Vercel requires the WSGI application to be named 'app' or 'handler'
handler = app
