"""
Vercel Serverless Function Handler for NexusGuard FastAPI backend.
Routes all sub-paths (/, /app, /api/health, /api/pipeline/run, etc.)
accurately using the __path query parameter populated by Vercel rewrites.
Also supports HEAD requests cleanly for uptime checks and crawlers.
"""

import sys
import urllib.parse
from pathlib import Path

# Add project root directory to sys.path so src and server modules resolve
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server import app as fastapi_app


async def app(scope, receive, send):
    """
    ASGI entrypoint for Vercel.
    Extracts the original request path from __path query param or fallback headers.
    """
    if scope.get("type") == "http":
        # Gracefully handle HEAD requests
        is_head = scope.get("method") == "HEAD"
        if is_head:
            scope["method"] = "GET"

        # 1. Check if __path was passed via Vercel rewrite
        qs = scope.get("query_string", b"").decode("utf-8")
        params = urllib.parse.parse_qs(qs, keep_blank_values=True)

        if "__path" in params:
            raw_path = params["__path"][0]
            target_path = "/" + raw_path.lstrip("/")
            scope["path"] = target_path
            scope["raw_path"] = target_path.encode("utf-8")
            del params["__path"]
            scope["query_string"] = urllib.parse.urlencode(params, doseq=True).encode("utf-8")
        else:
            # Fallback: check headers or strip /api/index prefix
            headers = dict(scope.get("headers", []))
            matched = headers.get(b"x-matched-path") or headers.get(b"x-invoke-path")
            if matched:
                orig = matched.decode("utf-8").split("?")[0]
                if orig and not (orig.startswith("/api/index") or orig.startswith("/api/index.py")):
                    scope["path"] = orig
                    scope["raw_path"] = orig.encode("utf-8")
            else:
                path = scope.get("path", "")
                for prefix in ["/api/index.py", "/api/index", "/api.py"]:
                    if path.startswith(prefix):
                        path = path[len(prefix):] or "/"
                        break
                scope["path"] = path
                scope["raw_path"] = path.encode("utf-8")

        if is_head:
            async def head_send(message):
                if message.get("type") == "http.response.body":
                    message = {"type": "http.response.body", "body": b"", "more_body": False}
                await send(message)
            await fastapi_app(scope, receive, head_send)
            return

    await fastapi_app(scope, receive, send)
