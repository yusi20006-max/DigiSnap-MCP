"""Canonical models shared by every store adapter."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Store:
    id: str
    name: str


@dataclass(frozen=True)
class Seller:
    id: str
    name: str
    rating: float | None = None


@dataclass(frozen=True)
class Specification:
    name: str
    value: str


@dataclass(frozen=True)
class Offer:
    id: str
    store: Store
    seller: Seller | None
    price: Decimal | None
    currency: str = "IRR"
    available: bool | None = None
    url: str | None = None
    warranty: str | None = None
    condition: str | None = None
    regular_price: Decimal | None = None

    @property
    def discount_percentage(self) -> Decimal | None:
        if self.regular_price is None or self.price is None or self.regular_price <= 0:
            return None
        if self.price >= self.regular_price:
            return Decimal("0")
        return (self.regular_price - self.price) / self.regular_price * Decimal("100")
    regular_price: Decimal | None = None




@dataclass(frozen=True)
class Product:
    id: str
    title: str
    store: Store
    url: str | None = None
    brand: str | None = None
    model: str | None = None
    variant: str | None = None
    specifications: tuple[Specification, ...] = ()
    offers: tuple[Offer, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def comparable_key(self) -> str:
        parts = [self.brand, self.model, self.variant, self.title]
        return " ".join(p.strip().lower() for p in parts if p).strip()
