"""Restricted Iran-side HTTP egress gateway for DigiSnap-MCP.

This service is intentionally NOT an open proxy. It accepts authenticated JSON
requests and only permits the two DigiSnap provider hosts.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener
from http.cookiejar import CookieJar

ALLOWED_HOSTS = frozenset({"api.digikala.com", "apix.snappshop.ir"})
ALLOWED_METHODS = frozenset({"GET", "POST"})
MAX_REQUEST_BODY = 2 * 1024 * 1024
MAX_RESPONSE_BODY = 8 * 1024 * 1024
TIMEOUT_SECONDS = float(os.getenv("EGRESS_UPSTREAM_TIMEOUT", "20"))
TOKEN = os.getenv("EGRESS_GATEWAY_TOKEN", "").strip()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


UPSTREAM_OPENER = build_opener(
    NoRedirect(),
    HTTPCookieProcessor(CookieJar()),
)


def validate_target(url: str) -> tuple[bool, str]:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False, "invalid URL"
    if parsed.scheme != "https":
        return False, "only https upstream URLs are allowed"
    if parsed.username or parsed.password:
        return False, "URL credentials are not allowed"
    if not parsed.hostname or parsed.hostname.lower() not in ALLOWED_HOSTS:
        return False, "upstream host is not allowlisted"
    return True, ""


def response_headers(response) -> dict[str, str]:
    allowed = {"content-type", "location", "retry-after", "server", "content-length"}
    result = {}
    for key, value in response.headers.items():
        if key.lower() in allowed:
            result[key] = value
    return result


def upstream_fetch(method: str, url: str, headers: dict[str, str], body: bytes | None) -> dict:
    ok, reason = validate_target(url)
    if not ok:
        raise ValueError(reason)
    if method not in ALLOWED_METHODS:
        raise ValueError("method is not allowed")

    request_headers = {}
    for name, value in headers.items():
        lowered = name.lower()
        if lowered in {"host", "content-length", "authorization"}:
            continue
        request_headers[str(name)] = str(value)

    request = Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with UPSTREAM_OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
            status = int(response.status)
            payload = response.read(MAX_RESPONSE_BODY + 1)
            if len(payload) > MAX_RESPONSE_BODY:
                raise ValueError("upstream response exceeds maximum size")
            return {
                "status": status,
                "headers": response_headers(response),
                "body_base64": base64.b64encode(payload).decode("ascii"),
            }
    except HTTPError as exc:
        payload = exc.read(MAX_RESPONSE_BODY + 1)
        if len(payload) > MAX_RESPONSE_BODY:
            payload = payload[:MAX_RESPONSE_BODY]
        return {
            "status": int(exc.code),
            "headers": response_headers(exc),
            "body_base64": base64.b64encode(payload).decode("ascii"),
        }
    except URLError as exc:
        raise RuntimeError(f"upstream network error: {exc}") from exc


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "DigiSnap-Iran-Egress/1.0"

    def log_message(self, format, *args):
        print(f"[gateway] {self.address_string()} {format % args}")

    def send_json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(HTTPStatus.OK, {
                "status": "healthy",
                "service": "digisnap-iran-egress-gateway",
            })
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/fetch":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        if not TOKEN:
            self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "gateway token is not configured"})
            return

        authorization = self.headers.get("Authorization", "")
        expected = f"Bearer {TOKEN}"
        if not secrets.compare_digest(authorization, expected):
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        content_length_raw = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_raw)
        except ValueError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid content length"})
            return

        if content_length < 0 or content_length > MAX_REQUEST_BODY:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request body too large"})
            return

        try:
            raw = self.rfile.read(content_length)
            envelope = json.loads(raw.decode("utf-8"))
            method = str(envelope.get("method", "")).upper()
            url = str(envelope.get("url", ""))
            headers = envelope.get("headers") or {}
            if not isinstance(headers, dict):
                raise ValueError("headers must be an object")

            body_base64 = envelope.get("body_base64")
            body = base64.b64decode(body_base64, validate=True) if body_base64 else None
            if body is not None and len(body) > MAX_REQUEST_BODY:
                raise ValueError("upstream request body too large")

            result = upstream_fetch(method, url, headers, body)
            self.send_json(HTTPStatus.OK, result)
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self.send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})


def main() -> None:
    host = os.getenv("EGRESS_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("EGRESS_PORT", "8787"))
    if not TOKEN:
        raise RuntimeError("EGRESS_GATEWAY_TOKEN must be configured")
    server = ThreadingHTTPServer((host, port), GatewayHandler)
    print(f"DigiSnap Iran egress gateway listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
