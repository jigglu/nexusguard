"""
Vercel Serverless Function Handler for NexusGuard FastAPI backend.
Reads original route from Vercel's x-matched-path / x-invoke-path headers
so all routes (/, /app, /api/health, /api/pipeline/run, etc.) route correctly.
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
    Preserves original request path from Vercel's edge proxy headers.
    """
    if scope.get("type") == "http":
        headers = dict(scope.get("headers", []))
        matched = headers.get(b"x-matched-path") or headers.get(b"x-invoke-path")
        if matched:
            orig_path = matched.decode("utf-8").split("?")[0]
            if orig_path:
                scope["path"] = orig_path

        # Strip any internal serverless prefixes if fallback
        path = scope.get("path", "")
        for prefix in ["/api/index.py", "/api/index", "/api.py"]:
            if path.startswith(prefix):
                path = path[len(prefix):] or "/"
                break
        scope["path"] = path

    await fastapi_app(scope, receive, send)
