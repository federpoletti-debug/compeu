"""Exoscale: the public pricing JSON behind exoscale.com/pricing, joined with the
public instance-type API (no authentication for either).

GET https://portal.exoscale.com/api/pricing/opencompute
    -> {"eur": {"running_<family>_<size>": "<price per hour>", ...}, "chf": ..., "usd": ...}
GET https://api-ch-gva-2.exoscale.com/v2/instance-type
    -> family, size, number of GPUs and the zones where each type runs

The APIs do not name the GPU model, so the family-to-model table below is taken
from Exoscale's GPU product pages (https://www.exoscale.com/gpu/). A GPU family
missing from the table is reported, not guessed.
"""

from __future__ import annotations

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

PRICING_URL = "https://portal.exoscale.com/api/pricing/opencompute"
TYPES_URL = "https://api-ch-gva-2.exoscale.com/v2/instance-type"
CURRENCY = "eur"

FAMILY_GPU = {
    "gpu": "NVIDIA P100",
    "gpu2": "NVIDIA V100",
    "gpu3": "NVIDIA A40",
    "gpua5000": "NVIDIA RTX A5000",
    "gpu3080ti": "NVIDIA RTX 3080 Ti",
    "gpua30": "NVIDIA A30",
    "gpurtx6000pro": "NVIDIA RTX PRO 6000",
}


class Exoscale:
    provider = "exoscale"
    version = 1
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        prices = http.get(PRICING_URL, timeout=TIMEOUT)
        prices.raise_for_status()
        types = http.get(TYPES_URL, timeout=TIMEOUT)
        types.raise_for_status()
        table = prices.json()[CURRENCY]
        gpu_types = [t for t in types.json()["instance-types"] if t.get("gpus")]
        records = []
        for t in gpu_types:
            key = f"running_{t['family']}_{t['size']}"
            records.append({"type": t, "price_key": key, "price": table.get(key)})
        return Fetched(source_url=PRICING_URL, records=records)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            t = rec["type"]
            if rec["price"] is None:
                fetched.problems.append(f"{rec['price_key']}: type listed without a price")
                continue
            gpu = FAMILY_GPU.get(t["family"])
            if gpu is None:
                fetched.problems.append(f"{t['family']}: GPU family not in the model table")
                continue
            for zone in t.get("zones") or []:
                offers.append(
                    Offer(
                        sku=f"{t['family']}.{t['size']}",
                        gpu_raw=gpu,
                        gpu_count=int(t["gpus"]),
                        price=dec(rec["price"]),
                        currency=CURRENCY.upper(),
                        unit="hour",
                        region=zone,
                        country=zone.split("-")[0].upper(),
                    )
                )
        return offers
