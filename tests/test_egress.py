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
    assert captured["handlers"] == ()


def test_build_http_opener_proxy_mode(monkeypatch):
    captured = {}

    def fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return type("Opener", (), {"open": lambda *args, **kwargs: None})()

    monkeypatch.setattr(transport, "build_opener", fake_build_opener)
    opener = transport.build_http_opener("http://proxy.example.test:8080")
    assert callable(opener)
    proxy_handlers = [handler for handler in captured["handlers"] if isinstance(handler, ProxyHandler)]
    assert proxy_handlers
    assert proxy_handlers[0].proxies["http"] == "http://proxy.example.test:8080"
    assert proxy_handlers[0].proxies["https"] == "http://proxy.example.test:8080"
