import pytest

from digisnap_mcp.adapters import AdapterRegistry, StoreAdapter
from digisnap_mcp.models import Product, Store


class FakeAdapter(StoreAdapter):
    store_id = "fake"
    store_name = "Fake"

    def search(self, query: str, *, limit: int = 20):
        return ()

    def get_product(self, product_id: str) -> Product:
        return Product(product_id, f"Product {product_id}", Store("fake", "Fake"))


def test_registry_registers_and_retrieves_adapter() -> None:
    registry = AdapterRegistry()
    adapter = FakeAdapter()
    registry.register(adapter)
    assert registry.ids() == ("fake",)
    assert registry.get("FAKE") is adapter


def test_registry_rejects_duplicates() -> None:
    registry = AdapterRegistry()
    registry.register(FakeAdapter())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeAdapter())


def test_unknown_store_is_explicit() -> None:
    registry = AdapterRegistry()
    with pytest.raises(KeyError, match="unknown store"):
        registry.get("missing")
