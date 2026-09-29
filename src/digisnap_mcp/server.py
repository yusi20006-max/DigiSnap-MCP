"""MCP server entry point and provider-neutral tool registration."""

from mcp.server.fastmcp import FastMCP

from .adapters import AdapterRegistry
from .comparison import ComparisonEngine
from .config import Settings
from .digikala import DigikalaAdapter
from .snappshop import SnappShopAdapter

mcp = FastMCP("DigiSnap-MCP")
registry = AdapterRegistry()
registry.register(DigikalaAdapter())
registry.register(SnappShopAdapter())
comparison = ComparisonEngine()
settings = Settings.from_env()


def _offer_dict(offer) -> dict:
    return {
        "id": offer.id,
        "price": str(offer.price) if offer.price is not None else None,
        "currency": offer.currency,
        "available": offer.available,
        "seller": offer.seller.name if offer.seller else None,
        "seller_id": offer.seller.id if offer.seller else None,
        "warranty": offer.warranty,
        "condition": offer.condition,
        "url": offer.url,
    }


def _product_dict(product) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "store": product.store.id,
        "brand": product.brand,
        "model": product.model,
        "variant": product.variant,
        "url": product.url,
        "specifications": [
            {"name": spec.name, "value": spec.value}
            for spec in product.specifications
        ],
        "offers": [_offer_dict(offer) for offer in product.offers],
        "metadata": product.metadata,
    }


@mcp.tool()
def list_stores() -> list[str]:
    """List currently registered shopping-store adapters."""
    return list(registry.ids())


@mcp.tool()
def search_digikala(query: str, limit: int = 10) -> list[dict]:
    """Search Digikala and return normalized products."""
    return [_product_dict(p) for p in registry.get("digikala").search(query, limit=limit)]


@mcp.tool()
def get_digikala_product(product_id: str) -> dict:
    """Get one normalized Digikala product."""
    return _product_dict(registry.get("digikala").get_product(product_id))


@mcp.tool()
def search_snappshop(query: str, limit: int = 10) -> list[dict]:
    """Search SnappShop and return normalized products."""
    return [_product_dict(p) for p in registry.get("snappshop").search(query, limit=limit)]


@mcp.tool()
def get_snappshop_product(product_id: str) -> dict:
    """Get one normalized SnappShop product with variants and offers."""
    return _product_dict(registry.get("snappshop").get_product(product_id))


@mcp.tool()
def compare_prices(product_ids: list[str], store_ids: list[str]) -> dict:
    """Compare normalized products supplied by registered store adapters."""
    if len(product_ids) != len(store_ids):
        raise ValueError("product_ids and store_ids must have the same length")
    products = [
        registry.get(store_id).get_product(product_id)
        for product_id, store_id in zip(product_ids, store_ids)
    ]
    result = comparison.compare(products)
    return {
        "products": [{"id": p.id, "store": p.store.id, "title": p.title} for p in result.products],
        "lowest_price": ({
            "store": result.lowest_price_offer.store.id,
            "seller": result.lowest_price_offer.seller.name if result.lowest_price_offer.seller else None,
            "price": str(result.lowest_price_offer.price),
            "currency": result.lowest_price_offer.currency,
        } if result.lowest_price_offer else None),
        "price_delta": ({
            "absolute": str(result.price_delta.absolute),
            "percentage": str(result.price_delta.percentage) if result.price_delta.percentage is not None else None,
        } if result.price_delta else None),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
