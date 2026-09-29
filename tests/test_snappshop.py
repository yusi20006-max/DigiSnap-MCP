import json

import pytest

from digisnap_mcp.errors import RateLimitError
from digisnap_mcp.snappshop import SnappShopAdapter


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def opener_factory(payload, status=200, seen=None):
    def opener(request, timeout):
        if seen is not None:
            seen.append((request.full_url, request.get_header("User-agent"), request.get_header("Origin")))
        return FakeResponse(payload, status)

    return opener


def test_search_normalizes_snappshop_cards():
    payload = {
        "data": {
            "structure": [{
                "section_type": "plp",
                "items": [{
                    "id": "42yeLw",
                    "title": "Samsung Galaxy A07",
                    "price": {"price": 49000000, "discounted_price": 33980000},
                    "href": "/product/snp-25751584",
                    "state": {"rate": 4.5, "rate_count": 12},
                }],
            }]
        }
    }
    seen = []
    product = SnappShopAdapter(opener=opener_factory(payload, seen=seen)).search("Galaxy", limit=1)[0]
    assert seen[0][0] == "https://apix.snappshop.ir/search/v1?lat=35.77331&lng=51.418591"
    assert seen[0][2] == "https://snappshop.ir"
    assert product.id == "42yeLw"
    assert product.store.id == "snappshop"
    assert product.offers[0].price == 33980000
    assert product.offers[0].currency == "IRR"
    assert product.url == "https://snappshop.ir/product/snp-25751584"


def test_product_normalizes_variants_sellers_specs_and_best_offer():
    payload = {
        "data": {
            "id": "42yeLw",
            "content": {"title_fa": "Samsung Galaxy A07"},
            "brand": {"title_fa": "سامسونگ"},
            "configurable_attribute": [{
                "id": "color",
                "type": "color",
                "title": "رنگ",
                "value": {"id": "black", "title": "مشکی"},
            }, {
                "id": "color",
                "type": "color",
                "title": "رنگ",
                "value": {"id": "green", "title": "سبز"},
            }],
            "variants": [{
                "variation_id": "v1",
                "attribute_ids": [{"attribute_value_id": "black"}],
                "vendor": [{
                    "vendor_product_info_id": "offer-1",
                    "vendor_id": "seller-1",
                    "price": 50000000,
                    "special_price": 45000000,
                    "stock": 2,
                    "is_available_in_vendor_inventory": True,
                    "warranty_id": "w1",
                }, {
                    "vendor_product_info_id": "offer-2",
                    "vendor_id": "seller-2",
                    "price": 47000000,
                    "special_price": 0,
                    "stock": 1,
                    "is_available_in_vendor_inventory": True,
                }],
            }],
            "vendors": [
                {"id": "seller-1", "title": "فروشنده اول"},
                {"id": "seller-2", "title": "فروشنده دوم"},
            ],
            "warranties": [{"id": "w1", "name": "گارانتی 18 ماهه"}],
            "attributes": [{"title": "حافظه", "value": "128GB"}],
        }
    }
    product = SnappShopAdapter(opener=opener_factory(payload)).get_product("42yeLw")
    assert product.brand == "سامسونگ"
    assert product.variant == "مشکی"
    assert product.specifications[0].value == "128GB"
    assert len(product.offers) == 2
    assert product.offers[0].seller.name == "فروشنده اول"
    assert product.offers[0].price == 45000000
    assert product.offers[0].warranty == "گارانتی 18 ماهه"
    assert product.offers[0].available is True


def test_rate_limit_is_explicit():
    with pytest.raises(RateLimitError):
        SnappShopAdapter(opener=opener_factory({}, status=429)).search("phone")


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        SnappShopAdapter(opener=opener_factory({})).search("   ")
