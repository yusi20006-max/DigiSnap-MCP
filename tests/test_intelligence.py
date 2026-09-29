from decimal import Decimal

from digisnap_mcp.intelligence import ShoppingIntelligence, ShoppingPolicy
from digisnap_mcp.models import Offer, Seller, Store


def make_offer(store_id, offer_id, price, available=True, warranty=None, rating=None, regular_price=None, currency="IRR"):
    store = Store(store_id, store_id.title())
    seller = Seller(f"{store_id}-seller", "Seller", rating)
    return Offer(offer_id, store, seller, Decimal(price), currency=currency, available=available, warranty=warranty, regular_price=Decimal(regular_price) if regular_price else None)


def test_best_price_filters_unavailable():
    offers = (make_offer("digikala", "cheap", "90"), make_offer("snappshop", "soldout", "50", False))
    assert ShoppingIntelligence.best_price(offers).id == "cheap"


def test_best_price_rejects_mixed_currency():
    offers = (make_offer("digikala", "irr", "90"), make_offer("snappshop", "usd", "10", currency="USD"))
    assert ShoppingIntelligence.best_price(offers) is None


def test_filters_warranty_and_seller_rating():
    offers = (make_offer("digikala", "a", "90", rating=4.0), make_offer("snappshop", "b", "80", warranty="Warranty", rating=4.8))
    policy = ShoppingPolicy(require_warranty=True, minimum_seller_rating=4.5)
    assert ShoppingIntelligence.best_price(offers, policy).id == "b"


def test_discount_uses_observed_regular_price():
    item = make_offer("digikala", "a", "80", regular_price="100")
    assert ShoppingIntelligence.analyze_offer(item).discount_percentage == Decimal("20")


def test_best_value_follows_explicit_priority():
    offers = (make_offer("digikala", "cheap", "80"), make_offer("snappshop", "warranty", "85", warranty="Valid", rating=4.9))
    result = ShoppingIntelligence.best_value(offers, ShoppingPolicy(priority=("warranty", "price", "seller_rating")))
    assert result is not None
    assert result.offer.id == "warranty"
    assert "selected_by_explicit_policy" in result.reasons
