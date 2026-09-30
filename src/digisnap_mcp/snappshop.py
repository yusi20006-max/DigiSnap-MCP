"""SnappShop adapter using the public web JSON API surface.

The upstream API is undocumented and may change. Provider-specific transport
and parsing stay isolated here so the canonical domain remains stable.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .transport import RequestPacer, TransportError, request_json

from .adapters import StoreAdapter
from .errors import AdapterError, ProductNotFoundError, RateLimitError
from .models import Offer, Product, Seller, Specification, Store

SNAPPSHOP_STORE = Store("snappshop", "SnappShop")
logger = logging.getLogger(__name__)
_SNAPPSHOP_PACER = RequestPacer(0.5)


class SnappShopAdapter(StoreAdapter):
    """Normalize SnappShop search and product responses."""

    store_id = "snappshop"
    store_name = "SnappShop"

    def __init__(
        self,
        *,
        base_url: str = "https://apix.snappshop.ir",
        timeout: float = 15.0,
        latitude: float | None = 35.77331,
        longitude: float | None = 51.418591,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.latitude = latitude
        self.longitude = longitude
        self._opener = opener

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.latitude is not None:
            params["lat"] = self.latitude
        if self.longitude is not None:
            params["lng"] = self.longitude
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json" if payload is not None else "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140.0.0.0 Mobile Safari/537.36",
            "Origin": "https://snappshop.ir",
            "Referer": "https://snappshop.ir/",
        }
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method.upper())
        try:
            return request_json(self._opener, request, timeout=self.timeout, pace=_SNAPPSHOP_PACER)
        except TransportError as exc:
            logger.error("SnappShop request failed path=%s status=%s", path, exc.status)
            if exc.status == 404:
                raise ProductNotFoundError("SnappShop resource not found") from exc
            if exc.status == 429:
                raise RateLimitError("SnappShop rate limit exceeded") from exc
            raise AdapterError(f"SnappShop request failed: {exc}") from exc

    @staticmethod
    def _first(data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = data.get(key)
            if value is not None:
                return value
        return None

    @staticmethod
    def _price(value: Any) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _seller_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        vendors = data.get("vendors") or data.get("sellers") or []
        result: dict[str, dict[str, Any]] = {}
        if isinstance(vendors, list):
            for vendor in vendors:
                if isinstance(vendor, dict):
                    vendor_id = vendor.get("id") or vendor.get("vendor_id")
                    if vendor_id is not None:
                        result[str(vendor_id)] = vendor
        return result

    @classmethod
    def _specifications(cls, data: dict[str, Any]) -> tuple[Specification, ...]:
        raw = data.get("attributes") or data.get("specifications") or []
        result: list[Specification] = []
        if isinstance(raw, dict):
            raw = [{"name": key, "value": value} for key, value in raw.items()]
        if not isinstance(raw, list):
            return ()
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = cls._first(item, "title", "name")
            value = item.get("value")
            if name is not None and value is not None:
                result.append(Specification(str(name), str(value)))
        return tuple(result)

    @staticmethod
    def _attribute_labels(
        data: dict[str, Any],
    ) -> dict[str, str]:
        labels: dict[str, str] = {}
        for item in data.get("configurable_attribute", []) or []:
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if isinstance(value, dict):
                value_id = value.get("id")
                title = value.get("title")
                if value_id is not None and title is not None:
                    labels[str(value_id)] = str(title)
        return labels

    @classmethod
    def _variant_label(
        cls,
        variant: dict[str, Any],
        labels: dict[str, str],
    ) -> str | None:
        values: list[str] = []
        for attr in variant.get("attribute_ids", []) or []:
            if not isinstance(attr, dict):
                continue
            value_id = attr.get("attribute_value_id")
            if value_id is not None and str(value_id) in labels:
                values.append(labels[str(value_id)])
        return ", ".join(values) if values else None

    @classmethod
    def _offer(
        cls,
        vendor: dict[str, Any],
        *,
        seller_map: dict[str, dict[str, Any]],
        variant_id: str,
        product_url: str | None,
        variant_label: str | None,
        warranty_map: dict[str, str],
    ) -> Offer:
        vendor_id = cls._first(vendor, "vendor_id", "seller_id") or "unknown"
        seller_raw = seller_map.get(str(vendor_id), {})
        seller_name = cls._first(seller_raw, "title", "name", "title_fa") or str(vendor_id)
        seller = Seller(
            str(vendor_id),
            str(seller_name),
        )

        regular = cls._price(cls._first(vendor, "price", "original_price"))
        special = cls._price(cls._first(vendor, "special_price", "discounted_price"))
        price = special if special is not None and special > 0 and (regular is None or special < regular) else regular
        stock = vendor.get("stock")
        available = bool(
            vendor.get("is_available_in_vendor_inventory")
            or vendor.get("is_available_in_shop")
            or (isinstance(stock, (int, float)) and stock > 0)
        )
        warranty_id = cls._first(vendor, "warranty_id")
        warranty = warranty_map.get(str(warranty_id)) if warranty_id is not None else None
        offer_id = cls._first(vendor, "vendor_product_info_id", "id") or f"{variant_id}:{vendor_id}"

        return Offer(
            id=str(offer_id),
            store=SNAPPSHOP_STORE,
            seller=seller,
            price=price,
            currency="IRR",
            available=available,
            url=product_url,
            warranty=warranty,
            condition="new",
            regular_price=regular,
        )

    @classmethod
    def _product(cls, payload: dict[str, Any], product_id: str | None = None) -> Product:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            raise AdapterError("SnappShop product payload has invalid data")

        raw_id = data.get("id") or product_id
        if raw_id is None:
            raise AdapterError("SnappShop product payload has no product id")

        content = data.get("content") if isinstance(data.get("content"), dict) else {}
        title = cls._first(content, "title_fa", "title", "name") or data.get("title") or f"SnappShop product {raw_id}"
        brand_raw = data.get("brand")
        brand = None
        if isinstance(brand_raw, dict):
            brand = cls._first(brand_raw, "title_fa", "title", "name")
        elif brand_raw:
            brand = str(brand_raw)

        slug = data.get("slug")
        page = data.get("page") if isinstance(data.get("page"), dict) else {}
        url = page.get("canonical_url") or page.get("redirect_url")
        if not url:
            url = f"https://snappshop.ir/product/{raw_id}"

        seller_map = cls._seller_map(data)
        warranty_map: dict[str, str] = {}
        for warranty in data.get("warranties", []) or []:
            if isinstance(warranty, dict) and warranty.get("id") is not None:
                name = warranty.get("name") or warranty.get("company_title")
                if name:
                    warranty_map[str(warranty["id"])] = str(name)

        labels = cls._attribute_labels(data)
        offers: list[Offer] = []
        variants = data.get("variants") or []
        if isinstance(variants, list):
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                variant_id = str(variant.get("variation_id") or raw_id)
                variant_label = cls._variant_label(variant, labels)
                for vendor in variant.get("vendor", []) or []:
                    if isinstance(vendor, dict):
                        offers.append(
                            cls._offer(
                                vendor,
                                seller_map=seller_map,
                                variant_id=variant_id,
                                product_url=url,
                                variant_label=variant_label,
                                warranty_map=warranty_map,
                            )
                        )

        variant_values = []
        for variant in variants if isinstance(variants, list) else []:
            if isinstance(variant, dict):
                label = cls._variant_label(variant, labels)
                if label:
                    variant_values.append(label)
        variant = ", ".join(dict.fromkeys(variant_values)) or None

        return Product(
            id=str(raw_id),
            title=str(title).strip(),
            store=SNAPPSHOP_STORE,
            url=str(url),
            brand=str(brand) if brand else None,
            model=None,
            variant=variant,
            specifications=cls._specifications(data),
            offers=tuple(offers),
            metadata={
                "source": "snappshop",
                "slug": slug,
                "variant_count": len(variants) if isinstance(variants, list) else 0,
            },
        )

    @classmethod
    def _search_products(cls, payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        structure = data.get("structure") or []
        products: list[dict[str, Any]] = []
        seen: set[str] = set()
        if isinstance(structure, list):
            for section in structure:
                if not isinstance(section, dict):
                    continue
                for item in section.get("items", []) or []:
                    if not isinstance(item, dict):
                        continue
                    item_id = item.get("id") or item.get("href")
                    if item_id is None or str(item_id) in seen:
                        continue
                    seen.add(str(item_id))
                    products.append(item)
        return products

    @classmethod
    def _search_card(cls, item: dict[str, Any]) -> Product:
        product_id = item.get("id")
        if product_id is None:
            raise AdapterError("SnappShop search item has no product id")
        price_raw = item.get("price") if isinstance(item.get("price"), dict) else {}
        regular = cls._price(price_raw.get("price"))
        special = cls._price(price_raw.get("discounted_price"))
        price = special if special is not None and special > 0 and (regular is None or special < regular) else regular
        href = item.get("href")
        url = str(href) if href else f"https://snappshop.ir/product/{product_id}"
        if url.startswith("/"):
            url = f"https://snappshop.ir{url}"
        offer = Offer(
            id=str(product_id),
            store=SNAPPSHOP_STORE,
            seller=None,
            price=price,
            currency="IRR",
            available=price is not None,
            url=url,
            condition="new",
            regular_price=regular,
        )
        return Product(
            id=str(product_id),
            title=str(item.get("title") or "").strip(),
            store=SNAPPSHOP_STORE,
            url=url,
            specifications=(),
            offers=(offer,),
            metadata={
                "source": "snappshop",
                "rating": (item.get("state") or {}).get("rate"),
                "rating_count": (item.get("state") or {}).get("rate_count"),
                "advertised": bool(item.get("is_ads")),
                "fake": bool(item.get("is_fake")),
            },
        )

    def search(self, query: str, *, limit: int = 20) -> tuple[Product, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        limit = max(1, min(limit, 100))
        payload = self._request_json(
            "POST",
            "/search/v1",
            payload={"query": query, "render": 4},
        )
        items = self._search_products(payload)
        return tuple(self._search_card(item) for item in items[:limit])

    def get_product(self, product_id: str) -> Product:
        if not str(product_id).strip():
            raise ValueError("product_id cannot be empty")
        encoded = str(product_id).strip()
        payload = self._request_json("GET", f"/products/v2/{encoded}")
        return self._product(payload, product_id=encoded)
