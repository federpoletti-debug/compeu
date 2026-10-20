"""Verda (formerly DataCrunch): public instance-types API (no authentication).

GET https://api.verda.com/v1/instance-types
Each instance type carries an on-demand price per hour, a spot price and, for
some types, a dynamic price. Currency is given per record.
"""

from __future__ import annotations

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://api.verda.com/v1/instance-types"


class Verda:
    provider = "verda"
    version = 1
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        records = [t for t in r.json() if (t.get("gpu") or {}).get("number_of_gpus")]
        return Fetched(source_url=URL, records=records)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for t in fetched.records:
            currency = (t.get("currency") or "").upper()
            if not currency:
                fetched.problems.append(f"{t.get('instance_type')}: no currency, skipped")
                continue
            prices = {
                "on_demand": t.get("price_per_hour"),
                "spot": t.get("spot_price"),
                "dynamic": t.get("dynamic_price"),
            }
            for model, value in prices.items():
                if value in (None, "", "0"):
                    continue
                offers.append(
                    Offer(
                        sku=t["instance_type"],
                        gpu_raw=t.get("name") or t.get("model") or "",
                        gpu_count=int(t["gpu"]["number_of_gpus"]),
                        price=dec(value),
                        currency=currency,
                        unit="hour",
                        pricing_model=model,
                        region="catalogue",
                        extra={
                            "gpu_memory_gb": (t.get("gpu_memory") or {}).get("size_in_gigabytes")
                        },
                    )
                )
        return offers
