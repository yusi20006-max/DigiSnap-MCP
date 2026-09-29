"""Small dependency-free HTTP transport used by store adapters."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request
from typing import Any, Callable

logger = logging.getLogger("digisnap_mcp.transport")


@dataclass(frozen=True)
class TransportError(Exception):
    message: str
    status: int | None = None
    retryable: bool = False
    location: str | None = None

    def __str__(self) -> str:
        return self.message


def request_json(
    opener: Callable[..., Any],
    request: Request,
    *,
    timeout: float,
    retries: int = 2,
    backoff: float = 0.25,
) -> dict[str, Any]:
    """Fetch JSON with bounded retries for rate limits and transient failures."""
    attempts = max(0, retries) + 1
    for attempt in range(attempts):
        try:
            with opener(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status >= 400:
                    raise TransportError(
                        f"HTTP {status}",
                        status=status,
                        retryable=status == 429 or status >= 500,
                    )
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise TransportError("upstream returned a non-object JSON payload")
                return payload
        except TransportError as exc:
            if not exc.retryable or attempt == attempts - 1:
                raise
            logger.warning("transient upstream response; retry=%s status=%s", attempt + 1, exc.status)
        except HTTPError as exc:
            retryable = exc.code == 429 or exc.code >= 500
            if not retryable or attempt == attempts - 1:
                raise TransportError(f"HTTP {exc.code}", status=exc.code, retryable=retryable, location=exc.headers.get("Location")) from exc
            logger.warning("transient HTTP error; retry=%s status=%s", attempt + 1, exc.code)
        except (URLError, TimeoutError, OSError) as exc:
            if attempt == attempts - 1:
                raise TransportError(f"network request failed: {exc}", retryable=True) from exc
            logger.warning("transient network error; retry=%s", attempt + 1)
        except json.JSONDecodeError as exc:
            raise TransportError(f"invalid JSON response: {exc}") from exc
        if backoff > 0:
            time.sleep(backoff * (2**attempt))
    raise AssertionError("unreachable")
