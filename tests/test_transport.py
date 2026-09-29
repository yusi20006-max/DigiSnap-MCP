from urllib.error import URLError
from urllib.request import Request

import pytest

from digisnap_mcp.transport import TransportError, request_json


class Response:
    def __init__(self, status=200, body=b'{"ok": true}'):
        self.status = status
        self.body = body

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

    result = request_json(opener, Request("https://example.test"), timeout=1, backoff=0)
    assert result == {"ok": True}
    assert len(calls) == 2


def test_transport_does_not_retry_invalid_json():
    def opener(request: Request, timeout: float):
        return Response(body=b"not-json")

    with pytest.raises(TransportError):
        request_json(opener, Request("https://example.test"), timeout=1, backoff=0)


def test_transport_retries_network_failure():
    calls = 0

    def opener(request: Request, timeout: float):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise URLError("temporary")
        return Response()

    assert request_json(opener, Request("https://example.test"), timeout=1, retries=2, backoff=0)["ok"] is True
    assert calls == 3
