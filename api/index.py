"""
Vercel Serverless Function entrypoint for NexusGuard FastAPI backend.
Normalizes routing for all deployment topologies (Vercel rewrites, routes,
reverse-proxies, subpath queries, and HEAD requests).
"""

import sys
import urllib.parse
from pathlib import Path

# Add project root directory to sys.path so src and server modules resolve
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from server import app as fastapi_app


class VercelPathNormalizer:
    """
    ASGI middleware ensuring all incoming requests route to the intended
    FastAPI endpoints regardless of Vercel serverless prefixing or rewrites.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            is_head = scope.get("method") == "HEAD"
            if is_head:
                scope["method"] = "GET"

            path = scope.get("path", "")
            qs = scope.get("query_string", b"").decode("utf-8")
            params = urllib.parse.parse_qs(qs, keep_blank_values=True)

            # 1. Check query param from rewrites (e.g. ?path=app or ?__path=app)
            path_param = params.get("__path") or params.get("path")
            if path_param and path_param[0] and not (path_param[0].startswith(":") or path_param[0] == "$1"):
                path = "/" + path_param[0].lstrip("/")
                if "__path" in params:
                    del params["__path"]
                if "path" in params:
                    del params["path"]
                scope["query_string"] = urllib.parse.urlencode(params, doseq=True).encode("utf-8")
            else:
                # 2. Check Vercel edge proxy headers
                headers = dict(scope.get("headers", []))
                matched = headers.get(b"x-matched-path") or headers.get(b"x-invoke-path")
                if matched:
                    orig = matched.decode("utf-8").split("?")[0]
                    if orig and not any(orig.startswith(p) for p in ["/api/index.py", "/api/index"]):
                        path = orig

            # 3. Strip any /api/index serverless prefixes
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
                await self.asgi_app(scope, receive, head_send)
                return

        await self.asgi_app(scope, receive, send)


# Export standard `app` for Vercel discovery
app = VercelPathNormalizer(fastapi_app)
