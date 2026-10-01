"""HTTP transport and bounded upstream resilience primitives."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPCookieProcessor,
    ProxyHandler,
    Request,
    build_opener,
)

import socks
from sockshandler import SocksiPyHandler

logger = logging.getLogger("digisnap_mcp.transport")


@dataclass(frozen=True)
class TransportError(Exception):
    message: str
    status: int | None = None
    retryable: bool = False
    location: str | None = None
    category: str = "upstream_error"
    retry_after: float | None = None

    def __str__(self) -> str:
        return self.message


class _NoRedirect(HTTPRedirectHandler):
    """Expose upstream redirects/challenges to the resilience layer."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ResponseCache:
    """Small process-local TTL cache for successful read-only JSON responses."""

    def __init__(self, ttl: float = 30.0, max_entries: int = 128) -> None:
        self.ttl = max(0.0, ttl)
        self.max_entries = max(1, max_entries)
        self._items: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(request: Request) -> str:
        body = request.data or b""
        digest = hashlib.sha256(body).hexdigest()
        return f"{request.get_method()}|{request.full_url}|{digest}"

    def get(self, request: Request) -> dict[str, Any] | None:
        if self.ttl <= 0 or request.get_method().upper() != "GET":
            return None
        key = self._key(request)
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires, payload = item
            if expires <= now:
                self._items.pop(key, None)
                return None
            return dict(payload)

    def put(self, request: Request, payload: dict[str, Any]) -> None:
        if self.ttl <= 0 or request.get_method().upper() != "GET":
            return
        key = self._key(request)
        with self._lock:
            if len(self._items) >= self.max_entries:
                oldest = min(self._items, key=lambda item: self._items[item][0])
                self._items.pop(oldest, None)
            self._items[key] = (time.monotonic() + self.ttl, dict(payload))


class RequestPacer:
    """Host-scoped minimum interval limiter."""

    def __init__(self, interval: float = 0.5) -> None:
        self.interval = max(0.0, interval)
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        if self.interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = self.interval - (now - self._last.get(host, 0.0))
            if delay > 0:
                time.sleep(delay)
                now = time.monotonic()
            self._last[host] = now


class _GatewayHeaders(dict):
    """Minimal case-insensitive header mapping for the gateway response shim."""

    def get(self, key: str, default: Any = None) -> Any:
        wanted = key.lower()
        for name, value in self.items():
            if name.lower() == wanted:
                return value
        return default


class _GatewayResponse:
    """Adapt the restricted egress-gateway envelope to the urllib response shape."""

    def __init__(self, *, status: int, headers: dict[str, str], body: bytes) -> None:
        self.status = status
        self.code = status
        self.headers = _GatewayHeaders(headers)
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_GatewayResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class GatewayOpener:
    """Route provider requests through an authenticated restricted HTTP gateway."""

    def __init__(self, gateway_url: str, token: str, *, timeout: float = 20.0) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def __call__(self, request: Request, timeout: float | None = None) -> _GatewayResponse:
        body = request.data or b""
        payload = {
            "method": request.get_method(),
            "url": request.full_url,
            "headers": {
                name: value
                for name, value in request.header_items()
                if name.lower() not in {"host", "content-length", "authorization"}
            },
            "body_base64": __import__("base64").b64encode(body).decode("ascii") if body else None,
        }
        gateway_request = Request(
            f"{self.gateway_url}/v1/fetch",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
            method="POST",
        )
        with urlopen(gateway_request, timeout=timeout or self.timeout) as response:
            envelope = json.loads(response.read().decode("utf-8"))

        if not isinstance(envelope, dict):
            raise TransportError("egress gateway returned an invalid response envelope", category="gateway_error")

        status = envelope.get("status")
        headers = envelope.get("headers") or {}
        body_base64 = envelope.get("body_base64")
        if not isinstance(status, int) or not isinstance(headers, dict):
            raise TransportError("egress gateway returned malformed response metadata", category="gateway_error")
        try:
            body_bytes = __import__("base64").b64decode(body_base64 or "", validate=True)
        except Exception as exc:
            raise TransportError("egress gateway returned invalid body encoding", category="gateway_error") from exc

        return _GatewayResponse(
            status=status,
            headers={str(key): str(value) for key, value in headers.items()},
            body=body_bytes,
        )


def build_gateway_opener(
    gateway_url: str,
    token: str,
    *,
    timeout: float = 20.0,
) -> Callable[..., Any]:
    """Build an authenticated opener for the operator-controlled egress gateway."""
    if not gateway_url.strip():
        raise ValueError("egress gateway URL cannot be empty")
    if not token.strip():
        raise ValueError("egress gateway token cannot be empty")
    return GatewayOpener(gateway_url, token, timeout=timeout)


def build_http_opener(proxy_url: str | None = None) -> Callable[..., Any]:
    """Build an opener with optional HTTP(S)/SOCKS5 routing and cookie persistence."""
    handlers: list[Any] = [_NoRedirect()]
    if proxy_url:
        parsed = urlsplit(proxy_url)
        if parsed.scheme in {"socks5", "socks5h"}:
            if not parsed.hostname:
                raise ValueError("SOCKS5 proxy URL must include a host")
            port = parsed.port or 1080
            username = unquote(parsed.username) if parsed.username else None
            password = unquote(parsed.password) if parsed.password else None
            handlers.append(
                SocksiPyHandler(
                    socks.SOCKS5,
                    parsed.hostname,
                    port,
                    rdns=parsed.scheme == "socks5h",
                    username=username,
                    password=password,
                )
            )
        elif parsed.scheme in {"http", "https"}:
            handlers.append(ProxyHandler({"http": proxy_url, "https": proxy_url}))
        else:
            raise ValueError(
                "unsupported upstream proxy scheme; use http://, https://, socks5://, or socks5h://"
            )
    handlers.append(HTTPCookieProcessor(CookieJar()))
    return build_opener(*handlers).open

