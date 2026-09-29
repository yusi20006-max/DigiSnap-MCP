from decimal import Decimal

from digisnap_mcp.comparison import ComparisonEngine
from digisnap_mcp.models import Offer, Product, Seller, Specification, Store


def product(store_id, product_id, title, price, *, brand=None, model=None, variant=None, specs=()):
    store = Store(store_id, store_id.title())
    offer = Offer(f"{store_id}-offer", store, Seller(f"{store_id}-seller", "Seller"), Decimal(price), available=True)
    return Product(product_id, title, store, brand=brand, model=model, variant=variant, specifications=specs, offers=(offer,))


def test_same_product_is_matched_across_stores():
    left = product("digikala", "d1", "Samsung Galaxy A07 128GB", "330", brand="Samsung", model="A07", variant="Black", specs=(Specification("Storage", "128GB"),))
    right = product("snappshop", "s1", "Samsung Galaxy A07 128 GB", "350", brand="Samsung", model="A07", variant="Black", specs=(Specification("Storage", "128GB"),))
    match = ComparisonEngine.match_products(left, right)
    assert match.matched is True
    assert match.score >= Decimal("0.72")


def test_different_variants_are_not_merged():
    left = product("digikala", "d1", "Galaxy A07", "330", brand="Samsung", model="A07", variant="Black")
    right = product("snappshop", "s1", "Galaxy A07", "340", brand="Samsung", model="A07", variant="Green")
    match = ComparisonEngine.match_products(left, right)
    assert match.matched is False
    assert "variant_mismatch" in match.reasons


def test_specification_differences_are_explicit():
    left = product("digikala", "d1", "Galaxy A07", "330", specs=(Specification("Storage", "128GB"), Specification("RAM", "4GB")))
    right = product("snappshop", "s1", "Galaxy A07", "340", specs=(Specification("Storage", "256GB"),))
    differences = ComparisonEngine.specification_differences(left, right)
    assert {"name": "Storage", "left": "128GB", "right": "256GB"} in differences
    assert {"name": "RAM", "left": "4GB", "right": None} in differences


def test_cross_store_compare_contains_match_and_price_delta():
    left = product("digikala", "d1", "Galaxy A07", "330", brand="Samsung", model="A07")
    right = product("snappshop", "s1", "Galaxy A07", "350", brand="Samsung", model="A07")
    result = ComparisonEngine.compare([left, right])
    assert result.matches[0].matched is True
    assert result.price_delta.absolute == Decimal("20")


def test_currency_mismatch_does_not_create_delta():
    left = product("digikala", "d1", "Galaxy A07", "330")
    store = Store("snappshop", "SnappShop")
    right_offer = Offer("o2", store, None, Decimal("350"), currency="USD", available=True)
    right = Product("s1", "Galaxy A07", store, offers=(right_offer,))
    result = ComparisonEngine.compare([left, right])
    assert result.price_delta is None
