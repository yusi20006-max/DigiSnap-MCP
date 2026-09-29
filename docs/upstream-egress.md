# Upstream egress

DigiSnap-MCP keeps its MCP listener independent from store-provider networking.

## Optional provider proxy

Set `UPSTREAM_HTTP_PROXY` when Digikala and SnappShop must be reached through an operator-controlled egress gateway.

Supported schemes:

```text
UPSTREAM_HTTP_PROXY=http://gateway.example:8080
UPSTREAM_HTTP_PROXY=https://gateway.example:8443
UPSTREAM_HTTP_PROXY=socks5://gateway.example:1080
UPSTREAM_HTTP_PROXY=socks5h://gateway.example:1080
```

`socks5h://` performs hostname resolution through the SOCKS5 gateway; `socks5://` resolves the destination hostname locally.

When unset, provider traffic uses direct outbound HTTPS.

The proxy value is not logged by DigiSnap-MCP. Do not commit credentials or proxy URLs containing secrets.

## Iran-origin upstreams

The production investigation in Phase 8.1 reproduced these responses from a foreign GitHub Actions runner:

- Digikala API: HTTP 307 from DigiCDN Edge, redirecting to the same API URL and issuing a DigiCDN cookie.
- SnappShop API: HTTP 403 from Sotoon CDN with a response asking VPN users to turn VPN off.

The same direct tests from the user's Iran-side Termux environment reproduced Digikala 307 and SnappShop 403.

A real SOCKS5 route was then tested from that Iran-side environment:

- Digikala `/v3/search/`: HTTP 200 on three consecutive requests.
- SnappShop `/search/v1`: HTTP 200 on three consecutive requests.

This demonstrates a working SOCKS5 egress path for the tested requests. It does not prove that the public SOCKS5 endpoint is stable, secure, or suitable for production.

Therefore DigiSnap-MCP does not hard-code a third-party proxy. A real operator-controlled Iran-capable egress gateway should be provisioned and tested before production use.

The planned Cloudflare deployment must preserve this constraint: a globally distributed runtime is not by itself an Iran-origin egress.
