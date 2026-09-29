from decimal import Decimal

from digisnap_mcp.comparison import ComparisonEngine
from digisnap_mcp.models import Offer, Product, Seller, Store


def product(store_id: str, product_id: str, price: str) -> Product:
    store = Store(store_id, store_id.title())
    seller = Seller(f"{store_id}-seller", "Seller")
    offer = Offer(f"{store_id}-offer", store, seller, Decimal(price), available=True)
    return Product(product_id, "Test Product", store, offers=(offer,))


def test_compare_finds_lowest_price_and_delta() -> None:
    result = ComparisonEngine.compare([
        product("digikala", "d1", "100"),
        product("snappshop", "s1", "125"),
    ])
    assert result.lowest_price_offer is not None
    assert result.lowest_price_offer.store.id == "digikala"
    assert result.price_delta is not None
    assert result.price_delta.absolute == Decimal("25")
    assert result.price_delta.percentage == Decimal("25")


def test_compare_ignores_explicitly_unavailable_offers() -> None:
    p = product("digikala", "d1", "100")
    unavailable = Offer("o2", p.store, None, Decimal("1"), available=False)
    result = ComparisonEngine.compare([Product(p.id, p.title, p.store, offers=(p.offers[0], unavailable))])
    assert len(result.offers) == 1


def test_compare_handles_no_offers() -> None:
    result = ComparisonEngine.compare([Product("d1", "Test", Store("digikala", "Digikala"))])
    assert result.lowest_price_offer is None
    assert result.price_delta is None
