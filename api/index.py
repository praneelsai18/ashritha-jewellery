import os
import sys

# Add backend directory to path using a bulletproof approach for Vercel
import os
import sys

# Vercel execution environment sets cwd to project root (/var/task)
backend_dir = os.path.join(os.getcwd(), 'backend')
if not os.path.exists(backend_dir):
    # Fallback to __file__ resolution just in case
    backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app

# Vercel requires the WSGI application to be named 'app' or 'handler'
handler = app
