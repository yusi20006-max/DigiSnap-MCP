"""Digikala adapter using its public web API surface.

The upstream API is undocumented and may change. All provider-specific parsing
is isolated in this module so the core comparison layer stays stable.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .transport import TransportError, request_json

from .adapters import StoreAdapter
from .errors import AdapterError, ProductNotFoundError, RateLimitError
from .models import Offer, Product, Seller, Specification, Store

DIGIKALA_STORE = Store("digikala", "Digikala")
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)


class DigikalaAdapter(StoreAdapter):
    store_id = "digikala"
    store_name = "Digikala"

    def __init__(
        self,
        *,
        base_url: str = "https://api.digikala.com",
        timeout: float = 15.0,
        opener=urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = opener

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {"Accept": "application/json", "User-Agent": "DigiSnap-MCP/0.6"}
        request = Request(url, headers=headers)
        try:
            return request_json(self._opener, request, timeout=self.timeout)
except TransportError as exc:
            raise
        except TransportError as exc:
            logger.error("Digikala request failed path=%s status=%s", path, exc.status)
            if exc.status == 429:
                raise RateLimitError("Digikala rate limit exceeded") from exc
            raise AdapterError(f"Digikala request failed: {exc}") from exc

    @staticmethod
    def _price(value: Any) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _first(data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if data.get(key) is not None:
                return data[key]
        return None

    @classmethod
    def _offer(cls, raw: dict[str, Any], *, fallback_id: str, product_url: str | None) -> Offer:
        seller_raw = raw.get("seller") or raw.get("seller_info") or {}
        seller = None
        if isinstance(seller_raw, dict):
            seller_id = cls._first(seller_raw, "id", "seller_id")
            seller_name = cls._first(seller_raw, "name", "title")
            if seller_id is not None or seller_name:
                seller = Seller(
                    str(seller_id or "unknown"),
                    str(seller_name or "Unknown seller"),
                    cls._as_float(cls._first(seller_raw, "rating", "rating_value")),
                )
        return Offer(
            id=str(cls._first(raw, "id", "offer_id") or fallback_id),
            store=DIGIKALA_STORE,
            seller=seller,
            price=cls._price(cls._first(raw, "price", "selling_price", "final_price")),
            currency="IRR",
            available=cls._availability(raw),
            url=cls._first(raw, "url", "product_url") or product_url,
            warranty=cls._warranty(raw),
            condition=cls._first(raw, "condition", "product_condition"),
            regular_price=cls._price(cls._first(raw, "original_price", "old_price", "rrp", "regular_price")),
        )

    @staticmethod
    def _as_float(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _availability(raw: dict[str, Any]) -> bool | None:
        value = raw.get("available")
        if isinstance(value, bool):
            return value
        stock = raw.get("stock")
        if isinstance(stock, dict):
            if isinstance(stock.get("is_in_stock"), bool):
                return stock["is_in_stock"]
            if isinstance(stock.get("available"), bool):
                return stock["available"]
        return None

    @staticmethod
    def _warranty(raw: dict[str, Any]) -> str | None:
        warranty = raw.get("warranty")
        if isinstance(warranty, str):
            return warranty
        if isinstance(warranty, dict):
            value = warranty.get("title") or warranty.get("name")
            return str(value) if value else None
        return None

    @classmethod
    def _specifications(cls, raw: dict[str, Any]) -> tuple[Specification, ...]:
        source = raw.get("specifications") or raw.get("specs") or []
        result: list[Specification] = []
        if isinstance(source, dict):
            source = [{"name": key, "value": value} for key, value in source.items()]
        for item in source if isinstance(source, list) else []:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("title")
            value = item.get("value")
            if value is None and isinstance(item.get("values"), list):
                value = ", ".join(str(v) for v in item["values"])
            if name is not None and value is not None:
                result.append(Specification(str(name), str(value)))
        return tuple(result)

    @classmethod
    def _product(cls, raw: dict[str, Any]) -> Product:
        product_id = cls._first(raw, "id", "product_id")
        if product_id is None:
            raise AdapterError("Digikala product payload has no product id")
        title = cls._first(raw, "title", "name") or f"Digikala product {product_id}"
        url = cls._first(raw, "url", "product_url")
        brand = raw.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("title") or brand.get("name")
        model = cls._first(raw, "model", "model_name")
        variant = cls._first(raw, "variant", "variant_title")
        offer_sources = raw.get("offers") or raw.get("sellers") or []
        offers = []
        if isinstance(offer_sources, list):
            for index, offer in enumerate(offer_sources):
                if isinstance(offer, dict):
                    offers.append(cls._offer(offer, fallback_id=f"{product_id}-{index}", product_url=url))
        direct_price = cls._first(raw, "price", "selling_price", "final_price")
        if not offers and direct_price is not None:
            offers.append(
                cls._offer(raw, fallback_id=str(product_id), product_url=url)
            )
        return Product(
            id=str(product_id),
            title=str(title),
            store=DIGIKALA_STORE,
            url=str(url) if url else None,
            brand=str(brand) if brand else None,
            model=str(model) if model else None,
            variant=str(variant) if variant else None,
            specifications=cls._specifications(raw),
            offers=tuple(offers),
            metadata={"source": "digikala"},
        )

    @staticmethod
    def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data") or payload
        for container in (data, payload):
            if isinstance(container, dict):
                products = container.get("products") or container.get("items")
                if isinstance(products, list):
                    return [item for item in products if isinstance(item, dict)]
                search = container.get("search")
                if isinstance(search, dict) and isinstance(search.get("products"), list):
                    return [item for item in search["products"] if isinstance(item, dict)]
        return []

    def search(self, query: str, *, limit: int = 20) -> tuple[Product, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        limit = max(1, min(limit, 100))
        payload = self._request_json("/v3/search/", {"q": query, "page": 1})
        products = tuple(self._product(item) for item in self._items(payload))
        return products[:limit]

    def get_product(self, product_id: str) -> Product:
        if not str(product_id).strip():
            raise ValueError("product_id cannot be empty")
        encoded = quote(str(product_id).strip(), safe="")
        payload = self._request_json(f"/v2/product/{encoded}/")
        try:
            data = payload.get("data") or payload
            raw = data.get("product") if isinstance(data, dict) else None
            if not isinstance(raw, dict):
                raw = data if isinstance(data, dict) else {}
            return self._product(raw)
        except (AdapterError, ProductNotFoundError):
            raise
        except Exception as exc:
            raise ProductNotFoundError(f"could not parse Digikala product {product_id}") from exc
