import base64
import json
from urllib.request import Request

import pytest

from digisnap_mcp.transport import GatewayOpener
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gateway.server import ALLOWED_HOSTS, validate_target


def test_gateway_allowlist():
    assert validate_target("https://api.digikala.com/v3/search/?q=test")[0]
    assert validate_target("https://apix.snappshop.ir/search/v1")[0]
    assert not validate_target("https://example.com")[0]
    assert not validate_target("http://api.digikala.com/v3/search/")[0]


def test_gateway_host_allowlist_is_exact():
    assert "api.digikala.com" in ALLOWED_HOSTS
    assert "apix.snappshop.ir" in ALLOWED_HOSTS
    assert "evil.example" not in ALLOWED_HOSTS


def test_gateway_opener_decodes_envelope(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body_base64": base64.b64encode(b'{"ok":true}').decode(),
            }).encode()

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/v1/fetch")
        assert request.get_method() == "POST"
        return FakeResponse()

    monkeypatch.setattr("digisnap_mcp.transport.urlopen", fake_urlopen)

    opener = GatewayOpener("https://gateway.example", "secret")
    response = opener(
        Request("https://api.digikala.com/v3/search/?q=test"),
        timeout=5,
    )

    assert response.status == 200
    assert response.read() == b'{"ok":true}'


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://api.digikala.com/v3/search/",
        "https://user:pass@api.digikala.com/v3/search/",
    ],
)
def test_gateway_rejects_unsafe_targets(url):
    assert validate_target(url)[0] is False
