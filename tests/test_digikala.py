import json
from decimal import Decimal

from digisnap_mcp.digikala import DigikalaAdapter
from digisnap_mcp.errors import RateLimitError


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def opener_for(payload, status=200, seen=None):
    def opener(request, timeout):
        if seen is not None:
            seen.append(request.full_url)
        return FakeResponse(payload, status)

    return opener


def test_search_normalizes_product_and_seller():
    seen = []
    payload = {
        "data": {"products": [{
            "id": 123, "title": "Galaxy A56", "brand": {"title": "Samsung"},
            "url": "https://www.digikala.com/product/dkp-123/",
            "offers": [{"id": 7, "selling_price": 25000000, "available": True,
                        "seller": {"id": 9, "name": "Seller A", "rating": 4.7}}]
        }]}
    }
    adapter = DigikalaAdapter(
        base_url="https://example.test",
        opener=opener_for(payload, seen=seen),
    )
    result = adapter.search("Galaxy A56")
    assert seen[0] == "https://example.test/v3/search/?q=Galaxy+A56&page=1"
    assert result[0].id == "123"
    assert result[0].brand == "Samsung"
    assert result[0].offers[0].price == Decimal("25000000")
    assert result[0].offers[0].seller.name == "Seller A"


def test_product_normalizes_specs_and_direct_price():
    seen = []
    payload = {
        "data": {"product": {"id": 123, "title": "Test", "price": 1000,
                             "specifications": [{"name": "RAM", "value": "8 GB"}]}}
    }
    adapter = DigikalaAdapter(
        base_url="https://example.test",
        opener=opener_for(payload, seen=seen),
    )
    result = adapter.get_product("123")
    assert seen[0] == "https://example.test/v2/product/123/"
    assert result.specifications[0].name == "RAM"
    assert result.offers[0].price == Decimal("1000")


def test_rate_limit_is_explicit():
    adapter = DigikalaAdapter(base_url="https://example.test", opener=opener_for({}, 429))
    try:
        adapter.get_product("1")
    except RateLimitError:
        return
    raise AssertionError("expected RateLimitError")
