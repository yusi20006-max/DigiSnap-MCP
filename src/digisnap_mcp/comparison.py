"""Cross-store product identity and offer comparison."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Iterable

from .models import Offer, Product

_STOPWORDS = {"the", "and", "with", "for", "new", "original", "سامسونگ", "گوشی", "موبایل"}


@dataclass(frozen=True)
class ProductMatch:
    left: Product
    right: Product
    score: Decimal
    matched: bool
    reasons: tuple[str, ...]


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
    matches: tuple[ProductMatch, ...] = ()


class ComparisonEngine:
    """Compare canonical products while keeping identity matching explicit."""

    @staticmethod
    def _tokens(value: str | None) -> set[str]:
        if not value:
            return set()
        normalized = value.lower().replace("‌", " ")
        return {
            token for token in re.findall(r"[\w]+", normalized, flags=re.UNICODE)
            if token not in _STOPWORDS and len(token) > 1
        }

    @classmethod
    def _similarity(cls, left: str | None, right: str | None) -> float:
        if not left or not right:
            return 0.0
        lt, rt = cls._tokens(left), cls._tokens(right)
        if lt and rt:
            overlap = len(lt & rt) / max(len(lt), len(rt))
            sequence = SequenceMatcher(None, " ".join(sorted(lt)), " ".join(sorted(rt))).ratio()
            return max(overlap, sequence)
        return SequenceMatcher(None, left.lower(), right.lower()).ratio()

    @classmethod
    def match_products(
        cls,
        left: Product,
        right: Product,
        *,
        threshold: Decimal = Decimal("0.72"),
    ) -> ProductMatch:
        reasons: list[str] = []
        scores: list[float] = []

        if left.brand and right.brand:
            brand_score = cls._similarity(left.brand, right.brand)
            scores.append(brand_score)
            if brand_score >= 0.9:
                reasons.append("brand")
            elif brand_score < 0.5:
                return ProductMatch(left, right, Decimal("0"), False, ("brand_mismatch",))

        if left.model and right.model:
            model_score = cls._similarity(left.model, right.model)
            scores.append(model_score)
            if model_score >= 0.9:
                reasons.append("model")

        title_score = cls._similarity(left.title, right.title)
        scores.append(title_score)
        if title_score >= 0.72:
            reasons.append("title")

        if left.variant and right.variant:
            variant_score = cls._similarity(left.variant, right.variant)
            scores.append(variant_score)
            if variant_score >= 0.9:
                reasons.append("variant")
            elif variant_score < 0.5:
                return ProductMatch(left, right, Decimal("0"), False, ("variant_mismatch",))

        left_specs = {s.name.lower(): s.value.lower() for s in left.specifications}
        right_specs = {s.name.lower(): s.value.lower() for s in right.specifications}
        common = set(left_specs) & set(right_specs)
        if common:
            equal = sum(
                cls._similarity(left_specs[name], right_specs[name]) >= 0.85
                for name in common
            )
            spec_score = equal / len(common)
            scores.append(spec_score)
            if spec_score >= 0.8:
                reasons.append("specifications")
            elif spec_score < 0.5:
                return ProductMatch(left, right, Decimal("0"), False, ("specification_mismatch",))

        score = sum(scores) / len(scores) if scores else 0.0
        matched = Decimal(str(round(score, 4))) >= threshold
        if not matched:
            reasons.append("low_similarity")
        return ProductMatch(left, right, Decimal(str(round(score, 4))), matched, tuple(dict.fromkeys(reasons)))

    @staticmethod
    def _available_offers(products: Iterable[Product]) -> tuple[Offer, ...]:
        return tuple(
            offer
            for product in products
            for offer in product.offers
            if offer.price is not None and offer.available is not False
        )

    @classmethod
    def compare(cls, products: Iterable[Product]) -> ProductComparison:
        products = tuple(products)
        offers = cls._available_offers(products)
        ordered = sorted(offers, key=lambda offer: offer.price)
        lowest = ordered[0] if ordered else None

        delta = None
        if len(ordered) >= 2:
            currencies = {offer.currency for offer in ordered}
            if len(currencies) == 1:
                low = ordered[0].price
                high = ordered[-1].price
                assert low is not None and high is not None
                percentage = (high - low) / low * Decimal("100") if low else None
                delta = PriceDelta(high - low, percentage)

        matches: list[ProductMatch] = []
        if len(products) == 2 and products[0].store.id != products[1].store.id:
            matches.append(cls.match_products(products[0], products[1]))
        return ProductComparison(products, offers, lowest, delta, tuple(matches))

    @staticmethod
    def specification_differences(left: Product, right: Product) -> tuple[dict[str, str | None], ...]:
        left_specs = {s.name.strip().lower(): s for s in left.specifications}
        right_specs = {s.name.strip().lower(): s for s in right.specifications}
        differences = []
        for name in sorted(set(left_specs) | set(right_specs)):
            lv, rv = left_specs.get(name), right_specs.get(name)
            if lv is None or rv is None or lv.value.strip().lower() != rv.value.strip().lower():
                differences.append({
                    "name": lv.name if lv else rv.name,
                    "left": lv.value if lv else None,
                    "right": rv.value if rv else None,
                })
        return tuple(differences)
