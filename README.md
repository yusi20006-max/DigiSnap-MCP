# DigiSnap-MCP

MCP server for comparing products, prices, sellers, availability and specifications across **Digikala** and **SnappShop**.

## Status

**Phase 5 — Shopping Intelligence implemented.**

## Registered tools

- `list_stores` — registered adapters
- `search_digikala` — search normalized Digikala products
- `get_digikala_product` — fetch normalized Digikala details
- `search_snappshop` — search normalized SnappShop products
- `get_snappshop_product` — fetch normalized SnappShop details, variants and offers
- `compare_products` — identity, variant, specification and offer comparison
- `compare_offers` — normalized offer and price comparison
- `compare_prices` — backward-compatible price comparison
- `find_best_price` — lowest observed comparable offer with explicit filters
- `find_best_value` — policy-driven offer selection with explainable reasons
- `analyze_offers` — expose observed price, discount, seller, warranty and availability signals

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

## Shopping intelligence

Phase 5 adds provider-neutral intelligence on canonical offers. It does not invent prices, availability or specifications.

- `find_best_price` filters normalized offers and compares only offers with the same currency.
- Seller IDs, minimum seller rating, warranty and availability can be explicit filters.
- `find_best_value` uses an ordered policy such as `price`, `availability`, `warranty`, `seller_rating` or `discount`; there is no hidden composite score.
- Discount percentages are calculated only when both current and observed regular prices are present.
- `PriceObservation` / `PriceHistoryProvider` define an optional historical-price contract without requiring a storage backend.
- `StockMonitorHook` defines an optional application hook for stock monitoring.

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
5. Shopping Intelligence — complete
6. Production Hardening, CI & Release

## Design principles

- Store-specific code stays inside adapters.
- Comparison operates only on normalized domain models.
- Missing upstream data is represented as unknown, never invented.
- Product variants remain explicit.
- External-store behavior is isolated behind adapter boundaries.
