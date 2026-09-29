"""Provider-neutral shopping intelligence over canonical offers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Protocol

from .models import Offer


@dataclass(frozen=True)
class ShoppingPolicy:
    """Explicit, configurable filtering and tie-break preferences."""

    require_available: bool = True
    require_warranty: bool = False
    minimum_seller_rating: float | None = None
    seller_ids: frozenset[str] = frozenset()
    preferred_stores: tuple[str, ...] = ()
    priority: tuple[str, ...] = ("price", "availability", "warranty", "seller_rating")


@dataclass(frozen=True)
class OfferAnalysis:
    offer: Offer
    discount_percentage: Decimal | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PriceObservation:
    """A timestamped observed price; storage remains an adapter/application concern."""

    observed_at: str
    price: Decimal
    currency: str
    offer_id: str | None = None


class PriceHistoryProvider(Protocol):
    """Optional future provider capability for historical price observations."""

    def history(self, product_id: str, *, limit: int = 30) -> tuple[PriceObservation, ...]:
        ...


class StockMonitorHook(Protocol):
    """Optional hook for applications that want to monitor stock changes."""

    def on_stock_change(self, offer: Offer) -> None:
        ...


class ShoppingIntelligence:
    """Analyze offers without opaque composite scoring."""

    @staticmethod
    def filter_offers(
        offers: Iterable[Offer],
        policy: ShoppingPolicy | None = None,
    ) -> tuple[Offer, ...]:
        policy = policy or ShoppingPolicy()
        preferred = {store.lower() for store in policy.preferred_stores}
        result: list[Offer] = []
        for offer in offers:
            if offer.price is None:
                continue
            if policy.require_available and offer.available is False:
                continue
            if policy.require_warranty and not offer.warranty:
                continue
            if policy.minimum_seller_rating is not None:
                rating = offer.seller.rating if offer.seller else None
                if rating is None or rating < policy.minimum_seller_rating:
                    continue
            if policy.seller_ids and (offer.seller is None or offer.seller.id not in policy.seller_ids):
                continue
            if preferred and offer.store.id.lower() not in preferred:
                continue
            result.append(offer)
        return tuple(result)

    @classmethod
    def best_price(
        cls,
        offers: Iterable[Offer],
        policy: ShoppingPolicy | None = None,
    ) -> Offer | None:
        candidates = cls.filter_offers(offers, policy)
        if not candidates:
            return None
        currencies = {offer.currency for offer in candidates}
        if len(currencies) > 1:
            return None
        return min(candidates, key=lambda offer: offer.price)  # type: ignore[arg-type]

    @staticmethod
    def analyze_offer(offer: Offer) -> OfferAnalysis:
        reasons: list[str] = []
        if offer.price is not None:
            reasons.append("observed_price")
        if offer.available is True:
            reasons.append("available")
        elif offer.available is False:
            reasons.append("unavailable")
        if offer.warranty:
            reasons.append("warranty")
        if offer.seller and offer.seller.rating is not None:
            reasons.append("seller_rating")
        if offer.discount_percentage is not None and offer.discount_percentage > 0:
            reasons.append("observed_discount")
        return OfferAnalysis(offer, offer.discount_percentage, tuple(reasons))

    @classmethod
    def best_value(
        cls,
        offers: Iterable[Offer],
        policy: ShoppingPolicy | None = None,
    ) -> OfferAnalysis | None:
        policy = policy or ShoppingPolicy()
        candidates = cls.filter_offers(offers, policy)
        if not candidates:
            return None
        currencies = {offer.currency for offer in candidates}
        if len(currencies) > 1:
            return None

        def key(offer: Offer) -> tuple:
            values: list[object] = []
            for criterion in policy.priority:
                if criterion == "price":
                    values.append(offer.price if offer.price is not None else Decimal("Infinity"))
                elif criterion == "availability":
                    values.append(0 if offer.available is True else 1)
                elif criterion == "warranty":
                    values.append(0 if offer.warranty else 1)
                elif criterion == "seller_rating":
                    values.append(-(offer.seller.rating or 0) if offer.seller else 0)
                elif criterion == "discount":
                    values.append(-(offer.discount_percentage or Decimal("0")))
                elif criterion == "store_preference":
                    values.append(0 if offer.store.id in policy.preferred_stores else 1)
            values.append(offer.id)
            return tuple(values)

        selected = min(candidates, key=key)
        reasons = list(ShoppingIntelligence.analyze_offer(selected).reasons)
        reasons.append("selected_by_explicit_policy")
        return OfferAnalysis(selected, selected.discount_percentage, tuple(dict.fromkeys(reasons)))
