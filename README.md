# DigiSnap-MCP

MCP server for comparing products, prices, sellers, availability and specifications across **Digikala** and **SnappShop**.

## Status

Phase 1 — Core MCP Server & Architecture is implemented.

## Core architecture

```
Store Adapter(s)
      |
      v
Canonical Product / Offer / Seller models
      |
      v
Comparison Engine
      |
      v
MCP Tools
```

The comparison layer is provider-neutral. Digikala and SnappShop integrations will be implemented as independent adapters in later phases.

## Current MCP tools

- `list_stores`
- `compare_prices`

## Development

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
```

Run the MCP server:

```bash
digisnap-mcp
```

The server currently uses MCP stdio transport.

## Roadmap

1. Core MCP Server & Architecture
2. Digikala Adapter
3. SnappShop Adapter
4. Cross-Store Product & Offer Comparison
5. Shopping Intelligence
6. Production Hardening, CI & Release

## Design principles

- Store-specific code stays inside adapters.
- Comparison operates only on normalized domain models.
- Missing upstream data is represented as unknown, never invented.
- Product variants remain explicit.
- External-store behavior is treated as unstable and isolated behind adapter boundaries.
