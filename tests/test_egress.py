from urllib.request import ProxyHandler

import digisnap_mcp.transport as transport


def test_build_http_opener_direct_mode(monkeypatch):
    captured = {}

    def fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return type("Opener", (), {"open": lambda *args, **kwargs: None})()

    monkeypatch.setattr(transport, "build_opener", fake_build_opener)
    opener = transport.build_http_opener()
    assert callable(opener)
    assert len(captured["handlers"]) == 2


def test_build_http_opener_http_proxy_mode(monkeypatch):
    captured = {}

    def fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return type("Opener", (), {"open": lambda *args, **kwargs: None})()

    monkeypatch.setattr(transport, "build_opener", fake_build_opener)
    opener = transport.build_http_opener("http://proxy.example.test:8080")
    assert callable(opener)
    cookie_handlers = [handler for handler in captured["handlers"] if isinstance(handler, transport.HTTPCookieProcessor)]
    assert cookie_handlers
    proxy_handlers = [
        handler for handler in captured["handlers"] if isinstance(handler, ProxyHandler)
    ]
    assert proxy_handlers
    assert proxy_handlers[0].proxies["http"] == "http://proxy.example.test:8080"
    assert proxy_handlers[0].proxies["https"] == "http://proxy.example.test:8080"


def test_build_http_opener_socks5h_mode(monkeypatch):
    captured = {}

    class FakeSocksiPyHandler:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    def fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return type("Opener", (), {"open": lambda *args, **kwargs: None})()

    monkeypatch.setattr(transport, "SocksiPyHandler", FakeSocksiPyHandler)
    monkeypatch.setattr(transport, "build_opener", fake_build_opener)

    opener = transport.build_http_opener("socks5h://user:pass@proxy.example.test:1081")

    assert callable(opener)
    assert captured["args"] == (
        transport.socks.SOCKS5,
        "proxy.example.test",
        1081,
    )
    assert captured["kwargs"] == {
        "rdns": True,
        "username": "user",
        "password": "pass",
    }
    assert any(isinstance(handler, FakeSocksiPyHandler) for handler in captured["handlers"])
    assert any(isinstance(handler, transport.HTTPCookieProcessor) for handler in captured["handlers"])


def test_build_http_opener_socks5_mode_uses_local_dns(monkeypatch):
    captured = {}

    class FakeSocksiPyHandler:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    def fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return type("Opener", (), {"open": lambda *args, **kwargs: None})()

    monkeypatch.setattr(transport, "SocksiPyHandler", FakeSocksiPyHandler)
    monkeypatch.setattr(transport, "build_opener", fake_build_opener)

    opener = transport.build_http_opener("socks5://proxy.example.test:1080")

    assert callable(opener)
    assert captured["args"] == (
        transport.socks.SOCKS5,
        "proxy.example.test",
        1080,
    )
    assert captured["kwargs"] == {
        "rdns": False,
        "username": None,
        "password": None,
    }


def test_build_http_opener_rejects_unknown_scheme():
    try:
        transport.build_http_opener("ftp://proxy.example.test:21")
    except ValueError as exc:
        assert "unsupported upstream proxy scheme" in str(exc)
    else:
        raise AssertionError("expected ValueError")
