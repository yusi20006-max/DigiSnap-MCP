# DigiSnap-MCP

MCP server for comparing products, prices, sellers, availability and specifications across **Digikala** and **SnappShop**.

## Status

**Phase 3 — SnappShop Adapter implemented.**

## Registered tools

- `list_stores` — registered adapters
- `search_digikala` — search normalized Digikala products
- `get_digikala_product` — fetch normalized Digikala details
- `search_snappshop` — search normalized SnappShop products
- `get_snappshop_product` — fetch normalized SnappShop details, variants and offers
- `compare_prices` — compare canonical products from registered stores

## SnappShop adapter

The adapter targets the public JSON API surface observed at `apix.snappshop.ir`:

- `POST /search/v1` for product search
- `GET /products/v2/{product_id}` for product details
- `lat` / `lng` are configurable and appended to requests by default
- search cards normalize discounted/regular price and product links
- product details retain variants, seller/offer IDs, seller names, stock state, warranty and specifications

The upstream API is undocumented and may change. Provider-specific HTTP and payload parsing are isolated in `snappshop.py`; the core comparison layer never depends on SnappShop-specific fields.

Prices are preserved as returned by the upstream payload and currently represented as `IRR` in the canonical model. No implicit 10x Toman/Rial conversion is performed.

## Digikala adapter

The Digikala web API is also undocumented and may change. Provider-specific HTTP,
endpoint paths and payload parsing are isolated in `digikala.py`.

## Development

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
```

Run:

```bash
digisnap-mcp
```

The server currently uses MCP stdio transport.

## Roadmap

1. Core MCP Server & Architecture — complete
2. Digikala Adapter — complete
3. SnappShop Adapter — complete
4. Cross-Store Product & Offer Comparison
5. Shopping Intelligence
6. Production Hardening, CI & Release

## Design principles

- Store-specific code stays inside adapters.
- Comparison operates only on normalized domain models.
- Missing upstream data is represented as unknown, never invented.
- Product variants remain explicit.
- External-store behavior is isolated behind adapter boundaries.
