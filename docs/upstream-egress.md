# Upstream egress

DigiSnap-MCP keeps its MCP listener independent from store-provider networking.

## Optional provider proxy

Set `UPSTREAM_HTTP_PROXY` when Digikala and SnappShop must be reached through an operator-controlled HTTP(S) egress gateway:

```text
UPSTREAM_HTTP_PROXY=http://gateway.example:8080
```

When unset, provider traffic uses direct outbound HTTPS.

The proxy value is not logged by DigiSnap-MCP. Do not commit credentials or proxy URLs containing secrets.

### Iran-origin upstreams

The production investigation in Phase 8.1 reproduced these responses from a foreign GitHub Actions runner:

- Digikala API: HTTP 307 from DigiCDN Edge, redirecting to the same API URL and issuing a DigiCDN cookie.
- SnappShop API: HTTP 403 from Sotoon CDN with a response asking VPN users to turn VPN off.

These observations establish that the foreign request origin is being rejected by the upstream/CDN path for the tested requests. They do not prove that every foreign IP is blocked, and they do not prove successful access from every Iranian network.

Therefore DigiSnap-MCP does not hard-code a third-party proxy. A real Iran-capable egress gateway must be provisioned and tested before claiming live recovery.

The planned Cloudflare deployment must preserve this constraint: a globally distributed runtime is not by itself an Iran-origin egress.
