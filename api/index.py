import os
import sys

api_dir = os.path.dirname(os.path.abspath(__file__))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from app import app

# Vercel requires the WSGI application to be named 'app' or 'handler'
handler = app
