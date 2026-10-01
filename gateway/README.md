# DigiSnap Iran Egress Gateway

Restricted HTTP relay for DigiSnap-MCP.

## Security model

- Not an open proxy.
- Requires `Authorization: Bearer <EGRESS_GATEWAY_TOKEN>`.
- Allows only `api.digikala.com` and `apix.snappshop.ir`.
- Allows only HTTPS upstream URLs.
- Allows only GET and POST.
- Binds to localhost by default.
- Intended to be exposed through a controlled HTTPS tunnel such as Cloudflare Tunnel.
- Does not implement CAPTCHA, authentication bypass, proxy rotation, or anti-abuse evasion.

## Run

```bash
export EGRESS_GATEWAY_TOKEN='replace-with-a-long-random-secret'
python -m gateway.server
```

Health:

```bash
curl http://127.0.0.1:8787/health
```

DigiSnap Railway variables:

```
UPSTREAM_EGRESS_GATEWAY=https://<gateway-host>
UPSTREAM_EGRESS_TOKEN=<same-secret>
```

The DigiSnap client sends a restricted JSON envelope to `/v1/fetch`; the gateway performs the provider request from its own network and returns the upstream status, selected headers and body.

## Cloudflare Tunnel

For development, Cloudflare Quick Tunnel can expose the local HTTP gateway:

```bash
cloudflared tunnel --url http://127.0.0.1:8787
```

Quick Tunnels are temporary and intended for testing. For production, use a named Cloudflare Tunnel with a stable hostname and an access policy.

## Operational requirement

The machine running this gateway must have the Iran-side network path that has already been verified to return HTTP 200 JSON from both Digikala and SnappShop. The gateway itself does not create that network path.
