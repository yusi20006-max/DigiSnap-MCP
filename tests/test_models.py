from decimal import Decimal

from digisnap_mcp.models import Offer, Product, Seller, Specification, Store


def test_product_identity_key_is_normalized() -> None:
    store = Store("digikala", "Digikala")
    product = Product("1", "Samsung Galaxy A56", store, brand="Samsung", model=" A56 ", variant="256GB")
    assert product.comparable_key == "samsung a56 256gb samsung galaxy a56"


def test_offer_keeps_seller_and_price() -> None:
    store = Store("digikala", "Digikala")
    seller = Seller("s1", "Example Seller", 4.8)
    offer = Offer("o1", store, seller, Decimal("100000"))
    assert offer.seller == seller
    assert offer.price == Decimal("100000")


def test_specification_is_immutable() -> None:
    spec = Specification("RAM", "8 GB")
    assert spec.name == "RAM"
    assert spec.value == "8 GB"
