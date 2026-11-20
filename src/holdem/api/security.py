"""Guards for a server that one person runs on their own machine, with no login.

The risk is a web page open in another tab. It can make the browser send requests to this server,
and with DNS rebinding it can even read the replies. Three checks stop that:

* the ``Host`` header must be an IP address or ``localhost`` (a rebinding attack needs a domain
  name there); extra names can be allowed with ``HOLDEM_ALLOWED_HOSTS``;
* a request that changes something must come from this app's own pages (``Origin`` matches);
* request bodies are small.

Every reply also carries headers that stop framing, content sniffing and foreign scripts.
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

MAX_BODY_BYTES = 64 * 1024
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def host_name(host: str) -> str:
    """The name part of a ``Host`` header: no port, no IPv6 brackets, lower case."""
    host = host.strip().lower()
    if host.startswith("["):
        return host[1:].partition("]")[0]
    return host.rpartition(":")[0] if host.count(":") == 1 else host


def extra_hosts() -> frozenset[str]:
    names = os.environ.get("HOLDEM_ALLOWED_HOSTS", "").split(",")
    return frozenset(name.strip().lower() for name in names if name.strip())


def host_allowed(host: str, extra: frozenset[str]) -> bool:
    name = host_name(host)
    if name == "localhost" or name in extra:
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


def same_origin(origin: str, host: str) -> bool:
    return urlsplit(origin).netloc.lower() == host.strip().lower()


def _refuse(status: int, detail: str) -> Response:
    return JSONResponse({"detail": detail}, status_code=status, headers=HEADERS)


def add_guards(app: FastAPI) -> None:
    extra = extra_hosts()

    @app.middleware("http")
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        host = request.headers.get("host", "")
        if not host_allowed(host, extra):
            return _refuse(400, "unknown host")
        api = request.url.path.startswith("/api/")
        if api and request.headers.get("sec-fetch-site") == "cross-site":
            return _refuse(403, "requests from other sites are not allowed")
        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and not same_origin(origin, host):
                return _refuse(403, "requests from other sites are not allowed")
            if "transfer-encoding" in request.headers:
                return _refuse(411, "send a Content-Length")
            length = request.headers.get("content-length", "0")
            if not length.isdigit() or int(length) > MAX_BODY_BYTES:
                return _refuse(413, "request body too large")
        response = await call_next(request)
        for name, value in HEADERS.items():
            response.headers.setdefault(name, value)
        if api:
            response.headers.setdefault("Cache-Control", "no-store")
        return response
