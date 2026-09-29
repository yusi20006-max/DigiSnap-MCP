"""MCP server entry point and provider-neutral tool registration."""

from mcp.server.fastmcp import FastMCP

from .adapters import AdapterRegistry
from .comparison import ComparisonEngine
from .config import Settings

mcp = FastMCP("DigiSnap-MCP")
registry = AdapterRegistry()
comparison = ComparisonEngine()
settings = Settings.from_env()


@mcp.tool()
def list_stores() -> list[str]:
    """List currently registered shopping-store adapters."""
    return list(registry.ids())


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
        "products": [
            {"id": p.id, "store": p.store.id, "title": p.title}
            for p in result.products
        ],
        "lowest_price": (
            {
                "store": result.lowest_price_offer.store.id,
                "seller": (
                    result.lowest_price_offer.seller.name
                    if result.lowest_price_offer.seller
                    else None
                ),
                "price": str(result.lowest_price_offer.price),
                "currency": result.lowest_price_offer.currency,
            }
            if result.lowest_price_offer
            else None
        ),
        "price_delta": (
            {
                "absolute": str(result.price_delta.absolute),
                "percentage": (
                    str(result.price_delta.percentage)
                    if result.price_delta.percentage is not None
                    else None
                ),
            }
            if result.price_delta
            else None
        ),
    }


def main() -> None:
    """Run the MCP server over the default stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
