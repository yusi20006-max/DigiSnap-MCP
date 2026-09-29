"""MCP server entry point and provider-neutral tool registration."""

import os

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .adapters import AdapterRegistry
from .comparison import ComparisonEngine
from .intelligence import ShoppingIntelligence, ShoppingPolicy
from .config import Settings
from .digikala import DigikalaAdapter
from .snappshop import SnappShopAdapter
from .transport import build_http_opener

mcp = FastMCP(
    "DigiSnap-MCP",
    host=os.getenv("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", os.getenv("FASTMCP_PORT", os.getenv("MCP_PORT", "8000")))),
)
registry = AdapterRegistry()
upstream_proxy = os.getenv("UPSTREAM_HTTP_PROXY")
upstream_opener = build_http_opener(upstream_proxy)
registry.register(DigikalaAdapter(opener=upstream_opener))
registry.register(SnappShopAdapter(opener=upstream_opener))
comparison = ComparisonEngine()
settings = Settings.from_env()


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Return a lightweight health response for deployment probes."""
    return JSONResponse({"status": "healthy", "service": "DigiSnap-MCP"})


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
        "regular_price": str(offer.regular_price) if offer.regular_price is not None else None,
        "discount_percentage": str(offer.discount_percentage) if offer.discount_percentage is not None else None,
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
        "specifications": [{"name": spec.name, "value": spec.value} for spec in product.specifications],
        "offers": [_offer_dict(offer) for offer in product.offers],
        "metadata": product.metadata,
    }


def _comparison_dict(result) -> dict:
    lowest = result.lowest_price_offer
    return {
        "products": [
            {"id": p.id, "store": p.store.id, "title": p.title, "url": p.url}
            for p in result.products
        ],
        "matched": all(match.matched for match in result.matches) if result.matches else False,
        "matches": [
            {
                "left_id": match.left.id,
                "right_id": match.right.id,
                "score": str(match.score),
                "matched": match.matched,
                "reasons": list(match.reasons),
            }
            for match in result.matches
        ],
        "lowest_price_offer": (
            {
                "store": lowest.store.id,
                "offer_id": lowest.id,
                "seller": lowest.seller.name if lowest.seller else None,
                "price": str(lowest.price),
                "currency": lowest.currency,
                "warranty": lowest.warranty,
                "available": lowest.available,
                "url": lowest.url,
            }
            if lowest
            else None
        ),
        "price_delta": (
            {
                "absolute": str(result.price_delta.absolute),
                "percentage": str(result.price_delta.percentage) if result.price_delta.percentage is not None else None,
                "currency": lowest.currency if lowest else None,
            }
            if result.price_delta
            else None
        ),
        "specification_differences": (
            [
                ComparisonEngine.specification_differences(result.products[0], result.products[1])
                if len(result.products) == 2
                else ()
            ][0]
            if len(result.products) == 2
            else ()
        ),
        "offers": [_offer_dict(offer) for offer in result.offers],
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


def _get_products(product_ids: list[str], store_ids: list[str]):
    if len(product_ids) != len(store_ids):
        raise ValueError("product_ids and store_ids must have the same length")
    if not product_ids:
        raise ValueError("at least one product is required")
    return tuple(
        registry.get(store_id).get_product(product_id)
        for product_id, store_id in zip(product_ids, store_ids)
    )


@mcp.tool()
def compare_products(product_ids: list[str], store_ids: list[str]) -> dict:
    """Compare products across stores, including identity, variants, specs and offers."""
    products = _get_products(product_ids, store_ids)
    return _comparison_dict(comparison.compare(products))


@mcp.tool()
def compare_offers(product_ids: list[str], store_ids: list[str]) -> dict:
    """Compare normalized offers across the supplied store products."""
    products = _get_products(product_ids, store_ids)
    result = comparison.compare(products)
    return {
        "matched": all(match.matched for match in result.matches) if result.matches else False,
        "offers": [_offer_dict(offer) for offer in result.offers],
        "lowest_price_offer": (
            _offer_dict(result.lowest_price_offer)
            if result.lowest_price_offer
            else None
        ),
        "price_delta": (
            {
                "absolute": str(result.price_delta.absolute),
                "percentage": str(result.price_delta.percentage) if result.price_delta.percentage is not None else None,
                "currency": result.lowest_price_offer.currency if result.lowest_price_offer else None,
            }
            if result.price_delta
            else None
        ),
    }


@mcp.tool()
def compare_prices(product_ids: list[str], store_ids: list[str]) -> dict:
    """Backward-compatible price comparison using the canonical comparison engine."""
    return compare_offers(product_ids, store_ids)


def _shopping_policy(
    *,
    require_available: bool = True,
    require_warranty: bool = False,
    minimum_seller_rating: float | None = None,
    seller_ids: list[str] | None = None,
    preferred_stores: list[str] | None = None,
    priority: list[str] | None = None,
) -> ShoppingPolicy:
    return ShoppingPolicy(
        require_available=require_available,
        require_warranty=require_warranty,
        minimum_seller_rating=minimum_seller_rating,
        seller_ids=frozenset(seller_ids or ()),
        preferred_stores=tuple(preferred_stores or ()),
        priority=tuple(priority or ("price", "availability", "warranty", "seller_rating")),
    )


@mcp.tool()
def find_best_price(
    product_ids: list[str],
    store_ids: list[str],
    require_available: bool = True,
    require_warranty: bool = False,
    minimum_seller_rating: float | None = None,
    seller_ids: list[str] | None = None,
) -> dict:
    """Find the lowest comparable observed offer under explicit filters."""
    products = _get_products(product_ids, store_ids)
    policy = _shopping_policy(
        require_available=require_available,
        require_warranty=require_warranty,
        minimum_seller_rating=minimum_seller_rating,
        seller_ids=seller_ids,
    )
    offers = [offer for product in products for offer in product.offers]
    selected = ShoppingIntelligence.best_price(offers, policy)
    return {
        "found": selected is not None,
        "offer": _offer_dict(selected) if selected else None,
        "selection": "lowest_observed_price",
        "currency_safe": selected is not None,
    }


@mcp.tool()
def find_best_value(
    product_ids: list[str],
    store_ids: list[str],
    priority: list[str] | None = None,
    require_available: bool = True,
    require_warranty: bool = False,
    minimum_seller_rating: float | None = None,
    seller_ids: list[str] | None = None,
) -> dict:
    """Select an offer using an explicit, ordered policy rather than a hidden score."""
    products = _get_products(product_ids, store_ids)
    policy = _shopping_policy(
        require_available=require_available,
        require_warranty=require_warranty,
        minimum_seller_rating=minimum_seller_rating,
        seller_ids=seller_ids,
        priority=priority,
    )
    offers = [offer for product in products for offer in product.offers]
    analysis = ShoppingIntelligence.best_value(offers, policy)
    return {
        "found": analysis is not None,
        "offer": _offer_dict(analysis.offer) if analysis else None,
        "discount_percentage": str(analysis.discount_percentage) if analysis and analysis.discount_percentage is not None else None,
        "reasons": list(analysis.reasons) if analysis else [],
        "priority": list(policy.priority),
    }


@mcp.tool()
def analyze_offers(
    product_ids: list[str],
    store_ids: list[str],
) -> list[dict]:
    """Expose observed discount, availability, warranty and seller signals without ranking."""
    products = _get_products(product_ids, store_ids)
    offers = [offer for product in products for offer in product.offers]
    return [
        {
            **_offer_dict(offer),
            "reasons": list(ShoppingIntelligence.analyze_offer(offer).reasons),
        }
        for offer in offers
    ]


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport in {"streamable-http", "http"}:
        mcp.run(transport="streamable-http")
        return
    mcp.run()


if __name__ == "__main__":
    main()
