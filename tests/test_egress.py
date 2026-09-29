from urllib.request import ProxyHandler

from digisnap_mcp.transport import build_http_opener


def test_build_http_opener_direct_mode():
    opener = build_http_opener()
    assert callable(opener)


def test_build_http_opener_proxy_mode():
    opener = build_http_opener("http://proxy.example.test:8080")
    assert callable(opener)
    handlers = getattr(opener, "handlers", ())
    proxy_handlers = [handler for handler in handlers if isinstance(handler, ProxyHandler)]
    assert proxy_handlers
    assert proxy_handlers[0].proxies["http"] == "http://proxy.example.test:8080"
    assert proxy_handlers[0].proxies["https"] == "http://proxy.example.test:8080"
