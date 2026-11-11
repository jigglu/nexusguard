"""
Vercel Serverless Function Handler for NexusGuard FastAPI backend.
Normalizes URL paths stripped or rewritten by Vercel's Serverless Function router.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path so src and server modules resolve
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server import app as fastapi_app


async def app(scope, receive, send):
    """
    ASGI entrypoint for Vercel.
    Normalizes scope['path'] if Vercel prepends '/api/index' or '/api/index.py'.
    """
    if scope.get("type") == "http":
        path = scope.get("path", "")
        for prefix in ["/api/index.py", "/api/index", "/api.py"]:
            if path.startswith(prefix):
                path = path[len(prefix):] or "/"
                break
        scope["path"] = path
    await fastapi_app(scope, receive, send)
