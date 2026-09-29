"""Provider-neutral comparison primitives."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .models import Offer, Product


@dataclass(frozen=True)
class PriceDelta:
    absolute: Decimal
    percentage: Decimal | None


@dataclass(frozen=True)
class ProductComparison:
    products: tuple[Product, ...]
    offers: tuple[Offer, ...]
    lowest_price_offer: Offer | None
    price_delta: PriceDelta | None


class ComparisonEngine:
    """Compare normalized products without knowing provider-specific details."""

    @staticmethod
    def compare(products: Iterable[Product]) -> ProductComparison:
        products = tuple(products)
        offers = tuple(
            offer
            for product in products
            for offer in product.offers
            if offer.price is not None and offer.available is not False
        )
        ordered = sorted(offers, key=lambda offer: offer.price)
        lowest = ordered[0] if ordered else None

        if len(ordered) >= 2:
            low = ordered[0].price
            high = ordered[-1].price
            assert low is not None and high is not None
            percentage = (high - low) / low * Decimal("100") if low else None
            delta = PriceDelta(high - low, percentage)
        else:
            delta = None

        return ProductComparison(products, offers, lowest, delta)
