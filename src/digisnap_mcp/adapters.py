"""Store adapter contract and registry."""

from abc import ABC, abstractmethod
from typing import Sequence

from .models import Product


class StoreAdapter(ABC):
    """Provider-neutral contract implemented by each shopping store."""

    store_id: str
    store_name: str

    @abstractmethod
    def search(self, query: str, *, limit: int = 20) -> Sequence[Product]:
        """Search products and return canonical Product objects."""

    @abstractmethod
    def get_product(self, product_id: str) -> Product:
        """Fetch one canonical product by provider-specific ID."""


class AdapterRegistry:
    """Registry that keeps adapters independent from comparison logic."""

    def __init__(self) -> None:
        self._adapters: dict[str, StoreAdapter] = {}

    def register(self, adapter: StoreAdapter) -> None:
        key = adapter.store_id.strip().lower()
        if not key:
            raise ValueError("adapter.store_id cannot be empty")
        if key in self._adapters:
            raise ValueError(f"adapter already registered: {key}")
        self._adapters[key] = adapter

    def get(self, store_id: str) -> StoreAdapter:
        key = store_id.strip().lower()
        try:
            return self._adapters[key]
        except KeyError as exc:
            raise KeyError(f"unknown store: {store_id}") from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
