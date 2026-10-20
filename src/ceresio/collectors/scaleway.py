"""Scaleway: public product catalogue API (no authentication).

GET https://api.scaleway.com/product-catalog/v2alpha1/public-catalog/products
Paginated. GPU instances are products with product_category "Instance" and a
hardware.gpu block. Prices are EUR per minute, excluding VAT.
"""

from __future__ import annotations

from decimal import Decimal

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://api.scaleway.com/product-catalog/v2alpha1/public-catalog/products"
PAGE_SIZE = 1000


class Scaleway:
    provider = "scaleway"
    version = 1
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        records, page, total = [], 1, None
        while True:
            r = http.get(URL, params={"page_size": PAGE_SIZE, "page": page}, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            total = data["total_count"]
            batch = data["products"]
            records += [p for p in batch if _is_gpu_instance(p)]
            seen = (page - 1) * PAGE_SIZE + len(batch)
            if not batch or seen >= total:
                break
            page += 1
        return Fetched(source_url=URL, records=records)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for p in fetched.records:
            if p.get("status") != "general_availability":
                fetched.problems.append(f"{p.get('sku')}: status {p.get('status')}, skipped")
                continue
            gpu = p["properties"]["hardware"]["gpu"]
            price = p.get("price", {}).get("retail_price")
            unit = (p.get("unit_of_measure") or {}).get("unit")
            if not price or unit not in ("minute", "hour") or not gpu.get("count"):
                fetched.problems.append(f"{p.get('sku')}: missing price, unit or GPU count")
                continue
            amount = dec(price.get("units", 0)) + Decimal(price.get("nanos", 0)) / Decimal(10**9)
            size = dec(p["unit_of_measure"].get("size", 1))  # price is per `size` units
            amount = amount / size
            zone = (p.get("locality") or {}).get("zone")
            offers.append(
                Offer(
                    sku=p["product"],
                    gpu_raw=gpu["type"],
                    gpu_count=int(gpu["count"]),
                    price=amount,
                    currency=price["currency_code"],
                    unit=unit,
                    region=zone,
                    country=zone.split("-")[0].upper() if zone else None,
                )
            )
        return offers


def _is_gpu_instance(p: dict) -> bool:
    if p.get("product_category") != "Instance":
        return False
    gpu = ((p.get("properties") or {}).get("hardware") or {}).get("gpu") or {}
    return bool(gpu.get("count"))
