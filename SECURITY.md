# Security Policy

## Reporting

Please report suspected security issues privately to the repository maintainer rather than opening a public issue with exploitable details.

## Scope

DigiSnap-MCP does not intentionally store credentials or customer data. Store adapters communicate with public upstream endpoints and should treat upstream responses as untrusted input.

Dependency and static checks run in CI. Keep dependencies current and avoid logging request headers, tokens, cookies, or full upstream payloads.
