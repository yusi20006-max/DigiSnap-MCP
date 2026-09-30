# Upstream resilience

DigiSnap-MCP keeps provider-specific resilience below the MCP and comparison layers.

## Behavior

- Upstream HTTP status is classified as success, redirect/challenge, blocked (403), rate-limited (429), transient server error (5xx), or client error.
- Digikala and SnappShop requests use a host-scoped 500 ms minimum interval.
- Successful GET JSON responses use a small process-local TTL cache (30 seconds by default).
- Upstream retries are bounded and use exponential backoff. Retry-After is honored for rate limits when it contains a numeric delay.
- Redirects are not followed automatically. A short-lived upstream challenge can therefore be observed and retried without hiding the provider response.
- The upstream opener has a process-local cookie jar so provider challenge cookies can persist across bounded retries.
- Diagnostics log only category, status and attempt number; request bodies, response bodies, cookies and proxy credentials are not logged.

## Egress

UPSTREAM_HTTP_PROXY remains the only upstream egress control:

- http://host:port
- https://host:port
- socks5://host:port
- socks5h://host:port

No public proxy is hard-coded or selected automatically.

## Failure semantics

A provider block/challenge is reported as an upstream adapter failure and is not treated as an MCP transport failure. 403 is not retried automatically. 429 and 5xx responses are retried within the configured bound.

This layer does not bypass authentication, CAPTCHA, access controls or provider anti-abuse mechanisms.
