"""
Vercel Serverless Function entrypoint for NexusGuard FastAPI backend.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path so src and server modules resolve
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server import app
