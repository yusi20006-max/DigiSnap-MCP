# DigiSnap-MCP

MCP server for comparing products, prices, sellers, availability and specifications across **Digikala** and **SnappShop**.

## Status

**Phase 4 — Cross-Store Product & Offer Comparison implemented.**

## Registered tools

- `list_stores` — registered adapters
- `search_digikala` — search normalized Digikala products
- `get_digikala_product` — fetch normalized Digikala details
- `search_snappshop` — search normalized SnappShop products
- `get_snappshop_product` — fetch normalized SnappShop details, variants and offers
- `compare_products` — identity, variant, specification and offer comparison
- `compare_offers` — normalized offer and price comparison
- `compare_prices` — backward-compatible price comparison

## Cross-store comparison

Phase 4 keeps provider-specific fields inside adapters and compares only canonical models.

The comparison layer provides:

- product identity matching with an explainable similarity score
- explicit variant mismatch detection
- brand/model/title signals
- shared specification comparison
- explicit specification differences
- seller, warranty, condition and availability fields on offers
- lowest available offer
- absolute and percentage price delta
- purchase URLs
- currency-safe price deltas: a monetary delta is omitted when the comparable offers use different currencies
- missing values remain unknown rather than being inferred

A match is a comparison signal, not an assertion of identity. Consumers can inspect `matched`, `score` and `reasons` before using a cross-store result.

## Provider adapters

### SnappShop

The adapter targets the public JSON API surface observed at `apix.snappshop.ir`:

- `POST /search/v1` for product search
- `GET /products/v2/{product_id}` for product details

The upstream API is undocumented and may change. Provider-specific HTTP and payload parsing are isolated in `snappshop.py`.

### Digikala

The Digikala web API is also undocumented and may change. Provider-specific HTTP, endpoint paths and payload parsing are isolated in `digikala.py`.

Prices are preserved as returned by the upstream payload and currently represented as `IRR` in the canonical model. No implicit 10x Toman/Rial conversion is performed.

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
4. Cross-Store Product & Offer Comparison — complete
5. Shopping Intelligence
6. Production Hardening, CI & Release

## Design principles

- Store-specific code stays inside adapters.
- Comparison operates only on normalized domain models.
- Missing upstream data is represented as unknown, never invented.
- Product variants remain explicit.
- External-store behavior is isolated behind adapter boundaries.
