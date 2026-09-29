# DigiSnap-MCP

MCP server for comparing products, prices, sellers, availability and specifications across **Digikala** and **SnappShop**.

## Status

**Phase 2 — Digikala Adapter implemented.**

## Digikala tools

- `search_digikala` — search products and return normalized results
- `get_digikala_product` — fetch one product and normalize specifications/offers
- `list_stores` — currently reports `digikala`

The Digikala web API is undocumented and may change. Provider-specific HTTP,
endpoint paths and payload parsing are isolated in the adapter. HTTP failures
and rate limits use explicit domain errors.

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
3. SnappShop Adapter
4. Cross-Store Product & Offer Comparison
5. Shopping Intelligence
6. Production Hardening, CI & Release

## Design principles

- Store-specific code stays inside adapters.
- Comparison operates only on normalized domain models.
- Missing upstream data is represented as unknown, never invented.
- Product variants remain explicit.
- External-store behavior is isolated behind adapter boundaries.
