# Contributing to DigiSnap-MCP

## Development

Requires Python 3.11+.

Run `python -m pip install -e ".[dev]"`, then `ruff check src tests`, `pytest --cov=digisnap_mcp --cov-report=term-missing`, and `python -m compileall -q src`.

## Pull requests

Use the project workflow: Issue → Implement → Test → PR → CI → Merge → Release.

Keep provider-specific behavior inside adapters and preserve the canonical domain models. Do not commit credentials, cookies, private API keys, or live customer data.

## Provider changes

Document endpoint assumptions and add deterministic fixtures/tests for parsing and error handling. Upstream provider APIs are undocumented and may change.
