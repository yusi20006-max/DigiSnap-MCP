from urllib.error import URLError
from urllib.request import Request

import pytest

from digisnap_mcp.transport import RequestPacer, ResponseCache, TransportError, request_json


class Response:
    def __init__(self, status=200, body=b'{"ok": true}', headers=None):
        self.status = status
        self.body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_transport_retries_transient_status():
    calls = []

    def opener(request: Request, timeout: float):
        calls.append(timeout)
        if len(calls) == 1:
            return Response(503)
        return Response()

    result = request_json(
        opener, Request("https://example.test"), timeout=1, backoff=0, pace=None
    )
    assert result == {"ok": True}
    assert len(calls) == 2


def test_transport_does_not_retry_invalid_json():
    def opener(request: Request, timeout: float):
        return Response(body=b"not-json")

    with pytest.raises(TransportError) as exc:
        request_json(
            opener, Request("https://example.test"), timeout=1, backoff=0, pace=None
        )
    assert exc.value.category == "invalid_json"


def test_transport_retries_network_failure():
    calls = 0

    def opener(request: Request, timeout: float):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise URLError("temporary")
        return Response()

    assert request_json(
        opener,
        Request("https://example.test"),
        timeout=1,
        retries=2,
        backoff=0,
        pace=None,
    )["ok"] is True
    assert calls == 3


def test_transport_classifies_redirect_and_preserves_location():
    def opener(request: Request, timeout: float):
        return Response(307, headers={"Location": "https://example.test/challenge"})

    with pytest.raises(TransportError) as exc:
        request_json(
            opener,
            Request("https://example.test"),
            timeout=1,
            retries=0,
            pace=None,
        )
    assert exc.value.status == 307
    assert exc.value.category == "redirect_or_challenge"
    assert exc.value.location == "https://example.test/challenge"


def test_transport_retries_rate_limit_and_honors_retry_after():
    calls = 0

    def opener(request: Request, timeout: float):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Response(429, headers={"Retry-After": "0"})
        return Response()

    assert request_json(
        opener, Request("https://example.test"), timeout=1, backoff=0, pace=None
    ) == {"ok": True}
    assert calls == 2


def test_transport_classifies_forbidden_as_blocked():
    def opener(request: Request, timeout: float):
        return Response(403)

    with pytest.raises(TransportError) as exc:
        request_json(
            opener, Request("https://example.test"), timeout=1, retries=2, pace=None
        )
    assert exc.value.category == "blocked"
    assert exc.value.retryable is False


def test_response_cache_is_ttl_bounded():
    cache = ResponseCache(ttl=60, max_entries=2)
    request = Request("https://example.test/item")
    cache.put(request, {"value": 1})
    assert cache.get(request) == {"value": 1}


def test_response_cache_only_caches_get():
    cache = ResponseCache(ttl=60)
    request = Request("https://example.test/item", method="POST")
    cache.put(request, {"value": 1})
    assert cache.get(request) is None


def test_request_pacer_zero_interval_is_noop():
    pacer = RequestPacer(0)
    pacer.wait("example.test")
